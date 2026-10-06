"""
Street-art asset generator for the GitHub profile README.
All type is converted to outlines so it renders identically everywhere
(GitHub serves these as <img>, which blocks web fonts).
"""
import os, random, math
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

OUT = os.path.join(os.path.dirname(__file__), "..", "assets")
os.makedirs(OUT, exist_ok=True)

CN_BOLD = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheroscn-bold.otf"
CN_BOLDIT = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheroscn-bolditalic.otf"

WALL = "#000000"
CHALK = "#F4F4F4"
PINK = "#FF2E88"
CONCRETE = "#1C1C1C"
ASH = "#8A8A8A"


class Face:
    def __init__(self, path):
        self.f = TTFont(path)
        self.gs = self.f.getGlyphSet()
        self.cmap = self.f.getBestCmap()
        self.upm = self.f["head"].unitsPerEm
        self.hmtx = self.f["hmtx"]

    def width(self, text, size, tracking=0.0):
        s = size / self.upm
        w = 0
        for ch in text:
            g = self.cmap.get(ord(ch))
            if g is None:
                continue
            w += self.hmtx[g][0] * s + tracking * size
        return w - tracking * size

    def path(self, text, size, x, y, tracking=0.0, anchor="start", jitter=0.0, seed=1):
        """Return an SVG path d-string for text. jitter = per-glyph baseline/rotation wobble (hand-cut stencil feel)."""
        rnd = random.Random(seed)
        s = size / self.upm
        total = self.width(text, size, tracking)
        if anchor == "middle":
            x -= total / 2
        elif anchor == "end":
            x -= total
        out = []
        cx = x
        for ch in text:
            g = self.cmap.get(ord(ch))
            if g is None:
                continue
            adv = self.hmtx[g][0] * s
            dy = rnd.uniform(-1, 1) * jitter * size
            rot = math.radians(rnd.uniform(-1, 1) * jitter * 40)
            pen = SVGPathPen(self.gs)
            # glyph space -> svg: scale, flip y, rotate around glyph centre, translate
            c, sn = math.cos(rot), math.sin(rot)
            gx = adv / 2
            # matrix = T(cx,y+dy) * R(rot about gx) * S(s,-s)
            a, b, cc, d = s * c, s * sn, s * sn, -s * c
            e = cx + gx - gx * c
            f = y + dy - gx * sn
            tp = TransformPen(pen, (a, b, cc, d, e, f))
            self.gs[g].draw(tp)
            out.append(pen.getCommands())
            cx += adv + tracking * size
        return " ".join(out)


BOLD = Face(CN_BOLD)
BOLDIT = Face(CN_BOLDIT)


def rough_poly(x0, y0, x1, y1, seed, amp=4.0, step=14, torn_ends=False):
    """Ragged-edge rectangle (torn paper / tape)."""
    r = random.Random(seed)
    pts = []
    n = max(2, int((x1 - x0) / step))
    for i in range(n + 1):
        pts.append((x0 + (x1 - x0) * i / n, y0 + r.uniform(-amp, amp) * 0.5))
    m = max(2, int((y1 - y0) / (step * 0.6)))
    for i in range(1, m):
        pts.append((x1 + r.uniform(-amp, amp) * (2.2 if torn_ends else 0.6), y0 + (y1 - y0) * i / m))
    for i in range(n, -1, -1):
        pts.append((x0 + (x1 - x0) * i / n, y1 + r.uniform(-amp, amp) * 0.5))
    for i in range(m - 1, 0, -1):
        pts.append((x0 + r.uniform(-amp, amp) * (2.2 if torn_ends else 0.6), y0 + (y1 - y0) * i / m))
    return "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts) + " Z"


def splatter(cx, cy, spread, n, seed, color, rmax=3.2):
    r = random.Random(seed)
    dots = []
    for _ in range(n):
        ang = r.uniform(0, 2 * math.pi)
        dist = abs(r.gauss(0, spread))
        rad = max(0.4, r.uniform(0.3, rmax) * (1 - min(dist / (spread * 3), 0.85)))
        dots.append(f'<circle cx="{cx + math.cos(ang) * dist:.1f}" cy="{cy + math.sin(ang) * dist * 0.6:.1f}" r="{rad:.2f}" fill="{color}"/>')
    return "".join(dots)


def drips(xs, y, seed, color, maxlen=70, width=(3, 7), cls="drip"):
    r = random.Random(seed)
    out = []
    for i, x in enumerate(xs):
        w = r.uniform(*width)
        L = r.uniform(maxlen * 0.35, maxlen)
        delay = 0.6 + i * 0.12 + r.uniform(0, 0.4)
        top = w * 1.9          # paint pools wide where it leaves the letter
        neck = w * 0.55
        bulb = w * 0.85
        d = (f"M{x - top / 2:.1f},{y:.1f} "
             f"C{x - top / 2:.1f},{y + L * 0.18:.1f} {x - neck / 2:.1f},{y + L * 0.25:.1f} {x - neck / 2:.1f},{y + L * 0.55:.1f} "
             f"L{x - neck / 2:.1f},{y + L - bulb:.1f} "
             f"A{bulb:.1f},{bulb * 1.1:.1f} 0 1 0 {x + neck / 2:.1f},{y + L - bulb:.1f} "
             f"L{x + neck / 2:.1f},{y + L * 0.55:.1f} "
             f"C{x + neck / 2:.1f},{y + L * 0.25:.1f} {x + top / 2:.1f},{y + L * 0.18:.1f} {x + top / 2:.1f},{y:.1f} Z")
        out.append(f'<path class="{cls}" style="animation-delay:{delay:.2f}s" d="{d}" fill="{color}"/>')
    return "".join(out)


COMMON_DEFS = f"""
<filter id="grain" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" seed="7" result="n"/>
  <feColorMatrix type="saturate" values="0" in="n" result="g"/>
  <feComponentTransfer in="g"><feFuncA type="table" tableValues="0 0.16"/></feComponentTransfer>
</filter>
<filter id="stain" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.008 0.02" numOctaves="4" seed="3" result="n"/>
  <feColorMatrix type="matrix" in="n" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 -1.3 0.62"/>
</filter>
<filter id="rough" x="-5%" y="-20%" width="110%" height="140%">
  <feTurbulence type="turbulence" baseFrequency="0.045" numOctaves="2" seed="11" result="t"/>
  <feDisplacementMap in="SourceGraphic" in2="t" scale="7" xChannelSelector="R" yChannelSelector="G"/>
</filter>
<filter id="paint" x="-6%" y="-25%" width="112%" height="150%">
  <feTurbulence type="fractalNoise" baseFrequency="0.06" numOctaves="2" seed="4" result="t"/>
  <feDisplacementMap in="SourceGraphic" in2="t" scale="5" xChannelSelector="R" yChannelSelector="G" result="d"/>
  <feTurbulence type="fractalNoise" baseFrequency="0.32" numOctaves="2" seed="9" result="wear"/>
  <feColorMatrix in="wear" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -18 13.5" result="wearA"/>
  <feComposite in="d" in2="wearA" operator="in"/>
</filter>
<filter id="overspray" x="-10%" y="-40%" width="120%" height="180%">
  <feGaussianBlur stdDeviation="9"/>
</filter>
"""


def anim_css(extra=""):
    return f"""<style>
  .drip {{ transform-box: fill-box; transform-origin: 50% 0; transform: scaleY(0);
          animation: run 2.6s cubic-bezier(.3,.0,.2,1) forwards; }}
  @keyframes run {{ to {{ transform: scaleY(1); }} }}
  {extra}
  @media (prefers-reduced-motion: reduce) {{ .drip {{ animation: none; transform: scaleY(1); }} }}
</style>"""


# ---------------------------------------------------------------- HEADER
def header():
    W, H = 1200, 470
    name = "HRISHIKESH"
    big = 196
    nm_y = 268
    nm_w = BOLD.width(name, big, tracking=0.01)
    nm_x0 = (W - nm_w) / 2

    name_d = BOLD.path(name, big, W / 2, nm_y, tracking=0.01, anchor="middle", jitter=0.018, seed=21)
    wake_d = BOLD.path("WAKE UP, SAMURAI.", 30, 92, 104, tracking=0.16, jitter=0.01, seed=3)
    burn_d = BOLDIT.path("we've got a city to burn", 52, W / 2 + 40, 352, tracking=0.0, anchor="middle", jitter=0.03, seed=8)
    role_d = BOLD.path("FULL STACK DEVELOPER  /  AI ENGINEER", 19, W - 170, 420, tracking=0.2, anchor="end", seed=2)
    surname_d = BOLD.path("GAVAI", 30, 92, 420, tracking=0.5, seed=5)

    # drips under selected letters of the name
    letter_x = []
    cx = nm_x0
    s = big / BOLD.upm
    for ch in name:
        g = BOLD.cmap[ord(ch)]
        adv = BOLD.hmtx[g][0] * s
        letter_x.append((cx, adv))
        cx += adv + 0.01 * big
    # (letter index, horizontal position inside the glyph) — always on a stem/bowl, never in a counter
    picks = [(0, 0.17), (2, 0.5), (3, 0.52), (6, 0.2), (9, 0.83)]
    drip_x = [letter_x[i][0] + letter_x[i][1] * f for i, f in picks]
    white_drips = drips(drip_x, nm_y - 4, 12, CHALK, maxlen=78, width=(4, 8))
    pink_drips = drips([430, 540, 705, 812], 362, 31, PINK, maxlen=52, width=(3, 5))

    tape = lambda x, y, w, h, rot, seed: (
        f'<path d="{rough_poly(x, y, x + w, y + h, seed, amp=5, step=9, torn_ends=True)}" '
        f'fill="#CFCFC9" fill-opacity="0.82" transform="rotate({rot} {x + w / 2} {y + h / 2})"/>'
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Hrishikesh Gavai. Wake up, Samurai. We've got a city to burn.">
<title>Hrishikesh Gavai — wake up, samurai</title>
<defs>{COMMON_DEFS}
<clipPath id="poster"><path d="{rough_poly(26, 26, W - 26, H - 26, 77, amp=9, step=11)}"/></clipPath>
</defs>
{anim_css()}
<g clip-path="url(#poster)">
  <rect width="{W}" height="{H}" fill="{WALL}"/>
  <rect width="{W}" height="{H}" fill="{CONCRETE}" filter="url(#stain)" opacity="0.38"/>
  <rect width="{W}" height="{H}" filter="url(#grain)"/>
  <!-- buffed-out old tags, ghosted under the new piece -->
  <path d="{BOLD.path('NSK', 260, 1010, 330, tracking=-0.02, anchor='middle', jitter=0.05, seed=40)}" fill="#1F1F1F" filter="url(#rough)" transform="rotate(-8 1010 260)"/>
  <path d="{BOLD.path('404', 150, 200, 250, anchor='middle', jitter=0.06, seed=41)}" fill="#1C1C1C" filter="url(#rough)" transform="rotate(6 200 200)"/>

  <path d="{wake_d}" fill="{ASH}" filter="url(#paint)"/>
  <rect x="92" y="118" width="210" height="4" fill="{PINK}" filter="url(#rough)"/>

  <g transform="rotate(-2.2 {W / 2} {nm_y})">
    <path d="{name_d}" fill="{CHALK}" filter="url(#overspray)" opacity="0.28"/>
    <path d="{name_d}" fill="{CHALK}" filter="url(#paint)"/>
    {white_drips}
  </g>

  <g transform="rotate(-4 {W / 2} 340)">
    <path d="{burn_d}" fill="{PINK}" filter="url(#overspray)" opacity="0.45"/>
    <path d="{burn_d}" fill="{PINK}" filter="url(#rough)"/>
    {pink_drips}
  </g>
  {splatter(1040, 150, 26, 70, 9, PINK)}
  {splatter(1110, 330, 18, 30, 10, CHALK, rmax=2.0)}

  <path d="{surname_d}" fill="{CHALK}" filter="url(#paint)"/>
  <path d="{role_d}" fill="{ASH}" filter="url(#paint)"/>
</g>
{tape(10, 30, 120, 34, -34, 1)}
{tape(W - 132, 26, 120, 34, 31, 2)}
{tape(W - 140, H - 70, 124, 34, -28, 3)}
</svg>"""
    open(f"{OUT}/header.svg", "w").write(svg)


# ---------------------------------------------------------------- SECTION LABELS (black gaffer tape)
def label(slug, text, seed, rot):
    size = 40
    tw = BOLD.width(text, size, tracking=0.14)
    W = int(tw + 150)
    H = 96
    d = BOLD.path(text, size, W / 2, 63, tracking=0.14, anchor="middle", jitter=0.012, seed=seed)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{text.title()}">
<title>{text.title()}</title>
<defs>{COMMON_DEFS}
<clipPath id="tp"><path d="{rough_poly(22, 16, W - 22, H - 16, seed, amp=6, step=8, torn_ends=True)}"/></clipPath></defs>
<g transform="rotate({rot} {W / 2} {H / 2})">
  <g clip-path="url(#tp)">
    <rect width="{W}" height="{H}" fill="#0A0A0A"/>
    <rect width="{W}" height="{H}" filter="url(#grain)"/>
    <rect x="0" y="22" width="{W}" height="1.2" fill="#2E2E2E"/>
    <rect x="0" y="{H - 23}" width="{W}" height="1.2" fill="#2E2E2E"/>
  </g>
  <path d="{d}" fill="{CHALK}" filter="url(#paint)"/>
  <rect x="{W - 58}" y="29" width="10" height="10" fill="{PINK}" transform="rotate(12 {W - 53} 34)"/>
</g>
</svg>"""
    open(f"{OUT}/label-{slug}.svg", "w").write(svg)


# ---------------------------------------------------------------- CATEGORY STICKERS (white vinyl, marker text)
def sticker(slug, text, seed, rot):
    size = 24
    tw = BOLD.width(text, size, tracking=0.12)
    W = int(tw + 70)
    H = 58
    d = BOLD.path(text, size, W / 2, 38, tracking=0.12, anchor="middle", jitter=0.02, seed=seed)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{text.title()}">
<title>{text.title()}</title>
<defs>{COMMON_DEFS}</defs>
<g transform="rotate({rot} {W / 2} {H / 2})">
  <path d="{rough_poly(10, 10, W - 10, H - 10, seed, amp=3, step=7)}" fill="#000" opacity="0.35" transform="translate(3 3)"/>
  <path d="{rough_poly(10, 10, W - 10, H - 10, seed, amp=3, step=7)}" fill="{CHALK}"/>
  <path d="{d}" fill="#000" filter="url(#rough)"/>
  <circle cx="22" cy="20" r="3.4" fill="{PINK}"/>
</g>
</svg>"""
    open(f"{OUT}/sticker-{slug}.svg", "w").write(svg)


# ---------------------------------------------------------------- BRUSH DIVIDER (theme-aware pair)
def divider(variant):
    W, H = 1000, 60
    ink = CHALK if variant == "dark" else "#111111"
    r = random.Random(14)
    # variable-width brush: upper edge left->right, lower edge right->left
    n = 60
    top, bot = [], []
    for i in range(n + 1):
        t = i / n
        x = 40 + t * (W - 80)
        thick = 9 * math.sin(math.pi * min(1, t * 1.15)) ** 0.6 + 1.5
        yc = 30 + math.sin(t * 5.3) * 3 + r.uniform(-0.8, 0.8)
        top.append((x, yc - thick / 2 - r.uniform(0, 1.6)))
        bot.append((x, yc + thick / 2 + r.uniform(0, 1.6)))
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in top) + " L" + " L".join(
        f"{x:.1f},{y:.1f}" for x, y in reversed(bot)) + " Z"
    # dry-brush streaks
    streaks = "".join(
        f'<rect x="{r.uniform(60, W - 140):.0f}" y="{r.uniform(24, 34):.1f}" width="{r.uniform(40, 160):.0f}" height="0.9" fill="{"#000" if variant == "dark" else "#fff"}" opacity="0.55"/>'
        for _ in range(9))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="divider">
<defs>{COMMON_DEFS}<clipPath id="b"><path d="{d}"/></clipPath></defs>
<g filter="url(#rough)">
  <path d="{d}" fill="{ink}"/>
  <g clip-path="url(#b)">{streaks}</g>
</g>
{splatter(W - 70, 26, 14, 28, 3, PINK, rmax=2.6)}
{splatter(70, 34, 10, 14, 4, ink, rmax=1.8)}
</svg>"""
    open(f"{OUT}/divider-{variant}.svg", "w").write(svg)


# ---------------------------------------------------------------- FOOTER
def footer():
    W, H = 1200, 230
    line1 = BOLD.path("THANKS FOR STOPPING BY THE WALL", 54, W / 2, 112, tracking=0.06, anchor="middle", jitter=0.012, seed=61)
    line2 = BOLDIT.path("now go make some noise", 34, W / 2 + 60, 168, anchor="middle", jitter=0.03, seed=62)
    sig = BOLD.path("H.G.", 26, W - 100, 190, tracking=0.2, anchor="end", seed=63)
    pdrips = drips([520, 655, 760], 176, 70, PINK, maxlen=34, width=(2.5, 4))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Thanks for stopping by the wall. Now go make some noise.">
<title>Thanks for stopping by the wall</title>
<defs>{COMMON_DEFS}<clipPath id="f"><path d="{rough_poly(26, 20, W - 26, H - 20, 91, amp=9, step=11)}"/></clipPath></defs>
{anim_css()}
<g clip-path="url(#f)">
  <rect width="{W}" height="{H}" fill="{WALL}"/>
  <rect width="{W}" height="{H}" fill="{CONCRETE}" filter="url(#stain)" opacity="0.38"/>
  <rect width="{W}" height="{H}" filter="url(#grain)"/>
  <path d="{line1}" fill="{CHALK}" filter="url(#paint)" transform="rotate(-1.2 {W / 2} 100)"/>
  <g transform="rotate(-3 {W / 2} 160)">
    <path d="{line2}" fill="{PINK}" filter="url(#overspray)" opacity="0.45"/>
    <path d="{line2}" fill="{PINK}" filter="url(#rough)"/>
    {pdrips}
  </g>
  <path d="{sig}" fill="{ASH}" filter="url(#paint)"/>
  {splatter(140, 70, 20, 40, 66, PINK)}
</g>
</svg>"""
    open(f"{OUT}/footer.svg", "w").write(svg)


if __name__ == "__main__":
    header()
    for slug, text, seed, rot in [
        ("whoami", "WHO'S BEHIND THE CAN", 101, -1.4),
        ("arsenal", "THE ARSENAL", 102, 1.2),
        ("stats", "WALL STATS", 103, -1.0),
        ("now", "ON THE WALL RIGHT NOW", 104, 1.5),
    ]:
        label(slug, text, seed, rot)
    for slug, text, seed, rot in [
        ("languages", "LANGUAGES", 201, -2.5),
        ("web", "WEB", 202, 2.0),
        ("databases", "DATABASES", 203, -1.5),
        ("cloud", "CLOUD + DEVOPS", 204, 2.4),
        ("ai", "AI / ML + DATA", 205, -2.2),
        ("gamedev", "GAME DEV", 206, 1.8),
    ]:
        sticker(slug, text, seed, rot)
    divider("dark")
    divider("light")
    footer()
    print(sorted(os.listdir(OUT)))
