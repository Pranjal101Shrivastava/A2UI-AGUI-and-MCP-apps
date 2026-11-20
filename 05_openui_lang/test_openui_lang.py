"""Offline tests for the OpenUI Lang parser and the four codelabs."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]

import openui  # noqa: E402
from shared.devserver import load_agent  # noqa: E402


def run(mode, name="run", body=None):
    agent = load_agent(HERE / mode)
    return list(agent.handle(name, body or {"prompt": agent.PROMPT}))


def program(events):
    return "".join(e["text"] for e in events if e["type"] == "chunk")


def test_literals_arrays_calls_and_escaped_strings():
    name, expr = openui.parse_statement('x = Card("a \\"b\\"", [1, -2.5, true, null, y])')
    assert name == "x" and expr[0] == "call" and expr[2][0] == ("lit", 'a "b"')
    assert expr[2][1][1][-1] == ("ref", "y")


def test_bad_syntax_is_reported_with_the_line():
    with pytest.raises(openui.ParseError):
        openui.parse_statement("x = Card(")
    assert openui.parse_program("ok = Text(\"a\")\nbad = ][")[2][0].startswith("line 2")


def test_forward_references_are_placeholders_until_defined():
    statements, order, _ = openui.parse_program("root = Stack([a, b])\na = Text(\"x\")\n")
    tree, _ = openui.resolve(statements, order, openui.PRIMITIVES)
    assert tree["children"][1] == {"type": "_pending", "name": "b"}


def test_reassignment_replaces_and_partial_lines_are_skipped():
    text = 'root = Text("one")\nroot = Text("two")\nroot = Text("thr'
    statements, order, errors = openui.parse_program(text, partial=True)
    assert errors == [] and openui.resolve(statements, order, openui.PRIMITIVES)[0]["props"]["text"] == "two"


def test_static_cards_must_match_the_registrar():
    agent = load_agent(HERE / "1_static")
    assert agent.check(program(run("1_static"))) == []
    assert agent.check('root = CourseCard("CMPE 281", "Cloud Technologies", 3, "Tue/Thu 18:00", 99, false)\n')


def test_static_enroll_reassigns_two_names():
    run("1_static")
    lines = program(run("1_static", "action", {"name": "enroll", "context": {"code": "CMPE 281"}})).splitlines()
    assert [line.split(" = ")[0] for line in lines] == ["cloud", "note"]


def test_declarative_and_mixed_programs_are_valid():
    for mode in ("2_declarative", "4_mixed"):
        traces = [e["text"] for e in run(mode) if e["type"] == "trace"]
        assert traces == ["program valid"], mode


def test_open_ended_is_one_html_artifact_statement():
    text = program(run("3_open_ended"))
    tree, errors = openui.check(text, openui.HTML_ARTIFACT)
    assert errors == [] and tree["type"] == "HtmlArtifact" and text.count("\n") == 1
