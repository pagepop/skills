# Dev Builds

This repository is public, so dev and test environment values must stay outside committed source, public GitHub Actions logs, public artifacts, and public releases.

## Recommended Model

- Public source contains only production-safe defaults and empty placeholders.
- Normal users can clone the repository and install the skill without seeing test environment values.
- Developers inject test environment values locally through an ignored env file or shell environment.
- Dev packages may be generated locally, but they must not be uploaded to public GitHub Actions artifacts or public GitHub Releases.

Do not treat a hidden test hostname as an authorization boundary. Test services must still enforce authentication and allowlists.

## Local Dev Environment

Create an ignored env file at the repository root:

```bash
cp packages/pagepop-skill/.env.example .env.dev.local
```

Set local-only values in `.env.dev.local`:

```bash
PAGEPOP_API_BASE_URL=<internal-dev-api-base-url>
PAGEPOP_WEB_BASE_URL=<internal-dev-web-base-url>
PAGEPOP_SKILL_STATE_DIR=.pagepop-dev
PAGEPOP_PACKAGE_VERSION=2026.04.27-r1
PAGEPOP_SKILL_CHANNEL=dev
PAGEPOP_RELEASE_TAG=pagepop-skill-dev-v2026.04.27-r1
```

The `.gitignore` rules ignore `.env.dev.local`; do not force-add it.

## Build A Dev Package Locally

```bash
python3 scripts/build-skill.py \
  --env-file .env.dev.local \
  --allow-non-prod
```

The package is written under `dist/`:

```text
dist/pagepop-skill-dev-2026.04.27-r1.zip
dist/pagepop-skill-dev-2026.04.27-r1.zip.sha256
dist/pagepop-skill-dev-2026.04.27-r1/
```

The package manifest records the `dev` channel, version, release tag, and build SHA. The API base URL is runtime configuration, not committed source configuration.

## Run Against The Test Environment

When testing directly from the built package, load the local env file before invoking the skill:

```bash
set -a
source .env.dev.local
set +a

python3 dist/pagepop-skill-dev-2026.04.27-r1/scripts/pagepop_skill.py status
```

Host integrations should pass the same environment variables to the skill process. Keep dev state separate from production state by setting `PAGEPOP_SKILL_STATE_DIR`.

## If Automation Is Required

Use a private or internal automation repository instead of this public repository:

1. The private workflow accepts a source ref or commit SHA from `pagepop/skills`.
2. It checks out the public source at that ref.
3. It injects test environment values from private environment secrets.
4. It builds the dev package with `--allow-non-prod`.
5. It stores the package as a private/internal artifact or release.

Public workflows in this repository should remain limited to tests, public-safety checks, and production-safe builds.
