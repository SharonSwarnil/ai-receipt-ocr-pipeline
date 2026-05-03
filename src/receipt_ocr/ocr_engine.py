from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from rapidocr_onnxruntime import RapidOCR

from receipt_ocr.models import OCRLine, OCRSummary, OCRWord


KEYWORD_PATTERN = re.compile(
    r"\b(total|subtotal|tax|cash|store|thank|item|price|amount|date)\b",
    re.IGNORECASE,
)
MONEY_PATTERN = re.compile(r"\$?\d[\d,]*\.\d{2}")


@dataclass(slots=True)
class OCRResultBundle:
    words: list[OCRWord]
    lines: list[OCRLine]
    summary: OCRSummary


class ReceiptOCR:
    def __init__(self) -> None:
        self.engine = RapidOCR()

    def run_best_variant(self, variants: dict[str, np.ndarray]) -> OCRResultBundle:
        best_bundle: OCRResultBundle | None = None
        for variant_name, image in variants.items():
            raw_result, _ = self.engine(image)
            words = self._to_words(raw_result or [])
            lines = self._group_words_into_lines(words)
            score = self._score_variant(lines)
            mean_conf = self._mean_confidence(words)
            summary = OCRSummary(
                variant_used=variant_name,
                token_count=len(words),
                line_count=len(lines),
                mean_confidence=mean_conf,
                score=score,
            )
            bundle = OCRResultBundle(words=words, lines=lines, summary=summary)
            if best_bundle is None or bundle.summary.score > best_bundle.summary.score:
                best_bundle = bundle
        if best_bundle is None:
            raise RuntimeError("OCR did not produce any result bundle.")
        return best_bundle

    def _to_words(self, raw_result: list[list[object]]) -> list[OCRWord]:
        words: list[OCRWord] = []
        for entry in raw_result:
            if len(entry) < 3:
                continue
            box, text, confidence = entry
            if not isinstance(box, list) or not str(text).strip():
                continue
            normalized_box = [
                [float(point[0]), float(point[1])]
                for point in box
                if isinstance(point, (list, tuple)) and len(point) == 2
            ]
            if len(normalized_box) != 4:
                continue
            words.append(
                OCRWord(
                    box=normalized_box,
                    text=str(text).strip(),
                    confidence=float(confidence),
                )
            )
        return sorted(words, key=lambda word: (word.center_y, word.x_min))

    def _group_words_into_lines(self, words: list[OCRWord]) -> list[OCRLine]:
        if not words:
            return []
        lines: list[list[OCRWord]] = []
        current_line: list[OCRWord] = [words[0]]
        current_center = words[0].center_y
        current_height = max(words[0].height, 1.0)
        for word in words[1:]:
            # A tighter vertical threshold reduces accidental merges between
            # adjacent item rows on densely packed receipts.
            threshold = max(current_height, word.height, 10.0) * 0.4
            if abs(word.center_y - current_center) <= threshold:
                current_line.append(word)
                current_center = sum(item.center_y for item in current_line) / len(current_line)
                current_height = sum(item.height for item in current_line) / len(current_line)
            else:
                lines.append(sorted(current_line, key=lambda item: item.x_min))
                current_line = [word]
                current_center = word.center_y
                current_height = max(word.height, 1.0)
        lines.append(sorted(current_line, key=lambda item: item.x_min))
        merged_lines = [OCRLine(words=line_words) for line_words in lines if line_words]
        return [line for line in merged_lines if line.text]

    def _score_variant(self, lines: list[OCRLine]) -> float:
        if not lines:
            return 0.0
        joined_text = " ".join(line.text for line in lines)
        keyword_hits = len(KEYWORD_PATTERN.findall(joined_text))
        money_hits = len(MONEY_PATTERN.findall(joined_text))
        mean_line_conf = sum(line.confidence for line in lines) / len(lines)
        line_bonus = min(len(lines) / 50.0, 1.0)
        keyword_bonus = min(keyword_hits / 10.0, 1.0)
        money_bonus = min(money_hits / 20.0, 1.0)
        return (mean_line_conf * 0.55) + (line_bonus * 0.2) + (keyword_bonus * 0.15) + (money_bonus * 0.1)

    def _mean_confidence(self, words: list[OCRWord]) -> float:
        if not words:
            return 0.0
        return float(sum(word.confidence for word in words) / len(words))
