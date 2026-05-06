from image_to_text.core import clean_text, parse_defects, to_markdown


def test_clean_text_removes_artifacts() -> None:
    raw = "ABC-1\r\nDescription: bad | text ¬\r\n\r\n\r\nActual: fail"
    cleaned = clean_text(raw)
    assert "|" not in cleaned
    assert "¬" not in cleaned
    assert "\r" not in cleaned


def test_parse_defects_with_sections() -> None:
    text = """ABC-42
Summary: Login button is broken
Steps: 1) Open app
2) Click login
Actual: Crash
Expected: Should login
"""
    records = parse_defects(text, source_image="shot.png")
    assert len(records) == 1
    rec = records[0]
    assert rec["id"] == "ABC-42"
    assert rec["source_image"] == "shot.png"
    assert "Summary" in rec["sections"]
    assert "Steps To Reproduce" in rec["sections"]
    assert rec["full_text"].startswith("ABC-42")


def test_parse_defects_without_id_keeps_all_text() -> None:
    text = "Screenshot title\nDescription: some note\nline 2"
    records = parse_defects(text)
    assert len(records) == 1
    assert records[0]["id"] == "UNKNOWN"
    assert "Screenshot title" in records[0]["full_text"]


def test_to_markdown_formats_steps() -> None:
    records = [
        {
            "id": "ABC-7",
            "source_image": "example.png",
            "sections": {
                "Steps To Reproduce": "1) step one\n2) step two",
                "Actual": "fails",
            },
            "full_text": "ABC-7",
        }
    ]
    md = to_markdown(records)
    assert "1. step one" in md
    assert "2. step two" in md
    assert "Source Image" in md
