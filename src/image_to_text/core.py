from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DEFECT_ID_RE = re.compile(r"[A-Z]{2,10}-\d+")
ARTIFACT_RE = re.compile(r"[|¬~`§±]")
SECTION_LABEL_RE = re.compile(
    r"^\s*(description|steps to reproduce|steps|expected|actual|summary|notes|"
    r"environment|impact|priority|workaround|result)\s*[:：]\s*(.*)$",
    re.IGNORECASE,
)


def load_and_preprocess(image_path: str, threshold: int = 140):
    """Open, validate, and pre-process a screenshot for OCR."""
    try:
        from PIL import Image, ImageFilter
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Pillow is required. Install with: pip install Pillow") from exc

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Screenshot not found: {image_path}")

    try:
        img = Image.open(path)
        img.verify()
        img = Image.open(path)
    except Exception as exc:
        raise OSError(f"Screenshot not found or unreadable: {exc}") from exc

    log.info("Loaded image: %s (%sx%s)", path.name, img.width, img.height)
    img = img.convert("L")

    if img.width < 1000:
        scale = 1000 / img.width
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        log.info("Resized image to %sx%s", img.width, img.height)

    img = img.filter(ImageFilter.SHARPEN)
    img = img.point(lambda px: 255 if px > threshold else 0)
    log.info("Pre-processing complete (grayscale + threshold=%d)", threshold)
    return img


def _pil_to_bytes(img) -> bytes:
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def extract_text(img, engine: str = "auto") -> str:
    """Run OCR on a pre-processed image and return raw text."""
    pytesseract = None
    easyocr = None

    try:
        import pytesseract as _pytesseract

        pytesseract = _pytesseract
    except ImportError:
        pass

    try:
        import easyocr as _easyocr

        easyocr = _easyocr
    except ImportError:
        pass

    if engine == "auto":
        engine = "tesseract" if pytesseract else "easyocr"

    if engine == "tesseract" and pytesseract is None:
        raise RuntimeError("pytesseract is not installed")
    if engine == "easyocr" and easyocr is None:
        raise RuntimeError("easyocr is not installed")

    if pytesseract is None and easyocr is None:
        raise RuntimeError("An OCR engine is required. Install one of: pytesseract or easyocr")

    try:
        if engine == "tesseract":
            text = pytesseract.image_to_string(img, lang="eng")
        elif engine == "easyocr":
            reader = easyocr.Reader(["en"], verbose=False)
            results = reader.readtext(_pil_to_bytes(img), detail=0)
            text = "\n".join(results)
        else:
            raise ValueError(f"Unknown OCR engine: {engine}")
    except Exception as exc:
        raise RuntimeError("Unable to extract text, please check image quality.") from exc

    log.info("OCR extraction success (%d characters)", len(text))
    return text


def clean_text(raw: str) -> str:
    """Normalize OCR text and remove common OCR artifacts."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = ARTIFACT_RE.sub("", text)
    lines = [line.rstrip() for line in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalize_label(label: str) -> str:
    label = label.strip().lower()
    if label in {"steps", "steps to reproduce"}:
        return "Steps To Reproduce"
    return " ".join(word.capitalize() for word in label.split())


def _extract_sections(block: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = "Notes"
    sections[current] = []

    for line in block.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            if sections[current] and sections[current][-1] != "":
                sections[current].append("")
            continue

        match = SECTION_LABEL_RE.match(line_stripped)
        if match:
            current = _normalize_label(match.group(1))
            sections.setdefault(current, [])
            rest = match.group(2).strip()
            if rest:
                sections[current].append(rest)
            continue

        sections.setdefault(current, []).append(line_stripped)

    flattened: dict[str, str] = {}
    for label, values in sections.items():
        text = "\n".join(values).strip()
        if text:
            flattened[label] = text
    return flattened or {"Notes": block.strip()}


def _split_defect_blocks(text: str) -> list[tuple[str, str]]:
    matches = list(DEFECT_ID_RE.finditer(text))
    if not matches:
        return [("UNKNOWN", text)]

    blocks: list[tuple[str, str]] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        defect_id = match.group(0)
        blocks.append((defect_id, text[start:end].strip()))
    return blocks


def parse_defects(text: str, source_image: str | None = None) -> list[dict[str, Any]]:
    """Extract structured records while preserving all OCR text."""
    defects: list[dict[str, Any]] = []
    for defect_id, block in _split_defect_blocks(text):
        record = {
            "id": defect_id,
            "source_image": source_image,
            "sections": _extract_sections(block),
            "full_text": block,
        }
        defects.append(record)

    log.info("Parsed %d record(s): %s", len(defects), [d["id"] for d in defects])
    return defects


def _split_steps(text: str) -> list[str]:
    numbered = re.findall(r"(?:^|\n)\s*\d+[.)]\s*(.+)", text)
    if numbered:
        return [step.strip() for step in numbered if step.strip()]
    return [line.strip() for line in text.splitlines() if line.strip()]


def to_markdown(defects: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for d in defects:
        lines.append(f"### Defect {d['id']}")
        if d.get("source_image"):
            lines.append(f"**Source Image:** {d['source_image']}")
        for label, content in d["sections"].items():
            if label == "Steps To Reproduce":
                lines.append(f"**{label}:**")
                for i, step in enumerate(_split_steps(content), 1):
                    lines.append(f"{i}. {step}")
            else:
                lines.append(f"**{label}:** {content}")
        lines.append("")
    return "\n".join(lines)


def to_text(defects: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for d in defects:
        title = f"Defect {d['id']}"
        if d.get("source_image"):
            title += f" ({d['source_image']})"
        blocks.append(title)
        blocks.append("-" * len(title))
        blocks.append(d["full_text"])
        blocks.append("")
    return "\n".join(blocks).strip()


def to_json(defects: list[dict[str, Any]]) -> str:
    return json.dumps(defects, indent=2, ensure_ascii=False)


def write_output(
    defects: list[dict[str, Any]],
    base_name: str,
    output_dir: str,
    fmt: str = "both",
    stdout: bool = False,
) -> None:
    """Write reports in requested format or print to stdout."""
    if stdout:
        if fmt in {"md", "both", "all"}:
            print(to_markdown(defects))
        if fmt in {"json", "both", "all"}:
            print(to_json(defects))
        if fmt in {"txt", "all"}:
            print(to_text(defects))
        return

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if fmt in {"md", "both", "all"}:
        md_path = out / f"{base_name}.md"
        md_path.write_text(to_markdown(defects), encoding="utf-8")
        log.info("Markdown report saved: %s", md_path)

    if fmt in {"json", "both", "all"}:
        json_path = out / f"{base_name}.json"
        json_path.write_text(to_json(defects), encoding="utf-8")
        log.info("JSON report saved: %s", json_path)

    if fmt in {"txt", "all"}:
        txt_path = out / f"{base_name}.txt"
        txt_path.write_text(to_text(defects), encoding="utf-8")
        log.info("Text report saved: %s", txt_path)


def process_image(
    image_path: str,
    engine: str = "auto",
    output_dir: str = "output",
    fmt: str = "both",
    stdout: bool = False,
    threshold: int = 140,
) -> list[dict[str, Any]]:
    """Full pipeline for one image: load, OCR, clean, parse, write output."""
    log.info("Starting OCR workflow for: %s", image_path)
    img = load_and_preprocess(image_path, threshold=threshold)
    raw_text = extract_text(img, engine=engine)
    cleaned = clean_text(raw_text)
    defects = parse_defects(cleaned, source_image=Path(image_path).name)

    write_output(defects, Path(image_path).stem, output_dir, fmt=fmt, stdout=stdout)
    return defects


def process_batch(
    image_paths: list[str],
    engine: str = "auto",
    output_dir: str = "output",
    fmt: str = "both",
    stdout: bool = False,
    threshold: int = 140,
) -> list[dict[str, Any]]:
    """Process multiple screenshots and aggregate parsed records."""
    all_defects: list[dict[str, Any]] = []
    for path in image_paths:
        try:
            defects = process_image(
                path,
                engine=engine,
                output_dir=output_dir,
                fmt=fmt,
                stdout=stdout,
                threshold=threshold,
            )
            all_defects.extend(defects)
        except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
            log.error("Skipping %s: %s", path, exc)
    return all_defects


def extract_raw(image_path: str, engine: str = "auto", threshold: int = 140) -> str:
    """Return cleaned OCR text from a screenshot without structured parsing."""
    img = load_and_preprocess(image_path, threshold=threshold)
    raw = extract_text(img, engine=engine)
    return clean_text(raw)
