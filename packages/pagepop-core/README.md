# pagepop-core

Shared PagePop integration logic.

This package should contain reusable code for:

- Configuration loading.
- PagePop HTTP clients.
- Authorization helpers.
- Streaming and reconnect handling.
- Artifact extraction and delivery helpers.
- Skill update checks.

It must not contain host-specific UI copy or environment-specific concrete defaults.

## Planned Modules

- `config`: environment and runtime configuration loading.
- `http`: PagePop HTTP transport helpers.
- `auth`: authorization flows and persisted credentials.
- `sse`: streaming and reconnect handling.
- `artifacts`: artifact summary extraction.
- `updates`: package update policy checks.
