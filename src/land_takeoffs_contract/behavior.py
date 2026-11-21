"""Basic tool behavior against a mocked Land Takeoffs API.

The hosted router calls its own `/v1` routes in-process and does not enforce
JSON Schema before that call. `validate_arguments` is what a strict client
does with the published schema. `run_tool` is the server-side behavior that
was verified in the hosted router: required links, the https check, id
routing, and the API paths each tool hits.
"""

from __future__ import annotations

from typing import Any

import jsonschema

from land_takeoffs_contract.manifests import tools_by_name

ACCOUNT_URL = "https://www.landtakeoffs.com/gradingiq"


class ToolError(Exception):
    """A failure the assistant should read. The hosted router sets isError."""


class MockApi:
    """Records `/v1` calls and returns fixture bodies. Nothing leaves the process."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.usage = {"balance": 2, "purchased": 2, "consumed": 0}
        self.rate_cards: list[dict[str, Any]] = [
            {"id": "rc-1", "name": "Default", "entry_count": 3}
        ]
        self.jobs: dict[str, dict[str, Any]] = {}
        self.results: dict[str, dict[str, Any]] = {}
        self.deliverables: dict[str, str] = {}
        self.media: dict[str, dict[str, Any]] = {}
        self.viewer: dict[str, dict[str, Any]] = {}
        self.projects: dict[str, dict[str, Any]] = {}
        self._seq = 1

    def call(self, method: str, path: str, **kw: Any) -> Any:
        recorded: dict[str, Any] = {"method": method, "path": path}
        for key in ("json", "params", "data"):
            if key in kw and kw[key] is not None:
                recorded[key] = kw[key]
        if "files" in kw:
            recorded["uploaded"] = True
        self.calls.append(recorded)
        return self._route(method, path, kw)

    def _route(self, method: str, path: str, kw: dict[str, Any]) -> Any:
        if method == "GET" and path == "/v1/usage":
            return dict(self.usage)
        if method == "GET" and path == "/v1/rate-cards":
            return [dict(card) for card in self.rate_cards]
        if method == "GET" and path == "/v1/jobs":
            limit = int((kw.get("params") or {}).get("limit") or 10)
            return {"jobs": list(self.jobs.values())[:limit]}
        if method == "POST" and path == "/v1/quick-pdf-read":
            return {"id": self._add_job("pdf_scope", (kw.get("data") or {}).get("project_name"))}
        if method == "POST" and path == "/v1/projects":
            pid = f"proj-{self._seq}"
            self._seq += 1
            self.projects[pid] = {"id": pid, "earthwork_inputs": {}}
            return {"id": pid}
        if method == "POST" and path.endswith("/files") and "/projects/" in path:
            return {"ok": True}
        if method == "GET" and path.startswith("/v1/projects/") and path.count("/") == 3:
            pid = path.split("/")[3]
            project = self.projects.get(pid)
            if project is None:
                raise ToolError("Request failed (404).")
            return dict(project)
        if method == "POST" and path.endswith("/scope"):
            return {"ok": True}
        if method == "PUT" and path.endswith("/surfaces/confirm"):
            return {"ok": True}
        if method == "PUT" and path.endswith("/earthwork-inputs"):
            pid = path.split("/")[3]
            self.projects.setdefault(pid, {"id": pid, "earthwork_inputs": {}})
            self.projects[pid]["earthwork_inputs"] = kw.get("json") or {}
            return {"ok": True}
        if method == "POST" and path.endswith("/jobs") and "/projects/" in path:
            return {"id": self._add_job("cad", "CAD")}
        if method == "GET" and path.startswith("/v1/jobs/") and path.endswith("/result"):
            jid = path.split("/")[3]
            if jid not in self.results:
                raise ToolError("Request failed (404).")
            return self.results[jid]
        if method == "GET" and path.startswith("/v1/jobs/") and path.count("/") == 3:
            jid = path.split("/")[3]
            if jid not in self.jobs:
                raise ToolError("Request failed (404).")
            return dict(self.jobs[jid])
        if method == "POST" and path.endswith("/deliverables"):
            jid = path.split("/")[3]
            if jid not in self.jobs:
                raise ToolError("Request failed (404).")
            fmt = (kw.get("json") or {}).get("format") or "bin"
            did = f"del-{self._seq}"
            self._seq += 1
            self.deliverables[did] = f"https://downloads.example/{did}.{fmt}"
            return {"id": did}
        if method == "GET" and path.startswith("/v1/deliverables/"):
            did = path.split("/")[3]
            if did not in self.deliverables:
                raise ToolError("Request failed (404).")
            return {"download_url": self.deliverables[did]}
        if method == "POST" and path.endswith("/media"):
            jid = path.split("/")[3]
            return dict(self.media.get(jid, {"status": "skipped", "message": "No CAD file to build a video from."}))
        if method == "GET" and path.endswith("/viewer"):
            jid = path.split("/")[3]
            return dict(self.viewer.get(jid, {}))
        raise ToolError(f"Unmodeled API call {method} {path}")

    def _add_job(self, kind: str, project_name: str | None) -> str:
        jid = f"job-{self._seq}"
        self._seq += 1
        self.jobs[jid] = {
            "id": jid,
            "status": "queued",
            "progress_pct": 0,
            "project_name": project_name or "Takeoff",
            "kind": kind,
            "created_at": "2026-11-21T00:00:00Z",
        }
        return jid

    def paths(self) -> list[tuple[str, str]]:
        return [(call["method"], call["path"]) for call in self.calls]


def validate_arguments(name: str, arguments: dict[str, Any]) -> None:
    """Validate one tool payload against the published input schema."""
    tool = tools_by_name().get(name)
    if tool is None:
        raise ToolError(f"Unknown tool: {name}")
    try:
        jsonschema.validate(arguments, tool["inputSchema"])
    except jsonschema.ValidationError as exc:
        raise ToolError(exc.message) from exc


def _https(urls: list[Any]) -> None:
    for url in urls:
        if not str(url).strip().lower().startswith("https://"):
            raise ToolError("Links must start with https://. Share the file and use its link.")


def _price_list_id(api: MockApi, value: Any) -> str | None:
    if value in (None, ""):
        return None
    want = str(value).strip().lower()
    lists = api.call("GET", "/v1/rate-cards")
    for card in lists or []:
        if want in (str(card.get("id")).lower(), str(card.get("name") or "").strip().lower()):
            return str(card["id"])
    names = ", ".join(str(card.get("name")) for card in lists or []) or "none saved yet"
    raise ToolError(f"No price list named '{value}'. Saved lists: {names}.")


def _job_status(api: MockApi, job_id: str) -> dict[str, Any]:
    job = api.call("GET", f"/v1/jobs/{job_id}")
    status = job.get("status")
    out: dict[str, Any] = {
        "job_id": job.get("id"),
        "status": status,
        "progress_pct": job.get("progress_pct"),
    }
    if status == "succeeded":
        out["next"] = "Call get_takeoff_results, then get_download_links."
    elif status in ("failed", "cancelled"):
        err = job.get("error") or {}
        out["reason"] = err.get("message") or err.get("code")
        out["charged"] = False
    else:
        out["next"] = "Still working. Check again in 30 to 60 seconds."
    return out


def _summarize(job_id: str, result: dict[str, Any], division: str | None) -> dict[str, Any]:
    lines: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    if isinstance(result.get("items"), list) and not result.get("quantities"):
        kind = "plan_set_read"
        for item in result["items"]:
            source = f"Sheet {item['source_sheet']}" if item.get("source_sheet") else None
            lines.append(
                {
                    "division": item.get("category"),
                    "description": item.get("description"),
                    "quantity": item.get("value"),
                    "unit": item.get("unit"),
                    "source": source,
                    "confidence": None if item.get("confidence") is None else str(item["confidence"]).lower(),
                }
            )
        for row in result.get("cannot_determine") or []:
            unknown.append({"description": row.get("description"), "reason": row.get("reason")})
    else:
        kind = "measured_takeoff"
        for item in (result.get("quantities") or {}).get("items") or []:
            if item.get("value") is None:
                unknown.append(
                    {"description": item.get("description"), "reason": (item.get("notes") or "")[:300]}
                )
                continue
            lines.append(
                {
                    "division": item.get("division"),
                    "description": item.get("description"),
                    "quantity": item.get("value"),
                    "unit": item.get("unit"),
                    "source": item.get("source"),
                    "confidence": None if item.get("confidence") is None else str(item["confidence"]).lower(),
                }
            )
    if division:
        want = division.strip().lower()
        lines = [line for line in lines if want in str(line.get("division") or "").lower()]
    return {
        "job_id": job_id,
        "kind": kind,
        "page_count": result.get("page_count"),
        "line_count": len(lines),
        "lines": lines,
        "not_determined": unknown[:25],
        "not_determined_count": len(unknown),
    }


def _media(api: MockApi, job_id: str) -> dict[str, Any]:
    try:
        media = api.call("POST", f"/v1/jobs/{job_id}/media")
    except ToolError:
        return {}
    if not media.get("video"):
        if media.get("status") in ("queued", "running"):
            return {"project_video": "Rendering now (a few minutes). Call again for the video link."}
        if media.get("status") == "skipped":
            return {"project_video": media.get("message") or "No CAD file to build a video from."}
        return {}
    out: dict[str, Any] = {"project_video": media["video"].get("download_url")}
    viewer = api.call("GET", f"/v1/jobs/{job_id}/viewer")
    if viewer.get("open_url"):
        out["site_viewer_3d"] = viewer["open_url"]
    return out


def run_tool(api: MockApi, name: str, args: dict[str, Any] | None) -> dict[str, Any]:
    """Run one published tool against `api`. Unknown tools and bad links raise ToolError."""
    args = dict(args or {})
    if name == "check_balance":
        usage = api.call("GET", "/v1/usage")
        return {
            "credits_available": usage.get("balance"),
            "credits_purchased": usage.get("purchased"),
            "credits_used": usage.get("consumed"),
            "buy_more": ACCOUNT_URL,
        }
    if name == "list_price_lists":
        cards = api.call("GET", "/v1/rate-cards")
        return {
            "price_lists": [
                {"name": card.get("name"), "items": card.get("entry_count")} for card in cards or []
            ]
        }
    if name == "list_takeoffs":
        limit = int(args.get("limit") or 10)
        limit = max(1, min(limit, 50))
        res = api.call("GET", "/v1/jobs", params={"limit": limit})
        return {
            "takeoffs": [
                {
                    "job_id": job.get("id"),
                    "project": job.get("project_name"),
                    "type": "plan set" if job.get("kind") == "pdf_scope" else "CAD",
                    "status": job.get("status"),
                    "created_at": job.get("created_at"),
                }
                for job in res.get("jobs") or []
            ]
        }
    if name == "get_upload_page":
        return {
            "upload_page": ACCOUNT_URL,
            "instructions": (
                "Open the page, sign in, and drop the plan-set PDF or CAD files under New takeoff."
            ),
        }
    if name == "get_upload_link":
        _price_list_id(api, args.get("price_list"))
        return {
            "upload_url": "https://mcp.landtakeoffs.com/u/example",
            "expires_in_hours": 24,
            "takeoff_id": "intake-upload",
        }
    if name == "get_takeoff_status":
        if not args.get("takeoff_id") and not args.get("job_id"):
            raise ToolError("Give the takeoff_id (or a job_id) from the start tool.")
        if args.get("takeoff_id") and not args.get("job_id"):
            return {"takeoff_id": str(args["takeoff_id"]), "status": "downloading"}
        return _job_status(api, str(args["job_id"]))
    if name == "get_takeoff_results":
        if not args.get("job_id") and not args.get("takeoff_id"):
            raise ToolError("Give the takeoff_id from the start tool, or a job_id.")
        if not args.get("job_id"):
            raise ToolError("This takeoff is not finished. Call get_takeoff_status and wait.")
        jid = str(args["job_id"])
        body = api.call("GET", f"/v1/jobs/{jid}/result")
        return _summarize(str(body.get("id") or jid), body.get("result") or {}, args.get("division"))
    if name == "get_download_links":
        if not args.get("job_id"):
            raise ToolError("Give the takeoff_id from the start tool, or a job_id.")
        jid = str(args["job_id"])
        links: dict[str, Any] = {}
        for fmt, label in (("xlsx", "excel_bid_sheet"), ("pdf", "pdf_summary")):
            created = api.call(
                "POST", f"/v1/jobs/{jid}/deliverables", json={"format": fmt, "mode": "client"}
            )
            downloaded = api.call("GET", f"/v1/deliverables/{created['id']}")
            links[label] = downloaded.get("download_url")
        links["note"] = "Links expire after a short time. Call again for fresh ones."
        links.update(_media(api, jid))
        return links
    if name == "start_plan_set_takeoff":
        url = args.get("plan_set_url")
        if not url:
            raise ToolError("Provide plan_set_url, a share link to the plan-set PDF.")
        _https([url])
        form: dict[str, Any] = {}
        if args.get("project_name"):
            form["project_name"] = str(args["project_name"])[:255]
        if args.get("customer_ref"):
            form["end_customer_ref"] = str(args["customer_ref"])[:128]
        price_list_id = _price_list_id(api, args.get("price_list"))
        if price_list_id:
            form["rate_card_id"] = price_list_id
        job = api.call("POST", "/v1/quick-pdf-read", data=form, files={"file": True})
        return {
            "status": "started",
            "job_id": job.get("id"),
            "takeoff_id": "intake-plan",
            "next": "Call get_takeoff_status every 30 to 60 seconds until it succeeds.",
        }
    if name == "start_takeoff":
        cad_url, pdf_url = args.get("cad_file_url"), args.get("plan_set_url")
        if not cad_url and not pdf_url:
            raise ToolError("Give a cad_file_url, a plan_set_url, or both.")
        refs = list(args.get("cad_reference_urls") or [])
        if refs and not cad_url:
            raise ToolError("Send cad_file_url with the referenced drawings.")
        _https([item for item in (cad_url, pdf_url, *refs) if item])
        _price_list_id(api, args.get("price_list"))
        # The hosted router hands the downloaded files to the in-process
        # takeoff flow. That flow is not a single /v1 route in the MCP router.
        api.calls.append({"method": "FLOW", "path": "start_takeoff"})
        return {
            "status": "started",
            "project_id": "proj-flow",
            "job_id": "job-flow",
            "takeoff_id": "intake-combined",
        }
    if name == "start_cad_takeoff":
        urls = [str(url) for url in args.get("file_urls") or []][:20]
        if not urls:
            raise ToolError("Provide at least one file link.")
        _https(urls)
        _price_list_id(api, args.get("price_list"))
        project = api.call(
            "POST",
            "/v1/projects",
            json={"name": str(args.get("project_name") or "CAD takeoff")[:255]},
        )
        pid = str(project["id"])
        for _url in urls:
            api.call("POST", f"/v1/projects/{pid}/files", files={"files": True})
        job = api.call("POST", f"/v1/projects/{pid}/jobs", json={})
        return {
            "status": "started",
            "project_id": pid,
            "job_id": job.get("id"),
            "files": urls,
            "takeoff_id": "intake-cad",
        }
    if name == "start_takeoff_from_chat_files":
        files = ([args["plan_set"]] if args.get("plan_set") else []) + list(args.get("cad_files") or [])
        if not files:
            raise ToolError("Attach a plan-set PDF, CAD files, or both.")
        urls = []
        for item in files:
            if not isinstance(item, dict) or not item.get("download_url"):
                raise ToolError("Each attached file needs its download_url.")
            urls.append(item["download_url"])
        _https(urls)
        _price_list_id(api, args.get("price_list"))
        api.calls.append({"method": "FLOW", "path": "start_takeoff"})
        return {
            "status": "started",
            "project_id": "proj-flow",
            "job_id": "job-flow",
            "takeoff_id": "intake-chat",
        }
    if name == "answer_cad_question":
        if "project_id" not in args:
            raise KeyError("project_id")
        pid = str(args["project_id"])
        if args.get("boundary_id"):
            api.call("POST", f"/v1/projects/{pid}/scope", json={"boundary_id": args["boundary_id"]})
        existing, proposed = args.get("existing_surface_id"), args.get("proposed_surface_id")
        if existing or proposed:
            if not (existing and proposed):
                raise ToolError("Give both existing_surface_id and proposed_surface_id.")
            api.call(
                "PUT",
                f"/v1/projects/{pid}/surfaces/confirm",
                json={"existing_surface_id": existing, "proposed_surface_id": proposed},
            )
        stated = {
            key: args[key]
            for key in ("strip_depth_in", "shrink_pct", "topsoil_reuse_pct")
            if args.get(key) is not None
        }
        if stated:
            project = api.call("GET", f"/v1/projects/{pid}")
            merged = {**(project.get("earthwork_inputs") or {}), **stated}
            api.call("PUT", f"/v1/projects/{pid}/earthwork-inputs", json=merged)
        job = api.call("POST", f"/v1/projects/{pid}/jobs", json={})
        return {"status": "started", "project_id": pid, "job_id": job.get("id")}
    raise ToolError(f"Unknown tool {name}.")
