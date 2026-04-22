from shared.i18n.translator import parse_accept_language


class TestParseAcceptLanguage:
    def test_zh_tw_returns_zh(self):
        assert parse_accept_language("zh-TW,zh;q=0.9,en;q=0.8") == "zh"

    def test_zh_hans_returns_zh(self):
        assert parse_accept_language("zh-Hans") == "zh"

    def test_zh_bare_returns_zh(self):
        assert parse_accept_language("zh") == "zh"

    def test_ja_returns_ja(self):
        assert parse_accept_language("ja,en-US;q=0.9") == "ja"

    def test_ja_jp_returns_ja(self):
        assert parse_accept_language("ja-JP") == "ja"

    def test_english_returns_zh(self):
        assert parse_accept_language("en-US,en;q=0.9") == "zh"

    def test_korean_returns_zh(self):
        assert parse_accept_language("ko-KR,ko;q=0.9") == "zh"

    def test_empty_header_returns_zh(self):
        assert parse_accept_language("") == "zh"
