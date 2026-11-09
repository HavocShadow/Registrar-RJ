"""Extract a site's system shortname from HTML content."""

import json
import re
import urllib.parse
from typing import Optional


def extract_shortname(html_content: str) -> Optional[str]:
    """Extract systemShortName from app settings or relevant script content."""
    if not html_content:
        return None

    try:
        shortname = _extract_from_appsetting(html_content)
        if shortname:
            return shortname

        shortname = _extract_by_regex(html_content)
        if shortname:
            return shortname

        return _extract_from_all_scripts(html_content)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _extract_from_appsetting(html_content: str) -> Optional[str]:
    script_re = re.compile(
        r'<script[^>]*\bid\s*=\s*["\']appSetting["\'][^>]*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    match = script_re.search(html_content)
    if not match:
        return None

    decoded = urllib.parse.unquote(match.group(1).strip())
    json_match = re.search(r"(\{.*\})", decoded, re.DOTALL)
    if not json_match:
        return None

    try:
        data = json.loads(json_match.group(1))
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    for key, value in data.items():
        if isinstance(key, str) and key.lower() == "systemshortname" and value:
            return str(value)

    for key in ("systemShortName", "systemshortname", "shortName", "shortname"):
        value = data.get(key)
        if value:
            return str(value)

    return None


def _extract_by_regex(html_content: str) -> Optional[str]:
    patterns = (
        r'"systemShortName"\s*:\s*"([^"]+)"',
        r'%22systemShortName%22%3A%22([^%]+)%22',
        r'systemShortName["\']?\s*:\s*["\']([^"\']+)["\']',
        r'shortname["\']?\s*:\s*["\']([^"\']+)["\']',
        r'shortName["\']?\s*:\s*["\']([^"\']+)["\']',
        r'"shortName":"([^"]+)"',
        r"shortName\\\":\\\"([^\\]+)\\\"",
        r'systemShortName\\\":\\\"([^\\]+)\\\"',
    )

    for pattern in patterns:
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def _extract_from_all_scripts(html_content: str) -> Optional[str]:
    script_pattern = re.compile(
        r"<script[^>]*>(.*?)</script>",
        re.IGNORECASE | re.DOTALL,
    )

    for script_content in script_pattern.findall(html_content):
        match = re.search(
            r'systemShortName\s*[:=]\s*["\']([^"\']+)["\']',
            script_content,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)

    return None
