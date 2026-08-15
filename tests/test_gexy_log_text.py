from packages.gexy.log_text import decode_log_bytes


def test_decode_utf8_collector_log():
    text = '{"prediction":{"status":"ok"}}\n'
    assert decode_log_bytes(text.encode("utf-8")) == text


def test_decode_utf16_collector_log():
    text = '{"prediction":{"status":"ok"}}\n'
    assert decode_log_bytes(text.encode("utf-16")) == text


def test_decode_utf16le_without_bom():
    text = '[2026-08-14T09:30:00-07:00] GEXY session collector starting\n'
    assert decode_log_bytes(text.encode("utf-16-le")) == text
