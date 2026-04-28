# UX Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace live API calls with a local JSON data layer, redesign the search tab to show a live card grid with pagination, and add a target SP input to the speed analysis tab.

**Architecture:** New `LocalJsonRepository` loads `data/pokemon_data.json` into memory at startup; all tabs call it directly. `PokeApiRepository` is kept but only used by the update script. A sidebar button rebuilds local data from PokéAPI on demand.

**Tech Stack:** Python 3.11+, Streamlit 1.35+, requests 2.31+, pytest

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `shared/config.py` | Add `DATA_JSON_PATH`, `SPRITES_DIR` |
| Create | `adapters/local_json_repository.py` | In-memory repo from local JSON |
| Create | `tests/adapters/test_local_json_repository.py` | Unit tests |
| Create | `tests/adapters/fixtures/test_pokemon_data.json` | Test fixture |
| Modify | `application/speed_service.py` | Add `target_sp` param |
| Modify | `tests/application/test_speed_service.py` | Tests for `target_sp` |
| Modify | `shared/i18n/zh.json` | New UI keys |
| Modify | `shared/i18n/en.json` | New UI keys |
| Modify | `shared/i18n/ja.json` | New UI keys |
| Create | `scripts/__init__.py` | Make scripts importable |
| Create | `scripts/build_data.py` | Fetch + download all data/sprites |
| Modify | `interfaces/streamlit/app.py` | New search UX, speed SP input, update button |

---

## Task 1: Config — DATA_JSON_PATH and SPRITES_DIR

**Files:**
- Modify: `shared/config.py`

- [ ] **Step 1: Add two new constants**

Replace the entire file with:

```python
from pathlib import Path

ROOT           = Path(__file__).parent.parent
CSV_PATH       = ROOT / "data" / "pokemon_names.csv"
DATA_JSON_PATH = ROOT / "data" / "pokemon_data.json"
SPRITES_DIR    = ROOT / "data" / "sprites"
CACHE_DIR      = ROOT / "adapters" / "cache"
I18N_DIR       = ROOT / "shared" / "i18n"
```

- [ ] **Step 2: Smoke-test**

```bash
cd /Users/wayneho/poke-calc
python3 -c "from shared.config import DATA_JSON_PATH, SPRITES_DIR; print(DATA_JSON_PATH, SPRITES_DIR)"
```

Expected: prints absolute paths ending in `data/pokemon_data.json` and `data/sprites`.

- [ ] **Step 3: Run existing tests to confirm nothing broke**

```bash
python3 -m pytest -q
```

Expected: `79 passed`.

- [ ] **Step 4: Commit**

```bash
git add shared/config.py
git commit -m "chore: add DATA_JSON_PATH and SPRITES_DIR to config"
```

---

## Task 2: LocalJsonRepository

**Files:**
- Create: `tests/adapters/fixtures/test_pokemon_data.json`
- Create: `tests/adapters/test_local_json_repository.py`
- Create: `adapters/local_json_repository.py`

- [ ] **Step 1: Create fixture JSON**

Create `tests/adapters/fixtures/test_pokemon_data.json`:

```json
[
  {
    "id": 25,
    "name_en": "pikachu",
    "name_zh": "皮卡丘",
    "name_ja": "ピカチュウ",
    "types": ["electric"],
    "base_stats": {"hp": 35, "attack": 55, "defense": 40, "sp_attack": 50, "sp_defense": 50, "speed": 90},
    "sprite_path": "data/sprites/25.png"
  },
  {
    "id": 445,
    "name_en": "garchomp",
    "name_zh": "烈咬陸鯊",
    "name_ja": "ガブリアス",
    "types": ["dragon", "ground"],
    "base_stats": {"hp": 108, "attack": 130, "defense": 95, "sp_attack": 80, "sp_defense": 85, "speed": 102},
    "sprite_path": "data/sprites/445.png"
  }
]
```

- [ ] **Step 2: Write failing tests**

Create `tests/adapters/test_local_json_repository.py`:

```python
import pytest
from pathlib import Path
from adapters.local_json_repository import LocalJsonRepository
from shared.exceptions import PokemonNotFoundError

FIXTURE = Path(__file__).parent / "fixtures" / "test_pokemon_data.json"


@pytest.fixture
def repo():
    return LocalJsonRepository(FIXTURE)


class TestGetById:
    def test_known_id_returns_pokemon(self, repo):
        p = repo.get_by_id(445)
        assert p.name_en == "garchomp"
        assert p.base_stats.speed == 102

    def test_unknown_id_raises(self, repo):
        with pytest.raises(PokemonNotFoundError):
            repo.get_by_id(999)


class TestGetByName:
    def test_english_lowercase(self, repo):
        assert repo.get_by_name("garchomp").id == 445

    def test_english_mixed_case(self, repo):
        assert repo.get_by_name("Garchomp").id == 445

    def test_chinese(self, repo):
        assert repo.get_by_name("烈咬陸鯊").id == 445

    def test_japanese(self, repo):
        assert repo.get_by_name("ガブリアス").id == 445

    def test_unknown_raises(self, repo):
        with pytest.raises(PokemonNotFoundError):
            repo.get_by_name("mewtwo")


class TestFuzzyMatch:
    def test_partial_english(self, repo):
        ids = [p.id for p in repo.fuzzy_match("chomp")]
        assert 445 in ids

    def test_partial_chinese(self, repo):
        ids = [p.id for p in repo.fuzzy_match("皮")]
        assert 25 in ids

    def test_partial_japanese(self, repo):
        ids = [p.id for p in repo.fuzzy_match("ピカ")]
        assert 25 in ids

    def test_no_match_returns_empty(self, repo):
        assert repo.fuzzy_match("xyzzy") == []

    def test_empty_query_returns_empty(self, repo):
        assert repo.fuzzy_match("") == []

    def test_search_delegates_to_fuzzy_match(self, repo):
        assert repo.search("pikachu") == repo.fuzzy_match("pikachu")
```

- [ ] **Step 3: Run to verify failure**

```bash
python3 -m pytest tests/adapters/test_local_json_repository.py -v
```

Expected: `ModuleNotFoundError: No module named 'adapters.local_json_repository'`

- [ ] **Step 4: Implement `adapters/local_json_repository.py`**

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
    )


class LocalJsonRepository(AbstractPokeRepository):

    def __init__(self, json_path: Path) -> None:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        self._by_id:  dict[int, Pokemon] = {}
        self._by_en:  dict[str, Pokemon] = {}
        self._by_zh:  dict[str, Pokemon] = {}
        self._by_ja:  dict[str, Pokemon] = {}
        self._all:    list[Pokemon]      = []
        for raw in data:
            p = _parse(raw)
            self._by_id[p.id]          = p
            self._by_en[p.name_en.lower()] = p
            self._by_zh[p.name_zh]     = p
            self._by_ja[p.name_ja]     = p
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
        return [
            p for p in self._all
            if ql in p.name_en.lower() or q in p.name_zh or q in p.name_ja
        ]
```

- [ ] **Step 5: Run tests to verify pass**

```bash
python3 -m pytest tests/adapters/test_local_json_repository.py -v
```

Expected: All 13 tests PASS.

- [ ] **Step 6: Run full suite**

```bash
python3 -m pytest -q
```

Expected: `92 passed`.

- [ ] **Step 7: Commit**

```bash
git add adapters/local_json_repository.py \
        tests/adapters/test_local_json_repository.py \
        tests/adapters/fixtures/test_pokemon_data.json
git commit -m "feat: add LocalJsonRepository with in-memory trilingual search"
```

---

## Task 3: SpeedService — target_sp parameter

**Files:**
- Modify: `application/speed_service.py`
- Modify: `tests/application/test_speed_service.py`

- [ ] **Step 1: Add new failing tests**

Append to the bottom of `tests/application/test_speed_service.py`:

```python
class TestSpeedServiceTargetSP:
    def test_target_sp_raises_target_speed(self):
        # target base 80, sp=4: speed = int((80+20+4)*1.0) = 104
        # user base 100, sp=0: speed = 120 > 104, no SP needed
        user   = make_pokemon(1, 100)
        target = make_pokemon(2, 80)
        result = svc.min_sp_to_outspeed(user, target, target_sp=4)
        assert result is not None
        assert result.sp_needed == 0
        assert result.target_speed == 104

    def test_target_sp_forces_user_to_invest(self):
        # user base 80 sp=0: speed = int((80+20)*1.0) = 100
        # target base 80 sp=4: speed = int((80+20+4)*1.0) = 104
        # need 100+sp > 104 → sp=5, my_speed=105
        user   = make_pokemon(1, 80)
        target = make_pokemon(2, 80)
        result = svc.min_sp_to_outspeed(user, target, target_sp=4)
        assert result is not None
        assert result.sp_needed == 5
        assert result.my_speed == 105
        assert result.target_speed == 104

    def test_target_sp_max_still_cannot_outspeed(self):
        # user base 60 max speed = int((60+20+32)*1.0) = 112
        # target base 100 sp=32 speed = int((100+20+32)*1.0) = 152 → None
        user   = make_pokemon(1, 60)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target, target_sp=32)
        assert result is None
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/application/test_speed_service.py::TestSpeedServiceTargetSP -v
```

Expected: `FAILED` — `min_sp_to_outspeed() got an unexpected keyword argument 'target_sp'`

- [ ] **Step 3: Update `application/speed_service.py`**

Replace the `min_sp_to_outspeed` method signature and body:

```python
from dataclasses import dataclass
from typing import Optional
from domain.models.nature import BattleStat
from domain.models.pokemon import Pokemon
from application.calculator import StatCalculator


@dataclass(frozen=True)
class SpeedResult:
    sp_needed: int
    my_speed: int
    target_speed: int


class SpeedService:

    def __init__(self, calculator: StatCalculator) -> None:
        self._calc = calculator

    def min_sp_to_outspeed(
        self,
        user: Pokemon,
        target: Pokemon,
        target_sp: int = 0,
    ) -> Optional[SpeedResult]:
        target_speed = self._calc.calc_stat(
            target.base_stats.speed, target_sp, target.nature, BattleStat.SPEED
        )
        for sp in range(0, 33):
            my_speed = self._calc.calc_stat(
                user.base_stats.speed, sp, user.nature, BattleStat.SPEED
            )
            if my_speed > target_speed:
                return SpeedResult(sp_needed=sp, my_speed=my_speed, target_speed=target_speed)
        return None
```

- [ ] **Step 4: Run all speed tests**

```bash
python3 -m pytest tests/application/test_speed_service.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 5: Run full suite**

```bash
python3 -m pytest -q
```

Expected: `95 passed`.

- [ ] **Step 6: Commit**

```bash
git add application/speed_service.py tests/application/test_speed_service.py
git commit -m "feat(speed): add target_sp parameter to min_sp_to_outspeed"
```

---

## Task 4: i18n — Add New UI Keys

**Files:**
- Modify: `shared/i18n/zh.json`
- Modify: `shared/i18n/en.json`
- Modify: `shared/i18n/ja.json`

- [ ] **Step 1: Add keys to `shared/i18n/zh.json`**

Insert the following block before the closing `}` (after `"nature_invalid"` and before `"types"`):

```json
  "search_prev": "← 上一頁",
  "search_next": "下一頁 →",
  "search_results_count": "{start}–{end} / {total} 筆",
  "speed_caption": "計算超越目標對手所需的最小 SP_Speed 分配。可自訂目標的速度 SP 假設值。",
  "speed_tgt_sp_label": "目標速度 SP（0–32）",
  "speed_tgt_preview": "目標速度：{speed}",
  "speed_my_preview": "目前速度（SP=0）：{speed}",
  "data_update_button": "更新資料庫",
  "data_update_running_info": "正在從 PokéAPI 更新資料，這需要幾分鐘...",
  "data_update_done": "✅ 更新完成，共 {count} 筆",
  "data_missing_warning": "⚠️ 尚未下載本地資料庫。請點擊側邊欄的「更新資料庫」，或執行以下指令：",
```

- [ ] **Step 2: Add keys to `shared/i18n/en.json`**

Insert the same block before the closing `}` (after `"nature_invalid"` line, before `"types"`):

```json
  "search_prev": "← Prev",
  "search_next": "Next →",
  "search_results_count": "{start}–{end} of {total}",
  "speed_caption": "Find the minimum SP_Speed needed to outspeed the target. You can set the assumed SP_Speed for the target.",
  "speed_tgt_sp_label": "Target SP_Speed (0–32)",
  "speed_tgt_preview": "Target Speed: {speed}",
  "speed_my_preview": "Current Speed (SP=0): {speed}",
  "data_update_button": "Update Database",
  "data_update_running_info": "Updating from PokéAPI, this takes a few minutes...",
  "data_update_done": "✅ Update complete, {count} entries",
  "data_missing_warning": "⚠️ Local database not found. Click \"Update Database\" in the sidebar or run:",
```

- [ ] **Step 3: Add keys to `shared/i18n/ja.json`**

Insert the same block before the closing `}` (after `"nature_invalid"` line, before `"types"`):

```json
  "search_prev": "← 前へ",
  "search_next": "次へ →",
  "search_results_count": "{start}–{end} 件 / 全{total}件",
  "speed_caption": "相手より速くなるために必要な最小 SP_Speed を計算します。相手の仮定 SP_Speed を設定できます。",
  "speed_tgt_sp_label": "目標 SP_Speed（0–32）",
  "speed_tgt_preview": "目標すばやさ：{speed}",
  "speed_my_preview": "現在すばやさ（SP=0）：{speed}",
  "data_update_button": "データ更新",
  "data_update_running_info": "PokéAPI からデータを更新中（数分かかります）...",
  "data_update_done": "✅ 更新完了，{count} 件",
  "data_missing_warning": "⚠️ ローカルデータベースが見つかりません。サイドバーの「データ更新」をクリックするか、次を実行してください：",
```

- [ ] **Step 4: Verify JSON is valid**

```bash
python3 -c "
import json
for f in ['zh', 'en', 'ja']:
    json.loads(open(f'shared/i18n/{f}.json').read())
    print(f'{f}.json OK')
"
```

Expected: `zh.json OK`, `en.json OK`, `ja.json OK`

- [ ] **Step 5: Commit**

```bash
git add shared/i18n/zh.json shared/i18n/en.json shared/i18n/ja.json
git commit -m "feat(i18n): add keys for search pagination, speed SP input, and data update"
```

---

## Task 5: build_data.py Script

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/build_data.py`

- [ ] **Step 1: Create `scripts/__init__.py`**

Create an empty file so `scripts` is importable as a package:

```bash
touch scripts/__init__.py
```

- [ ] **Step 2: Implement `scripts/build_data.py`**

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
from typing import Callable

BASE     = "https://pokeapi.co/api/v2"
TOTAL    = 1025
ROOT     = Path(__file__).parent.parent
OUT_JSON = ROOT / "data" / "pokemon_data.json"
SPRITES  = ROOT / "data" / "sprites"


def _fetch_pokemon(pid: int) -> dict | None:
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
    on_progress: Callable[[int, int, str], None] | None = None,
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
```

- [ ] **Step 3: Commit**

```bash
git add scripts/__init__.py scripts/build_data.py
git commit -m "feat: add build_data.py script (replaces build_csv.py, adds sprite download)"
```

---

## Task 6: Build Local Data

**Files:**
- Create: `data/pokemon_data.json` (generated)
- Create: `data/sprites/*.png` (generated, ~1025 files)

- [ ] **Step 1: Run the build script**

```bash
cd /Users/wayneho/poke-calc
python3 scripts/build_data.py
```

Expected: Progress lines like `[1/1025] bulbasaur / 妙蛙種子 / フシギダネ`. Takes ~5 minutes.

If interrupted, re-run — already-downloaded entries are skipped automatically.

- [ ] **Step 2: Verify output**

```bash
python3 -c "
import json
data = json.loads(open('data/pokemon_data.json').read())
print(f'Entries: {len(data)}')
print(f'First: {data[0][\"name_en\"]} / {data[0][\"name_zh\"]}')
print(f'Last:  {data[-1][\"name_en\"]} / {data[-1][\"name_zh\"]}')
no_sprite = [e['id'] for e in data if not e['sprite_path']]
print(f'Missing sprites: {len(no_sprite)} IDs: {no_sprite[:5]}')
"
```

Expected: `Entries: 1025` (or close), first is Bulbasaur, last is Terapagos/Iron Crown area. Missing sprites count should be small (0–10).

```bash
ls data/sprites/ | wc -l
```

Expected: Close to 1025.

- [ ] **Step 3: Commit**

```bash
git add data/pokemon_data.json data/sprites/
git commit -m "feat: add pokemon_data.json and HOME sprites (Gen 1-9)"
```

Note: This commit will be large (~100 MB). If the repo has a file size limit, add `data/sprites/` to `.gitignore` and only commit `pokemon_data.json`.

---

## Task 7: App — Wire LocalJsonRepository + First-Run Warning

**Files:**
- Modify: `interfaces/streamlit/app.py`

This task updates the service wiring and adds the first-run guard. The search/speed/survival tab content is updated in subsequent tasks.

- [ ] **Step 1: Update imports at the top of `interfaces/streamlit/app.py`**

Replace the current import block (lines 1–11) with:

```python
import dataclasses
from pathlib import Path
import streamlit as st
from adapters.local_json_repository import LocalJsonRepository
from application.calculator import StatCalculator
from application.speed_service import SpeedService
from application.survival_service import AttackInput, SurvivalService
from domain.models.nature import NatureRegistry, BattleStat
from shared.config import DATA_JSON_PATH, SPRITES_DIR
from shared.i18n.translator import Translator, parse_accept_language
```

- [ ] **Step 2: Replace `build_services()` function**

Replace the existing `build_services` function (currently lines 43–53) with:

```python
@st.cache_resource
def build_services() -> dict:
    calc  = StatCalculator()
    local = LocalJsonRepository(DATA_JSON_PATH) if DATA_JSON_PATH.exists() else None
    return {
        "calc":     calc,
        "local":    local,
        "speed":    SpeedService(calc),
        "survival": SurvivalService(calc),
    }
```

- [ ] **Step 3: Add first-run guard after sidebar, before `st.title`**

Locate the line `st.title(t("page_title"))`. Insert these lines BEFORE it:

```python
if svc["local"] is None:
    st.warning(t("data_missing_warning"))
    st.code("python3 scripts/build_data.py")
    st.stop()
```

- [ ] **Step 4: Restart and verify the app loads**

If `data/pokemon_data.json` exists (from Task 6):

```bash
cd /Users/wayneho/poke-calc
python3 -m streamlit run interfaces/streamlit/app.py
```

Expected: App loads, no errors in terminal, all three tabs visible. If JSON doesn't exist yet, the warning banner and `st.stop()` fire correctly.

- [ ] **Step 5: Commit**

```bash
git add interfaces/streamlit/app.py
git commit -m "feat(app): wire LocalJsonRepository and add first-run warning"
```

---

## Task 8: App — Search Tab Redesign

**Files:**
- Modify: `interfaces/streamlit/app.py` (search tab section only)

- [ ] **Step 1: Replace the search tab section**

Find and replace the entire `# ── Search Tab` block (from `with tab_search:` to just before `# ── Speed Tab`):

```python
# ── Search Tab ──────────────────────────────────────────────────────────────
with tab_search:
    st.header(t("search_header"))
    query = st.text_input(
        t("search_input_label"),
        placeholder=t("search_placeholder"),
        key="search_query",
    )

    if query:
        results = svc["local"].fuzzy_match(query)

        if not results:
            st.warning(t("search_not_found"))
        else:
            total = len(results)

            # Reset page and selection when query changes
            if st.session_state.get("_search_last_query") != query:
                st.session_state["_search_page"] = 0
                st.session_state["_search_last_query"] = query
                st.session_state.pop("_selected_id", None)

            PAGE_SIZE = 8
            page  = st.session_state.get("_search_page", 0)
            start = page * PAGE_SIZE
            end   = min(start + PAGE_SIZE, total)

            # Card grid: 4 columns × 2 rows
            for row_start in range(0, end - start, 4):
                cols = st.columns(4)
                for i, p in enumerate(results[start + row_start: start + row_start + 4]):
                    with cols[i]:
                        sprite = SPRITES_DIR / f"{p.id}.png"
                        if sprite.exists():
                            st.image(str(sprite), width=80)
                        name = {"zh": p.name_zh, "en": p.name_en.title(), "ja": p.name_ja}[lang]
                        if st.button(name, key=f"card_{p.id}", use_container_width=True):
                            st.session_state["_selected_id"] = p.id

            # Pagination controls
            nav_l, nav_m, nav_r = st.columns([1, 2, 1])
            if page > 0:
                if nav_l.button(t("search_prev"), key="pg_prev"):
                    st.session_state["_search_page"] = page - 1
                    st.rerun()
            nav_m.caption(
                t("search_results_count").format(start=start + 1, end=end, total=total)
            )
            if end < total:
                if nav_r.button(t("search_next"), key="pg_next"):
                    st.session_state["_search_page"] = page + 1
                    st.rerun()

            # Detail view — shown below cards when a card has been clicked
            if "_selected_id" in st.session_state:
                p = svc["local"].get_by_id(st.session_state["_selected_id"])
                st.divider()
                col_img, col_info = st.columns([1, 3])
                with col_img:
                    sprite = SPRITES_DIR / f"{p.id}.png"
                    if sprite.exists():
                        st.image(str(sprite), width=160)
                with col_info:
                    st.subheader(f"{p.name_zh}　{p.name_en.title()}　{p.name_ja}")
                    st.caption(t("search_types_label") + " / ".join(t.type_name(tp) for tp in p.types))
                    b = p.base_stats
                    st.table({
                        t("stat_col_name"):  t.strings("stat_names"),
                        t("stat_col_value"): [b.hp, b.attack, b.defense, b.sp_attack, b.sp_defense, b.speed],
                    })
```

- [ ] **Step 2: Restart and manually test the search tab**

```bash
python3 -m streamlit run interfaces/streamlit/app.py
```

In the browser — **🔍 寶可夢查詢** tab:

1. Type `皮` → cards appear for 皮卡丘, 皮皮, 皮可西, etc. with sprites
2. Type `Gar` → cards appear for Garchomp (and any other "gar" matches)
3. Click a card → detail view appears below with large sprite + stat table
4. Type a long query that returns >8 results (e.g. `a`) → pagination controls appear
5. Click Next → page 2 cards shown, count updates (e.g. `9–16 / 42 筆`)
6. Type `xyzzy` → "找不到" warning appears

- [ ] **Step 3: Commit**

```bash
git add interfaces/streamlit/app.py
git commit -m "feat(app): redesign search tab with live card grid and pagination"
```

---

## Task 9: App — Speed Tab Target SP

**Files:**
- Modify: `interfaces/streamlit/app.py` (speed tab section only)

- [ ] **Step 1: Replace the speed tab section**

Find and replace the entire `# ── Speed Tab` block (from `with tab_speed:` to just before `# ── Survival Tab`):

```python
# ── Speed Tab ────────────────────────────────────────────────────────────────
with tab_speed:
    st.header(t("speed_header"))
    st.caption(t("speed_caption"))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(t("speed_my_mon"))
        my_query = st.text_input(t("speed_name_label"), key="speed_my", placeholder="Garchomp / 烈咬陸鯊")
        my_nature_name = st.selectbox(
            t("speed_nature_label"),
            options=["Hardy", "Timid", "Jolly", "Hasty", "Naive",
                     "Brave", "Relaxed", "Quiet", "Sassy", t("speed_nature_other")],
            key="speed_my_nature",
        )
        if my_nature_name == t("speed_nature_other"):
            my_nature_name = st.text_input(t("speed_nature_input"), key="speed_my_nature_input")

    with col2:
        st.subheader(t("speed_tgt_mon"))
        tgt_query = st.text_input(t("speed_name_label"), key="speed_tgt", placeholder="Kyogre / 蓋歐卡")
        tgt_nature_name = st.selectbox(
            t("speed_nature_label"),
            options=["Hardy", "Timid", "Jolly", "Hasty", "Naive",
                     "Brave", "Relaxed", "Quiet", "Sassy", t("speed_nature_other")],
            key="speed_tgt_nature",
        )
        if tgt_nature_name == t("speed_nature_other"):
            tgt_nature_name = st.text_input(t("speed_nature_input"), key="speed_tgt_nature_input")
        tgt_sp = int(st.number_input(
            t("speed_tgt_sp_label"), min_value=0, max_value=32, value=0, step=1,
            key="speed_tgt_sp",
        ))

    if st.button(t("speed_button"), key="speed_calc") and my_query and tgt_query:
        try:
            my_nature  = NatureRegistry.get_by_name(my_nature_name)
            tgt_nature = NatureRegistry.get_by_name(tgt_nature_name)
        except ValueError as e:
            st.error(t("nature_invalid").format(error=e))
            st.stop()

        my_results  = svc["local"].fuzzy_match(my_query)
        tgt_results = svc["local"].fuzzy_match(tgt_query)

        if not my_results:
            st.error(t("speed_my_not_found").format(name=my_query))
        elif not tgt_results:
            st.error(t("speed_tgt_not_found").format(name=tgt_query))
        else:
            st.session_state["_speed_my_id"]     = my_results[0].id
            st.session_state["_speed_my_nature"]  = my_nature_name
            st.session_state["_speed_tgt_id"]    = tgt_results[0].id
            st.session_state["_speed_tgt_nature"] = tgt_nature_name

    # Live result — re-renders whenever tgt_sp changes
    if "_speed_my_id" in st.session_state:
        try:
            my_nature  = NatureRegistry.get_by_name(st.session_state["_speed_my_nature"])
            tgt_nature = NatureRegistry.get_by_name(st.session_state["_speed_tgt_nature"])
            my_mon  = dataclasses.replace(
                svc["local"].get_by_id(st.session_state["_speed_my_id"]), nature=my_nature
            )
            tgt_mon = dataclasses.replace(
                svc["local"].get_by_id(st.session_state["_speed_tgt_id"]), nature=tgt_nature
            )

            tgt_preview = svc["calc"].calc_stat(
                tgt_mon.base_stats.speed, tgt_sp, tgt_mon.nature, BattleStat.SPEED
            )
            my_preview = svc["calc"].calc_stat(
                my_mon.base_stats.speed, 0, my_mon.nature, BattleStat.SPEED
            )

            result = svc["speed"].min_sp_to_outspeed(my_mon, tgt_mon, target_sp=tgt_sp)

            st.divider()
            preview_cols = st.columns(2)
            preview_cols[0].caption(t("speed_my_preview").format(speed=my_preview))
            preview_cols[1].caption(t("speed_tgt_preview").format(speed=tgt_preview))

            if result is None:
                st.error(t("speed_cannot_outspeed").format(my=my_mon.name_zh, tgt=tgt_mon.name_zh))
            else:
                st.success(t("speed_success").format(sp=result.sp_needed))
                metric_cols = st.columns(3)
                metric_cols[0].metric(t("speed_metric_sp"), result.sp_needed)
                metric_cols[1].metric(t("speed_metric_speed").format(name=my_mon.name_zh), result.my_speed)
                metric_cols[2].metric(t("speed_metric_speed").format(name=tgt_mon.name_zh), result.target_speed)
        except Exception:
            pass
```

- [ ] **Step 2: Restart and manually test the speed tab**

```bash
python3 -m streamlit run interfaces/streamlit/app.py
```

In browser — **⚡ 超速分析** tab:

1. My: `Garchomp` / Jolly, Target: `Tyranitar` / Brave, Target SP=0 → click Calculate → result appears
2. Change Target SP from 0 to 8 → result updates instantly (no button press)
3. Target speed preview and my speed preview update correctly
4. My: `Pikachu` / Timid, Target: `Garchomp` / Jolly, SP=0 → shows ❌ cannot outspeed or SP needed
5. Invalid name → error shown

- [ ] **Step 3: Commit**

```bash
git add interfaces/streamlit/app.py
git commit -m "feat(app): add target SP input with live speed preview to speed tab"
```

---

## Task 10: App — Sidebar Update Button

**Files:**
- Modify: `interfaces/streamlit/app.py` (sidebar section only)

- [ ] **Step 1: Add update button to the sidebar**

Find the existing `with st.sidebar:` block. It currently contains only the language selector. Add the update button after the language selector:

```python
with st.sidebar:
    chosen = st.selectbox(
        "🌐 Language",
        options=["zh", "en", "ja"],
        format_func=lambda l: {"zh": "繁體中文", "en": "English", "ja": "日本語"}[l],
        index=["zh", "en", "ja"].index(lang),
    )
    if chosen != lang:
        st.query_params["lang"] = chosen
        st.rerun()

    st.divider()
    if st.button("🔄 " + t("data_update_button"), key="update_db"):
        from scripts.build_data import build as _build
        progress = st.progress(0.0, text=t("data_update_running_info"))

        def _on_progress(current: int, total: int, name: str) -> None:
            progress.progress(current / total, text=f"[{current}/{total}] {name}")

        count = _build(on_progress=_on_progress)
        progress.empty()
        st.success(t("data_update_done").format(count=count))
        build_services.clear()
        st.rerun()
```

- [ ] **Step 2: Restart and manually test the update button**

```bash
python3 -m streamlit run interfaces/streamlit/app.py
```

In browser:

1. Sidebar shows **🔄 更新資料庫** button
2. Click it → progress bar appears, updates as each Pokémon downloads
3. On completion: "✅ 更新完成，共 1025 筆" shows, app reloads
4. Verify that already-cached Pokémon are skipped (SKIP messages in progress)

- [ ] **Step 3: Run full test suite one final time**

```bash
python3 -m pytest -q
```

Expected: `95 passed`.

- [ ] **Step 4: Commit**

```bash
git add interfaces/streamlit/app.py
git commit -m "feat(app): add sidebar update button with progress bar"
```

---

## Summary

| Layer | Change |
|---|---|
| `shared/config.py` | `DATA_JSON_PATH`, `SPRITES_DIR` added |
| `adapters/local_json_repository.py` | New — loads entire JSON into memory, O(1) lookup |
| `application/speed_service.py` | `target_sp` parameter added (default 0) |
| `scripts/build_data.py` | New — fetches all data + sprites, resumable |
| `data/pokemon_data.json` | New — 1025 Pokémon, trilingual, with stats |
| `data/sprites/*.png` | New — 1025 HOME sprites |
| `interfaces/streamlit/app.py` | Search card grid, speed SP input, update button |
