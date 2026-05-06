# img-to-text

Extract and organize text from screenshots with OCR.

<p align="center">
  <a href="https://github.com/bhayanak/image-to-text/actions/workflows/ci.yml"><img src="https://github.com/bhayanak/image-to-text/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://codecov.io/gh/bhayanak/image-to-text"><img src="https://codecov.io/gh/bhayanak/sp-dl/graph/badge.svg" alt="Coverage"></a>
  <a href="https://codecov.io/gh/bhayanak/image-to-text"><img src="https://img.shields.io/badge/coverage-98%25-brightgreen" alt="Coverage 98%"></a>
  <a href="https://pypi.org/project/img-to-text/"><img src="https://img.shields.io/pypi/v/img-to-text" alt="PyPI"></a>
  <a href="https://pypi.org/project/img-to-text/"><img src="https://img.shields.io/pypi/pyversions/img-to-text" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
</p>

## Features

- OCR from screenshots using `pytesseract` or `easyocr`
- Automatic pre-processing for better OCR quality
- Structured extraction into labeled sections when possible
- Full text is always preserved in output
- Report output as Markdown, JSON, and plain text

## Install

```bash
pip install img-to-text
```

Local development install:

```bash
pip install -e ".[dev,all-ocr]"
```

## Usage

```bash
img-to-text extract screenshot.png
img-to-text extract screenshot.png --format all
img-to-text extract screenshot1.png screenshot2.png --stdout --format json
img-to-text raw screenshot.png --engine easyocr
```

### Output formats

- `md`: organized markdown report
- `json`: structured JSON records including `full_text`
- `txt`: plain text grouped by record
- `both`: markdown + JSON (default)
- `all`: markdown + JSON + text

## License

[MIT](LICENSE)