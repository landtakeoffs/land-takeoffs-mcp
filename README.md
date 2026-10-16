# Land Takeoffs MCP

Connect your AI assistant to [Land Takeoffs](https://www.landtakeoffs.com), a self-serve sitework estimating product. Send a stamped civil plan-set PDF and/or a CAD file (DWG, DXF or LandXML) and get back sitework quantities, each with the source sheet and a confidence level, plus an Excel bid sheet and a PDF summary.

This repository contains the plugin listing files only (Cursor and Grok plugin manifests, MCP connection config, one skill). The Land Takeoffs service itself is a hosted remote MCP server:

```
https://mcp.landtakeoffs.com/mcp
```

Transport: Streamable HTTP.

Land Takeoffs is built by a licensed grading contractor. It reports what the drawings show and lists anything it could not determine. It does not guess quantities that are not on the plans. Review results before you bid, as you would any takeoff.

## What you get

- **Plan-set takeoff.** Reads a civil plan-set PDF and returns sitework quantities by division (storm, sanitary sewer, water, erosion control, clearing and earthwork, paving, curb and concrete), each with the source sheet and a confidence level. Lines that could not be determined are listed with the reason.
- **Measured cut and fill.** Measures earthwork from existing and proposed surfaces in CAD or terrain files, and asks you when a boundary or surface is unclear.
- **Combined takeoff.** Send a plan set and a CAD file together: earthwork is measured from the CAD, everything else is read from the plans, in one report.
- **Bid-ready files.** Excel bid sheet (optionally priced from your saved price list) and a PDF summary.
- **Project media for CAD takeoffs.** A short project video, still images, a download-all zip and a 3D site viewer link. These are rendered from the takeoff data; nothing is AI-generated. A plan-set-only takeoff has no CAD to render, so it gets no video.

## Connect

You need a Land Takeoffs account. The sign-in screen creates one with Google, Microsoft or email. New accounts include 1 free takeoff. A takeoff costs 1 credit (plan sets: 1 credit per 100 pages). Failed takeoffs are not charged.

### Claude

1. Open **Settings**, then **Connectors**.
2. Find **Land Takeoffs** in the directory and select **Connect**. If it is not listed yet, choose **Add custom connector** and paste `https://mcp.landtakeoffs.com/mcp`.
3. Sign in to Land Takeoffs and approve access.

Claude Code:

```
claude mcp add --transport http land-takeoffs https://mcp.landtakeoffs.com/mcp
```

Then run `/mcp` in Claude Code and sign in.

### Cursor

Install **Land Takeoffs** from the Cursor Marketplace, or add the server by hand to `~/.cursor/mcp.json` (or `.cursor/mcp.json` in a project):

```json
{
  "mcpServers": {
    "land-takeoffs": {
      "url": "https://mcp.landtakeoffs.com/mcp"
    }
  }
}
```

Cursor opens the Land Takeoffs sign-in in your browser on first use.

### Grok Bot

Install **Land Takeoffs** from the plugin marketplace, or add a remote MCP server with the URL `https://mcp.landtakeoffs.com/mcp`. Sign in with your Land Takeoffs account when prompted. Do not paste an API key into chat.

### ChatGPT

Search for **Land Takeoffs** in the app directory and select **Connect**. If it is not listed in your workspace, turn on Developer mode (Settings, Apps and Connectors, Advanced settings), then create a connector with the URL above and choose OAuth.

### Any other MCP client

Add a remote Streamable HTTP server at `https://mcp.landtakeoffs.com/mcp`. Setup guide: <https://www.landtakeoffs.com/ai>

## Authentication

- **OAuth 2.1 with PKCE (S256)** is the default. Clients register through Dynamic Client Registration or a Client ID Metadata Document. You sign in on landtakeoffs.com and approve access. Access tokens last 1 hour and refresh tokens rotate.
- **API key** (for clients that take a pasted key): create a key on your Land Takeoffs account page and send it as `Authorization: Bearer <your key>` or the `X-API-Key` header. Keep it out of shared config files and repositories.
- A connected app can run takeoffs, read results and your credit balance, and fetch downloads. It cannot create API keys or manage connections.
- To disconnect, remove Land Takeoffs in your assistant's connector settings, or revoke it under Connected apps on your Land Takeoffs account page.

No credentials are stored in this repository.

### Network endpoints

- `https://mcp.landtakeoffs.com/mcp` (MCP, Streamable HTTP)
- `https://mcp.landtakeoffs.com/oauth/authorize`, `/oauth/token`, `/oauth/register`, `/oauth/revoke` (OAuth 2.1)
- `https://www.landtakeoffs.com` (sign-in and consent page, account page)

This plugin runs no local code, hooks or scripts.

## Sending your files

Full civil sets are often too large for chat attachments, so the plans do not pass through the assistant. Use any of:

1. **A share link** from Dropbox, Google Drive, OneDrive or SharePoint, or a direct https link anyone with the link can open.
2. **A private upload link.** Ask for an upload link; the assistant gives you a page where you drop files from your computer. The link works for one takeoff and expires after 24 hours.
3. **Your account page** at <https://www.landtakeoffs.com/gradingiq>.

## Example prompts

- "Run a sitework takeoff on this plan set: https://www.dropbox.com/s/..."
- "I have the civil set and the grading DWG on my computer. Give me an upload link and run a combined takeoff."
- "How much cut and fill is on this site, and is it balanced?"
- "List the storm pipe by size with the sheet each run is on."
- "Give me the Excel bid sheet and the PDF summary for my last takeoff."
- "Show my recent takeoffs and how many credits I have left."

A plan-set takeoff usually finishes in a few minutes. Large sets take longer.

## Tools

| Tool | What it does | Read-only |
| --- | --- | --- |
| `check_balance` | Credits left, purchased and used | Yes |
| `list_price_lists` | Names of your saved unit-price lists | Yes |
| `list_takeoffs` | Recent takeoffs, newest first, with status | Yes |
| `start_takeoff` | One takeoff from a CAD file and/or a plan-set PDF (share links) | No |
| `start_plan_set_takeoff` | Takeoff from a plan-set PDF share link | No |
| `start_cad_takeoff` | Measured earthwork from CAD or terrain file links | No |
| `start_takeoff_from_chat_files` | Takeoff from files attached in the chat (for apps that pass attachments to tools) | No |
| `answer_cad_question` | Your choice of site boundary, or existing and proposed surfaces | No |
| `get_takeoff_status` | Progress of a takeoff | Yes |
| `get_takeoff_results` | Quantities by division with source sheet and confidence, plus lines not determined | Yes |
| `get_download_links` | Creates and returns links to the Excel bid sheet, PDF summary, and (CAD takeoffs) video, images, zip and 3D viewer | No (creates files) |
| `get_upload_link` | Private single-use upload page, valid 24 hours | No (creates a link) |
| `get_upload_page` | Link to your account page | Yes |

None of the tools delete data.

## Plugin contents

```
.cursor-plugin/plugin.json   Cursor plugin manifest
.grok-plugin/plugin.json     Grok plugin manifest
mcp.json                     MCP config (Cursor)
.mcp.json                    MCP config (Grok)
skills/run-sitework-takeoff/ Skill: how to run a takeoff with the tools
assets/logo.png              Logo (1024x1024 PNG)
```

## Support

Email [nate@landtakeoffs.com](mailto:nate@landtakeoffs.com). Setup guide: <https://www.landtakeoffs.com/ai>

## Privacy and terms

- Privacy policy: <https://www.landtakeoffs.com/privacy>
- Terms of service: <https://www.landtakeoffs.com/terms>

Your plans and CAD files are processed on Land Takeoffs servers to produce your takeoff. The privacy policy explains what is collected, how files and results are used (including to test and improve takeoff accuracy), and how to contact us. Review it before sending confidential plans.

## License

MIT. See [LICENSE](LICENSE). This license covers the files in this repository; use of the hosted service is governed by the Land Takeoffs terms.
