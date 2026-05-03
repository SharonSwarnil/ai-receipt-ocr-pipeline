from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from receipt_ocr.extractors import (
    extract_amount_candidates,
    extract_date,
    format_amount,
    normalize_amount,
    parse_inline_item,
)
from receipt_ocr.models import OCRLine, OCRWord


def make_line(text: str, confidence: float = 0.95) -> OCRLine:
    words = []
    x_position = 0.0
    for token in text.split():
        words.append(
            OCRWord(
                box=[
                    [x_position, 0.0],
                    [x_position + 20.0, 0.0],
                    [x_position + 20.0, 10.0],
                    [x_position, 10.0],
                ],
                text=token,
                confidence=confidence,
            )
        )
        x_position += 22.0
    return OCRLine(words=words)


class ExtractorTests(unittest.TestCase):
    def test_normalize_amount(self) -> None:
        self.assertEqual(str(normalize_amount("$25.44")), "25.44")
        self.assertEqual(format_amount(normalize_amount("1.00T")), "1.00")

    def test_extract_amount_candidates(self) -> None:
        amounts = extract_amount_candidates("Subtotal $24.00 Total $25.44")
        self.assertEqual([str(amount) for amount in amounts], ["24.00", "25.44"])

    def test_extract_date(self) -> None:
        field = extract_date([make_line("06-28-2014 12:34PM")])
        self.assertEqual(field.value, "2014-06-28")
        self.assertGreater(field.confidence, 0.7)

    def test_parse_inline_item(self) -> None:
        item = parse_inline_item(make_line("BANANAS ORGANIC 0.87"))
        assert item is not None
        self.assertEqual(item.name, "BANANAS ORGANIC")
        self.assertEqual(item.price, "0.87")


if __name__ == "__main__":
    unittest.main()

