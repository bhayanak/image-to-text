from unittest.mock import patch

from image_to_text.cli import build_parser, main


def test_build_parser() -> None:
    parser = build_parser()
    assert parser is not None
    args = parser.parse_args(["extract", "test.png"])
    assert args.command == "extract"
    assert args.images == ["test.png"]


def test_extract_command_help() -> None:
    parser = build_parser()
    args = parser.parse_args(["extract", "test.png", "--format", "json", "--output-dir", "out"])
    assert args.format == "json"
    assert args.output_dir == "out"
    assert args.stdout is False


def test_raw_command_help() -> None:
    parser = build_parser()
    args = parser.parse_args(["raw", "test.png", "--engine", "easyocr"])
    assert args.command == "raw"
    assert args.engine == "easyocr"


@patch("image_to_text.cli.process_batch")
def test_extract_command_runs_with_stdout(mock_batch, capsys) -> None:
    mock_batch.return_value = [
        {"id": "ABC-1", "source_image": None, "sections": {"Notes": "ok"}, "full_text": "ok"}
    ]
    code = main(["extract", "sample.png", "--format", "json", "--stdout", "-q"])
    assert code == 0


@patch("image_to_text.cli.process_batch")
def test_extract_command_runs_to_file(mock_batch, tmp_path) -> None:
    mock_batch.return_value = [
        {"id": "ABC-1", "source_image": None, "sections": {"Notes": "ok"}, "full_text": "ok"}
    ]
    code = main(["extract", "sample.png", "--format", "md", "--output-dir", str(tmp_path)])
    assert code == 0
    mock_batch.assert_called_once()


@patch("image_to_text.cli.extract_raw")
def test_raw_command_runs(mock_extract, capsys) -> None:
    mock_extract.return_value = "hello world"
    code = main(["raw", "sample.png"])
    assert code == 0
    captured = capsys.readouterr()
    assert "hello world" in captured.out


@patch("image_to_text.cli.extract_raw")
def test_raw_command_multiple_files(mock_extract, capsys) -> None:
    mock_extract.side_effect = ["text1", "text2"]
    code = main(["raw", "file1.png", "file2.png"])
    assert code == 0
    captured = capsys.readouterr()
    assert "file1.png" in captured.out
    assert "file2.png" in captured.out


@patch("image_to_text.cli.extract_raw")
def test_raw_command_handles_error(mock_extract, capsys) -> None:
    mock_extract.side_effect = FileNotFoundError("not found")
    code = main(["raw", "missing.png"])
    assert code == 0  # Command completes even if image missing


def test_main_keyboard_interrupt(monkeypatch) -> None:
    def mock_process(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr("image_to_text.cli.process_batch", mock_process)
    code = main(["extract", "test.png"])
    assert code == 1


def test_extract_with_verbose_logging(monkeypatch, capsys) -> None:
    def mock_process(*args, **kwargs):
        return []

    monkeypatch.setattr("image_to_text.cli.process_batch", mock_process)
    code = main(["extract", "test.png", "-v"])
    assert code == 0


def test_extract_with_quiet_logging(monkeypatch, capsys) -> None:
    def mock_process(*args, **kwargs):
        return []

    monkeypatch.setattr("image_to_text.cli.process_batch", mock_process)
    code = main(["extract", "test.png", "-q"])
    assert code == 0


def test_extract_formats_md_json_txt(monkeypatch) -> None:
    def mock_process(*args, **kwargs):
        return [{"id": "T-1", "source_image": None, "sections": {}, "full_text": "test"}]

    monkeypatch.setattr("image_to_text.cli.process_batch", mock_process)
    for fmt in ["md", "json", "txt", "both", "all"]:
        code = main(["extract", "test.png", "--format", fmt])
        assert code == 0


def test_extract_with_threshold(monkeypatch) -> None:
    def mock_process(paths, engine, output_dir, fmt, stdout, threshold):
        assert threshold == 120
        return []

    monkeypatch.setattr("image_to_text.cli.process_batch", mock_process)
    code = main(["extract", "test.png", "--threshold", "120"])
    assert code == 0


def test_extract_with_engine(monkeypatch) -> None:
    def mock_process(paths, engine, output_dir, fmt, stdout, threshold):
        assert engine == "easyocr"
        return []

    monkeypatch.setattr("image_to_text.cli.process_batch", mock_process)
    code = main(["extract", "test.png", "--engine", "easyocr"])
    assert code == 0


def test_parser_defaults() -> None:
    """Test parser defaults for both commands."""
    parser = build_parser()

    # Extract defaults
    args = parser.parse_args(["extract", "test.png"])
    assert args.format == "both"
    assert args.output_dir == "output"
    assert args.stdout is False
    assert args.engine == "auto"
    assert args.threshold == 140

    # Raw defaults
    args = parser.parse_args(["raw", "test.png"])
    assert args.engine == "auto"
    assert args.threshold == 140


@patch("image_to_text.cli.process_batch")
def test_extract_empty_results(mock_batch, capsys) -> None:
    """Test extract with no extracted records."""
    mock_batch.return_value = []
    code = main(["extract", "test.png", "-q"])
    assert code == 0
    captured = capsys.readouterr()
    assert "No defects" in captured.out or "No text" in captured.out


@patch("image_to_text.cli.process_batch")
def test_extract_multiple_images(mock_batch) -> None:
    """Test extract with multiple image files."""
    mock_batch.return_value = [
        {"id": "A-1", "source_image": "a.png", "sections": {}, "full_text": "a"},
        {"id": "B-2", "source_image": "b.png", "sections": {}, "full_text": "b"},
    ]
    code = main(["extract", "test1.png", "test2.png"])
    assert code == 0
    assert mock_batch.call_count == 1


@patch("image_to_text.cli.extract_raw")
def test_raw_file_not_found_error_handling(mock_extract) -> None:
    """Test raw command handles file errors gracefully."""
    mock_extract.side_effect = FileNotFoundError("file not found")
    code = main(["raw", "missing.png"])
    assert code == 0  # Should not crash
