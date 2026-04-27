# PagePop Skills

Official skills, manifests, and MCP integrations for connecting to PagePop.

This repository is public. Do not commit non-production environment values, private deployment details, tokens, or generated runtime state.

## Repository Layout

- `packages/pagepop-core`: shared PagePop client and integration logic.
- `packages/pagepop-skill`: generic installable PagePop skill package.
- `packages/pagepop-mcp-server`: MCP server for PagePop tools, resources, and prompts.
- `adapters/openclaw`: OpenClaw-specific integration notes.
- `docs`: architecture, environment isolation, and release documentation.
- `scripts`: build, release, and public-safety checks.

## Documentation

- [Architecture](docs/architecture.md)
- [Environment Isolation](docs/environments.md)
- [Dev Builds](docs/dev-builds.md)
- [Release Process](docs/release.md)
- [GitHub Setup](docs/github-setup.md)

## Local Build

```bash
python3 scripts/build-skill.py \
  --pagepop_package_version YYYY.MM.DD-rN \
  --pagepop_skill_channel prod
```

Generated packages are written to `dist/` and ignored by git.

## Environment Safety

Environment-specific values are injected at build or runtime. Before publishing any release, run:

```bash
bash scripts/check-public-safety.sh
```
