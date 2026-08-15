from __future__ import annotations

from pathlib import Path


def decode_log_bytes(data: bytes) -> str:
    """Decode collector logs written by either modern UTF-8 or Windows PowerShell.

    Windows PowerShell 5.1 can emit UTF-16 text through pipeline/file cmdlets. GEXY
    collector logs have existed in both UTF-8 and UTF-16 forms, so research readers
    must normalize encoding without changing the source file.
    """
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")

    sample = data[:512]
    if b"\x00" in sample:
        for encoding in ("utf-16-le", "utf-16-be"):
            try:
                text = data.decode(encoding)
            except UnicodeDecodeError:
                continue
            if "{" in text or "GEXY" in text:
                return text

    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass

    for encoding in ("utf-16-le", "utf-16-be"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    return data.decode("utf-8", errors="replace")


def read_log_text(path: str | Path) -> str:
    return decode_log_bytes(Path(path).read_bytes())
