import json
from pathlib import Path
from domain.models.pokemon import Pokemon
from domain.models.stats import StatSet
from domain.repositories.abstract import AbstractPokeRepository
from shared.exceptions import PokemonNotFoundError


def _parse(raw: dict) -> Pokemon:
    s = raw["base_stats"]
    return Pokemon(
        id=raw["id"],
        name_en=raw["name_en"],
        name_zh=raw["name_zh"],
        name_ja=raw["name_ja"],
        types=raw["types"],
        base_stats=StatSet(
            hp=s["hp"], attack=s["attack"], defense=s["defense"],
            sp_attack=s["sp_attack"], sp_defense=s["sp_defense"], speed=s["speed"],
        ),
        sprite_url=raw.get("sprite_path", ""),
        is_final_evolution=raw.get("is_final_evolution", False),
        abilities=raw.get("abilities", []),
        dream_ability=raw.get("dream_ability", None),
        mega_forms=raw.get("mega_forms", []),
    )


def _parse_mega(base: Pokemon, mega: dict, form_index: int) -> Pokemon:
    ms = mega.get("base_stats", {})
    virtual_id = base.id + (form_index + 1) * 10000
    ability = mega.get("ability")
    return Pokemon(
        id=virtual_id,
        name_en=mega.get("name_en", f"Mega {base.name_en}"),
        name_zh=mega.get("name_zh", f"Mega {base.name_zh}"),
        name_ja=mega.get("name_ja", f"メガ{base.name_ja}"),
        types=tuple(mega.get("types", list(base.types))),
        base_stats=StatSet(
            hp=ms.get("hp", 0), attack=ms.get("attack", 0),
            defense=ms.get("defense", 0), sp_attack=ms.get("sp_attack", 0),
            sp_defense=ms.get("sp_defense", 0), speed=ms.get("speed", 0),
        ),
        sprite_url=mega.get("sprite_path", ""),
        is_final_evolution=True,
        abilities=[ability] if ability else [],
        dream_ability=None,
        mega_forms=[],
    )


class LocalJsonRepository(AbstractPokeRepository):

    def __init__(self, json_path: Path) -> None:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        self._by_id:  dict[int, Pokemon] = {}
        self._by_en:  dict[str, Pokemon] = {}
        self._by_zh:  dict[str, Pokemon] = {}
        self._by_ja:  dict[str, Pokemon] = {}
        self._all:    list[Pokemon]      = []
        for i, raw in enumerate(data):
            try:
                p = _parse(raw)
            except (KeyError, TypeError) as exc:
                raise ValueError(f"Bad record at index {i}: {exc}") from exc
            self._index(p)
            for fi, mega in enumerate(p.mega_forms):
                try:
                    vp = _parse_mega(p, mega, fi)
                    self._index(vp)
                except Exception:
                    pass

    def _index(self, p: Pokemon) -> None:
        self._by_id[p.id]              = p
        self._by_en[p.name_en.lower()] = p
        self._by_zh[p.name_zh]         = p
        self._by_ja[p.name_ja]         = p
        self._all.append(p)

    def get_by_id(self, pokemon_id: int, name_zh: str = "", name_ja: str = "") -> Pokemon:
        if pokemon_id not in self._by_id:
            raise PokemonNotFoundError(pokemon_id)
        return self._by_id[pokemon_id]

    def get_by_name(self, name: str) -> Pokemon:
        key = name.strip()
        p = self._by_en.get(key.lower()) or self._by_zh.get(key) or self._by_ja.get(key)
        if p is None:
            raise PokemonNotFoundError(name)
        return p

    def search(self, query: str) -> list[Pokemon]:
        return self.fuzzy_match(query)

    def fuzzy_match(self, query: str) -> list[Pokemon]:
        q = query.strip()
        if not q:
            return []
        ql = q.lower()
        matches = [
            p for p in self._all
            if ql in p.name_en.lower() or q in p.name_zh or q in p.name_ja
        ]
        return sorted(matches, key=lambda p: (not p.is_final_evolution, p.id))
