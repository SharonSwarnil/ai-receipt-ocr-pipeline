# Receipt OCR Pipeline

A practical OCR pipeline that turns receipt images into structured JSON with confidence scoring, validation checks, and spend summaries.

This project focuses on the part that usually gets messy in the real world: receipts with skew, blur, weak contrast, odd layouts, noisy headers, and totals that compete with tax, cash, or subtotal lines. Instead of treating OCR as a one-step problem, the pipeline cleans the image, tests multiple OCR-ready variants, extracts fields with targeted rules, and flags the uncertain cases for review.

## Highlights

- Processed `371` receipt images end to end
- Recovered totals for `370` receipts
- Generated per-receipt JSON plus an aggregate spend summary
- Added confidence scoring and low-confidence flags for manual review
- Built direct dataset download and output validation scripts for reproducibility

## Pipeline at a glance

```text
Receipt image
  -> preprocessing
  -> OCR on multiple image variants
  -> best result selection
  -> field extraction
  -> per-receipt JSON
  -> summary and validation
```

## What the project does

- preprocesses receipt images before OCR
- runs OCR with `rapidocr-onnxruntime`
- extracts store name, transaction date, item lines, item prices, and total amount
- writes one JSON file per receipt
- builds an overall expense summary
- flags low-confidence fields for manual review

## Tech stack

- Python
- RapidOCR with ONNX Runtime
- OpenCV
- Pillow
- python-dateutil
- unittest

## Why I built it this way

Most receipt OCR demos work on clean examples. This repo is closer to the kind of pipeline I would want if I actually had to debug messy receipts in production.

- multiple image variants instead of trusting one preprocessing pass
- field-specific extractors instead of one generic parser
- confidence scores attached to extracted values
- validation scripts so bad outputs are easy to spot quickly
- store-name filtering to remove noisy labels like `TAX INVOICE` and `POSTED`

## Project structure

- `main.py`: entry point for the full pipeline
- `scripts/download_dataset.py`: downloads the dataset from Google Drive
- `scripts/validate_outputs.py`: checks for missing and low-confidence fields
- `src/receipt_ocr/`: preprocessing, OCR, extraction, and summary code
- `tests/`: unit tests for parsing logic
- `docs/approach.md`: project notes and design choices
- `docs/next_steps.md`: ideas for taking the project further
- `outputs/summary.json`: latest full-run summary
- `outputs/samples/`: a few sample receipt JSON outputs
- `outputs/OUTPUTS.md`: short note about what is included in the repo

## Quick start

Run these commands from the project root:

```powershell
python -m pip install -r requirements.txt
python scripts/download_dataset.py
python main.py --input dataset --output outputs
python scripts/validate_outputs.py
python -m unittest discover -s tests
```

If outputs already exist and you just want to resume:

```powershell
python main.py --input dataset --output outputs --skip-existing
```

## Confidence scoring strategy

Confidence scores are computed using:

- OCR confidence from RapidOCR
- pattern validation for dates and money values
- keyword checks such as `TOTAL` and `AMOUNT`
- positional hints, such as giving more weight to totals near the bottom of the receipt

Fields with confidence below `0.7` are flagged for manual review.

## Sample output

The repo includes a few representative JSON outputs under `outputs/samples/`.

Each receipt produces a structure like this:

```json
{
  "source_file": "0.jpg",
  "store_name": {
    "value": "WALMART",
    "confidence": 0.94,
    "raw_text": "WAL*MART"
  },
  "date": {
    "value": "2010-08-20",
    "confidence": 0.91,
    "raw_text": "08/20/10 13:12:01"
  },
  "items": [
    {
      "name": "BANANAS",
      "price": "0.20",
      "confidence": 0.88,
      "raw_text": "BANANAS || 0.411b 11b/0.49 0.20N"
    }
  ],
  "total_amount": {
    "value": "5.11",
    "confidence": 0.97,
    "raw_text": "TOTAL 5.11"
  }
}
```

## Current results

On the latest full run in this repo:

- `371` receipts were processed
- `370` receipts had a recovered total
- `24335.95` total spend was recovered
- `122` receipts were flagged for at least one low-confidence field
- `6.JPG` is the only file still missing a total

The full summary is available in `outputs/summary.json`.

## Notes

- There is no fine-tuning step in this repo. The project is built around OCR, preprocessing, and rule-based extraction.
- I added `scripts/download_dataset.py` after hitting an incomplete Google Drive folder download on an earlier pass.
- Some OCR noise still remains on difficult receipts, but the low-confidence flags make those cases easy to find.
