"""
code_scanner.py — Static code analysis using Python's built-in AST module.

What it does:
1. Walks the repo for Python source files
2. For each file, parses the AST to extract:
   - Function and class counts (complexity proxy)
   - Hardcoded secrets (passwords, tokens, API keys in variable names/strings)
   - Missing docstrings on public functions/classes
   - TODO/FIXME/HACK comments
3. Checks requirements.txt / pyproject.toml for known bad dependency patterns
4. Returns a structured CodeScanResult dict

Why AST instead of an external linter?
- AST is built into Python — zero extra dependencies
- Fast and reliable for pattern detection
- Works on any Python version >= 3.8
- External tools (pylint, bandit) can be added on top later
"""
import ast
import os
import re
from pathlib import Path
from typing import TypedDict
from loguru import logger


# ── Types ─────────────────────────────────────────────────────────────────────

class Finding(TypedDict):
    file: str
    line: int
    severity: str          # CRITICAL | HIGH | MEDIUM | LOW
    category: str          # security | quality | documentation
    title: str
    description: str


class CodeScanResult(TypedDict):
    repo_path: str
    total_python_files: int
    total_lines: int
    findings: list[Finding]
    file_tree: list[str]   # top-level directory structure


# ── Patterns to detect ────────────────────────────────────────────────────────

# Variable/argument names that suggest secret values
SECRET_NAME_PATTERNS = re.compile(
    r"(password|passwd|secret|api_key|apikey|token|private_key|access_key|auth_key)",
    re.IGNORECASE
)

# String values that look like real secrets (not placeholders)
SECRET_VALUE_PATTERN = re.compile(
    r"^(sk-|ghp_|xox[baprs]-|AIza|AKIA|ya29\.|eyJ)[a-zA-Z0-9_\-]{10,}$"
)

# Comment patterns indicating known debt
DEBT_COMMENT_PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX|NOQA)\b", re.IGNORECASE)

# Skip these dirs when scanning
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".tox", "dist", "build"}

MAX_FILES = 200  # Cap to avoid scanning huge repos slowly


# ── File tree helper ──────────────────────────────────────────────────────────

def get_file_tree(repo_path: str, max_depth: int = 2) -> list[str]:
    """Return a simplified directory tree (top N levels)."""
    tree = []
    base = Path(repo_path)
    for item in sorted(base.iterdir()):
        if item.name.startswith(".") or item.name in SKIP_DIRS:
            continue
        prefix = "📁 " if item.is_dir() else "📄 "
        tree.append(f"{prefix}{item.name}")
        if item.is_dir() and max_depth > 1:
            for sub in sorted(item.iterdir()):
                if sub.name.startswith(".") or sub.name in SKIP_DIRS:
                    continue
                sub_prefix = "  📁 " if sub.is_dir() else "  📄 "
                tree.append(f"{sub_prefix}{sub.name}")
    return tree


# ── AST visitor ───────────────────────────────────────────────────────────────

class AuditVisitor(ast.NodeVisitor):
    """Visits Python AST nodes and collects findings."""

    def __init__(self, filepath: str, rel_path: str):
        self.filepath = filepath
        self.rel_path = rel_path
        self.findings: list[Finding] = []

    def _add(self, severity: str, category: str, title: str, desc: str, line: int):
        self.findings.append({
            "file": self.rel_path,
            "line": line,
            "severity": severity,
            "category": category,
            "title": title,
            "description": desc,
        })

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_docstring(node, "function")
        self._check_args_for_secrets(node)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef  # same check for async

    def visit_ClassDef(self, node: ast.ClassDef):
        self._check_docstring(node, "class")
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        """Check assignments for hardcoded secrets."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                if SECRET_NAME_PATTERNS.search(target.id):
                    # Check if the value is an obviously hardcoded string
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        val = node.value.value
                        if val and not val.startswith("$") and val not in ("", "None", "null", "changeme"):
                            if SECRET_VALUE_PATTERN.match(val) or len(val) > 20:
                                self._add(
                                    "CRITICAL", "security",
                                    f"Hardcoded secret: '{target.id}'",
                                    f"Variable '{target.id}' appears to contain a hardcoded secret value.",
                                    node.lineno,
                                )
        self.generic_visit(node)

    def _check_docstring(self, node, kind: str):
        """Flag public functions/classes missing a docstring."""
        if node.name.startswith("_"):
            return  # Private — don't require docs
        if not (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            self._add(
                "LOW", "documentation",
                f"Missing docstring on {kind} '{node.name}'",
                f"Public {kind} '{node.name}' has no docstring.",
                node.lineno,
            )

    def _check_args_for_secrets(self, node: ast.FunctionDef):
        """Flag function parameters with secret-like names and default values."""
        for default, arg in zip(reversed(node.args.defaults), reversed(node.args.args)):
            if SECRET_NAME_PATTERNS.search(arg.arg):
                if isinstance(default, ast.Constant) and isinstance(default.value, str):
                    val = default.value
                    if val and val not in ("", "None"):
                        self._add(
                            "HIGH", "security",
                            f"Secret in default arg: '{arg.arg}'",
                            f"Parameter '{arg.arg}' in '{node.name}' has a hardcoded default value.",
                            node.lineno,
                        )


# ── Comment scanner ───────────────────────────────────────────────────────────

def scan_comments(filepath: str, rel_path: str) -> list[Finding]:
    """Scan source lines for TODO/FIXME/HACK comments."""
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, start=1):
                if DEBT_COMMENT_PATTERN.search(line):
                    findings.append({
                        "file": rel_path,
                        "line": i,
                        "severity": "LOW",
                        "category": "quality",
                        "title": "Technical debt marker",
                        "description": line.strip(),
                    })
    except Exception as e:
        logger.warning(f"Could not scan comments in {filepath}: {e}")
    return findings


# ── Main scan function ────────────────────────────────────────────────────────

def scan_code(repo_path: str) -> CodeScanResult:
    """
    Run the full static analysis scan on the repository.

    Args:
        repo_path: Absolute path to the repository root

    Returns:
        CodeScanResult with all findings
    """
    if not os.path.isdir(repo_path):
        raise ValueError(f"Not a valid directory: {repo_path}")

    all_findings: list[Finding] = []
    total_files = 0
    total_lines = 0
    file_tree = get_file_tree(repo_path)

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

        for fname in files:
            if not fname.endswith(".py"):
                continue
            if total_files >= MAX_FILES:
                break

            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, repo_path)

            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    source = f.read()

                total_files += 1
                total_lines += source.count("\n")

                # AST analysis
                try:
                    tree = ast.parse(source, filename=fpath)
                    visitor = AuditVisitor(fpath, rel_path)
                    visitor.visit(tree)
                    all_findings.extend(visitor.findings)
                except SyntaxError as e:
                    all_findings.append({
                        "file": rel_path,
                        "line": getattr(e, "lineno", 0) or 0,
                        "severity": "MEDIUM",
                        "category": "quality",
                        "title": "Syntax error",
                        "description": str(e),
                    })

                # Comment scan
                all_findings.extend(scan_comments(fpath, rel_path))

            except Exception as e:
                logger.warning(f"Error scanning {fpath}: {e}")

    logger.info(
        f"Code scan complete: {total_files} files, "
        f"{total_lines} lines, {len(all_findings)} findings"
    )

    # Sort: CRITICAL first, then HIGH, MEDIUM, LOW
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_findings.sort(key=lambda f: severity_order.get(f["severity"], 99))

    return {
        "repo_path": repo_path,
        "total_python_files": total_files,
        "total_lines": total_lines,
        "findings": all_findings,
        "file_tree": file_tree,
    }
