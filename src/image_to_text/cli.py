from __future__ import annotations

import argparse
import logging
import sys

from .core import extract_raw, process_batch

log = logging.getLogger(__name__)


def _configure_logging(verbose: bool = False, quiet: bool = False) -> None:
    level = logging.DEBUG if verbose else (logging.WARNING if quiet else logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s")


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("images", nargs="+", help="Path(s) to screenshot image files.")
    parser.add_argument(
        "--engine",
        choices=["tesseract", "easyocr", "auto"],
        default="auto",
        help="OCR engine (default: auto-detect).",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=140,
        help="Binarization threshold 0-255 (default: 140). Lower values produce more black.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose", action="store_true", help="Show debug-level logs.")
    group.add_argument("-q", "--quiet", action="store_true", help="Show only errors.")


def cmd_extract(args: argparse.Namespace) -> int:
    _configure_logging(args.verbose, args.quiet)
    defects = process_batch(
        args.images,
        engine=args.engine,
        output_dir=args.output_dir,
        fmt=args.format,
        stdout=args.stdout,
        threshold=args.threshold,
    )
    if not args.stdout:
        if defects:
            print(f"\nExtracted {len(defects)} record(s). Reports saved to: {args.output_dir}/")
        else:
            print("\nNo text could be extracted from the provided images.")
    return 0


def cmd_raw(args: argparse.Namespace) -> int:
    _configure_logging(args.verbose, args.quiet)
    for path in args.images:
        try:
            text = extract_raw(path, engine=args.engine, threshold=args.threshold)
            if len(args.images) > 1:
                print(f"--- {path} ---")
            print(text)
        except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
            log.error("Skipping %s: %s", path, exc)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="img-to-text",
        description="Extract and organize text from screenshots via OCR.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_extract = subparsers.add_parser(
        "extract",
        help="Run OCR, parse text into organized sections, and write reports.",
    )
    _add_common_args(p_extract)
    p_extract.add_argument(
        "--format",
        choices=["md", "json", "txt", "both", "all"],
        default="both",
        help="Output format (default: both => md + json).",
    )
    p_extract.add_argument(
        "--output-dir",
        default="output",
        help="Directory for generated reports (default: ./output).",
    )
    p_extract.add_argument(
        "--stdout",
        action="store_true",
        help="Print report to stdout instead of writing files.",
    )
    p_extract.set_defaults(func=cmd_extract)

    p_raw = subparsers.add_parser(
        "raw",
        help="Dump cleaned OCR text without structured parsing.",
    )
    _add_common_args(p_raw)
    p_raw.set_defaults(func=cmd_raw)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("\nAborted.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
