#!/usr/bin/env python3
"""Pull build-time imports from the ecosystem repos, as declared in sources.toml.

The site documents each project's current `main`. Hand-written prose lives
here; material that the source repos already maintain in end-user form (the
Lens user manual, Loom's per-command CLI pages, Influx's runbook) is fetched
verbatim at build time rather than copied, so it cannot lag upstream. Every
destination is gitignored — scripts/check_drift.py asserts that.

Run before `mkdocs build`:   python3 scripts/sync_sources.py
Offline / from sibling checkouts:
    LITHOS_DOCS_SOURCES_ROOT=~/projects/lithos/code python3 scripts/sync_sources.py
(the root must contain one directory per repo name: lithos-lens, lithos-loom, influx)

A GITHUB_TOKEN in the environment raises the API rate limit for directory
listings; unauthenticated use is fine for a handful of builds per hour.
"""

from __future__ import annotations

import fnmatch
import json
import os
import posixpath
import re
import sys
import tomllib
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "sources.toml"
LOCAL_ROOT = os.environ.get("LITHOS_DOCS_SOURCES_ROOT", "")
LINK_RE = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)(\))")


@dataclass(frozen=True)
class Item:
    repo: str
    ref: str
    src: str  # upstream path
    dest: str  # repo-relative destination
    rewrite_links: bool
    drop: tuple[str, ...]
    title: str | None
    banner: bool


def _http(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "lithos-docs-sync"})
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def fetch(repo: str, ref: str, path: str) -> bytes:
    if LOCAL_ROOT:
        local = Path(LOCAL_ROOT).expanduser() / repo.split("/")[1] / path
        return local.read_bytes()
    return _http(f"https://raw.githubusercontent.com/{repo}/{ref}/{path}")


def listdir(repo: str, ref: str, path: str) -> list[str]:
    if LOCAL_ROOT:
        local = Path(LOCAL_ROOT).expanduser() / repo.split("/")[1] / path
        return sorted(p.name for p in local.iterdir() if p.is_file())
    data = json.loads(_http(f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"))
    return sorted(e["name"] for e in data if e.get("type") == "file")


def expand(entry: dict) -> list[Item]:
    repo, ref = entry["repo"], entry.get("ref", "main")
    common = dict(
        drop=tuple(entry.get("drop_lines_matching", ())),
        title=entry.get("title"),
        banner=entry.get("banner", True),
    )
    if "src" in entry:
        src, dest = entry["src"], entry["dest"]
        return [Item(repo, ref, src, dest, entry.get("rewrite_links", src.endswith(".md")), **common)]
    src_dir, dest_dir = entry["src_dir"].rstrip("/"), entry["dest_dir"].rstrip("/")
    pattern = entry.get("pattern", "*")
    return [
        Item(
            repo,
            ref,
            f"{src_dir}/{name}",
            f"{dest_dir}/{name}",
            entry.get("rewrite_links", name.endswith(".md")),
            **common,
        )
        for name in listdir(repo, ref, src_dir)
        if fnmatch.fnmatch(name, pattern)
    ]


def rewrite(text: str, item: Item, imported: dict[tuple[str, str], str]) -> str:
    """Relative links: to a co-imported file -> relative link between dests; else GitHub URL."""
    src_dir = posixpath.dirname(item.src)
    dest_dir = posixpath.dirname(item.dest)

    def sub(m: re.Match[str]) -> str:
        target = m.group(2)
        if re.match(r"^[a-z]+:|^#|^/", target):
            return m.group(0)
        path, _, frag = target.partition("#")
        upstream = posixpath.normpath(posixpath.join(src_dir, path))
        dest = imported.get((item.repo, upstream))
        if dest is not None:
            new = posixpath.relpath(dest, dest_dir)
        else:
            new = f"https://github.com/{item.repo}/blob/{item.ref}/{upstream}"
        return f"{m.group(1)}{new}{'#' + frag if frag else ''}{m.group(3)}"

    return LINK_RE.sub(sub, text)


def transform_md(text: str, item: Item, imported: dict[tuple[str, str], str]) -> str:
    lines = text.splitlines()
    if item.drop:
        drops = [re.compile(p) for p in item.drop]
        lines = [ln for ln in lines if not any(d.search(ln) for d in drops)]
    if item.title:
        for i, ln in enumerate(lines):
            if ln.startswith("# "):
                lines[i] = f"# {item.title}"
                break
    text = "\n".join(lines).rstrip() + "\n"
    if item.rewrite_links:
        text = rewrite(text, item, imported)
    if item.banner:
        url = f"https://github.com/{item.repo}/blob/{item.ref}/{item.src}"
        note = (
            f'!!! abstract "Pulled from the {item.repo.split("/")[1]} repo"\n'
            f"    This page is imported at build time from "
            f"[`{item.src}`]({url}) on `{item.ref}`. Edit it there, not here.\n\n"
        )
        # Keep the H1 first so page titles and anchors are unchanged.
        if text.startswith("# "):
            head, _, rest = text.partition("\n")
            text = f"{head}\n\n{note}{rest.lstrip()}"
        else:
            text = note + text
    return (
        f"<!-- IMPORTED by scripts/sync_sources.py from {item.repo}:{item.src}@{item.ref}."
        " Do not edit; this file is gitignored. -->\n" + text
    )


def main() -> int:
    manifest = tomllib.loads(MANIFEST.read_text())
    items = [it for entry in manifest["import"] for it in expand(entry)]
    imported = {(it.repo, it.src): it.dest for it in items}
    for it in items:
        raw = fetch(it.repo, it.ref, it.src)
        out = ROOT / it.dest
        out.parent.mkdir(parents=True, exist_ok=True)
        if it.dest.endswith(".md"):
            out.write_text(transform_md(raw.decode("utf-8"), it, imported))
        else:
            out.write_bytes(raw)
        print(f"  {it.repo}:{it.src} -> {it.dest}")
    print(f"Synced {len(items)} files from {len({it.repo for it in items})} repos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
