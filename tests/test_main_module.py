"""Tests for __main__ module entry point."""

import runpy
import sys
import types

import pytest


def test_main_module_raises_system_exit_with_cli_code(monkeypatch) -> None:
    fake_cli = types.SimpleNamespace(main=lambda: 7)
    monkeypatch.setitem(sys.modules, "image_to_text.cli", fake_cli)

    with monkeypatch.context() as m:
        m.setattr(sys, "argv", ["-m", "image_to_text"])
        with pytest.raises(SystemExit) as exc:
            runpy.run_module("image_to_text.__main__", run_name="__main__")

    assert exc.value.code == 7
