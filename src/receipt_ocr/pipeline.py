from __future__ import annotations

import json
from pathlib import Path

from receipt_ocr.extractors import extract_date, extract_items, extract_store_name, extract_total_amount
from receipt_ocr.models import FieldValue, ReceiptResult
from receipt_ocr.ocr_engine import ReceiptOCR
from receipt_ocr.preprocess import build_image_variants, load_image
from receipt_ocr.summary import build_expense_summary


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


class ReceiptPipeline:
    def __init__(self) -> None:
        self.ocr = ReceiptOCR()

    def process_image(self, image_path: Path) -> ReceiptResult:
        image = load_image(str(image_path))
        variants = build_image_variants(image)
        bundle = self.ocr.run_best_variant(variants)
        store_name = extract_store_name(bundle.lines)
        date = extract_date(bundle.lines)
        total_amount, conflicts, total_index = extract_total_amount(bundle.lines)
        items, items_confidence = extract_items(bundle.lines, total_index)
        low_confidence_fields = [
            field_name
            for field_name, field in (
                ("store_name", store_name),
                ("date", date),
                ("total_amount", total_amount),
            )
            if field.confidence < 0.7
        ]
        if items_confidence < 0.7:
            low_confidence_fields.append("items")
        notes: list[str] = []
        if not items:
            notes.append("No item rows were confidently extracted from this receipt.")
        if total_amount.value is None and items:
            notes.append("Total amount missing; downstream summary will exclude this receipt.")
        return ReceiptResult(
            source_file=image_path.name,
            store_name=store_name,
            date=date,
            total_amount=total_amount,
            items=items,
            items_confidence=items_confidence,
            ocr_summary=bundle.summary,
            low_confidence_fields=low_confidence_fields,
            conflicts=conflicts,
            notes=notes,
        )

    def process_directory(
        self,
        input_dir: Path,
        output_dir: Path,
        limit: int | None = None,
        skip_existing: bool = False,
    ) -> dict[str, object]:
        input_dir = input_dir.resolve()
        output_dir = output_dir.resolve()
        json_dir = output_dir / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        image_paths = sorted(
            path
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        if limit is not None:
            image_paths = image_paths[:limit]
        results: list[ReceiptResult] = []
        for index, image_path in enumerate(image_paths, start=1):
            output_path = json_dir / f"{image_path.stem}.json"
            if skip_existing and output_path.exists():
                print(f"[{index}/{len(image_paths)}] Skipping {image_path.name}")
                with output_path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                results.append(self._receipt_from_json(payload))
                continue
            print(f"[{index}/{len(image_paths)}] Processing {image_path.name}")
            receipt_result = self.process_image(image_path)
            results.append(receipt_result)
            with output_path.open("w", encoding="utf-8") as handle:
                json.dump(receipt_result.to_dict(), handle, indent=2, ensure_ascii=False)
        summary = build_expense_summary(results)
        summary["summary_path"] = str((output_dir / "summary.json").resolve())
        with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, ensure_ascii=False)
        return summary

    def _receipt_from_json(self, payload: dict[str, object]) -> ReceiptResult:
        def field_from(key: str) -> FieldValue:
            raw = payload[key]
            assert isinstance(raw, dict)
            return FieldValue(
                value=raw.get("value"),  # type: ignore[arg-type]
                confidence=float(raw.get("confidence", 0.0)),
                raw_text=raw.get("raw_text"),  # type: ignore[arg-type]
            )

        items = []
        for item_payload in payload.get("items", []):
            assert isinstance(item_payload, dict)
            from receipt_ocr.models import ExtractedItem, OCRSummary

            items.append(
                ExtractedItem(
                    name=str(item_payload.get("name", "")),
                    price=str(item_payload.get("price", "")),
                    confidence=float(item_payload.get("confidence", 0.0)),
                    raw_text=item_payload.get("raw_text"),  # type: ignore[arg-type]
                )
            )
        summary_payload = payload["ocr_summary"]
        assert isinstance(summary_payload, dict)
        from receipt_ocr.models import OCRSummary

        return ReceiptResult(
            source_file=str(payload["source_file"]),
            store_name=field_from("store_name"),
            date=field_from("date"),
            total_amount=field_from("total_amount"),
            items=items,
            items_confidence=float(payload.get("items_confidence", 0.0)),
            ocr_summary=OCRSummary(
                variant_used=str(summary_payload.get("variant_used", "unknown")),
                token_count=int(summary_payload.get("token_count", 0)),
                line_count=int(summary_payload.get("line_count", 0)),
                mean_confidence=float(summary_payload.get("mean_confidence", 0.0)),
                score=float(summary_payload.get("variant_score", 0.0)),
            ),
            low_confidence_fields=list(payload.get("low_confidence_fields", [])),
            conflicts=list(payload.get("conflicts", [])),
            notes=list(payload.get("notes", [])),
        )

