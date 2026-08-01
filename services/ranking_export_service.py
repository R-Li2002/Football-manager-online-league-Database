from __future__ import annotations

import io
import posixpath
import re
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.orm import Session

from services.import_service import resolve_import_root
from services.ranking_import_service import preview_ranking_workbook
from services.ranking_service import get_rankings

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CALC_CHAIN_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/calcChain"


def find_latest_ranking_workbook() -> Path | None:
    ranking_root = resolve_import_root() / "Rate"
    candidates = [
        path
        for pattern in ("*.xlsx", "*.xlsm")
        for path in ranking_root.glob(pattern)
        if path.is_file() and not path.name.startswith("~$")
    ]
    return max(candidates, key=lambda path: (path.stat().st_mtime, path.stat().st_size, path.name), default=None)


def _worksheet_archive_path(archive: ZipFile, sheet_name: str) -> str:
    workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
    relationship_id = None
    for sheet in workbook_root.findall(f".//{{{MAIN_NS}}}sheet"):
        if sheet.get("name") == sheet_name:
            relationship_id = sheet.get(f"{{{OFFICE_REL_NS}}}id")
            break
    if not relationship_id:
        raise ValueError(f"排位模板中未找到工作表：{sheet_name}")

    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for relationship in relationships.findall(f"{{{PACKAGE_REL_NS}}}Relationship"):
        if relationship.get("Id") == relationship_id:
            target = relationship.get("Target", "").lstrip("/")
            if target.startswith("xl/"):
                return posixpath.normpath(target)
            return posixpath.normpath(posixpath.join("xl", target))
    raise ValueError(f"排位模板工作表关系缺失：{sheet_name}")


def _cell_style_attributes(opening_attributes: str) -> str:
    style = re.search(r'\bs="([^"]+)"', opening_attributes)
    return f' s="{style.group(1)}"' if style else ""


def _replace_cell(xml: str, reference: str, body: str, *, cell_type: str | None = None) -> str:
    pattern = re.compile(
        rf'<c\b(?P<attrs>(?=[^>]*\br="{re.escape(reference)}")[^>]*?)(?:/>|>.*?</c>)',
        re.DOTALL,
    )
    match = pattern.search(xml)
    if not match:
        raise ValueError(f"排位模板缺少单元格：{reference}")
    style = _cell_style_attributes(match.group("attrs"))
    type_attribute = f' t="{cell_type}"' if cell_type else ""
    replacement = f'<c r="{reference}"{style}{type_attribute}>{body}</c>'
    return xml[:match.start()] + replacement + xml[match.end():]


def _number(value: int | float) -> str:
    if isinstance(value, int):
        return str(value)
    return format(float(value), ".15g")


def _patch_ranking_sheet(sheet_xml: bytes, rows) -> bytes:
    xml = sheet_xml.decode("utf-8")
    start_row = 7
    template_last_row = 66
    if len(rows) > template_last_row - start_row + 1:
        raise ValueError("当前球队数量超过排位模板可用行数")

    for offset, row in enumerate(rows):
        row_no = start_row + offset
        draws = int(row.draws)
        xml = _replace_cell(xml, f"A{row_no}", f"<v>{int(row.rank)}</v>")
        team_name = str(row.team_name).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        xml = _replace_cell(xml, f"B{row_no}", f"<is><t>{team_name}</t></is>", cell_type="inlineStr")
        xml = _replace_cell(xml, f"C{row_no}", f"<v>{_number(row.base_points)}</v>")
        xml = _replace_cell(xml, f"D{row_no}", f"<f>E{row_no}+F{row_no}+{draws}</f>")
        xml = _replace_cell(xml, f"E{row_no}", f"<v>{int(row.wins)}</v>")
        xml = _replace_cell(xml, f"F{row_no}", f"<v>{int(row.losses)}</v>")
        xml = _replace_cell(xml, f"G{row_no}", f'<f>IFERROR(E{row_no}/D{row_no},"")</f>')
        xml = _replace_cell(xml, f"H{row_no}", f"<f>C{row_no}+D{row_no}*20</f>")

    first_empty_row = start_row + len(rows)
    for row_no in range(first_empty_row, template_last_row + 1):
        for column in "ABCDEFGH":
            xml = _replace_cell(xml, f"{column}{row_no}", "")
    return xml.encode("utf-8")


def _mark_workbook_for_recalculation(workbook_xml: bytes) -> bytes:
    xml = workbook_xml.decode("utf-8")
    replacement = '<calcPr calcId="0" calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1" calcOnSave="1" calcCompleted="0" fullPrecision="1"/>'
    if re.search(r"<calcPr\b[^>]*/>", xml):
        xml = re.sub(r"<calcPr\b[^>]*/>", replacement, xml, count=1)
    else:
        xml = xml.replace("</workbook>", f"{replacement}</workbook>")
    return xml.encode("utf-8")


def _remove_calc_chain_relationship(relationships_xml: bytes) -> bytes:
    xml = relationships_xml.decode("utf-8")
    pattern = re.compile(rf'<Relationship\b[^>]*Type="{re.escape(CALC_CHAIN_REL_TYPE)}"[^>]*/>')
    return pattern.sub("", xml).encode("utf-8")


def _remove_calc_chain_content_type(content_types_xml: bytes) -> bytes:
    xml = content_types_xml.decode("utf-8")
    pattern = re.compile(r'<Override\b[^>]*PartName="/xl/calcChain.xml"[^>]*/>')
    return pattern.sub("", xml).encode("utf-8")


def build_ranking_excel(db: Session, template_path: str | Path | None = None):
    template = Path(template_path) if template_path else find_latest_ranking_workbook()
    if not template or not template.is_file():
        raise ValueError("未找到排位 Excel 模板")

    preview = preview_ranking_workbook(db, template)
    ranking_payload = get_rankings(db)
    output = io.BytesIO()
    with ZipFile(template, "r") as source, ZipFile(output, "w", compression=ZIP_DEFLATED) as target:
        sheet_path = _worksheet_archive_path(source, preview["sheet"])
        for item in source.infolist():
            if item.filename == "xl/calcChain.xml":
                continue
            data = source.read(item.filename)
            if item.filename == sheet_path:
                data = _patch_ranking_sheet(data, ranking_payload.rows)
            elif item.filename == "xl/workbook.xml":
                data = _mark_workbook_for_recalculation(data)
            elif item.filename == "xl/_rels/workbook.xml.rels":
                data = _remove_calc_chain_relationship(data)
            elif item.filename == "[Content_Types].xml":
                data = _remove_calc_chain_content_type(data)
            target.writestr(item, data)

    output.seek(0)
    filename = f"HEIGO_ranking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return output, filename
