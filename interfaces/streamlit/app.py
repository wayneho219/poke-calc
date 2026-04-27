import dataclasses
import streamlit as st
from adapters.local_json_repository import LocalJsonRepository
from application.calculator import StatCalculator
from application.speed_service import SpeedService
from application.survival_service import AttackInput, SurvivalService
from domain.models.nature import NatureRegistry, BattleStat
from shared.config import DATA_JSON_PATH, SPRITES_DIR
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
            my_mon  = dataclasses.replace(my_results[0],  nature=my_nature)
            tgt_mon = dataclasses.replace(tgt_results[0], nature=tgt_nature)
            result  = svc["speed"].min_sp_to_outspeed(my_mon, tgt_mon)

            st.divider()
            if result is None:
                st.error(t("speed_cannot_outspeed").format(my=my_mon.name_zh, tgt=tgt_mon.name_zh))
            else:
                st.success(t("speed_success").format(sp=result.sp_needed))
                cols = st.columns(3)
                cols[0].metric(t("speed_metric_sp"), result.sp_needed)
                cols[1].metric(t("speed_metric_speed").format(name=my_mon.name_zh), result.my_speed)
                cols[2].metric(t("speed_metric_speed").format(name=tgt_mon.name_zh), result.target_speed)

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
