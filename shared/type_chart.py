# Generation VIII type effectiveness chart (18×18).
# Keys are lowercase English type names matching PokéAPI slugs.

_CHART: dict[str, dict[str, float]] = {
    "normal":   {"rock": 0.5, "ghost": 0.0, "steel": 0.5},
    "fire":     {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0,
                 "bug": 2.0, "rock": 0.5, "dragon": 0.5, "steel": 2.0},
    "water":    {"fire": 2.0, "water": 0.5, "grass": 0.5,
                 "ground": 2.0, "rock": 2.0, "dragon": 0.5},
    "electric": {"water": 2.0, "electric": 0.5, "grass": 0.5,
                 "ground": 0.0, "flying": 2.0, "dragon": 0.5},
    "grass":    {"fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5,
                 "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0,
                 "dragon": 0.5, "steel": 0.5},
    "ice":      {"water": 0.5, "grass": 2.0, "ice": 0.5,
                 "ground": 2.0, "flying": 2.0, "dragon": 2.0, "steel": 0.5},
    "fighting": {"normal": 2.0, "ice": 2.0, "rock": 2.0, "dark": 2.0,
                 "steel": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5,
                 "bug": 0.5, "fairy": 0.5, "ghost": 0.0},
    "poison":   {"grass": 2.0, "fairy": 2.0, "poison": 0.5, "ground": 0.5,
                 "rock": 0.5, "ghost": 0.5, "steel": 0.0},
    "ground":   {"fire": 2.0, "electric": 2.0, "poison": 2.0, "rock": 2.0,
                 "steel": 2.0, "grass": 0.5, "bug": 0.5, "flying": 0.0},
    "flying":   {"grass": 2.0, "fighting": 2.0, "bug": 2.0,
                 "electric": 0.5, "rock": 0.5, "steel": 0.5},
    "psychic":  {"fighting": 2.0, "poison": 2.0, "psychic": 0.5,
                 "steel": 0.5, "dark": 0.0},
    "bug":      {"grass": 2.0, "psychic": 2.0, "dark": 2.0,
                 "fire": 0.5, "fighting": 0.5, "flying": 0.5,
                 "ghost": 0.5, "steel": 0.5, "fairy": 0.5, "poison": 0.5},
    "rock":     {"flying": 2.0, "bug": 2.0, "fire": 2.0, "ice": 2.0,
                 "fighting": 0.5, "ground": 0.5, "steel": 0.5},
    "ghost":    {"normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5},
    "dragon":   {"dragon": 2.0, "steel": 0.5, "fairy": 0.0},
    "dark":     {"ghost": 2.0, "psychic": 2.0, "dark": 0.5,
                 "fighting": 0.5, "fairy": 0.5},
    "steel":    {"ice": 2.0, "rock": 2.0, "fairy": 2.0,
                 "fire": 0.5, "water": 0.5, "electric": 0.5, "steel": 0.5},
    "fairy":    {"fighting": 2.0, "dragon": 2.0, "dark": 2.0,
                 "fire": 0.5, "poison": 0.5, "steel": 0.5},
}

ALL_TYPES: list[str] = list(_CHART.keys())


def get_effectiveness(attacker_types: list[str], defender_types: list[str]) -> float:
    mult = 1.0
    for atk in attacker_types:
        for def_ in defender_types:
            mult *= _CHART.get(atk, {}).get(def_, 1.0)
    return mult


def get_matchups(defender_types: list[str]) -> dict[str, float]:
    return {atk: get_effectiveness([atk], defender_types) for atk in ALL_TYPES}
