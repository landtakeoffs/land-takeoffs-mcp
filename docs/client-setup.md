# Client setup

The hosted server is remote Streamable HTTP. Every client in this list uses the same URL:

```
https://mcp.landtakeoffs.com/mcp
```

That URL is the one committed in `mcp.json`, `.mcp.json`, and `server.json`. A request with no credential returns HTTP 401 and a `WWW-Authenticate` header pointing at the OAuth protected-resource metadata. Sign in with a Land Takeoffs account, or send an API key from the account page. Do not paste a key into chat or commit one.

This page only describes setup that is in this repository or on the public setup page. It does not describe a directory listing that was not checked by completing a connect flow.

## Cursor

Committed files:

- `.cursor-plugin/plugin.json` names the plugin `land-takeoffs`, version `1.1.1`. It has no server URL and no hooks.
- `mcp.json` is the client config:

```json
{
  "mcpServers": {
    "land-takeoffs": {
      "url": "https://mcp.landtakeoffs.com/mcp"
    }
  }
}
```

There is no `type` field and no `headers` field. Cursor treats a remote `url` as Streamable HTTP and opens the Land Takeoffs sign-in in the browser on first use.

To add it by hand, put that block in `~/.cursor/mcp.json` or in a project's `.cursor/mcp.json`. The plugin can also be installed from the Cursor Marketplace; this repository does not contain a Marketplace install log.

## Grok

Committed files:

- `.grok-plugin/plugin.json` names the plugin `land-takeoffs`, version `1.1.1`. It has no server URL and no hooks.
- `.mcp.json` is the client config. It is the same server as Cursor, plus the transport field Grok's config uses:

```json
{
  "mcpServers": {
    "land-takeoffs": {
      "type": "http",
      "url": "https://mcp.landtakeoffs.com/mcp"
    }
  }
}
```

Install **Land Takeoffs** from the plugin marketplace, or add a remote MCP server with that URL. Sign in when prompted. Do not paste an API key into chat. Neither committed file contains a key.

## Claude

This repository has no Claude config file. The public setup page at <https://www.landtakeoffs.com/ai> says:

1. Open **Settings**, then **Connectors**.
2. Find **Land Takeoffs** in the directory and select **Connect**. If it is not in the directory yet, choose **Add custom connector** and paste `https://mcp.landtakeoffs.com/mcp`.
3. Sign in to Land Takeoffs and approve access.
4. In a chat, turn Land Takeoffs on from the tools menu if it is not already on.

The README in this repository also documents Claude Code, which has no config file here:

```
claude mcp add --transport http land-takeoffs https://mcp.landtakeoffs.com/mcp
```

Then run `/mcp` in Claude Code and sign in. That command does not attach an API key. The hosted server accepts a key as a Bearer token for clients that cannot complete OAuth; keep the key out of shell history that gets committed.

Claude team and enterprise workspaces may require an owner to add a custom connector before members can use it. That constraint is not encoded in this repository.

## ChatGPT

This repository has no ChatGPT config file. The public setup page says:

1. Open the ChatGPT app directory and search for **Land Takeoffs**.
2. Select **Connect**.
3. Sign in to Land Takeoffs and approve access.

The README also documents a custom connector for a workspace where the directory entry is not listed: turn on Developer mode (Settings, Apps and Connectors, Advanced settings), create a connector with `https://mcp.landtakeoffs.com/mcp`, and choose OAuth. The live server's 401 response is what starts that OAuth discovery. No client secret is required: the authorization server advertises `token_endpoint_auth_methods_supported: ["none"]` and a dynamic registration endpoint.

`start_takeoff_from_chat_files` is the tool for a plan set or CAD file the ChatGPT app passes into the tool call. Files that exist only on the user's computer use `get_upload_link` instead.

## Perplexity

This repository has no Perplexity manifest. Perplexity's help center documents a custom remote connector as: open **Plugins**, then **Add custom**, then **Add MCP connector**, choose **Remote**, and enter a name plus an `https://` MCP server URL. Use `https://mcp.landtakeoffs.com/mcp`.

The hosted server supports dynamic client registration and PKCE S256, and it does not issue client secrets (`token_endpoint_auth_methods_supported` is `none`). Perplexity's help page says a client id and secret are needed only when the remote server does not support dynamic registration. Organization accounts may need an administrator to allow custom connectors. There is no Perplexity directory entry recorded in this repository.

## After it is connected

1. Send files as a share link (Dropbox, Google Drive, OneDrive or SharePoint, or a direct https link anyone with the link can open), or ask for `get_upload_link` and use that page. The upload link is for one takeoff and expires after 24 hours.
2. For a CAD file, the skill in `skills/run-sitework-takeoff/SKILL.md` says to ask for topsoil strip depth, shrink percent, and how much stripped topsoil is reused as fill before starting.
3. Poll `get_takeoff_status` with the returned `takeoff_id` until it succeeds or fails, then call `get_takeoff_results` and `get_download_links`.

To disconnect, remove the connector in the assistant, or revoke it under Connected apps on the Land Takeoffs account page.
