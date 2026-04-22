import json
import pytest
from pathlib import Path
from shared.i18n.translator import Translator, parse_accept_language


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_i18n_dir(tmp_path):
    en = {
        "greeting": "Hello",
        "stat_names": ["HP", "Attack"],
        "types": {"fire": "Fire", "water": "Water"},
    }
    zh = {
        "greeting": "你好",
        "stat_names": ["HP", "攻擊"],
        "types": {"fire": "火", "water": "水"},
    }
    ja = {
        "greeting": "こんにちは",
        "stat_names": ["HP", "こうげき"],
        "types": {"fire": "ほのお", "water": "みず"},
    }
    for lang, data in [("en", en), ("zh", zh), ("ja", ja)]:
        (tmp_path / f"{lang}.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
    return tmp_path


# ── Translator tests ──────────────────────────────────────────────────────────

class TestTranslator:
    def test_en_key_returns_english(self, tmp_i18n_dir):
        t = Translator("en", i18n_dir=tmp_i18n_dir)
        assert t("greeting") == "Hello"

    def test_zh_key_returns_chinese(self, tmp_i18n_dir):
        t = Translator("zh", i18n_dir=tmp_i18n_dir)
        assert t("greeting") == "你好"

    def test_ja_key_returns_japanese(self, tmp_i18n_dir):
        t = Translator("ja", i18n_dir=tmp_i18n_dir)
        assert t("greeting") == "こんにちは"

    def test_missing_key_falls_back_to_key_name(self, tmp_i18n_dir):
        t = Translator("en", i18n_dir=tmp_i18n_dir)
        assert t("nonexistent_xyz") == "nonexistent_xyz"

    def test_strings_returns_list(self, tmp_i18n_dir):
        t = Translator("en", i18n_dir=tmp_i18n_dir)
        assert t.strings("stat_names") == ["HP", "Attack"]

    def test_strings_missing_key_returns_empty_list(self, tmp_i18n_dir):
        t = Translator("en", i18n_dir=tmp_i18n_dir)
        assert t.strings("no_such_list") == []

    def test_type_name_en(self, tmp_i18n_dir):
        t = Translator("en", i18n_dir=tmp_i18n_dir)
        assert t.type_name("fire") == "Fire"

    def test_type_name_zh(self, tmp_i18n_dir):
        t = Translator("zh", i18n_dir=tmp_i18n_dir)
        assert t.type_name("fire") == "火"

    def test_type_name_ja(self, tmp_i18n_dir):
        t = Translator("ja", i18n_dir=tmp_i18n_dir)
        assert t.type_name("fire") == "ほのお"

    def test_type_name_unknown_falls_back(self, tmp_i18n_dir):
        t = Translator("en", i18n_dir=tmp_i18n_dir)
        assert t.type_name("shadow") == "shadow"
