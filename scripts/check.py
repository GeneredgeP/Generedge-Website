#!/usr/bin/env python3
"""Structural + accessibility checks on the generated HTML. Run after build.py.

Honours GE_BASE the same way build.py does, so it can check a build made for a
GitHub Pages project site (served under /<repo>/) as well as a domain-root one.
"""
import html.parser
import os
import re
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _clean_base(value):
    value = (value or "").strip()
    if value in ("", "/"):
        return ""
    if not value.startswith("/"):
        value = "/" + value
    return value.rstrip("/")


BASE = _clean_base(os.environ.get("GE_BASE"))

# Only the real generated pages: not the sources, not the build scripts, and
# not the packaged copy in _site/ (which is a stale duplicate between builds).
SKIP_DIRS = {'src', 'scripts', '_site', '.git', '.github'}
pages = sorted(list(ROOT.glob('*.html')) + list(ROOT.glob('*/index.html')))
pages = [p for p in pages if not SKIP_DIRS & set(p.relative_to(ROOT).parts)]
# Legacy-URL redirect stubs (meta refresh pages build.py writes from
# _redirects) are not real pages; skip them.
pages = [p for p in pages if 'http-equiv="refresh"' not in p.read_text(encoding='utf-8')[:600]]
problems, ids_by_page = [], {}


class Check(html.parser.HTMLParser):
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','source','track','wbr'}
    # HTML lets these be left unclosed, so an enclosing end tag closing over
    # one of them is legal rather than a mistake.
    OPTIONAL_END = {'li','p','td','th','tr','option','dt','dd','thead','tbody','tfoot'}

    def __init__(self):
        super().__init__()
        self.stack=[]; self.h=[]; self.imgs=[]; self.ids=set()
        self.hrefs=[]; self.labels=set(); self.controls=[]; self.buttons=0
        self.assets=[]; self.targets_blank=[]; self.lead_forms=[]
        self.mismatched=[]; self.stray=[]

    def _record(self,t,d):
        if t in ('h1','h2','h3','h4'): self.h.append(int(t[1]))
        if t=='img': self.imgs.append(d)
        if d.get('id'): self.ids.add(d['id'])
        if d.get('href'): self.hrefs.append(d['href'])
        if t=='label' and d.get('for'): self.labels.add(d['for'])
        if t in ('input','select','textarea') and d.get('type')!='hidden': self.controls.append(d)
        if t=='button': self.buttons+=1
        # local files the page pulls in and that must therefore exist
        if t=='img' and d.get('src'): self.assets.append(d['src'])
        if t=='script' and d.get('src'): self.assets.append(d['src'])
        if t=='link' and d.get('href') and d.get('rel') in ('stylesheet','icon','apple-touch-icon'):
            self.assets.append(d['href'])
        if t=='a' and d.get('target')=='_blank': self.targets_blank.append(d)
        if t=='form' and 'data-lead-form' in d: self.lead_forms.append(d)

    def handle_starttag(self,t,a):
        self._record(t,dict(a))
        if t not in self.VOID: self.stack.append(t)

    # XML-style self-closing (<path d="…"/>) never opens anything. Pushing it
    # here is what used to leave a stray 'path' on the stack from every SVG.
    def handle_startendtag(self,t,a): self._record(t,dict(a))

    def handle_endtag(self,t):
        if t in self.VOID: return
        if self.stack and self.stack[-1]==t:
            self.stack.pop(); return
        if t in self.stack:
            # Unwinding silently is what made this check inert: a missing
            # </div> was simply absorbed by the next closing tag. Record every
            # tag this end tag closed over instead.
            while self.stack:
                top=self.stack.pop()
                if top==t: break
                if top not in self.OPTIONAL_END:
                    self.mismatched.append((top,t))
        else:
            self.stray.append(t)



def intrinsic_size(path):
    """(width, height) of a PNG or JPEG, read from the file header.

    Deliberately dependency-free: the site has no build requirements and this
    check must run anywhere build.py does.
    """
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        # IHDR is always the first chunk: width and height are big-endian u32.
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            # SOF0-SOF15 carry the frame size; C4/C8/CC are not frame headers.
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h = int.from_bytes(data[i + 5:i + 7], "big")
                w = int.from_bytes(data[i + 7:i + 9], "big")
                return w, h
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    return None


parsed={}
for p in pages:
    c=Check(); c.feed(p.read_text(encoding='utf-8')); parsed[p]=c
    ids_by_page[p.relative_to(ROOT).as_posix()] = c.ids


def strip_base(path):
    """Turn a deployed URL path back into a repo-relative one."""
    if BASE and path.startswith(BASE):
        path = path[len(BASE):] or '/'
    return path


def resolve(href):
    """Map an internal href to the page file that should serve it."""
    path = strip_base(href.split('#')[0])
    if not path or path == '/':
        return 'index.html'
    t = path.strip('/')
    if (ROOT/t).is_file(): return t
    if (ROOT/t/'index.html').is_file(): return f'{t}/index.html'
    return None


for p in pages:
    c=parsed[p]; name=p.relative_to(ROOT).as_posix()
    src=p.read_text(encoding='utf-8')
    if c.stack: problems.append(f"{name}: unclosed tags {c.stack}")
    for opened, closer in c.mismatched:
        problems.append(f"{name}: </{closer}> closes over an unclosed <{opened}>")
    for t in c.stray:
        problems.append(f"{name}: stray </{t}> with no matching open tag")
    if c.h.count(1)!=1: problems.append(f"{name}: {c.h.count(1)} <h1> (want exactly 1)")
    if src.count('<main')!=1: problems.append(f"{name}: {src.count('<main')} <main> elements")
    if '<title>' not in src: problems.append(f"{name}: no <title>")
    if 'name="description"' not in src: problems.append(f"{name}: no meta description")
    if 'rel="canonical"' not in src: problems.append(f"{name}: no canonical")
    if '{{' in src or '}}' in src: problems.append(f"{name}: unsubstituted template token")
    if 'window.GE_FORM' not in src: problems.append(f"{name}: form configuration not injected")

    for im in c.imgs:
        if 'alt' not in im: problems.append(f"{name}: <img> without alt: {im.get('src')}")
        elif not im['alt'].strip() and 'aria-hidden' not in im:
            problems.append(f"{name}: <img> empty alt but not aria-hidden: {im.get('src')}")

        # Declared size must match the file, or the browser reserves the wrong
        # box and the page shifts as the image loads. This is the invariant
        # CLAUDE.md relies on, and fetch-assets.sh can break it by resizing.
        srcpath = (im.get('src') or '')
        if srcpath.startswith(('http', '//', 'data:')): continue
        w, h = im.get('width'), im.get('height')
        if not (w and h and w.isdigit() and h.isdigit()): continue
        f = ROOT / strip_base(srcpath.split('?')[0]).lstrip('/')
        if not f.is_file(): continue
        actual = intrinsic_size(f)
        if not actual or not actual[1]:
            continue
        # Declaring a scaled-down size is fine (the nav logo does it); what must
        # not drift is the RATIO, since that is what reserves the box shape.
        declared_ratio = int(w) / int(h)
        actual_ratio = actual[0] / actual[1]
        if abs(declared_ratio - actual_ratio) / actual_ratio > 0.02:
            problems.append(
                f"{name}: <img src={srcpath}> declares {w}x{h} "
                f"(ratio {declared_ratio:.3f}) but the file is "
                f"{actual[0]}x{actual[1]} (ratio {actual_ratio:.3f})")

    for ctl in c.controls:
        i=ctl.get('id')
        if not i: problems.append(f"{name}: form control with no id: {ctl}")
        elif i not in c.labels and 'aria-label' not in ctl:
            problems.append(f"{name}: control #{i} has no label")

    # every local asset the page references must actually be in the repo
    for a in c.assets:
        if a.startswith(('http://','https://','//','data:')): continue
        rel = strip_base(a.split('?')[0]).lstrip('/')
        if not (ROOT/rel).is_file():
            problems.append(f"{name}: missing asset {a}")

    # a new tab opened without rel=noopener hands the opener to the other page
    for a in c.targets_blank:
        if 'noopener' not in (a.get('rel') or ''):
            problems.append(f"{name}: target=_blank without rel=noopener: {a.get('href')}")

    # Without JavaScript a form with no action GETs the current page, putting
    # the visitor's name, email and phone into the URL and losing the lead.
    for fm in c.lead_forms:
        fid = fm.get('id') or '(no id)'
        action = (fm.get('action') or '').strip()
        method = (fm.get('method') or 'get').strip().lower()
        if not action:
            problems.append(f"{name}: lead form #{fid} has no action — a no-JS submit would leak PII into the URL")
        if method != 'post':
            problems.append(f"{name}: lead form #{fid} uses method={method!r}, must be post")

    for hr in c.hrefs:
        if hr.startswith(('http','mailto:','tel:')) or hr=='#': continue
        frag = hr.split('#')[1] if '#' in hr else None
        if hr.startswith('#'):
            target=name
        else:
            target=resolve(hr)
            if target is None:
                problems.append(f"{name}: broken internal link {hr}"); continue
        if frag and frag not in ids_by_page.get(target,set()):
            problems.append(f"{name}: link {hr} -> #{frag} not found in {target}")

    # With a base path, no root-absolute internal URL may escape the prefix.
    # Scanned over the raw source rather than the parsed attribute list, so a
    # URL hiding in srcset or an inline url(/…) cannot slip through — those are
    # exactly the shapes that would 404 silently on a project site.
    if BASE:
        for m in re.finditer(r'(?:href|src|action|srcset|imagesrcset)="([^"]*)"', src):
            for part in m.group(1).split(','):
                url = part.strip().split(' ')[0]
                if not url.startswith('/') or url.startswith('//'): continue
                if not url.startswith(BASE + '/') and url != BASE:
                    problems.append(f"{name}: URL {url} is not under the base path {BASE}")
        for m in re.finditer(r'url\(([\'"]?)(/[^)\'"]*)', src):
            url = m.group(2)
            if url.startswith('//'): continue
            if not url.startswith(BASE + '/'):
                problems.append(f"{name}: url({url}) is not under the base path {BASE}")

print(f"checked {len(pages)} pages (base={BASE or '/'})")
if problems:
    print("\nISSUES:"); [print(" -",x) for x in problems]; sys.exit(1)
print("all structural and accessibility checks passed")
