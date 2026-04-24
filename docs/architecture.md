# PagePop Skills Architecture

This repository hosts public PagePop integrations.

The repository is organized around three layers:

- `packages/pagepop-core`: shared PagePop client logic, including configuration, authorization, streaming, and artifact helpers.
- `packages/pagepop-skill`: the generic installable skill package. It should not be tied to a single host application.
- `packages/pagepop-mcp-server`: the MCP server shape for exposing PagePop tools, resources, and prompts.

Host-specific behavior belongs under `adapters/`.

Examples:

- `adapters/openclaw`: OpenClaw-specific installation notes, event semantics, and launch-context guidance.
- `examples/local-cli`: local smoke-test examples that do not contain environment-specific defaults.

## Design Rules

- PagePop capability code lives in `pagepop-core`.
- Skill packaging code lives in `pagepop-skill`.
- MCP-specific transport and tool registration lives in `pagepop-mcp-server`.
- Host-specific instructions live in `adapters/<host>`.
- Environment-specific values are injected at build or runtime and are never committed as concrete defaults.
