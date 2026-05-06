# img-to-text

Extract and organize text from screenshots with OCR.

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