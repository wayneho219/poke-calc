import dataclasses
import streamlit as st
from adapters.local_json_repository import LocalJsonRepository
from application.calculator import StatCalculator
from application.speed_service import SpeedService
from application.survival_service import AttackInput, SurvivalService
from domain.models.nature import NatureRegistry, BattleStat
from shared.config import DATA_JSON_PATH, SPRITES_DIR, MEGA_SPRITES_DIR
from shared.i18n.translator import Translator, parse_accept_language


def detect_lang() -> str:
    if "lang" in st.query_params:
        candidate = st.query_params["lang"]
        if candidate in ("zh", "en", "ja"):
            return candidate
    try:
        header = st.context.headers.get("Accept-Language", "")
        return parse_accept_language(header)
    except AttributeError:
        return "zh"


lang = detect_lang()
t = Translator(lang)

st.set_page_config(page_title=t("page_title"), layout="wide")

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


svc = build_services()

if svc["local"] is None:
    st.warning(t("data_missing_warning"))
    st.code("python3 scripts/build_data.py")
    st.stop()

st.title(t("page_title"))

tab_search, tab_speed, tab_survival = st.tabs([t("tab_search"), t("tab_speed"), t("tab_survival")])

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
                mega_name_key = "name_zh" if lang == "zh" else ("name_en" if lang == "en" else "name_ja")
                with st.expander(mega.get(mega_name_key, mega.get("name_en", "Mega"))):
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
            st.session_state["_speed_my_id"]      = my_results[0].id
            st.session_state["_speed_my_nature"]  = my_nature_name
            st.session_state["_speed_tgt_id"]     = tgt_results[0].id
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

# ── Survival Tab ─────────────────────────────────────────────────────────────
with tab_survival:
    st.header(t("surv_header"))
    st.caption(t("surv_caption"))

    col_mon, col_atk = st.columns(2)

    with col_mon:
        st.subheader(t("surv_my_mon"))
        surv_query = st.text_input(t("surv_name_label"), key="surv_mon", placeholder="Garchomp / 烈咬陸鯊")
        surv_nature_name = st.selectbox(
            t("surv_nature_label"),
            options=["Hardy", "Bold", "Impish", "Relaxed", "Lax", t("surv_nature_other")],
            key="surv_nature",
        )
        if surv_nature_name == t("surv_nature_other"):
            surv_nature_name = st.text_input(t("surv_nature_input"), key="surv_nature_input")

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

    if st.button(t("surv_button"), key="surv_calc") and surv_query:
        try:
            surv_nature = NatureRegistry.get_by_name(surv_nature_name)
        except ValueError as e:
            st.error(t("nature_invalid").format(error=e))
            st.stop()

        surv_results = svc["local"].fuzzy_match(surv_query)

        if not surv_results:
            st.error(t("surv_not_found").format(name=surv_query))
        else:
            mon = dataclasses.replace(surv_results[0], nature=surv_nature)
            attack = AttackInput(
                power=power,
                attacker_atk=attacker_atk,
                is_physical=is_physical,
                type_multiplier=type_mult,
            )
            prefer_hp, prefer_def = svc["survival"].optimize(mon, attack)

            st.divider()

            # optimize() returns survived=False for both results when impossible;
            # both flags are identical by service contract.
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
