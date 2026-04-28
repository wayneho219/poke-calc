from __future__ import annotations
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

    Uses a version counter to reset the text_input widget, because Streamlit
    forbids writing directly to a session_state key that is bound to an active widget.
    """
    selected_key = f"_ps_sel_{key}"
    version_key  = f"_ps_ver_{key}"

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
                st.session_state[version_key] = st.session_state.get(version_key, 0) + 1
                st.rerun()
        return p

    # ── Search input ─────────────────────────────────────────────────────────
    # Include version in widget key so incrementing it resets the input to empty.
    version = st.session_state.get(version_key, 0)
    query_widget_key = f"_ps_query_{key}_{version}"

    query = st.text_input(
        label,
        key=query_widget_key,
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
                    st.session_state[version_key] = version + 1
                    st.rerun()
            with col_types:
                badge_html = types_html(p.types, translator)
                st.markdown(badge_html, unsafe_allow_html=True)

    return None
