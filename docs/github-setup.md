# GitHub Setup Checklist

Configure the repository before publishing production releases.

## Branch Protection

Protect `main`:

- Require pull request review before merging.
- Require status checks to pass.
- Require the `CI / public-safety` job.
- Restrict force pushes.

## Environments

Create a `production` environment:

- Add required reviewers.
- Restrict deployments to `main`.
- Store production release variables only.
- Store sensitive values as secrets.

Do not configure a public workflow that uploads non-production packages as artifacts.

## Repository Settings

Recommended settings:

- Disable actions from untrusted third-party sources unless explicitly needed.
- Require approval for workflows from external contributors.
- Keep GitHub Releases production-only.
- Use security scanning and secret scanning if available.

## Release Naming

Use deterministic tags:

```text
pagepop-skill-vYYYY.MM.DD-rN
pagepop-mcp-server-vYYYY.MM.DD-rN
```

The release tag must match the generated `skill-manifest.json`.
