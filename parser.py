"""
parser.py — Robust shortname extraction for appSetting HTML pages.

Perbaikan utama dibanding versi lama:
1. Pattern `%22systemShortName%22...` dicoba LEBIH DULU (match langsung
   di HTML mentah, tidak butuh JSON parse utuh).
2. JSON decode pakai `JSONDecoder().raw_decode()` — ambil objek JSON VALID
   pertama, bukan greedy `{.*}` yang bisa gagal di HTML 690KB.
3. Toleran terhadap beberapa varian decode (as-is, html-unescape, url-unescape).
4. Regex `</script\s*>` toleran spasi.
5. Fallback scan semua `<script>` kalau appSetting tidak ketemu.
"""

import html as html_module
import json
import re
import urllib.parse
from typing import Optional

# ============ CONSTANTS ============

_APP_SETTING_RE = re.compile(
    r'<script\b[^>]*?\bid\s*=\s*["\']appSetting["\'][^>]*?>(.*?)</script\s*>',
    re.IGNORECASE | re.DOTALL,
)

_SCRIPT_TAG_RE = re.compile(
    r"<script\b[^>]*>(.*?)</script\s*>",
    re.IGNORECASE | re.DOTALL,
)

_SHORTNAME_KEYS_LOWER = frozenset(("systemshortname", "shortname", "short_name"))

# Pattern langsung di HTML mentah (urutan = prioritas)
_DIRECT_PATTERNS = (
    # URL-encoded dengan %3A
    r'%22systemShortName%22\s*%3A\s*%22([^%"]+)%22',
    # URL-encoded dengan literal ':' (seperti sample user)
    r'%22systemShortName%22\s*:\s*%22([^%"]+)%22',
    # JSON plain
    r'"systemShortName"\s*:\s*"([^"\\]+)"',
    # JSON double-escaped (\\"...\\")
    r'\\"systemShortName\\"\s*:\s*\\"([^"\\]+)\\"',
    # Fallback longgar
    r'systemShortName["\']?\s*[:=]\s*["\']([^"\']+)["\']',
)


# ============ HELPERS ============


def _decode_variants(raw: str):
    """Yield beberapa varian decode dari raw string tanpa merusak aslinya."""
    if not raw:
        return
    yield raw

    try:
        unescaped = html_module.unescape(raw)
        if unescaped != raw:
            yield unescaped
    except Exception:
        pass

    try:
        unquoted = urllib.parse.unquote(raw)
        if unquoted != raw:
            yield unquoted
            try:
                both = html_module.unescape(unquoted)
                if both != unquoted:
                    yield both
            except Exception:
                pass
    except Exception:
        pass


def _try_loads(s: str):
    """Parse JSON toleran terhadap prefix/suffix sampah."""
    if not s:
        return None
    s = s.strip()
    if not s:
        return None

    # Coba langsung
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass

    # Fallback: cari '{' pertama, pakai raw_decode (tidak greedy)
    start = s.find("{")
    if start < 0:
        return None

    decoder = json.JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(s, start)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _find_shortname(obj) -> Optional[str]:
    """Cari shortname di dict secara case-insensitive."""
    if not isinstance(obj, dict):
        return None
    for key, value in obj.items():
        if isinstance(key, str) and key.lower() in _SHORTNAME_KEYS_LOWER and value:
            return str(value)
    return None


# ============ MAIN API ============


def extract_shortname(html_content: str) -> Optional[str]:
    """Extract systemShortName dari HTML. Return str atau None."""
    if not html_content:
        return None

    # ---- Fast path: regex langsung di HTML mentah ----
    for pattern in _DIRECT_PATTERNS:
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                return value

    # ---- Method 1: <script id="appSetting"> ----
    match = _APP_SETTING_RE.search(html_content)
    if match:
        raw = match.group(1).strip()
        for candidate in _decode_variants(raw):
            obj = _try_loads(candidate)
            sn = _find_shortname(obj)
            if sn:
                return sn

    # ---- Method 3: scan tiap <script> ----
    for script_body in _SCRIPT_TAG_RE.findall(html_content):
        if "shortname" not in script_body.lower():
            continue
        for candidate in _decode_variants(script_body):
            obj = _try_loads(candidate)
            sn = _find_shortname(obj)
            if sn:
                return sn

    return None
