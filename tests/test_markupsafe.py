from __future__ import annotations

import typing as t

import pytest

from markupsafe import escape
from markupsafe import escape_silent
from markupsafe import Markup
from markupsafe import soft_str


def test_adding() -> None:
    unsafe = '<script type="application/x-some-script">alert("foo");</script>'
    safe = Markup("<em>username</em>")
    assert unsafe + safe == str(escape(unsafe)) + str(safe)


@pytest.mark.parametrize(
    ("template", "data", "expect"),
    (
        ("<em>%s</em>", "<bad user>", "<em>&lt;bad user&gt;</em>"),
        (
            "<em>%(username)s</em>",
            {"username": "<bad user>"},
            "<em>&lt;bad user&gt;</em>",
        ),
        ("%i", 3.14, "3"),
        ("%.2f", 3.14, "3.14"),
    ),
)
def test_string_interpolation(template: str, data: t.Any, expect: str) -> None:
    assert Markup(template) % data == expect


def test_type_behavior() -> None:
    assert type(Markup("foo") + "bar") is Markup
    x = Markup("foo")
    assert x.__html__() is x


def test_html_interop() -> None:
    class Foo:
        def __html__(self) -> str:
            return "<em>awesome</em>"

        def __str__(self) -> str:
            return "awesome"

    assert Markup(Foo()) == "<em>awesome</em>"
    result = Markup("<strong>%s</strong>") % Foo()
    assert result == "<strong><em>awesome</em></strong>"


@pytest.mark.parametrize("args", ["foo", 42, ("foo", 42)])
def test_missing_interpol(args: t.Any) -> None:
    with pytest.raises(TypeError):
        assert Markup("<em></em>") % args


def test_tuple_interpol() -> None:
    result = Markup("<em>%s:%s</em>") % ("<foo>", "<bar>")
    expect = Markup("<em>&lt;foo&gt;:&lt;bar&gt;</em>")
    assert result == expect


def test_dict_interpol() -> None:
    result = Markup("<em>%(foo)s</em>") % {"foo": "<foo>"}
    expect = Markup("<em>&lt;foo&gt;</em>")
    assert result == expect

    result = Markup("<em>%(foo)s:%(bar)s</em>") % {"foo": "<foo>", "bar": "<bar>"}
    expect = Markup("<em>&lt;foo&gt;:&lt;bar&gt;</em>")
    assert result == expect


def test_escaping() -> None:
    assert escape("\"<>&'") == "&#34;&lt;&gt;&amp;&#39;"
    assert (
        Markup(
            "<!-- outer comment -->"
            "<em>Foo &amp; Bar"
            " <!-- inner comment about <em> -->\n "
            "</em>"
            "<!-- comment\nwith\nnewlines\n-->"
            "<meta content='tag\nwith\nnewlines'>"
        ).striptags()
        == "Foo & Bar"
    )


def test_unescape() -> None:
    assert Markup("&lt;test&gt;").unescape() == "<test>"

    result = Markup("jack & tavi are cooler than mike &amp; russ").unescape()
    expect = "jack & tavi are cooler than mike & russ"
    assert result == expect

    original = "&foo&#x3b;"
    once = Markup(original).unescape()
    twice = Markup(once).unescape()
    expect = "&foo;"
    assert once == expect
    assert twice == expect


def test_format() -> None:
    result = Markup("<em>{awesome}</em>").format(awesome="<awesome>")
    assert result == "<em>&lt;awesome&gt;</em>"

    result = Markup("{0[1][bar]}").format([0, {"bar": "<bar/>"}])
    assert result == "&lt;bar/&gt;"

    result = Markup("{0[1][bar]}").format([0, {"bar": Markup("<bar/>")}])
    assert result == "<bar/>"


def test_format_map() -> None:
    result = Markup("<em>{value}</em>").format_map({"value": "<value>"})
    assert result == "<em>&lt;value&gt;</em>"


def test_formatting_empty() -> None:
    formatted = Markup("{}").format(0)
    assert formatted == Markup("0")


def test_custom_formatting() -> None:
    class HasHTMLOnly:
        def __html__(self) -> Markup:
            return Markup("<foo>")

    class HasHTMLAndFormat:
        def __html__(self) -> Markup:
            return Markup("<foo>")

        def __html_format__(self, spec: str) -> Markup:
            return Markup("<FORMAT>")

    assert Markup("{0}").format(HasHTMLOnly()) == Markup("<foo>")
    assert Markup("{0}").format(HasHTMLAndFormat()) == Markup("<FORMAT>")


def test_complex_custom_formatting() -> None:
    class User:
        def __init__(self, id: int, username: str) -> None:
            self.id = id
            self.username = username

        def __html_format__(self, format_spec: str) -> Markup:
            if format_spec == "link":
                return Markup('<a href="/user/{0}">{1}</a>').format(
                    self.id, self.__html__()
                )
            elif format_spec:
                raise ValueError("Invalid format spec")

            return self.__html__()

        def __html__(self) -> Markup:
            return Markup("<span class=user>{0}</span>").format(self.username)

    user = User(1, "foo")
    result = Markup("<p>User: {0:link}").format(user)
    expect = Markup('<p>User: <a href="/user/1"><span class=user>foo</span></a>')
    assert result == expect


def test_formatting_with_objects() -> None:
    class Stringable:
        def __str__(self) -> str:
            return "строка"

    assert Markup("{s}").format(s=Stringable()) == Markup("строка")


def test_escape_silent() -> None:
    assert escape_silent(None) == Markup()
    assert escape(None) == Markup(None)
    assert escape_silent("<foo>") == Markup("&lt;foo&gt;")


def test_splitting() -> None:
    expect = [Markup("a"), Markup("b")]
    assert Markup("a b").split() == expect
    assert Markup("a b").rsplit() == expect
    assert Markup("a\nb").splitlines() == expect


def test_mul() -> None:
    assert Markup("a") * 3 == Markup("aaa")


def test_escape_return_type() -> None:
    assert isinstance(escape("a"), Markup)
    assert isinstance(escape(Markup("a")), Markup)

    class Foo:
        def __html__(self) -> str:
            return "<strong>Foo</strong>"

    assert isinstance(escape(Foo()), Markup)


def test_soft_str() -> None:
    assert type(soft_str("")) is str  # noqa: E721
    assert type(soft_str(Markup())) is Markup  # noqa: E721
    assert type(soft_str(15)) is str  # noqa: E721
