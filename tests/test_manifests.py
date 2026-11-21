"""Plugin manifests, registry file, and the captured public server card."""

from __future__ import annotations

import re
from pathlib import Path

from land_takeoffs_contract.manifests import ROOT, load_json, plugin_versions, server_card, server_url

EXPECTED_TOOLS = [
    "start_takeoff_from_chat_files",
    "list_price_lists",
    "check_balance",
    "start_takeoff",
    "start_plan_set_takeoff",
    "start_cad_takeoff",
    "answer_cad_question",
    "get_takeoff_status",
    "get_takeoff_results",
    "get_download_links",
    "list_takeoffs",
    "get_upload_link",
    "get_upload_page",
]

SECRET_PATTERNS = (
    re.compile(r"gik_live_[A-Za-z0-9_\-]{8,}"),
    re.compile(r"giq_at_[A-Za-z0-9_\-]{8,}"),
    re.compile(r"giq_rt_[A-Za-z0-9_\-]{8,}"),
    re.compile(r"whsec_[A-Za-z0-9]{8,}"),
    re.compile(r"sk_live_[A-Za-z0-9]{8,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
)


def test_versions_match_the_published_server() -> None:
    versions = plugin_versions()
    assert versions == {
        "cursor": "1.1.1",
        "grok": "1.1.1",
        "registry": "1.1.1",
        "server_card": "1.1.1",
    }


def test_every_manifest_points_at_the_same_remote() -> None:
    url = "https://mcp.landtakeoffs.com/mcp"
    assert server_url() == url
    cursor = load_json(ROOT / "mcp.json")
    grok = load_json(ROOT / ".mcp.json")
    registry = load_json(ROOT / "server.json")
    assert cursor["mcpServers"]["land-takeoffs"]["url"] == url
    assert grok["mcpServers"]["land-takeoffs"]["url"] == url
    assert grok["mcpServers"]["land-takeoffs"]["type"] == "http"
    assert "type" not in cursor["mcpServers"]["land-takeoffs"]
    assert registry["remotes"][0] == {"type": "streamable-http", "url": url}
    assert registry["name"] == "com.landtakeoffs/takeoffs"
    assert server_card()["serverInfo"]["version"] == "1.1.1"
    assert server_card()["remotes"][0]["url"] == url


def test_server_card_lists_the_live_tools_and_upload_resource() -> None:
    card = server_card()
    assert [tool["name"] for tool in card["tools"]] == EXPECTED_TOOLS
    assert card["prompts"] == []
    assert card["resources"][0]["uri"] == "ui://land-takeoffs/upload-card.html"
    assert card["authentication"] == {"required": True, "schemes": ["oauth2"]}
    assert card["remotes"][0]["supportedProtocolVersions"] == [
        "2025-11-25",
        "2025-06-18",
        "2025-03-26",
        "2024-11-05",
    ]


def test_configs_do_not_embed_credentials() -> None:
    for relative in ("mcp.json", ".mcp.json", "server.json"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "headers" not in text
        assert "Authorization" not in text
        assert "apiKey" not in text


def test_repository_text_has_no_credential_markers() -> None:
    skipped = {Path("tests/test_manifests.py")}
    offenders: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix in {".png", ".pyc"}:
            continue
        relative = path.relative_to(ROOT)
        if relative in skipped or ".git" in relative.parts or ".venv" in relative.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                offenders.append(f"{relative}: {pattern.pattern}")
    assert offenders == []


def test_skill_names_every_published_tool() -> None:
    skill = (ROOT / "skills" / "run-sitework-takeoff" / "SKILL.md").read_text(encoding="utf-8")
    missing = [name for name in EXPECTED_TOOLS if name not in skill]
    assert missing == []


def test_plugin_manifests_do_not_request_local_execution() -> None:
    for relative in (".cursor-plugin/plugin.json", ".grok-plugin/plugin.json"):
        manifest = load_json(ROOT / relative)
        assert manifest["name"] == "land-takeoffs"
        assert manifest["license"] == "MIT"
        assert "hooks" not in manifest
        assert "mcpServers" not in manifest
        assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
