# Output Notes

This folder keeps the project outputs that are useful to review on GitHub without making the repo unnecessarily heavy.

## Included in the repo

- `summary.json`: aggregate results from the latest full run
- `samples/`: a few representative receipt JSON files

## Not included in the repo

- the full `outputs/json/` directory with all `371` receipt outputs

That full folder is easy to regenerate locally with:

```powershell
python main.py --input dataset --output outputs
```

I kept the sample files here so the extraction format, confidence scores, and edge cases are still easy to inspect from the repo page.
