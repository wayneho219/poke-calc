# UX Improvements v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the text-input Pokémon and nature selectors with fuzzy-search dropdowns and a 5×5 nature grid across all three tabs, and add type effectiveness, abilities, and Mega evolution sections to the Search tab detail card.

**Architecture:** New reusable Streamlit components (`pokemon_selector`, `nature_selector`, `type_badge`) are extracted to `interfaces/streamlit/components/`. A new `shared/type_chart.py` provides the 18×18 effectiveness matrix. `build_data.py` is extended to fetch abilities, evolution chain flags, Mega forms, and type sprites. The domain model gains four new optional fields (backward-compatible via defaults), and `LocalJsonRepository.fuzzy_match` gains final-evolution priority sorting.

**Tech Stack:** Python 3.11, Streamlit 1.x, PokéAPI REST, pytest, dataclasses (frozen), session_state pattern for component state.

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `shared/config.py` | Add MEGA_SPRITES_DIR, TYPE_SPRITES_DIR |
| Modify | `domain/models/pokemon.py` | Add 4 new optional fields |
| Modify | `adapters/local_json_repository.py` | Parse new fields; sort fuzzy_match |
| Modify | `tests/adapters/fixtures/test_pokemon_data.json` | Add new fields for tests |
| Modify | `tests/adapters/test_local_json_repository.py` | Tests for new field parsing and sort order |
| Create | `shared/type_chart.py` | 18×18 effectiveness matrix + helper functions |
| Create | `tests/shared/test_type_chart.py` | Unit tests for type chart |
| Modify | `shared/i18n/zh.json`, `en.json`, `ja.json` | Add section-header and UI-label keys |
| Modify | `scripts/build_data.py` | Fetch abilities, evolution chain, Mega forms, type sprites |
| Create | `interfaces/streamlit/components/__init__.py` | Package marker |
| Create | `interfaces/streamlit/components/type_badge.py` | HTML badge helper returning strings |
| Create | `interfaces/streamlit/components/pokemon_selector.py` | Reusable fuzzy-search selector widget |
| Create | `interfaces/streamlit/components/nature_selector.py` | Reusable 5×5 nature grid widget |
| Modify | `interfaces/streamlit/app.py` | Wire all three tabs to new components |

---

## Task 1: Config — sprite directory constants

**Files:**
- Modify: `shared/config.py`

- [ ] **Step 1: Modify config.py**

```python
# shared/config.py
from pathlib import Path

ROOT             = Path(__file__).parent.parent
CSV_PATH         = ROOT / "data" / "pokemon_names.csv"
DATA_JSON_PATH   = ROOT / "data" / "pokemon_data.json"
SPRITES_DIR      = ROOT / "data" / "sprites"
MEGA_SPRITES_DIR = ROOT / "data" / "sprites" / "mega"
TYPE_SPRITES_DIR = ROOT / "data" / "sprites" / "types"
CACHE_DIR        = ROOT / "adapters" / "cache"
I18N_DIR         = ROOT / "shared" / "i18n"
```

- [ ] **Step 2: Verify the constants resolve**

```bash
cd /Users/wayneho/poke-calc
python3 -c "from shared.config import MEGA_SPRITES_DIR, TYPE_SPRITES_DIR; print(MEGA_SPRITES_DIR); print(TYPE_SPRITES_DIR)"
```

Expected output (two lines):
```
/Users/wayneho/poke-calc/data/sprites/mega
/Users/wayneho/poke-calc/data/sprites/types
```

- [ ] **Step 3: Commit**

```bash
git add shared/config.py
git commit -m "chore(config): add MEGA_SPRITES_DIR and TYPE_SPRITES_DIR constants"
```

---

## Task 2: Domain Model — extend Pokemon dataclass

**Files:**
- Modify: `domain/models/pokemon.py`
- Modify: `tests/adapters/fixtures/test_pokemon_data.json`

- [ ] **Step 1: Replace pokemon.py with the new version**

```python
# domain/models/pokemon.py
from __future__ import annotations
from dataclasses import dataclass, field
from .nature import Nature, NatureRegistry
from .stats import StatSet


@dataclass(frozen=True)
class Pokemon:
    id: int
    name_en: str
    name_zh: str
    name_ja: str
    base_stats: StatSet
    types: tuple[str, ...]
    nature: Nature = field(default_factory=lambda: NatureRegistry.get_by_name("Hardy"))
    sprite_url: str = ""
    sprite_shiny_url: str = ""
    is_final_evolution: bool = False
    abilities: list = field(default_factory=list)
    dream_ability: dict | None = None
    mega_forms: list = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "types", tuple(self.types))
```

- [ ] **Step 2: Update test fixture JSON to include new fields**

Replace `tests/adapters/fixtures/test_pokemon_data.json` with:

```json
[
  {
    "id": 25,
    "name_en": "pikachu",
    "name_zh": "皮卡丘",
    "name_ja": "ピカチュウ",
    "types": ["electric"],
    "base_stats": {"hp": 35, "attack": 55, "defense": 40, "sp_attack": 50, "sp_defense": 50, "speed": 90},
    "sprite_path": "data/sprites/25.png",
    "is_final_evolution": false,
    "abilities": [
      {"name_zh": "靜電", "name_en": "Static", "name_ja": "せいでんき",
       "desc_zh": "接觸到對手時，有30%的機率令其麻痺。", "desc_en": "Contact with the Pokémon may cause paralysis.", "desc_ja": "触れた相手をまひさせることがある。"}
    ],
    "dream_ability": {"name_zh": "避雷針", "name_en": "Lightning Rod", "name_ja": "ひらいしん",
      "desc_zh": "把電屬性招式引向自己，不承受傷害，提升特攻。", "desc_en": "Draws in all Electric-type moves to boost Sp. Atk.", "desc_ja": "でんきタイプの技を引きつけ、とくこうを上げる。"},
    "mega_forms": []
  },
  {
    "id": 445,
    "name_en": "garchomp",
    "name_zh": "烈咬陸鯊",
    "name_ja": "ガブリアス",
    "types": ["dragon", "ground"],
    "base_stats": {"hp": 108, "attack": 130, "defense": 95, "sp_attack": 80, "sp_defense": 85, "speed": 102},
    "sprite_path": "data/sprites/445.png",
    "is_final_evolution": true,
    "abilities": [
      {"name_zh": "鯊魚皮", "name_en": "Sand Veil", "name_ja": "すながくれ",
       "desc_zh": "沙暴天氣時閃躲率提升20%。", "desc_en": "Boosts evasion in a sandstorm.", "desc_ja": "すなあらしのとき、回避率が上がる。"},
      {"name_zh": "粗皮", "name_en": "Rough Skin", "name_ja": "ざらざら",
       "desc_zh": "接觸到對手時，對手損失其最大HP的1/8。", "desc_en": "Inflicts damage on the attacker upon contact.", "desc_ja": "触れた相手のHPを少し削る。"}
    ],
    "dream_ability": null,
    "mega_forms": [
      {
        "suffix": "mega",
        "name_zh": "Mega 烈咬陸鯊",
        "name_en": "Mega Garchomp",
        "name_ja": "メガガブリアス",
        "types": ["dragon", "ground"],
        "base_stats": {"hp": 108, "attack": 170, "defense": 115, "sp_attack": 120, "sp_defense": 95, "speed": 92},
        "ability": {"name_zh": "沙之力", "name_en": "Sand Force", "name_ja": "すなのちから",
          "desc_zh": "沙暴天氣下，岩石、鋼、地面屬性技能威力提升1.3倍。", "desc_en": "Boosts Rock, Steel and Ground moves in a sandstorm.", "desc_ja": "すなあらしのとき、いわ・はがね・じめんタイプの技の威力が上がる。"},
        "sprite_path": ""
      }
    ]
  }
]
```

- [ ] **Step 3: Run existing tests to confirm no regressions**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest tests/adapters/test_local_json_repository.py -v
```

Expected: all tests PASS (fixture now has new fields but `_parse` still reads only the old fields — that gets fixed in Task 3).

- [ ] **Step 4: Commit**

```bash
git add domain/models/pokemon.py tests/adapters/fixtures/test_pokemon_data.json
git commit -m "feat(domain): add is_final_evolution, abilities, dream_ability, mega_forms to Pokemon"
```

---

## Task 3: LocalJsonRepository — parse new fields + sorted fuzzy_match

**Files:**
- Modify: `adapters/local_json_repository.py`
- Modify: `tests/adapters/test_local_json_repository.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/adapters/test_local_json_repository.py`:

```python
class TestNewFields:
    def test_is_final_evolution_parsed(self, repo):
        p = repo.get_by_id(445)
        assert p.is_final_evolution is True

    def test_is_final_evolution_false_default(self, repo):
        p = repo.get_by_id(25)
        assert p.is_final_evolution is False

    def test_abilities_parsed(self, repo):
        p = repo.get_by_id(445)
        assert len(p.abilities) == 2
        assert p.abilities[0]["name_en"] == "Sand Veil"

    def test_dream_ability_none_when_absent(self, repo):
        p = repo.get_by_id(445)
        assert p.dream_ability is None

    def test_dream_ability_parsed(self, repo):
        p = repo.get_by_id(25)
        assert p.dream_ability is not None
        assert p.dream_ability["name_en"] == "Lightning Rod"

    def test_mega_forms_parsed(self, repo):
        p = repo.get_by_id(445)
        assert len(p.mega_forms) == 1
        assert p.mega_forms[0]["suffix"] == "mega"


class TestFuzzyMatchSorting:
    def test_final_evolution_sorts_first(self, repo):
        results = repo.fuzzy_match("a")
        final_idxs = [i for i, p in enumerate(results) if p.is_final_evolution]
        non_final_idxs = [i for i, p in enumerate(results) if not p.is_final_evolution]
        if final_idxs and non_final_idxs:
            assert max(final_idxs) < min(non_final_idxs)
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest tests/adapters/test_local_json_repository.py::TestNewFields -v
```

Expected: FAIL with `AttributeError: 'Pokemon' object has no attribute 'is_final_evolution'` or similar (because `_parse` doesn't read the new fields yet).

- [ ] **Step 3: Update `_parse` and `fuzzy_match` in `adapters/local_json_repository.py`**

```python
import json
from pathlib import Path
from domain.models.pokemon import Pokemon
from domain.models.stats import StatSet
from domain.repositories.abstract import AbstractPokeRepository
from shared.exceptions import PokemonNotFoundError


def _parse(raw: dict) -> Pokemon:
    s = raw["base_stats"]
    return Pokemon(
        id=raw["id"],
        name_en=raw["name_en"],
        name_zh=raw["name_zh"],
        name_ja=raw["name_ja"],
        types=raw["types"],
        base_stats=StatSet(
            hp=s["hp"], attack=s["attack"], defense=s["defense"],
            sp_attack=s["sp_attack"], sp_defense=s["sp_defense"], speed=s["speed"],
        ),
        sprite_url=raw.get("sprite_path", ""),
        is_final_evolution=raw.get("is_final_evolution", False),
        abilities=raw.get("abilities", []),
        dream_ability=raw.get("dream_ability", None),
        mega_forms=raw.get("mega_forms", []),
    )


class LocalJsonRepository(AbstractPokeRepository):

    def __init__(self, json_path: Path) -> None:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        self._by_id:  dict[int, Pokemon] = {}
        self._by_en:  dict[str, Pokemon] = {}
        self._by_zh:  dict[str, Pokemon] = {}
        self._by_ja:  dict[str, Pokemon] = {}
        self._all:    list[Pokemon]      = []
        for i, raw in enumerate(data):
            try:
                p = _parse(raw)
            except (KeyError, TypeError) as exc:
                raise ValueError(f"Bad record at index {i}: {exc}") from exc
            self._by_id[p.id]              = p
            self._by_en[p.name_en.lower()] = p
            self._by_zh[p.name_zh]         = p
            self._by_ja[p.name_ja]         = p
            self._all.append(p)

    def get_by_id(self, pokemon_id: int, name_zh: str = "", name_ja: str = "") -> Pokemon:
        if pokemon_id not in self._by_id:
            raise PokemonNotFoundError(pokemon_id)
        return self._by_id[pokemon_id]

    def get_by_name(self, name: str) -> Pokemon:
        key = name.strip()
        p = self._by_en.get(key.lower()) or self._by_zh.get(key) or self._by_ja.get(key)
        if p is None:
            raise PokemonNotFoundError(name)
        return p

    def search(self, query: str) -> list[Pokemon]:
        return self.fuzzy_match(query)

    def fuzzy_match(self, query: str) -> list[Pokemon]:
        q = query.strip()
        if not q:
            return []
        ql = q.lower()
        matches = [
            p for p in self._all
            if ql in p.name_en.lower() or q in p.name_zh or q in p.name_ja
        ]
        return sorted(matches, key=lambda p: (not p.is_final_evolution, p.id))
```

- [ ] **Step 4: Run all repository tests**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest tests/adapters/test_local_json_repository.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add adapters/local_json_repository.py tests/adapters/test_local_json_repository.py
git commit -m "feat(adapter): parse new Pokemon fields and sort fuzzy_match by final evolution"
```

---

## Task 4: Type chart — 18×18 effectiveness matrix

**Files:**
- Create: `shared/type_chart.py`
- Create: `tests/shared/test_type_chart.py`

- [ ] **Step 1: Write failing tests**

Create `tests/shared/test_type_chart.py`:

```python
import pytest
from shared.type_chart import get_effectiveness, get_matchups


class TestGetEffectiveness:
    def test_neutral(self):
        assert get_effectiveness(["normal"], ["normal"]) == 1.0

    def test_immune(self):
        assert get_effectiveness(["normal"], ["ghost"]) == 0.0

    def test_super_effective(self):
        assert get_effectiveness(["fire"], ["grass"]) == 2.0

    def test_not_very_effective(self):
        assert get_effectiveness(["fire"], ["water"]) == 0.5

    def test_dual_type_multiplicative(self):
        # Rock vs Fire/Flying = 2× (rock>fire) × 2× (rock>flying) = 4×
        assert get_effectiveness(["rock"], ["fire", "flying"]) == 4.0

    def test_ground_vs_flying_immune(self):
        # Ground vs Flying = 0×
        assert get_effectiveness(["ground"], ["flying"]) == 0.0

    def test_ground_vs_fire_flying(self):
        # Ground vs Fire/Flying: 2× (vs fire) × 0× (vs flying) = 0×
        assert get_effectiveness(["ground"], ["fire", "flying"]) == 0.0


class TestGetMatchups:
    def test_charizard_rock_4x(self):
        m = get_matchups(["fire", "flying"])
        assert m["rock"] == 4.0

    def test_charizard_ground_immune(self):
        m = get_matchups(["fire", "flying"])
        assert m["ground"] == 0.0

    def test_charizard_water_2x(self):
        m = get_matchups(["fire", "flying"])
        assert m["water"] == 2.0

    def test_charizard_electric_2x(self):
        m = get_matchups(["fire", "flying"])
        assert m["electric"] == 2.0

    def test_charizard_fire_half(self):
        m = get_matchups(["fire", "flying"])
        assert m["fire"] == 0.5

    def test_returns_all_18_types(self):
        m = get_matchups(["normal"])
        assert len(m) == 18

    def test_matchups_grouping_weaknesses(self):
        m = get_matchups(["fire", "flying"])
        weaknesses = {t for t, v in m.items() if v > 1}
        assert "rock" in weaknesses
        assert "water" in weaknesses
        assert "electric" in weaknesses

    def test_matchups_grouping_immunities(self):
        m = get_matchups(["fire", "flying"])
        immunities = {t for t, v in m.items() if v == 0}
        assert "ground" in immunities
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest tests/shared/test_type_chart.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'shared.type_chart'`

- [ ] **Step 3: Create `shared/type_chart.py`**

```python
# shared/type_chart.py
# Generation VIII type effectiveness chart (18×18).
# Keys are lowercase English type names matching PokéAPI slugs.

_CHART: dict[str, dict[str, float]] = {
    "normal":   {"rock": 0.5, "ghost": 0.0, "steel": 0.5},
    "fire":     {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0,
                 "bug": 2.0, "rock": 0.5, "dragon": 0.5, "steel": 2.0},
    "water":    {"fire": 2.0, "water": 0.5, "grass": 0.5,
                 "ground": 2.0, "rock": 2.0, "dragon": 0.5},
    "electric": {"water": 2.0, "electric": 0.5, "grass": 0.5,
                 "ground": 0.0, "flying": 2.0, "dragon": 0.5},
    "grass":    {"fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5,
                 "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0,
                 "dragon": 0.5, "steel": 0.5},
    "ice":      {"water": 0.5, "grass": 2.0, "ice": 0.5,
                 "ground": 2.0, "flying": 2.0, "dragon": 2.0, "steel": 0.5},
    "fighting": {"normal": 2.0, "ice": 2.0, "rock": 2.0, "dark": 2.0,
                 "steel": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5,
                 "bug": 0.5, "fairy": 0.5, "ghost": 0.0},
    "poison":   {"grass": 2.0, "fairy": 2.0, "poison": 0.5, "ground": 0.5,
                 "rock": 0.5, "ghost": 0.5, "steel": 0.0},
    "ground":   {"fire": 2.0, "electric": 2.0, "poison": 2.0, "rock": 2.0,
                 "steel": 2.0, "grass": 0.5, "bug": 0.5, "flying": 0.0},
    "flying":   {"grass": 2.0, "fighting": 2.0, "bug": 2.0,
                 "electric": 0.5, "rock": 0.5, "steel": 0.5},
    "psychic":  {"fighting": 2.0, "poison": 2.0, "psychic": 0.5,
                 "steel": 0.5, "dark": 0.0},
    "bug":      {"grass": 2.0, "psychic": 2.0, "dark": 2.0,
                 "fire": 0.5, "fighting": 0.5, "flying": 0.5,
                 "ghost": 0.5, "steel": 0.5, "fairy": 0.5, "poison": 0.5},
    "rock":     {"flying": 2.0, "bug": 2.0, "fire": 2.0, "ice": 2.0,
                 "fighting": 0.5, "ground": 0.5, "steel": 0.5},
    "ghost":    {"normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5},
    "dragon":   {"dragon": 2.0, "steel": 0.5, "fairy": 0.0},
    "dark":     {"ghost": 2.0, "psychic": 2.0, "dark": 0.5,
                 "fighting": 0.5, "fairy": 0.5},
    "steel":    {"ice": 2.0, "rock": 2.0, "fairy": 2.0,
                 "fire": 0.5, "water": 0.5, "electric": 0.5, "steel": 0.5},
    "fairy":    {"fighting": 2.0, "dragon": 2.0, "dark": 2.0,
                 "fire": 0.5, "poison": 0.5, "steel": 0.5},
}

ALL_TYPES: list[str] = list(_CHART.keys())


def get_effectiveness(attacker_types: list[str], defender_types: list[str]) -> float:
    mult = 1.0
    for atk in attacker_types:
        for def_ in defender_types:
            mult *= _CHART.get(atk, {}).get(def_, 1.0)
    return mult


def get_matchups(defender_types: list[str]) -> dict[str, float]:
    return {atk: get_effectiveness([atk], defender_types) for atk in ALL_TYPES}
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest tests/shared/test_type_chart.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add shared/type_chart.py tests/shared/test_type_chart.py
git commit -m "feat(shared): add type_chart with 18x18 Gen VIII effectiveness matrix"
```

---

## Task 5: i18n — section-header and UI-label keys

**Files:**
- Modify: `shared/i18n/zh.json`
- Modify: `shared/i18n/en.json`
- Modify: `shared/i18n/ja.json`

- [ ] **Step 1: Add new keys to `zh.json`**

Add these key-value pairs inside the top-level JSON object (before the closing `}`), after the existing `"types"` block:

```json
  "detail_abilities": "特性",
  "detail_dream_ability_prefix": "夢：",
  "detail_type_matchup": "屬性相性",
  "detail_weaknesses": "弱點",
  "detail_resistances": "抵抗",
  "detail_immunities": "免疫",
  "detail_mega": "Mega 進化",
  "detail_ability_hint": "點擊特性名稱查看說明",
  "selector_placeholder": "輸入名稱搜尋...",
  "selector_clear": "清除選擇",
  "nature_grid_header": "性格（點選格子）",
  "nature_grid_clear": "清除性格"
```

- [ ] **Step 2: Add new keys to `en.json`**

```json
  "detail_abilities": "Abilities",
  "detail_dream_ability_prefix": "Hidden: ",
  "detail_type_matchup": "Type Matchup",
  "detail_weaknesses": "Weaknesses",
  "detail_resistances": "Resistances",
  "detail_immunities": "Immunities",
  "detail_mega": "Mega Evolution",
  "detail_ability_hint": "Click an ability name to see its description",
  "selector_placeholder": "Type to search...",
  "selector_clear": "Clear selection",
  "nature_grid_header": "Nature (select a cell)",
  "nature_grid_clear": "Clear nature"
```

- [ ] **Step 3: Add new keys to `ja.json`**

```json
  "detail_abilities": "特性",
  "detail_dream_ability_prefix": "夢：",
  "detail_type_matchup": "タイプ相性",
  "detail_weaknesses": "弱点",
  "detail_resistances": "耐性",
  "detail_immunities": "無効",
  "detail_mega": "メガシンカ",
  "detail_ability_hint": "特性名をクリックして説明を表示",
  "selector_placeholder": "名前を入力して検索...",
  "selector_clear": "選択解除",
  "nature_grid_header": "せいかく（セルを選択）",
  "nature_grid_clear": "せいかく解除"
```

- [ ] **Step 4: Verify JSON is valid**

```bash
cd /Users/wayneho/poke-calc
python3 -c "import json; [json.load(open(f'shared/i18n/{l}.json')) for l in ('zh','en','ja')]; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Run translator tests**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest tests/shared/test_translator.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add shared/i18n/zh.json shared/i18n/en.json shared/i18n/ja.json
git commit -m "feat(i18n): add section-header keys for v2 UI components"
```

---

## Task 6: build_data.py — abilities and evolution chain

**Files:**
- Modify: `scripts/build_data.py`

- [ ] **Step 1: Add helper functions and integrate into `build()`**

Replace `scripts/build_data.py` entirely with:

```python
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


def _fetch_mega_forms(species_data: dict) -> list[dict]:
    mega_forms = []
    for variety in species_data.get("varieties", []):
        name = variety["pokemon"]["name"]
        if "mega" not in name:
            continue
        resp = requests.get(variety["pokemon"]["url"], timeout=10)
        resp.raise_for_status()
        raw = resp.json()

        # Determine suffix (e.g. "mega-x", "mega-y", "mega")
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

        # Try HOME sprite, fall back to official-artwork
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

        # Build localized names (use species names + suffix label)
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
```

- [ ] **Step 2: Verify import is clean**

```bash
cd /Users/wayneho/poke-calc
python3 -c "from scripts.build_data import build, download_type_sprites; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/build_data.py
git commit -m "feat(build): fetch abilities, evolution chain, Mega forms, and type sprites"
```

---

## Task 7: Streamlit components package

**Files:**
- Create: `interfaces/streamlit/components/__init__.py`
- Create: `interfaces/streamlit/components/type_badge.py`

- [ ] **Step 1: Create the package marker**

Create `interfaces/streamlit/components/__init__.py` as an empty file:

```python
```

- [ ] **Step 2: Create `type_badge.py`**

```python
# interfaces/streamlit/components/type_badge.py
import base64
from pathlib import Path
from shared.config import TYPE_SPRITES_DIR

_TYPE_COLORS: dict[str, str] = {
    "normal":   "#A8A77A", "fire":     "#EE8130", "water":    "#6390F0",
    "electric": "#F7D02C", "grass":    "#7AC74C", "ice":      "#96D9D6",
    "fighting": "#C22E28", "poison":   "#A33EA1", "ground":   "#E2BF65",
    "flying":   "#A98FF3", "psychic":  "#F95587", "bug":      "#A6B91A",
    "rock":     "#B6A136", "ghost":    "#735797", "dragon":   "#6F35FC",
    "dark":     "#705746", "steel":    "#B7B7CE", "fairy":    "#D685AD",
}

_DARK_TEXT_TYPES = {"electric", "ice", "ground", "steel"}


def type_badge_html(type_en: str, type_name: str) -> str:
    """Return an HTML <span> badge for a single type, with optional embedded PNG."""
    color = _TYPE_COLORS.get(type_en, "#888888")
    text_color = "#333333" if type_en in _DARK_TEXT_TYPES else "#ffffff"
    img_tag = ""
    sprite_path: Path = TYPE_SPRITES_DIR / f"{type_en}.png"
    if sprite_path.exists():
        b64 = base64.b64encode(sprite_path.read_bytes()).decode()
        img_tag = (
            f'<img src="data:image/png;base64,{b64}" '
            f'style="width:16px;height:16px;vertical-align:middle;'
            f'border-radius:2px;margin-right:3px;image-rendering:pixelated">'
        )
    return (
        f'<span style="display:inline-flex;align-items:center;background:{color};'
        f'border-radius:4px;padding:2px 8px;font-size:11px;font-weight:bold;'
        f'color:{text_color};font-family:monospace;margin:2px">'
        f"{img_tag}{type_name}</span>"
    )


def types_html(types: tuple[str, ...], translator) -> str:
    """Return concatenated badge HTML for a list of types."""
    return "".join(type_badge_html(tp, translator.type_name(tp)) for tp in types)
```

- [ ] **Step 3: Verify import**

```bash
cd /Users/wayneho/poke-calc
python3 -c "from interfaces.streamlit.components.type_badge import type_badge_html; print(type_badge_html('fire', '火')[:30])"
```

Expected: starts with `<span style=`

- [ ] **Step 4: Commit**

```bash
git add interfaces/streamlit/components/__init__.py interfaces/streamlit/components/type_badge.py
git commit -m "feat(components): add type_badge HTML helper"
```

---

## Task 8: pokemon_selector component

**Files:**
- Create: `interfaces/streamlit/components/pokemon_selector.py`

- [ ] **Step 1: Create `pokemon_selector.py`**

```python
# interfaces/streamlit/components/pokemon_selector.py
import streamlit as st
from domain.models.pokemon import Pokemon
from adapters.local_json_repository import LocalJsonRepository
from interfaces.streamlit.components.type_badge import types_html
from shared.config import SPRITES_DIR


def pokemon_selector(
    key: str,
    label: str,
    repo: LocalJsonRepository,
    lang: str,
    translator,
) -> Pokemon | None:
    """
    Fuzzy-search Pokémon selector.

    Manages its own state in st.session_state under keys prefixed with `key`.
    Returns the currently selected Pokemon, or None.
    """
    query_key    = f"_ps_query_{key}"
    selected_key = f"_ps_sel_{key}"

    # ── Confirmed selection ──────────────────────────────────────────────────
    if st.session_state.get(selected_key) is not None:
        try:
            p = repo.get_by_id(st.session_state[selected_key])
        except Exception:
            st.session_state[selected_key] = None
            st.rerun()
            return None

        name = {"zh": p.name_zh, "en": p.name_en.title(), "ja": p.name_ja}[lang]
        col_img, col_info, col_btn = st.columns([1, 5, 1])
        with col_img:
            sprite = SPRITES_DIR / f"{p.id}.png"
            if sprite.exists():
                st.image(str(sprite), width=60)
        with col_info:
            st.markdown(f"**{name}**")
            badge_html = types_html(p.types, translator)
            st.markdown(badge_html, unsafe_allow_html=True)
        with col_btn:
            if st.button("✕", key=f"_ps_clear_{key}", help=translator("selector_clear")):
                st.session_state[selected_key] = None
                st.session_state[query_key] = ""
                st.rerun()
        return p

    # ── Search input ─────────────────────────────────────────────────────────
    query = st.text_input(
        label,
        key=query_key,
        placeholder=translator("selector_placeholder"),
    )

    if query:
        candidates = repo.fuzzy_match(query)[:8]
        for p in candidates:
            name = {"zh": p.name_zh, "en": p.name_en.title(), "ja": p.name_ja}[lang]
            col_img, col_name, col_types = st.columns([1, 3, 3])
            with col_img:
                sprite = SPRITES_DIR / f"{p.id}.png"
                if sprite.exists():
                    st.image(str(sprite), width=40)
            with col_name:
                if st.button(name, key=f"_ps_btn_{key}_{p.id}", use_container_width=True):
                    st.session_state[selected_key] = p.id
                    st.session_state[query_key] = ""
                    st.rerun()
            with col_types:
                badge_html = types_html(p.types, translator)
                st.markdown(badge_html, unsafe_allow_html=True)

    return None
```

- [ ] **Step 2: Verify import**

```bash
cd /Users/wayneho/poke-calc
python3 -c "from interfaces.streamlit.components.pokemon_selector import pokemon_selector; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add interfaces/streamlit/components/pokemon_selector.py
git commit -m "feat(components): add pokemon_selector fuzzy-search widget"
```

---

## Task 9: nature_selector component

**Files:**
- Create: `interfaces/streamlit/components/nature_selector.py`

- [ ] **Step 1: Create `nature_selector.py`**

```python
# interfaces/streamlit/components/nature_selector.py
import streamlit as st
from domain.models.nature import ALL_NATURES, BattleStat, Nature

STATS_ORDER = [
    BattleStat.ATTACK,
    BattleStat.DEFENSE,
    BattleStat.SP_ATTACK,
    BattleStat.SP_DEFENSE,
    BattleStat.SPEED,
]

# Neutral natures appear on the diagonal in order of STATS_ORDER rows
_NEUTRAL_NATURES: list[Nature] = [n for n in ALL_NATURES if n.boosted is None]

# Quick lookup: (boosted, reduced) -> Nature for non-neutral natures
_GRID: dict[tuple, Nature] = {
    (n.boosted, n.reduced): n for n in ALL_NATURES if n.boosted is not None
}

_STAT_LABELS: dict[str, list[str]] = {
    "zh": ["攻擊", "防禦", "特攻", "特防", "速度"],
    "en": ["Atk",  "Def",  "SpA",  "SpD",  "Spe"],
    "ja": ["こうげき", "ぼうぎょ", "とくこう", "とくぼう", "すばやさ"],
}


def _cell_nature(row: int, col: int) -> Nature:
    if row == col:
        return _NEUTRAL_NATURES[row]
    return _GRID[(STATS_ORDER[row], STATS_ORDER[col])]


def nature_selector(key: str, lang: str, translator) -> str | None:
    """
    5×5 nature grid selector.

    Returns the selected nature's English name, or None if nothing selected.
    Diagonal cells (neutral natures) are rendered as disabled buttons.
    """
    selected_key = f"_nat_{key}"
    current: str | None = st.session_state.get(selected_key)

    stat_labels = _STAT_LABELS.get(lang, _STAT_LABELS["zh"])

    # Column headers (reduced stat)
    header_cols = st.columns([0.6] + [1] * 5)
    header_cols[0].markdown("")
    for j, label in enumerate(stat_labels):
        header_cols[j + 1].markdown(
            f'<div style="text-align:center;font-size:10px;color:#888">{label}↓</div>',
            unsafe_allow_html=True,
        )

    for row in range(5):
        row_cols = st.columns([0.6] + [1] * 5)
        row_cols[0].markdown(
            f'<div style="font-size:10px;color:#888;padding-top:6px">{stat_labels[row]}↑</div>',
            unsafe_allow_html=True,
        )
        for col in range(5):
            nature = _cell_nature(row, col)
            nat_name = {"zh": nature.name_zh, "en": nature.name_en, "ja": nature.name_ja}[lang]
            is_neutral = (row == col)
            is_selected = (current == nature.name_en)

            with row_cols[col + 1]:
                if is_neutral:
                    st.button(
                        nat_name,
                        key=f"_nat_{key}_{row}_{col}",
                        disabled=True,
                        use_container_width=True,
                    )
                else:
                    btn_type = "primary" if is_selected else "secondary"
                    if st.button(
                        nat_name,
                        key=f"_nat_{key}_{row}_{col}",
                        type=btn_type,
                        use_container_width=True,
                        help=f"+{stat_labels[row]} / -{stat_labels[col]}",
                    ):
                        if is_selected:
                            st.session_state[selected_key] = None
                        else:
                            st.session_state[selected_key] = nature.name_en
                        st.rerun()

    if current:
        if st.button(translator("nature_grid_clear"), key=f"_nat_clear_{key}"):
            st.session_state[selected_key] = None
            st.rerun()

    return current
```

- [ ] **Step 2: Verify import**

```bash
cd /Users/wayneho/poke-calc
python3 -c "from interfaces.streamlit.components.nature_selector import nature_selector; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add interfaces/streamlit/components/nature_selector.py
git commit -m "feat(components): add nature_selector 5x5 grid widget"
```

---

## Task 10: Search tab redesign

**Files:**
- Modify: `interfaces/streamlit/app.py` (Search tab section only)

The search tab section (lines `# ── Search Tab ──` through the end of the `with tab_search:` block) needs to be replaced. The new version uses `pokemon_selector` and shows a rich detail card when a Pokémon is selected.

- [ ] **Step 1: Replace the Search tab block in `app.py`**

Find the section:
```python
# ── Search Tab ──────────────────────────────────────────────────────────────
with tab_search:
```

Replace everything inside that `with tab_search:` block with:

```python
# ── Search Tab ──────────────────────────────────────────────────────────────
with tab_search:
    from interfaces.streamlit.components.pokemon_selector import pokemon_selector
    from interfaces.streamlit.components.type_badge import type_badge_html, types_html
    from shared.type_chart import get_matchups

    st.header(t("search_header"))
    selected_mon = pokemon_selector("search", t("search_input_label"), svc["local"], lang, t)

    if selected_mon is not None:
        p = selected_mon
        st.divider()
        col_img, col_info = st.columns([1, 3])
        with col_img:
            sprite = SPRITES_DIR / f"{p.id}.png"
            if sprite.exists():
                st.image(str(sprite), width=160)
        with col_info:
            st.subheader(f"{p.name_zh}　{p.name_en.title()}　{p.name_ja}")
            badge_html = types_html(p.types, t)
            st.markdown(badge_html, unsafe_allow_html=True)
            b = p.base_stats
            st.table({
                t("stat_col_name"):  t.strings("stat_names"),
                t("stat_col_value"): [b.hp, b.attack, b.defense, b.sp_attack, b.sp_defense, b.speed],
            })

        # ── Type matchup ────────────────────────────────────────────────────
        st.markdown(f"**{t('detail_type_matchup')}**")
        matchups = get_matchups(list(p.types))
        weaknesses    = sorted([(tp, v) for tp, v in matchups.items() if v > 1],  key=lambda x: -x[1])
        resistances   = sorted([(tp, v) for tp, v in matchups.items() if 0 < v < 1], key=lambda x: x[1])
        immunities    = [(tp, v) for tp, v in matchups.items() if v == 0]

        if weaknesses:
            st.markdown(f"*{t('detail_weaknesses')}*")
            html_parts = []
            cur_mult = None
            for tp, v in weaknesses:
                if v != cur_mult:
                    cur_mult = v
                    mult_str = "4×" if v == 4.0 else "2×"
                    html_parts.append(f'<span style="font-size:11px;color:#f38ba8;margin:0 4px">{mult_str}</span>')
                html_parts.append(type_badge_html(tp, t.type_name(tp)))
            st.markdown("".join(html_parts), unsafe_allow_html=True)

        if resistances:
            st.markdown(f"*{t('detail_resistances')}*")
            html_parts = []
            cur_mult = None
            for tp, v in resistances:
                if v != cur_mult:
                    cur_mult = v
                    mult_str = "¼×" if v == 0.25 else "½×"
                    html_parts.append(f'<span style="font-size:11px;color:#89b4fa;margin:0 4px">{mult_str}</span>')
                html_parts.append(type_badge_html(tp, t.type_name(tp)))
            st.markdown("".join(html_parts), unsafe_allow_html=True)

        if immunities:
            st.markdown(f"*{t('detail_immunities')}*")
            html_parts = ['<span style="font-size:11px;color:#a6adc8;margin:0 4px">0×</span>']
            for tp, _ in immunities:
                html_parts.append(type_badge_html(tp, t.type_name(tp)))
            st.markdown("".join(html_parts), unsafe_allow_html=True)

        # ── Abilities ────────────────────────────────────────────────────────
        if p.abilities or p.dream_ability:
            st.divider()
            st.markdown(f"**{t('detail_abilities')}**")
            abil_hint_key = f"_abil_desc_search_{p.id}"

            ability_cols_html = []
            all_abilities = list(p.abilities)
            if p.dream_ability:
                all_abilities.append({**p.dream_ability, "_is_dream": True})

            for i, ab in enumerate(all_abilities):
                is_dream = ab.get("_is_dream", False)
                ab_name = {"zh": ab.get("name_zh", ""), "en": ab.get("name_en", ""), "ja": ab.get("name_ja", "")}[lang]
                prefix = t("detail_dream_ability_prefix") if is_dream else ""
                label = f"{prefix}{ab_name}"
                if st.button(label, key=f"_abil_btn_search_{p.id}_{i}"):
                    ab_desc = {"zh": ab.get("desc_zh", ""), "en": ab.get("desc_en", ""), "ja": ab.get("desc_ja", "")}[lang]
                    st.session_state[abil_hint_key] = f"**{label}**\n\n{ab_desc}"

            if abil_hint_key in st.session_state:
                st.info(st.session_state[abil_hint_key])
            else:
                st.caption(t("detail_ability_hint"))

        # ── Mega forms ──────────────────────────────────────────────────────
        if p.mega_forms:
            st.divider()
            st.markdown(f"**{t('detail_mega')}**")
            for mega in p.mega_forms:
                with st.expander(mega.get("name_zh" if lang == "zh" else ("name_en" if lang == "en" else "name_ja"), mega.get("name_en", "Mega"))):
                    mcol_img, mcol_info = st.columns([1, 3])
                    with mcol_img:
                        mega_sprite = MEGA_SPRITES_DIR / f"{p.id}-{mega['suffix']}.png"
                        if mega_sprite.exists():
                            st.image(str(mega_sprite), width=120)
                    with mcol_info:
                        mega_types = mega.get("types", [])
                        if mega_types:
                            st.markdown(types_html(tuple(mega_types), t), unsafe_allow_html=True)
                        ms = mega.get("base_stats", {})
                        orig = p.base_stats
                        orig_vals = {"hp": orig.hp, "attack": orig.attack, "defense": orig.defense,
                                     "sp_attack": orig.sp_attack, "sp_defense": orig.sp_defense, "speed": orig.speed}
                        stat_names = t.strings("stat_names")
                        stat_keys  = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]
                        rows_data = []
                        for sname, skey in zip(stat_names, stat_keys):
                            mv = ms.get(skey, 0)
                            ov = orig_vals.get(skey, 0)
                            marker = " ▲" if mv > ov else ""
                            rows_data.append({"stat": sname, "mega": f"{mv}{marker}", "base": ov})
                        st.dataframe(rows_data, use_container_width=True, hide_index=True)

                    mega_ability = mega.get("ability", {})
                    if mega_ability:
                        ab_name = {"zh": mega_ability.get("name_zh", ""), "en": mega_ability.get("name_en", ""), "ja": mega_ability.get("name_ja", "")}[lang]
                        abil_key = f"_mega_abil_desc_{p.id}_{mega['suffix']}"
                        if st.button(ab_name, key=f"_mega_abil_btn_{p.id}_{mega['suffix']}"):
                            desc = {"zh": mega_ability.get("desc_zh", ""), "en": mega_ability.get("desc_en", ""), "ja": mega_ability.get("desc_ja", "")}[lang]
                            st.session_state[abil_key] = f"**{ab_name}**\n\n{desc}"
                        if abil_key in st.session_state:
                            st.info(st.session_state[abil_key])
```

Also add `MEGA_SPRITES_DIR` to the import at the top of `app.py`:

```python
from shared.config import DATA_JSON_PATH, SPRITES_DIR, MEGA_SPRITES_DIR
```

- [ ] **Step 2: Run the full test suite to check no regressions**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest -v
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add interfaces/streamlit/app.py
git commit -m "feat(ui): redesign Search tab with pokemon_selector and rich detail card"
```

---

## Task 11: Speed and Survival tabs redesign

**Files:**
- Modify: `interfaces/streamlit/app.py` (Speed and Survival tab sections)

- [ ] **Step 1: Replace the Speed tab block**

Find the section `# ── Speed Tab ──` and replace the entire `with tab_speed:` block with:

```python
# ── Speed Tab ────────────────────────────────────────────────────────────────
with tab_speed:
    from interfaces.streamlit.components.pokemon_selector import pokemon_selector
    from interfaces.streamlit.components.nature_selector import nature_selector

    st.header(t("speed_header"))
    st.caption(t("speed_caption"))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(t("speed_my_mon"))
        my_mon = pokemon_selector("speed_my", t("speed_name_label"), svc["local"], lang, t)
        st.markdown(f"*{t('nature_grid_header')}*")
        my_nature_en = nature_selector("speed_my", lang, t)

    with col2:
        st.subheader(t("speed_tgt_mon"))
        tgt_mon = pokemon_selector("speed_tgt", t("speed_name_label"), svc["local"], lang, t)
        st.markdown(f"*{t('nature_grid_header')}*")
        tgt_nature_en = nature_selector("speed_tgt", lang, t)
        tgt_sp = int(st.number_input(
            t("speed_tgt_sp_label"), min_value=0, max_value=32, value=0, step=1,
            key="speed_tgt_sp",
        ))

    # Auto-calculate when both Pokémon are selected
    if my_mon is not None and tgt_mon is not None:
        try:
            my_nature  = NatureRegistry.get_by_name(my_nature_en) if my_nature_en else NatureRegistry.get_by_name("Hardy")
            tgt_nature = NatureRegistry.get_by_name(tgt_nature_en) if tgt_nature_en else NatureRegistry.get_by_name("Hardy")
            my_mon_with_nature  = dataclasses.replace(my_mon,  nature=my_nature)
            tgt_mon_with_nature = dataclasses.replace(tgt_mon, nature=tgt_nature)

            tgt_preview = svc["calc"].calc_stat(
                tgt_mon_with_nature.base_stats.speed, tgt_sp, tgt_mon_with_nature.nature, BattleStat.SPEED
            )
            my_preview = svc["calc"].calc_stat(
                my_mon_with_nature.base_stats.speed, 0, my_mon_with_nature.nature, BattleStat.SPEED
            )

            result = svc["speed"].min_sp_to_outspeed(my_mon_with_nature, tgt_mon_with_nature, target_sp=tgt_sp)

            st.divider()
            preview_cols = st.columns(2)
            preview_cols[0].caption(t("speed_my_preview").format(speed=my_preview))
            preview_cols[1].caption(t("speed_tgt_preview").format(speed=tgt_preview))

            if result is None:
                st.error(t("speed_cannot_outspeed").format(
                    my=my_mon_with_nature.name_zh, tgt=tgt_mon_with_nature.name_zh
                ))
            else:
                st.success(t("speed_success").format(sp=result.sp_needed))
                metric_cols = st.columns(3)
                metric_cols[0].metric(t("speed_metric_sp"), result.sp_needed)
                metric_cols[1].metric(t("speed_metric_speed").format(name=my_mon_with_nature.name_zh), result.my_speed)
                metric_cols[2].metric(t("speed_metric_speed").format(name=tgt_mon_with_nature.name_zh), result.target_speed)
        except Exception:
            pass
```

- [ ] **Step 2: Replace the Survival tab block**

Find the section `# ── Survival Tab ──` and replace the entire `with tab_survival:` block with:

```python
# ── Survival Tab ─────────────────────────────────────────────────────────────
with tab_survival:
    from interfaces.streamlit.components.pokemon_selector import pokemon_selector
    from interfaces.streamlit.components.nature_selector import nature_selector

    st.header(t("surv_header"))
    st.caption(t("surv_caption"))

    col_mon, col_atk = st.columns(2)

    with col_mon:
        st.subheader(t("surv_my_mon"))
        surv_mon = pokemon_selector("surv_mon", t("surv_name_label"), svc["local"], lang, t)
        st.markdown(f"*{t('nature_grid_header')}*")
        surv_nature_en = nature_selector("surv_mon", lang, t)

    with col_atk:
        st.subheader(t("surv_atk_params"))
        power        = st.number_input(t("surv_power_label"), min_value=1, max_value=250, value=120, key="surv_power")
        attacker_atk = st.number_input(t("surv_atk_label"), min_value=1, max_value=999, value=200, key="surv_atk")
        is_physical  = st.radio(t("surv_cat_label"), [t("surv_cat_physical"), t("surv_cat_special")], key="surv_cat") == t("surv_cat_physical")
        type_mult    = st.select_slider(
            t("surv_mult_label"),
            options=[0.25, 0.5, 1.0, 2.0, 4.0],
            value=1.0,
            key="surv_mult",
        )

    # Auto-calculate when Pokémon is selected
    if surv_mon is not None:
        try:
            surv_nature = NatureRegistry.get_by_name(surv_nature_en) if surv_nature_en else NatureRegistry.get_by_name("Hardy")
            mon = dataclasses.replace(surv_mon, nature=surv_nature)
            attack = AttackInput(
                power=int(power),
                attacker_atk=int(attacker_atk),
                is_physical=is_physical,
                type_multiplier=float(type_mult),
            )
            prefer_hp, prefer_def = svc["survival"].optimize(mon, attack)

            st.divider()
            if not prefer_hp.survived:
                st.error(t("surv_impossible"))
            else:
                st.success(t("surv_success").format(sp=prefer_hp.total_sp))
                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader(t("surv_plan_hp"))
                    st.metric(t("surv_metric_sp_hp"), prefer_hp.sp_hp)
                    st.metric(t("surv_metric_sp_def"), prefer_hp.sp_def)
                    st.metric(t("surv_metric_final_hp"), prefer_hp.final_hp)
                    st.metric(t("surv_metric_final_def"), prefer_hp.final_def)
                    st.caption(t("surv_metric_total").format(sp=prefer_hp.total_sp))
                with col_b:
                    st.subheader(t("surv_plan_def"))
                    st.metric(t("surv_metric_sp_hp"), prefer_def.sp_hp)
                    st.metric(t("surv_metric_sp_def"), prefer_def.sp_def)
                    st.metric(t("surv_metric_final_hp"), prefer_def.final_hp)
                    st.metric(t("surv_metric_final_def"), prefer_def.final_def)
                    st.caption(t("surv_metric_total").format(sp=prefer_def.total_sp))
        except Exception:
            pass
```

- [ ] **Step 3: Run the full test suite**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add interfaces/streamlit/app.py
git commit -m "feat(ui): replace Speed and Survival tabs with pokemon_selector and nature_selector; auto-calculate"
```

---

## Task 12: Trigger data rebuild (manual step)

This task is manual and only needs to be done once. The previous `pokemon_data.json` does not contain `abilities`, `is_final_evolution`, or `mega_forms`. The resumption logic in `build_data.py` now checks for the presence of the `"abilities"` key, so running the build script will re-fetch all records.

- [ ] **Step 1: Run the build script**

```bash
cd /Users/wayneho/poke-calc
python3 scripts/build_data.py
```

Expected: progress logs for all 1025 Pokémon. This takes ~30–60 minutes due to PokéAPI rate limits.

The script is resumable: if interrupted, re-run it and it will skip entries that already have `"abilities"` in the JSON.

- [ ] **Step 2: Verify the rebuilt JSON has new fields**

```bash
cd /Users/wayneho/poke-calc
python3 -c "
import json
data = json.load(open('data/pokemon_data.json'))
charizard = next(p for p in data if p['id'] == 6)
print('is_final_evolution:', charizard['is_final_evolution'])
print('abilities:', [a['name_en'] for a in charizard['abilities']])
print('mega_forms:', [m['suffix'] for m in charizard['mega_forms']])
print('dream_ability:', charizard['dream_ability']['name_en'] if charizard['dream_ability'] else None)
"
```

Expected:
```
is_final_evolution: True
abilities: ['Blaze']
mega_forms: ['mega-x', 'mega-y']
dream_ability: Solar Power
```

- [ ] **Step 3: Verify type sprites downloaded**

```bash
ls /Users/wayneho/poke-calc/data/sprites/types/
```

Expected: 18 PNG files (fire.png, water.png, etc.)

---

## Self-Review Checklist

**Spec coverage:**
- [x] Dropdown selector with fuzzy match (Tasks 8, 9)
- [x] Final evolution priority sorting (Task 3)
- [x] 5×5 nature grid (Task 9)
- [x] Auto-calculate on Speed/Survival (Task 11)
- [x] Search tab: type matchup section (Task 10)
- [x] Search tab: abilities + dream ability + click-to-show description (Task 10)
- [x] Search tab: Mega evolution with sprite + stats + ability (Task 10)
- [x] Official PNG type badges (Tasks 6 type sprites, Task 7 type_badge)
- [x] Type names in current language (type_badge uses translator.type_name)
- [x] build_data.py: abilities + evolution chain + Mega forms (Task 6)
- [x] type_chart.py with get_matchups (Task 4)
- [x] i18n keys for all new UI labels (Task 5)
- [x] Domain model new fields backward-compatible (Task 2)

**Out of scope (per spec section 七):**
- Gigantamax / regional forms
- Type effectiveness on Speed/Survival tabs
- Full game-mechanic descriptions for abilities
