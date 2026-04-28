# v3 Speed Modifier + Radar Chart + UX Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-side speed modifier selectors to the Speed tab; replace the base-stat table with a hexagonal radar chart (with Mega overlay); fix multiple UX issues: settings popover, always-visible search input, selectable neutral natures, Mega forms in search index, and Search tab layout improvements.

**Architecture:** `SpeedService.min_sp_to_outspeed` gains `my_mult`/`tgt_mult` float parameters (default 1.0). A new `stat_radar.py` component wraps Plotly `Scatterpolar`. `LocalJsonRepository` indexes Mega forms as virtual `Pokemon` entries (ID = `base_id + (form_index+1)*10000`). Sidebar is replaced by a `st.popover("⚙️")` at the top right. Plotly is added as a project dependency.

**Tech Stack:** Python 3.9, Streamlit 1.x, Plotly 5.x, pytest, dataclasses.

---

## File Map

| Action | Path | Purpose |
|---|---|---|
| Modify | `pyproject.toml` | Add `plotly>=5.0` dependency |
| Modify | `shared/i18n/zh.json` | Speed modifier label keys |
| Modify | `shared/i18n/en.json` | Speed modifier label keys |
| Modify | `shared/i18n/ja.json` | Speed modifier label keys |
| Modify | `application/speed_service.py` | Add `my_mult` / `tgt_mult` params |
| Modify | `tests/application/test_speed_service.py` | Tests for multiplier logic |
| Create | `interfaces/streamlit/components/stat_radar.py` | Plotly radar chart helper |
| Modify | `interfaces/streamlit/components/nature_selector.py` | Neutral natures selectable; name truncation; width fix |
| Modify | `interfaces/streamlit/components/pokemon_selector.py` | Always-visible input; sprite fallback; width fix |
| Modify | `adapters/local_json_repository.py` | Index Mega forms as virtual Pokemon |
| Modify | `tests/adapters/test_local_json_repository.py` | Tests for Mega virtual entries |
| Modify | `interfaces/streamlit/app.py` | All UI wiring: popover, radar, abilities layout, type labels, Speed tab modifiers |

---

## Task 1: Plotly dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add plotly to pyproject.toml**

Replace the `dependencies` block in `pyproject.toml`:

```toml
dependencies = [
    "streamlit>=1.35",
    "requests>=2.31",
    "plotly>=5.0",
]
```

- [ ] **Step 2: Install plotly**

```bash
pip install plotly
```

- [ ] **Step 3: Verify import**

```bash
python3 -c "import plotly; print(plotly.__version__)"
```

Expected: a version string like `5.x.x`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore(deps): add plotly>=5.0 for radar chart"
```

---

## Task 2: i18n — speed modifier labels

**Files:**
- Modify: `shared/i18n/zh.json`
- Modify: `shared/i18n/en.json`
- Modify: `shared/i18n/ja.json`

- [ ] **Step 1: Add keys to zh.json**

Add these entries inside the top-level JSON object (before the closing `}`):

```json
  "speed_modifier_label": "速度修正",
  "speed_modifier_none": "無",
  "speed_modifier_scarf": "講究圍巾",
  "speed_modifier_tailwind": "追風",
  "speed_modifier_weather": "天氣倍速特性",
  "speed_modifier_paralysis": "麻痺",
  "speed_modifier_iron_ball": "黑色鐵球"
```

- [ ] **Step 2: Add keys to en.json**

```json
  "speed_modifier_label": "Speed Modifier",
  "speed_modifier_none": "None",
  "speed_modifier_scarf": "Choice Scarf",
  "speed_modifier_tailwind": "Tailwind",
  "speed_modifier_weather": "Weather Speed Ability",
  "speed_modifier_paralysis": "Paralysis",
  "speed_modifier_iron_ball": "Iron Ball"
```

- [ ] **Step 3: Add keys to ja.json**

```json
  "speed_modifier_label": "すばやさ補正",
  "speed_modifier_none": "なし",
  "speed_modifier_scarf": "こだわりスカーフ",
  "speed_modifier_tailwind": "おいかぜ",
  "speed_modifier_weather": "天候倍速特性",
  "speed_modifier_paralysis": "まひ",
  "speed_modifier_iron_ball": "くろいてっきゅう"
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

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add shared/i18n/zh.json shared/i18n/en.json shared/i18n/ja.json
git commit -m "feat(i18n): add speed modifier label keys"
```

---

## Task 3: SpeedService — speed multiplier parameters

**Files:**
- Modify: `application/speed_service.py`
- Modify: `tests/application/test_speed_service.py`

- [ ] **Step 1: Write failing tests**

Add the following class to `tests/application/test_speed_service.py`:

```python
class TestSpeedMultipliers:
    def test_default_mult_unchanged(self):
        # Default (mult=1.0) must match the original behaviour exactly.
        user   = make_pokemon(1, 80)
        target = make_pokemon(2, 100)
        assert svc.min_sp_to_outspeed(user, target) == \
               svc.min_sp_to_outspeed(user, target, my_mult=1.0, tgt_mult=1.0)

    def test_my_scarf_reduces_sp_needed(self):
        # Without scarf: user base 80 needs sp=21 to beat target base 100 (speed=120).
        # With scarf (×1.5): user speed at sp=0 = floor(100 * 1.5) = 150 > 120 → sp=0.
        user   = make_pokemon(1, 80)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target, my_mult=1.5)
        assert result is not None
        assert result.sp_needed == 0
        assert result.my_speed == 150
        assert result.target_speed == 120

    def test_target_scarf_requires_more_sp(self):
        # user base 100 (speed=120 at sp=0), target base 80 (speed=100).
        # Target with scarf: tgt_speed = floor(100 * 1.5) = 150.
        # Need user speed > 150: floor((100+20+sp)*1.0) > 150 → 120+sp > 150 → sp=31 gives 151.
        user   = make_pokemon(1, 100)
        target = make_pokemon(2, 80)
        result = svc.min_sp_to_outspeed(user, target, tgt_mult=1.5)
        assert result is not None
        assert result.sp_needed == 31
        assert result.my_speed == 151
        assert result.target_speed == 150

    def test_target_paralysis_reduces_sp_needed(self):
        # user base 80 (speed=100 at sp=0), target base 100.
        # Target paralysed (×0.5): tgt_speed = floor(120 * 0.5) = 60.
        # user sp=0: speed=100 > 60 → sp=0.
        user   = make_pokemon(1, 80)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target, tgt_mult=0.5)
        assert result is not None
        assert result.sp_needed == 0
        assert result.my_speed == 100
        assert result.target_speed == 60

    def test_my_paralysis_increases_sp_needed(self):
        # user base 100, target base 80 (speed=100).
        # user paralysed (×0.5): my_speed at sp=0 = floor(120 * 0.5) = 60 < 100.
        # Need floor((120+sp)*0.5) > 100 → (120+sp)*0.5 > 100 → 120+sp > 200 → sp > 80
        # But sp max is 32: floor((120+32)*0.5) = floor(76) = 76 < 100 → None.
        user   = make_pokemon(1, 100)
        target = make_pokemon(2, 80)
        result = svc.min_sp_to_outspeed(user, target, my_mult=0.5)
        assert result is None

    def test_both_multipliers_apply_independently(self):
        # Both sides with Tailwind (×2.0): target base 80 tgt_speed=200, user base 80.
        # floor((80+20+sp)*1.0 * 2.0) > 200 → floor((100+sp)*2.0) > 200
        # sp=0: floor(100*2.0)=200, not > 200. sp=1: floor(101*2.0)=202 > 200. → sp=1.
        user   = make_pokemon(1, 80)
        target = make_pokemon(2, 80)
        result = svc.min_sp_to_outspeed(user, target, my_mult=2.0, tgt_mult=2.0)
        assert result is not None
        assert result.sp_needed == 1
        assert result.my_speed == 202
        assert result.target_speed == 200
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest tests/application/test_speed_service.py::TestSpeedMultipliers -v
```

Expected: FAIL with `TypeError` (unexpected keyword argument `my_mult`).

- [ ] **Step 3: Update SpeedService**

Replace `application/speed_service.py` entirely:

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
        my_mult: float = 1.0,
        tgt_mult: float = 1.0,
    ) -> Optional[SpeedResult]:
        target_speed = int(
            self._calc.calc_stat(target.base_stats.speed, target_sp, target.nature, BattleStat.SPEED)
            * tgt_mult
        )
        for sp in range(0, 33):
            my_speed = int(
                self._calc.calc_stat(user.base_stats.speed, sp, user.nature, BattleStat.SPEED)
                * my_mult
            )
            if my_speed > target_speed:
                return SpeedResult(sp_needed=sp, my_speed=my_speed, target_speed=target_speed)
        return None
```

- [ ] **Step 4: Run all speed tests**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest tests/application/test_speed_service.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add application/speed_service.py tests/application/test_speed_service.py
git commit -m "feat(speed): add my_mult / tgt_mult parameters to min_sp_to_outspeed"
```

---

## Task 4: Speed tab UI — modifier selectors

**Files:**
- Modify: `interfaces/streamlit/app.py` (Speed tab section only)

The speed modifier constants and the modified preview/result calculation are all added inside the `with tab_speed:` block. No new files needed.

- [ ] **Step 1: Replace the Speed tab block in app.py**

Find the section:
```python
# ── Speed Tab ────────────────────────────────────────────────────────────────
with tab_speed:
```

Replace everything inside `with tab_speed:` with:

```python
# ── Speed Tab ────────────────────────────────────────────────────────────────
with tab_speed:
    from interfaces.streamlit.components.pokemon_selector import pokemon_selector
    from interfaces.streamlit.components.nature_selector import nature_selector

    _MODIFIER_KEYS  = [
        "speed_modifier_none", "speed_modifier_scarf", "speed_modifier_tailwind",
        "speed_modifier_weather", "speed_modifier_paralysis", "speed_modifier_iron_ball",
    ]
    _MODIFIER_MULTS = [1.0, 1.5, 2.0, 2.0, 0.5, 0.5]
    _modifier_labels = [f"{t(k)}　×{m}" for k, m in zip(_MODIFIER_KEYS, _MODIFIER_MULTS)]

    st.header(t("speed_header"))
    st.caption(t("speed_caption"))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(t("speed_my_mon"))
        my_mon = pokemon_selector("speed_my", t("speed_name_label"), svc["local"], lang, t)
        st.markdown(f"*{t('nature_grid_header')}*")
        my_nature_en = nature_selector("speed_my", lang, t)
        my_modifier_idx = st.selectbox(
            t("speed_modifier_label"),
            options=range(len(_modifier_labels)),
            format_func=lambda i: _modifier_labels[i],
            key="speed_my_modifier",
        )
        my_mult = _MODIFIER_MULTS[my_modifier_idx]

    with col2:
        st.subheader(t("speed_tgt_mon"))
        tgt_mon = pokemon_selector("speed_tgt", t("speed_name_label"), svc["local"], lang, t)
        st.markdown(f"*{t('nature_grid_header')}*")
        tgt_nature_en = nature_selector("speed_tgt", lang, t)
        tgt_modifier_idx = st.selectbox(
            t("speed_modifier_label"),
            options=range(len(_modifier_labels)),
            format_func=lambda i: _modifier_labels[i],
            key="speed_tgt_modifier",
        )
        tgt_mult = _MODIFIER_MULTS[tgt_modifier_idx]
        tgt_sp = int(st.number_input(
            t("speed_tgt_sp_label"), min_value=0, max_value=32, value=0, step=1,
            key="speed_tgt_sp",
        ))

    if my_mon is not None and tgt_mon is not None:
        try:
            my_nature  = NatureRegistry.get_by_name(my_nature_en)  if my_nature_en  else NatureRegistry.get_by_name("Hardy")
            tgt_nature = NatureRegistry.get_by_name(tgt_nature_en) if tgt_nature_en else NatureRegistry.get_by_name("Hardy")
            my_mon_with_nature  = dataclasses.replace(my_mon,  nature=my_nature)
            tgt_mon_with_nature = dataclasses.replace(tgt_mon, nature=tgt_nature)

            tgt_preview = int(svc["calc"].calc_stat(
                tgt_mon_with_nature.base_stats.speed, tgt_sp, tgt_mon_with_nature.nature, BattleStat.SPEED
            ) * tgt_mult)
            my_preview = int(svc["calc"].calc_stat(
                my_mon_with_nature.base_stats.speed, 0, my_mon_with_nature.nature, BattleStat.SPEED
            ) * my_mult)

            result = svc["speed"].min_sp_to_outspeed(
                my_mon_with_nature, tgt_mon_with_nature,
                target_sp=tgt_sp, my_mult=my_mult, tgt_mult=tgt_mult,
            )

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

- [ ] **Step 2: Run full test suite**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest -v
```

Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
git add interfaces/streamlit/app.py
git commit -m "feat(ui): add speed modifier selectbox to Speed tab"
```

---

## Task 5: stat_radar component

**Files:**
- Create: `interfaces/streamlit/components/stat_radar.py`

- [ ] **Step 1: Create stat_radar.py**

```python
# interfaces/streamlit/components/stat_radar.py
from __future__ import annotations
import plotly.graph_objects as go
from domain.models.stats import StatSet

_FILL_COLOR   = "rgba(99, 144, 240, 0.30)"
_LINE_COLOR   = "#6390F0"
_MEGA_FILL    = "rgba(238, 129, 48, 0.25)"
_MEGA_LINE    = "#EE8130"
_MAX_STAT     = 255


def _stat_values(stats: StatSet) -> list[int]:
    return [stats.hp, stats.attack, stats.defense, stats.sp_attack, stats.sp_defense, stats.speed]


def stat_radar_chart(
    base_stats: StatSet,
    stat_labels: list[str],
    mega_stats: StatSet | None = None,
    mega_label: str = "Mega",
    base_label: str = "",
) -> go.Figure:
    """
    Build a Plotly Scatterpolar radar chart for base stats.
    If mega_stats is provided, overlays the Mega form as a second trace.
    """
    labels_closed = stat_labels + [stat_labels[0]]

    base_vals = _stat_values(base_stats)
    base_vals_closed = base_vals + [base_vals[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=base_vals_closed,
        theta=labels_closed,
        fill="toself",
        name=base_label or "Base",
        line=dict(color=_LINE_COLOR, width=2),
        fillcolor=_FILL_COLOR,
        mode="lines+markers+text",
        text=[str(v) for v in base_vals] + [""],
        textposition="top center",
        textfont=dict(size=11, color=_LINE_COLOR),
    ))

    if mega_stats is not None:
        mega_vals = _stat_values(mega_stats)
        mega_vals_closed = mega_vals + [mega_vals[0]]
        fig.add_trace(go.Scatterpolar(
            r=mega_vals_closed,
            theta=labels_closed,
            fill="toself",
            name=mega_label,
            line=dict(color=_MEGA_LINE, width=2, dash="dot"),
            fillcolor=_MEGA_FILL,
            mode="lines+markers+text",
            text=[str(v) for v in mega_vals] + [""],
            textposition="top center",
            textfont=dict(size=11, color=_MEGA_LINE),
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, _MAX_STAT],
                tickfont=dict(size=8),
                gridcolor="rgba(200,200,200,0.2)",
                linecolor="rgba(200,200,200,0.3)",
            ),
            angularaxis=dict(
                tickfont=dict(size=11),
                gridcolor="rgba(200,200,200,0.2)",
                linecolor="rgba(200,200,200,0.3)",
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=(mega_stats is not None),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        margin=dict(l=50, r=50, t=30, b=30),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
```

- [ ] **Step 2: Verify import**

```bash
cd /Users/wayneho/poke-calc
python3 -c "from interfaces.streamlit.components.stat_radar import stat_radar_chart; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add interfaces/streamlit/components/stat_radar.py
git commit -m "feat(components): add stat_radar Plotly radar chart helper"
```

---

## Task 6: Wire radar chart into Search tab

**Files:**
- Modify: `interfaces/streamlit/app.py` (Search tab section only)

The Search tab has two places that display stats as a table:
1. The main detail card (`st.table` for the selected Pokémon's base stats)
2. Inside each Mega evolution `st.expander` (`st.dataframe` showing base vs. Mega stats)

Both are replaced in this task.

- [ ] **Step 1: Replace the base-form stat table in the Search tab**

Find:
```python
        with col_info:
            st.subheader(f"{p.name_zh}　{p.name_en.title()}　{p.name_ja}")
            badge_html = types_html(p.types, t)
            st.markdown(badge_html, unsafe_allow_html=True)
            b = p.base_stats
            st.table({
                t("stat_col_name"):  t.strings("stat_names"),
                t("stat_col_value"): [b.hp, b.attack, b.defense, b.sp_attack, b.sp_defense, b.speed],
            })
```

Replace with:

```python
        with col_info:
            from interfaces.streamlit.components.stat_radar import stat_radar_chart
            st.subheader(f"{p.name_zh}　{p.name_en.title()}　{p.name_ja}")
            badge_html = types_html(p.types, t)
            st.markdown(badge_html, unsafe_allow_html=True)
            fig = stat_radar_chart(p.base_stats, t.strings("stat_names"))
            st.plotly_chart(fig, use_container_width=True)
```

- [ ] **Step 2: Replace the Mega stat dataframe with an overlaid radar chart**

Find (inside the `for mega in p.mega_forms:` loop):
```python
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
```

Replace with:

```python
                    with mcol_info:
                        from interfaces.streamlit.components.stat_radar import stat_radar_chart
                        from domain.models.stats import StatSet
                        mega_types = mega.get("types", [])
                        if mega_types:
                            st.markdown(types_html(tuple(mega_types), t), unsafe_allow_html=True)
                        ms = mega.get("base_stats", {})
                        if ms:
                            mega_stat_obj = StatSet(
                                hp=ms.get("hp", 0), attack=ms.get("attack", 0),
                                defense=ms.get("defense", 0), sp_attack=ms.get("sp_attack", 0),
                                sp_defense=ms.get("sp_defense", 0), speed=ms.get("speed", 0),
                            )
                            mega_display_name = mega.get(
                                "name_zh" if lang == "zh" else ("name_en" if lang == "en" else "name_ja"),
                                "Mega"
                            )
                            base_display_name = {"zh": p.name_zh, "en": p.name_en.title(), "ja": p.name_ja}[lang]
                            fig = stat_radar_chart(
                                p.base_stats, t.strings("stat_names"),
                                mega_stats=mega_stat_obj,
                                mega_label=mega_display_name,
                                base_label=base_display_name,
                            )
                            st.plotly_chart(fig, use_container_width=True)
```

- [ ] **Step 3: Check StatSet import at top of app.py**

`StatSet` is not currently imported in `app.py`. Add it to the existing import line for domain models:

Find:
```python
from domain.models.nature import NatureRegistry, BattleStat
```

Replace with:
```python
from domain.models.nature import NatureRegistry, BattleStat
from domain.models.stats import StatSet
```

- [ ] **Step 4: Run full test suite**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add interfaces/streamlit/app.py
git commit -m "feat(ui): replace base-stat table with Plotly radar chart; overlay Mega comparison"
```

---

---

## Task 7: Fix `use_container_width` deprecation

**Files:**
- Modify: `interfaces/streamlit/components/nature_selector.py`
- Modify: `interfaces/streamlit/components/pokemon_selector.py`

Streamlit deprecated `use_container_width` on buttons in favour of `width`. Replace all occurrences before 2025-12-31 deadline (already past). `st.image` and `st.plotly_chart` are unaffected.

- [ ] **Step 1: Fix nature_selector.py**

In `interfaces/streamlit/components/nature_selector.py`, replace both occurrences:

```python
# OLD (two places)
use_container_width=True,
# NEW
width="stretch",
```

The full updated button calls become:

```python
# Neutral (diagonal)
st.button(
    nat_name,
    key=f"_nat_{key}_{row}_{col}",
    disabled=True,
    width="stretch",
)

# Non-neutral
if st.button(
    nat_name,
    key=f"_nat_{key}_{row}_{col}",
    type=btn_type,
    width="stretch",
    help=f"+{stat_labels[row]} / -{stat_labels[col]}",
):
```

- [ ] **Step 2: Fix pokemon_selector.py**

In `interfaces/streamlit/components/pokemon_selector.py`, replace:

```python
# OLD
if st.button(name, key=f"_ps_btn_{key}_{p.id}", use_container_width=True):
# NEW
if st.button(name, key=f"_ps_btn_{key}_{p.id}", width="stretch"):
```

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest -v
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add interfaces/streamlit/components/nature_selector.py interfaces/streamlit/components/pokemon_selector.py
git commit -m "fix(components): replace deprecated use_container_width with width='stretch'"
```

---

## Task 8: Settings ⚙️ popover — remove sidebar

**Files:**
- Modify: `interfaces/streamlit/app.py`

Remove the `with st.sidebar:` block entirely. Replace with a `st.columns([10, 1])` header layout where the right column holds a `st.popover("⚙️")` containing the language selector and update-database button. The update progress bar is triggered via session state and rendered in the main area.

- [ ] **Step 1: Replace sidebar + page title with popover header**

Find and remove the entire sidebar block:
```python
with st.sidebar:
    chosen = st.selectbox(
        "🌐 Language",
        ...
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

And the `st.title(t("page_title"))` line. Replace both with:

```python
_hdr_main, _hdr_gear = st.columns([10, 1])
_hdr_main.title(t("page_title"))

with _hdr_gear.popover("⚙️", use_container_width=False):
    chosen = st.selectbox(
        "🌐 " + t("speed_modifier_label"),
        options=["zh", "en", "ja"],
        format_func=lambda l: {"zh": "繁體中文", "en": "English", "ja": "日本語"}[l],
        index=["zh", "en", "ja"].index(lang),
        key="_lang_select",
    )
    if chosen != lang:
        st.query_params["lang"] = chosen
        st.rerun()

    st.divider()
    if st.button("🔄 " + t("data_update_button"), key="update_db"):
        st.session_state["_run_update"] = True
        st.rerun()

_update_placeholder = st.empty()
if st.session_state.get("_run_update"):
    st.session_state["_run_update"] = False
    with _update_placeholder.container():
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

- [ ] **Step 2: Run full test suite**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest -v
```

Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
git add interfaces/streamlit/app.py
git commit -m "feat(ui): replace sidebar with settings popover in page header"
```

---

## Task 9: Mega forms in search index

**Files:**
- Modify: `adapters/local_json_repository.py`
- Modify: `tests/adapters/test_local_json_repository.py`

After parsing each real Pokémon, iterate its `mega_forms` list and construct a virtual `Pokemon` for each form. Virtual ID = `base_id + (form_index + 1) * 10000`. Virtual entries are added to all four lookup dictionaries and `_all`, so `fuzzy_match` and `get_by_id` both work on them.

- [ ] **Step 1: Write failing tests**

Add to `tests/adapters/test_local_json_repository.py`:

```python
class TestMegaIndex:
    def test_mega_garchomp_searchable_by_zh(self, repo):
        results = repo.fuzzy_match("Mega 烈咬陸鯊")
        names = [p.name_zh for p in results]
        assert "Mega 烈咬陸鯊" in names

    def test_mega_garchomp_searchable_by_en(self, repo):
        results = repo.fuzzy_match("Mega Garchomp")
        names = [p.name_en for p in results]
        assert "Mega Garchomp" in names

    def test_mega_garchomp_has_mega_base_stats(self, repo):
        results = repo.fuzzy_match("Mega Garchomp")
        mega = next(p for p in results if p.name_en == "Mega Garchomp")
        assert mega.base_stats.attack == 170
        assert mega.base_stats.speed == 92

    def test_mega_virtual_id_retrievable(self, repo):
        # Virtual ID for Garchomp (445) first mega form = 445 + 10000 = 10445
        mega = repo.get_by_id(10445)
        assert mega.name_en == "Mega Garchomp"

    def test_mega_is_final_evolution(self, repo):
        mega = repo.get_by_id(10445)
        assert mega.is_final_evolution is True

    def test_base_pokemon_still_in_index(self, repo):
        # Ensure base Garchomp is still accessible after adding Mega
        base = repo.get_by_id(445)
        assert base.name_en == "garchomp"
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest tests/adapters/test_local_json_repository.py::TestMegaIndex -v
```

Expected: FAIL (Mega entries not in index yet).

- [ ] **Step 3: Update `LocalJsonRepository.__init__` to index Mega forms**

In `adapters/local_json_repository.py`, add a helper function and update `__init__`:

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


def _parse_mega(base: Pokemon, mega: dict, form_index: int) -> Pokemon:
    ms = mega.get("base_stats", {})
    virtual_id = base.id + (form_index + 1) * 10000
    ability = mega.get("ability")
    return Pokemon(
        id=virtual_id,
        name_en=mega.get("name_en", f"Mega {base.name_en}"),
        name_zh=mega.get("name_zh", f"Mega {base.name_zh}"),
        name_ja=mega.get("name_ja", f"メガ{base.name_ja}"),
        types=tuple(mega.get("types", list(base.types))),
        base_stats=StatSet(
            hp=ms.get("hp", 0), attack=ms.get("attack", 0),
            defense=ms.get("defense", 0), sp_attack=ms.get("sp_attack", 0),
            sp_defense=ms.get("sp_defense", 0), speed=ms.get("speed", 0),
        ),
        sprite_url=mega.get("sprite_path", ""),
        is_final_evolution=True,
        abilities=[ability] if ability else [],
        dream_ability=None,
        mega_forms=[],
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
            self._index(p)
            for fi, mega in enumerate(p.mega_forms):
                try:
                    vp = _parse_mega(p, mega, fi)
                    self._index(vp)
                except Exception:
                    pass

    def _index(self, p: Pokemon) -> None:
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

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add adapters/local_json_repository.py tests/adapters/test_local_json_repository.py
git commit -m "feat(adapter): index Mega forms as virtual Pokemon entries for search"
```

---

## Task 10: `pokemon_selector` — always-visible search input

**Files:**
- Modify: `interfaces/streamlit/components/pokemon_selector.py`

Currently the text input disappears after selection. New behaviour: input is always visible; the selected Pokémon is shown in a compact strip below the input; typing triggers a new search that replaces the current selection when clicked.

- [ ] **Step 1: Replace pokemon_selector.py entirely**

```python
from __future__ import annotations
import streamlit as st
from domain.models.pokemon import Pokemon
from adapters.local_json_repository import LocalJsonRepository
from interfaces.streamlit.components.type_badge import types_html
from shared.config import SPRITES_DIR


def _sprite_path(p: Pokemon):
    """Return the best available sprite Path for p, or None."""
    from pathlib import Path
    candidate = SPRITES_DIR / f"{p.id}.png"
    if candidate.exists():
        return candidate
    if p.sprite_url:
        fallback = Path(p.sprite_url)
        if fallback.exists():
            return fallback
    return None


def pokemon_selector(
    key: str,
    label: str,
    repo: LocalJsonRepository,
    lang: str,
    translator,
) -> Pokemon | None:
    """
    Fuzzy-search Pokémon selector with always-visible input.

    The text input stays visible at all times. When a Pokémon is selected its
    info appears below the input in a compact strip. Typing a new query shows
    search results; clicking one replaces the current selection.
    Returns the currently selected Pokemon, or None.
    """
    selected_key = f"_ps_sel_{key}"
    version_key  = f"_ps_ver_{key}"

    # ── Search input (always shown) ───────────────────────────────────────────
    version = st.session_state.get(version_key, 0)
    query_widget_key = f"_ps_query_{key}_{version}"

    query = st.text_input(
        label,
        key=query_widget_key,
        placeholder=translator("selector_placeholder"),
    )

    # ── Compact selected-Pokémon strip ────────────────────────────────────────
    selected_id = st.session_state.get(selected_key)
    selected_pokemon: Pokemon | None = None
    if selected_id is not None:
        try:
            selected_pokemon = repo.get_by_id(selected_id)
        except Exception:
            st.session_state[selected_key] = None
            selected_pokemon = None

    if selected_pokemon is not None and not query:
        p = selected_pokemon
        name = {"zh": p.name_zh, "en": p.name_en.title(), "ja": p.name_ja}[lang]
        col_img, col_info, col_btn = st.columns([1, 5, 1])
        with col_img:
            sp = _sprite_path(p)
            if sp:
                st.image(str(sp), width=48)
        with col_info:
            st.markdown(f"**{name}**")
            st.markdown(types_html(p.types, translator), unsafe_allow_html=True)
        with col_btn:
            if st.button("✕", key=f"_ps_clear_{key}", help=translator("selector_clear")):
                st.session_state[selected_key] = None
                st.session_state[version_key] = version + 1
                st.rerun()

    # ── Search results ────────────────────────────────────────────────────────
    if query:
        candidates = repo.fuzzy_match(query)[:8]
        for p in candidates:
            name = {"zh": p.name_zh, "en": p.name_en.title(), "ja": p.name_ja}[lang]
            col_img, col_name, col_types = st.columns([1, 3, 3])
            with col_img:
                sp = _sprite_path(p)
                if sp:
                    st.image(str(sp), width=36)
            with col_name:
                if st.button(name, key=f"_ps_btn_{key}_{p.id}", width="stretch"):
                    st.session_state[selected_key] = p.id
                    st.session_state[version_key] = version + 1
                    st.rerun()
            with col_types:
                st.markdown(types_html(p.types, translator), unsafe_allow_html=True)

    return selected_pokemon if not query else None
```

- [ ] **Step 2: Verify import**

```bash
cd /Users/wayneho/poke-calc
python3 -c "from interfaces.streamlit.components.pokemon_selector import pokemon_selector; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest -v
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add interfaces/streamlit/components/pokemon_selector.py
git commit -m "feat(components): pokemon_selector always-visible input; sprite fallback for Mega"
```

---

## Task 11: `nature_selector` — neutral natures selectable + name truncation

**Files:**
- Modify: `interfaces/streamlit/components/nature_selector.py`

Two fixes: (1) diagonal neutral-nature cells become clickable; (2) long names (EN/JA) are truncated to 5 chars with `…` and the full name shown in `help`.

- [ ] **Step 1: Replace nature_selector.py entirely**

```python
from __future__ import annotations
import streamlit as st
from domain.models.nature import ALL_NATURES, BattleStat, Nature

STATS_ORDER = [
    BattleStat.ATTACK,
    BattleStat.DEFENSE,
    BattleStat.SP_ATTACK,
    BattleStat.SP_DEFENSE,
    BattleStat.SPEED,
]

_NEUTRAL_NATURES: list[Nature] = [n for n in ALL_NATURES if n.boosted is None]

_GRID: dict[tuple, Nature] = {
    (n.boosted, n.reduced): n for n in ALL_NATURES if n.boosted is not None
}

_STAT_LABELS: dict[str, list[str]] = {
    "zh": ["攻擊", "防禦", "特攻", "特防", "速度"],
    "en": ["Atk",  "Def",  "SpA",  "SpD",  "Spe"],
    "ja": ["こうげき", "ぼうぎょ", "とくこう", "とくぼう", "すばやさ"],
}

_MAX_LABEL_LEN = 5


def _truncate(name: str) -> str:
    return name if len(name) <= _MAX_LABEL_LEN else name[:_MAX_LABEL_LEN] + "…"


def _cell_nature(row: int, col: int) -> Nature:
    if row == col:
        return _NEUTRAL_NATURES[row]
    return _GRID[(STATS_ORDER[row], STATS_ORDER[col])]


def nature_selector(key: str, lang: str, translator) -> str | None:
    """
    5×5 nature grid selector.

    Returns the selected nature's English name, or None if nothing selected.
    All 25 cells are clickable; diagonal (neutral) natures use secondary style.
    Long names are truncated with full name shown in the button tooltip.
    """
    selected_key = f"_nat_{key}"
    current: str | None = st.session_state.get(selected_key)

    stat_labels = _STAT_LABELS.get(lang, _STAT_LABELS["zh"])

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
            full_name = {"zh": nature.name_zh, "en": nature.name_en, "ja": nature.name_ja}[lang]
            label = _truncate(full_name)
            is_neutral = (row == col)
            is_selected = (current == nature.name_en)

            if is_neutral:
                help_text = full_name + "（中性）"
            else:
                help_text = f"{full_name}　+{stat_labels[row]} / -{stat_labels[col]}"

            btn_type = "primary" if is_selected else "secondary"

            with row_cols[col + 1]:
                if st.button(
                    label,
                    key=f"_nat_{key}_{row}_{col}",
                    type=btn_type,
                    width="stretch",
                    help=help_text,
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

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest -v
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add interfaces/streamlit/components/nature_selector.py
git commit -m "feat(components): neutral natures selectable; truncate long names in grid"
```

---

## Task 12: Search tab UI — abilities layout, type labels, section order

**Files:**
- Modify: `interfaces/streamlit/app.py` (Search tab only)

Three changes in the Search tab detail card:
1. Move abilities section above the radar chart
2. Ability buttons laid out in one row (one column per ability)
3. Type matchup multiplier labels larger and more distinct (font size 15px, bold)

- [ ] **Step 1: Reorder and refactor Search tab detail card in app.py**

Inside `with tab_search:`, find the full detail card block starting from `if selected_mon is not None:` and replace it with the following. Note the new order: name+types → **abilities** → radar chart → type matchup → Mega.

```python
    if selected_mon is not None:
        p = selected_mon
        st.divider()
        col_img, col_info = st.columns([1, 3])
        with col_img:
            sprite = SPRITES_DIR / f"{p.id}.png"
            if sprite.exists():
                st.image(str(sprite), width=160)
        with col_info:
            from interfaces.streamlit.components.stat_radar import stat_radar_chart
            st.subheader(f"{p.name_zh}　{p.name_en.title()}　{p.name_ja}")
            badge_html = types_html(p.types, t)
            st.markdown(badge_html, unsafe_allow_html=True)

            # ── Abilities (above stats) ──────────────────────────────────────
            if p.abilities or p.dream_ability:
                st.markdown(f"**{t('detail_abilities')}**")
                abil_hint_key = f"_abil_desc_search_{p.id}"

                all_abilities = list(p.abilities)
                if p.dream_ability:
                    all_abilities.append({**p.dream_ability, "_is_dream": True})

                ab_cols = st.columns(len(all_abilities))
                for i, (ab, col) in enumerate(zip(all_abilities, ab_cols)):
                    is_dream = ab.get("_is_dream", False)
                    ab_name = {"zh": ab.get("name_zh", ""), "en": ab.get("name_en", ""), "ja": ab.get("name_ja", "")}[lang]
                    prefix = t("detail_dream_ability_prefix") if is_dream else ""
                    label = f"{prefix}{ab_name}"
                    with col:
                        if st.button(label, key=f"_abil_btn_search_{p.id}_{i}"):
                            ab_desc = {"zh": ab.get("desc_zh", ""), "en": ab.get("desc_en", ""), "ja": ab.get("desc_ja", "")}[lang]
                            st.session_state[abil_hint_key] = f"**{label}**\n\n{ab_desc}"

                if abil_hint_key in st.session_state:
                    st.info(st.session_state[abil_hint_key])
                else:
                    st.caption(t("detail_ability_hint"))

            # ── Radar chart ──────────────────────────────────────────────────
            fig = stat_radar_chart(p.base_stats, t.strings("stat_names"))
            st.plotly_chart(fig, use_container_width=True)

        # ── Type matchup ─────────────────────────────────────────────────────
        st.markdown(f"**{t('detail_type_matchup')}**")
        matchups = get_matchups(list(p.types))
        weaknesses  = sorted([(tp, v) for tp, v in matchups.items() if v > 1], key=lambda x: -x[1])
        resistances = sorted([(tp, v) for tp, v in matchups.items() if 0 < v < 1], key=lambda x: x[1])
        immunities  = [(tp, v) for tp, v in matchups.items() if v == 0]

        if weaknesses:
            st.markdown(f"*{t('detail_weaknesses')}*")
            html_parts = []
            cur_mult = None
            for tp, v in weaknesses:
                if v != cur_mult:
                    cur_mult = v
                    mult_str = "4×" if v == 4.0 else "2×"
                    html_parts.append(
                        f'<span style="font-size:15px;font-weight:bold;color:#f38ba8;margin:0 6px">{mult_str}</span>'
                    )
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
                    html_parts.append(
                        f'<span style="font-size:15px;font-weight:bold;color:#89b4fa;margin:0 6px">{mult_str}</span>'
                    )
                html_parts.append(type_badge_html(tp, t.type_name(tp)))
            st.markdown("".join(html_parts), unsafe_allow_html=True)

        if immunities:
            st.markdown(f"*{t('detail_immunities')}*")
            html_parts = ['<span style="font-size:15px;font-weight:bold;color:#a6adc8;margin:0 6px">0×</span>']
            for tp, _ in immunities:
                html_parts.append(type_badge_html(tp, t.type_name(tp)))
            st.markdown("".join(html_parts), unsafe_allow_html=True)

        # ── Mega forms ───────────────────────────────────────────────────────
        if p.mega_forms:
            st.divider()
            st.markdown(f"**{t('detail_mega')}**")
            for mega in p.mega_forms:
                mega_name_key = "name_zh" if lang == "zh" else ("name_en" if lang == "en" else "name_ja")
                with st.expander(mega.get(mega_name_key, mega.get("name_en", "Mega"))):
                    mcol_img, mcol_info = st.columns([1, 3])
                    with mcol_img:
                        mega_sprite = MEGA_SPRITES_DIR / f"{p.id}-{mega['suffix']}.png"
                        if mega_sprite.exists():
                            st.image(str(mega_sprite), width=120)
                    with mcol_info:
                        from interfaces.streamlit.components.stat_radar import stat_radar_chart
                        mega_types = mega.get("types", [])
                        if mega_types:
                            st.markdown(types_html(tuple(mega_types), t), unsafe_allow_html=True)
                        ms = mega.get("base_stats", {})
                        if ms:
                            mega_stat_obj = StatSet(
                                hp=ms.get("hp", 0), attack=ms.get("attack", 0),
                                defense=ms.get("defense", 0), sp_attack=ms.get("sp_attack", 0),
                                sp_defense=ms.get("sp_defense", 0), speed=ms.get("speed", 0),
                            )
                            mega_display_name = mega.get(mega_name_key, "Mega")
                            base_display_name = {"zh": p.name_zh, "en": p.name_en.title(), "ja": p.name_ja}[lang]
                            fig = stat_radar_chart(
                                p.base_stats, t.strings("stat_names"),
                                mega_stats=mega_stat_obj,
                                mega_label=mega_display_name,
                                base_label=base_display_name,
                            )
                            st.plotly_chart(fig, use_container_width=True)

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

Also ensure `StatSet` is imported at the top of `app.py`:

```python
from domain.models.stats import StatSet
```

- [ ] **Step 2: Run full test suite**

```bash
cd /Users/wayneho/poke-calc
python3 -m pytest -v
```

Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
git add interfaces/streamlit/app.py
git commit -m "feat(ui): abilities above stats; same-row ability buttons; larger type multiplier labels; Mega radar overlay"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Speed modifier selector for my Pokémon (Task 4)
- [x] Speed modifier selector for target Pokémon (Task 4)
- [x] Options: 無×1.0 / 講究圍巾×1.5 / 追風×2.0 / 天氣倍速特性×2.0 / 麻痺×0.5 / 黑色鐵球×0.5 (Tasks 2 & 4)
- [x] SpeedService multiplier logic + tests (Task 3)
- [x] Preview and result reflect modified speed (Task 4)
- [x] Base stat table → hexagonal radar chart in Search tab (Tasks 5 & 12)
- [x] Stat values shown at each vertex (Task 5)
- [x] Single unified color (Task 5)
- [x] Mega evolution expander uses radar chart with overlay (Tasks 5 & 12)
- [x] Plotly installed as dependency (Task 1)
- [x] i18n for speed modifier labels (Task 2)
- [x] `use_container_width` deprecation fixed (Task 7)
- [x] Settings ⚙️ popover replaces sidebar (Task 8)
- [x] Mega forms searchable in Speed/Survival/Search tabs (Task 9)
- [x] Mega virtual ID scheme: `base_id + (form_index+1)*10000` (Task 9)
- [x] pokemon_selector always-visible input; sprite fallback (Task 10)
- [x] Neutral natures selectable in 5×5 grid (Task 11)
- [x] Long nature names truncated with help tooltip (Task 11)
- [x] Abilities section above base stats (Task 12)
- [x] Ability buttons in same row (Task 12)
- [x] Type multiplier labels larger and bolder (Task 12)
