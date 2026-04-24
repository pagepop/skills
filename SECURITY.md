# Security Policy

This repository is public. Treat every committed file, branch, tag, release asset, and workflow artifact as externally visible.

Do not commit:

- Non-production API hosts or web hosts.
- Access tokens, API keys, cookies, or local login token paths.
- Internal Git remotes, private issue links, or private deployment notes.
- Generated caches such as `__pycache__`, `.pyc`, or local state files.

Environment-specific values must be provided through GitHub Environments, local ignored environment files, or the deployment platform.

Before publishing a release, run:

```bash
bash scripts/check-public-safety.sh
```
