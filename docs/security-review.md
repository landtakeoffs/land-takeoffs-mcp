# Security review

Reviewed 21 November 2026. Scope is the public plugin repository and the hosted MCP server it points at (`https://mcp.landtakeoffs.com/mcp`, Railway service `grading-iq`). The hosted router and its OAuth and API-key code live in the private `landtakeoffs/grading-iq` repository, not in this one. Production settings were read as names only. No secret value was copied, and nothing on the service was changed.

This review does not assert SOC 2 or any other compliance certification. Nothing in this repository is evidence of one.

## Fixed in this change

These are limited to this repository. They do not change the hosted server.

| Severity | Finding | What changed |
| --- | --- | --- |
| Low | The registry's latest entry is `com.landtakeoffs/takeoffs` `1.1.1` and names this repository, but both plugin manifests said `1.0.0` and the repository had no `server.json`. | Plugin manifests are `1.1.1`. `server.json` is the manifest already published for `1.1.1`. The registry was not updated. |
| Low | The skill did not name `start_takeoff_from_chat_files`, which the live server exposes. | The skill's start step now includes that tool. |
| Info | This repository had no test that the committed configs stay free of credentials, and no check that the published tool schemas still parse. | Schema tests, a mocked `/v1` stand-in, a credential-pattern scan, and `.github/workflows/test.yml`. |

Git history of this repository is three commits. A search of that history and of the current tree found no API keys, tokens, or private keys. `mcp.json` and `.mcp.json` contain only the server URL.

## Deferred

These are in the hosted service or in documents this repository does not control. Fixing them would change server behaviour or production configuration, so they were not patched here.

### High

**The server a reviewer must audit is not in the repository the registry names.**

`server.json` and the latest registry entry set `repository` to `https://github.com/landtakeoffs/land-takeoffs-mcp`. That repository is this plugin listing. The router, OAuth implementation, database models, and the API test suite are in private `landtakeoffs/grading-iq` (`api/app/routers/mcp.py`, `api/app/routers/oauth.py`). A review of this repository alone cannot verify credit checks, file fetching, or token storage.

Recommended fix: point the registry `repository` at the repository reviewers will actually receive, or publish the MCP and OAuth modules in the repository the registry already names. Do not publish the registry change until that repository decision is made.

### Medium

**`tools/call` does not enforce the published JSON Schema.**

The router passes `arguments` into the tool function as-is. It checks that start tools have an `https://` link and that status and result tools have an id. It does not reject unknown properties, out-of-range numbers, or values outside an enum. Those constraints are in the card and are only as strong as the client. `get_upload_link` will also accept earthwork fields that are not in its schema.

Recommended fix: validate arguments with the tool's `inputSchema` before doing any work, and return `isError` with the schema message. Add `required` on `start_takeoff` (at least one of the file URLs), on the chat-file tool, and on the status, results, and download tools. Give `get_upload_link.strip_depth_in` the same 0..36 bounds as the other tools.

**Share-link and client-metadata fetches resolve DNS, then connect again.**

`_check_url` rejects a host whose addresses are private, loopback, link-local, multicast, reserved, or unspecified, and it re-checks each redirect. The HTTP client then resolves the name a second time. A name that changes answers between the check and the connection can reach an address the check did not see. The client-metadata fetch uses the same host check and does not follow redirects.

Recommended fix: connect to the address that passed the check, or verify the peer address after connect, and keep the redirect limit. Add an explicit deny for shared address space (RFC 6598) so the result does not depend on which Python version treats that range as private.

**The public setup page and the server disagree about file size.**

The setup page at `https://www.landtakeoffs.com/ai` describes plan sets of 50 to 500 MB and says none of the three upload paths has a size problem. The API setting `max_upload_bytes` defaults to 200 MB. The production variable list for `grading-iq` does not include an override of that setting, so the running process is using the default unless a different commit is deployed. The fetch path rejects a body over that ceiling.

Recommended fix: set the production ceiling to the size the setup page promises, or change the page so it states the ceiling the server enforces.

**Credit enforcement is off unless the environment turns it on.**

`billing_enforced` defaults to false. The comment in settings says metering still runs and enforcement was left off so existing tenants would not be cut off when the ledger shipped. The production service has a `BILLING_ENFORCED` variable. Its value was not read. The tools tell the assistant that a takeoff uses credits and that a failure is not charged. If production is still on the default, the API will not refuse a job for lack of credits.

Recommended fix: confirm the production value. If it is off, either turn it on or stop describing the MCP tools as refusing work when the balance cannot cover it.

**The API dependency set has no lockfile in the tree that was listed.**

`api/pyproject.toml` pins ranges (`fastapi`, `httpx`, `cryptography`, `python-multipart`, `pillow`, `pymupdf`, `stripe`, and others) and there was no `uv.lock`, `poetry.lock`, or requirements lock in that tree. This plugin repository has no runtime dependencies, so there was nothing to upgrade here. A scan of the deployed image was not run.

Recommended fix: commit a lockfile in the API repository and scan the image that Railway runs. Treat `python-multipart`, `pillow`, `cryptography`, and `pymupdf` as the first packages to check, because they parse untrusted uploads.

### Low

**The server card understates how a client can authenticate.**

`authentication.schemes` is `["oauth2"]`. `POST /mcp` also accepts an API key as a Bearer token or `X-API-Key`. The 401 body says so. A client that trusts only the card will not know the key path exists, and a reviewer who trusts only the card will understate who can call the API.

Recommended fix: add the API-key scheme to the card, or drop the key path from the 401 text if OAuth is the only supported client auth.

**Two hostnames reach the same MCP process.**

`https://grading-iq-production.up.railway.app/mcp` returns the same 401 as `https://mcp.landtakeoffs.com/mcp`, and its metadata URL is the custom domain. The source default for `public_base_url` is the Railway hostname. Production sets `PUBLIC_BASE_URL` (value not read); the live issuer is `https://mcp.landtakeoffs.com`, so the deployed value matches the custom domain. The old hostname is still a second front door.

Recommended fix: keep the Railway hostname for the platform, and reject MCP and OAuth requests whose `Host` is not `mcp.landtakeoffs.com` if that second name is no longer wanted.

**Settings ship a localhost database URL that includes a username and password.**

The settings module's own comment says secrets have no defaults. `database_url` still has a default pointing at `localhost`. Production sets `DATABASE_URL`. The default password was not copied into this repository.

Recommended fix: remove the default and fail startup when `DATABASE_URL` is unset, which is what the comment already requires for secrets.

**OAuth client metadata is fetched from a URL the client chooses.**

A `client_id` that is an `https://` URL is fetched (64 KB cap, no redirects, public addresses only) and cached for an hour. That is an intentional Client ID Metadata Document fetch. It is also a server-side request to an attacker-chosen URL that passes the public-address check.

Recommended fix: keep the size cap and the public-address check, pin the resolved address as in the share-link finding, and rate-limit metadata fetches separately from dynamic registration.

**CORS on the API allows more methods than MCP uses.**

An `OPTIONS` request from `https://example.com` was rejected with `Disallowed CORS origin`. The error response still listed `GET, POST, PUT, DELETE` and allowed `Authorization` and `X-API-Key`. The allowed origins in source are `https://landtakeoffs.com` and `https://www.landtakeoffs.com`. The server card itself is `Access-Control-Allow-Origin: *` and allows only `GET, HEAD`, which matches a public catalogue.

Recommended fix: leave the card public. Restrict the API preflight's allowed methods to the methods the browser client uses.

**`not_determined` is truncated.**

The results tool returns at most 25 undetermined lines and a separate count. A caller that only reads the array will miss the rest. The description does not say this.

Recommended fix: state the cap in the tool description, or page the remainder.

### Informational

- No tool is annotated `destructiveHint: true`. None of the 13 tools delete a project. The account page is where a user deletes a project.
- The four tools that fetch a caller-supplied URL are `openWorldHint: true`. The other tools are not.
- Tokens compared for PKCE use `hmac.compare_digest`. API keys and OAuth tokens are looked up by SHA-256, not by comparing plaintext.
- Upload links are described by the connector notes as 256 random bits stored only as a hash, 24 hours, one takeoff, and not a login. That matches the public tool description of the 24-hour single-use link. The upload-link module was not re-read line by line for this review.
- `initialize` logs the client name, protocol, and whether the UI extension is present. It does not log the bearer token.
- The production service holds credentials for the database, object storage, the model provider, payments, and the portal. Names were listed; values were not read and are not recorded here.
- Registry version `1.1.0` is still `active`. It is not `isLatest`, its description differs, and it has no repository URL. Clients that pin `1.1.0` see a different description for the same remote URL.
- The public setup page's tool table omits `start_takeoff_from_chat_files` and `list_price_lists`.
- `get_takeoff_status` describes the state "finished". The value the router returns for a completed job is `succeeded`.

## What a follow-up review still needs

1. The production value of `BILLING_ENFORCED`, `MAX_UPLOAD_BYTES` if it is ever set, and the OAuth TTL variables.
2. The object-storage region, compared with the "United States" sentence on the public setup page.
3. A lockfile scan and an image scan of the `grading-iq` deploy, in that repository.
4. The `start_takeoff` service's own HTTP calls, which sit behind the MCP router and were not expanded into a route list here.
