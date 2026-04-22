import streamlit as st
from adapters.poke_api_repository import PokeApiRepository
from adapters.csv_name_provider import CsvNameProvider
from application.calculator import StatCalculator
from application.search_service import SearchService
from application.speed_service import SpeedService
from application.survival_service import SurvivalService
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
        from domain.models.nature import NatureRegistry

        my_results  = svc["search"].search(my_query)
        tgt_results = svc["search"].search(tgt_query)

        if not my_results:
            st.error(f"找不到我方寶可夢：{my_query}")
        elif not tgt_results:
            st.error(f"找不到目標寶可夢：{tgt_query}")
        else:
            import dataclasses
            my_mon  = dataclasses.replace(my_results[0],  nature=NatureRegistry.get_by_name(my_nature_name))
            tgt_mon = dataclasses.replace(tgt_results[0], nature=NatureRegistry.get_by_name(tgt_nature_name))
            result  = svc["speed"].min_sp_to_outspeed(my_mon, tgt_mon)

            st.divider()
            if result.sp_needed == -1:
                st.error(f"❌ 即使投入所有 SP，{my_mon.name_zh} 仍無法超越 {tgt_mon.name_zh}（速度差距過大）。")
            else:
                st.success(f"✅ 需要 **SP_Speed = {result.sp_needed}** 點")
                cols = st.columns(3)
                cols[0].metric("所需 SP", result.sp_needed)
                cols[1].metric(f"{my_mon.name_zh} 速度", result.my_speed)
                cols[2].metric(f"{tgt_mon.name_zh} 速度", result.target_speed)

# ── Survival Tab (placeholder UI) ────────────────────────────────────────────
with tab_survival:
    st.header("存活分析")
    st.info("功能開發中，敬請期待。")
