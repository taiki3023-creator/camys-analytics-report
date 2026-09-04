# Automation Contract

Use this reference when an agent needs the current public automation surface.

## Public REST Routes

- `GET /api/export/plans`
  - Returns public plan metadata and the recommended commercial tier.
- `POST /api/export/jobs`
  - Creates a commercial export job.
- `GET /api/export/jobs/{jobId}`
  - Returns the current job state.

## Authentication

Use either:

- `Authorization: Bearer <api_key>`
- `x-api-key: <api_key>`

## Expected payload

```json
{
  "html": "<section class=\"slide\">...</section>",
  "css": ".slide { width: 1600px; min-height: 900px; }",
  "fileName": "deck.pptx",
  "autoEmbedFonts": false,
  "metadata": {
    "channel": "agent"
  }
}
```

## Job lifecycle

Typical states:

- `queued`
- `processing`
- `completed`
- `failed`

Completed jobs may include:

- `fileName`
- `mimeType`
- `fileBase64`

For agent-facing summaries, do not dump `fileBase64` unless explicitly required. Public API and MCP sanitize untrusted SVG and rasterize it before export.

## MCP mapping

The public stdio MCP server in this repo wraps the same REST routes:

- `html2pptx_list_export_plans`
- `html2pptx_create_export_job`
- `html2pptx_get_export_job`
- `html2pptx_wait_for_export_job`

### MCP response format

The MCP server defaults to `responseFormat: "both"`, returning:

1. **`resource` content block** — embedded PPTX as `blob` (base64), MCP spec compliant
2. **`text` content block** — `Download: <presigned URL>` for clients that cannot handle blob resources

This ensures compatibility with Claude Code and other MCP clients. Agents should extract the download URL from the text block and use `curl -s -L -o <fileName> "<url>"` to save the file locally.
