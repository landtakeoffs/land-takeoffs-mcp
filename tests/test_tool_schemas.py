"""Published input schemas, including the gaps the hosted card still has."""

from __future__ import annotations

import jsonschema
import pytest

from land_takeoffs_contract.behavior import ToolError, validate_arguments
from land_takeoffs_contract.manifests import tools_by_name

TOOLS = tools_by_name()


def test_every_tool_schema_is_a_closed_object() -> None:
    for name, tool in TOOLS.items():
        schema = tool["inputSchema"]
        assert schema["type"] == "object", name
        assert schema["additionalProperties"] is False, name
        assert "outputSchema" not in tool, name
        jsonschema.Draft202012Validator.check_schema(schema)


def test_empty_object_is_valid_for_tools_with_no_required_fields() -> None:
    for name in ("check_balance", "list_price_lists", "get_upload_page", "list_takeoffs"):
        validate_arguments(name, {})


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        ("start_plan_set_takeoff", {"plan_set_url": "https://example.com/set.pdf"}),
        ("start_cad_takeoff", {"file_urls": ["https://example.com/site.xml"]}),
        ("start_takeoff", {"plan_set_url": "https://example.com/set.pdf"}),
        (
            "start_takeoff_from_chat_files",
            {"plan_set": {"download_url": "https://example.com/a.pdf", "file_id": "file_1"}},
        ),
        ("answer_cad_question", {"project_id": "proj-1", "shrink_pct": 10}),
        ("get_takeoff_status", {"takeoff_id": "intake-1"}),
        ("get_takeoff_results", {"job_id": "job-1", "division": "storm"}),
        ("get_download_links", {"job_id": "job-1"}),
        ("list_takeoffs", {"limit": 1}),
        ("get_upload_link", {"project_name": "Oak Street"}),
    ],
)
def test_documented_payloads_match_the_published_schema(name: str, payload: dict) -> None:
    validate_arguments(name, payload)


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        ("start_plan_set_takeoff", {}),
        ("start_cad_takeoff", {"file_urls": []}),
        ("start_cad_takeoff", {"file_urls": ["https://example.com/a.xml"], "extra": True}),
        ("list_takeoffs", {"limit": 51}),
        ("list_takeoffs", {"limit": 0}),
        ("start_takeoff", {"shrink_pct": 41}),
        ("start_takeoff", {"storm_rcp_class": "II"}),
        ("answer_cad_question", {}),
        (
            "start_takeoff_from_chat_files",
            {"plan_set": {"download_url": "https://example.com/a.pdf"}},
        ),
        ("start_cad_takeoff", {"file_urls": ["https://example.com/n.xml"] * 21}),
    ],
)
def test_schema_rejects_missing_fields_bounds_and_unknown_keys(name: str, payload: dict) -> None:
    with pytest.raises(ToolError):
        validate_arguments(name, payload)


def test_published_schema_gaps_are_still_present() -> None:
    """These are properties of the live card, not the shape we want long term."""
    assert "required" not in TOOLS["start_takeoff"]["inputSchema"]
    assert "required" not in TOOLS["start_takeoff_from_chat_files"]["inputSchema"]
    assert "required" not in TOOLS["get_takeoff_status"]["inputSchema"]
    assert "required" not in TOOLS["get_takeoff_results"]["inputSchema"]
    assert "required" not in TOOLS["get_download_links"]["inputSchema"]
    strip = TOOLS["get_upload_link"]["inputSchema"]["properties"]["strip_depth_in"]
    assert "minimum" not in strip and "maximum" not in strip
    bounded = TOOLS["start_takeoff"]["inputSchema"]["properties"]["strip_depth_in"]
    assert bounded["minimum"] == 0 and bounded["maximum"] == 36
    assert TOOLS["check_balance"]["annotations"]["readOnlyHint"] is True
    assert TOOLS["get_download_links"]["annotations"]["readOnlyHint"] is False
    assert TOOLS["start_plan_set_takeoff"]["annotations"]["openWorldHint"] is True
    assert TOOLS["get_upload_page"]["annotations"]["openWorldHint"] is False
