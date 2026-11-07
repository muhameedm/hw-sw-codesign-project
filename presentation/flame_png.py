"""Draws the bottom rows of a FlameGraph SVG on white, for use in slides."""
import re, sys, html
from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"

def render(svg, out, rows=6):
    s = open(svg, errors="ignore").read()
    frames = []
    for m in re.finditer(r"<title>(.*?)</title>\s*<rect ([^>]*)/?>", s, re.S):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m[2]))
        if "fill" not in a or not a["fill"].startswith("rgb"): continue
        x, w = a["x"], a["width"]
        frames.append((html.unescape(m[1]).rsplit(" (", 1)[0], float(x.rstrip("%")), float(a["y"]), float(w.rstrip("%")), float(a["height"]),
                       tuple(map(int, re.findall(r"\d+", a["fill"])[:3])), x.endswith("%")))
    ys = sorted({f[2] for f in frames}, reverse=True)[:rows]
    W, R = 1920, 70
    H = len(ys) * R
    k = W / 1200
    img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 30)
    for name, x, y, w, hh, col, pct in frames:
        if y not in ys: continue
        px = (x / 100 * 1180 + 10 if pct else x) * k
        pw = (w / 100 * 1180 if pct else w) * k
        py = H - (ys.index(y) + 1) * R
        d.rectangle([px, py + 2, px + max(pw - 1, 1), py + R - 3], fill=col)
        if pw > 70:
            t = name.split(".lto")[0]
            while t and d.textlength(t, font=font) > pw - 10: t = t[:-1]
            d.text((px + 6, py + 16), t, fill="black", font=font)
    img.save(out)

if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 6)
