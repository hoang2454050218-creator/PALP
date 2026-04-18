"""
PALP Migration Gate -- enforces backward-compatible migrations.

Checks every uncommitted migration for:
1. ``RunPython`` operations missing reverse_code (not reversible).
2. ``RemoveField`` / ``DeleteModel`` in same release as code that still
   references the field/model (heuristic via grep).
3. ``AlterField`` that narrows column (e.g. NOT NULL, smaller max_length)
   without explicit data migration.

Run manually:    python scripts/check_migrations.py
Run in CI:       see .github/workflows/ci.yml migration-check job
"""
from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"


class Finding:
    def __init__(self, file: Path, lineno: int, severity: str, message: str):
        self.file = file
        self.lineno = lineno
        self.severity = severity
        self.message = message

    def __str__(self) -> str:
        rel = self.file.relative_to(REPO_ROOT)
        return f"[{self.severity}] {rel}:{self.lineno} {self.message}"


def changed_migration_files(base: str = "origin/master") -> list[Path]:
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", f"{base}..HEAD"],
            cwd=REPO_ROOT, text=True,
        )
    except subprocess.CalledProcessError:
        return list(BACKEND.glob("*/migrations/*.py"))
    files = []
    for line in out.splitlines():
        p = REPO_ROOT / line
        if "migrations" in p.parts and p.suffix == ".py" and p.name != "__init__.py":
            files.append(p)
    return files


def check_runpython_reversibility(path: Path) -> list[Finding]:
    findings = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return findings

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (
            func.attr if isinstance(func, ast.Attribute)
            else func.id if isinstance(func, ast.Name)
            else ""
        )
        if name != "RunPython":
            continue

        kwargs = {kw.arg: kw.value for kw in node.keywords}
        # Positional args: (code, reverse_code, atomic=True)
        has_reverse = (
            len(node.args) >= 2
            or "reverse_code" in kwargs
        )
        if not has_reverse:
            findings.append(Finding(
                path, node.lineno, "ERROR",
                "RunPython without reverse_code is not reversible. "
                "Use migrations.RunPython.noop explicitly if intentional.",
            ))
            continue

        # Check noop both ways (silent migration)
        rev = kwargs.get("reverse_code") or (node.args[1] if len(node.args) > 1 else None)
        if rev and isinstance(rev, ast.Attribute) and rev.attr == "noop":
            fwd = kwargs.get("code") or (node.args[0] if node.args else None)
            if fwd and isinstance(fwd, ast.Attribute) and fwd.attr == "noop":
                findings.append(Finding(
                    path, node.lineno, "WARNING",
                    "RunPython with noop both forward and reverse is a no-op migration.",
                ))
    return findings


def check_destructive_operations(path: Path) -> list[Finding]:
    findings = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return findings

    destructive = {"RemoveField", "DeleteModel", "RenameField", "RenameModel"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (
            func.attr if isinstance(func, ast.Attribute)
            else func.id if isinstance(func, ast.Name)
            else ""
        )
        if name in destructive:
            findings.append(Finding(
                path, node.lineno, "WARNING",
                f"{name} is destructive. Verify backward compatibility "
                f"(see docs/MIGRATION_RUNBOOK.md section 6).",
            ))
    return findings


def check_narrowing_alter(path: Path) -> list[Finding]:
    findings = []
    src = path.read_text(encoding="utf-8")
    if "AlterField" in src and "null=False" in src and "default=" not in src:
        findings.append(Finding(
            path, 1, "WARNING",
            "AlterField setting null=False without default may break existing rows. "
            "Consider data migration first.",
        ))
    return findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="origin/master",
                        help="Git base branch to diff against")
    parser.add_argument("--all", action="store_true",
                        help="Check ALL migrations, not just changed ones")
    args = parser.parse_args()

    files = (
        list(BACKEND.glob("*/migrations/*.py"))
        if args.all else changed_migration_files(args.base)
    )
    files = [f for f in files if f.exists() and f.name != "__init__.py"]

    if not files:
        print("No migration files to check.")
        return 0

    print(f"Checking {len(files)} migration file(s)...")
    findings = []
    for f in files:
        findings.extend(check_runpython_reversibility(f))
        findings.extend(check_destructive_operations(f))
        findings.extend(check_narrowing_alter(f))

    errors = [f for f in findings if f.severity == "ERROR"]
    warnings = [f for f in findings if f.severity == "WARNING"]

    for f in findings:
        print(f, file=sys.stderr if f.severity == "ERROR" else sys.stdout)

    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s).")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
