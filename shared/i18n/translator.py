from __future__ import annotations
import json
from pathlib import Path
from shared.config import I18N_DIR


def parse_accept_language(header: str) -> str:
    if not header:
        return "zh"
    first = header.split(",")[0].split(";")[0].strip().lower()
    if first.startswith("zh"):
        return "zh"
    if first.startswith("ja"):
        return "ja"
    return "zh"


class Translator:

    def __init__(self, lang: str, i18n_dir: Path = I18N_DIR) -> None:
        path = i18n_dir / f"{lang}.json"
        self._data: dict = json.loads(path.read_text(encoding="utf-8"))

    def __call__(self, key: str) -> str:
        value = self._data.get(key, key)
        return value if isinstance(value, str) else key

    def strings(self, key: str) -> list[str]:
        value = self._data.get(key)
        return value if isinstance(value, list) else []

    def type_name(self, type_en: str) -> str:
        return self._data.get("types", {}).get(type_en, type_en)
