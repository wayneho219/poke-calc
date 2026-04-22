import json
import requests
from pathlib import Path
from typing import Union
from domain.models.pokemon import Pokemon
from domain.models.stats import StatSet
from domain.repositories.abstract import AbstractPokeRepository
from shared.exceptions import PokemonNotFoundError


class PokeApiRepository(AbstractPokeRepository):

    BASE_URL = "https://pokeapi.co/api/v2"

    def __init__(self, cache_dir: Path) -> None:
        self._cache = cache_dir
        self._cache.mkdir(parents=True, exist_ok=True)

    def _fetch_raw(self, identifier: Union[int, str]) -> dict:
        cache_file = self._cache / f"{identifier}.json" if isinstance(identifier, int) else None
        if cache_file and cache_file.exists():
            return json.loads(cache_file.read_text(encoding="utf-8"))

        resp = requests.get(f"{self.BASE_URL}/pokemon/{identifier}", timeout=10)
        if resp.status_code == 404:
            raise PokemonNotFoundError(identifier)
        resp.raise_for_status()
        data = resp.json()

        if cache_file:
            tmp = cache_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data), encoding="utf-8")
            tmp.replace(cache_file)
        return data

    def _parse(self, raw: dict, name_zh: str = "", name_ja: str = "") -> Pokemon:
        stats = {s["stat"]["name"]: s["base_stat"] for s in raw["stats"]}
        home = raw.get("sprites", {}).get("other", {}).get("home", {}) or {}
        try:
            base_stats = StatSet(
                hp         = stats["hp"],
                attack     = stats["attack"],
                defense    = stats["defense"],
                sp_attack  = stats["special-attack"],
                sp_defense = stats["special-defense"],
                speed      = stats["speed"],
            )
        except KeyError as exc:
            raise ValueError(
                f"Unexpected stats schema for pokemon id={raw.get('id')}: missing key {exc}"
            ) from exc
        return Pokemon(
            id          = raw["id"],
            name_en     = raw["name"],
            name_zh     = name_zh,
            name_ja     = name_ja,
            types       = [t["type"]["name"] for t in raw["types"]],
            base_stats  = base_stats,
            sprite_url       = home.get("front_default", ""),
            sprite_shiny_url = home.get("front_shiny", ""),
        )

    def get_by_id(self, pokemon_id: int, name_zh: str = "", name_ja: str = "") -> Pokemon:
        return self._parse(self._fetch_raw(pokemon_id), name_zh, name_ja)

    def get_by_name(self, name: str) -> Pokemon:
        return self._parse(self._fetch_raw(name.lower()))

    def search(self, query: str) -> list[Pokemon]:
        return []
