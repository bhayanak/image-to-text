#!/usr/bin/env python3
"""Compatibility wrapper for local script-style execution."""

from image_to_text.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
