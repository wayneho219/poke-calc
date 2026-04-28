# UX Improvements v2 — Design Spec

**日期：** 2026-04-27  
**目標：** 以對戰為導向，全面改善三個頁籤的寶可夢選擇體驗、性格選擇體驗，並在查詢頁籤補充特性、相性、Mega 進化資訊。

---

## 總覽

| 頁籤 | 主要改動 |
|---|---|
| 查詢 | dropdown 選擇 → 詳情卡（特性 + 相性 + Mega） |
| 超速 | dropdown 選擇 + 5×5 性格格子 + 自動計算 |
| 存活 | dropdown 選擇 + 5×5 性格格子 + 自動計算 |
| 全部 | 屬性一律用官方 PNG badge + 依語言顯示名稱 |

---

## 一、資料層

### 1-1. `build_data.py` 擴充

現有的 `build_data.py` 需要額外抓取以下資料並寫入 `pokemon_data.json`：

#### 特性（每筆 Pokémon）

```json
"abilities": [
  {
    "name_zh": "猛火", "name_en": "Blaze", "name_ja": "もうか",
    "desc_zh": "HP 不足 1/3 時，火屬性技能威力提升 1.5 倍。",
    "desc_en": "Powers up Fire-type moves when the Pokémon's HP is low.",
    "desc_ja": "ピンチのとき、ほのおタイプの技の威力が上がる。"
  }
],
"dream_ability": {
  "name_zh": "太陽之力", "name_en": "Solar Power", "name_ja": "サンパワー",
  "desc_zh": "烈日天氣下特殊技能威力 ×1.5，每回合損失 1/8 HP。",
  "desc_en": "Boosts Sp. Atk in sunny weather, but HP decreases each turn.",
  "desc_ja": "はれのとき、とくこうが上がるが、毎ターンHPが減る。"
}
```

- 一般特性最多 2 個（slot 1 / slot 2），`is_hidden: false`
- 夢特性為 `is_hidden: true` 的那一個
- 說明文字從 PokéAPI `/ability/{id}` 抓取，優先使用最新世代的 flavor text

#### 進化鏈

- 從 PokéAPI `/pokemon-species/{id}` 取得 `evolution_chain.url`
- 遞迴解析進化鏈，若該 Pokémon 在鏈末端（無再進化）則 `is_final_evolution: true`
- 不進化的單一形態（傳說、幻、部分一般）也設為 `true`

```json
"is_final_evolution": true
```

#### Mega 進化

- 從 `/pokemon-species/{id}` 取得 `varieties`，找出含 `mega` 的 form
- 各 Mega form 從 `/pokemon/{form-name}` 取得：屬性、六項種族值、特性
- Mega sprite：從 PokéAPI HOME sprites 或 official-artwork 取得

```json
"mega_forms": [
  {
    "suffix": "mega-x",
    "name_zh": "Mega 噴火龍 X",
    "name_en": "Mega Charizard X",
    "name_ja": "メガリザードンX",
    "types": ["dragon", "fire"],
    "base_stats": {"hp": 78, "attack": 130, "defense": 111, "sp_attack": 130, "sp_defense": 85, "speed": 100},
    "ability": {
      "name_zh": "硬爪", "name_en": "Tough Claws", "name_ja": "かたいツメ",
      "desc_zh": "直接攻擊技能威力提升 1.3 倍。",
      "desc_en": "Boosts the power of contact moves.",
      "desc_ja": "直接攻撃の技の威力が上がる。"
    },
    "sprite_path": "data/sprites/mega/6-mega-x.png"
  }
]
```

### 1-2. 屬性圖片

- 下載 18 個官方屬性 PNG → `data/sprites/types/{type_name}.png`
- 來源：PokéAPI sprites repo（Generation VIII / Sword-Shield 版本）
- `data/sprites/types/` 加入 `.gitignore`（同 sprites 策略）

### 1-3. 屬性名稱 i18n

在 `shared/i18n/zh.json`、`en.json`、`ja.json` 新增 18 個屬性名稱 key：

```json
"type_fire": "火",
"type_water": "水",
...
```

### 1-4. 屬性對照表

新增 `shared/type_chart.py`：hardcode 18×18 攻防相性矩陣。

提供函式：
```python
def get_effectiveness(attacker_types: list[str], defender_types: list[str]) -> float
def get_matchups(defender_types: list[str]) -> dict[str, float]
# 回傳 {"rock": 4.0, "water": 2.0, "fire": 0.5, "ground": 0.0, ...}
```

`get_matchups` 的結果分組：
- `weaknesses`：倍率 > 1（含 2× 和 4×）
- `resistances`：倍率 < 1 且 > 0
- `immunities`：倍率 == 0

---

## 二、共用元件

### 2-1. 屬性 Badge 元件

所有頁籤顯示屬性時統一使用 HTML component 渲染：

- 官方 PNG 圖示（16×16）+ 當前語言屬性名稱
- 18 種屬性各有對應官方底色（CSS fallback，圖片載入失敗時）
- 實作為 `interfaces/streamlit/components/type_badge.py`，回傳 HTML 字串，由呼叫方用 `st.components.v1.html` 渲染

### 2-1-a. Domain Model 更新

`domain/models/pokemon.py` 的 `Pokemon` dataclass 需新增欄位：
- `is_final_evolution: bool = False`
- `abilities: list = field(default_factory=list)`
- `dream_ability: dict | None = None`
- `mega_forms: list = field(default_factory=list)`

`LocalJsonRepository` 需同步解析上述新欄位。fixture JSON 需更新。

---

### 2-2. Pokémon Dropdown 元件

三個頁籤共用，實作為可復用的 function：

```python
def pokemon_selector(key: str, label: str, repo: LocalJsonRepository, lang: str) -> Pokemon | None
```

行為：
- `st.text_input` 接受輸入
- 輸入後即時呼叫 `repo.fuzzy_match(query)`，最多顯示 8 筆候選
- 候選排序：`is_final_evolution=True` 優先，其餘依 ID 升冪
- 候選以 `st.button` 列表顯示，各含小圖示 + 名字（依語言）+ 屬性 badge
- 選定後顯示確認卡（圖示 + 名字 + 屬性 + 速度），清空候選列表
- 回傳選定的 `Pokemon` 物件，未選定時回傳 `None`

### 2-3. 性格格子元件

```python
def nature_selector(key: str, lang: str) -> str | None
# 回傳性格英文名稱（與 NatureRegistry 相容），未選定時回傳 None
```

- 5×5 `st.columns` 排列，25 個 `st.button`
- 按鈕文字依語言顯示（需在 i18n 加 25 個性格 key）
- 對角線（中性性格）用灰色 `disabled` 樣式
- 已選定的格子用高亮色顯示
- 每個格子 tooltip 顯示「+速度 / -攻擊」格式的加成說明

---

## 三、查詢頁籤

### 3-1. 輸入區

- 替換現有 card grid 為 `pokemon_selector` 元件
- 選定後展開詳情卡，候選列表收起

### 3-2. 詳情卡

```
[圖片]  名字（三語）
        屬性 badge × N
        HP / 攻擊 / 防禦 / 特攻 / 特防 / 速度

▸ 屬性相性
  弱點：4× [badge...] 2× [badge...]
  抵抗：½× [badge...] ¼× [badge...]
  免疫：0× [badge...]

▸ 特性
  [猛火] [夢：太陽之力（紫色）]
  ┌────────────────────────┐
  │ 點擊特性後說明顯示於此  │
  └────────────────────────┘

▸ Mega 進化（若有）
  ┌─ Mega X ──────────────┐
  │ [Mega 圖片]            │
  │ 屬性 badge             │
  │ 數值（高於原本者標紅）  │
  │ 特性（可點擊查說明）   │
  └───────────────────────┘
```

---

## 四、超速頁籤

- 我方 / 目標各使用 `pokemon_selector`
- 性格各使用 `nature_selector`（5×5 格子）
- 目標 SP 輸入（0–32）保留
- **移除「計算」按鈕**：`svc["local"]` 中我方和目標都已選定時自動計算
- 計算結果區保持現有格式（速度預覽 caption + success/error + 三欄 metric）

---

## 五、存活頁籤

- 寶可夢使用 `pokemon_selector`
- 性格使用 `nature_selector`（5×5 格子）
- **移除「計算」按鈕**：寶可夢選定後即自動計算
- 計算結果區保持現有格式

---

## 六、測試策略

- `shared/type_chart.py`：unit test 覆蓋已知相性（噴火龍弱點岩石 4×、免疫地面 0×）
- `pokemon_selector`：用 fixture JSON 測試排序（最終進化優先）、選定後回傳正確 Pokemon
- `nature_selector`：測試選定後回傳正確英文名稱
- `build_data.py`：用 mock HTTP 測試新欄位正確寫入
- UI：手動測試三個頁籤的互動流程

---

## 七、不在此次範圍內

- Gigantamax / 地區形態的特殊處理（留待下一輪）
- 超速 / 存活頁籤顯示寶可夢屬性相性（只在查詢頁籤顯示）
- 特性的遊戲機制完整解說（只顯示 PokéAPI 的 flavor text）
