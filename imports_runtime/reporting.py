from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class DatasetSummary:
    source: str
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        self.errors.append(message)

@dataclass
class ImportReport:
    workbook_path: str
    attributes_csv_path: str
    dry_run: bool
    strict_mode: bool
    committed: bool = False
    fatal_error: str | None = None
    datasets: dict[str, DatasetSummary] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        if self.fatal_error:
            return True
        return any(summary.errors for summary in self.datasets.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "workbook_path": self.workbook_path,
            "attributes_csv_path": self.attributes_csv_path,
            "dry_run": self.dry_run,
            "strict_mode": self.strict_mode,
            "committed": self.committed,
            "fatal_error": self.fatal_error,
            "warnings": self.warnings,
            "datasets": {name: asdict(summary) for name, summary in self.datasets.items()},
        }

def dataset_summary(report: ImportReport, name: str, source: Path) -> DatasetSummary:
    summary = DatasetSummary(source=str(source))
    report.datasets[name] = summary
    return summary

def print_report(report: ImportReport) -> None:
    print("== HEIGO Import Report ==")
    print(f"workbook: {report.workbook_path}")
    print(f"attributes_csv: {report.attributes_csv_path}")
    print(f"dry_run: {report.dry_run}")
    print(f"strict_mode: {report.strict_mode}")
    print(f"committed: {report.committed}")
    if report.warnings:
        print("\nWarnings:")
        for warning in report.warnings:
            print(f"- {warning}")

    for dataset_name, summary in report.datasets.items():
        print(f"\n[{dataset_name}]")
        print(
            f"created={summary.created} updated={summary.updated} unchanged={summary.unchanged} skipped={summary.skipped}"
        )
        for warning in summary.warnings:
            print(f"- warning: {warning}")
        for error in summary.errors:
            print(f"- error: {error}")
        if summary.details.get("error_counts"):
            print(f"- validation_error_counts: {json.dumps(summary.details['error_counts'], ensure_ascii=False)}")
        if summary.details:
            print(f"- details: {json.dumps(summary.details, ensure_ascii=False)}")

    if report.fatal_error:
        print(f"\nFatal error: {report.fatal_error}")
