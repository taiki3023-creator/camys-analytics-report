---
name: edit-slide
version: 1.1.6
description: Open local html2pptx slide HTML files in the PowerPoint-style visual editor with a localhost bridge for two-way file sync. Prefer the local MCP tool because it starts the loopback editor UI and bridge; never use hosted edit-slide for local files.
---

# edit-slide

Use this skill when a user wants to open or visually edit a local html2pptx slide HTML file.

Trigger this skill for phrases such as:

- "ノーコードで編集できる画面を開いて"
- "HTMLでスライドを作って編集画面を展開して"
- "open the editor"
- "preview the slides visually"
- "let me edit the generated slide HTML"

## What This Provides

The UI must be served from a loopback origin such as `http://localhost:<port>/edit-slide` when the html2pptx app is running locally. Do not use hosted `https://html2pptx.app/edit-slide` for local file editing. The user's local files are read and saved by a small localhost bridge started by the `html2pptx-cli`.

The same edit flow can be launched either by the CLI or by the local stdio MCP
tool `html2pptx_open_local_slide_editor`. Remote `/mcp` can still export PPTX
and read docs/templates, but it cannot open files on the user's machine, so it
does not expose local editor tools.

This means the skill alone is not the UI. The runtime path is:

```
html2pptx edit <file>
  -> starts http://127.0.0.1:<port> bridge in the user's current project
  -> opens http://localhost:<editor-port>/edit-slide?file=<path>&bridge=<localhost>#bridgeToken=<session-token>
  -> browser edits are saved back to the same local HTML file
```

## Requirements

- Node.js 18+
- `html2pptx-cli` installed, available through npm, or run from the hosted tarball URL below
- The target file must be `.html` or `.htm`
- The file should contain one or more `<section class="slide">` elements

If `npm` / `npx` is not available in the agent environment, prefer the local
stdio MCP tool when it is already configured. If it is not configured, ask the
user before adding it; otherwise the user must install or expose a CLI runner.

No API key is required for local visual editing. An API key is only needed when exporting through the authenticated PPTX conversion API.

## MCP Choice And Consent

Use remote MCP when the agent only needs to export HTML to PPTX or inspect
html2pptx docs, usage, plans, and templates. Use local stdio MCP when the agent
must open a local `.html` / `.htm` file in edit-slide and write browser edits
back to disk.

Do not silently install or add local stdio MCP. Adding it changes the user's MCP
configuration. If the tool is not already available and you want to add it, ask
the user first with a concise confirmation such as:

```text
ローカルHTMLを edit ページで開くには、html2pptx の local MCP を追加する必要があります。
この設定はこのPCの MCP 設定を変更します。追加して進めてよいですか？
```

## Open A File

If the local stdio MCP tool `html2pptx_open_local_slide_editor` is available, call it with only the project-relative `filePath`; it starts or reuses the loopback editor UI and starts the localhost file bridge.

If local MCP is not available, use a source checkout or local editor app install for the loopback UI and the hosted CLI tarball for the bridge when the npm package cache does not yet have the newest CLI:

```bash
npx --yes https://html2pptx.app/downloads/html2pptx-cli-0.4.0.tgz edit ./html2pptx/slides.html
```

If npm has `html2pptx-cli@0.4.0` or newer available in the user's environment, this shorter form is also valid:

```bash
npx --yes html2pptx-cli edit ./html2pptx/slides.html
```

If `html2pptx-cli` is installed globally:

```bash
html2pptx edit ./html2pptx/slides.html
```

Useful options:

```bash
html2pptx edit ./html2pptx/slides.html --no-open
html2pptx edit ./html2pptx/slides.html --port 3217
html2pptx edit ./html2pptx/slides.html --base-url http://localhost:<editor-port>
```

Use `--no-open` when you should only print the URL instead of opening the browser.

## Agent Workflow

When a user asks to preview, open, visually inspect, launch an editable screen, or no-code edit a slide HTML file:

1. Ensure the HTML file is inside the current project and has a `.html` or `.htm` extension.
2. For generated html2pptx slide decks, save the file under `./html2pptx/<fileName>.html`.
3. Prefer a project-relative path in the command so the URL stays portable.
4. If the local stdio MCP tool `html2pptx_open_local_slide_editor` is already available, call it with `{ "filePath": "<path>" }`; it starts or reuses the loopback editor UI and internally runs the CLI bridge.
5. If local stdio MCP is not available, either ask the user before adding it or use the CLI fallback. Do not add local MCP without confirmation.
6. Otherwise run `npx --yes https://html2pptx.app/downloads/html2pptx-cli-0.4.0.tgz edit <path>` from an environment where the local editor UI can be resolved. Do not add a hosted `--base-url`.
7. If the CLI fallback reports that the editor UI is unavailable, use the local MCP package or run from an html2pptx source checkout.
8. Keep the command running. It owns the localhost bridge used for reads and saves.
9. In the final response, include the CLI/MCP-generated editor URL. It must start with `http://localhost:<editor-port>/edit-slide?file=...` and include `&bridge=...#bridgeToken=...`.
10. After the user edits in the browser, re-read the HTML file from disk before making further edits or exporting.

If this skill is being used together with the `html2pptx` skill, the expected combined flow is: author slide-safe HTML, save it under `./html2pptx/`, open edit-slide through the local bridge, and only export to PPTX when the user explicitly asks for a PowerPoint file.

Editor state is project-local. Each project that runs the local editor gets its own `.html2pptx/edit-slide/` directory. The editor does not create version history, backups, or audit logs; browser edits overwrite the current HTML file after the optimistic hash check passes. Element comments are saved in the same edited HTML file as `data-html2pptx-comment*` attributes, so the `html2pptx` skill can read them later only when the user explicitly asks to apply comments.

Example:

```bash
npx --yes https://html2pptx.app/downloads/html2pptx-cli-0.4.0.tgz edit ./html2pptx/product-roadmap.html
```

Expected result:

```text
Local bridge: http://127.0.0.1:3217
Editor URL: http://localhost:<editor-port>/edit-slide?file=html2pptx%2Fproduct-roadmap.html&bridge=http%3A%2F%2F127.0.0.1%3A3217#bridgeToken=<session-token>
```

## Local Repository Use

Do not use `https://html2pptx.app/edit-slide` or a bare `http://localhost:<editor-port>/edit-slide` as a standalone editor URL. The route is only for a local edit session launched with a target file and localhost bridge. Local UI still needs the CLI/MCP bridge URL and session token.

## Editing Contract

- The bridge only serves `127.0.0.1`.
- The editor URL includes a per-session secret token in the fragment; the token is not sent to the hosted app request, the editor must present it for local reads and writes, and removes it from the address bar after startup.
- It accepts reads/writes for `.html` and `.htm` files under the current working directory.
- Writes require the editor's local write header and an optimistic `baseHash`.
- The editor does not create version history, backups, or audit logs.
- The editor uses a browser-tab lock so duplicate tabs do not silently overwrite each other.
- The slide preview iframe uses no-referrer handling so external image/font loads do not receive the tokenized editor URL.
- The editor UI can read the selected local HTML through the bridge while the command is running. Use only loopback UI (`http://localhost:<editor-port>` or another localhost origin); hosted UI is not allowed for local file editing.
- The MCP launcher is stdio-only and only starts this same local CLI bridge. Remote `/mcp` does not expose local editor tools because remote servers cannot access files on the user's machine.
- Adding the local stdio MCP server is a user environment configuration change. Ask for confirmation before adding it; otherwise use the CLI fallback.
- PPTX export is separate from visual editing. The local editor's export button should only show a prompt telling the user to ask Claude Code or another agent: `Claude Codeや各エージェントに、html2pptx skillsを使って、HTMLをPowerPoint出力してください。` Do not wire this button to direct PPTX generation.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `html2pptx: command not found` | Use the already-configured local stdio MCP tool, use `npx --yes https://html2pptx.app/downloads/html2pptx-cli-0.4.0.tgz edit <file>`, or install `html2pptx-cli@0.4.0+` globally. |
| `npx: command not found` | Use the already-configured local stdio MCP tool `html2pptx_open_local_slide_editor`, or ask before adding local MCP. If local MCP is not available, install/expose npm or a global `html2pptx` CLI before opening edit-slide. |
| Browser opens but the deck does not load | Check that the path is relative to the command's working directory and the file extension is `.html` or `.htm`. |
| Saves fail after the page was open for a while | The terminal bridge was probably stopped. Run the edit command again and reopen the URL. |
| Local MCP is not configured | Ask the user before adding it. If they decline, use the CLI bridge command instead. |
| A second tab is view-only | This is expected. The editor prevents two tabs from writing the same file unless the user transfers the edit lock. |
| Need to share the deck publicly | Do not use the local editor bridge for sharing. Use the html2pptx skill's remote MCP publishing flow to create a draft only: run AI security preflight, validate HTML, fix errors, then call `html2pptx_publish_template` with `visibility: "draft"`. Final sharing/publishing must happen in the dashboard. |

After the user edits visually, the source of truth is the HTML file on disk. Re-read the file before continuing.
