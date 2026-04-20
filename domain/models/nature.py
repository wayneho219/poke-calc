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
    Nature("Quirky",  "浮動", "きまぐれ",   None, None),
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
