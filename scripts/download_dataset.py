from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests
from gdown.download_folder import download_folder


FOLDER_URL = "https://drive.google.com/drive/folders/1RNoCZI-MTXn1LqHAKBWJdOz_jhsSmdKF?usp=drive_link"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download the full public assignment dataset from Google Drive."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dataset"),
        help="Directory where receipt images will be downloaded.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap for the number of missing files to download.",
    )
    parser.add_argument(
        "--retry",
        type=int,
        default=3,
        help="Retry attempts per file.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.25,
        help="Short delay between successful downloads.",
    )
    return parser.parse_args()


def fetch_folder_listing(output_dir: Path) -> list[object]:
    return download_folder(
        url=FOLDER_URL,
        output=str(output_dir),
        quiet=True,
        use_cookies=False,
        skip_download=True,
    )


def download_file(
    session: requests.Session,
    file_id: str,
    destination: Path,
    retries: int,
) -> tuple[bool, str]:
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    headers = {"User-Agent": USER_AGENT}
    last_error = "unknown error"
    for attempt in range(1, retries + 1):
        try:
            with session.get(
                url,
                headers=headers,
                stream=True,
                allow_redirects=True,
                timeout=90,
            ) as response:
                content_type = response.headers.get("content-type", "")
                response.raise_for_status()
                if "html" in content_type.lower():
                    raise RuntimeError(
                        f"unexpected HTML response after redirects: {response.url}"
                    )
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            handle.write(chunk)
                return True, ""
        except Exception as exc:  # noqa: BLE001
            last_error = f"attempt {attempt}: {type(exc).__name__}: {exc}"
            time.sleep(min(2.0 * attempt, 10.0))
    return False, last_error


def main() -> int:
    args = parse_args()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Reading Google Drive folder metadata...")
    files = fetch_folder_listing(output_dir)
    local_files = {path.name for path in output_dir.glob("*") if path.is_file()}
    missing = [
        item
        for item in files
        if Path(item.path).name not in local_files
    ]
    if args.limit is not None:
        missing = missing[: args.limit]

    print(
        f"Remote files: {len(files)} | Local files: {len(local_files)} | Missing: {len(missing)}"
    )
    if not missing:
        print("Dataset is already complete.")
        return 0

    session = requests.Session()
    downloaded = 0
    failed: list[tuple[str, str]] = []
    for index, item in enumerate(missing, start=1):
        destination = output_dir / Path(item.local_path).name
        print(f"[{index}/{len(missing)}] Downloading {destination.name}")
        ok, error = download_file(
            session=session,
            file_id=item.id,
            destination=destination,
            retries=args.retry,
        )
        if ok:
            downloaded += 1
            time.sleep(args.sleep_seconds)
        else:
            failed.append((destination.name, error))
            print(f"  failed: {error}")

    print(
        f"Download finished. Added {downloaded} files. Remaining failures: {len(failed)}"
    )
    if failed:
        print("Failed files:")
        for name, error in failed[:50]:
            print(f"  {name}: {error}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

