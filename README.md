# generedge.com

Static website for GenerEdge, Inc. — replaces the previous WordPress + Elementor
site. Plain HTML/CSS/JS, no runtime dependencies.

**Live: <https://generedgep.github.io/Generedge-Website/>**

Published automatically to GitHub Pages on every push to the default branch,
and deployable to Hostinger as a plain file copy. The Pages build is marked
`noindex` until the site runs on its real domain — see *Deploying*.

> **Working on this with Claude Code? Read [`CLAUDE.md`](./CLAUDE.md) first.**
> It has the project context, the house rules, and what is still outstanding.

---

## Quick start

```bash
# Build the pages from src/
python3 scripts/build.py

# Check structure, links, assets and accessibility
python3 scripts/check.py

# Preview locally
python3 -m http.server 8000
# → http://localhost:8000
```

## Editing

Edit page bodies in `src/`, then re-run `python3 scripts/build.py`.

Shared header, footer, `<head>`, meta tags and the cookie banner live in
`scripts/build.py`. The root-level `.html` files are generated output — editing
them directly gets your work overwritten.

## Pages

| URL | Source |
|---|---|
| `/` | `src/index.html` |
| `/business-loans/` | `src/business-loans.html` |
| `/about-us/` | `src/about-us.html` |
| `/contact-us/` | `src/contact-us.html` |
| `/privacy-policy/` | `src/privacy-policy.html` |
| `/terms-and-conditions/` | `src/terms-and-conditions.html` |
| `/cookies-policy/` | `src/cookies-policy.html` |
| `404` | `src/404.html` |

---

## Where the forms go

The three lead forms (builder application on the home page, business financing
application, and the contact form) all post to whatever is configured in the
`FORM` dict at the top of `scripts/build.py`:

```python
FORM = {
    "provider": "custom",
    "email": "eduardo@generedge.com",   # only used in the visitor's fallback
    "endpoint": "https://script.google.com/macros/s/AKfycbwIcdy5jJyotFhhLvyarHE3Gx8K-_vRUsRwvYX3M092Yodhu-5NM4qS_k7VsZhnxgD9/exec",
    ...
}
```

**Current setup: GenerEdge's own Google Apps Script.** No third-party form
service. Each submission is emailed to `eduardo@generedge.com`, with reply-to
set to the visitor's email, and appended to the Google Sheet
**"GenerEdge — Website Leads"** in the same account.

- **Where the script lives:** script.google.com, signed in as
  `eduardo@generedge.com`, project **"GenerEdge — Website Forms"**. Deployed as
  a Web app: *Execute as: Me*, *Who has access: Anyone* (not "Anyone with a
  Google account" — that would make every visitor's POST fail).
- **Source of truth:** `apps-script/Code.gs` in this repo. Edit it here, paste
  it into the editor, save.
- **Redeploy without changing the URL:** Deploy → **Manage deployments** →
  pencil on the existing deployment → Version: **New version** → Deploy.
  *Never* use "New deployment" for an update: it mints a new `/exec` URL and the
  live site keeps posting to the old version.
- **Change the recipient:** the `TO` constant in `Code.gs`, then redeploy as
  above. `FORM["email"]` in `build.py` is only what the visitor sees in the
  fallback.
- **Health check:** opening the `/exec` URL in a browser returns
  `{"ok":true,"service":"generedge.com forms"}`.

`site.js` posts the JSON with `Content-Type: text/plain;charset=utf-8` and no
other headers for the `custom` provider. That is deliberate: Apps Script cannot
answer a CORS preflight, and `application/json` would trigger one. As a "simple"
request, fetch follows Apps Script's redirect and reads the `200 {"ok":true}`.
A `{"ok":false}` (MailApp failure) counts as a failure.

Without JavaScript the form does a native urlencoded POST to the same URL with
raw field names; the script maps them to the same labels and shows the visitor a
small thank-you page. The `_honey` honeypot is checked server-side on both
paths — if it carries anything the script answers ok and drops the submission.

### Can GitHub Actions handle the form instead?

No. An Action cannot receive an anonymous POST from a visitor's browser, and
every mechanism that could — `repository_dispatch`, the REST API — needs a
token. On a static site that token would have to live in client-side JavaScript,
where anyone can read it and use it against the repo. Sending mail from an
Action has the same problem with SMTP credentials.

Actions run *after* a push, which is why they are right for building and
deploying this site and wrong for receiving form submissions. The Apps Script
web app is the endpoint that holds the "secret" (the Google account) server-side.

### Switching provider

Change `FORM["provider"]` and re-run the build.

| provider | what to set | notes |
|---|---|---|
| `custom` | `endpoint` | **current** — the Apps Script `/exec` URL. Any endpoint taking a `text/plain` body containing JSON and answering 2xx works. |
| `formsubmit` | `email` | no signup, but each address needs a one-time activation click. |
| `web3forms` | `access_key` | free key emailed to you by web3forms.com. The key is public by design — it only permits posting to your own inbox. |
| `formspree` | `endpoint` | your `https://formspree.io/f/xxxx` URL. |

Whatever the provider, **a lead is never silently lost**: if the request fails,
the form shows the phone number and email address plus a "Send it by email
instead" link that opens the visitor's mail client pre-filled with everything
they typed.

Every form also carries a honeypot field, inline `aria-invalid` errors, an
`aria-live` status region, a disabled-while-sending guard, and fires a
`generate_lead` GA event on success.

---

## Deploying

### GitHub Pages (automatic)

**Live at <https://generedgep.github.io/Generedge-Website/>.**

`.github/workflows/deploy-pages.yml` builds and publishes on every push to the
default branch. Other branches get the build and the checks as CI but publish
nothing.

Pages serves the repository from the **`gh-pages`** branch, which holds only
generated output — never edit it by hand, the next deploy replaces it. Building
into a branch rather than a Pages deployment is deliberate: pushing a branch
needs only the `contents: write` permission a workflow can grant itself, while
the deployment API needs Pages to have been switched on by an account with admin
rights first.

The site is served from `https://<user>.github.io/<repo>/`, so the workflow
works out that sub-path from the repository name, builds with `GE_BASE` set to
it, and every internal URL is rewritten to match. Nothing in `src/` needs to
know about it — which is also why nothing in `src/` may hardcode
`https://generedge.com/...`; write root-relative links like `/about-us/`.

github.io builds are marked `noindex, nofollow`. A project site cannot serve a
robots.txt that crawlers will read (they only fetch
`https://<user>.github.io/robots.txt`, which belongs to the user site), so
without the meta tag this would become a fully indexable duplicate of a
financial services site competing with generedge.com in search. The tag flips to
`index, follow` automatically as soon as the build runs against a real domain.

### Moving to generedge.com

1. Add a `CNAME` file at the repo root containing `generedge.com`.
2. Set the domain under **Settings → Pages**.
3. Point the DNS records at GitHub Pages.

`GE_BASE` then resolves to empty, URLs return to domain-root form and the pages
become indexable — all from the CNAME file, with no workflow edit.

### Hostinger

The committed root-level HTML is already built for a domain root, so deployment
is a plain file copy. Either connect this repo under **Websites → Advanced →
Git**, or upload the contents of `_site/` (run `python3 scripts/package.py`
first) to `public_html/`.

`.htaccess` must go up with it — it carries the legacy 301 redirects.

### Build configuration

| Variable | Default | Purpose |
|---|---|---|
| `GE_ORIGIN` | `https://generedge.com` | scheme + host used for canonicals, Open Graph and the sitemap |
| `GE_BASE` | *(empty)* | sub-path the site is served under, e.g. `/Generedge-Website` |

```bash
# what GitHub Pages publishes
GE_ORIGIN=https://generedgep.github.io GE_BASE=/Generedge-Website python3 scripts/build.py
```

---

## Scripts

| Script | Purpose |
|---|---|
| `scripts/build.py` | assembles `src/` + shared chrome into the root HTML, `sitemap.xml` and `robots.txt` |
| `scripts/check.py` | structure, links, referenced assets, forms and accessibility checks |
| `scripts/package.py` | copies the publishable subset into `_site/` |
| `scripts/fetch-assets.sh` | re-pulls the original images from the old WordPress site |
| `scripts/make-social-images.py` | regenerates `og-default.png` and `apple-touch-icon.png` (needs Pillow; optional) |

---

## Still outstanding before the domain moves

- [x] Lead forms delivering — via the GenerEdge Apps Script (see "Where the forms go")
- [ ] Set the real GA4 measurement ID in `SITE["ga_id"]` — analytics stay off until then
- [ ] Tracey signs off on the copy flagged in `CLAUDE.md` §4 — including the
      SMS consent checkbox becoming optional, the 4 msgs/mo frequency, and the
      removal of the "Over $15 million" fee tier
- [ ] Legal review of the three policy pages
- [ ] Confirm `handshake.jpg` stock photo licensing
- [ ] DNS: replicate MX/SPF/DKIM/DMARC **before** switching nameservers
- [ ] Submit `sitemap.xml` in Google Search Console

Done during the rebuild: real images pulled off WordPress, branded social card
and touch icon generated, forms connected, GitHub Pages deployment wired up,
legacy 301s written. A designer can replace `og-default.png` and
`apple-touch-icon.png` at any time — nothing else depends on how they look.

## Browser support

Modern evergreen browsers. Degrades gracefully: without JavaScript, all content
and navigation still work — only the scroll reveals, animated counters, mobile
menu and client-side form validation are lost.
