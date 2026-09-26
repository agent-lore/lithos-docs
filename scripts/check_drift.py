#!/usr/bin/env python3
"""Drift check: assert this docs site agrees with the lithos repo.

The lithos repo maintains a drift-checked, generated MCP tool catalog
(docs/generated/tool_catalog.md — CI over there fails if it disagrees with
the code). This script asserts the docs site agrees with that catalog:

1. Every tool in the catalog has a `## `tool`` section under docs/mcp-tools/.
2. Every tool section in docs/mcp-tools/ still exists in the catalog
   (catches removed/renamed tools lingering in the docs).
3. Every "<N> tools" / "<N> MCP tools" claim in the docs equals the
   catalog's tool count.
4. No banned stale markers (removed tools, the pre-0.3.2 transport flag,
   the never-existed /metrics endpoint) appear outside the changelog.
   A line may mention one deliberately (migration notes, "there is no X")
   by carrying an HTML comment containing `drift-allow`.

Run locally:  python3 scripts/check_drift.py
Offline:      LITHOS_TOOL_CATALOG=/path/to/lithos/docs/generated/tool_catalog.md \
              python3 scripts/check_drift.py

Exits non-zero with a report when the site has drifted.
"""

from __future__ import annotations

import os
import re
import sys
import urllib.request
from pathlib import Path

CATALOG_URL = (
    "https://raw.githubusercontent.com/agent-lore/lithos/main/docs/generated/tool_catalog.md"
)
DOCS = Path(__file__).resolve().parent.parent / "docs"
ALLOW_MARKER = "drift-allow"
# Historical pages may state historical facts.
EXCLUDED = {"changelog.md"}
BANNED = [
    "lithos_links",       # removed v0.2.1 -> lithos_related
    "lithos_provenance",  # removed v0.2.1 -> lithos_related
    "lithos_semantic",    # removed v0.2.0 -> lithos_search(mode="semantic")
    "lithos_health",      # removed pre-0.2.1 -> GET /health
    "--transport sse",    # renamed v0.3.2 -> --transport http
    "GET /metrics",       # never existed; telemetry is OTLP push-only
]


def load_catalog() -> str:
    src = os.environ.get("LITHOS_TOOL_CATALOG")
    if src:
        return Path(src).read_text(encoding="utf-8")
    try:
        with urllib.request.urlopen(CATALOG_URL, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.URLError:
        # e.g. a local python built without SSL — fall back to curl
        import subprocess

        return subprocess.run(
            ["curl", "-fsSL", "--max-time", "30", CATALOG_URL],
            check=True, capture_output=True, text=True,
        ).stdout


def main() -> int:
    problems: list[str] = []

    catalog = load_catalog()
    tools = set(re.findall(r"^(lithos_[a-z_]+)\(", catalog, re.M))
    header = re.search(r"(\d+) tools exposed", catalog)
    count = int(header.group(1)) if header else len(tools)
    if not tools:
        print("FATAL: no tool signatures parsed from the catalog — check the fetch/format")
        return 2
    if header and count != len(tools):
        problems.append(
            f"catalog header claims {count} tools but {len(tools)} signatures parsed"
        )

    pages = [
        p for p in sorted(DOCS.rglob("*.md"))
        if p.relative_to(DOCS).as_posix() not in EXCLUDED
    ]

    # 1 + 2: tool sections vs catalog
    ref_text = "\n".join(p.read_text(encoding="utf-8") for p in DOCS.glob("mcp-tools/*.md"))
    documented = set(re.findall(r"^## `(lithos_[a-z_]+)`", ref_text, re.M))
    for tool in sorted(tools - documented):
        problems.append(f"tool in catalog but missing from docs/mcp-tools/: {tool}")
    for tool in sorted(documented - tools):
        problems.append(f"docs/mcp-tools/ documents a tool absent from the catalog: {tool}")

    # 3 + 4: per-page count claims and banned markers
    for page in pages:
        rel = page.relative_to(DOCS).as_posix()
        for lineno, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
            if ALLOW_MARKER in line:
                continue
            for claim in re.findall(r"(\d+)\s+(?:MCP\s+)?tools\b", line):
                if int(claim) != count:
                    problems.append(
                        f"{rel}:{lineno}: claims {claim} tools; catalog has {count}"
                    )
            for marker in BANNED:
                if marker in line:
                    problems.append(
                        f"{rel}:{lineno}: stale marker {marker!r} "
                        f"(annotate the line with <!-- {ALLOW_MARKER} --> if deliberate)"
                    )

    if problems:
        print(f"Docs drift detected ({len(problems)} problem(s)) vs lithos main:\n")
        for p in problems:
            print(f"  - {p}")
        print(
            "\nSources of truth and the update playbook are in AGENTS.md. "
            "The catalog checked against: "
            + os.environ.get("LITHOS_TOOL_CATALOG", CATALOG_URL)
        )
        return 1

    print(f"OK: {len(tools)} tools documented, counts consistent, no stale markers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
