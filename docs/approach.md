# Project Notes

## What I was trying to solve

The goal was simple on paper: take a folder of receipt images and turn them into structured JSON. In practice, the hard part is that receipts are messy. Some are clean scans, some are dim phone photos, some are skewed, and some have layouts that make it hard to tell the merchant name from headers like `TAX INVOICE` or `POSTED`.

I wanted the project to handle that mess without turning into a one-off script that only works on a few lucky examples.

## Pipeline design

I split the flow into four parts:

1. image preprocessing
2. OCR
3. field extraction
4. output validation and summary generation

Each receipt is resized, deskewed, contrast-enhanced, denoised, and converted into multiple OCR-ready variants. OCR runs on those variants and the pipeline picks the best result using a simple score based on confidence and text coverage.

After that, the OCR output is grouped into reading-order lines and passed to field-specific extractors:

- `store_name`: picked from strong candidates near the top of the receipt, with filters to reject noisy labels
- `date`: matched with regex, parsed, and normalized to ISO format
- `items`: extracted from the body using inline item-price patterns and multi-line fallbacks
- `total_amount`: selected with keyword checks and extra guards so values like subtotal, tax, cash, or change do not get picked by mistake

## Why I stayed rule-based

This repo does not train a custom model. I kept it OCR-first and rule-based for two reasons:

- the dataset was small enough that a solid extraction pipeline was the fastest way to get reliable results
- the output is easier to debug when each step is visible

If a merchant name looks wrong or a total is missing, I can inspect the OCR text, the candidate lines, and the confidence values directly instead of treating the model as a black box.

## Confidence scoring

Every extracted field carries a confidence value. The score combines:

- OCR confidence from RapidOCR
- pattern validation for dates and money fields
- keyword evidence such as `TOTAL`, `AMOUNT`, and date markers
- positional hints, such as totals being more likely near the bottom

Anything below `0.70` is added to `low_confidence_fields` so the difficult cases can be reviewed quickly.

## A few issues I ran into

- Merchant names were noisy in early runs. Labels like `TAX INVOICE`, `ITEM`, `POSTED`, and `TOTAL` sometimes looked stronger than the actual store name, so I added filtering for invalid store keywords.
- Item lines were inconsistent. Some receipts keep the name and price on one line, while others split them across multiple lines.
- OCR artifacts showed up in small ways, like merged tokens such as `EGGS1 DOZ`. I cleaned up the easy cases without getting too aggressive and breaking valid text.
- The original Google Drive folder download was incomplete in this environment, so I added a direct downloader script that fetches files one by one and can resume cleanly.

## Current results

On the current full run:

- `371` receipt JSON files were generated
- `370` totals were recovered
- `24335.95` total spend was recovered
- `122` receipts were flagged for at least one low-confidence field
- `6.JPG` is the only file still missing a total

## If I kept working on it

The next improvements would be:

- a small labeled validation set for proper field-level accuracy tracking
- containerization for easier deployment
- data and output versioning for repeatable runs
- a lightweight review layer for low-confidence receipts
- a learning-based classifier on top of OCR lines if I wanted to push accuracy further
