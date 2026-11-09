import re
from typing import Optional


_LEVEL_RE = re.compile(r"\b(INFO|WARNING|ERROR|CRITICAL)\b")
_CONTEXT_ACCOUNT_RE = re.compile(r"\[account=(?P<account>[^\]]+)\]")
_ACCOUNT_PATTERNS = (
    re.compile(
        r"\b(?:Login ditolak|Login gagal) untuk akun\s+(?P<account>[^\s,;:]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bLogin request failed for account\s+(?P<account>[^\s,;:]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bAccount row\s+\d+\s+\((?P<account>[^)]+)\)\s+failed\b",
        re.IGNORECASE,
    ),
)
_TERMINAL_FAILURE_PATTERNS = (
    re.compile(r"\bAccount row \d+(?:\s+\([^)]+\))?\s+failed\b", re.IGNORECASE),
    re.compile(
        r"\bAccount row \d+\s+has no game balance after retry\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bLogin gagal untuk akun\s+\S+\s+setelah\s+\d+\s+percobaan\b",
        re.IGNORECASE,
    ),
)
_TRANSIENT_SPIN_REJECTION = re.compile(
    r"\bGame spin response indicates a rejected action\b", re.IGNORECASE
)


def extract_account_id(line: str) -> Optional[str]:
    context_match = _CONTEXT_ACCOUNT_RE.search(line)
    if context_match:
        account_id = context_match.group("account").strip()
        return account_id if account_id and account_id != "-" else None

    for pattern in _ACCOUNT_PATTERNS:
        match = pattern.search(line)
        if match:
            account_id = match.group("account").strip()
            return account_id or None

    return None


def is_transient_spin_rejection(line: str, source: str) -> bool:
    """Identify a retry-level warning that must not count as a failed account."""
    return (
        source in {"888.py", "mr2.py"}
        and "WARNING" in line
        and _TRANSIENT_SPIN_REJECTION.search(line) is not None
    )


def extract_error_record(line: str, source: str) -> Optional[dict]:
    """Return source, status, level, account ID, and original text."""
    level_match = _LEVEL_RE.search(line)
    if not level_match or level_match.group(1) not in {"WARNING", "ERROR", "CRITICAL"}:
        return None

    level = level_match.group(1)
    account_id = extract_account_id(line)
    if not account_id:
        return None

    status = None
    if source == "auto_wd.py":
        status_match = re.search(
            r"withdrawal verification status:\s*(VERIFICATION FAILED|PENDING|FAILED)\b",
            line,
            re.IGNORECASE,
        )
        if status_match:
            status = status_match.group(1).upper()

    if source in {"888.py", "mr2.py"}:
        if not any(pattern.search(line) for pattern in _TERMINAL_FAILURE_PATTERNS):
            return None
    elif level == "WARNING":
        lowered_line = line.lower()
        if "login ditolak" in lowered_line and "pada percobaan" in lowered_line:
            return None
        if status is None and not re.search(
            r"\b(fail(?:ed)?|gagal|ditolak|unavailable|no game balance|"
            r"exception|timeout|request error|rejected)\b|http [45]\d{2}",
            lowered_line,
        ):
            return None

    return {
        "account_id": account_id,
        "source": source,
        "level": level,
        "status": status or ("FAILED" if source in {"auto_wd.py", "888.py", "mr2.py"} else "ERROR"),
        "message": line.strip(),
    }


def extract_error_account_id(line: str) -> Optional[str]:
    """Return an account ID only for warning/error log records."""
    record = extract_error_record(line, "unknown")
    return record["account_id"] if record else None
