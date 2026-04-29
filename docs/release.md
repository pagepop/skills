# Release Process

This repository uses a single public GitHub repository for source, development, and production releases.

The safety rule is strict:

> Anything committed, tagged, uploaded as a release asset, or stored as a workflow artifact in this public repository must be safe for external users to see.

## Skill Release

1. Ensure all changes are reviewed on a feature branch.
2. Run local checks:

   ```bash
   bash scripts/check-public-safety.sh
   python3 scripts/build-skill.py \
     --pagepop_package_version YYYY.MM.DD-rN \
     --pagepop_skill_channel prod
   ```

3. Trigger the `Release Skill` workflow from GitHub Actions.
4. Select the `production` environment.
5. After approval, the workflow builds a production package and publishes a GitHub Release.
6. Configure the PagePop backend update policy to point to the release asset URL and SHA-256 file.

The skill update check is notification-only. The skill emits update metadata, but it does not download, verify, install, or restart itself. The host application, installer, or user workflow must download the release asset, verify the SHA-256 file, install the package, and restart the skill process.

## Non-Production Builds

Non-production packages are for internal validation only.

Local non-production builds require an explicit flag:

```bash
python3 scripts/build-skill.py \
  --env-file .env.local \
  --allow-non-prod
```

Do not publish non-production packages as public GitHub Releases or public workflow artifacts.

## GitHub UI Setup

Before enabling releases, configure these settings in GitHub:

- Create a `production` environment.
- Add required reviewers to `production`.
- Restrict production deployments to `main`.
- Keep repository Actions enabled only for trusted workflows.
- Do not add non-production hostnames to committed files.

Optional variables for the production environment:

- `PAGEPOP_API_BASE_URL`
- `PAGEPOP_WEB_BASE_URL`
- `PAGEPOP_RELEASE_REPO`

Sensitive values must be stored as secrets, not variables.
