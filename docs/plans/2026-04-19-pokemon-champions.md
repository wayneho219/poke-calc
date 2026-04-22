# Pokémon Champions 2026 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a competitive Pokémon strategy toolbox for the 2026 format, with trilingual search, speed analysis, and survival optimization, backed by a Clean Architecture that can later be extended to a mobile app.

**Architecture:** DDD four-layer Clean Architecture (domain / application / adapters / interfaces). All dependencies point inward; `domain/` has zero external imports. Services are pure functions injected via constructors, making unit tests trivial.

**Tech Stack:** Python 3.11+, Streamlit 1.35+, requests 2.31+, pytest

---

## File Map

| File | Responsibility |
|---|---|
| `domain/models/nature.py` | `BattleStat`, `Nature`, `ALL_NATURES`, `NatureRegistry` |
| `domain/models/stats.py` | `StatSet`, `SPAllocation` |
| `domain/models/move.py` | `Move` |
| `domain/models/pokemon.py` | `Pokemon` |
| `domain/repositories/abstract.py` | `AbstractPokeRepository` ABC |
| `shared/config.py` | Root-relative paths |
| `shared/exceptions.py` | `PokemonNotFoundError` |
| `application/calculator.py` | `StatCalculator` (lv50 formulas) |
| `application/speed_service.py` | `SpeedService`, `SpeedResult` |
| `application/survival_service.py` | `SurvivalService`, `SurvivalResult`, `AttackInput` |
| `application/search_service.py` | `SearchService` (trilingual) |
| `adapters/csv_name_provider.py` | `CsvNameProvider`, `NameRecord` |
| `adapters/poke_api_repository.py` | `PokeApiRepository` |
| `scripts/build_csv.py` | One-time script to build `pokemon_names.csv` |
| `interfaces/streamlit/app.py` | Streamlit tab UI entry point |
| `tests/domain/test_nature.py` | Nature tests |
| `tests/domain/test_stats.py` | Stats tests |
| `tests/application/test_calculator.py` | Calculator tests |
| `tests/application/test_speed_service.py` | Speed tests |
| `tests/application/test_survival_service.py` | Survival tests |
| `tests/adapters/test_csv_name_provider.py` | CSV provider tests |
| `tests/application/test_search_service.py` | Search tests |

---

## Task 1: Project Setup

**Files:**
- Create: `poke-calc/` (project root)
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: all `__init__.py` files

- [ ] **Step 1: Create project directory structure**

```bash
cd /Users/wayneho
mkdir -p poke-calc/{domain/{models,repositories},application,adapters/cache,shared,data,interfaces/streamlit,scripts,tests/{domain,application,adapters}}
touch poke-calc/domain/__init__.py
touch poke-calc/domain/models/__init__.py
touch poke-calc/domain/repositories/__init__.py
touch poke-calc/application/__init__.py
touch poke-calc/adapters/__init__.py
touch poke-calc/shared/__init__.py
touch poke-calc/interfaces/__init__.py
touch poke-calc/interfaces/streamlit/__init__.py
touch poke-calc/tests/__init__.py
touch poke-calc/tests/domain/__init__.py
touch poke-calc/tests/application/__init__.py
touch poke-calc/tests/adapters/__init__.py
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "pokemon-champions"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "streamlit>=1.35",
    "requests>=2.31",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-mock>=3.12"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.setuptools.packages.find]
where = ["."]
```

- [ ] **Step 3: Create `requirements.txt`**

```
streamlit>=1.35
requests>=2.31
pytest>=8.0
pytest-mock>=3.12
```

- [ ] **Step 4: Install dependencies**

```bash
cd /Users/wayneho/poke-calc
pip install -e ".[dev]"
```

Expected: No errors. `streamlit`, `requests`, `pytest` all installed.

- [ ] **Step 5: Verify pytest runs**

```bash
cd /Users/wayneho/poke-calc
python -m pytest --co -q
```

Expected: `no tests ran` (no tests yet, exit code 5 is OK).

- [ ] **Step 6: Commit**

```bash
cd /Users/wayneho/poke-calc
git init
git add pyproject.toml requirements.txt
git commit -m "chore: initialize project structure"
```

---

## Task 2: Domain — Nature System

**Files:**
- Create: `domain/models/nature.py`
- Create: `tests/domain/test_nature.py`

- [ ] **Step 1: Write failing tests**

Create `tests/domain/test_nature.py`:

```python
import pytest
from domain.models.nature import BattleStat, Nature, NatureRegistry, ALL_NATURES

ATK = BattleStat.ATTACK
DEF = BattleStat.DEFENSE
SPA = BattleStat.SP_ATTACK
SPD = BattleStat.SP_DEFENSE
SPE = BattleStat.SPEED


class TestNatureModifier:
    def test_boosted_stat_returns_1_1(self):
        jolly = NatureRegistry.get_by_name("Jolly")
        assert jolly.modifier(SPE) == 1.1

    def test_reduced_stat_returns_0_9(self):
        jolly = NatureRegistry.get_by_name("Jolly")
        assert jolly.modifier(SPA) == 0.9

    def test_neutral_stat_returns_1_0(self):
        jolly = NatureRegistry.get_by_name("Jolly")
        assert jolly.modifier(ATK) == 1.0

    def test_neutral_nature_all_stats_1_0(self):
        hardy = NatureRegistry.get_by_name("Hardy")
        for stat in BattleStat:
            assert hardy.modifier(stat) == 1.0


class TestNatureRegistry:
    def test_get_by_english_name(self):
        n = NatureRegistry.get_by_name("Jolly")
        assert n.name_en == "Jolly"

    def test_get_by_english_name_case_insensitive(self):
        n = NatureRegistry.get_by_name("jolly")
        assert n.name_en == "Jolly"

    def test_get_by_traditional_chinese(self):
        n = NatureRegistry.get_by_name("爽朗")
        assert n.name_en == "Jolly"

    def test_get_by_japanese(self):
        n = NatureRegistry.get_by_name("ようき")
        assert n.name_en == "Jolly"

    def test_get_by_unknown_raises(self):
        with pytest.raises(ValueError):
            NatureRegistry.get_by_name("InvalidNature")

    def test_find_by_boosted_speed(self):
        results = NatureRegistry.find_by_boosted(SPE)
        names = {n.name_en for n in results}
        assert names == {"Timid", "Hasty", "Jolly", "Naive"}

    def test_find_by_reduced_speed(self):
        results = NatureRegistry.find_by_reduced(SPE)
        names = {n.name_en for n in results}
        assert names == {"Brave", "Relaxed", "Quiet", "Sassy"}

    def test_find_by_stats_exact(self):
        results = NatureRegistry.find_by_stats(SPE, SPA)
        assert len(results) == 1
        assert results[0].name_en == "Jolly"

    def test_all_natures_count(self):
        assert len(ALL_NATURES) == 25
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/wayneho/poke-calc
python -m pytest tests/domain/test_nature.py -v
```

Expected: `ModuleNotFoundError: No module named 'domain'`

- [ ] **Step 3: Implement `domain/models/nature.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional, ClassVar


class BattleStat(Enum):
    ATTACK    = "attack"
    DEFENSE   = "defense"
    SP_ATTACK = "sp_attack"
    SP_DEFENSE = "sp_defense"
    SPEED     = "speed"


@dataclass(frozen=True)
class Nature:
    name_en: str
    name_zh: str
    name_ja: str
    boosted: Optional[BattleStat]
    reduced: Optional[BattleStat]

    def modifier(self, stat: BattleStat) -> float:
        if self.boosted == stat:
            return 1.1
        if self.reduced == stat:
            return 0.9
        return 1.0


_A = BattleStat.ATTACK
_D = BattleStat.DEFENSE
_SA = BattleStat.SP_ATTACK
_SD = BattleStat.SP_DEFENSE
_S = BattleStat.SPEED

ALL_NATURES: list[Nature] = [
    Nature("Hardy",   "勤奮", "がんばりや", None, None),
    Nature("Lonely",  "孤獨", "さみしがり", _A,  _D),
    Nature("Brave",   "勇敢", "ゆうかん",   _A,  _S),
    Nature("Adamant", "固執", "いじっぱり", _A,  _SA),
    Nature("Naughty", "頑皮", "やんちゃ",   _A,  _SD),
    Nature("Bold",    "大膽", "ずぶとい",   _D,  _A),
    Nature("Docile",  "坦率", "すなお",     None, None),
    Nature("Relaxed", "悠閒", "のんき",     _D,  _S),
    Nature("Impish",  "淘氣", "わんぱく",   _D,  _SA),
    Nature("Lax",     "樂天", "のうてんき", _D,  _SD),
    Nature("Timid",   "膽小", "おくびょう", _S,  _A),
    Nature("Hasty",   "急躁", "せっかち",   _S,  _D),
    Nature("Serious", "認真", "まじめ",     None, None),
    Nature("Jolly",   "爽朗", "ようき",     _S,  _SA),
    Nature("Naive",   "天真", "むじゃき",   _S,  _SD),
    Nature("Modest",  "內斂", "ひかえめ",   _SA, _A),
    Nature("Mild",    "溫和", "おっとり",   _SA, _D),
    Nature("Quiet",   "冷靜", "れいせい",   _SA, _S),
    Nature("Bashful", "害羞", "てれや",     None, None),
    Nature("Rash",    "浮躁", "うっかりや", _SA, _SD),
    Nature("Calm",    "溫順", "おだやか",   _SD, _A),
    Nature("Gentle",  "溫柔", "おとなしい", _SD, _D),
    Nature("Sassy",   "自大", "なまいき",   _SD, _S),
    Nature("Careful", "慎重", "しんちょう", _SD, _SA),
    Nature("Quirky",  "浮躁", "きまぐれ",   None, None),
]


class NatureRegistry:
    _by_name: ClassVar[dict[str, Nature]] = {
        **{n.name_en.lower(): n for n in ALL_NATURES},
        **{n.name_zh: n for n in ALL_NATURES},
        **{n.name_ja: n for n in ALL_NATURES},
    }

    @classmethod
    def get_by_name(cls, name: str) -> Nature:
        result = cls._by_name.get(name.strip().lower()) or cls._by_name.get(name.strip())
        if result is None:
            raise ValueError(f"未知性格：{name}")
        return result

    @classmethod
    def find_by_boosted(cls, boosted: BattleStat) -> list[Nature]:
        return [n for n in ALL_NATURES if n.boosted == boosted]

    @classmethod
    def find_by_reduced(cls, reduced: BattleStat) -> list[Nature]:
        return [n for n in ALL_NATURES if n.reduced == reduced]

    @classmethod
    def find_by_stats(cls, boosted: BattleStat, reduced: BattleStat) -> list[Nature]:
        return [n for n in ALL_NATURES if n.boosted == boosted and n.reduced == reduced]
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd /Users/wayneho/poke-calc
python -m pytest tests/domain/test_nature.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add domain/models/nature.py tests/domain/test_nature.py
git commit -m "feat: add Nature domain model with trilingual NatureRegistry"
```

---

## Task 3: Domain — Stats System

**Files:**
- Create: `domain/models/stats.py`
- Create: `tests/domain/test_stats.py`

- [ ] **Step 1: Write failing tests**

Create `tests/domain/test_stats.py`:

```python
import pytest
from domain.models.stats import StatSet, SPAllocation


class TestSPAllocation:
    def test_total_sums_all_fields(self):
        sp = SPAllocation(hp=10, attack=5, defense=3, sp_attack=0, sp_defense=8, speed=12)
        assert sp.total() == 38

    def test_default_total_is_zero(self):
        assert SPAllocation().total() == 0

    def test_validate_passes_within_limits(self):
        sp = SPAllocation(hp=32, speed=32, defense=2)
        assert sp.validate() is True

    def test_validate_fails_if_total_exceeds_66(self):
        sp = SPAllocation(hp=32, attack=32, defense=3)
        assert sp.validate() is False

    def test_validate_fails_if_single_stat_exceeds_32(self):
        sp = SPAllocation(hp=33)
        assert sp.validate() is False

    def test_validate_fails_if_negative(self):
        sp = SPAllocation(hp=-1)
        assert sp.validate() is False

    def test_validate_passes_at_exact_limits(self):
        sp = SPAllocation(hp=32, attack=32, defense=2)
        assert sp.total() == 66
        assert sp.validate() is True
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/domain/test_stats.py -v
```

Expected: `ModuleNotFoundError: No module named 'domain.models.stats'`

- [ ] **Step 3: Implement `domain/models/stats.py`**

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class StatSet:
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int


@dataclass(frozen=True)
class SPAllocation:
    hp: int = 0
    attack: int = 0
    defense: int = 0
    sp_attack: int = 0
    sp_defense: int = 0
    speed: int = 0

    def total(self) -> int:
        return self.hp + self.attack + self.defense + self.sp_attack + self.sp_defense + self.speed

    def validate(self) -> bool:
        values = [self.hp, self.attack, self.defense, self.sp_attack, self.sp_defense, self.speed]
        return all(0 <= v <= 32 for v in values) and self.total() <= 66
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python -m pytest tests/domain/test_stats.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add domain/models/stats.py tests/domain/test_stats.py
git commit -m "feat: add StatSet and SPAllocation domain models"
```

---

## Task 4: Domain — Move & Pokemon

**Files:**
- Create: `domain/models/move.py`
- Create: `domain/models/pokemon.py`

- [ ] **Step 1: Implement `domain/models/move.py`**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    name: str
    power: int
    category: str       # "physical" | "special"
    type_name: str
```

- [ ] **Step 2: Implement `domain/models/pokemon.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from .nature import Nature, NatureRegistry
from .stats import StatSet


@dataclass(frozen=True)
class Pokemon:
    id: int
    name_en: str
    name_zh: str
    name_ja: str
    base_stats: StatSet
    types: list[str]
    nature: Nature = field(default_factory=lambda: NatureRegistry.get_by_name("Hardy"))
    sprite_url: str = ""
    sprite_shiny_url: str = ""
```

- [ ] **Step 3: Smoke-test imports**

```bash
python -c "from domain.models.pokemon import Pokemon; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add domain/models/move.py domain/models/pokemon.py
git commit -m "feat: add Move and Pokemon domain models"
```

---

## Task 5: Domain — Abstract Repository

**Files:**
- Create: `domain/repositories/abstract.py`

- [ ] **Step 1: Implement `domain/repositories/abstract.py`**

```python
from abc import ABC, abstractmethod
from domain.models.pokemon import Pokemon


class AbstractPokeRepository(ABC):

    @abstractmethod
    def get_by_id(self, pokemon_id: int, name_zh: str = "", name_ja: str = "") -> Pokemon:
        ...

    @abstractmethod
    def get_by_name(self, name: str) -> Pokemon:
        ...

    @abstractmethod
    def search(self, query: str) -> list[Pokemon]:
        ...
```

- [ ] **Step 2: Smoke-test ABC**

```bash
python -c "from domain.repositories.abstract import AbstractPokeRepository; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add domain/repositories/abstract.py
git commit -m "feat: add AbstractPokeRepository interface"
```

---

## Task 6: Shared — Config & Exceptions

**Files:**
- Create: `shared/config.py`
- Create: `shared/exceptions.py`

- [ ] **Step 1: Implement `shared/config.py`**

```python
from pathlib import Path

ROOT      = Path(__file__).parent.parent
CSV_PATH  = ROOT / "data" / "pokemon_names.csv"
CACHE_DIR = ROOT / "adapters" / "cache"
```

- [ ] **Step 2: Implement `shared/exceptions.py`**

```python
class PokemonNotFoundError(Exception):
    def __init__(self, identifier: int | str) -> None:
        super().__init__(f"Pokemon not found: {identifier}")
        self.identifier = identifier
```

- [ ] **Step 3: Smoke-test**

```bash
python -c "from shared.config import CSV_PATH; from shared.exceptions import PokemonNotFoundError; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add shared/config.py shared/exceptions.py
git commit -m "feat: add shared config and exceptions"
```

---

## Task 7: Application — StatCalculator

**Files:**
- Create: `application/calculator.py`
- Create: `tests/application/test_calculator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/application/test_calculator.py`:

```python
from domain.models.nature import NatureRegistry, BattleStat
from domain.models.stats import StatSet, SPAllocation
from domain.models.pokemon import Pokemon
from application.calculator import StatCalculator

NEUTRAL = NatureRegistry.get_by_name("Hardy")
JOLLY   = NatureRegistry.get_by_name("Jolly")   # +Speed, -SpA

# Garchomp base stats
GARCHOMP_BASE = StatSet(hp=108, attack=130, defense=95, sp_attack=80, sp_defense=85, speed=102)


def make_garchomp(nature=NEUTRAL) -> Pokemon:
    return Pokemon(
        id=445, name_en="Garchomp", name_zh="烈咬陸鯊", name_ja="ガブリアス",
        base_stats=GARCHOMP_BASE, types=["dragon", "ground"], nature=nature,
    )


calc = StatCalculator()


class TestCalcHP:
    def test_no_sp(self):
        assert calc.calc_hp(108, 0) == 183   # 108 + 75 + 0

    def test_with_sp(self):
        assert calc.calc_hp(108, 10) == 193  # 108 + 75 + 10


class TestCalcStat:
    def test_neutral_no_sp(self):
        # int((102 + 20 + 0) * 1.0) = 122
        assert calc.calc_stat(102, 0, NEUTRAL, BattleStat.SPEED) == 122

    def test_jolly_speed_no_sp(self):
        # int((102 + 20 + 0) * 1.1) = int(134.2) = 134
        assert calc.calc_stat(102, 0, JOLLY, BattleStat.SPEED) == 134

    def test_jolly_sp_attack_reduced(self):
        # int((80 + 20 + 0) * 0.9) = int(90.0) = 90
        assert calc.calc_stat(80, 0, JOLLY, BattleStat.SP_ATTACK) == 90

    def test_floors_not_rounds(self):
        # int((102 + 20 + 4) * 1.1) = int(138.6) = 138
        assert calc.calc_stat(102, 4, JOLLY, BattleStat.SPEED) == 138


class TestCalcAll:
    def test_returns_statset_type(self):
        from domain.models.stats import StatSet
        result = calc.calc_all(make_garchomp(JOLLY), SPAllocation())
        assert isinstance(result, StatSet)

    def test_hp_matches_calc_hp(self):
        result = calc.calc_all(make_garchomp(), SPAllocation(hp=8))
        assert result.hp == calc.calc_hp(108, 8)

    def test_speed_matches_calc_stat(self):
        result = calc.calc_all(make_garchomp(JOLLY), SPAllocation(speed=4))
        assert result.speed == calc.calc_stat(102, 4, JOLLY, BattleStat.SPEED)
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/application/test_calculator.py -v
```

Expected: `ModuleNotFoundError: No module named 'application.calculator'`

- [ ] **Step 3: Implement `application/calculator.py`**

```python
from domain.models.nature import BattleStat, Nature
from domain.models.stats import StatSet, SPAllocation
from domain.models.pokemon import Pokemon


class StatCalculator:

    def calc_hp(self, base: int, sp: int) -> int:
        return base + 75 + sp

    def calc_stat(self, base: int, sp: int, nature: Nature, stat: BattleStat) -> int:
        return int((base + 20 + sp) * nature.modifier(stat))

    def calc_all(self, pokemon: Pokemon, allocation: SPAllocation) -> StatSet:
        n = pokemon.nature
        b = pokemon.base_stats
        return StatSet(
            hp         = self.calc_hp(b.hp, allocation.hp),
            attack     = self.calc_stat(b.attack,     allocation.attack,     n, BattleStat.ATTACK),
            defense    = self.calc_stat(b.defense,    allocation.defense,    n, BattleStat.DEFENSE),
            sp_attack  = self.calc_stat(b.sp_attack,  allocation.sp_attack,  n, BattleStat.SP_ATTACK),
            sp_defense = self.calc_stat(b.sp_defense, allocation.sp_defense, n, BattleStat.SP_DEFENSE),
            speed      = self.calc_stat(b.speed,      allocation.speed,      n, BattleStat.SPEED),
        )
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python -m pytest tests/application/test_calculator.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add application/calculator.py tests/application/test_calculator.py
git commit -m "feat: implement StatCalculator with lv50 formulas"
```

---

## Task 8: Application — SpeedService

**Files:**
- Create: `application/speed_service.py`
- Create: `tests/application/test_speed_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/application/test_speed_service.py`:

```python
from domain.models.nature import NatureRegistry
from domain.models.stats import StatSet
from domain.models.pokemon import Pokemon
from application.calculator import StatCalculator
from application.speed_service import SpeedService

NEUTRAL = NatureRegistry.get_by_name("Hardy")

def make_pokemon(pid: int, base_speed: int) -> Pokemon:
    return Pokemon(
        id=pid, name_en=f"Mon{pid}", name_zh="測試", name_ja="テスト",
        base_stats=StatSet(hp=100, attack=100, defense=100, sp_attack=100, sp_defense=100, speed=base_speed),
        types=["normal"],
    )


svc = SpeedService(StatCalculator())


class TestSpeedService:
    def test_no_sp_needed_already_faster(self):
        # user base 100, target base 80 (both neutral)
        # user speed = 120, target speed = 100
        user   = make_pokemon(1, 100)
        target = make_pokemon(2, 80)
        result = svc.min_sp_to_outspeed(user, target)
        assert result.sp_needed == 0
        assert result.my_speed > result.target_speed

    def test_sp_needed_to_outspeed(self):
        # user base 80 → neutral speed = 100+sp
        # target base 100 → neutral speed = 120
        # Need 100+sp > 120 → sp >= 21
        user   = make_pokemon(1, 80)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target)
        assert result.sp_needed == 21
        assert result.my_speed == 121
        assert result.target_speed == 120

    def test_cannot_outspeed_returns_minus_one(self):
        # user base 60, max speed = 112; target base 100, speed = 120
        user   = make_pokemon(1, 60)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target)
        assert result.sp_needed == -1
        assert result.my_speed == -1
        assert result.target_speed == 120

    def test_equal_base_speed_same_nature(self):
        # Both base 100 neutral: user needs sp=1 to outspeed
        user   = make_pokemon(1, 100)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target)
        assert result.sp_needed == 1
        assert result.my_speed == 121
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/application/test_speed_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'application.speed_service'`

- [ ] **Step 3: Implement `application/speed_service.py`**

```python
from dataclasses import dataclass
from domain.models.nature import BattleStat
from domain.models.pokemon import Pokemon
from application.calculator import StatCalculator


@dataclass(frozen=True)
class SpeedResult:
    sp_needed: int
    my_speed: int
    target_speed: int


class SpeedService:

    def __init__(self, calculator: StatCalculator) -> None:
        self._calc = calculator

    def min_sp_to_outspeed(self, user: Pokemon, target: Pokemon) -> SpeedResult:
        target_speed = self._calc.calc_stat(
            target.base_stats.speed, 0, target.nature, BattleStat.SPEED
        )
        for sp in range(0, 33):
            my_speed = self._calc.calc_stat(
                user.base_stats.speed, sp, user.nature, BattleStat.SPEED
            )
            if my_speed > target_speed:
                return SpeedResult(sp_needed=sp, my_speed=my_speed, target_speed=target_speed)
        return SpeedResult(sp_needed=-1, my_speed=-1, target_speed=target_speed)
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python -m pytest tests/application/test_speed_service.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add application/speed_service.py tests/application/test_speed_service.py
git commit -m "feat: implement SpeedService"
```

---

## Task 9: Application — SurvivalService

**Files:**
- Create: `application/survival_service.py`
- Create: `tests/application/test_survival_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/application/test_survival_service.py`:

```python
from domain.models.nature import NatureRegistry
from domain.models.stats import StatSet
from domain.models.pokemon import Pokemon
from application.calculator import StatCalculator
from application.survival_service import SurvivalService, AttackInput

NEUTRAL = NatureRegistry.get_by_name("Hardy")

def make_pokemon(base_hp: int, base_def: int) -> Pokemon:
    return Pokemon(
        id=1, name_en="Test", name_zh="測試", name_ja="テスト",
        base_stats=StatSet(hp=base_hp, attack=100, defense=base_def,
                           sp_attack=100, sp_defense=100, speed=100),
        types=["normal"],
    )


svc = SurvivalService(StatCalculator())

# Engineered test case (verified by hand):
# base_hp=100, base_def=100, neutral
# power=120, atk=500, physical, type_mult=1.0
# damage = int(22*120*500/def_final/50 + 2) = int(26400/def_final + 2)
# Minimum total SP = 33
# prefer_hp: sp_hp=2, sp_def=31  (HP=177, def=151, damage=176 < 177)
# prefer_def: sp_hp=1, sp_def=32  (HP=176, def=152, damage=175 < 176)
STRONG_ATTACK = AttackInput(power=120, attacker_atk=500, is_physical=True, type_multiplier=1.0)


class TestSurvivalService:
    def test_no_sp_needed_returns_zeros(self):
        # Weak attack: damage will always be less than HP
        weak_attack = AttackInput(power=40, attacker_atk=100, is_physical=True, type_multiplier=1.0)
        mon = make_pokemon(100, 100)
        prefer_hp, prefer_def = svc.optimize(mon, weak_attack)
        assert prefer_hp.total_sp == 0
        assert prefer_def.total_sp == 0
        assert prefer_hp.survived is True

    def test_minimum_total_sp_is_correct(self):
        mon = make_pokemon(100, 100)
        prefer_hp, prefer_def = svc.optimize(mon, STRONG_ATTACK)
        assert prefer_hp.total_sp == 33
        assert prefer_def.total_sp == 33

    def test_prefer_hp_has_higher_sp_hp(self):
        mon = make_pokemon(100, 100)
        prefer_hp, prefer_def = svc.optimize(mon, STRONG_ATTACK)
        assert prefer_hp.sp_hp >= prefer_def.sp_hp

    def test_prefer_def_has_higher_sp_def(self):
        mon = make_pokemon(100, 100)
        prefer_hp, prefer_def = svc.optimize(mon, STRONG_ATTACK)
        assert prefer_def.sp_def >= prefer_hp.sp_def

    def test_prefer_hp_exact_values(self):
        mon = make_pokemon(100, 100)
        prefer_hp, _ = svc.optimize(mon, STRONG_ATTACK)
        assert prefer_hp.sp_hp == 2
        assert prefer_hp.sp_def == 31
        assert prefer_hp.final_hp == 177

    def test_prefer_def_exact_values(self):
        mon = make_pokemon(100, 100)
        _, prefer_def = svc.optimize(mon, STRONG_ATTACK)
        assert prefer_def.sp_hp == 1
        assert prefer_def.sp_def == 32
        assert prefer_def.final_hp == 176

    def test_both_results_actually_survive(self):
        mon = make_pokemon(100, 100)
        prefer_hp, prefer_def = svc.optimize(mon, STRONG_ATTACK)
        assert prefer_hp.survived is True
        assert prefer_def.survived is True
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/application/test_survival_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'application.survival_service'`

- [ ] **Step 3: Implement `application/survival_service.py`**

```python
from dataclasses import dataclass
from typing import Optional
from domain.models.nature import BattleStat
from domain.models.pokemon import Pokemon
from application.calculator import StatCalculator


@dataclass(frozen=True)
class AttackInput:
    power: int
    attacker_atk: int
    is_physical: bool
    type_multiplier: float


@dataclass(frozen=True)
class SurvivalResult:
    sp_hp: int
    sp_def: int
    total_sp: int
    final_hp: int
    final_def: int
    survived: bool


class SurvivalService:

    SP_MAX = 32
    SP_TOTAL_MAX = 66

    def __init__(self, calculator: StatCalculator) -> None:
        self._calc = calculator

    def _damage(self, attack: AttackInput, def_final: int) -> int:
        return int((22 * attack.power * attack.attacker_atk / def_final / 50 + 2) * attack.type_multiplier)

    def _def_stat(self, attack: AttackInput) -> BattleStat:
        return BattleStat.DEFENSE if attack.is_physical else BattleStat.SP_DEFENSE

    def _min_sp_def_for_hp(self, pokemon: Pokemon, hp_final: int, attack: AttackInput) -> Optional[int]:
        stat = self._def_stat(attack)
        for sp_def in range(0, self.SP_MAX + 1):
            def_final = self._calc.calc_stat(pokemon.base_stats.defense, sp_def, pokemon.nature, stat)
            if self._damage(attack, def_final) < hp_final:
                return sp_def
        return None

    def optimize(self, pokemon: Pokemon, attack: AttackInput) -> tuple[SurvivalResult, SurvivalResult]:
        best_total = self.SP_TOTAL_MAX + 1
        candidates: list[SurvivalResult] = []
        stat = self._def_stat(attack)

        for sp_hp in range(0, self.SP_MAX + 1):
            hp_final = self._calc.calc_hp(pokemon.base_stats.hp, sp_hp)
            sp_def = self._min_sp_def_for_hp(pokemon, hp_final, attack)

            if sp_def is None or sp_hp + sp_def > self.SP_TOTAL_MAX:
                continue

            total = sp_hp + sp_def
            if total > best_total:
                continue

            def_final = self._calc.calc_stat(pokemon.base_stats.defense, sp_def, pokemon.nature, stat)
            result = SurvivalResult(sp_hp, sp_def, total, hp_final, def_final, True)

            if total < best_total:
                best_total = total
                candidates = [result]
            else:
                candidates.append(result)

        if not candidates:
            return (
                SurvivalResult(0, 0, 0, self._calc.calc_hp(pokemon.base_stats.hp, 0), 0, False),
                SurvivalResult(0, 0, 0, self._calc.calc_hp(pokemon.base_stats.hp, 0), 0, False),
            )

        prefer_hp  = max(candidates, key=lambda r: r.sp_hp)
        prefer_def = max(candidates, key=lambda r: r.sp_def)
        return prefer_hp, prefer_def
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python -m pytest tests/application/test_survival_service.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add application/survival_service.py tests/application/test_survival_service.py
git commit -m "feat: implement SurvivalService with analytical optimization"
```

---

## Task 10: Adapters — CsvNameProvider

**Files:**
- Create: `adapters/csv_name_provider.py`
- Create: `tests/adapters/test_csv_name_provider.py`
- Create: `tests/adapters/fixtures/test_names.csv`

- [ ] **Step 1: Create test fixture CSV**

Create `tests/adapters/fixtures/test_names.csv`:

```
id,name_en,name_zh,name_ja
25,Pikachu,皮卡丘,ピカチュウ
445,Garchomp,烈咬陸鯊,ガブリアス
248,Tyranitar,班基拉斯,バンギラス
```

- [ ] **Step 2: Write failing tests**

Create `tests/adapters/test_csv_name_provider.py`:

```python
import pytest
from pathlib import Path
from adapters.csv_name_provider import CsvNameProvider

FIXTURE = Path(__file__).parent / "fixtures" / "test_names.csv"


@pytest.fixture
def provider():
    return CsvNameProvider(FIXTURE)


class TestCsvNameProvider:
    def test_english_exact_match(self, provider):
        ids = provider.fuzzy_match("Garchomp")
        assert 445 in ids

    def test_english_partial_match(self, provider):
        ids = provider.fuzzy_match("chomp")
        assert 445 in ids

    def test_english_case_insensitive(self, provider):
        ids = provider.fuzzy_match("garchomp")
        assert 445 in ids

    def test_traditional_chinese_match(self, provider):
        ids = provider.fuzzy_match("烈咬陸鯊")
        assert 445 in ids

    def test_japanese_match(self, provider):
        ids = provider.fuzzy_match("ガブリアス")
        assert 445 in ids

    def test_partial_japanese_match(self, provider):
        ids = provider.fuzzy_match("ピカチ")
        assert 25 in ids

    def test_no_match_returns_empty(self, provider):
        ids = provider.fuzzy_match("Xyzzy")
        assert ids == []

    def test_multiple_results(self, provider):
        # "班" appears only in Tyranitar zh name
        ids = provider.fuzzy_match("班")
        assert 248 in ids
```

- [ ] **Step 3: Run to verify failure**

```bash
python -m pytest tests/adapters/test_csv_name_provider.py -v
```

Expected: `ModuleNotFoundError: No module named 'adapters.csv_name_provider'`

- [ ] **Step 4: Implement `adapters/csv_name_provider.py`**

```python
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NameRecord:
    pokemon_id: int
    name_en: str
    name_zh: str
    name_ja: str


class CsvNameProvider:

    def __init__(self, csv_path: Path) -> None:
        self._records: list[NameRecord] = self._load(csv_path)

    def _load(self, path: Path) -> list[NameRecord]:
        with path.open(encoding="utf-8") as f:
            return [
                NameRecord(
                    pokemon_id=int(row["id"]),
                    name_en=row["name_en"],
                    name_zh=row["name_zh"],
                    name_ja=row["name_ja"],
                )
                for row in csv.DictReader(f)
            ]

    def fuzzy_match(self, query: str) -> list[int]:
        q = query.lower()
        return [
            r.pokemon_id for r in self._records
            if q in r.name_en.lower()
            or q in r.name_zh
            or q in r.name_ja
        ]
```

- [ ] **Step 5: Run tests to verify pass**

```bash
python -m pytest tests/adapters/test_csv_name_provider.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add adapters/csv_name_provider.py tests/adapters/ 
git commit -m "feat: implement CsvNameProvider with trilingual fuzzy search"
```

---

## Task 11: Scripts — Build `pokemon_names.csv`

**Files:**
- Create: `scripts/build_csv.py`

This script fetches all Pokémon names from PokéAPI and writes `data/pokemon_names.csv`. Run once; result is committed to the repo.

- [ ] **Step 1: Implement `scripts/build_csv.py`**

```python
"""
One-time script to build data/pokemon_names.csv from PokéAPI.
Usage: python scripts/build_csv.py
Fetches species 1-1025 (Gen 1-9 national dex).
"""
import csv
import time
import requests
from pathlib import Path

BASE  = "https://pokeapi.co/api/v2"
OUT   = Path(__file__).parent.parent / "data" / "pokemon_names.csv"
TOTAL = 1025  # Gen 1-9


def fetch_names(species_id: int) -> dict | None:
    url = f"{BASE}/pokemon-species/{species_id}"
    resp = requests.get(url, timeout=10)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    names = {n["language"]["name"]: n["name"] for n in data["names"]}
    return {
        "id":      species_id,
        "name_en": names.get("en", ""),
        "name_zh": names.get("zh-Hant", names.get("zh-Hans", "")),
        "name_ja": names.get("ja", names.get("ja-Hrkt", "")),
    }


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(1, TOTAL + 1):
        row = fetch_names(i)
        if row:
            rows.append(row)
            print(f"[{i}/{TOTAL}] {row['name_en']} / {row['name_zh']} / {row['name_ja']}")
        time.sleep(0.05)  # avoid rate limit

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name_en", "name_zh", "name_ja"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. {len(rows)} records written to {OUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script**

```bash
cd /Users/wayneho/poke-calc
python scripts/build_csv.py
```

Expected: Progress lines like `[1/1025] Bulbasaur / 妙蛙種子 / フシギダネ`, finishes with `Done. 1025 records written`.

This takes ~3-5 minutes due to rate limiting.

- [ ] **Step 3: Verify CSV**

```bash
head -5 data/pokemon_names.csv
wc -l data/pokemon_names.csv
```

Expected: Header + 5 rows visible, line count ≈ 1026.

- [ ] **Step 4: Commit**

```bash
git add data/pokemon_names.csv scripts/build_csv.py
git commit -m "feat: add pokemon_names.csv (Gen 1-9 trilingual) and build script"
```

---

## Task 12: Adapters — PokeApiRepository

**Files:**
- Create: `adapters/poke_api_repository.py`

No unit tests (requires live network). Verified manually via smoke test.

- [ ] **Step 1: Implement `adapters/poke_api_repository.py`**

```python
import json
import requests
from pathlib import Path
from domain.models.nature import NatureRegistry
from domain.models.pokemon import Pokemon
from domain.models.stats import StatSet
from domain.repositories.abstract import AbstractPokeRepository
from shared.exceptions import PokemonNotFoundError


class PokeApiRepository(AbstractPokeRepository):

    BASE_URL = "https://pokeapi.co/api/v2"

    def __init__(self, cache_dir: Path) -> None:
        self._cache = cache_dir
        self._cache.mkdir(parents=True, exist_ok=True)

    def _fetch_raw(self, identifier: int | str) -> dict:
        cache_file = self._cache / f"{identifier}.json" if isinstance(identifier, int) else None
        if cache_file and cache_file.exists():
            return json.loads(cache_file.read_text(encoding="utf-8"))

        resp = requests.get(f"{self.BASE_URL}/pokemon/{identifier}", timeout=10)
        if resp.status_code == 404:
            raise PokemonNotFoundError(identifier)
        resp.raise_for_status()
        data = resp.json()

        if cache_file:
            cache_file.write_text(json.dumps(data), encoding="utf-8")
        return data

    def _parse(self, raw: dict, name_zh: str = "", name_ja: str = "") -> Pokemon:
        stats = {s["stat"]["name"]: s["base_stat"] for s in raw["stats"]}
        home = raw.get("sprites", {}).get("other", {}).get("home", {}) or {}
        return Pokemon(
            id          = raw["id"],
            name_en     = raw["name"],
            name_zh     = name_zh,
            name_ja     = name_ja,
            types       = [t["type"]["name"] for t in raw["types"]],
            base_stats  = StatSet(
                hp         = stats["hp"],
                attack     = stats["attack"],
                defense    = stats["defense"],
                sp_attack  = stats["special-attack"],
                sp_defense = stats["special-defense"],
                speed      = stats["speed"],
            ),
            sprite_url       = home.get("front_default", ""),
            sprite_shiny_url = home.get("front_shiny", ""),
        )

    def get_by_id(self, pokemon_id: int, name_zh: str = "", name_ja: str = "") -> Pokemon:
        return self._parse(self._fetch_raw(pokemon_id), name_zh, name_ja)

    def get_by_name(self, name: str) -> Pokemon:
        return self._parse(self._fetch_raw(name.lower()))

    def search(self, query: str) -> list[Pokemon]:
        raise NotImplementedError("Use SearchService + CsvNameProvider for search")
```

- [ ] **Step 2: Smoke test with Garchomp**

```bash
python -c "
from pathlib import Path
from adapters.poke_api_repository import PokeApiRepository
repo = PokeApiRepository(Path('adapters/cache'))
p = repo.get_by_id(445, '烈咬陸鯊', 'ガブリアス')
print(p.name_en, p.base_stats.speed, p.sprite_url[:40])
"
```

Expected: `garchomp 102 https://raw.githubusercontent.com/PokeAPI...`

- [ ] **Step 3: Verify cache file created**

```bash
ls adapters/cache/445.json
```

Expected: File exists.

- [ ] **Step 4: Commit**

```bash
git add adapters/poke_api_repository.py
git commit -m "feat: implement PokeApiRepository with JSON cache and HOME sprites"
```

---

## Task 13: Application — SearchService

**Files:**
- Create: `application/search_service.py`
- Create: `tests/application/test_search_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/application/test_search_service.py`:

```python
import pytest
from unittest.mock import MagicMock
from pathlib import Path
from domain.models.nature import NatureRegistry
from domain.models.stats import StatSet
from domain.models.pokemon import Pokemon
from application.search_service import SearchService
from adapters.csv_name_provider import CsvNameProvider
from shared.exceptions import PokemonNotFoundError

GARCHOMP = Pokemon(
    id=445, name_en="garchomp", name_zh="烈咬陸鯊", name_ja="ガブリアス",
    base_stats=StatSet(hp=108, attack=130, defense=95, sp_attack=80, sp_defense=85, speed=102),
    types=["dragon", "ground"],
)
PIKACHU = Pokemon(
    id=25, name_en="pikachu", name_zh="皮卡丘", name_ja="ピカチュウ",
    base_stats=StatSet(hp=35, attack=55, defense=40, sp_attack=50, sp_defense=50, speed=90),
    types=["electric"],
)


@pytest.fixture
def svc():
    repo = MagicMock()
    repo.get_by_id.side_effect = lambda pid, zh="", ja="": {445: GARCHOMP, 25: PIKACHU}[pid]
    repo.get_by_name.return_value = PIKACHU
    # __file__ = tests/application/test_search_service.py → parent.parent = tests/
    csv = CsvNameProvider(Path(__file__).parent.parent / "adapters" / "fixtures" / "test_names.csv")
    return SearchService(repo, csv)


class TestSearchService:
    def test_search_by_english_returns_pokemon(self, svc):
        results = svc.search("Garchomp")
        assert any(p.id == 445 for p in results)

    def test_search_by_chinese_returns_pokemon(self, svc):
        results = svc.search("烈咬陸鯊")
        assert any(p.id == 445 for p in results)

    def test_search_by_japanese_returns_pokemon(self, svc):
        results = svc.search("ガブリアス")
        assert any(p.id == 445 for p in results)

    def test_search_fallback_to_api(self, svc):
        results = svc.search("pikachu")
        assert len(results) >= 1

    def test_search_unknown_returns_empty(self, svc):
        svc._repo.get_by_name.side_effect = PokemonNotFoundError("xyzzy")
        results = svc.search("xyzzy")
        assert results == []
```

- [ ] **Step 2: Fix fixture path in test**

The test references the fixtures CSV via a relative path. Update the fixture line to:

```python
csv = CsvNameProvider(Path(__file__).parent.parent / "tests" / "adapters" / "fixtures" / "test_names.csv")
```

- [ ] **Step 3: Run to verify failure**

```bash
python -m pytest tests/application/test_search_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'application.search_service'`

- [ ] **Step 4: Implement `application/search_service.py`**

```python
from domain.models.pokemon import Pokemon
from domain.repositories.abstract import AbstractPokeRepository
from adapters.csv_name_provider import CsvNameProvider
from shared.exceptions import PokemonNotFoundError


class SearchService:

    def __init__(self, repository: AbstractPokeRepository, csv_provider: CsvNameProvider) -> None:
        self._repo = repository
        self._csv = csv_provider

    def search(self, query: str) -> list[Pokemon]:
        query = query.strip()
        ids = self._csv.fuzzy_match(query)
        if ids:
            return [self._repo.get_by_id(pid) for pid in ids]
        try:
            return [self._repo.get_by_name(query.lower())]
        except (PokemonNotFoundError, Exception):
            return []
```

- [ ] **Step 5: Run tests to verify pass**

```bash
python -m pytest tests/application/test_search_service.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Run full test suite**

```bash
python -m pytest -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add application/search_service.py tests/application/test_search_service.py
git commit -m "feat: implement SearchService with CSV-first trilingual search"
```

---

## Task 14: Interfaces — Streamlit App (Setup + Search Tab)

**Files:**
- Create: `interfaces/streamlit/app.py`

Streamlit UI cannot be unit-tested. Verify by running the app and using it in a browser.

- [ ] **Step 1: Implement `interfaces/streamlit/app.py`**

```python
import streamlit as st
from pathlib import Path
from adapters.poke_api_repository import PokeApiRepository
from adapters.csv_name_provider import CsvNameProvider
from application.calculator import StatCalculator
from application.search_service import SearchService
from application.speed_service import SpeedService
from application.survival_service import SurvivalService, AttackInput
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
    st.info("請至下一個 Task 完成此頁籤的 UI。")

# ── Survival Tab (placeholder UI) ────────────────────────────────────────────
with tab_survival:
    st.header("存活分析")
    st.info("請至下一個 Task 完成此頁籤的 UI。")
```

- [ ] **Step 2: Run the app**

```bash
cd /Users/wayneho/poke-calc
streamlit run interfaces/streamlit/app.py
```

Expected: Browser opens at `http://localhost:8501`. No errors in terminal.

- [ ] **Step 3: Manual test — search tab**

In the browser:
1. Type `Garchomp` → HOME sprite + stats table appear
2. Type `烈咬陸鯊` → same result
3. Type `ガブリアス` → same result
4. Type `Xyzzy` → warning message appears

- [ ] **Step 4: Commit**

```bash
git add interfaces/streamlit/app.py
git commit -m "feat: add Streamlit app with working search tab"
```

---

## Task 15: Interfaces — Speed Analysis Tab

**Files:**
- Modify: `interfaces/streamlit/app.py:Speed Tab section`

- [ ] **Step 1: Replace the Speed tab placeholder**

Replace the `# ── Speed Tab` section with:

```python
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
```

- [ ] **Step 2: Restart the app and test**

Stop the app (Ctrl+C) then:

```bash
streamlit run interfaces/streamlit/app.py
```

In browser, go to **⚡ 超速分析** tab:
1. My: `Garchomp` / Jolly, Target: `Tyranitar` / Brave → shows SP result
2. My: `Pikachu` / Timid, Target: `Garchomp` / Jolly → shows cannot outspeed or SP needed
3. Invalid name → shows error message

- [ ] **Step 3: Commit**

```bash
git add interfaces/streamlit/app.py
git commit -m "feat: implement speed analysis tab UI"
```

---

## Task 16: Interfaces — Survival Analysis Tab

**Files:**
- Modify: `interfaces/streamlit/app.py:Survival Tab section`

- [ ] **Step 1: Replace the Survival tab placeholder**

Replace the `# ── Survival Tab` section with:

```python
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
        power       = st.number_input("招式威力", min_value=1, max_value=250, value=120, key="surv_power")
        attacker_atk= st.number_input("攻擊方實際攻擊力", min_value=1, max_value=999, value=200, key="surv_atk")
        is_physical = st.radio("攻擊類別", ["物理", "特殊"], key="surv_cat") == "物理"
        type_mult   = st.select_slider(
            "屬性相性",
            options=[0.25, 0.5, 1.0, 2.0, 4.0],
            value=1.0,
            key="surv_mult",
        )

    if st.button("計算最佳存活分配", key="surv_calc") and surv_query:
        from domain.models.nature import NatureRegistry
        from application.survival_service import AttackInput
        import dataclasses

        surv_results = svc["search"].search(surv_query)
        if not surv_results:
            st.error(f"找不到寶可夢：{surv_query}")
        else:
            mon = dataclasses.replace(
                surv_results[0],
                nature=NatureRegistry.get_by_name(surv_nature_name),
            )
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
```

- [ ] **Step 2: Restart app and test**

```bash
streamlit run interfaces/streamlit/app.py
```

Go to **🛡️ 存活分析** tab. Test cases:

1. **Normal test**: Garchomp / Bold, power=120, atk=200, physical, type=1.0
   → Shows two plans with same total SP, prefer_hp has higher SP_HP

2. **Impossible case**: power=250, atk=999, type=4.0
   → Shows "無法扛下" error

3. **Zero SP needed**: power=40, atk=80, physical, type=0.5
   → Shows SP_HP=0, SP_Def=0

- [ ] **Step 3: Run full test suite one final time**

```bash
python -m pytest -v
```

Expected: All tests PASS.

- [ ] **Step 4: Final commit**

```bash
git add interfaces/streamlit/app.py
git commit -m "feat: implement survival analysis tab UI — project complete"
```

---

## Summary

| Layer | Status |
|---|---|
| `domain/` | Nature, Stats, Move, Pokemon, AbstractRepo |
| `application/` | Calculator, SpeedService, SurvivalService, SearchService |
| `adapters/` | CsvNameProvider, PokeApiRepository |
| `interfaces/` | Streamlit 3-tab UI |
| `data/` | pokemon_names.csv (Gen 1-9, trilingual) |
