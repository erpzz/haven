from csvline import split


def test_plain():
    assert split("a,b,c") == ["a", "b", "c"]


def test_quoted_separator():
    assert split('x,"a, b",y') == ["x", "a, b", "y"]


def test_escaped_quote():
    assert split('"say ""hi""",z') == ['say "hi"', "z"]


def test_empty_fields():
    assert split("a,,c,") == ["a", "", "c", ""]
    assert split(",") == ["", ""]
