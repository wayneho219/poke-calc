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
