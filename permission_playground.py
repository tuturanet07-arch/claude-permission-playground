#!/usr/bin/env python3
"""Explain which Claude Code permission rule matches a proposed tool call.

This is an educational approximation, not an implementation of Claude Code's
permission engine. It never runs the proposed command.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def _tool_match(pattern: str, tool: str) -> bool:
    if "(" in pattern and pattern.endswith(")"):
        name = pattern.split("(", 1)[0]
        return name == tool
    if "*" in pattern:
        return fnmatch.fnmatchcase(tool, pattern)
    return pattern == tool


def _input_spec(pattern: str) -> str | None:
    if "(" not in pattern or not pattern.endswith(")"):
        return None
    return pattern.split("(", 1)[1][:-1]


def _bash_match(spec: str, command: str) -> bool:
    """Approximate Claude Code's documented whole-command wildcard matching."""
    spec = spec.strip()
    if spec.endswith(":*"):
        spec = spec[:-2] + " *"
    if spec == "*":
        return True
    if "*" not in spec:
        return command.strip() == spec
    # A trailing " *" also covers the bare prefix (for example, "ls *"
    # matches both "ls" and "ls -la"). Other wildcard placements use glob
    # matching, so multiple asterisks work as expected.
    if spec.endswith(" *") and spec.count("*") == 1 and command.strip() == spec[:-2]:
        return True
    return fnmatch.fnmatchcase(command, spec)


def _path_match(spec: str, target: str) -> bool:
    # Claude patterns are glob-like; normalize separators for cross-platform demos.
    spec = spec.replace("\\", "/")
    target = target.replace("\\", "/")
    return fnmatch.fnmatchcase(target, spec)


def _webfetch_match(spec: str, url: str) -> bool:
    """Match the documented WebFetch domain specifier subset."""
    if not spec.startswith("domain:"):
        return False
    pattern = spec[len("domain:"):].strip().lower().rstrip(".")
    hostname = (urlsplit(url).hostname or "").lower().rstrip(".")
    if not pattern or not hostname:
        return False
    # A leading *. deliberately excludes the apex domain; bare * covers all.
    if pattern == "*":
        return True
    if pattern.startswith("*."):
        suffix = pattern[1:]
        return hostname.endswith(suffix) and hostname != pattern[2:]
    pattern_labels = pattern.split(".")
    hostname_labels = hostname.split(".")
    return len(pattern_labels) == len(hostname_labels) and all(
        fnmatch.fnmatchcase(host_label, pattern_label)
        for pattern_label, host_label in zip(pattern_labels, hostname_labels)
    )


def matches(rule: str, tool: str, tool_input: dict[str, Any]) -> tuple[bool, str]:
    """Return match and explanation for the supported rule subset."""
    rule = rule.strip()
    spec = _input_spec(rule)
    name = rule.split("(", 1)[0] if spec is not None else rule
    if not _tool_match(name, tool):
        return False, "tool name differs"
    if spec is None:
        return True, "tool name matches (no input restriction)"
    if tool == "Bash":
        command = str(tool_input.get("command", ""))
        result = _bash_match(spec, command)
        return result, "Bash command matches" if result else "Bash command differs"
    if tool == "WebFetch":
        value = str(tool_input.get("url", ""))
        result = _webfetch_match(spec, value)
        return result, "WebFetch hostname matches" if result else "WebFetch hostname differs or rule is unsupported"
    field = "file_path" if tool in {"Read", "Edit", "Write", "NotebookEdit"} else None
    if field:
        value = str(tool_input.get(field, ""))
        result = _path_match(spec, value)
        return result, f"{field} matches" if result else f"{field} differs"
    return False, "this rule type is outside the simulator's supported subset"


def explain(settings: dict[str, Any], tool: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    """Explain deny/ask/allow precedence, then report the configured mode."""
    permissions = settings.get("permissions", {})
    if not isinstance(permissions, dict):
        permissions = {}
    evaluated: list[dict[str, Any]] = []
    for group in ("deny", "ask", "allow"):
        rules = permissions.get(group, [])
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, str):
                continue
            matched, reason = matches(rule, tool, tool_input)
            evaluated.append({"group": group, "rule": rule, "matched": matched, "reason": reason})
    winner = next((item for item in evaluated if item["matched"]), None)
    mode = str(settings.get("defaultMode", "default"))
    decision = winner["group"] if winner else "mode-dependent"
    summary = {
        "tool": tool,
        "input": tool_input,
        "default_mode": mode,
        "decision": decision,
        "winning_rule": winner["rule"] if winner else None,
        "precedence_note": "Deny rules are checked before ask rules, then allow rules."
    }
    broad_allow_rules = []
    for item in evaluated:
        rule = item["rule"]
        is_broad = rule == tool
        if tool == "Bash" and rule == "Bash(*)":
            is_broad = True
        if tool == "WebFetch" and rule == "WebFetch(domain:*)":
            is_broad = True
        if item["group"] == "allow" and item["matched"] and is_broad:
            broad_allow_rules.append(rule)
    if broad_allow_rules:
        summary["warnings"] = [
            "A broad allow rule matched this call; review its scope before relying on it."
        ]
        summary["broad_allow_rules"] = broad_allow_rules
    if winner is None:
        if mode == "bypassPermissions":
            summary["mode_effect"] = "permission prompts are skipped in this mode"
        elif mode in {"acceptEdits", "plan", "dontAsk", "auto"}:
            summary["mode_effect"] = f"{mode!r} changes the default approval behavior; consult Claude Code's current mode documentation"
        else:
            summary["mode_effect"] = "no configured rule matched; Claude Code's normal permission flow applies"
    return {"summary": summary, "rules_checked": evaluated}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Simulate and explain a subset of Claude Code permission-rule matching.")
    parser.add_argument("settings", type=Path, help="path to a settings.json file")
    parser.add_argument("--tool", required=True, help="canonical tool name, for example Bash or Read")
    parser.add_argument("--input", default="{}", help="JSON object for the tool input; Bash example: '{\"command\":\"git status\"}'")
    args = parser.parse_args(argv)
    try:
        settings = json.loads(args.settings.read_text(encoding="utf-8"))
        tool_input = json.loads(args.input)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    if not isinstance(settings, dict) or not isinstance(tool_input, dict):
        print("Settings and --input must each contain a JSON object.", file=sys.stderr)
        return 2
    result = explain(settings, args.tool, tool_input)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
