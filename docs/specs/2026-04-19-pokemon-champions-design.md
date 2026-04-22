# Pokémon Champions 2026 — 競技對戰策略工具箱 設計文件

**日期**：2026-04-19
**狀態**：已核准，待實作

---

## 1. 專案概述

一個基於 2026 新制賽制規則的寶可夢競技對戰策略計算工具，以 Streamlit 作為初期 UI 介面。設計上嚴格遵循 Clean Architecture，確保未來可平滑遷移至行動 App（Flutter + FastAPI）。

### 核心功能

- **三語寶可夢搜尋**：支援繁體中文、英文、日文模糊匹配，並顯示 Pokémon HOME 高畫質圖片
- **超速分析（SpeedService）**：計算超越目標對手所需的最小 SP_Speed 分配
- **存活分析（SurvivalService）**：找出能扛下特定攻擊的最小 SP_HP + SP_Def 總和，並同時呈現「偏HP版」與「偏防禦版」兩個最優方案

---

## 2. 賽制規則（2026）

| 參數 | 值 |
|---|---|
| 個體值（IVs） | 全數固定為 31 |
| SP 總點數上限 | 66 |
| 單項 SP 上限 | 32 |
| 對戰等級 | 50 |

### 等級 50 計算公式

$$HP = Base_{HP} + 75 + SP_{HP}$$

$$其餘能力值 = \lfloor (Base + 20 + SP) \times 性格修正 \rfloor$$

性格修正值：`0.9`（下降）、`1.0`（中性）、`1.1`（上升）

---

## 3. 架構選型

### 方案：DDD 四層 Clean Architecture（方案 C）

選擇理由：
- 與微服務架構思維對齊，維護認知負擔低
- 未來拆分微服務時邊界最清晰
- `interfaces/` 層完全隔離，替換為 FastAPI + Flutter 只需加目錄

### 依賴方向（嚴格單向）

```
interfaces  →  application  →  domain
adapters    →  application  →  domain
adapters    →  domain
interfaces  →  adapters（透過建構子注入）
shared      ←  所有層皆可使用
```

`domain/` 層零外部 import，只使用 Python 標準庫。

---

## 4. 目錄結構

```
pokemon_champions/
├── domain/
│   ├── models/
│   │   ├── pokemon.py          # Pokemon dataclass
│   │   ├── stats.py            # StatSet, SPAllocation dataclasses
│   │   ├── move.py             # Move dataclass
│   │   └── nature.py           # Nature, BattleStat, NatureRegistry
│   └── repositories/
│       └── abstract.py         # AbstractPokeRepository（ABC）
│
├── application/
│   ├── calculator.py           # StatCalculator（等級50公式）
│   ├── speed_service.py        # SpeedService
│   ├── survival_service.py     # SurvivalService
│   └── search_service.py       # SearchService（三語模糊匹配）
│
├── adapters/
│   ├── poke_api_repository.py  # PokeApiRepository（API + JSON快取）
│   ├── csv_name_provider.py    # CsvNameProvider（三語對照表）
│   └── cache/                  # {pokemon_id}.json 快取目錄
│
├── shared/
│   ├── config.py               # 路徑設定（相對路徑，部署安全）
│   └── exceptions.py           # PokemonNotFoundError 等
│
├── data/
│   └── pokemon_names.csv       # 三語名稱對照表（id, name_en, name_zh, name_ja）
│
├── interfaces/
│   └── streamlit/
│       └── app.py              # Streamlit 入口點（Tab UI）
│
├── pyproject.toml
└── requirements.txt
```

---

## 5. 領域模型（Domain Models）

### `domain/models/nature.py`

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, ClassVar

class BattleStat(Enum):
    ATTACK    = "attack"
    DEFENSE   = "defense"
    SP_ATTACK = "sp_attack"
    SP_DEFENSE= "sp_defense"
    SPEED     = "speed"

@dataclass(frozen=True)
class Nature:
    name_en: str
    name_zh: str
    name_ja: str
    boosted: Optional[BattleStat]
    reduced: Optional[BattleStat]

    def modifier(self, stat: BattleStat) -> float:
        if self.boosted == stat: return 1.1
        if self.reduced == stat: return 0.9
        return 1.0

class NatureRegistry:
    """支援中文、英文、日文三語查詢，以及依上升/下降能力值查詢"""

    @classmethod
    def get_by_name(cls, name: str) -> Nature: ...

    @classmethod
    def find_by_boosted(cls, boosted: BattleStat) -> list[Nature]:
        """找出所有該能力上升的性格（不限下降項）"""
        ...

    @classmethod
    def find_by_reduced(cls, reduced: BattleStat) -> list[Nature]:
        """找出所有該能力下降的性格（不限上升項）"""
        ...

    @classmethod
    def find_by_stats(
        cls,
        boosted: BattleStat,
        reduced: BattleStat,
    ) -> list[Nature]:
        """精確比對：上升與下降能力皆指定，最多回傳一個結果"""
        ...
```

> `find_by_stats` 兩個參數皆為必填（無 `Optional`），語義明確。若只想查「速度上升的所有性格」，使用 `find_by_boosted(BattleStat.SPEED)`。

全部 25 種性格皆收錄於 `ALL_NATURES` 常數列表，含三語名稱。

### `domain/models/stats.py`

```python
@dataclass(frozen=True)
class StatSet:
    hp: int; attack: int; defense: int
    sp_attack: int; sp_defense: int; speed: int

@dataclass(frozen=True)
class SPAllocation:
    hp: int = 0; attack: int = 0; defense: int = 0
    sp_attack: int = 0; sp_defense: int = 0; speed: int = 0

    def total(self) -> int: ...
    def validate(self) -> bool:  # 單項 ≤ 32，總和 ≤ 66
```

### `domain/models/pokemon.py`

```python
@dataclass(frozen=True)
class Pokemon:
    id: int
    name_en: str
    name_zh: str
    name_ja: str
    base_stats: StatSet
    types: list[str]
    nature: Nature = field(default_factory=lambda: NatureRegistry.get_by_name("Hardy"))
    sprite_url: str = ""        # Pokémon HOME 高畫質圖（front_default）
    sprite_shiny_url: str = ""  # 異色 HOME 圖
```

### `domain/repositories/abstract.py`

```python
class AbstractPokeRepository(ABC):
    @abstractmethod
    def get_by_id(self, pokemon_id: int, name_zh: str, name_ja: str) -> Pokemon: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Pokemon: ...

    @abstractmethod
    def search(self, query: str) -> list[Pokemon]: ...
```

---

## 6. Application Services

### StatCalculator

- `calc_hp(base, sp) → int`：套用 HP 公式
- `calc_stat(base, sp, nature, stat) → int`：套用其餘能力公式（含 `floor`）
- `calc_all(pokemon, allocation) → StatSet`：一次計算全部六項

### SpeedService

- 輸入：我方 `Pokemon`、目標 `Pokemon`
- 輸出：`SpeedResult(sp_needed, my_speed, target_speed)`
- `sp_needed = -1` 表示全投仍無法超速
- 目標寶可夢預設 SP_Speed = 0（最保守估計）

### SurvivalService（解析法）

- 輸入：我方 `Pokemon`、`AttackInput(power, attacker_atk, is_physical, type_multiplier)`
- 演算法：遍歷 SP_HP（0–32），對每個 HP 值解析出最小 SP_Def，收集所有最優解
- 輸出：`tuple[SurvivalResult, SurvivalResult]`
  - `prefer_hp`：SP_HP 最大的並列最優方案
  - `prefer_def`：SP_Def 最大的並列最優方案
- 傷害公式：`floor((22 × power × atk / def / 50 + 2) × type_multiplier)`（最大傷害，不含隨機因子）

### SearchService（三語模糊匹配）

- 輸入：任意語言的查詢字串
- 流程：CSV 模糊匹配 → 找到則批次查詢 Repository → 找不到則 fallback 至 PokéAPI 英文名查詢
- 輸出：`list[Pokemon]`

---

## 7. Adapters

### CsvNameProvider

- 讀取 `data/pokemon_names.csv`（欄位：`id, name_en, name_zh, name_ja`）
- `fuzzy_match(query) → list[int]`：三語子字串匹配，回傳 pokemon_id 列表

### PokeApiRepository

- `get_by_id`：查本地 JSON 快取，未命中則打 API 並存檔
- 快取路徑：`adapters/cache/{pokemon_id}.json`
- Sprite 來源：`sprites.other.home.front_default`（HOME 3D 渲染圖）
- 涵蓋範圍：Gen 1–9 全國圖鑑 + 所有變形（地區、Mega、究極爆發等）

---

## 8. Streamlit UI（interfaces/streamlit/app.py）

### 頁面結構

`st.tabs` 三個頁籤：

| 頁籤 | 功能 |
|---|---|
| 🔍 寶可夢查詢 | 三語搜尋 + HOME 圖片展示 + 基礎數值顯示 |
| ⚡ 超速分析 | 輸入我方 & 目標寶可夢 → 顯示最小 SP_Speed 與達成速度值 |
| 🛡️ 存活分析 | 輸入我方寶可夢 & 攻擊參數 → 顯示偏HP版 & 偏防禦版兩個最優方案 |

### 關鍵設計原則

- Services 透過 `@st.cache_resource` 初始化一次，跨 session 共享
- Services 為純函數介面（接受參數、回傳結果），不依賴 `st.session_state`
- 圖片透過 `st.image(sprite_url)` 直接從 PokéAPI CDN 顯示

---

## 9. 路徑與設定

`shared/config.py` 使用 `Path(__file__).parent.parent` 計算根目錄，所有路徑為相對路徑，確保：
- 本地開發正常運作
- 部署至伺服器或 Docker 時無需修改
- 未來打包為行動 App 時路徑可替換

---

## 10. 未來行動化路徑

```
現在：       Streamlit → application/ → domain/
未來選項A：  Flutter（純前端，重寫計算為 Dart）
未來選項B：  Flutter → FastAPI → application/ → domain/（Python 邏輯零改動）
```

選項 B 只需在 `interfaces/` 新增 `fastapi/` 目錄，`application/` 與 `domain/` 完全不動。

---

## 11. 技術依賴

```
Python      >= 3.11
streamlit   >= 1.35
requests    >= 2.31
```

無 ORM，無資料庫，無 async（現階段不需要）。
