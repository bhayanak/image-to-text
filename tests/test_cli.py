from image_to_text import cli


def test_extract_command_runs(monkeypatch, capsys) -> None:
    def fake_process_batch(*args, **kwargs):
        return [{"id": "ABC-1", "sections": {"Notes": "ok"}, "full_text": "ok"}]

    monkeypatch.setattr(cli, "process_batch", fake_process_batch)
    code = cli.main(["extract", "sample.png", "--format", "json", "--stdout"])
    assert code == 0


def test_raw_command_runs(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "extract_raw", lambda *_args, **_kwargs: "hello world")
    code = cli.main(["raw", "sample.png"])
    assert code == 0
    out = capsys.readouterr().out
    assert "hello world" in out
