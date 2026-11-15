#!/usr/bin/env python3
"""Consistency check run at every wind-up. Shared from the base: don't edit it in a project.

Checks that:
- inbox/ holds only its README
- every file in sources/<category>/ is listed in that category's README, and every listed file exists
- every top-level folder, sources category and reference subfolder has a README.md
- every relative link in Markdown and HTML files points to something that exists
- every path written in backticks in a Markdown file exists
- no base-only file (the licence) is in a project
- no file from the base has been edited here (adding files and leaving files out are fine)

Run from the repo root: python3 scripts/check.py
Exits with 1 if anything needs fixing.
"""
import os
import re
import subprocess
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".github"}
IGNORED_FILES = {".DS_Store", "README.md"}
# Shared files: identical to the base in every project.
SHARED = ["README.md", "AGENTS.md", "guidance", "scripts", ".github", "inbox/README.md", ".gitattributes"]

problems = []


def rel(path):
    return os.path.relpath(path, ROOT)


def check_inbox():
    inbox = os.path.join(ROOT, "inbox")
    if not os.path.isdir(inbox):
        problems.append("inbox/ is missing")
        return
    for dirpath, _, files in os.walk(inbox):
        for f in files:
            if f == ".DS_Store" or (f == "README.md" and dirpath == inbox):
                continue
            problems.append(f"{rel(os.path.join(dirpath, f))} is still in the inbox: file it or ask about it")


def links_in(text):
    found = re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text)
    found += re.findall(r'(?:href|src)="([^"#]+)', text)
    return [l for l in found if not re.match(r"^[a-z]+:", l)]


def check_sources():
    sources = os.path.join(ROOT, "sources")
    if not os.path.isdir(sources):
        return
    for cat in sorted(os.listdir(sources)):
        d = os.path.join(sources, cat)
        if not os.path.isdir(d):
            continue
        readme = os.path.join(d, "README.md")
        if not os.path.exists(readme):
            problems.append(f"{rel(d)}/ has no README.md index")
            continue
        text = open(readme, encoding="utf-8", errors="ignore").read()
        listed = {os.path.normpath(urllib.parse.unquote(l)) for l in links_in(text)}
        for l in listed:
            if not os.path.exists(os.path.join(d, l)):
                problems.append(f"{rel(readme)} lists {l}, which doesn't exist")
        for dirpath, _, files in os.walk(d):
            for f in files:
                if f in IGNORED_FILES:
                    continue
                r = os.path.normpath(os.path.relpath(os.path.join(dirpath, f), d))
                if r not in listed:
                    problems.append(f"{rel(os.path.join(dirpath, f))} isn't listed in {rel(readme)}")


def check_readmes():
    wanted = [os.path.join(ROOT, d) for d in os.listdir(ROOT)
              if os.path.isdir(os.path.join(ROOT, d)) and d not in SKIP_DIRS and not d.startswith(".")]
    for parent in ("sources", "reference"):
        p = os.path.join(ROOT, parent)
        if os.path.isdir(p):
            wanted += [os.path.join(p, d) for d in os.listdir(p) if os.path.isdir(os.path.join(p, d))]
    for d in wanted:
        if not os.path.exists(os.path.join(d, "README.md")):
            problems.append(f"{rel(d)}/ has no README.md")


def check_links():
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.endswith((".md", ".html")):
                continue
            path = os.path.join(dirpath, f)
            text = open(path, encoding="utf-8", errors="ignore").read()
            for l in links_in(text):
                target = os.path.normpath(os.path.join(dirpath, urllib.parse.unquote(l)))
                if not os.path.exists(target):
                    problems.append(f"{rel(path)} links to {l}, which doesn't exist")


PATHISH = re.compile(r"^[\w.\-' ()&,+]+(/[\w.\-' ()&,+]*)+$|^[\w.\-' ()&,+]+\.(md|pdf|png|jpe?g|html|py|txt|docx?|pptx?|xlsx|csv|m4a|mp4|mov|key|pages)$", re.I)


def check_backtick_paths():
    """Paths written in backticks, the usual way to name a file in these repos, must exist.

    A path is tried relative to the file it's in, that file's parent folder, the repo root and
    sources/. The shared README.md is skipped: it names example folders. Skipped: anything
    with a wildcard or placeholder, commands, and lines saying the path is to be created.
    """
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(dirpath, f)
            if rel(path).startswith("sources" + os.sep) and f != "README.md":
                continue  # originals are never edited, so never checked
            if rel(path) == "README.md":
                continue  # the shared rules name example folders that a project may not have
            in_code = False
            for n, line in enumerate(open(path, encoding="utf-8", errors="ignore"), 1):
                if line.lstrip().startswith("```"):
                    in_code = not in_code
                    continue
                if in_code or "to be created" in line or "not yet" in line.lower():
                    continue
                for token in re.findall(r"`([^`\n]+)`", line):
                    t = token.strip()
                    if "YYYY" in t or any(c in t for c in "*?<>{}|$=…~") or t.startswith(("-", "http", "/", "git ", "python")):
                        continue
                    if "/" not in t or not PATHISH.match(t):
                        continue  # a bare file name is usually a name, not a path
                    candidates = [os.path.join(dirpath, t), os.path.join(os.path.dirname(dirpath), t),
                                  os.path.join(ROOT, t), os.path.join(ROOT, "sources", t)]
                    if not any(os.path.exists(os.path.normpath(c)) for c in candidates):
                        problems.append(f"{rel(path)}:{n} names `{t}`, which doesn't exist")


def check_base_only():
    """Files listed in .github/base-only (the base's licence) must not be in a project."""
    listing = os.path.join(ROOT, ".github", "base-only")
    is_project = subprocess.run(["git", "remote", "get-url", "base"], cwd=ROOT, capture_output=True).returncode == 0
    if not is_project or not os.path.exists(listing):
        return
    for line in open(listing, encoding="utf-8"):
        path = line.strip()
        if path and not path.startswith("#") and os.path.exists(os.path.join(ROOT, path)):
            problems.append(f"{path} belongs to the base only: delete it from this project")


def check_shared():
    """Shared files should match base/main. Skipped in the base itself and before the first fetch."""
    try:
        subprocess.run(["git", "rev-parse", "--verify", "-q", "base/main"], cwd=ROOT, check=True,
                       capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return
    # Only edits count. Files a project adds beside the base's (additive) and base
    # files it deleted on purpose (left out) are both fine.
    out = subprocess.run(["git", "diff", "--name-only", "--diff-filter=M", "base/main", "--"] + SHARED,
                         cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
    for f in filter(None, out):
        problems.append(f"{f} was edited here but comes from the base: make the change in the base instead")


check_inbox()
check_sources()
check_readmes()
check_links()
check_backtick_paths()
check_base_only()
check_shared()

if problems:
    print(f"{len(problems)} thing(s) to fix:")
    for p in problems:
        print(f"- {p}")
    sys.exit(1)
print("All checks passed.")
