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

# ── Speed Tab (placeholder UI) ───────────────────────────────────────────────
with tab_speed:
    st.header("超速分析")
    st.info("功能開發中，敬請期待。")

# ── Survival Tab (placeholder UI) ────────────────────────────────────────────
with tab_survival:
    st.header("存活分析")
    st.info("功能開發中，敬請期待。")
