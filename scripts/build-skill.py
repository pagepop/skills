#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "packages" / "pagepop-skill"
DIST_DIR = ROOT / "dist"
MANIFEST_TEMPLATE = PACKAGE_DIR / "skill-manifest.template.json"
VERSION_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}-r\d+$")
ALLOWED_PAGEPOP_HOSTS = {"pagepop.cn", "www.pagepop.cn", "pc-api.pagepop.cn"}
PAGEPOP_HOST_RE = re.compile(r"\b(?:[a-z0-9-]+\.)*pagepop\.cn\b", re.IGNORECASE)


def read_env_file(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def git_short_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def resolve_value(name: str, args: argparse.Namespace, env_file_values: dict[str, str], default: str = "") -> str:
    arg_value = getattr(args, name.lower(), "")
    if arg_value:
        return arg_value
    return os.getenv(name, "") or env_file_values.get(name, "") or default


def render_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("${" + key + "}", value)
    unresolved = sorted(set(re.findall(r"\$\{[A-Z0-9_]+\}", rendered)))
    if unresolved:
        raise SystemExit(f"unresolved manifest variables: {', '.join(unresolved)}")
    return rendered


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_public_safe(path: pathlib.Path) -> None:
    forbidden = [
        ("internal Git service hostname", re.compile(r"gitlab\.[a-z0-9.-]+", re.IGNORECASE)),
        ("local token path", re.compile(r"/tmp/[a-z0-9._-]*token", re.IGNORECASE)),
    ]
    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix in {".zip", ".gz"}:
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for host in PAGEPOP_HOST_RE.findall(text):
            if host.lower() not in ALLOWED_PAGEPOP_HOSTS:
                raise SystemExit(f"public safety check failed in build output: non-allowlisted PagePop hostname in {file_path}")
        for label, pattern in forbidden:
            if pattern.search(text):
                raise SystemExit(f"public safety check failed in build output: {label} in {file_path}")


def build(args: argparse.Namespace) -> pathlib.Path:
    env_file_values = read_env_file(pathlib.Path(args.env_file).expanduser()) if args.env_file else {}
    package_version = resolve_value("PAGEPOP_PACKAGE_VERSION", args, env_file_values)
    if not package_version:
        raise SystemExit("PAGEPOP_PACKAGE_VERSION is required")
    if not VERSION_RE.match(package_version):
        raise SystemExit("PAGEPOP_PACKAGE_VERSION must match YYYY.MM.DD-rN")

    channel = resolve_value("PAGEPOP_SKILL_CHANNEL", args, env_file_values, "prod")
    if channel != "prod" and not args.allow_non_prod:
        raise SystemExit("non-prod package builds require --allow-non-prod and must not be publicly released")

    skill_id = resolve_value("PAGEPOP_SKILL_ID", args, env_file_values, "pagepop-skill")
    release_repo = resolve_value("PAGEPOP_RELEASE_REPO", args, env_file_values, "pagepop/skills")
    release_tag = resolve_value("PAGEPOP_RELEASE_TAG", args, env_file_values, f"{skill_id}-v{package_version}")
    build_sha = resolve_value("PAGEPOP_BUILD_SHA", args, env_file_values, git_short_sha())
    published_at = resolve_value(
        "PAGEPOP_PUBLISHED_AT",
        args,
        env_file_values,
        dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    )

    build_dir = DIST_DIR / f"{skill_id}-{channel}-{package_version}"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    for item in PACKAGE_DIR.iterdir():
        if item.name in {".env.example", "skill-manifest.template.json", "tests"}:
            continue
        target = build_dir / item.name
        if item.is_dir():
            shutil.copytree(item, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
        else:
            shutil.copy2(item, target)

    manifest_values = {
        "PAGEPOP_SKILL_ID": skill_id,
        "PAGEPOP_PACKAGE_VERSION": package_version,
        "PAGEPOP_SKILL_CHANNEL": channel,
        "PAGEPOP_BUILD_SHA": build_sha,
        "PAGEPOP_RELEASE_REPO": release_repo,
        "PAGEPOP_RELEASE_TAG": release_tag,
        "PAGEPOP_PUBLISHED_AT": published_at,
    }
    manifest_text = render_template(MANIFEST_TEMPLATE.read_text(encoding="utf-8"), manifest_values)
    json.loads(manifest_text)
    (build_dir / "skill-manifest.json").write_text(manifest_text + "\n", encoding="utf-8")

    ensure_public_safe(build_dir)

    zip_path = DIST_DIR / f"{skill_id}-{channel}-{package_version}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(build_dir.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(build_dir))

    sha_path = zip_path.with_suffix(zip_path.suffix + ".sha256")
    sha_path.write_text(f"{sha256_file(zip_path)}  {zip_path.name}\n", encoding="utf-8")

    print(json.dumps({"package": str(zip_path), "sha256": str(sha_path), "build_dir": str(build_dir)}, indent=2))
    return zip_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a PagePop skill package from templates")
    parser.add_argument("--env-file", default="", help="Optional env file with build variables")
    parser.add_argument("--pagepop_package_version", default="", help="Package version, for example 2026.04.24-r1")
    parser.add_argument("--pagepop_skill_channel", default="", help="Package channel, defaults to prod")
    parser.add_argument("--pagepop_skill_id", default="", help="Skill id")
    parser.add_argument("--pagepop_release_repo", default="", help="GitHub owner/repo")
    parser.add_argument("--pagepop_release_tag", default="", help="Release tag")
    parser.add_argument("--pagepop_build_sha", default="", help="Build sha")
    parser.add_argument("--pagepop_published_at", default="", help="Published timestamp")
    parser.add_argument("--allow-non-prod", action="store_true", help="Allow non-prod local builds")
    return parser.parse_args(argv)


if __name__ == "__main__":
    build(parse_args(sys.argv[1:]))
