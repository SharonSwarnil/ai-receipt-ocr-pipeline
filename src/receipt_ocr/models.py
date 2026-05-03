from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class OCRWord:
    box: list[list[float]]
    text: str
    confidence: float

    @property
    def x_min(self) -> float:
        return min(point[0] for point in self.box)

    @property
    def x_max(self) -> float:
        return max(point[0] for point in self.box)

    @property
    def y_min(self) -> float:
        return min(point[1] for point in self.box)

    @property
    def y_max(self) -> float:
        return max(point[1] for point in self.box)

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def center_y(self) -> float:
        return (self.y_min + self.y_max) / 2.0


@dataclass(slots=True)
class OCRLine:
    words: list[OCRWord]

    @property
    def text(self) -> str:
        return " ".join(word.text.strip() for word in self.words if word.text.strip()).strip()

    @property
    def confidence(self) -> float:
        if not self.words:
            return 0.0
        return sum(word.confidence for word in self.words) / len(self.words)

    @property
    def x_min(self) -> float:
        return min(word.x_min for word in self.words)

    @property
    def x_max(self) -> float:
        return max(word.x_max for word in self.words)

    @property
    def y_min(self) -> float:
        return min(word.y_min for word in self.words)

    @property
    def y_max(self) -> float:
        return max(word.y_max for word in self.words)

    @property
    def center_y(self) -> float:
        return (self.y_min + self.y_max) / 2.0

    @property
    def height(self) -> float:
        return self.y_max - self.y_min


@dataclass(slots=True)
class FieldValue:
    value: str | None
    confidence: float
    raw_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "confidence": round(max(0.0, min(1.0, self.confidence)), 4),
            "raw_text": self.raw_text,
        }


@dataclass(slots=True)
class ExtractedItem:
    name: str
    price: str
    confidence: float
    raw_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "price": self.price,
            "confidence": round(max(0.0, min(1.0, self.confidence)), 4),
            "raw_text": self.raw_text,
        }


@dataclass(slots=True)
class OCRSummary:
    variant_used: str
    token_count: int
    line_count: int
    mean_confidence: float
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_used": self.variant_used,
            "token_count": self.token_count,
            "line_count": self.line_count,
            "mean_confidence": round(self.mean_confidence, 4),
            "variant_score": round(self.score, 4),
        }


@dataclass(slots=True)
class ReceiptResult:
    source_file: str
    store_name: FieldValue
    date: FieldValue
    total_amount: FieldValue
    items: list[ExtractedItem]
    items_confidence: float
    ocr_summary: OCRSummary
    low_confidence_fields: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "ocr_summary": self.ocr_summary.to_dict(),
            "store_name": self.store_name.to_dict(),
            "date": self.date.to_dict(),
            "items": [item.to_dict() for item in self.items],
            "items_confidence": round(max(0.0, min(1.0, self.items_confidence)), 4),
            "total_amount": self.total_amount.to_dict(),
            "low_confidence_fields": self.low_confidence_fields,
            "conflicts": self.conflicts,
            "notes": self.notes,
        }

