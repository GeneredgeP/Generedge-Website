#!/usr/bin/env python3
"""Generate assets/img/og-default.png and assets/img/apple-touch-icon.png.

    pip install Pillow && python3 scripts/make-social-images.py

Optional one-off tool — the site itself has no build dependencies, and the two
PNGs it writes are committed. Re-run it only if the branding changes, or replace
its output with hand-designed artwork.

  og-default.png     1200x630  the card social networks show when a link to the
                               site is shared. Uses the real logo unmodified.
  apple-touch-icon.png 180x180 iOS home-screen icon, matching favicon.svg.
"""

import pathlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG = ROOT / "assets" / "img"
FONTS = ROOT / "scripts" / "fonts"

# Brand tokens — same values as the CSS custom properties in assets/css/site.css.
FOREST = (16, 76, 47)
DEEP = (8, 40, 26)
GREEN = (13, 132, 61)
GLOW = (76, 215, 135)
STONE = (242, 245, 242)
MUTED = (74, 90, 81)
PALE = (207, 229, 217)
WHITE = (255, 255, 255)

SS = 3  # supersample factor, downscaled at the end for clean edges


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def wrap(d, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if d.textlength(trial, font=fnt) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def og_card():
    """Shared by every page. Since 11/19 (Steve): no "Approval-Ready Borrowing"
    and no business-loan tagline; the home hero's joint-venture titles instead,
    next to the site's construction photo."""
    W, H = 1200, 630
    band = 104
    field = H - band
    im = Image.new("RGB", (W * SS, H * SS), WHITE)
    d = ImageDraw.Draw(im)

    # Photo on the right, its left edge cut as the logo's forward chevron.
    x0, tip = 640, 700
    pw, ph = W - x0 + 80, field
    photo = Image.open(IMG / "mf-construction.jpg").convert("RGB")
    # Crop to the panel's shape around the crane and the framed top floor.
    target = pw / ph
    cw = round(photo.height * target)
    left = min(max(330, 0), photo.width - cw)
    photo = photo.crop((left, 0, left + cw, photo.height)).resize((pw * SS, ph * SS), Image.LANCZOS)
    mask = Image.new("L", photo.size, 0)
    md = ImageDraw.Draw(mask)
    off = x0 - 80  # photo is pasted at this x
    pts = [(x0 - off, 0), (pw, 0), (pw, ph), (x0 - off, ph), (tip - off, ph / 2)]
    md.polygon([(x * SS, y * SS) for x, y in pts], fill=255)
    im.paste(photo, (off * SS, 0), mask)
    # Glow stroke along the chevron edge.
    d.line([(x0 * SS, 0), (tip * SS, field / 2 * SS), (x0 * SS, field * SS)],
           fill=GLOW, width=7 * SS, joint="curve")

    # Logo: chevron + "GenerEdge" wordmark cut from logo.png (800x233), without
    # the "Approval-Ready Borrowing" lines.
    src = Image.open(IMG / "logo.png").convert("RGBA")
    chevron = src.crop((4, 5, 122, 198))
    word = src.crop((146, 4, 553, 92))
    ch_h = round(word.height * 1.25)
    chevron = chevron.resize((round(chevron.width * ch_h / chevron.height), ch_h), Image.LANCZOS)
    gap = 26
    lock = Image.new("RGBA", (chevron.width + gap + word.width, ch_h), (0, 0, 0, 0))
    lock.paste(chevron, (0, 0), chevron)
    lock.paste(word, (chevron.width + gap, (ch_h - word.height) // 2), word)
    lw = 290 * SS
    lh = round(lw * lock.height / lock.width)
    lock = lock.resize((lw, lh), Image.LANCZOS)
    im.paste(lock, (72 * SS, 62 * SS), lock)

    kicker = font("Figtree-600.ttf", 19 * SS)
    headline = font("Archivo-800.ttf", 40 * SS)
    sub = font("Figtree-600.ttf", 27 * SS)
    small = font("Figtree-600.ttf", 25 * SS)
    mark = font("Archivo-800.ttf", 27 * SS)

    y = 62 + 62 + 34
    d.text((72 * SS, y * SS), "M U L T I - F A M I L Y   J O I N T   V E N T U R E S",
           font=kicker, fill=GREEN)
    y += 40
    for line in wrap(d, "Connecting Multi-Family Developers and Landowners with Development Partners",
                     headline, 520 * SS):
        d.text((72 * SS, y * SS), line, font=headline, fill=FOREST)
        y += 50
    y += 14
    d.rectangle([72 * SS, y * SS, 120 * SS, (y + 5) * SS], fill=GLOW)
    y += 22
    d.text((72 * SS, y * SS), "Financing Multi-Family Development", font=sub, fill=GREEN)

    # Forest band across the foot of the card.
    d.rectangle([0, field * SS, W * SS, H * SS], fill=FOREST)
    d.rectangle([0, field * SS, W * SS, (field + 6) * SS], fill=GLOW)
    d.text((72 * SS, (field + 40) * SS), "generedge.com", font=mark, fill=WHITE)
    # Not "Underwriting": GenerEdge is not a lender.
    right = "Joint ventures  ·  Development financing  ·  Business loans"
    rw = d.textlength(right, font=small)
    d.text((W * SS - 72 * SS - rw, (field + 43) * SS), right, font=small, fill=PALE)

    im = im.resize((W, H), Image.LANCZOS)
    out = IMG / "og-default.png"
    im.save(out, optimize=True)
    print(f"wrote {out.relative_to(ROOT)} ({W}x{H}, {out.stat().st_size/1024:.0f} KB)")


def touch_icon():
    # Same marks as assets/img/favicon.svg, on its 64-unit grid. iOS applies its
    # own corner mask, so this is drawn full-bleed and square.
    S = 180
    k = S * SS / 64.0
    im = Image.new("RGB", (S * SS, S * SS), DEEP)
    d = ImageDraw.Draw(im)
    # The forward chevron of the logo mark, stroked with round caps and joins.
    pts = [(23 * k, 17 * k), (38 * k, 32 * k), (23 * k, 47 * k)]
    w = round(9 * k)
    d.line(pts, fill=GLOW, width=w, joint="curve")
    for x, y in pts:
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=GLOW)
    im = im.resize((S, S), Image.LANCZOS)
    out = IMG / "apple-touch-icon.png"
    im.save(out, optimize=True)
    print(f"wrote {out.relative_to(ROOT)} ({S}x{S}, {out.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    og_card()
    touch_icon()
