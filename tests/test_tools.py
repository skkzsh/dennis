import pytest

from dennis.tools import (
    VariableTokenizer,
    PythonFormat,
    PythonBraceFormat,
    parse_dennis_note,
)


def test_empty_tokenizer():
    vartok = VariableTokenizer([])
    assert vartok.contains("python-format") is False
    assert vartok.tokenize("a b c d e") == ["a b c d e"]
    assert vartok.extract_tokens("a b c d e") == set()
    assert vartok.is_token("{0}") is False
    assert vartok.extract_variable_name("{0}") is None


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Hello %s", ["Hello ", "%s"]),
        ("Hello %(username)s", ["Hello ", "%(username)s"]),
        ("Hello %(user)s%(name)s", ["Hello ", "%(user)s", "%(name)s"]),
        ("Hello {username}", ["Hello ", "{username}"]),
        ("Hello {user}{name}", ["Hello ", "{user}", "{name}"]),
        ("Products and Services", ["Products and Services"]),
    ],
)
def test_python_tokenizing(text, expected):
    vartok = VariableTokenizer(["python-format", "python-brace-format"])
    assert vartok.tokenize(text) == expected


class TestPythonBraceFormat:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Hello", ["Hello"]),
            ("{foo}", ["{foo}"]),
            ("Hello {foo}", ["Hello ", "{foo}"]),
            ("{foo} Hello", ["{foo}", " Hello"]),
            ("{foo:%Y-%m-%d}", ["{foo:%Y-%m-%d}"]),
            ("{foo:%Y-%m-%d %H:%M}", ["{foo:%Y-%m-%d %H:%M}"]),
        ],
    )
    def test_parse(self, text, expected):
        vartok = VariableTokenizer(["python-brace-format"])
        assert vartok.tokenize(text) == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("{}", ""),
            ("{0}", "0"),
            ("{abc}", "abc"),
            ("{abc.def}", "abc.def"),
            ("{abc[0]}", "abc[0]"),
            ("{abc!s}", "abc"),  # conversion
            ("{abc: >16}", "abc"),  # format_spec
        ],
    )
    def test_variable_name(self, text, expected):
        v = PythonBraceFormat()
        assert v.extract_variable_name(text) == expected


@pytest.mark.parametrize(
    "text,expected", [("%s", ""), ("%d", ""), ("%.2f", ""), ("%(foo)s", "foo")]
)
def test_pythonformat(text, expected):
    v = PythonFormat()
    assert v.extract_variable_name(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("", []),
        ("Foo", []),
        ("Foo bar", []),
        ("dennis-ignore", []),
        ("dennis-ignore: *", "*"),
        ("dennis-ignore: E101", ["E101"]),
        ("dennis-ignore: E101, E102", ["E101"]),
        ("dennis-ignore: E101,E102", ["E101", "E102"]),
        ("localizers ignore this: dennis-ignore: E101,E102", ["E101", "E102"]),
    ],
)
def test_parse_dennis_note(text, expected):
    assert parse_dennis_note(text) == expected


class TestVariableTokenizerCache:
    def test_extract_tokens_cache(self):
        vartok = VariableTokenizer(["python-format"])
        text = "Hello %s"

        vartok.extract_tokens.cache_clear()

        # Miss
        vartok.extract_tokens(text)
        assert vartok.extract_tokens.cache_info().misses == 1
        assert vartok.extract_tokens.cache_info().hits == 0

        # Hit
        vartok.extract_tokens(text)
        assert vartok.extract_tokens.cache_info().misses == 1
        assert vartok.extract_tokens.cache_info().hits == 1

        # Miss with different unique param
        vartok.extract_tokens(text, unique=False)
        assert vartok.extract_tokens.cache_info().misses == 2
        assert vartok.extract_tokens.cache_info().hits == 1

    def test_extract_variable_name_cache(self):
        vartok = VariableTokenizer(["python-format", "python-brace-format"])

        vartok.extract_variable_name.cache_clear()

        # Miss
        vartok.extract_variable_name("%(name)s")
        assert vartok.extract_variable_name.cache_info().misses == 1
        assert vartok.extract_variable_name.cache_info().hits == 0

        # Hit
        vartok.extract_variable_name("%(name)s")
        assert vartok.extract_variable_name.cache_info().misses == 1
        assert vartok.extract_variable_name.cache_info().hits == 1

        # Miss with different format
        vartok.extract_variable_name("{name}")
        assert vartok.extract_variable_name.cache_info().misses == 2
        assert vartok.extract_variable_name.cache_info().hits == 1

    def test_cache_instance_separation(self):
        vartok1 = VariableTokenizer(["python-format"])
        vartok2 = VariableTokenizer(["python-format"])
        text = "Hello %s"

        vartok1.extract_tokens.cache_clear()

        vartok1.extract_tokens(text)
        assert vartok1.extract_tokens.cache_info().misses == 1
        assert vartok1.extract_tokens.cache_info().hits == 0

        # Different instance should be a miss (self is part of key)
        vartok2.extract_tokens(text)
        assert vartok2.extract_tokens.cache_info().misses == 2
        assert vartok2.extract_tokens.cache_info().hits == 0
