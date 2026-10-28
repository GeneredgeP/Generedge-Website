#!/usr/bin/env python3
"""Assemble the publishable site into _site/.

    python3 scripts/package.py

Copies only what belongs on a web server — the generated HTML, the assets, the
crawler files and the redirect tables — and leaves the sources, the build
scripts and the project notes behind. The GitHub Pages workflow uploads _site/,
and running this locally shows exactly what would be deployed.

It refuses to package a build that is older than the sources it came from, and
it prints the deployment target the build was made for, because _site/ is what
CLAUDE.md tells the operator to upload to Hostinger — shipping a Pages-targeted
build there would 404 every stylesheet, image and internal link and block
crawling, with no visible error.
"""

import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"

sys.path.insert(0, str(ROOT / "scripts"))
import build  # noqa: E402  — the source of truth for what gets generated

# Files a visitor may fetch that are not page output.
STATIC = [
    "robots.txt",
    "sitemap.xml",
    ".nojekyll",
    "CNAME",            # only exists once a custom domain is attached
    ".htaccess",        # Apache/LiteSpeed: legacy 301s, headers, ErrorDocument
    "_redirects",       # the same table for Netlify/Cloudflare Pages
    "assets",
]

# Page output, derived from build.PAGES so a new page cannot be built, checked
# and then silently left unpublished. Taking the first path segment yields the
# page directories plus the two root-level files (index.html, 404.html), which
# the copy loop below handles as files.
PAGES = sorted({out.split("/")[0] for out, *_ in build.PAGES.values()})

# Legacy-URL redirect stubs (see build.legacy_redirects) and the Google Search
# Console ownership file(s) at the root.
LEGACY = sorted({src.strip("/").split("/")[0] for src, _ in build.legacy_redirects()})
GOOGLE = sorted(p.name for p in ROOT.glob("google*.html"))

PUBLISH = PAGES + STATIC + LEGACY + GOOGLE


def newest(paths):
    times = [p.stat().st_mtime for p in paths if p.is_file()]
    return max(times) if times else 0


def oldest(paths):
    times = [p.stat().st_mtime for p in paths if p.is_file()]
    return min(times) if times else 0


def check_fresh():
    """Refuse to publish output older than the sources that produced it."""
    sources = list((ROOT / "src").glob("*.html")) + [ROOT / "scripts" / "build.py"]
    generated = [ROOT / out for out, *_ in build.PAGES.values()]
    missing = [g for g in generated if not g.is_file()]
    if missing:
        sys.exit(
            "no build to publish (missing "
            + ", ".join(m.relative_to(ROOT).as_posix() for m in missing)
            + ") — run scripts/build.py first"
        )
    if newest(sources) > oldest(generated):
        sys.exit(
            "generated HTML is older than src/ or build.py — run "
            "scripts/build.py first, or _site/ will ship stale content"
        )


def describe_target():
    """Report the origin and base path the build was actually made for."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<link rel="canonical" href="([^"]+)"', html)
    canonical = m.group(1) if m else "(no canonical found)"
    indexable = 'content="index' in html
    return canonical, indexable


def main():
    check_fresh()
    canonical, indexable = describe_target()

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    copied, skipped = [], []
    for name in PUBLISH:
        src = ROOT / name
        if not src.exists():
            skipped.append(name)
            continue
        dest = OUT / name
        if src.is_dir():
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)
        copied.append(name)

    if not (OUT / "index.html").is_file():
        sys.exit("no index.html to publish — run scripts/build.py first")

    files = [f for f in OUT.rglob("*") if f.is_file()]
    total = sum(f.stat().st_size for f in files)
    print(f"packaged {len(files)} files ({total/1024:.0f} KB) into {OUT.relative_to(ROOT)}/")
    print(f"  built for: {canonical}  ({'indexable' if indexable else 'noindex'})")
    print("  included:", ", ".join(sorted(copied)))
    if skipped:
        print("  not present:", ", ".join(skipped))


if __name__ == "__main__":
    main()
