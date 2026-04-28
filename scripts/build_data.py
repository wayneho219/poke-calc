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
MEGA_SPRITES = ROOT / "data" / "sprites" / "mega"
TYPE_SPRITES = ROOT / "data" / "sprites" / "types"

_TYPE_IDS = {
    "normal": 1, "fighting": 2, "flying": 3, "poison": 4,
    "ground": 5, "rock": 6, "bug": 7, "ghost": 8, "steel": 9,
    "fire": 10, "water": 11, "grass": 12, "electric": 13,
    "psychic": 14, "ice": 15, "dragon": 16, "dark": 17, "fairy": 18,
}


def _fetch_pokemon(pid: int) -> Optional[dict]:
    resp = requests.get(f"{BASE}/pokemon/{pid}", timeout=10)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def _fetch_species(pid: int) -> dict:
    resp = requests.get(f"{BASE}/pokemon-species/{pid}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def _fetch_species_names(species_data: dict) -> dict:
    names = {n["language"]["name"]: n["name"] for n in species_data["names"]}
    return {
        "name_zh": names.get("zh-hant", names.get("zh-hans", "")),
        "name_ja": names.get("ja",     names.get("ja-hrkt", "")),
    }


def _fetch_ability(ability_url: str) -> dict:
    resp = requests.get(ability_url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    names = {n["language"]["name"]: n["name"] for n in data["names"]}
    flavor_texts: dict[str, str] = {}
    for ft in data.get("flavor_text_entries", []):
        lang = ft["language"]["name"]
        if lang not in flavor_texts:
            flavor_texts[lang] = ft["flavor_text"].replace("\n", " ").replace("\f", " ")
    return {
        "name_zh": names.get("zh-hant", names.get("zh-hans", names.get("en", ""))),
        "name_en": names.get("en", ""),
        "name_ja": names.get("ja", names.get("ja-hrkt", "")),
        "desc_zh": flavor_texts.get("zh-hant", flavor_texts.get("zh-hans", flavor_texts.get("en", ""))),
        "desc_en": flavor_texts.get("en", ""),
        "desc_ja": flavor_texts.get("ja", flavor_texts.get("ja-hrkt", "")),
    }


def _is_final_evolution(pid: int, chain: dict) -> bool:
    def _traverse(node: dict) -> Optional[bool]:
        species_url = node["species"]["url"]
        current_id = int(species_url.rstrip("/").split("/")[-1])
        if current_id == pid:
            return len(node["evolves_to"]) == 0
        for child in node["evolves_to"]:
            result = _traverse(child)
            if result is not None:
                return result
        return None

    result = _traverse(chain["chain"])
    return bool(result) if result is not None else True


def _fetch_evolution_chain(evolution_url: str) -> dict:
    resp = requests.get(evolution_url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _parse_ability_names(data: dict) -> dict:
    names = {n["language"]["name"]: n["name"] for n in data["names"]}
    flavor_texts: dict[str, str] = {}
    for ft in data.get("flavor_text_entries", []):
        lang = ft["language"]["name"]
        if lang not in flavor_texts:
            flavor_texts[lang] = ft["flavor_text"].replace("\n", " ").replace("\f", " ")
    return {
        "name_zh": names.get("zh-hant", names.get("zh-hans", names.get("en", ""))),
        "name_en": names.get("en", ""),
        "name_ja": names.get("ja", names.get("ja-hrkt", "")),
        "desc_zh": flavor_texts.get("zh-hant", flavor_texts.get("zh-hans", flavor_texts.get("en", ""))),
        "desc_en": flavor_texts.get("en", ""),
        "desc_ja": flavor_texts.get("ja", flavor_texts.get("ja-hrkt", "")),
    }


def _fetch_mega_forms(species_data: dict) -> list[dict]:
    mega_forms = []
    for variety in species_data.get("varieties", []):
        name = variety["pokemon"]["name"]
        if "mega" not in name:
            continue
        resp = requests.get(variety["pokemon"]["url"], timeout=10)
        resp.raise_for_status()
        raw = resp.json()

        suffix = name.split(f"{species_data['name']}-", 1)[-1] if "-" in name else "mega"

        stats = {s["stat"]["name"]: s["base_stat"] for s in raw["stats"]}
        types = [t["type"]["name"] for t in raw["types"]]

        abilities = raw.get("abilities", [])
        ability_data = {}
        for a in abilities:
            resp2 = requests.get(a["ability"]["url"], timeout=10)
            resp2.raise_for_status()
            ability_data = _parse_ability_names(resp2.json())
            break  # Mega forms only have one ability

        other = (raw.get("sprites", {}).get("other", {}) or {})
        home = other.get("home", {}) or {}
        artwork = other.get("official-artwork", {}) or {}
        sprite_url = home.get("front_default") or artwork.get("front_default") or ""

        sprite_path = ""
        if sprite_url:
            dest = MEGA_SPRITES / f"{species_data['id']}-{suffix}.png"
            MEGA_SPRITES.mkdir(parents=True, exist_ok=True)
            try:
                r = requests.get(sprite_url, timeout=15)
                r.raise_for_status()
                dest.write_bytes(r.content)
                sprite_path = str(dest.relative_to(ROOT))
            except Exception:
                pass

        form_names = {n["language"]["name"]: n["name"] for n in raw.get("names", [])}
        name_zh = form_names.get("zh-hant", form_names.get("zh-hans", f"Mega {species_data['name'].title()}"))
        name_en = form_names.get("en", f"Mega {species_data['name'].title()}")
        name_ja = form_names.get("ja", form_names.get("ja-hrkt", ""))

        mega_forms.append({
            "suffix": suffix,
            "name_zh": name_zh,
            "name_en": name_en,
            "name_ja": name_ja,
            "types": types,
            "base_stats": {
                "hp": stats["hp"], "attack": stats["attack"],
                "defense": stats["defense"], "sp_attack": stats["special-attack"],
                "sp_defense": stats["special-defense"], "speed": stats["speed"],
            },
            "ability": ability_data,
            "sprite_path": sprite_path,
        })
        time.sleep(0.1)

    return mega_forms


def _download_sprite(url: str, path: Path) -> bool:
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        return True
    except Exception:
        return False


def download_type_sprites() -> None:
    TYPE_SPRITES.mkdir(parents=True, exist_ok=True)
    base_url = (
        "https://raw.githubusercontent.com/PokeAPI/sprites/master"
        "/sprites/types/generation-viii/sword-shield/{type_id}.png"
    )
    for type_name, type_id in _TYPE_IDS.items():
        dest = TYPE_SPRITES / f"{type_name}.png"
        if dest.exists():
            continue
        url = base_url.format(type_id=type_id)
        _download_sprite(url, dest)
        time.sleep(0.05)


def build(
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> int:
    SPRITES.mkdir(parents=True, exist_ok=True)
    download_type_sprites()

    existing: dict[int, dict] = {}
    if OUT_JSON.exists():
        for entry in json.loads(OUT_JSON.read_text(encoding="utf-8")):
            existing[entry["id"]] = entry

    rows: list[dict] = []
    for pid in range(1, TOTAL + 1):
        sprite_path = SPRITES / f"{pid}.png"

        if pid in existing and sprite_path.exists() and "abilities" in existing[pid]:
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

            species   = _fetch_species(pid)
            names     = _fetch_species_names(species)
            stats     = {s["stat"]["name"]: s["base_stat"] for s in raw["stats"]}
            home      = (raw.get("sprites", {}).get("other", {}) or {}).get("home", {}) or {}
            sprite_url = home.get("front_default", "") or ""
            if sprite_path.exists():
                downloaded = True
            else:
                downloaded = _download_sprite(sprite_url, sprite_path) if sprite_url else False

            # Abilities
            regular_abilities = []
            dream_ability = None
            for a in raw.get("abilities", []):
                ab = _fetch_ability(a["ability"]["url"])
                if a.get("is_hidden"):
                    dream_ability = ab
                else:
                    regular_abilities.append(ab)
                time.sleep(0.05)

            # Evolution chain
            evo_url = species.get("evolution_chain", {}).get("url", "")
            is_final = True
            if evo_url:
                chain_data = _fetch_evolution_chain(evo_url)
                is_final = _is_final_evolution(pid, chain_data)
                time.sleep(0.05)

            # Mega forms
            mega_forms = _fetch_mega_forms(species)

            entry = {
                "id":       pid,
                "name_en":  raw["name"],
                "name_zh":  names["name_zh"],
                "name_ja":  names["name_ja"],
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
                "is_final_evolution": is_final,
                "abilities": regular_abilities,
                "dream_ability": dream_ability,
                "mega_forms": mega_forms,
            }
            rows.append(entry)
            label = f"{raw['name']} / {names['name_zh']} / {names['name_ja']}"
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
