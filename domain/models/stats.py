from dataclasses import dataclass


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
