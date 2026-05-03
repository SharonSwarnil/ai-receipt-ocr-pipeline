# Receipt OCR Pipeline

This repo is a small document-AI project that turns messy receipt images into structured JSON and a spend summary.

I built it to handle the kind of problems that show up in real OCR work: skewed scans, low-contrast photos, mixed receipt layouts, noisy merchant names, and totals that are not always easy to spot. The pipeline does not train a custom model. Instead, it combines image cleanup, OCR, parsing rules, and confidence checks so the full flow is easy to rerun and inspect.

## What it does

- preprocesses receipt images before OCR
- runs OCR with `rapidocr-onnxruntime`
- extracts store name, transaction date, item lines, item prices, and total amount
- writes one JSON file per receipt
- builds an overall expense summary
- flags low-confidence fields for manual review

## Why this project is useful

Most receipt OCR demos work on clean examples and break down quickly once the input gets a little messy. This project tries to be more practical:

- it tests multiple image variants and picks the strongest OCR result
- it uses field-specific extraction logic instead of one generic parser
- it keeps confidence scores next to the extracted values
- it separates generation and validation, which makes debugging easier

## Project structure

- `main.py`: entry point for the full pipeline
- `scripts/download_dataset.py`: downloads the dataset from Google Drive
- `scripts/validate_outputs.py`: checks the generated outputs for missing and low-confidence fields
- `src/receipt_ocr/`: preprocessing, OCR, extraction, and summary code
- `tests/`: unit tests for parsing logic
- `docs/approach.md`: project notes and design choices
- `docs/next_steps.md`: what I would improve next
- `outputs/`: generated JSON files and the final summary

## Quick start

Run these commands from the project root:

```powershell
python -m pip install -r requirements.txt
python scripts/download_dataset.py
python main.py --input dataset --output outputs
python scripts/validate_outputs.py
python -m unittest discover -s tests
```

If you already have outputs and just want to continue without reprocessing everything:

```powershell
python main.py --input dataset --output outputs --skip-existing
```

## Step by step

### 1. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 2. Download the dataset

```powershell
python scripts/download_dataset.py
```

The downloader fetches each file directly instead of relying on a single folder export, which helps avoid partial downloads.

### 3. Run the OCR pipeline

```powershell
python main.py --input dataset --output outputs
```

This creates:

- `outputs/json/*.json`
- `outputs/summary.json`

### 4. Validate the run

```powershell
python scripts/validate_outputs.py
python -m unittest discover -s tests
```

This gives a quick check on:

- output file count
- files missing totals
- files missing store names
- files with low-confidence fields
- parser test coverage

## How the pipeline works

1. Each receipt image is cleaned up with resizing, deskewing, contrast enhancement, denoising, and thresholding.
2. OCR runs on multiple processed variants of the same image.
3. The best OCR result is selected using confidence and text coverage.
4. The extracted text is grouped into lines and parsed into store name, date, items, and total.
5. A JSON file is written for each receipt, then a summary file is generated for the whole dataset.

## Confidence scoring strategy

Confidence scores are computed using:

- OCR confidence from RapidOCR
- pattern validation for dates and money values
- keyword checks such as `TOTAL` and `AMOUNT`
- positional hints, such as giving more weight to totals near the bottom of the receipt

Fields with confidence below `0.7` are flagged for manual review.

## About training

There is no fine-tuning step in this repo.

The project is built around OCR, preprocessing, and rule-based extraction. For this kind of dataset, that was enough to get a solid baseline while keeping the pipeline simple to run and inspect.

## Example output

Each receipt produces a JSON file like this:

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

## Current run snapshot

On the current full dataset run in this repo:

- `371` receipts were processed
- `370` receipts had a recovered total
- `24335.95` total spend was recovered
- `122` receipts were flagged for at least one low-confidence field
- `6.JPG` is the only file still missing a total

Generated files:

- `outputs/json/`
- `outputs/summary.json`

## A couple of practical notes

- I added `scripts/download_dataset.py` after hitting an incomplete Google Drive folder download on an earlier pass.
- I tightened store-name filtering after seeing noisy labels like `TAX INVOICE`, `POSTED`, and `TOTAL` show up as merchants in early runs.
- Some OCR noise still remains on difficult receipts, but the low-confidence flags make those cases easy to find.
