import dataclasses
import streamlit as st
from adapters.poke_api_repository import PokeApiRepository
from adapters.csv_name_provider import CsvNameProvider
from application.calculator import StatCalculator
from application.search_service import SearchService
from application.speed_service import SpeedService
from application.survival_service import AttackInput, SurvivalService
from domain.models.nature import NatureRegistry
from shared.config import CSV_PATH, CACHE_DIR

st.set_page_config(page_title="Pokémon Champions 2026", layout="wide")


@st.cache_resource
def build_services() -> dict:
    repo  = PokeApiRepository(CACHE_DIR)
    csv   = CsvNameProvider(CSV_PATH)
    calc  = StatCalculator()
    return {
        "repo":     repo,
        "search":   SearchService(repo, csv),
        "speed":    SpeedService(calc),
        "survival": SurvivalService(calc),
    }


svc = build_services()

st.title("Pokémon Champions 2026 — 競技策略工具箱")

tab_search, tab_speed, tab_survival = st.tabs(["🔍 寶可夢查詢", "⚡ 超速分析", "🛡️ 存活分析"])

# ── Search Tab ──────────────────────────────────────────────────────────────
with tab_search:
    st.header("寶可夢查詢")
    query = st.text_input("輸入名稱（繁中 / English / 日本語）", placeholder="烈咬陸鯊 / Garchomp / ガブリアス")

    if query:
        with st.spinner("搜尋中..."):
            results = svc["search"].search(query)

        if not results:
            st.warning("找不到符合的寶可夢，請確認名稱是否正確。")
        else:
            for p in results:
                col_img, col_info = st.columns([1, 3])
                with col_img:
                    if p.sprite_url:
                        st.image(p.sprite_url, width=160)
                with col_info:
                    st.subheader(f"{p.name_zh}　{p.name_en.title()}　{p.name_ja}")
                    st.caption("屬性：" + " / ".join(p.types))
                    b = p.base_stats
                    st.table({
                        "能力": ["HP", "攻擊", "防禦", "特攻", "特防", "速度"],
                        "種族值": [b.hp, b.attack, b.defense, b.sp_attack, b.sp_defense, b.speed],
                    })

# ── Speed Tab ────────────────────────────────────────────────────────────────
with tab_speed:
    st.header("⚡ 超速分析")
    st.caption("計算超越目標對手（速度+1）所需的最小 SP_Speed 分配。目標寶可夢假設 SP_Speed = 0。")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("我方寶可夢")
        my_query = st.text_input("名稱", key="speed_my", placeholder="Garchomp / 烈咬陸鯊")
        my_nature_name = st.selectbox(
            "性格",
            options=["Hardy", "Timid", "Jolly", "Hasty", "Naive",
                     "Brave", "Relaxed", "Quiet", "Sassy", "其他..."],
            key="speed_my_nature",
        )
        if my_nature_name == "其他...":
            my_nature_name = st.text_input("輸入性格名稱（中/英/日）", key="speed_my_nature_input")

    with col2:
        st.subheader("目標寶可夢")
        tgt_query = st.text_input("名稱", key="speed_tgt", placeholder="Kyogre / 蓋歐卡")
        tgt_nature_name = st.selectbox(
            "性格",
            options=["Hardy", "Timid", "Jolly", "Hasty", "Naive",
                     "Brave", "Relaxed", "Quiet", "Sassy", "其他..."],
            key="speed_tgt_nature",
        )
        if tgt_nature_name == "其他...":
            tgt_nature_name = st.text_input("輸入性格名稱（中/英/日）", key="speed_tgt_nature_input")

    if st.button("計算超速 SP", key="speed_calc") and my_query and tgt_query:
        try:
            my_nature  = NatureRegistry.get_by_name(my_nature_name)
            tgt_nature = NatureRegistry.get_by_name(tgt_nature_name)
        except ValueError as e:
            st.error(f"無法識別的性格：{e}")
            st.stop()

        with st.spinner("搜尋中..."):
            my_results  = svc["search"].search(my_query)
            tgt_results = svc["search"].search(tgt_query)

        if not my_results:
            st.error(f"找不到我方寶可夢：{my_query}")
        elif not tgt_results:
            st.error(f"找不到目標寶可夢：{tgt_query}")
        else:
            my_mon  = dataclasses.replace(my_results[0],  nature=my_nature)
            tgt_mon = dataclasses.replace(tgt_results[0], nature=tgt_nature)
            result  = svc["speed"].min_sp_to_outspeed(my_mon, tgt_mon)

            st.divider()
            if result is None:
                st.error(f"❌ 即使投入所有 SP，{my_mon.name_zh} 仍無法超越 {tgt_mon.name_zh}（速度差距過大）。")
            else:
                st.success(f"✅ 需要 **SP_Speed = {result.sp_needed}** 點")
                cols = st.columns(3)
                cols[0].metric("所需 SP", result.sp_needed)
                cols[1].metric(f"{my_mon.name_zh} 速度", result.my_speed)
                cols[2].metric(f"{tgt_mon.name_zh} 速度", result.target_speed)

# ── Survival Tab ─────────────────────────────────────────────────────────────
with tab_survival:
    st.header("🛡️ 存活分析")
    st.caption("找出能扛下特定攻擊的最小 SP_HP + SP_Def 總和，同時呈現偏HP與偏防禦兩種最優方案。")

    col_mon, col_atk = st.columns(2)

    with col_mon:
        st.subheader("我方寶可夢")
        surv_query = st.text_input("名稱", key="surv_mon", placeholder="Garchomp / 烈咬陸鯊")
        surv_nature_name = st.selectbox(
            "性格",
            options=["Hardy", "Bold", "Impish", "Relaxed", "Lax", "其他..."],
            key="surv_nature",
        )
        if surv_nature_name == "其他...":
            surv_nature_name = st.text_input("輸入性格名稱（中/英/日）", key="surv_nature_input")

    with col_atk:
        st.subheader("攻擊參數")
        power        = st.number_input("招式威力", min_value=1, max_value=250, value=120, key="surv_power")
        attacker_atk = st.number_input("攻擊方實際攻擊力", min_value=1, max_value=999, value=200, key="surv_atk")
        is_physical  = st.radio("攻擊類別", ["物理", "特殊"], key="surv_cat") == "物理"
        type_mult    = st.select_slider(
            "屬性相性",
            options=[0.25, 0.5, 1.0, 2.0, 4.0],
            value=1.0,
            key="surv_mult",
        )

    if st.button("計算最佳存活分配", key="surv_calc") and surv_query:
        try:
            surv_nature = NatureRegistry.get_by_name(surv_nature_name)
        except ValueError as e:
            st.error(f"無法識別的性格：{e}")
            st.stop()

        with st.spinner("搜尋中..."):
            surv_results = svc["search"].search(surv_query)

        if not surv_results:
            st.error(f"找不到寶可夢：{surv_query}")
        else:
            mon = dataclasses.replace(surv_results[0], nature=surv_nature)
            attack = AttackInput(
                power=int(power),
                attacker_atk=int(attacker_atk),
                is_physical=is_physical,
                type_multiplier=float(type_mult),
            )
            prefer_hp, prefer_def = svc["survival"].optimize(mon, attack)

            st.divider()

            if not prefer_hp.survived:
                st.error("❌ 在 SP 限制內無法扛下此攻擊，請調整攻擊參數。")
            else:
                st.success(f"✅ 最小 SP 總投入：**{prefer_hp.total_sp}** 點（SP_HP + SP_Def）")

                col_a, col_b = st.columns(2)

                with col_a:
                    st.subheader("偏 HP 方案")
                    st.metric("SP_HP", prefer_hp.sp_hp)
                    st.metric("SP_Def", prefer_hp.sp_def)
                    st.metric("最終 HP", prefer_hp.final_hp)
                    st.metric("最終防禦", prefer_hp.final_def)
                    st.caption(f"合計 SP 投入：{prefer_hp.total_sp}")

                with col_b:
                    st.subheader("偏防禦方案")
                    st.metric("SP_HP", prefer_def.sp_hp)
                    st.metric("SP_Def", prefer_def.sp_def)
                    st.metric("最終 HP", prefer_def.final_hp)
                    st.metric("最終防禦", prefer_def.final_def)
                    st.caption(f"合計 SP 投入：{prefer_def.total_sp}")
