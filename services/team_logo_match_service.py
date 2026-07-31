from __future__ import annotations

from datetime import datetime, timedelta
from difflib import SequenceMatcher
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import io
import json
import os
import re
import xml.etree.ElementTree as ET

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from models import Team, TeamLogoSource
from schemas_write import TeamLogoMatchApplyRequest
from services.admin_common import LogWriter, require_admin
from services.team_logo_service import (
    ALLOWED_TEAM_LOGO_TYPES,
    MAX_TEAM_LOGO_BYTES,
    MAX_TEAM_LOGO_DIMENSION,
    MIN_TEAM_LOGO_DIMENSION,
    TEAM_LOGO_OUTPUT_SIZE,
    TEAM_LOGO_PUBLIC_PREFIX,
    TEAM_LOGO_ROOT,
    _delete_previous_team_logo,
)


FCLOGO_PROVIDER = "fclogo"
FCLOGO_SITE_ORIGIN = "https://fclogo.top"
FCLOGO_ASSET_ORIGIN = "https://assets.fclogo.top"
FCLOGO_PREVIEW_ORIGIN = "https://cdn.sanity.io/images/11hmdf08/production/"
FCLOGO_SEARCH_URL = "https://tvtxqfxchbburasicdax.supabase.co/rest/v1/rpc/search_logos"
FCLOGO_PUBLIC_KEY = os.environ.get(
    "FCLOGO_SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2dHhxZnhjaGJidXJhc2ljZGF4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI4MDM4MzcsImV4cCI6MjA2ODM3OTgzN30.4ToZiHcgTvPGfQxVkbnERyX4A6Nm8gSveitkWg3qxkM",
).strip()
MAX_SEARCH_TERM_LENGTH = 80
MAX_SVG_BYTES = 5 * 1024 * 1024
SEARCH_CACHE_TTL = timedelta(minutes=10)
SEARCH_CACHE: dict[str, tuple[datetime, list[dict[str, Any]]]] = {}
VALID_SLUG_RE = re.compile(r"^/[A-Za-z0-9][A-Za-z0-9._~%+\-/]*$")
VALID_ASSET_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._~%+\-]*$")
EXTERNAL_REFERENCE_RE = re.compile(r"(?:https?:|javascript:|file:|//)", re.IGNORECASE)
EXTERNAL_CSS_URL_RE = re.compile(r"url\(\s*['\"]?(?!#)", re.IGNORECASE)
FORBIDDEN_TAGS = {"script", "foreignobject", "iframe", "object", "embed", "audio", "video"}
NAME_ALIASES = {
    "r madrid": "real madrid",
    "a madrid": "atletico madrid",
    "man utd": "manchester united",
    "man ufc": "manchester united",
    "bayer 04": "bayer leverkusen",
    "sporting cp": "sporting clube de portugal",
}


def _normalize_name(value: str) -> str:
    normalized = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", str(value or "").casefold()).strip()
    return NAME_ALIASES.get(normalized, normalized)


def _match_score(query: str, candidate: dict[str, Any]) -> float:
    normalized_query = _normalize_name(query)
    names = [
        candidate.get("subject_short_name"),
        candidate.get("subject_name"),
        candidate.get("subject_local_name"),
        candidate.get("subject_short_name_zh"),
        candidate.get("subject_name_zh"),
    ]
    scores: list[float] = []
    for raw_name in names:
        name = _normalize_name(str(raw_name or ""))
        if not name:
            continue
        if name == normalized_query:
            scores.append(100.0)
        elif normalized_query and (normalized_query in name or name in normalized_query):
            scores.append(84.0)
        else:
            scores.append(SequenceMatcher(None, normalized_query, name).ratio() * 82.0)
    score = max(scores, default=0.0)
    variant = str(candidate.get("style_name") or "").casefold()
    if variant == "color":
        score += 4.0
    elif variant in {"mono", "flat"}:
        score -= 3.0
    return round(min(score, 100.0), 1)


def _fetch_json(request: Request, *, timeout: float = 8.0) -> Any:
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="FCLOGO 搜索服务暂时不可用，请稍后重试") from exc


def _fetch_bytes(url: str, *, timeout: float = 12.0, max_bytes: int = MAX_SVG_BYTES) -> bytes:
    request = Request(url, headers={"User-Agent": "HEIGO-TeamLogoMatcher/1.0", "Accept": "image/svg+xml"})
    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = str(response.headers.get("Content-Type") or "").lower()
            if "svg" not in content_type and "xml" not in content_type:
                raise HTTPException(status_code=502, detail="FCLOGO 返回的文件不是 SVG")
            content = response.read(max_bytes + 1)
    except HTTPException:
        raise
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"FCLOGO 队徽下载失败（上游 {exc.code}）") from exc
    except (URLError, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail="FCLOGO 队徽下载失败，请稍后重试") from exc
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="FCLOGO 队徽文件超过 5MB 安全上限")
    return content


def _validated_slug(slug: str) -> str:
    value = str(slug or "").strip()
    if not VALID_SLUG_RE.fullmatch(value) or ".." in value or value.endswith("/"):
        raise HTTPException(status_code=400, detail="FCLOGO 候选标识无效")
    return value


def _asset_url_for_slug(slug: str) -> str:
    safe_slug = _validated_slug(slug)
    filename = safe_slug.rsplit("/", 1)[-1]
    return f"{FCLOGO_ASSET_ORIGIN}/svg/{quote(filename, safe='-._~%')}.svg"


class _OpenGraphImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.image_url: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "meta" or self.image_url:
            return
        values = {str(key).casefold(): str(value or "") for key, value in attrs}
        if values.get("property", "").casefold() == "og:image":
            self.image_url = values.get("content") or None


def _asset_url_from_detail_html(html: str) -> str | None:
    parser = _OpenGraphImageParser()
    parser.feed(html)
    prefix = f"{FCLOGO_ASSET_ORIGIN}/png/"
    if not parser.image_url or not parser.image_url.startswith(prefix) or not parser.image_url.endswith(".png"):
        return None
    filename = parser.image_url.removeprefix(prefix).removesuffix(".png")
    if not VALID_ASSET_FILENAME_RE.fullmatch(filename):
        return None
    return f"{FCLOGO_ASSET_ORIGIN}/svg/{quote(filename, safe='-._~%')}.svg"


def _resolve_asset_url(slug: str) -> str:
    safe_slug = _validated_slug(slug)
    detail_url = f"{FCLOGO_SITE_ORIGIN}{safe_slug}"
    request = Request(detail_url, headers={"User-Agent": "HEIGO-TeamLogoMatcher/1.0", "Accept": "text/html"})
    try:
        with urlopen(request, timeout=10.0) as response:
            html = response.read(1024 * 1024 + 1)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail="FCLOGO 候选详情读取失败，请稍后重试") from exc
    if len(html) > 1024 * 1024:
        raise HTTPException(status_code=502, detail="FCLOGO 候选详情超过安全上限")
    resolved = _asset_url_from_detail_html(html.decode("utf-8", "ignore"))
    if not resolved:
        raise HTTPException(status_code=502, detail="FCLOGO 候选缺少可验证的 SVG 文件信息")
    return resolved


def _safe_preview_url(value: Any) -> str | None:
    url = str(value or "").strip()
    return url if url.startswith(FCLOGO_PREVIEW_ORIGIN) else None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _contains_external_reference(value: str) -> bool:
    return bool(
        EXTERNAL_REFERENCE_RE.search(value)
        or EXTERNAL_CSS_URL_RE.search(value)
        or "data:" in value.casefold()
        or "@import" in value.casefold()
    )


def sanitize_svg(content: bytes) -> bytes:
    lowered = content[:4096].lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise HTTPException(status_code=400, detail="SVG 含有不允许的文档声明")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise HTTPException(status_code=400, detail="SVG 文件结构无效") from exc
    if _local_name(root.tag) != "svg":
        raise HTTPException(status_code=400, detail="下载文件不是有效 SVG")
    if not (root.get("viewBox") or (root.get("width") and root.get("height"))):
        raise HTTPException(status_code=400, detail="SVG 缺少有效尺寸信息")

    def clean(parent: ET.Element) -> None:
        for child in list(parent):
            if _local_name(child.tag) in FORBIDDEN_TAGS:
                parent.remove(child)
                continue
            clean(child)
        for attribute, raw_value in list(parent.attrib.items()):
            name = _local_name(attribute)
            value = str(raw_value or "").strip()
            if name.startswith("on"):
                del parent.attrib[attribute]
                continue
            if name in {"href", "src"} and value and not value.startswith("#"):
                del parent.attrib[attribute]
                continue
            if _contains_external_reference(value):
                del parent.attrib[attribute]
        if _local_name(parent.tag) == "style" and _contains_external_reference(parent.text or ""):
            parent.text = ""

    clean(root)
    sanitized = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    if len(sanitized) > MAX_SVG_BYTES:
        raise HTTPException(status_code=400, detail="清洗后的 SVG 文件仍超过安全上限")
    return sanitized


def _render_webp(svg: bytes, target: Path) -> None:
    try:
        import cairosvg
        from PIL import Image

        png = cairosvg.svg2png(bytestring=svg, output_width=1024, output_height=1024)
        image = Image.open(io.BytesIO(png)).convert("RGBA")
        bbox = image.getchannel("A").getbbox()
        if bbox:
            image = image.crop(bbox)
        image.thumbnail((TEAM_LOGO_OUTPUT_SIZE, TEAM_LOGO_OUTPUT_SIZE))
        canvas = Image.new("RGBA", (TEAM_LOGO_OUTPUT_SIZE, TEAM_LOGO_OUTPUT_SIZE), (255, 255, 255, 0))
        canvas.alpha_composite(image, ((TEAM_LOGO_OUTPUT_SIZE - image.width) // 2, (TEAM_LOGO_OUTPUT_SIZE - image.height) // 2))
        canvas.save(target, format="WEBP", quality=92, method=6)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail="SVG 无法安全转换为网站队徽") from exc


def get_match_overview(db: Session, admin: str | None) -> dict[str, Any]:
    require_admin(admin)
    latest_by_team: dict[int, TeamLogoSource] = {}
    for item in db.query(TeamLogoSource).order_by(TeamLogoSource.imported_at.desc(), TeamLogoSource.id.desc()).all():
        latest_by_team.setdefault(item.team_id, item)
    teams = db.query(Team).filter(Team.level.in_(("超级", "甲级", "乙级"))).order_by(Team.level, Team.name).all()
    return {
        "provider": {"name": "FCLOGO", "site_url": FCLOGO_SITE_ORIGIN, "authorized": True},
        "teams": [
            {
                "id": team.id,
                "name": team.name,
                "level": team.level,
                "logo_path": team.logo_path,
                "latest_source": _source_payload(latest_by_team.get(team.id)),
            }
            for team in teams
        ],
    }


def _source_payload(source: TeamLogoSource | None) -> dict[str, Any] | None:
    if not source:
        return None
    return {
        "provider": source.provider,
        "source_url": source.source_url,
        "source_name": source.source_name,
        "source_version": source.source_version,
        "source_variant": source.source_variant,
        "matched_query": source.matched_query,
        "matched_score": source.matched_score,
        "imported_by": source.imported_by,
        "imported_at": source.imported_at.isoformat() if source.imported_at else None,
    }


def search_fclogo(db: Session, admin: str | None, team_id: int, query: str) -> dict[str, Any]:
    require_admin(admin)
    team = db.query(Team).filter(Team.id == team_id, Team.level.in_(("超级", "甲级", "乙级"))).first()
    if not team:
        raise HTTPException(status_code=404, detail="联赛球队不存在")
    term = str(query or "").strip()
    if not term:
        raise HTTPException(status_code=400, detail="请输入球队搜索词")
    if len(term) > MAX_SEARCH_TERM_LENGTH:
        raise HTTPException(status_code=400, detail="球队搜索词不能超过 80 个字符")

    cache_key = term.casefold()
    now = datetime.now()
    for key, (created_at, _items) in list(SEARCH_CACHE.items()):
        if now - created_at > SEARCH_CACHE_TTL:
            SEARCH_CACHE.pop(key, None)
    if len(SEARCH_CACHE) > 128:
        for key in sorted(SEARCH_CACHE, key=lambda item: SEARCH_CACHE[item][0])[:-128]:
            SEARCH_CACHE.pop(key, None)
    cached = SEARCH_CACHE.get(cache_key)
    if cached and now - cached[0] <= SEARCH_CACHE_TTL:
        raw_items = cached[1]
    else:
        body = json.dumps({"search_term": term, "language_code": "en"}).encode("utf-8")
        request = Request(
            FCLOGO_SEARCH_URL,
            data=body,
            method="POST",
            headers={
                "apikey": FCLOGO_PUBLIC_KEY,
                "Authorization": f"Bearer {FCLOGO_PUBLIC_KEY}",
                "Content-Type": "application/json",
                "Origin": FCLOGO_SITE_ORIGIN,
                "User-Agent": "HEIGO-TeamLogoMatcher/1.0",
            },
        )
        payload = _fetch_json(request)
        raw_items = payload if isinstance(payload, list) else []
        SEARCH_CACHE[cache_key] = (now, raw_items)

    candidates: list[dict[str, Any]] = []
    for item in raw_items[:24]:
        if not isinstance(item, dict):
            continue
        try:
            slug = _validated_slug(str(item.get("slug") or ""))
        except HTTPException:
            continue
        score = _match_score(term, item)
        candidates.append(
            {
                "slug": slug,
                "detail_url": f"{FCLOGO_SITE_ORIGIN}{slug}",
                "preview_url": _safe_preview_url(item.get("preview_image_url")),
                "name": item.get("subject_short_name") or item.get("subject_name"),
                "full_name": item.get("subject_name"),
                "local_name": item.get("subject_local_name"),
                "name_zh": item.get("subject_short_name_zh") or item.get("subject_name_zh"),
                "version": str(item.get("version") or ""),
                "variant": item.get("style_name") or "Unknown",
                "variant_zh": item.get("style_name_zh") or "",
                "confidence": score,
            }
        )
    candidates.sort(key=lambda item: (-float(item["confidence"]), item["variant"] != "Color", item["name"] or ""))
    return {"team": {"id": team.id, "name": team.name, "logo_path": team.logo_path}, "query": term, "candidates": candidates[:12]}


def apply_fclogo_candidate(
    db: Session,
    admin: str | None,
    request: TeamLogoMatchApplyRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    if not request.confirmed:
        raise HTTPException(status_code=400, detail="必须人工确认后才能替换队徽")
    team = db.query(Team).filter(Team.id == request.team_id, Team.level.in_(("超级", "甲级", "乙级"))).first()
    if not team:
        raise HTTPException(status_code=404, detail="联赛球队不存在")
    slug = _validated_slug(request.slug)
    asset_url = _resolve_asset_url(slug)
    sanitized = sanitize_svg(_fetch_bytes(asset_url))
    digest = sha256(sanitized).hexdigest()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    TEAM_LOGO_ROOT.mkdir(parents=True, exist_ok=True)
    svg_filename = f"{team.id}_{timestamp}.svg"
    webp_filename = f"{team.id}_{timestamp}.webp"
    svg_target = TEAM_LOGO_ROOT / svg_filename
    webp_target = TEAM_LOGO_ROOT / webp_filename
    previous_logo_path = team.logo_path
    previous_logo_is_tracked = bool(
        previous_logo_path
        and db.query(TeamLogoSource.id).filter(TeamLogoSource.team_id == team.id, TeamLogoSource.webp_path == previous_logo_path).first()
    )
    try:
        svg_target.write_bytes(sanitized)
        _render_webp(sanitized, webp_target)
        webp_path = f"{TEAM_LOGO_PUBLIC_PREFIX}{webp_filename}"
        source = TeamLogoSource(
            team_id=team.id,
            provider=FCLOGO_PROVIDER,
            source_url=f"{FCLOGO_SITE_ORIGIN}{slug}",
            source_name=str(request.source_name or "").strip()[:255],
            source_version=str(request.source_version or "").strip()[:50] or None,
            source_variant=str(request.source_variant or "").strip()[:50] or None,
            svg_path=f"{TEAM_LOGO_PUBLIC_PREFIX}{svg_filename}",
            webp_path=webp_path,
            sha256=digest,
            matched_query=str(request.matched_query or "").strip()[:80],
            matched_score=request.matched_score,
            imported_by=operator,
            imported_at=datetime.now(),
        )
        db.add(source)
        team.logo_path = webp_path
        db.commit()
        db.refresh(source)
    except HTTPException:
        db.rollback()
        svg_target.unlink(missing_ok=True)
        webp_target.unlink(missing_ok=True)
        raise
    except Exception as exc:
        db.rollback()
        svg_target.unlink(missing_ok=True)
        webp_target.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="队徽保存失败，原队徽未改变") from exc

    if not previous_logo_is_tracked:
        _delete_previous_team_logo(team.id, previous_logo_path, keep_path=team.logo_path)
    write_to_log("球队队徽匹配", f"{team.id} / {team.name} <- FCLOGO {slug}", operator)
    return {
        "success": True,
        "message": f"{team.name} 队徽已更新",
        "team_id": team.id,
        "logo_path": team.logo_path,
        "source": _source_payload(source),
    }


def upload_local_team_logo(
    db: Session,
    admin: str | None,
    team_id: int,
    logo: UploadFile,
    write_to_log: LogWriter,
    *,
    confirmed: bool = False,
) -> dict[str, Any]:
    operator = require_admin(admin)
    if not confirmed:
        raise HTTPException(status_code=400, detail="必须人工确认后才能替换队徽")
    team = db.query(Team).filter(Team.id == team_id, Team.level.in_(("超级", "甲级", "乙级"))).first()
    if not team:
        raise HTTPException(status_code=404, detail="联赛球队不存在")
    original_name = Path(str(logo.filename or "team-logo")).name[:255]
    content_type = str(logo.content_type or "").casefold()
    is_svg = content_type in {"image/svg+xml", "application/svg+xml"} or original_name.casefold().endswith(".svg")
    byte_limit = MAX_SVG_BYTES if is_svg else MAX_TEAM_LOGO_BYTES
    content = logo.file.read(byte_limit + 1)
    if len(content) > byte_limit:
        limit_label = "5MB" if is_svg else "2MB"
        raise HTTPException(status_code=400, detail=f"本地队徽不能超过 {limit_label}")
    if not content:
        raise HTTPException(status_code=400, detail="上传的队徽文件为空")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    TEAM_LOGO_ROOT.mkdir(parents=True, exist_ok=True)
    webp_filename = f"{team.id}_{timestamp}.webp"
    webp_target = TEAM_LOGO_ROOT / webp_filename
    svg_target: Path | None = None
    digest_content = content
    source_variant = "SVG" if is_svg else content_type.upper().removeprefix("IMAGE/")
    try:
        if is_svg:
            sanitized = sanitize_svg(content)
            digest_content = sanitized
            svg_filename = f"{team.id}_{timestamp}.svg"
            svg_target = TEAM_LOGO_ROOT / svg_filename
            svg_target.write_bytes(sanitized)
            _render_webp(sanitized, webp_target)
        else:
            if content_type not in ALLOWED_TEAM_LOGO_TYPES:
                raise HTTPException(status_code=400, detail="本地队徽支持 JPG、PNG、WEBP 或 SVG")
            try:
                from PIL import Image, ImageOps

                image = Image.open(io.BytesIO(content))
                image.verify()
                image = Image.open(io.BytesIO(content))
                image = ImageOps.exif_transpose(image).convert("RGBA")
            except Exception as exc:
                raise HTTPException(status_code=400, detail="队徽文件无法识别") from exc
            width, height = image.size
            if min(width, height) < MIN_TEAM_LOGO_DIMENSION:
                raise HTTPException(status_code=400, detail=f"队徽尺寸至少 {MIN_TEAM_LOGO_DIMENSION}x{MIN_TEAM_LOGO_DIMENSION}")
            if max(width, height) > MAX_TEAM_LOGO_DIMENSION:
                raise HTTPException(status_code=400, detail=f"队徽最长边不能超过 {MAX_TEAM_LOGO_DIMENSION}px")
            bbox = image.getchannel("A").getbbox()
            if bbox:
                image = image.crop(bbox)
            image.thumbnail((TEAM_LOGO_OUTPUT_SIZE, TEAM_LOGO_OUTPUT_SIZE))
            canvas = Image.new("RGBA", (TEAM_LOGO_OUTPUT_SIZE, TEAM_LOGO_OUTPUT_SIZE), (255, 255, 255, 0))
            canvas.alpha_composite(image, ((TEAM_LOGO_OUTPUT_SIZE - image.width) // 2, (TEAM_LOGO_OUTPUT_SIZE - image.height) // 2))
            canvas.save(webp_target, format="WEBP", quality=92, method=6)

        previous_logo_path = team.logo_path
        previous_logo_is_tracked = bool(
            previous_logo_path
            and db.query(TeamLogoSource.id).filter(TeamLogoSource.team_id == team.id, TeamLogoSource.webp_path == previous_logo_path).first()
        )
        webp_path = f"{TEAM_LOGO_PUBLIC_PREFIX}{webp_filename}"
        source = TeamLogoSource(
            team_id=team.id,
            provider="local_upload",
            source_url=f"local-upload://{quote(original_name)}",
            source_name=original_name,
            source_version=None,
            source_variant=source_variant,
            svg_path=f"{TEAM_LOGO_PUBLIC_PREFIX}{svg_target.name}" if svg_target else webp_path,
            webp_path=webp_path,
            sha256=sha256(digest_content).hexdigest(),
            matched_query=None,
            matched_score=None,
            imported_by=operator,
            imported_at=datetime.now(),
        )
        db.add(source)
        team.logo_path = webp_path
        db.commit()
        db.refresh(source)
    except HTTPException:
        db.rollback()
        if svg_target:
            svg_target.unlink(missing_ok=True)
        webp_target.unlink(missing_ok=True)
        raise
    except Exception as exc:
        db.rollback()
        if svg_target:
            svg_target.unlink(missing_ok=True)
        webp_target.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="队徽保存失败，原队徽未改变") from exc

    if not previous_logo_is_tracked:
        _delete_previous_team_logo(team.id, previous_logo_path, keep_path=team.logo_path)
    write_to_log("球队队徽上传", f"{team.id} / {team.name} <- {original_name}", operator)
    return {
        "success": True,
        "message": f"{team.name} 本地队徽已上传",
        "team_id": team.id,
        "logo_path": team.logo_path,
        "source": _source_payload(source),
    }
