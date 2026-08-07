"""Deterministic, offline gateway for tests and local demos.

Simulates the GenAI Lab gateway by applying rule-based analysis to the diff
embedded in the prompt. It returns the same JSON shapes the real agents expect,
so the entire pipeline runs with no network access and no credentials.
"""

from __future__ import annotations

import json
import re
import time

from .llm_gateway import LLMResponse

_UNTRUSTED_DIFF_OPEN = "<untrusted_diff>"
_UNTRUSTED_DIFF_CLOSE = "</untrusted_diff>"

_FILE_HEADER = re.compile(r"^diff --git a/(\S+) b/(\S+)", re.MULTILINE)

_CORE_PATTERNS: list[tuple[re.Pattern[str], str, str, str, str]] = [
    (
        re.compile(r"\bexcept\s*:"),
        "warning",
        "style",
        "Bare except clause catches all exceptions",
        "Specify the exception type.",
    ),
    (
        re.compile(r"\bprint\("),
        "info",
        "debug",
        "Debug print left in the diff",
        "Route through a logger or remove it.",
    ),
    (
        re.compile(r"\b(TODO|FIXME)\b"),
        "info",
        "cleanup",
        "Unresolved marker in the diff",
        "Resolve the marked item.",
    ),
]

_SECURITY_PATTERNS: list[tuple[re.Pattern[str], str, str, str, str, float]] = [
    (
        re.compile(r"\beval\s*\("),
        "critical",
        "code-injection",
        "eval() executes arbitrary code from untrusted input",
        "Use ast.literal_eval or a strict whitelist.",
        0.95,
    ),
    (
        re.compile(r"\bexec\s*\("),
        "critical",
        "code-injection",
        "exec() executes arbitrary code from untrusted input",
        "Avoid exec; use a safe evaluator.",
        0.95,
    ),
    (
        re.compile(r"\bos\.system\s*\("),
        "critical",
        "command-injection",
        "os.system() runs a shell command and enables injection",
        "Use subprocess with an argument list.",
        0.9,
    ),
    (
        re.compile(r"\bshell\s*=\s*True\b"),
        "critical",
        "command-injection",
        "shell=True enables shell injection",
        "Pass an argument list to subprocess.",
        0.9,
    ),
    (
        re.compile(r"\bpickle\.loads\b"),
        "critical",
        "insecure-deserialization",
        "pickle.loads on untrusted data is unsafe",
        "Use a safe serializer such as JSON.",
        0.85,
    ),
    (
        re.compile(r"\b(password|api_key|secret|token)\s*=\s*['\"][^'\"]+['\"]"),
        "error",
        "hardcoded-secret",
        "Hardcoded credential in code",
        "Move to environment variables / a secret manager.",
        0.8,
    ),
    (
        re.compile(r"\bverify\s*=\s*False\b"),
        "error",
        "tls",
        "TLS certificate verification disabled",
        "Keep certificate verification enabled.",
        0.8,
    ),
]


def _extract_diff(messages: list[dict[str, str]]) -> str:
    text = " ".join(message.get("content", "") for message in messages)
    start = text.find(_UNTRUSTED_DIFF_OPEN)
    end = text.find(_UNTRUSTED_DIFF_CLOSE)
    if start != -1 and end != -1:
        return text[start + len(_UNTRUSTED_DIFF_OPEN) : end]
    return text


def _files_from_diff(diff: str) -> list[str]:
    return [match[0] for match in _FILE_HEADER.findall(diff)]


def _detect(model: str) -> str:
    lowered = model.lower()
    if "gpt-4o" in lowered or "triage" in lowered:
        return "triage"
    if "gemini" in lowered or "summar" in lowered:
        return "summarizer"
    if "deepseek" in lowered or "security" in lowered:
        return "security"
    return "core"


def _core_findings(diff: str, files: list[str]) -> list[dict]:
    path = files[0] if files else "unknown"
    findings = []
    for pattern, severity, category, message, suggestion in _CORE_PATTERNS:
        if pattern.search(diff):
            findings.append(
                {
                    "severity": severity,
                    "category": category,
                    "file_path": path,
                    "message": message,
                    "suggestion": suggestion,
                    "confidence": 0.8,
                }
            )
    return findings


def _security_findings(diff: str, files: list[str]) -> list[dict]:
    path = files[0] if files else "unknown"
    findings = []
    for (
        pattern,
        severity,
        category,
        message,
        suggestion,
        confidence,
    ) in _SECURITY_PATTERNS:
        if pattern.search(diff):
            findings.append(
                {
                    "severity": severity,
                    "category": category,
                    "file_path": path,
                    "message": message,
                    "suggestion": suggestion,
                    "confidence": confidence,
                }
            )
    return findings


class DemoGateway:
    """Mimics ``LLMGateway.chat`` with rule-based, deterministic responses."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> LLMResponse:
        self.calls.append(model)
        diff = _extract_diff(messages)
        files = _files_from_diff(diff)
        start = time.monotonic()
        content = self._respond(_detect(model), diff, files)
        body = json.dumps(content)
        return LLMResponse(
            content=body,
            model=model,
            latency_ms=int((time.monotonic() - start) * 1000),
            tokens_in=max(1, len(diff) // 4),
            tokens_out=max(1, len(body) // 4),
        )

    def _respond(self, kind: str, diff: str, files: list[str]) -> dict:
        if kind == "triage":
            return {"core": files, "security": files}
        if kind == "summarizer":
            security_count = len(_security_findings(diff, files))
            return {
                "summary": (
                    f"Reviewed {len(files)} changed file(s). "
                    f"The security agent reported {security_count} issue(s)."
                ),
                "changes": (
                    [f"Changed {file}" for file in files]
                    if files
                    else ["No file changes detected"]
                ),
                "impact": (
                    [f"{security_count} security issue(s) to address"]
                    if security_count
                    else ["No security issues found"]
                ),
                "recommendations": [],
            }
        if kind == "security":
            return {"findings": _security_findings(diff, files)}
        return {"findings": _core_findings(diff, files)}
