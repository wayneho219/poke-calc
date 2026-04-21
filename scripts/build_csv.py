"""
One-time script to build data/pokemon_names.csv from PokéAPI.
Usage: python scripts/build_csv.py
Fetches species 1-1025 (Gen 1-9 national dex).
"""
import csv
import time
import requests
from pathlib import Path

BASE  = "https://pokeapi.co/api/v2"
OUT   = Path(__file__).parent.parent / "data" / "pokemon_names.csv"
TOTAL = 1025  # Gen 1-9


def fetch_names(species_id: int):
    url = f"{BASE}/pokemon-species/{species_id}"
    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        print(f"[{species_id}] Network error: {e}")
        return None
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    names = {n["language"]["name"]: n["name"] for n in data["names"]}
    return {
        "id":      species_id,
        "name_en": names.get("en", ""),
        "name_zh": names.get("zh-hant", names.get("zh-hans", "")),
        "name_ja": names.get("ja", names.get("ja-Hrkt", "")),
    }


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        for i in range(1, TOTAL + 1):
            row = fetch_names(i)
            if row:
                rows.append(row)
                print(f"[{i}/{TOTAL}] {row['name_en']} / {row['name_zh']} / {row['name_ja']}")
            else:
                print(f"[{i}/{TOTAL}] SKIPPED (404)")
            time.sleep(0.05)  # avoid rate limit
    except KeyboardInterrupt:
        print("\nInterrupted — writing partial results…")
    finally:
        with OUT.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "name_en", "name_zh", "name_ja"])
            writer.writeheader()
            writer.writerows(rows)

        print(f"\nDone. {len(rows)} records written to {OUT}")


if __name__ == "__main__":
    main()
