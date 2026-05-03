from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable

from dateutil import parser as date_parser

from receipt_ocr.models import ExtractedItem, FieldValue, OCRLine


DATE_PATTERN = re.compile(
    r"(?<!\d)(\d{1,4}[\/\-.]\d{1,2}[\/\-.]\d{1,4})(?!\d)"
)
AMOUNT_PATTERN = re.compile(r"[$S]?\d[\d,]*\.\d{2}")
TOP_STORE_SCAN = 8
INVALID_STORE_KEYWORDS = {
    "TAX",
    "INVOICE",
    "TOTAL",
    "ITEM",
    "ITEMS",
    "POSTED",
    "TABLE",
}
INVALID_STORE_PHRASES = {
    "TAX INVOICE",
    "PAYMENT TYPE",
    "YOUR ORDER NUMBER",
}

STORE_STOPWORDS = {
    "SURVEY",
    "FEEDBACK",
    "RECEIPT",
    "CHANCE",
    "WWW",
    "THANK",
    "OPEN",
    "STORE",
    "TEL",
    "PHONE",
    "MANAGER",
    "CASHIER",
    "SUPERCENTER",
    "DESCRIPTION",
}
HEADER_KEYWORDS = {"DESCRIPTION", "QTY", "PRICE", "TOTAL", "AMOUNT"}
TOTAL_KEYWORDS = {"TOTAL", "AMOUNT DUE", "BALANCE DUE", "NET TOTAL"}
SUBTOTAL_KEYWORDS = {"SUBTOTAL", "SUB TOTAL"}
EXCLUDED_TOTAL_KEYWORDS = {
    "CASH",
    "CHANGE",
    "DEBIT",
    "CREDIT",
    "SAVINGS",
    "DISCOUNT",
    "AUTH",
    "TRACE",
    "APPROVED",
}
NON_ITEM_KEYWORDS = {
    "DISCOUNT",
    "NON TAXABLE",
    "THANK",
    "CHANGE",
    "CASH",
    "DEBIT",
    "CREDIT",
    "SALE",
    "SALES TAX",
    "TAX",
    "AUTH",
    "TRACE",
    "APPROVED",
    "PURCHASE",
    "VISA",
    "MASTERCARD",
    "TC#",
    "TR#",
    "ST#",
    "OP#",
    "MANAGER",
    "PHONE",
    "STORE",
    "OPEN",
    "ITEMS SOLD",
    "THANK YOU",
}


def clean_text(text: str) -> str:
    text = text.replace("\uFF08", "(").replace("\uFF09", ")")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def upper_text(text: str) -> str:
    return clean_text(text).upper()


def contains_phrase(text: str, phrase: str) -> bool:
    pattern = r"\b" + re.escape(phrase) + r"\b"
    return re.search(pattern, upper_text(text)) is not None


def alpha_ratio(text: str) -> float:
    letters = sum(char.isalpha() for char in text)
    total = max(len(text), 1)
    return letters / total


def extract_amount_candidates(text: str) -> list[Decimal]:
    candidates: list[Decimal] = []
    for match in AMOUNT_PATTERN.findall(text.replace("O", "0")):
        normalized = normalize_amount(match)
        if normalized is None:
            continue
        candidates.append(normalized)
    return candidates


def normalize_amount(raw_value: str) -> Decimal | None:
    cleaned = raw_value.strip()
    cleaned = cleaned.replace("$", "").replace("S", "5")
    cleaned = re.sub(r"[^0-9.,]", "", cleaned)
    cleaned = cleaned.replace(",", "")
    if cleaned.count(".") > 1:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def format_amount(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'))}"


def has_keyword(text: str, keywords: Iterable[str]) -> bool:
    return any(contains_phrase(text, keyword) for keyword in keywords)


def starts_with_total_marker(text: str) -> bool:
    normalized = upper_text(text)
    return re.search(
        r"^(GRAND\s+TOTAL|TOTAL|AMOUNT DUE|BALANCE DUE|NET TOTAL|SUB\s*TOTAL)\b",
        normalized,
    ) is not None


def is_header_line(text: str) -> bool:
    matches = sum(1 for keyword in HEADER_KEYWORDS if contains_phrase(text, keyword))
    return matches >= 2


def is_invalid_store_name(text: str) -> bool:
    upper = upper_text(text)
    squashed = re.sub(r"[^A-Z0-9]+", "", upper)
    if any(phrase in upper for phrase in INVALID_STORE_PHRASES):
        return True
    if squashed in {"TAXINVOICE", "TOTAL", "POSTED", "TABLE", "ITEM", "ITEMS"}:
        return True
    if squashed.startswith("ITEM") and len(squashed) <= 10:
        return True
    if any(contains_phrase(upper, keyword) for keyword in INVALID_STORE_KEYWORDS):
        short_line = len(upper.split()) <= 4
        if short_line:
            return True
    return False


def looks_like_store_candidate(line: OCRLine) -> bool:
    text = clean_text(line.text)
    upper = upper_text(text)
    if not text or any(stopword in upper for stopword in STORE_STOPWORDS):
        return False
    if "@" in text or ".COM" in upper or "ID#" in upper or is_header_line(text):
        return False
    if is_invalid_store_name(text):
        return False
    if len(text) < 4 or alpha_ratio(text) < 0.45:
        return False
    if len(re.findall(r"\d", text)) > 3:
        return False
    return True


def extract_store_name(lines: list[OCRLine]) -> FieldValue:
    candidates: list[tuple[float, OCRLine]] = []
    for index, line in enumerate(lines[:TOP_STORE_SCAN]):
        if not looks_like_store_candidate(line):
            continue
        position_bonus = max(0.0, 0.25 - (index * 0.03))
        uppercase_bonus = 0.1 if line.text.isupper() else 0.0
        score = (line.confidence * 0.65) + position_bonus + uppercase_bonus + (alpha_ratio(line.text) * 0.1)
        candidates.append((score, line))
    if not candidates:
        return FieldValue(value=None, confidence=0.0, raw_text=None)
    score, line = max(candidates, key=lambda item: item[0])
    if score < 0.8:
        return FieldValue(value=None, confidence=score, raw_text=line.text)
    return FieldValue(value=clean_text(line.text), confidence=min(score, 0.99), raw_text=line.text)


def parse_date_string(raw_value: str) -> str | None:
    normalized = raw_value.replace("O", "0")
    try:
        parsed = date_parser.parse(normalized, dayfirst=False, yearfirst=False)
    except (ValueError, OverflowError, TypeError):
        return None
    if parsed.year < 1990 or parsed.year > datetime.now().year + 1:
        return None
    return parsed.strftime("%Y-%m-%d")


def extract_date(lines: list[OCRLine]) -> FieldValue:
    candidates: list[tuple[float, str, OCRLine]] = []
    for index, line in enumerate(lines):
        matches = DATE_PATTERN.findall(clean_text(line.text))
        if not matches:
            continue
        for match in matches:
            normalized_date = parse_date_string(match)
            if normalized_date is None:
                continue
            keyword_bonus = 0.15 if contains_phrase(line.text, "DATE") else 0.0
            lower_priority_penalty = 0.0 if index >= len(lines) // 2 else 0.05
            score = min(0.99, (line.confidence * 0.7) + 0.2 + keyword_bonus - lower_priority_penalty)
            candidates.append((score, normalized_date, line))
    if not candidates:
        return FieldValue(value=None, confidence=0.0, raw_text=None)
    score, normalized_date, line = max(candidates, key=lambda item: item[0])
    return FieldValue(value=normalized_date, confidence=score, raw_text=line.text)


def score_total_candidate(line: OCRLine, index: int, total_lines: int) -> tuple[float, Decimal | None]:
    amounts = extract_amount_candidates(line.text)
    if not amounts:
        return (0.0, None)
    starts_with_total = re.search(
        r"^(GRAND\s+TOTAL|TOTAL|AMOUNT DUE|BALANCE DUE|NET TOTAL)\b",
        upper_text(line.text),
    )
    starts_with_subtotal = re.search(r"^SUB\s*TOTAL\b", upper_text(line.text))
    value = amounts[-1]
    score = line.confidence * 0.55
    if starts_with_total:
        score += 0.38
    elif has_keyword(line.text, TOTAL_KEYWORDS):
        score += 0.05
    if starts_with_subtotal:
        score -= 0.28
    if has_keyword(line.text, EXCLUDED_TOTAL_KEYWORDS):
        score -= 0.18
    if len(amounts) > 1 and not starts_with_total and not starts_with_subtotal:
        score -= 0.25
    if index < int(total_lines * 0.5) and not starts_with_total and not starts_with_subtotal:
        score -= 0.1
    score += min(index / max(total_lines, 1), 1.0) * 0.08
    if value > Decimal("0.00"):
        score += 0.08
    return (score, value)


def extract_total_amount(lines: list[OCRLine]) -> tuple[FieldValue, list[str], int | None]:
    candidates: list[tuple[float, Decimal, OCRLine, int]] = []
    conflicts: list[str] = []
    for index, line in enumerate(lines):
        score, value = score_total_candidate(line, index, len(lines))
        if value is None or score <= 0:
            continue
        candidates.append((score, value, line, index))
    if not candidates:
        return (FieldValue(value=None, confidence=0.0, raw_text=None), conflicts, None)
    candidates.sort(key=lambda item: item[0], reverse=True)
    best_score, best_value, best_line, best_index = candidates[0]
    for score, value, line, _ in candidates[1:4]:
        if abs(score - best_score) < 0.08 and value != best_value:
            conflicts.append(
                f"Competing total candidate {format_amount(value)} from '{clean_text(line.text)}'"
            )
    return (
        FieldValue(
            value=format_amount(best_value),
            confidence=min(best_score, 0.99),
            raw_text=best_line.text,
        ),
        conflicts,
        best_index,
    )


def is_probable_item_line(line: OCRLine) -> bool:
    text = clean_text(line.text)
    if not text or has_keyword(text, NON_ITEM_KEYWORDS):
        return False
    if starts_with_total_marker(text) or has_keyword(text, EXCLUDED_TOTAL_KEYWORDS):
        return False
    if is_header_line(text):
        return False
    if alpha_ratio(text) < 0.15:
        return False
    if not re.match(r"^[^A-Za-z]*[A-Za-z]", text):
        return False
    return True


def looks_like_detail_price_line(line: OCRLine) -> bool:
    text = clean_text(line.text)
    if not text:
        return False
    letter_count = sum(character.isalpha() for character in text)
    amounts = extract_amount_candidates(text)
    return bool(amounts) and letter_count <= 4


def clean_item_name(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"[@*]+", " ", text)
    tokens = []
    for token in text.split():
        compact = re.sub(r"[^A-Za-z0-9/-]", "", token)
        if re.fullmatch(r"[A-Z0-9]*\d{5,}[A-Z0-9]*", compact, flags=re.IGNORECASE):
            continue
        tokens.append(token)
    text = " ".join(tokens)
    text = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", text)
    text = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", text)
    text = re.sub(r"\b\d+\s*[xX@]?\s*$", "", text)
    text = re.sub(r"\b[FNT]\b\s*$", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -:")


def parse_inline_item(line: OCRLine) -> ExtractedItem | None:
    text = clean_text(line.text)
    if not is_probable_item_line(line):
        return None
    amounts = extract_amount_candidates(text)
    if not amounts:
        return None
    last_amount = format_amount(amounts[-1])
    price_index = len(text)
    for match in AMOUNT_PATTERN.finditer(text.replace("O", "0")):
        price_index = match.start()
        break
    name = clean_item_name(text[:price_index])
    if not name or len(name) < 2:
        return None
    if starts_with_total_marker(text):
        return None
    confidence = min(0.99, (line.confidence * 0.75) + 0.18)
    return ExtractedItem(
        name=name,
        price=last_amount or "0.00",
        confidence=confidence,
        raw_text=line.text,
    )


def find_item_section_bounds(lines: list[OCRLine], total_index: int | None) -> tuple[int, int]:
    start_index = 0
    for index, line in enumerate(lines):
        if is_header_line(line.text):
            start_index = index + 1
            break
        if is_probable_item_line(line) and (
            extract_amount_candidates(line.text)
            or (
                index + 1 < len(lines)
                and looks_like_detail_price_line(lines[index + 1])
            )
        ):
            start_index = index
            break
    end_index = total_index if total_index is not None else len(lines)
    if end_index <= start_index:
        end_index = len(lines)
    return start_index, end_index


def extract_items(lines: list[OCRLine], total_index: int | None) -> tuple[list[ExtractedItem], float]:
    start_index, end_index = find_item_section_bounds(lines, total_index)
    section = lines[start_index:end_index]
    items: list[ExtractedItem] = []
    skip_next = False
    for index, line in enumerate(section):
        if skip_next:
            skip_next = False
            continue
        parsed = parse_inline_item(line)
        if parsed is not None:
            items.append(parsed)
            continue
        if not is_probable_item_line(line):
            continue
        if index + 1 >= len(section):
            continue
        next_line = section[index + 1]
        if looks_like_detail_price_line(next_line):
            detail_amounts = extract_amount_candidates(next_line.text)
            if not detail_amounts:
                continue
            items.append(
                ExtractedItem(
                    name=clean_item_name(line.text),
                    price=format_amount(detail_amounts[-1]) or "0.00",
                    confidence=min(
                        0.92,
                        (line.confidence * 0.45) + (next_line.confidence * 0.35) + 0.12,
                    ),
                    raw_text=f"{line.text} || {next_line.text}",
                )
            )
            skip_next = True
    if not items:
        return ([], 0.0)
    average_confidence = sum(item.confidence for item in items) / len(items)
    return (items, average_confidence)
