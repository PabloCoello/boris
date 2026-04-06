"""Tests for boris.core.orchestrator module."""

from boris.core.orchestrator import parse_tool_call


def test_valid_tool_call():
    resp = '{"tool": "reminder", "args": {"text": "Llamar al médico", "datetime": "2026-04-06T10:00:00"}}'
    tool, text = parse_tool_call(resp)
    assert tool is not None
    assert tool["tool"] == "reminder"
    assert tool["args"]["text"] == "Llamar al médico"
    assert text == ""


def test_plain_text_is_not_tool_call():
    tool, text = parse_tool_call("Buenos días, mi señor.")
    assert tool is None
    assert text == "Buenos días, mi señor."


def test_malformed_json_is_not_tool_call():
    tool, text = parse_tool_call('{"tool": "reminder", "args": {broken}')
    assert tool is None
    assert "broken" in text


def test_json_without_tool_key_is_not_tool_call():
    tool, text = parse_tool_call('{"action": "play", "song": "test"}')
    assert tool is None
    assert "play" in text


def test_empty_response():
    tool, text = parse_tool_call("")
    assert tool is None
    assert text == ""


def test_tool_call_with_no_args():
    tool, text = parse_tool_call('{"tool": "reminders_list"}')
    assert tool is not None
    assert tool["tool"] == "reminders_list"
    assert text == ""


def test_text_with_braces_is_not_tool_call():
    tool, text = parse_tool_call("La temperatura es {alta} hoy")
    assert tool is None
    assert "temperatura" in text


def test_whitespace_around_json():
    tool, text = parse_tool_call('  {"tool": "search", "args": {"query": "clima"}}  ')
    assert tool is not None
    assert tool["tool"] == "search"
