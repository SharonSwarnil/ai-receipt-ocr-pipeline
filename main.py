from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from receipt_ocr.pipeline import ReceiptPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract structured data from receipt images."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "dataset",
        help="Directory containing receipt images.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "outputs",
        help="Directory where JSON outputs and summary will be written.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for the number of files to process.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip receipts whose JSON output already exists.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pipeline = ReceiptPipeline()
    summary = pipeline.process_directory(
        input_dir=args.input,
        output_dir=args.output,
        limit=args.limit,
        skip_existing=args.skip_existing,
    )
    print(
        "Processed {processed_receipts} receipts. Summary written to {summary_path}".format(
            processed_receipts=summary["processed_receipts"],
            summary_path=summary["summary_path"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

