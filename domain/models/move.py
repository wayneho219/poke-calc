from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    name: str
    power: int
    category: str       # "physical" | "special"
    type_name: str
