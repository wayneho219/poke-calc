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
        # "pikachu-gmax" is absent from test_names.csv, so CSV returns [].
        # SearchService must fall through to get_by_name.
        svc._repo.get_by_name.return_value = PIKACHU
        results = svc.search("pikachu-gmax")
        svc._repo.get_by_name.assert_called_once_with("pikachu-gmax")
        assert results == [PIKACHU]

    def test_search_unknown_returns_empty(self, svc):
        svc._repo.get_by_name.side_effect = PokemonNotFoundError("xyzzy")
        results = svc.search("xyzzy")
        assert results == []
