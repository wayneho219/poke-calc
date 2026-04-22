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
    types: tuple[str, ...]
    nature: Nature = field(default_factory=lambda: NatureRegistry.get_by_name("Hardy"))
    sprite_url: str = ""
    sprite_shiny_url: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "types", tuple(self.types))
