"""Fixture-based tests for PIL operations and file handling."""

import pytest
from PIL import Image

from image_to_text.core import (
    clean_text,
    load_and_preprocess,
    parse_defects,
    to_json,
    to_markdown,
    to_text,
    write_output,
)


@pytest.fixture
def test_image(tmp_path):
    """Create a simple test image."""
    img = Image.new("RGB", (100, 80), color=(200, 200, 200))
    img_path = tmp_path / "test.png"
    img.save(img_path)
    return str(img_path)


@pytest.fixture
def large_test_image(tmp_path):
    """Create a large test image."""
    img = Image.new("RGB", (2000, 1500), color=(100, 100, 100))
    img_path = tmp_path / "large.png"
    img.save(img_path)
    return str(img_path)


def test_load_preprocess_small_image_resizes(test_image) -> None:
    """Verify that small images get resized."""
    result = load_and_preprocess(test_image)
    assert result.width >= 1000
    assert result.mode == "L"  # Should be grayscale


def test_load_preprocess_large_image_not_resized(large_test_image) -> None:
    """Verify that large images are not resized."""
    result = load_and_preprocess(large_test_image)
    assert result.width == 2000
    assert result.mode == "L"


def test_write_output_creates_directories(tmp_path) -> None:
    """Test that write_output creates output directories."""
    records = [
        {
            "id": "TEST-1",
            "source_image": "test.png",
            "sections": {"Notes": "test"},
            "full_text": "TEST-1 content",
        }
    ]
    output_dir = tmp_path / "new" / "output"
    write_output(records, "test", str(output_dir), fmt="md", stdout=False)
    assert output_dir.exists()
    assert (output_dir / "test.md").exists()


def test_write_output_single_formats(tmp_path) -> None:
    """Test writing each format individually."""
    records = [{"id": "A-1", "source_image": None, "sections": {}, "full_text": "a"}]
    output_dir = tmp_path / "out"

    write_output(records, "md_only", str(output_dir), fmt="md", stdout=False)
    assert (output_dir / "md_only.md").exists()
    assert not (output_dir / "md_only.json").exists()

    write_output(records, "json_only", str(output_dir), fmt="json", stdout=False)
    assert (output_dir / "json_only.json").exists()
    assert not (output_dir / "json_only.md").exists()

    write_output(records, "txt_only", str(output_dir), fmt="txt", stdout=False)
    assert (output_dir / "txt_only.txt").exists()


def test_to_markdown_empty_records() -> None:
    """Test markdown output with no records."""
    md = to_markdown([])
    assert md == ""


def test_to_text_empty_records() -> None:
    """Test text output with no records."""
    txt = to_text([])
    assert txt == ""


def test_to_json_empty_records() -> None:
    """Test JSON output with empty records."""
    js = to_json([])
    assert "[]" in js


def test_clean_text_preserves_content() -> None:
    """Test that clean_text preserves meaningful content."""
    text = "Line1\\nLine2\\n\\n\\nLine3"
    cleaned = clean_text(text)
    assert "Line1" in cleaned
    assert "Line2" in cleaned
    assert "Line3" in cleaned


def test_parse_defects_preserves_all_text() -> None:
    """Verify that full_text field preserves all OCR output."""
    text = "PRE-123\\nSome description\\nMore details"
    records = parse_defects(text)
    assert len(records) == 1
    assert records[0]["full_text"] == text
    assert "PRE-123" in records[0]["id"]


def test_output_file_content_markdown(tmp_path) -> None:
    """Test that markdown output contains expected content."""
    records = [
        {
            "id": "T-99",
            "source_image": "example.png",
            "sections": {"Notes": "Important note"},
            "full_text": "content",
        }
    ]
    output_dir = tmp_path
    write_output(records, "test", str(output_dir), fmt="md", stdout=False)

    md_file = output_dir / "test.md"
    content = md_file.read_text()
    assert "T-99" in content
    assert "Important note" in content
    assert "example.png" in content


def test_output_file_content_json(tmp_path) -> None:
    """Test that JSON output is valid and contains expected data."""
    records = [
        {
            "id": "J-1",
            "source_image": "test.png",
            "sections": {"Notes": "test"},
            "full_text": "j1",
        }
    ]
    output_dir = tmp_path
    write_output(records, "test", str(output_dir), fmt="json", stdout=False)

    json_file = output_dir / "test.json"
    content = json_file.read_text()
    assert '"id": "J-1"' in content
    assert "test.png" in content
