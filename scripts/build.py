#!/usr/bin/env python3
"""
GenerEdge static site builder.

Assembles the shared chrome (head, header, footer, cookie banner) around the
per-page bodies in src/ and writes plain HTML to the repo root.

    python3 scripts/build.py

The generated .html files are committed, so deployment is a plain file copy —
no build step is required on the server. Re-run this after editing anything in
src/ or after changing SITE/PAGES below.

Two environment variables let the same source tree publish to more than one
host without editing anything:

    GE_ORIGIN   scheme + host the site will be served from
                (default https://generedge.com)
    GE_BASE     sub-path the site is served under, no trailing slash
                (default empty — i.e. served from the domain root)

GitHub Pages project sites live at https://<user>.github.io/<repo>/, so the
Pages workflow calls this with GE_BASE=/<repo>. Every root-absolute URL in the
generated HTML is rewritten with that prefix. On Hostinger (or once a custom
domain is attached to Pages) both are left at their defaults and nothing is
rewritten.
"""

import json
import os
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

# --------------------------------------------------------------------------
# Deployment target — overridable from the environment (see module docstring)
# --------------------------------------------------------------------------


def _clean_base(value):
    """Normalise a base path: '', '/', '/repo/' and 'repo' all behave sanely."""
    value = (value or "").strip()
    if value in ("", "/"):
        return ""
    if not value.startswith("/"):
        value = "/" + value
    return value.rstrip("/")


ORIGIN = (os.environ.get("GE_ORIGIN") or "https://generedge.com").rstrip("/")
BASE = _clean_base(os.environ.get("GE_BASE"))

# A github.io build is a preview, not the production site. It must not be
# indexed: it would be a complete, self-canonicalising duplicate of a financial
# services site competing with generedge.com in search — and robots.txt cannot
# stop it, because crawlers only read https://<user>.github.io/robots.txt, which
# a *project* site (served under /<repo>/) does not control. The meta tag is the
# only lever that works from here. Set GE_NOINDEX=0 to force indexing anyway.
_noindex_env = os.environ.get("GE_NOINDEX")
if _noindex_env is not None:
    NOINDEX = _noindex_env not in ("", "0", "false", "no")
else:
    NOINDEX = ORIGIN.endswith(".github.io")

# --------------------------------------------------------------------------
# Site-wide settings
# --------------------------------------------------------------------------

SITE = {
    "name": "GenerEdge",
    "legal_name": "GenerEdge, Inc.",
    "origin": ORIGIN,
    "base": BASE,
    "phone_display": "(727) 370-0200",
    "phone_href": "+17273700200",
    "email": "info@generedge.com",
    "locality": "St. Petersburg",
    "region": "FL",
    "tagline": "Approval-Ready Borrowing",
    # Calendly — house rule: Home uses Steve's link, every other page uses Tracey's.
    "calendly_steve": "https://calendly.com/steve-generedge/15min",
    "calendly_tracey": "https://calendly.com/tracey-generedge/new-meeting",
    # Analytics stays dormant until this is a real GA4 ID AND the visitor
    # accepts cookies. Leave the placeholder to keep it off.
    "ga_id": "G-XXXXXXXXXX",
}

# --------------------------------------------------------------------------
# Where lead submissions go
# --------------------------------------------------------------------------
# provider:
#   "formsubmit" — emails the lead to `email` via formsubmit.co. No account, no
#                  API key, works from a static host. The FIRST submission after
#                  launch triggers a one-time confirmation email to that address;
#                  clicking the link in it activates the form for good.
#   "web3forms"  — set `access_key` to the key web3forms.com emails you. The key
#                  is public by design (it only allows posting to your own inbox).
#   "formspree"  — set `endpoint` to your https://formspree.io/f/xxxx URL.
#   "custom"     — set `endpoint` to any URL that accepts a JSON POST. Use this
#                  for the Close CRM worker described in CLAUDE.md.
#
# Whatever the provider, a failed send never loses the lead: site.js falls back
# to a pre-filled mailto: link so the visitor can send the same details by email.
FORM = {
    # Leads go to GenerEdge's own Google Apps Script web app (source in
    # apps-script/Code.gs, project "GenerEdge — Website Forms" under
    # eduardo@generedge.com), which emails them and logs them to a Sheet.
    "provider": "custom",
    # Shown to visitors in the failure fallback (mailto link). The address the
    # Apps Script sends leads to is the TO constant in apps-script/Code.gs.
    "email": "eduardo@generedge.com",
    "endpoint": "https://script.google.com/macros/s/AKfycbwIcdy5jJyotFhhLvyarHE3Gx8K-_vRUsRwvYX3M092Yodhu-5NM4qS_k7VsZhnxgD9/exec",
    "access_key": "",
    "subject": "New enquiry from generedge.com",
}

NAV = [
    ("/", "Home", "home"),
    ("/business-loans/", "Business Financing", "loans"),
    ("/about-us/", "About Us", "about"),
]

# key -> (output path, <title>, meta description, nav key)
PAGES = {
    "index": (
        "index.html",
        "GenerEdge — Approval-Ready Borrowing for Builders",
        "No up-front fees. GenerEdge works for builders to get their loans approved — "
        "lender matching, underwriting review and closing support.",
        "home",
    ),
    "business-loans": (
        "business-loans/index.html",
        "Business Financing from Mission-Driven Lenders | GenerEdge",
        "Business loans from $50,000 to $1 million through credit unions, CDFIs and "
        "community banks. No hard credit pull to get matched. No up-front fees.",
        "loans",
    ),
    "about-us": (
        "about-us/index.html",
        "About Us — Your Small Business Loan Co-Pilot | GenerEdge",
        "Real people, lower rates, zero hidden surprises. GenerEdge is an independent "
        "borrower's agent working with community banks, credit unions and CDFIs. No "
        "up-front fees.",
        "about",
    ),
    "contact-us": (
        "contact-us/index.html",
        "Contact Us | GenerEdge",
        "Talk to a real person about your financing. Call (727) 370-0200, email "
        "info@generedge.com, or send us your project details.",
        "contact",
    ),
    "privacy-policy": (
        "privacy-policy/index.html",
        "Privacy Policy | GenerEdge",
        "How GenerEdge, Inc. collects, uses, shares and safeguards your information, "
        "including SMS messaging and mobile privacy.",
        "legal",
    ),
    "terms-and-conditions": (
        "terms-and-conditions/index.html",
        "Terms and Conditions | GenerEdge",
        "The terms governing your use of generedge.com, including SMS messaging terms, "
        "disclaimers and dispute resolution.",
        "legal",
    ),
    "cookies-policy": (
        "cookies-policy/index.html",
        "Cookie Policy | GenerEdge",
        "What cookies generedge.com uses, why, and how to control them.",
        "legal",
    ),
    "404": (
        "404.html",
        "Page Not Found | GenerEdge",
        "The page you are looking for has moved or no longer exists.",
        "none",
    ),
}


def form_endpoints():
    """(ajax endpoint for fetch, plain endpoint for a native form POST).

    They differ for FormSubmit, which has a separate JSON route.
    """
    provider = FORM["provider"]
    endpoint = FORM["endpoint"]
    if provider == "formsubmit":
        plain = endpoint or "https://formsubmit.co/" + FORM["email"]
        ajax = endpoint or "https://formsubmit.co/ajax/" + FORM["email"]
        return ajax, plain
    if provider == "web3forms":
        url = endpoint or "https://api.web3forms.com/submit"
        return url, url
    return endpoint, endpoint


def form_attrs():
    """method/action for the <form> tag, so it still works without JavaScript.

    JavaScript calls preventDefault() and posts with fetch instead, so these
    attributes only ever take effect when scripting is off or has failed. That
    matters: a form with no action at all falls back to a GET of the current
    page, which would put the visitor's name, email and phone number into the
    URL — and into browser history and server logs — and then lose the lead.
    """
    _, plain = form_endpoints()
    if plain:
        return f'method="post" action="{plain}"'
    # Nothing configured: hand it to the visitor's mail client rather than
    # leaking the fields into a query string.
    return f'method="post" action="mailto:{SITE["email"]}" enctype="text/plain"'


def form_hidden():
    """Provider fields a native (non-JavaScript) POST needs in the markup.

    FormSubmit's captcha is deliberately left on for this path — it is the only
    bot defence when the honeypot's JavaScript check cannot run.
    """
    if FORM["provider"] == "web3forms" and FORM["access_key"]:
        return f'<input type="hidden" name="access_key" value="{FORM["access_key"]}">'
    return ""


def form_config():
    """The object site.js reads to decide where a submission goes."""
    provider = FORM["provider"]
    endpoint, _plain = form_endpoints()
    return {
        "provider": provider,
        "endpoint": endpoint,
        "accessKey": FORM["access_key"],
        "email": FORM["email"],
        "phone": SITE["phone_display"],
        "subject": FORM["subject"],
    }


def _script_safe(json_text):
    """Make a JSON literal safe to inline in a <script> block.

    The HTML tokenizer ends the block at the first literal `</script>`, so a
    value containing one would break the page and leave window.GE_FORM
    undefined. `<\\/` is valid JSON string syntax and parses back to `</`.
    """
    return json_text.replace("</", "<\\/").replace("<!--", "<\\!--")


def head(title, desc, canonical_path):
    canonical = SITE["origin"] + BASE + canonical_path
    og_image = SITE["origin"] + BASE + "/assets/img/og-default.png"
    form_json = _script_safe(json.dumps(form_config(), separators=(",", ":")))
    ga_json = _script_safe(json.dumps(SITE["ga_id"]))
    robots = "noindex, nofollow" if NOINDEX else "index, follow"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="{robots}">

<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE['name']}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_image}">
<meta name="twitter:card" content="summary_large_image">

<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/img/apple-touch-icon.png">
<meta name="theme-color" content="#08281A">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700;800&amp;family=Figtree:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/site.css">
<script>document.documentElement.className+=" js";window.GE_GA_ID={ga_json};window.GE_FORM={form_json};</script>
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>
<div class="site">
"""


def header(active):
    items = []
    for href, label, key in NAV:
        cur = ' aria-current="page"' if key == active else ""
        items.append(f'      <a href="{href}"{cur}>{label}</a>')
    cur_contact = ' aria-current="page"' if active == "contact" else ""
    items.append(
        f'      <a href="/contact-us/" class="btn btn--out btn--sm"{cur_contact}>Contact Us</a>'
    )
    links = "\n".join(items)
    # 800x233 is the intrinsic size of assets/img/logo.png — keep the ratio so
    # the browser reserves the right box and nothing shifts as it loads.
    return f"""<nav class="nav" aria-label="Main">
  <div class="wrap">
    <a href="/" class="logotext" aria-label="GenerEdge home">
      <img src="/assets/img/logo.png" alt="GenerEdge" width="200" height="58">
    </a>
    <button class="navtoggle" type="button" aria-expanded="false" aria-controls="navlinks">
      <svg width="20" height="16" viewBox="0 0 20 16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true"><path d="M1 1h18M1 8h18M1 15h18"/></svg>
      Menu
    </button>
    <div class="navlinks" id="navlinks">
{links}
    </div>
  </div>
</nav>
<main id="main">
"""


FOOTER = f"""</main>

<footer class="foot">
  <div class="wrap">
    <div class="cols">
      <div>
        <div style="font-family:var(--display);font-size:26px;font-weight:800;color:#fff;margin-bottom:14px">GenerEdge</div>
        <p style="color:#CFE5D9;font-size:17px;max-width:38ch">Equal access lending. Get in touch to learn how GenerEdge can help.</p>
        <a href="/contact-us/" class="btn btn--light btn--sm" style="margin-top:20px">Contact us</a>
      </div>
      <div>
        <h2>Quick links</h2>
        <ul>
          <li><a href="/">Home</a></li>
          <li><a href="/business-loans/">Business Financing</a></li>
          <li><a href="/about-us/">About Us</a></li>
          <li><a href="/contact-us/">Contact Us</a></li>
        </ul>
      </div>
      <div>
        <h2>Legal</h2>
        <ul>
          <li><a href="/privacy-policy/">Privacy Policy</a></li>
          <li><a href="/terms-and-conditions/">Terms and Conditions</a></li>
          <li><a href="/cookies-policy/">Cookie Policy</a></li>
          <li><button type="button" class="linkish" data-consent-reopen>Cookie settings</button></li>
        </ul>
      </div>
      <div>
        <h2>Contact</h2>
        <address>
          {SITE['legal_name']}<br>
          {SITE['locality']}, {SITE['region']}<br>
          <a href="tel:{SITE['phone_href']}">{SITE['phone_display']}</a><br>
          <a href="mailto:{SITE['email']}">{SITE['email']}</a>
        </address>
      </div>
    </div>
    <p class="disc">{SITE['legal_name']} is not a lender. GenerEdge connects businesses with third-party lenders and financing providers. Approval, rates and terms are determined solely by the lender. Copyright &copy; 2026 {SITE['legal_name']} All rights reserved.</p>
  </div>
</footer>
</div>

<div class="cc" role="region" aria-label="Cookie consent" hidden>
  <div class="wrap">
    <p>We use essential cookies to run this site. With your permission we also use Google Analytics to understand how the site is used. Read our <a href="/cookies-policy/">Cookie Policy</a> and <a href="/privacy-policy/">Privacy Policy</a>.</p>
    <div class="cc__actions">
      <button type="button" class="btn btn--ghost" data-consent="denied">Essential only</button>
      <button type="button" class="btn btn--light" data-consent="granted">Accept analytics</button>
    </div>
  </div>
</div>

<script src="/assets/js/site.js" defer></script>
</body>
</html>
"""


ORG_SCHEMA = f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "FinancialService",
  "name": "{SITE['legal_name']}",
  "url": "{SITE['origin'] + BASE}/",
  "telephone": "{SITE['phone_display']}",
  "email": "{SITE['email']}",
  "address": {{
    "@type": "PostalAddress",
    "addressLocality": "{SITE['locality']}",
    "addressRegion": "{SITE['region']}",
    "addressCountry": "US"
  }},
  "areaServed": "US",
  "description": "GenerEdge connects business borrowers with credit unions, CDFIs and community banks offering fair rates and terms, and guides loan files from application through closing.",
  "disambiguatingDescription": "GenerEdge is not a lender. It is a lending connector service."
}}
</script>
"""


# Root-absolute URLs in href/src/action attributes. Protocol-relative ("//cdn")
# and absolute ("https://") URLs are left alone by the negative lookahead.
_ABS_URL = re.compile(r'(\s(?:href|src|action)=")/(?!/)')
# srcset holds a comma-separated candidate list, not a single URL, so the
# attribute rule above cannot reach it.
_SRCSET = re.compile(r'(\s(?:srcset|imagesrcset)=")([^"]*)"')
# url(/…) in an inline style attribute is a third shape the attribute rule
# misses. Skip absolute, protocol-relative and data: URLs.
_CSS_URL = re.compile(r'url\((?![\'"]?(?:https?:|//|data:))([\'"]?)/')


def apply_base(html):
    """Prefix every root-absolute internal URL with the deployment sub-path.

    Anything that escapes this ends up 404ing silently on a project site, so
    every shape a root-absolute URL can take in the generated HTML is covered
    here — and check.py asserts the result independently.
    """
    if not BASE:
        return html

    def srcset(m):
        candidates = []
        for part in m.group(2).split(","):
            part = part.strip()
            if part.startswith("/") and not part.startswith("//"):
                part = BASE + part
            candidates.append(part)
        return f'{m.group(1)}{", ".join(candidates)}"'

    html = _ABS_URL.sub(r"\1" + BASE + "/", html)
    html = _SRCSET.sub(srcset, html)
    html = _CSS_URL.sub(lambda m: f"url({m.group(1)}{BASE}/", html)
    return html


def build():
    written = []
    for key, (out, title, desc, navkey) in PAGES.items():
        body_file = SRC / f"{key}.html"
        if not body_file.exists():
            raise SystemExit(f"missing body: {body_file}")
        body = body_file.read_text(encoding="utf-8")

        canonical_path = "/" if out == "index.html" else "/" + out.replace("index.html", "")
        if out == "404.html":
            canonical_path = "/404.html"

        html = head(title, desc, canonical_path)
        if navkey == "home":
            html = html.replace("</head>", ORG_SCHEMA + "</head>")
        if out == "404.html":
            html = html.replace(
                '<meta name="robots" content="index, follow">',
                '<meta name="robots" content="noindex, follow">',
            )

        html += header(navkey)
        html += body.rstrip() + "\n\n"
        html += FOOTER

        # Calendly rule: Home -> Steve, all other pages -> Tracey.
        link = SITE["calendly_steve"] if navkey == "home" else SITE["calendly_tracey"]
        html = html.replace("{{CALENDLY}}", link)
        html = html.replace("{{PHONE}}", SITE["phone_display"])
        html = html.replace("{{PHONE_HREF}}", SITE["phone_href"])
        html = html.replace("{{EMAIL}}", SITE["email"])
        html = html.replace("{{FORM_ATTRS}}", form_attrs())
        html = html.replace("{{FORM_HIDDEN}}", form_hidden())

        html = apply_base(html)

        dest = ROOT / out
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
        written.append(out)

    # sitemap
    urls = []
    for key, (out, *_rest) in PAGES.items():
        if out == "404.html":
            continue
        path = "/" if out == "index.html" else "/" + out.replace("index.html", "")
        loc = SITE["origin"] + BASE + path
        if out == "index.html":
            prio = "1.0"
        elif key in ("privacy-policy", "terms-and-conditions", "cookies-policy"):
            prio = "0.3"
        else:
            prio = "0.8"
        urls.append(
            f"  <url><loc>{loc}</loc><changefreq>monthly</changefreq><priority>{prio}</priority></url>"
        )
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    written.append("sitemap.xml")

    # robots.txt — the sitemap URL has to follow the deployment target
    if NOINDEX:
        # Belt and braces. On a project site this file sits at a path crawlers
        # never fetch, so the meta tag is what actually does the work — but on a
        # user site or a custom domain served from Pages this one is read.
        robots = (
            "# Preview deployment — not the production site.\n"
            "User-agent: *\n"
            "Disallow: /\n"
        )
    else:
        # No Disallow for /404.html: blocking it in robots.txt would stop
        # crawlers fetching the page and therefore seeing its noindex, which is
        # the directive that actually keeps it out of the index.
        robots = (
            "User-agent: *\n"
            "Allow: /\n"
            "\n"
            f"Sitemap: {SITE['origin'] + BASE}/sitemap.xml\n"
        )
    (ROOT / "robots.txt").write_text(robots, encoding="utf-8")
    written.append("robots.txt")

    for f in written:
        print("wrote", f)
    print(
        f"origin={SITE['origin']!r} base={BASE!r} "
        f"form={FORM['provider']!r} indexable={not NOINDEX}"
    )


if __name__ == "__main__":
    build()
