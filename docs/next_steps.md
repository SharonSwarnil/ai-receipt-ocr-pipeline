# Next Steps

This repo already runs end to end, but if I were turning it into a more production-ready OCR service, these are the first things I would add.

## 1. Packaging and deployment

- add a `Dockerfile` so the runtime is easy to reproduce
- move config values into a small settings file or environment variables
- expose the pipeline through a simple API or batch job wrapper

## 2. Better evaluation

- create a small hand-labeled validation set
- measure field-level accuracy for store name, date, items, and total
- track which receipt types fail most often

## 3. Data and output versioning

- version the dataset snapshots
- keep output summaries tied to a specific code revision
- make it easier to compare one run against another

## 4. Review flow for difficult receipts

- surface low-confidence receipts in a small review queue
- keep conflict details for totals and merchant names
- allow corrected values to be fed back into the system

## 5. Accuracy improvements

- add perspective correction for strongly angled photos
- improve merchant-name normalization across OCR variants
- add a learned line-classification layer if higher accuracy becomes more important than simplicity

## 6. Tests I would expand

- more unit tests around merchant filtering and total selection
- regression tests for tricky receipts that previously failed
- a smoke test that runs a tiny batch and checks the final summary shape
