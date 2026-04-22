# UX Improvements Design

**Date:** 2026-04-22
**Scope:** Local data layer, search UX redesign, speed analysis SP input

---

## Problem Summary

1. **Search is slow and hard to use** — every lookup hits PokeAPI; partial-name search returns no results
2. **All data depends on network** — no local cache of stats or sprites
3. **Speed analysis assumes target SP = 0** — unrealistic for competitive play

---

## Section 1: Data Layer

### New file structure

```
data/
  pokemon_data.json    ← single source of truth (names + stats + sprite paths)
  sprites/
    1.png              ← HOME sprite, local
    2.png
    ...
    1025.png
```

### `pokemon_data.json` schema (one entry per Pokémon)

```json
{
  "id": 445,
  "name_en": "garchomp",
  "name_zh": "烈咬陸鯊",
  "name_ja": "ガブリアス",
  "types": ["dragon", "ground"],
  "base_stats": {
    "hp": 108, "attack": 130, "defense": 95,
    "sp_attack": 80, "sp_defense": 85, "speed": 102
  },
  "sprite_path": "data/sprites/445.png"
}
```

### App startup behaviour

`LocalJsonRepository` loads the entire JSON into memory once via `@st.cache_resource`. All subsequent queries are in-memory — no disk I/O, no network calls during normal use.

### Build script

`scripts/build_data.py` replaces `scripts/build_csv.py`. It:
1. Fetches all 1–1025 Pokémon from PokeAPI (names, stats, HOME sprite URL)
2. Downloads each HOME sprite to `data/sprites/{id}.png`
3. Writes `data/pokemon_data.json`

Supports **resume on interrupt**: skips IDs whose sprite file already exists and whose entry is already in the JSON.

---

## Section 2: LocalJsonRepository

**New file:** `adapters/local_json_repository.py`

Implements `AbstractPokeRepository`. Replaces `PokeApiRepository` for all normal app use.

### Indexes built at load time

| Index | Key | Value |
|---|---|---|
| by_id | `int` | `Pokemon` |
| by_name_en | `str` (lowercase) | `Pokemon` |
| by_name_zh | `str` | `Pokemon` |
| by_name_ja | `str` | `Pokemon` |

### Methods

- `get_by_id(id)` — O(1) dict lookup
- `get_by_name(name)` — checks all three name indexes
- `fuzzy_match(query)` — linear scan across all three name fields, returns list of matching `Pokemon` (replaces `CsvNameProvider`)

### Backward compatibility

`PokeApiRepository` and `CsvNameProvider` are **not deleted**. `PokeApiRepository` is only used by `build_data.py` and the in-app update flow. `CsvNameProvider` becomes unused but is kept.

`SearchService` code is **not changed**. However, the Search tab UI calls `local_repo.fuzzy_match(query)` directly to populate the card grid (returns `list[Pokemon]` from memory). `SearchService` is still used by the Speed and Survival tabs for single-Pokémon name lookups.

---

## Section 3: Search UX

### Flow

1. User types in `st.text_input` (e.g. `皮`)
2. On each keystroke: `fuzzy_match(query)` runs in memory → list of matching `Pokemon`
3. Results displayed as a **card grid** (4 columns × 2 rows = 8 per page)
4. Clicking a card sets `st.session_state["selected_pokemon"]` and reruns the page
5. Detail view (large sprite + stat table) appears below the card grid when a Pokémon is selected
6. Empty input → grid hidden (avoids showing all 1025 on load)

### Card layout

Each card contains:
- HOME sprite from `data/sprites/{id}.png` (small display, ~80px)
- Pokémon name in the UI language (zh/en/ja)

### Pagination

- 8 cards per page (2 rows × 4 columns)
- Prev / Next buttons with `「1–8 / 12 筆」` counter
- Page resets to 1 when query changes

---

## Section 4: Speed Analysis — Target SP Input

### UI changes (target Pokémon column)

Add below the nature selectbox:

```
假設速度 SP：[number_input, 0–32, default 0]
目標速度：{calculated_speed}   ← live, updates on input change
```

Add to the user's Pokémon column as well:

```
目前速度（SP=0）：{base_speed_no_sp}   ← displayed once Pokémon is selected
```

### `SpeedService` change

```python
def min_sp_to_outspeed(
    self,
    user: Pokemon,
    target: Pokemon,
    target_sp: int = 0,          # ← new, default keeps existing tests passing
) -> Optional[SpeedResult]:
```

`target_sp` is passed from the UI. Existing tests require no changes (default = 0).

---

## Section 5: Update Data Flow

### Entry point

Sidebar button: **🔄 更新資料庫**

### Steps

1. Show `st.progress` bar with message `「正在下載 [N/1025] {name}...」`
2. For each ID 1–1025:
   - Fetch from PokeAPI (names, stats, sprite URL)
   - Download HOME sprite → `data/sprites/{id}.png`
   - Append entry to in-memory list
3. Write `data/pokemon_data.json` atomically (write to `.tmp`, then rename)
4. Show `「✅ 更新完成，共 1025 筆」`
5. Call `st.cache_resource.clear()` to reload `LocalJsonRepository` from new file

### Resume on interrupt

Before fetching, check if `data/sprites/{id}.png` already exists. If yes, load the existing entry from the current JSON instead of re-fetching.

### First-run guidance

If `pokemon_data.json` does not exist on app start, show a warning banner:

```
⚠️ 尚未下載本地資料。請點擊側邊欄的「更新資料庫」，或執行：
   python3 scripts/build_data.py
```

---

## Files Changed

| Action | File |
|---|---|
| New | `adapters/local_json_repository.py` |
| New | `scripts/build_data.py` |
| Modified | `interfaces/streamlit/app.py` |
| Modified | `application/speed_service.py` |
| Modified | `shared/config.py` (add `DATA_JSON_PATH`, `SPRITES_DIR`) |
| Kept (unused) | `adapters/csv_name_provider.py` |
| Kept (build-only) | `adapters/poke_api_repository.py` |
| Replaced | `data/pokemon_names.csv` → `data/pokemon_data.json` |

---

## Out of Scope

- Survival analysis UI changes (separate session)
- Offline sprite hosting (sprites are local files, not embedded in the app bundle)
- Mobile layout optimisation
