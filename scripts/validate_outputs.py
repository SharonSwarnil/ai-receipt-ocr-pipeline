from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    outputs_dir = Path("outputs/json")
    files = sorted(outputs_dir.glob("*.json"))
    if not files:
        print("No receipt JSON outputs found in outputs/json.")
        return 1

    low_confidence: list[tuple[str, list[str]]] = []
    missing_total: list[str] = []
    missing_store: list[str] = []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        low_fields = payload.get("low_confidence_fields", [])
        if low_fields:
            low_confidence.append((path.name, list(low_fields)))
        if not payload.get("total_amount", {}).get("value"):
            missing_total.append(path.name)
        if not payload.get("store_name", {}).get("value"):
            missing_store.append(path.name)

    print(f"Output files: {len(files)}")
    print(f"Files with low-confidence fields: {len(low_confidence)}")
    print(f"Files missing total_amount: {len(missing_total)}")
    print(f"Files missing store_name: {len(missing_store)}")

    if low_confidence:
        print("\nSample low-confidence files:")
        for name, fields in low_confidence[:20]:
            print(f"  {name}: {', '.join(fields)}")

    if missing_total:
        print("\nFiles missing totals:")
        for name in missing_total[:20]:
            print(f"  {name}")

    if missing_store:
        print("\nFiles missing store names:")
        for name in missing_store[:20]:
            print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
