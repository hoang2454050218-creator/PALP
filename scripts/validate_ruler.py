#!/usr/bin/env python3
"""Validate the .ruler/ source-of-truth before commit / apply.

Checks:
1. .ruler/ruler.toml exists and is valid TOML.
2. Every .ruler/*.md is non-empty.
3. Every .ruler/skills/*/SKILL.md has YAML frontmatter with `name` + `description`.
4. Skills directory names match the `name:` field in frontmatter.
5. .ruler/skills/INDEX.md references every skill that exists.
6. ruler.toml MCP servers are well-formed (have command+args OR url).

Exit codes:
- 0: all checks passed
- 1: one or more checks failed (errors printed to stderr)

Usage:
    python scripts/validate_ruler.py
    just ruler-lint
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

REPO_ROOT = Path(__file__).resolve().parent.parent
RULER_DIR = REPO_ROOT / ".ruler"
SKILLS_DIR = RULER_DIR / "skills"
INDEX_FILE = SKILLS_DIR / "INDEX.md"
TOML_FILE = RULER_DIR / "ruler.toml"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
NAME_RE = re.compile(r"^name:\s*(.+)$", re.MULTILINE)
DESCRIPTION_RE = re.compile(r"^description:\s*(.+)$", re.MULTILINE)


class ValidationError(Exception):
    """One concrete validation problem."""


def _err(message: str) -> None:
    print(f"[ruler-lint] ERROR: {message}", file=sys.stderr)


def _ok(message: str) -> None:
    print(f"[ruler-lint] OK: {message}")


def check_ruler_dir() -> None:
    if not RULER_DIR.is_dir():
        raise ValidationError(f"{RULER_DIR} does not exist")
    if not TOML_FILE.is_file():
        raise ValidationError(f"{TOML_FILE} does not exist")
    _ok(f"{RULER_DIR} present")


def check_toml() -> dict:
    with TOML_FILE.open("rb") as fh:
        try:
            data = tomllib.load(fh)
        except tomllib.TOMLDecodeError as exc:
            raise ValidationError(f"{TOML_FILE} invalid TOML: {exc}") from exc
    _ok(f"{TOML_FILE.name} valid TOML")
    return data


def check_mcp_servers(config: dict) -> None:
    servers = config.get("mcp_servers", {})
    if not isinstance(servers, dict):
        raise ValidationError("[mcp_servers] must be a table of named servers")
    for name, server in servers.items():
        if not isinstance(server, dict):
            raise ValidationError(f"mcp_servers.{name} must be a table")
        has_command = "command" in server
        has_url = "url" in server
        if not (has_command or has_url):
            raise ValidationError(
                f"mcp_servers.{name} must define either `command` (stdio) or `url` (remote)"
            )
        if has_command and not isinstance(server.get("args", []), list):
            raise ValidationError(f"mcp_servers.{name}.args must be a list")
    _ok(f"{len(servers)} MCP server(s) well-formed")


def check_rule_files() -> list[Path]:
    md_files = sorted(p for p in RULER_DIR.glob("*.md") if p.name != "README.md")
    if not md_files:
        raise ValidationError("no .ruler/*.md rule files found")
    for path in md_files:
        if path.stat().st_size == 0:
            raise ValidationError(f"{path.relative_to(REPO_ROOT)} is empty")
    _ok(f"{len(md_files)} rule file(s) present and non-empty")
    return md_files


def check_skills() -> list[str]:
    if not SKILLS_DIR.is_dir():
        return []
    skill_names: list[str] = []
    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            raise ValidationError(f"{skill_dir.relative_to(REPO_ROOT)} missing SKILL.md")
        content = skill_md.read_text(encoding="utf-8")
        if not content.strip():
            raise ValidationError(f"{skill_md.relative_to(REPO_ROOT)} is empty")
        match = FRONTMATTER_RE.match(content)
        if not match:
            raise ValidationError(
                f"{skill_md.relative_to(REPO_ROOT)} missing YAML frontmatter "
                "(expected `---\\nname: ...\\ndescription: ...\\n---`)"
            )
        frontmatter = match.group(1)
        name_match = NAME_RE.search(frontmatter)
        desc_match = DESCRIPTION_RE.search(frontmatter)
        if not name_match:
            raise ValidationError(
                f"{skill_md.relative_to(REPO_ROOT)} frontmatter missing `name:`"
            )
        if not desc_match:
            raise ValidationError(
                f"{skill_md.relative_to(REPO_ROOT)} frontmatter missing `description:`"
            )
        name = name_match.group(1).strip()
        if name != skill_dir.name:
            raise ValidationError(
                f"{skill_md.relative_to(REPO_ROOT)} frontmatter name='{name}' "
                f"does not match directory '{skill_dir.name}'"
            )
        skill_names.append(name)
    _ok(f"{len(skill_names)} skill(s) valid")
    return skill_names


def check_index(skill_names: list[str]) -> None:
    if not skill_names:
        return
    if not INDEX_FILE.is_file():
        raise ValidationError(f"{INDEX_FILE.relative_to(REPO_ROOT)} missing")
    index_content = INDEX_FILE.read_text(encoding="utf-8")
    missing = [name for name in skill_names if f"**{name}**" not in index_content]
    if missing:
        raise ValidationError(
            f"{INDEX_FILE.relative_to(REPO_ROOT)} missing entries for: {', '.join(missing)}"
        )
    _ok(f"INDEX.md references all {len(skill_names)} skill(s)")


def main() -> int:
    try:
        check_ruler_dir()
        config = check_toml()
        check_mcp_servers(config)
        check_rule_files()
        skill_names = check_skills()
        check_index(skill_names)
    except ValidationError as exc:
        _err(str(exc))
        return 1
    print("[ruler-lint] All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
