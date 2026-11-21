"""Load the plugin manifests and the captured public server card."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SERVER_CARD = ROOT / "contract" / "server-card.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def server_card() -> dict[str, Any]:
    card = load_json(SERVER_CARD)
    if not isinstance(card, dict) or not isinstance(card.get("tools"), list):
        raise ValueError("server card is missing its tool list")
    return card


def tools_by_name() -> dict[str, dict[str, Any]]:
    return {tool["name"]: tool for tool in server_card()["tools"]}


def plugin_versions() -> dict[str, str]:
    cursor = load_json(ROOT / ".cursor-plugin" / "plugin.json")
    grok = load_json(ROOT / ".grok-plugin" / "plugin.json")
    registry = load_json(ROOT / "server.json")
    return {
        "cursor": cursor["version"],
        "grok": grok["version"],
        "registry": registry["version"],
        "server_card": server_card()["version"],
    }


def server_url() -> str:
    return load_json(ROOT / "server.json")["remotes"][0]["url"]
