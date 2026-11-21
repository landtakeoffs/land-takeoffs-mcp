"""Checks against the published Land Takeoffs MCP contract.

The hosted server is not in this repository. This package loads the committed
server card and plugin manifests, validates tool schemas, and runs each tool
against an in-memory stand-in for the `/v1` API the hosted router calls.
"""

from land_takeoffs_contract.behavior import MockApi, ToolError, run_tool
from land_takeoffs_contract.manifests import ROOT, load_json, plugin_versions, server_url

__all__ = [
    "MockApi",
    "ROOT",
    "ToolError",
    "load_json",
    "plugin_versions",
    "run_tool",
    "server_url",
]
