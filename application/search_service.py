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
        except PokemonNotFoundError:
            return []
