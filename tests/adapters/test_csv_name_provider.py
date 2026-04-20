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

    def test_raises_on_missing_column(self, tmp_path):
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("id,name_en\n1,Bulbasaur\n", encoding="utf-8")
        with pytest.raises(ValueError, match="missing required columns"):
            CsvNameProvider(bad_csv)
