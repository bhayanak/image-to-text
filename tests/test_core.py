import builtins
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from image_to_text.core import (
    _extract_sections,
    _normalize_label,
    _split_defect_blocks,
    _split_steps,
    clean_text,
    extract_raw,
    extract_text,
    load_and_preprocess,
    parse_defects,
    process_batch,
    to_json,
    to_markdown,
    to_text,
    write_output,
)


def test_clean_text_removes_artifacts() -> None:
    raw = "ABC-1\r\nDescription: bad | text ¬\r\n\r\n\r\nActual: fail"
    cleaned = clean_text(raw)
    assert "|" not in cleaned
    assert "¬" not in cleaned
    assert "\r" not in cleaned


def test_clean_text_normalizes_line_endings() -> None:
    raw = "Line1\nLine2\n\n\n\nLine3"
    cleaned = clean_text(raw)
    assert cleaned == "Line1\nLine2\n\nLine3"


def test_normalize_label() -> None:
    assert _normalize_label("steps") == "Steps To Reproduce"
    assert _normalize_label("Steps to Reproduce") == "Steps To Reproduce"
    assert _normalize_label("description") == "Description"
    assert _normalize_label("  SUMMARY  ") == "Summary"


def test_extract_sections_with_labels() -> None:
    text = """Description: This is a bug
Steps: 1) first
2) second
Actual: crashes"""
    sections = _extract_sections(text)
    assert "Description" in sections
    assert "Steps To Reproduce" in sections
    assert "Actual" in sections
    assert "This is a bug" in sections["Description"]


def test_extract_sections_without_labels() -> None:
    text = "Just some text\nwithout labels"
    sections = _extract_sections(text)
    assert "Notes" in sections
    assert "Just some text" in sections["Notes"]


def test_split_steps_numbered() -> None:
    text = "1) first step\n2) second step\n3) third"
    steps = _split_steps(text)
    assert len(steps) == 3
    assert steps[0] == "first step"
    assert steps[1] == "second step"
    assert steps[2] == "third"


def test_split_steps_unnumbered() -> None:
    text = "just\nmulti\nline\ntext"
    steps = _split_steps(text)
    assert len(steps) == 4
    assert "just" in steps


def test_split_defect_blocks_single() -> None:
    text = "ABC-123\nSome content"
    blocks = _split_defect_blocks(text)
    assert len(blocks) == 1
    assert blocks[0][0] == "ABC-123"
    assert "Some content" in blocks[0][1]


def test_split_defect_blocks_multiple() -> None:
    text = "ABC-1\nContent1\nXYZ-2\nContent2\nPQR-99\nContent3"
    blocks = _split_defect_blocks(text)
    assert len(blocks) == 3
    assert blocks[0][0] == "ABC-1"
    assert blocks[1][0] == "XYZ-2"
    assert blocks[2][0] == "PQR-99"


def test_split_defect_blocks_no_id() -> None:
    text = "No defect ID here"
    blocks = _split_defect_blocks(text)
    assert len(blocks) == 1
    assert blocks[0][0] == "UNKNOWN"


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


def test_to_markdown_multiple_records() -> None:
    records = [
        {"id": "A-1", "source_image": None, "sections": {"Notes": "note1"}, "full_text": "A-1"},
        {"id": "B-2", "source_image": None, "sections": {"Notes": "note2"}, "full_text": "B-2"},
    ]
    md = to_markdown(records)
    assert "A-1" in md
    assert "B-2" in md


def test_to_text() -> None:
    records = [{"id": "TEST-1", "source_image": "img.png", "sections": {}, "full_text": "content1"}]
    txt = to_text(records)
    assert "TEST-1" in txt
    assert "img.png" in txt
    assert "content1" in txt


def test_to_json() -> None:
    records = [{"id": "X-1", "source_image": None, "sections": {"N": "v"}, "full_text": "t"}]
    js = to_json(records)
    assert '"id": "X-1"' in js
    assert '"sections"' in js


def test_write_output_to_files(tmp_path) -> None:
    records = [
        {"id": "TST-1", "source_image": None, "sections": {"Notes": "ok"}, "full_text": "ok"}
    ]
    output_dir = str(tmp_path)
    write_output(records, "test", output_dir, fmt="both", stdout=False)
    assert (tmp_path / "test.md").exists()
    assert (tmp_path / "test.json").exists()


def test_write_output_txt_format(tmp_path) -> None:
    records = [{"id": "T-1", "source_image": None, "sections": {}, "full_text": "text"}]
    write_output(records, "test", str(tmp_path), fmt="txt", stdout=False)
    assert (tmp_path / "test.txt").exists()


def test_write_output_all_formats(tmp_path) -> None:
    records = [{"id": "A-1", "source_image": None, "sections": {}, "full_text": "all"}]
    write_output(records, "test", str(tmp_path), fmt="all", stdout=False)
    assert (tmp_path / "test.md").exists()
    assert (tmp_path / "test.json").exists()
    assert (tmp_path / "test.txt").exists()


def test_write_output_to_stdout(capsys) -> None:
    records = [{"id": "S-1", "source_image": None, "sections": {}, "full_text": "stdout"}]
    write_output(records, "test", "dummy", fmt="md", stdout=True)
    captured = capsys.readouterr()
    assert "S-1" in captured.out


def test_load_and_preprocess_file_not_found() -> None:
    with pytest.raises(FileNotFoundError, match="Screenshot not found"):
        load_and_preprocess("nonexistent_image_xyz.png")


@patch("image_to_text.core.process_image")
def test_process_batch_multiple_images(mock_process) -> None:
    mock_process.return_value = [
        {"id": "B-1", "source_image": None, "sections": {}, "full_text": "ok"}
    ]
    results = process_batch(["img1.png", "img2.png"])
    assert len(results) == 2
    assert mock_process.call_count == 2


@patch("image_to_text.core.process_image")
def test_process_batch_handles_errors(mock_process) -> None:
    mock_process.side_effect = [
        FileNotFoundError("missing"),
        [{"id": "B-1", "source_image": None, "sections": {}, "full_text": "ok"}],
    ]
    results = process_batch(["bad.png", "good.png"])
    assert len(results) == 1


@patch("image_to_text.core.extract_text")
@patch("image_to_text.core.load_and_preprocess")
def test_extract_raw(mock_load, mock_extract) -> None:
    mock_img = MagicMock()
    mock_load.return_value = mock_img
    mock_extract.return_value = "raw text\n\n\nextra"
    result = extract_raw("test.png")
    assert "raw text" in result
    assert "extra" in result


def test_extract_text_no_ocr_installed(monkeypatch) -> None:
    """Test extract_text raises error when specific OCR engine not available."""
    from PIL import Image

    real_import = builtins.__import__

    def _import_fail_ocr(name, *args, **kwargs):
        if name in {"pytesseract", "easyocr"}:
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import_fail_ocr)

    img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    with pytest.raises(RuntimeError, match="easyocr is not installed"):
        extract_text(img, "auto")


def test_extract_text_invalid_engine(monkeypatch) -> None:
    """Test extract_text raises error for invalid engine."""
    from PIL import Image

    real_import = builtins.__import__

    def _import_fail_ocr(name, *args, **kwargs):
        if name in {"pytesseract", "easyocr"}:
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import_fail_ocr)

    img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    with pytest.raises(RuntimeError, match="An OCR engine is required"):
        extract_text(img, "invalid_engine")


def test_load_preprocess_corrupt_image(tmp_path, monkeypatch) -> None:
    """Test load_and_preprocess handles corrupt image gracefully."""
    from image_to_text.core import load_and_preprocess

    # Create a corrupt image file
    bad_img = tmp_path / "corrupt.png"
    bad_img.write_bytes(b"not a real image")

    with pytest.raises(OSError, match="Screenshot not found or unreadable"):
        load_and_preprocess(str(bad_img))


def test_pil_to_bytes_conversion() -> None:
    """Test PIL image to bytes conversion."""
    from PIL import Image

    from image_to_text.core import _pil_to_bytes

    img = Image.new("RGB", (50, 50), color=(100, 100, 100))
    data = _pil_to_bytes(img)
    assert isinstance(data, bytes)
    assert len(data) > 0


def test_extract_sections_preserves_blank_line_inside_section() -> None:
    text = """Description: line one

line two"""
    sections = _extract_sections(text)
    assert sections["Description"] == "line one\n\nline two"


def test_write_output_stdout_all_prints_all_formats(capsys) -> None:
    records = [{"id": "A-1", "source_image": None, "sections": {"Notes": "ok"}, "full_text": "ok"}]
    write_output(records, "test", "ignored", fmt="all", stdout=True)
    out = capsys.readouterr().out
    assert "### Defect A-1" in out
    assert '"id": "A-1"' in out
    assert "Defect A-1" in out


def test_process_image_pipeline_happy_path(monkeypatch, tmp_path) -> None:
    dummy_img = object()
    monkeypatch.setattr(
        "image_to_text.core.load_and_preprocess",
        lambda *_args, **_kwargs: dummy_img,
    )
    monkeypatch.setattr(
        "image_to_text.core.extract_text",
        lambda *_args, **_kwargs: "ABC-1\nNotes: ok",
    )
    monkeypatch.setattr("image_to_text.core.clean_text", lambda text: text)
    monkeypatch.setattr(
        "image_to_text.core.parse_defects",
        lambda text, source_image=None: [
            {
                "id": "ABC-1",
                "source_image": source_image,
                "sections": {"Notes": "ok"},
                "full_text": text,
            }
        ],
    )

    calls = {"count": 0}

    def _fake_write(defects, base_name, output_dir, fmt="both", stdout=False):
        assert defects[0]["id"] == "ABC-1"
        assert base_name == "sample"
        assert output_dir == str(tmp_path)
        assert fmt == "json"
        assert stdout is False
        calls["count"] += 1

    monkeypatch.setattr("image_to_text.core.write_output", _fake_write)

    from image_to_text.core import process_image

    result = process_image("sample.png", output_dir=str(tmp_path), fmt="json")
    assert result[0]["source_image"] == "sample.png"
    assert calls["count"] == 1


def test_extract_text_uses_tesseract_when_available(monkeypatch) -> None:
    class FakeTesseract:
        @staticmethod
        def image_to_string(_img, lang="eng"):
            assert lang == "eng"
            return "from tesseract"

    monkeypatch.setitem(sys.modules, "pytesseract", FakeTesseract)
    monkeypatch.delitem(sys.modules, "easyocr", raising=False)
    result = extract_text(object(), "auto")
    assert result == "from tesseract"


def test_extract_text_uses_easyocr_when_selected(monkeypatch) -> None:
    class FakeReader:
        def __init__(self, langs, verbose=False):
            assert langs == ["en"]
            assert verbose is False

        def readtext(self, _data, detail=0):
            assert detail == 0
            return ["line one", "line two"]

    fake_easy = types.SimpleNamespace(Reader=FakeReader)
    monkeypatch.delitem(sys.modules, "pytesseract", raising=False)
    monkeypatch.setitem(sys.modules, "easyocr", fake_easy)

    from PIL import Image

    img = Image.new("RGB", (16, 16), color=(255, 255, 255))
    result = extract_text(img, "easyocr")
    assert result == "line one\nline two"


def test_extract_text_wraps_engine_exception(monkeypatch) -> None:
    class BrokenTesseract:
        @staticmethod
        def image_to_string(_img, lang="eng"):
            raise ValueError("broken engine")

    monkeypatch.setitem(sys.modules, "pytesseract", BrokenTesseract)
    monkeypatch.delitem(sys.modules, "easyocr", raising=False)

    with pytest.raises(RuntimeError, match="Unable to extract text"):
        extract_text(object(), "tesseract")
