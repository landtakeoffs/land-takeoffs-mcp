"""Each published tool against the in-memory API. No network calls."""

from __future__ import annotations

import pytest

from land_takeoffs_contract.behavior import ACCOUNT_URL, MockApi, ToolError, run_tool


def test_check_balance_reads_usage() -> None:
    api = MockApi()
    out = run_tool(api, "check_balance", {})
    assert out["credits_available"] == 2
    assert out["credits_purchased"] == 2
    assert out["credits_used"] == 0
    assert out["buy_more"] == ACCOUNT_URL
    assert api.paths() == [("GET", "/v1/usage")]


def test_list_price_lists_returns_names_only() -> None:
    api = MockApi()
    out = run_tool(api, "list_price_lists", {})
    assert out == {"price_lists": [{"name": "Default", "items": 3}]}
    assert api.paths() == [("GET", "/v1/rate-cards")]


def test_list_takeoffs_defaults_and_clamps_the_limit() -> None:
    api = MockApi()
    api.jobs["job-9"] = {
        "id": "job-9",
        "status": "succeeded",
        "project_name": "Oak",
        "kind": "pdf_scope",
        "created_at": "2026-11-21T00:00:00Z",
    }
    listed = run_tool(api, "list_takeoffs", {})
    assert listed["takeoffs"][0]["type"] == "plan set"
    assert api.calls[0]["params"] == {"limit": 10}
    run_tool(api, "list_takeoffs", {"limit": 0})
    assert api.calls[-1]["params"] == {"limit": 10}
    run_tool(api, "list_takeoffs", {"limit": 80})
    assert api.calls[-1]["params"] == {"limit": 50}
    api.jobs["job-8"] = {**api.jobs["job-9"], "id": "job-8", "kind": "cad"}
    cad = run_tool(api, "list_takeoffs", {"limit": 2})
    assert {row["type"] for row in cad["takeoffs"]} <= {"plan set", "CAD"}


def test_get_upload_page_does_not_call_the_api() -> None:
    api = MockApi()
    out = run_tool(api, "get_upload_page", {})
    assert out["upload_page"] == ACCOUNT_URL
    assert api.calls == []


def test_get_upload_link_checks_a_price_list_name_when_one_is_sent() -> None:
    api = MockApi()
    out = run_tool(api, "get_upload_link", {})
    assert out["expires_in_hours"] == 24
    assert out["takeoff_id"] == "intake-upload"
    assert api.calls == []
    named = run_tool(api, "get_upload_link", {"price_list": "Default"})
    assert named["upload_url"].startswith("https://")
    assert api.paths() == [("GET", "/v1/rate-cards")]
    with pytest.raises(ToolError, match="No price list"):
        run_tool(api, "get_upload_link", {"price_list": "missing"})


def test_status_requires_an_id_and_routes_job_ids_to_the_job() -> None:
    api = MockApi()
    with pytest.raises(ToolError, match="takeoff_id"):
        run_tool(api, "get_takeoff_status", {})
    pending = run_tool(api, "get_takeoff_status", {"takeoff_id": "intake-1"})
    assert pending["status"] == "downloading"
    api.jobs["job-1"] = {"id": "job-1", "status": "succeeded", "progress_pct": 100}
    done = run_tool(api, "get_takeoff_status", {"job_id": "job-1", "takeoff_id": "ignored"})
    assert done["status"] == "succeeded"
    assert "get_takeoff_results" in done["next"]
    api.jobs["job-2"] = {
        "id": "job-2",
        "status": "failed",
        "progress_pct": 40,
        "error": {"message": "unreadable sheet"},
    }
    failed = run_tool(api, "get_takeoff_status", {"job_id": "job-2"})
    assert failed["charged"] is False
    assert failed["reason"] == "unreadable sheet"
    api.jobs["job-3"] = {"id": "job-3", "status": "running", "progress_pct": 10}
    running = run_tool(api, "get_takeoff_status", {"job_id": "job-3"})
    assert "30 to 60" in running["next"]


def test_results_group_plan_set_lines_and_can_filter_a_division() -> None:
    api = MockApi()
    with pytest.raises(ToolError, match="takeoff_id"):
        run_tool(api, "get_takeoff_results", {})
    with pytest.raises(ToolError, match="not finished"):
        run_tool(api, "get_takeoff_results", {"takeoff_id": "intake-1"})
    api.results["job-1"] = {
        "id": "job-1",
        "result": {
            "page_count": 4,
            "items": [
                {
                    "category": "Storm",
                    "description": "18 in RCP",
                    "value": 120,
                    "unit": "LF",
                    "source_sheet": "C4.1",
                    "confidence": "High",
                },
                {
                    "category": "Paving",
                    "description": "asphalt",
                    "value": 10,
                    "unit": "SY",
                    "source_sheet": "C5.0",
                    "confidence": None,
                },
            ],
            "cannot_determine": [{"description": "headwall", "reason": "not labeled"}],
        },
    }
    out = run_tool(api, "get_takeoff_results", {"job_id": "job-1", "division": "storm"})
    assert out["kind"] == "plan_set_read"
    assert out["line_count"] == 1
    assert out["lines"][0]["source"] == "Sheet C4.1"
    assert out["lines"][0]["confidence"] == "high"
    assert out["not_determined_count"] == 1
    assert api.paths() == [("GET", "/v1/jobs/job-1/result")]


def test_results_mark_measured_lines_without_a_quantity_as_not_determined() -> None:
    api = MockApi()
    api.results["job-2"] = {
        "id": "job-2",
        "result": {
            "quantities": {
                "items": [
                    {"division": "Earthwork", "description": "cut", "value": 10, "unit": "CY", "confidence": "MED"},
                    {"division": "Earthwork", "description": "swell", "value": None, "notes": "not on the file"},
                ]
            }
        },
    }
    out = run_tool(api, "get_takeoff_results", {"job_id": "job-2"})
    assert out["kind"] == "measured_takeoff"
    assert out["lines"][0]["confidence"] == "med"
    assert out["not_determined"][0]["reason"] == "not on the file"


def test_download_links_create_the_workbook_and_summary_then_ask_for_media() -> None:
    api = MockApi()
    with pytest.raises(ToolError, match="job_id"):
        run_tool(api, "get_download_links", {})
    api.jobs["job-1"] = {"id": "job-1", "status": "succeeded"}
    out = run_tool(api, "get_download_links", {"job_id": "job-1"})
    assert out["excel_bid_sheet"].endswith(".xlsx")
    assert out["pdf_summary"].endswith(".pdf")
    assert out["project_video"]
    assert "short time" in out["note"]
    methods = api.paths()
    assert ("POST", "/v1/jobs/job-1/deliverables") in methods
    assert ("POST", "/v1/jobs/job-1/media") in methods


def test_download_links_surface_a_rendering_video_and_a_viewer() -> None:
    api = MockApi()
    api.jobs["job-1"] = {"id": "job-1", "status": "succeeded"}
    api.media["job-1"] = {"status": "running"}
    rendering = run_tool(api, "get_download_links", {"job_id": "job-1"})
    assert "Rendering" in rendering["project_video"]
    api.media["job-1"] = {"status": "ready", "video": {"download_url": "https://downloads.example/video.mp4"}}
    api.viewer["job-1"] = {"open_url": "https://www.landtakeoffs.com/3d/example"}
    ready = run_tool(api, "get_download_links", {"job_id": "job-1"})
    assert ready["project_video"] == "https://downloads.example/video.mp4"
    assert ready["site_viewer_3d"].endswith("/example")
    api.media["job-1"] = {"status": "absent"}
    quiet = run_tool(api, "get_download_links", {"job_id": "job-1"})
    assert "project_video" not in quiet
    api.jobs["job-4"] = {
        "id": "job-4",
        "status": "cancelled",
        "progress_pct": 0,
        "error": {"code": "cancelled"},
    }
    cancelled = run_tool(api, "get_takeoff_status", {"job_id": "job-4"})
    assert cancelled["reason"] == "cancelled"
    assert cancelled["charged"] is False


def test_download_links_drop_media_when_the_media_call_fails() -> None:
    api = MockApi()
    api.jobs["job-1"] = {"id": "job-1", "status": "succeeded"}

    def fail_media(method: str, path: str, **kw: object) -> object:
        if path.endswith("/media"):
            raise ToolError("media unavailable")
        return MockApi.call(api, method, path, **kw)

    api.call = fail_media  # type: ignore[method-assign]
    out = run_tool(api, "get_download_links", {"job_id": "job-1"})
    assert "excel_bid_sheet" in out
    assert "project_video" not in out


def test_plan_set_start_rejects_a_missing_or_non_https_link_then_posts_the_pdf() -> None:
    api = MockApi()
    with pytest.raises(ToolError, match="plan_set_url"):
        run_tool(api, "start_plan_set_takeoff", {})
    with pytest.raises(ToolError, match="https://"):
        run_tool(api, "start_plan_set_takeoff", {"plan_set_url": "http://example.com/set.pdf"})
    out = run_tool(
        api,
        "start_plan_set_takeoff",
        {
            "plan_set_url": "https://example.com/set.pdf",
            "project_name": "Oak",
            "customer_ref": "A-1",
            "price_list": "rc-1",
        },
    )
    assert out["status"] == "started"
    assert out["takeoff_id"] == "intake-plan"
    posted = api.calls[-1]
    assert posted["path"] == "/v1/quick-pdf-read"
    assert posted["uploaded"] is True
    assert posted["data"]["rate_card_id"] == "rc-1"
    assert posted["data"]["end_customer_ref"] == "A-1"


def test_combined_start_requires_a_file_and_records_the_takeoff_flow() -> None:
    api = MockApi()
    with pytest.raises(ToolError, match="cad_file_url"):
        run_tool(api, "start_takeoff", {})
    with pytest.raises(ToolError, match="cad_file_url"):
        run_tool(api, "start_takeoff", {"cad_reference_urls": ["https://example.com/survey.dwg"]})
    with pytest.raises(ToolError, match="https://"):
        run_tool(api, "start_takeoff", {"plan_set_url": "notes://set"})
    out = run_tool(
        api,
        "start_takeoff",
        {"cad_file_url": "https://example.com/grade.dwg", "plan_set_url": "https://example.com/set.pdf"},
    )
    assert out["status"] == "started"
    assert ("FLOW", "start_takeoff") in api.paths()


def test_cad_start_creates_a_project_uploads_each_file_and_starts_a_job() -> None:
    api = MockApi()
    with pytest.raises(ToolError, match="at least one"):
        run_tool(api, "start_cad_takeoff", {})
    with pytest.raises(ToolError, match="https://"):
        run_tool(api, "start_cad_takeoff", {"file_urls": ["ftp://example.com/a.xml"]})
    out = run_tool(
        api,
        "start_cad_takeoff",
        {"file_urls": ["https://example.com/a.xml", "https://example.com/b.dwg"], "project_name": "Site"},
    )
    assert out["status"] == "started"
    assert api.paths().count(("POST", f"/v1/projects/{out['project_id']}/files")) == 2
    assert ("POST", f"/v1/projects/{out['project_id']}/jobs") in api.paths()


def test_chat_files_require_a_download_url_and_use_the_same_flow() -> None:
    api = MockApi()
    with pytest.raises(ToolError, match="Attach"):
        run_tool(api, "start_takeoff_from_chat_files", {})
    with pytest.raises(ToolError, match="download_url"):
        run_tool(api, "start_takeoff_from_chat_files", {"plan_set": {"file_id": "f"}})
    with pytest.raises(ToolError, match="https://"):
        run_tool(
            api,
            "start_takeoff_from_chat_files",
            {"cad_files": [{"download_url": "http://files.example/a.dwg", "file_id": "f"}]},
        )
    out = run_tool(
        api,
        "start_takeoff_from_chat_files",
        {"plan_set": {"download_url": "https://files.example/set.pdf", "file_id": "f1"}},
    )
    assert out["takeoff_id"] == "intake-chat"
    assert ("FLOW", "start_takeoff") in api.paths()


def test_answer_cad_question_writes_the_choice_then_starts() -> None:
    api = MockApi()
    with pytest.raises(KeyError):
        run_tool(api, "answer_cad_question", {})
    with pytest.raises(ToolError, match="both"):
        run_tool(api, "answer_cad_question", {"project_id": "proj-1", "existing_surface_id": "eg"})
    api.projects["proj-1"] = {"id": "proj-1", "earthwork_inputs": {"shrink_pct": 5}}
    out = run_tool(
        api,
        "answer_cad_question",
        {
            "project_id": "proj-1",
            "boundary_id": "b1",
            "existing_surface_id": "eg",
            "proposed_surface_id": "fg",
            "strip_depth_in": 6,
        },
    )
    assert out["status"] == "started"
    assert ("POST", "/v1/projects/proj-1/scope") in api.paths()
    assert ("PUT", "/v1/projects/proj-1/surfaces/confirm") in api.paths()
    assert ("PUT", "/v1/projects/proj-1/earthwork-inputs") in api.paths()
    saved = next(call for call in api.calls if call["path"].endswith("earthwork-inputs"))
    assert saved["json"]["shrink_pct"] == 5
    assert saved["json"]["strip_depth_in"] == 6


def test_unknown_tool_and_unknown_job_are_errors() -> None:
    api = MockApi()
    with pytest.raises(ToolError, match="Unknown tool"):
        run_tool(api, "delete_everything", {})
    with pytest.raises(ToolError, match="404"):
        run_tool(api, "get_takeoff_status", {"job_id": "missing"})


def test_mock_rejects_a_route_it_does_not_model() -> None:
    api = MockApi()
    with pytest.raises(ToolError, match="Unmodeled"):
        api.call("DELETE", "/v1/projects/proj-1")
