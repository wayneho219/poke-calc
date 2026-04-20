import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NameRecord:
    pokemon_id: int
    name_en: str
    name_zh: str
    name_ja: str


class CsvNameProvider:

    def __init__(self, csv_path: Path) -> None:
        self._records: list[NameRecord] = self._load(csv_path)

    def _load(self, path: Path) -> list[NameRecord]:
        required = {"id", "name_en", "name_zh", "name_ja"}
        with path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise ValueError(f"CSV missing required columns. Expected: {required}")
            return [
                NameRecord(
                    pokemon_id=int(row["id"]),
                    name_en=row["name_en"],
                    name_zh=row["name_zh"],
                    name_ja=row["name_ja"],
                )
                for row in reader
            ]

    def fuzzy_match(self, query: str) -> list[int]:
        q = query.lower()
        return [
            r.pokemon_id for r in self._records
            if q in r.name_en.lower()
            or q in r.name_zh
            or q in r.name_ja
        ]
