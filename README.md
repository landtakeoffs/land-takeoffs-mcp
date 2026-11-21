# Land Takeoffs MCP

Connect an AI assistant to [Land Takeoffs](https://www.landtakeoffs.com) and run a sitework takeoff from a stamped civil plan-set PDF and/or a CAD file (DWG, DXF, or LandXML). Each quantity comes back with the source sheet or file and a confidence level. Lines the drawings do not show are listed, not guessed. A finished takeoff includes an Excel bid sheet and a PDF summary. A takeoff that includes CAD also gets a project video, still images, a download-all zip, and a 3D site viewer link, rendered from the takeoff geometry.

This repository is the plugin listing: Cursor and Grok manifests, the MCP client config, the registry manifest, and one skill. It does not contain the hosted server. The server is a remote Streamable HTTP endpoint:

```
https://mcp.landtakeoffs.com/mcp
```

The published registry name is `com.landtakeoffs/takeoffs`, version **1.1.1**. A connected assistant can start takeoffs, read results and the credit balance, and fetch downloads. It cannot create API keys or manage connections. No tool deletes data.

Full detail is in the docs:

- [Technical overview](docs/technical-overview.md): tools, inputs and outputs, transport, auth, how the server calls the API, hosting, and a diagram
- [Client setup](docs/client-setup.md): ChatGPT, Claude, Perplexity, Cursor, and Grok, from the files in this repo and the public setup page
- [Security review](docs/security-review.md): findings, what was fixed here, and what is left for the hosted service

## Connect

You need a Land Takeoffs account. The sign-in screen creates one with Google, Microsoft, or email. New accounts include 1 free takeoff. A takeoff uses 1 credit (a plan set uses 1 credit per 100 pages). A failed takeoff is not charged.

Sign-in is OAuth 2.1 with PKCE (S256). Clients that cannot do OAuth can send an API key from the account page as `Authorization: Bearer <key>` or `X-API-Key`. Do not put that key in a shared config file or in this repository.

| Client | What this repo contains | URL |
| --- | --- | --- |
| Cursor | `mcp.json` and `.cursor-plugin/plugin.json` | `https://mcp.landtakeoffs.com/mcp` |
| Grok | `.mcp.json` and `.grok-plugin/plugin.json` | same, with `"type": "http"` |
| Claude, ChatGPT, Perplexity | No client-specific manifest | same remote URL |

Step-by-step setup is in [docs/client-setup.md](docs/client-setup.md). The public setup page is <https://www.landtakeoffs.com/ai>.

## Tools

The live catalogue, including input schemas, is public and does not require a sign-in:

<https://mcp.landtakeoffs.com/.well-known/mcp/server-card.json>

| Tool | What it does | Read-only |
| --- | --- | --- |
| `check_balance` | Credits left, purchased, and used | Yes |
| `list_price_lists` | Names of saved unit-price lists | Yes |
| `list_takeoffs` | Recent takeoffs, newest first | Yes |
| `get_upload_page` | Link to the signed-in account page | Yes |
| `get_takeoff_status` | Progress for a `takeoff_id` or `job_id` | Yes |
| `get_takeoff_results` | Quantities by division, with source and confidence, plus lines not determined | Yes |
| `start_takeoff` | One takeoff from a CAD file and/or a plan-set PDF | No |
| `start_plan_set_takeoff` | Takeoff from a plan-set PDF share link | No |
| `start_cad_takeoff` | Measured earthwork from CAD or terrain links | No |
| `start_takeoff_from_chat_files` | Takeoff from files the chat app passed into the tool | No |
| `answer_cad_question` | Boundary or surface choice that lets a CAD takeoff continue | No |
| `get_download_links` | Creates the Excel bid sheet and PDF summary and returns links, plus CAD media when it exists | No |
| `get_upload_link` | Private single-use upload page, valid 24 hours | No |

There is also one MCP App resource, `ui://land-takeoffs/upload-card.html`, and no prompts. Inputs, response fields, and the API route each tool calls are in the [technical overview](docs/technical-overview.md).

## Repository layout

```
.cursor-plugin/plugin.json          Cursor plugin manifest (1.1.1)
.grok-plugin/plugin.json            Grok plugin manifest (1.1.1)
mcp.json                            Cursor MCP config
.mcp.json                           Grok MCP config
server.json                         Registry manifest for com.landtakeoffs/takeoffs 1.1.1
contract/server-card.json           Public server card captured for the tests
skills/run-sitework-takeoff/        Skill: how to run a takeoff with the tools
src/land_takeoffs_contract/         Schema checks and a mocked /v1 stand-in
tests/                              Tests for every tool
.github/workflows/test.yml          Runs those tests
assets/logo.png                     Logo (1024x1024 PNG)
```

This plugin runs no local code, hooks, or scripts. The Python package only runs in tests.

## Tests

```
python -m pip install -e ".[dev]"
python -m pytest --cov=land_takeoffs_contract --cov-report=term-missing
```

Before this change the repository had no application code and no tests, so there was nothing to measure. The tests do not call the hosted server.

## Support

Email [nate@landtakeoffs.com](mailto:nate@landtakeoffs.com). The public setup page also lists [support@landtakeoffs.com](mailto:support@landtakeoffs.com).

- Privacy policy: <https://www.landtakeoffs.com/privacy>
- Terms of service: <https://www.landtakeoffs.com/terms>

Plans and CAD files are processed on Land Takeoffs servers to produce the takeoff. The privacy policy describes what is collected and how files and results are used. Review it before sending confidential plans.

## License

MIT. See [LICENSE](LICENSE). This license covers the files in this repository. Use of the hosted service is governed by the Land Takeoffs terms.
