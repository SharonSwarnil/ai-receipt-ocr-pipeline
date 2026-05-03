from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from receipt_ocr.models import ReceiptResult

INVALID_STORE_KEYWORDS = {
    "tax",
    "invoice",
    "total",
    "item",
    "items",
    "posted",
    "table",
}
INVALID_STORE_PHRASES = {
    "tax invoice",
    "payment type",
    "your order number",
}


def safe_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def is_valid_store_name(store_name: str) -> bool:
    lowered = store_name.lower().strip()
    squashed = re.sub(r"[^a-z0-9]+", "", lowered)
    if any(phrase in lowered for phrase in INVALID_STORE_PHRASES):
        return False
    if squashed in {"taxinvoice", "total", "posted", "table", "item", "items"}:
        return False
    if squashed.startswith("item") and len(squashed) <= 10:
        return False
    if any(keyword in lowered for keyword in INVALID_STORE_KEYWORDS):
        if len(lowered.split()) <= 4:
            return False
    return True


def canonicalize_store_name(store_name: str) -> str:
    normalized = "".join(character for character in store_name.upper() if character.isalnum())
    if "WALMART" in normalized:
        return "WALMART"
    if normalized == "DOLLARTREE":
        return "DOLLAR TREE"
    if normalized in {"WHOLEFOODS", "WHOLE", "FOODS"}:
        return "WHOLE FOODS"
    if normalized.startswith("TRADERJOES"):
        return "TRADER JOE'S"
    if normalized.startswith("MRDIY"):
        return "MR D.I.Y."
    return store_name


def build_expense_summary(results: list[ReceiptResult]) -> dict[str, object]:
    total_spend = Decimal("0.00")
    spend_per_store: dict[str, Decimal] = {}
    missing_total_files: list[str] = []
    low_confidence_count = 0
    for result in results:
        if result.low_confidence_fields:
            low_confidence_count += 1
        total_value = safe_decimal(result.total_amount.value)
        if total_value is None:
            missing_total_files.append(result.source_file)
            continue
        total_spend += total_value
        if not result.store_name.value or result.store_name.confidence < 0.75:
            store_name = "UNKNOWN_STORE"
        else:
            store_name = canonicalize_store_name(result.store_name.value)
            if not is_valid_store_name(store_name):
                store_name = "UNKNOWN_STORE"
        spend_per_store[store_name] = spend_per_store.get(store_name, Decimal("0.00")) + total_value
    summary = {
        "processed_receipts": len(results),
        "number_of_transactions": len(results) - len(missing_total_files),
        "total_spend": f"{total_spend.quantize(Decimal('0.01'))}",
        "spend_per_store": {
            store: f"{amount.quantize(Decimal('0.01'))}"
            for store, amount in sorted(
                spend_per_store.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        },
        "receipts_missing_total": missing_total_files,
        "receipts_with_low_confidence_fields": low_confidence_count,
    }
    return summary
