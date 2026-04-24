# Environment Isolation

This repository is public. Environment isolation must not rely on hiding committed files.

## Source Defaults

Committed source may include:

- Production-safe defaults.
- Empty placeholders.
- Template variables such as `${PAGEPOP_API_BASE_URL}`.

Committed source must not include:

- Non-production hostnames.
- Internal GitLab, VPN, jump host, or deployment URLs.
- Local token paths.
- Access tokens, API keys, cookies, or service secrets.

## Runtime Configuration

Use these configuration layers:

- Local development: ignored `.env.local` or shell environment variables.
- GitHub CI: GitHub Environment variables and secrets.
- Release builds: values injected by the release workflow.
- Backend policy: PagePop backend controls recommended and required package updates.

## GitHub Environments

Use separate GitHub Environments for production and non-production workflows.

Recommended variables:

- `PAGEPOP_API_BASE_URL`
- `PAGEPOP_WEB_BASE_URL`
- `PAGEPOP_SKILL_CHANNEL`
- `PAGEPOP_RELEASE_REPO`

Recommended secrets:

- Signing keys.
- Release tokens.
- Any service credentials.

Do not print environment values in workflow logs. If a value must be logged for debugging, mask it first or log only a derived label.

## Release Boundary

Production releases are the only assets intended for external users.

Non-production packages may be built locally or in protected workflows, but they must not be published as public GitHub Releases or public workflow artifacts.

Before a release:

1. Build from templates.
2. Run tests.
3. Run `bash scripts/check-public-safety.sh`.
4. Publish only the production package.
