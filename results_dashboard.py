#!/usr/bin/env python3
"""Read-only Textual viewer for previously saved RegisV8 results."""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Static


DEFAULT_RESULTS = (
    Path(__file__).resolve().parents[1] / "output_regis" / "regis_results.json"
)
KNOWN_STATUSES = {"success", "failed", "pending", "in_progress"}


def load_results(path: Path) -> list[dict[str, Any]]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Tidak dapat membaca file hasil: {exc}") from exc

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"JSON tidak valid pada baris {exc.lineno}, kolom {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(data, list):
        raise RuntimeError("Format hasil harus berupa JSON array.")

    valid_results = []
    invalid_rows = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            invalid_rows.append(str(index))
            continue
        valid_results.append(item)

    if invalid_rows:
        raise RuntimeError(
            "Format hasil rusak: setiap item harus berupa object. "
            f"Item bermasalah: {', '.join(invalid_rows[:10])}"
        )
    return valid_results


def normalize_status(value: Any) -> str:
    status = str(value or "unknown").strip().lower()
    return status if status in KNOWN_STATUSES else "unknown"


def format_duration(value: Any) -> str:
    try:
        duration = float(value or 0)
    except (TypeError, ValueError):
        return "invalid"
    if duration < 0:
        return "invalid"
    return f"{duration:.2f}s"


class ResultsDashboard(App[None]):
    TITLE = "RegisV8 — Saved Results (Read Only)"
    CSS = """
    $background: #000000;
    $surface: #000000;
    $panel: #000000;
    $boost: #151515;

    Screen {
        layout: vertical;
        background: #000000;
    }
    #summary {
        height: 3;
        padding: 1 2;
        background: #000000;
    }
    DataTable {
        height: 1fr;
        background: #000000;
        scrollbar-background: #000000;
        scrollbar-color: #555555;
        scrollbar-color-hover: #888888;
        scrollbar-color-active: #aaaaaa;
    }
    DataTable > .datatable--header,
    DataTable > .datatable--header-cursor,
    DataTable > .datatable--even-row,
    DataTable > .datatable--odd-row {
        background: #000000;
    }
    DataTable > .datatable--cursor {
        background: #202020;
    }
    DataTable > .datatable--header {
        color: $warning;
        text-style: bold;
    }
    #message {
        height: 3;
        padding: 1 2;
    }
    """
    BINDINGS = [
        ("a", "show_all", "All"),
        ("s", "show_success", "Success"),
        ("f", "show_failed", "Failed"),
        ("r", "reload_results", "Reload"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, results_path: Path):
        super().__init__()
        self.results_path = results_path
        self.results: list[dict[str, Any]] = []
        self.filter_status = "all"
        self.last_error = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Loading saved results...", id="summary")
        yield Static("", id="message")
        yield DataTable(id="results-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        for title, key in (
            ("#", "id"),
            ("ACCOUNT", "account"),
            ("SITE", "site"),
            ("SHORTNAME", "shortname"),
            ("HTTP", "http"),
            ("STATUS", "status"),
            ("DETAIL", "detail"),
            ("TIME", "time"),
        ):
            table.add_column(title, key=key)
        self.reload_results()
        self.set_interval(2.0, self.reload_results)

    def action_reload_results(self) -> None:
        self.reload_results()

    def action_show_all(self) -> None:
        self.filter_status = "all"
        self.render_results()

    def action_show_success(self) -> None:
        self.filter_status = "success"
        self.render_results()

    def action_show_failed(self) -> None:
        self.filter_status = "failed"
        self.render_results()

    def reload_results(self) -> None:
        try:
            self.results = load_results(self.results_path)
            self.last_error = ""
        except RuntimeError as exc:
            self.results = []
            self.last_error = str(exc)
        self.render_results()

    def render_results(self) -> None:
        if not self.is_mounted:
            return

        table = self.query_one("#results-table", DataTable)
        table.clear()
        counts = Counter(normalize_status(row.get("status")) for row in self.results)
        visible = [
            row for row in self.results
            if self.filter_status == "all"
            or normalize_status(row.get("status")) == self.filter_status
        ]

        for position, row in enumerate(visible, start=1):
            status = normalize_status(row.get("status"))
            status_style = {
                "success": "bold green",
                "failed": "bold red",
                "pending": "bold yellow",
                "in_progress": "bold cyan",
                "unknown": "bold magenta",
            }[status]
            http_status = row.get("http_status_post")
            detail = row.get("error_message") or ""
            if not detail and status == "unknown":
                detail = f"Status tidak dikenal: {row.get('status')!r}"
            elif not detail and status == "failed":
                detail = "Hasil ditandai gagal; tidak ada error_message tersimpan."
            elif not detail:
                detail = str(row.get("response_body") or "")

            table.add_row(
                Text(str(row.get("mission_id", position)), style="bold blue"),
                Text(str(row.get("account") or "-"), style="white"),
                Text(str(row.get("site_url") or "-"), style="cyan"),
                Text(str(row.get("short_name") or "-"), style="bright_cyan"),
                Text(str(http_status if http_status is not None else "-")),
                Text(status.upper(), style=status_style),
                Text(detail or "-", style="red" if status in {"failed", "unknown"} else "white"),
                Text(format_duration(row.get("execution_time"))),
                key=str(position),
            )

        summary = Text()
        summary.append(f"File: {self.results_path}  ", style="dim")
        summary.append(f"Total: {len(self.results)}  ", style="bold")
        summary.append(f"Success: {counts['success']}  ", style="bold green")
        summary.append(f"Failed: {counts['failed']}  ", style="bold red")
        summary.append(
            f"Pending: {counts['pending'] + counts['in_progress']}  ",
            style="bold yellow",
        )
        summary.append(f"Unknown: {counts['unknown']}", style="bold magenta")
        self.query_one("#summary", Static).update(summary)

        if self.last_error:
            self.query_one("#message", Static).update(
                Text(f"ERROR: {self.last_error}", style="bold red")
            )
        else:
            self.query_one("#message", Static).update(
                Text(
                    f"Filter: {self.filter_status.upper()}  | "
                    "A=All  S=Success  F=Failed  R=Reload  | "
                    "Read-only: tidak ada request jaringan atau perubahan hasil.",
                    style="bold cyan",
                )
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only Textual viewer for saved RegisV8 results."
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=DEFAULT_RESULTS,
        help=f"Path file hasil JSON (default: {DEFAULT_RESULTS})",
    )
    args = parser.parse_args()
    ResultsDashboard(args.results.expanduser()).run()


if __name__ == "__main__":
    main()
