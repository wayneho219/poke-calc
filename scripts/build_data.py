"""
Build data/pokemon_data.json and data/sprites/{id}.png from PokéAPI.
Usage: python3 scripts/build_data.py
Supports resume: skips entries whose sprite already exists.
"""
import json
import time
import requests
from pathlib import Path
from typing import Callable, Optional

BASE     = "https://pokeapi.co/api/v2"
TOTAL    = 1025
ROOT     = Path(__file__).parent.parent
OUT_JSON = ROOT / "data" / "pokemon_data.json"
SPRITES  = ROOT / "data" / "sprites"


def _fetch_pokemon(pid: int) -> Optional[dict]:
    resp = requests.get(f"{BASE}/pokemon/{pid}", timeout=10)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def _fetch_species_names(pid: int) -> dict:
    resp = requests.get(f"{BASE}/pokemon-species/{pid}", timeout=10)
    resp.raise_for_status()
    names = {n["language"]["name"]: n["name"] for n in resp.json()["names"]}
    return {
        "name_zh": names.get("zh-Hant", names.get("zh-Hans", "")),
        "name_ja": names.get("ja",      names.get("ja-Hrkt", "")),
    }


def _download_sprite(url: str, path: Path) -> bool:
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        return True
    except Exception:
        return False


def build(
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> int:
    SPRITES.mkdir(parents=True, exist_ok=True)

    existing: dict[int, dict] = {}
    if OUT_JSON.exists():
        for entry in json.loads(OUT_JSON.read_text(encoding="utf-8")):
            existing[entry["id"]] = entry

    rows: list[dict] = []
    for pid in range(1, TOTAL + 1):
        sprite_path = SPRITES / f"{pid}.png"

        if pid in existing and sprite_path.exists():
            rows.append(existing[pid])
            if on_progress:
                on_progress(pid, TOTAL, f"SKIP {existing[pid].get('name_en', str(pid))}")
            continue

        try:
            raw = _fetch_pokemon(pid)
            if raw is None:
                if on_progress:
                    on_progress(pid, TOTAL, f"SKIPPED #{pid} (404)")
                continue

            species   = _fetch_species_names(pid)
            stats     = {s["stat"]["name"]: s["base_stat"] for s in raw["stats"]}
            home      = (raw.get("sprites", {}).get("other", {}) or {}).get("home", {}) or {}
            sprite_url = home.get("front_default", "") or ""
            downloaded = _download_sprite(sprite_url, sprite_path) if sprite_url else False

            entry = {
                "id":       pid,
                "name_en":  raw["name"],
                "name_zh":  species["name_zh"],
                "name_ja":  species["name_ja"],
                "types":    [t["type"]["name"] for t in raw["types"]],
                "base_stats": {
                    "hp":         stats["hp"],
                    "attack":     stats["attack"],
                    "defense":    stats["defense"],
                    "sp_attack":  stats["special-attack"],
                    "sp_defense": stats["special-defense"],
                    "speed":      stats["speed"],
                },
                "sprite_path": f"data/sprites/{pid}.png" if downloaded else "",
            }
            rows.append(entry)
            label = f"{raw['name']} / {species['name_zh']} / {species['name_ja']}"
            if on_progress:
                on_progress(pid, TOTAL, label)

        except Exception as e:
            if on_progress:
                on_progress(pid, TOTAL, f"ERROR #{pid}: {e}")

        time.sleep(0.1)

    tmp = OUT_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.rename(OUT_JSON)
    return len(rows)


def main() -> None:
    def on_progress(current: int, total: int, name: str) -> None:
        print(f"[{current}/{total}] {name}")
    count = build(on_progress=on_progress)
    print(f"\nDone. {count} records written to {OUT_JSON}")


if __name__ == "__main__":
    main()
