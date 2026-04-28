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
                        width="stretch",
                    )
                else:
                    btn_type = "primary" if is_selected else "secondary"
                    if st.button(
                        nat_name,
                        key=f"_nat_{key}_{row}_{col}",
                        type=btn_type,
                        width="stretch",
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
