"""
report_generator.py — Produce the final structured audit report.

Takes raw outputs from:
  - doc_analyzer  → docs_summary (str)
  - code_scanner  → CodeScanResult (dict)
  - crew (optional) → ai_report_json (str from CrewAI)

And writes:
  1. A JSON file: {audit_output_dir}/{job_id}/report.json
  2. A Markdown file: {audit_output_dir}/{job_id}/report.md

The JSON structure matches the AuditReport Pydantic model in app/models/audit.py.
The Markdown is human-readable — suitable for sending to a client.
"""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from loguru import logger

from app.audit_agent.code_scanner import CodeScanResult


# ── JSON extraction ────────────────────────────────────────────────────────────

def extract_json_from_text(text: str) -> Optional[dict]:
    """
    Try to extract a JSON object from a larger text string.
    CrewAI agents sometimes wrap their JSON output in markdown code blocks.
    """
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to extract from ```json ... ``` code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find the first {...} in the text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


# ── Score derivation ───────────────────────────────────────────────────────────

def _derive_code_score(scan: CodeScanResult) -> int:
    """
    Derive a code quality score (1-10) from scan findings.
    Start at 10, subtract points for each finding by severity.
    """
    penalty = {
        "CRITICAL": 3,
        "HIGH":     2,
        "MEDIUM":   1,
        "LOW":      0,  # low findings don't penalize score directly
    }
    score = 10
    for finding in scan["findings"]:
        score -= penalty.get(finding["severity"], 0)
    return max(1, min(10, score))


def _findings_to_report_items(scan: CodeScanResult) -> list[dict]:
    """Convert CodeScanResult findings to the report JSON schema format."""
    items = []
    for i, f in enumerate(scan["findings"][:20], start=1):  # cap at 20
        items.append({
            "id": f"F{i:03d}",
            "severity": f["severity"],
            "category": f["category"],
            "title": f["title"],
            "description": f"{f['description']} (File: {f['file']}, Line: {f['line']})",
            "remediation": _suggest_remediation(f),
        })
    return items


def _suggest_remediation(finding: dict) -> str:
    """Generate a generic remediation suggestion based on category and title."""
    title = finding["title"].lower()
    if "hardcoded secret" in title or "secret in default" in title:
        return "Move to environment variables or secrets manager. Never commit credentials to git."
    if "missing docstring" in title:
        return "Add a docstring explaining purpose, parameters, and return values."
    if "technical debt" in title:
        return "Address the TODO/FIXME before the next release. Create a tracking issue."
    if "syntax error" in title:
        return "Fix the syntax error. Run 'python -m py_compile <file>' to verify."
    if "dependency" in title:
        return "Run 'pip install --upgrade <package>' and review the changelog for breaking changes."
    return "Review and address according to project coding standards."


# ── Main report builder ────────────────────────────────────────────────────────

async def generate_report(
    job_id: str,
    repo_path: str,
    output_dir: str,
    scan_result: CodeScanResult,
    docs_summary: str,
    ai_report_raw: Optional[str] = None,  # Raw crew output (may contain JSON)
    doc_score: int = 7,
    runtime_analysis: Optional[dict] = None,
) -> dict:
    """
    Build and write the final audit report.

    Args:
        job_id:         Unique job identifier (used as output subdirectory)
        repo_path:      Path that was scanned
        output_dir:     Base directory for output files (from settings.audit_output_dir)
        scan_result:    Output from code_scanner.scan_code()
        docs_summary:   Output from doc_analyzer.analyze_docs()
        ai_report_raw:  Optional raw output from CrewAI report_agent
        doc_score:      Documentation quality score (1-10)

    Returns:
        The report as a Python dict (also written to disk as JSON + Markdown)
    """
    # ... (derive scores and findings) ...
    code_score = _derive_code_score(scan_result)

    # Try to parse AI report JSON to get enhanced findings
    ai_findings = []
    if ai_report_raw:
        parsed = extract_json_from_text(ai_report_raw)
        if parsed and "findings" in parsed:
            ai_findings = parsed.get("findings", [])
            # Use AI scores if available
            if "documentation_score" in parsed:
                doc_score = parsed["documentation_score"]
            if "code_quality_score" in parsed:
                code_score = parsed["code_quality_score"]
            logger.info(f"AI report parsed: {len(ai_findings)} AI findings")

    # Build static findings from scanner
    static_findings = _findings_to_report_items(scan_result)

    # Combine findings (AI findings added to static ones)
    all_findings = static_findings + ai_findings
    if ai_findings:
        logger.info(f"Merged {len(ai_findings)} AI findings with {len(static_findings)} static findings")

    # Build executive summary
    critical_count = sum(1 for f in all_findings if f.get("severity") == "CRITICAL")
    high_count = sum(1 for f in all_findings if f.get("severity") == "HIGH")
    exec_summary = (
        f"The repository at '{os.path.basename(repo_path)}' was audited across "
        f"{scan_result['total_python_files']} Python files "
        f"({scan_result['total_lines']:,} lines). "
        f"Found {len(all_findings)} total findings including "
        f"{critical_count} CRITICAL and {high_count} HIGH severity issues. "
        f"Overall health score: {(code_score + doc_score) // 2}/10."
    )

    report = {
        "job_id": job_id,
        "repo_path": repo_path,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_health_score": (code_score + doc_score) // 2,
        "executive_summary": exec_summary,
        "documentation_score": doc_score,
        "code_quality_score": code_score,
        "total_files_scanned": scan_result["total_python_files"],
        "total_lines_scanned": scan_result["total_lines"],
        "file_tree": scan_result["file_tree"],
        "findings": all_findings,
        "docs_summary": docs_summary[:3000],  # Truncate for JSON size
        "runtime_analysis": runtime_analysis,
    }

    # ── Write output files ─────────────────────────────────────────────────────
    
    # 1. Local Write
    job_dir = os.path.join(output_dir, job_id)
    os.makedirs(job_dir, exist_ok=True)

    report_json_str = json.dumps(report, indent=2)
    report_md_str = _to_markdown(report)

    # Write JSON locally
    json_path = os.path.join(job_dir, "report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(report_json_str)
    
    # Write Markdown locally
    md_path = os.path.join(job_dir, "report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_md_str)

    logger.info(f"Local reports written to: {job_dir}")

    # 2. MinIO Upload
    from app.config import settings
    if settings.use_minio:
        from app.utils.storage import storage_client
        try:
            # Upload JSON
            json_key = f"{job_id}/report.json"
            await storage_client.upload_bytes(
                json_key, 
                report_json_str.encode("utf-8"), 
                "application/json"
            )
            report["minio_json_url"] = await storage_client.get_presigned_url(json_key)

            # Upload Markdown
            md_key = f"{job_id}/report.md"
            await storage_client.upload_bytes(
                md_key, 
                report_md_str.encode("utf-8"), 
                "text/markdown"
            )
            report["minio_md_url"] = await storage_client.get_presigned_url(md_key)
            
            logger.info(f"Reports uploaded to MinIO bucket '{settings.minio_bucket}'")
        except Exception as e:
            logger.error(f"MinIO upload failed: {e}")

    return report


def _to_markdown(report: dict) -> str:
    """Convert report dict to a human-readable Markdown document."""
    lines = [
        f"# Software Audit Report",
        f"",
        f"**Repository:** `{report['repo_path']}`  ",
        f"**Generated:** {report['generated_at']}  ",
        f"**Overall Health Score:** {report['overall_health_score']}/10  ",
        f"",
        f"## Executive Summary",
        f"",
        f"{report['executive_summary']}",
        f"",
        f"## Scores",
        f"",
        f"| Area | Score |",
        f"|------|-------|",
        f"| Code Quality | {report['code_quality_score']}/10 |",
        f"| Documentation | {report['documentation_score']}/10 |",
        f"| **Overall** | **{report['overall_health_score']}/10** |",
        f"",
        f"## Findings ({len(report['findings'])} total)",
        f"",
    ]

    severity_emoji = {
        "CRITICAL": "🔴",
        "HIGH":     "🟠",
        "MEDIUM":   "🟡",
        "LOW":      "🟢",
    }

    for finding in report["findings"]:
        emoji = severity_emoji.get(finding.get("severity", "LOW"), "⚪")
        lines += [
            f"### {emoji} [{finding.get('severity', '?')}] {finding.get('title', 'Unknown')}",
            f"",
            f"**Category:** {finding.get('category', 'N/A')}  ",
            f"**ID:** `{finding.get('id', 'N/A')}`  ",
            f"",
            f"{finding.get('description', '')}",
            f"",
            f"**Remediation:** {finding.get('remediation', '')}",
            f"",
            f"---",
            f"",
        ]

    # Append runtime analysis if present
    if report.get("runtime_analysis"):
        ra = report["runtime_analysis"]
        status = "✅ SUCCESS" if ra.get("success") else "❌ FAILED"
        lines += [
            f"## Runtime Analysis",
            f"",
            f"**Status:** {status}  ",
            f"**Entry Point:** `{ra.get('command', 'N/A')}`  ",
            f"**Duration:** {ra.get('duration_seconds', 0):.1f} seconds  ",
            f"",
            f"### Logs",
            f"```text",
            f"{ra.get('stdout', '')}",
            f"{ra.get('stderr', '')}",
            f"```",
            f"",
        ]

    # Append docs summary
    lines += [
        f"## Documentation Analysis",
        f"",
        f"{report.get('docs_summary', 'N/A')}",
        f"",
        f"## File Structure",
        f"",
    ]
    lines.extend(report.get("file_tree", []))

    return "\n".join(lines)
