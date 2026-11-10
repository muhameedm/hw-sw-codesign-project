"""Builds presentation.pptx from the project's own files.

pyflate slides fill in automatically once these exist in the repository root:
pyflate_orig.json, pyflate_opt.json, pyflate_orig_perf_report.txt,
pyflate_orig.svg, pyflate_opt.svg.
"""
import csv, json, os, re, shutil, statistics, zipfile
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE as X, XL_LABEL_POSITION as LP
from pptx.enum.shapes import MSO_SHAPE as S
from pptx.enum.text import MSO_ANCHOR as V, PP_ALIGN as A
from pptx.util import Inches as I, Pt
import flame_png

ROOT = ".."
OUT = "presentation.pptx"
INK, TEAL, AMBER, GREY, RED = "1A2230", "11806F", "D9801F", "5C6675", "BE3B2A"
TINT, TEALT, AMBERT, REDT, LINE, WHITE = "F1F3F6", "DDF1EE", "FBEBD6", "FBE6E2", "D5DAE1", "FFFFFF"
MONO = "Courier New"

def rgb(h): return RGBColor.from_string(h)
def path(n): return os.path.join(ROOT, n)

def values(name):
    d = json.load(open(path(name)))
    return [v for r in d["benchmarks"][0]["runs"] for v in r.get("values", [])]

def stats(name):
    v = values(name)
    return statistics.mean(v), statistics.stdev(v), len(v)

def self_rows(report, n=None):
    rows = []
    for l in open(path(report), errors="ignore"):
        m = re.match(r"\s+([\d.]+)%\s+python3\S*\s+(\S+)\s+\[\.\]\s+(\S+)", l)
        if m: rows.append((float(m[1]), m[3].split(".lto")[0]))
    rows.sort(reverse=True)
    return rows[:n] if n else rows

def flame_pct(svg, name):
    t = open(path(svg), errors="ignore").read()
    vals = [float(m) for m in re.findall(re.escape(name) + r"[^<(]*\([\d,]+ samples?, ([\d.]+)%\)", t)]
    return max(vals) if vals else 0.0

def src(rel, start, end):
    L = open(path(rel)).read().split("\n")
    return [(i + 1, L[i]) for i in range(start - 1, end)]

def find_line(rel, text):
    for i, l in enumerate(open(path(rel)).read().split("\n")):
        if text in l: return i + 1
    raise ValueError(text)

def counters(n):
    r = {}
    for row in csv.reader(open(path(f"perf_stat/stat_{n}.csv"))):
        if len(row) > 3 and row[0][:1].isdigit(): r[row[2]] = float(row[0])
    r["ipc"] = r["instructions"] / r["cycles"]
    r["cm"] = 100 * r["cache-misses"] / r["cache-references"]
    r["bm"] = 100 * r["branch-misses"] / r["branches"]
    return r

PF = None
if os.path.exists(path("pyflate_orig.json")) and os.path.exists(path("pyflate_opt.json")):
    o, od, on = stats("pyflate_orig.json"); p, pd, pn = stats("pyflate_opt.json")
    PF = dict(o=o, od=od, n=on, p=p, pd=pd, speed=o / p, red=100 * (o - p) / o)
PF_SVG = os.path.exists(path("pyflate_orig.svg")) and os.path.exists(path("pyflate_opt.svg"))
PF_REPORT = os.path.exists(path("pyflate_orig_perf_report.txt"))

for n in ("raytrace_orig", "raytrace_opt") + (("pyflate_orig", "pyflate_opt") if PF_SVG else ()):
    flame_png.render(path(n + ".svg"), f"assets/{n}.png", 6)

prs = Presentation()
prs.slide_width, prs.slide_height = I(13.333), I(7.5)
LAYOUT = prs.slide_layouts[5]

def add_runs(p, runs, size, color, bold, font):
    for r in ([runs] if isinstance(runs, (str, tuple)) else runs):
        t, o = (r, {}) if isinstance(r, str) else r
        run = p.add_run(); run.text = t
        run.font.size = Pt(o.get("size", size)); run.font.bold = o.get("bold", bold)
        run.font.color.rgb = rgb(o.get("color", color))
        f = o.get("font", font)
        if f: run.font.name = f

def text(s, x, y, w, h, paras, size=16, color=INK, align=None, bold=False, font=None, anchor=V.TOP, after=6, bullets=False):
    b = s.shapes.add_textbox(I(x), I(y), I(w), I(h)); tf = b.text_frame
    tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, r in enumerate(paras if isinstance(paras, list) else [paras]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if align: p.alignment = align
        p.space_after = Pt(after)
        if bullets:
            pPr = p._p.get_or_add_pPr(); pPr.set("marL", "228600"); pPr.set("indent", "-228600")
            from lxml import etree
            bu = etree.SubElement(pPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}buChar"); bu.set("char", "•")
        add_runs(p, r, size, color, bold, font)
    return b

def box(s, x, y, w, h, fill=TINT, shape=S.ROUNDED_RECTANGLE, line=None, adj=.05):
    b = s.shapes.add_shape(shape, I(x), I(y), I(w), I(h))
    if shape == S.ROUNDED_RECTANGLE: b.adjustments[0] = adj
    b.fill.solid(); b.fill.fore_color.rgb = rgb(fill)
    if line: b.line.color.rgb = rgb(line); b.line.width = Pt(1.25)
    else: b.line.fill.background()
    b.shadow.inherit = False
    return b

def tag(s, x, y, w, h, t, fill=TINT, color=INK, size=14, bold=True, line=None, shape=S.ROUNDED_RECTANGLE):
    b = box(s, x, y, w, h, fill, shape, line, .1); tf = b.text_frame
    tf.word_wrap = True; tf.vertical_anchor = V.MIDDLE
    tf.margin_left = tf.margin_right = I(.06); tf.margin_top = tf.margin_bottom = I(.02)
    for i, r in enumerate(t if isinstance(t, list) else [t]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = A.CENTER; add_runs(p, r, size, color, bold, None)
    return b

def arrow(s, x, y, w=.3, h=.24, fill=GREY, shape=S.RIGHT_ARROW): return box(s, x, y, w, h, fill, shape)

def card(s, x, y, w, h, head, rows, fill=TINT, hc=TEAL, size=15, hs=18):
    box(s, x, y, w, h, fill)
    text(s, x + .24, y + .18, w - .48, .4, head, hs, hc, bold=True)
    text(s, x + .24, y + .68, w - .48, h - .8, rows, size, bullets=True, after=5)

def stat(s, x, y, w, h, big, small, color=TEAL, fill=TINT, size=34):
    box(s, x, y, w, h, fill)
    text(s, x + .22, y + .14, w - .4, h * .55, big, size, color, bold=True)
    text(s, x + .22, y + h - .46, w - .4, .4, small, 13, GREY)

def banner(s, y, t, h=.62, x=.6, w=12.13):
    b = box(s, x, y, w, h, INK, adj=.12); tf = b.text_frame; tf.word_wrap = True
    tf.vertical_anchor = V.MIDDLE; tf.margin_left = I(.28)
    add_runs(tf.paragraphs[0], t, 17, WHITE, True, None)

def code(s, x, y, w, h, title, rows, size=13, note=None):
    """rows: (line number, text) pairs. A leading '!' marks a highlighted line."""
    box(s, x, y, w, h, INK, adj=.03)
    text(s, x + .2, y + .13, w - .4, .28, title, 12, "AEB8C6", font=MONO)
    if note: text(s, x + .2, y + .13, w - .4, .28, note, 12, "F0B266", align=A.RIGHT, bold=True)
    paras = []
    for n, t in rows:
        hot = t.startswith("!"); t = t[1:] if hot else t
        num = f"{n:>3}  " if n else ""
        paras.append([(num, {"color": "7D8796", "font": MONO}), (t or " ", {"color": "FFC47A" if hot else "E8ECF2", "bold": hot, "font": MONO})])
    text(s, x + .2, y + .5, w - .4, h - .6, paras, size, after=0)

def table(s, x, y, w, cols, rows, size=14, rh=.42, head=True, align=None, colors=None):
    """cols: widths. rows: first row is the header. colors: {(r,c): hex}."""
    g = s.shapes.add_table(len(rows), len(cols), I(x), I(y), I(w), I(rh * len(rows)))
    t = g.table
    t._tbl.tblPr.set("bandRow", "0"); t._tbl.tblPr.set("firstRow", "0")
    for i, c in enumerate(cols): t.columns[i].width = I(c)
    for r, row in enumerate(rows):
        t.rows[r].height = I(rh)
        for c, v in enumerate(row):
            cell = t.cell(r, c); cell.vertical_anchor = V.MIDDLE
            cell.margin_left = cell.margin_right = I(.1); cell.margin_top = cell.margin_bottom = I(.03)
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(INK if r == 0 and head else (TINT if r % 2 == 0 else WHITE))
            p = cell.text_frame.paragraphs[0]
            if align and align[c]: p.alignment = align[c]
            col = WHITE if r == 0 and head else (colors or {}).get((r, c), INK)
            add_runs(p, str(v), size, col, r == 0 and head, None)
    return g

PART = [""]
def slide(title, notes, dark=False):
    s = prs.slides.add_slide(LAYOUT); t = s.shapes.title
    t.left, t.top, t.width, t.height = I(.6), I(.34), I(12.13), I(.8)
    tf = t.text_frame; tf.word_wrap = True; tf.vertical_anchor = V.MIDDLE
    tf.margin_left = tf.margin_right = 0
    p = tf.paragraphs[0]; p.alignment = A.LEFT
    add_runs(p, title, 30, WHITE if dark else INK, True, None)
    if dark:
        s.background.fill.solid(); s.background.fill.fore_color.rgb = rgb(INK)
    else:
        if PART[0]: text(s, .6, 7.03, 6, .25, PART[0], 11, GREY)
        text(s, 12.13, 7.03, .6, .25, str(len(prs.slides)), 11, GREY, A.RIGHT)
    s.notes_slide.notes_text_frame.text = notes
    return s

def divider(label, name, sub, notes):
    s = slide(name, notes, True)
    t = s.shapes.title; t.top, t.height = I(3.0), I(1.1)
    t.text_frame.paragraphs[0].runs[0].font.size = Pt(52)
    text(s, .6, 2.35, 8, .5, label, 22, "F0B266", bold=True)
    text(s, .6, 4.2, 11, .5, sub, 20, "C9D0DA")

def pending(s, x, y, w, h, t="Filled in when the VM run finishes"):
    tag(s, x, y, w, h, t, TINT, GREY, 16, False, LINE)

C, R_, L_ = A.CENTER, A.RIGHT, None

def counter_slide(bench, loops, note, title):
    o, p = counters("bm_" + bench), counters("opt_" + bench)
    s = slide(title, f"The VM does not support hardware counters, so these come from perf stat directly on the tangerine host, with 5 repeats of {loops} loops pinned to one core. IPC stays the same, so the speedup comes from executing fewer instructions. Times on the other slides are from the VM, so do not mix the two.")
    g = lambda v: f"{v / 1e9:.2f} G"
    rows = [["Counter", "Original", "Optimized", "Change"],
            ["Instructions", g(o["instructions"]), g(p["instructions"]), f"{o['instructions'] / p['instructions']:.2f}x fewer"],
            ["Cycles", g(o["cycles"]), g(p["cycles"]), f"{o['cycles'] / p['cycles']:.2f}x fewer"],
            ["IPC", f"{o['ipc']:.2f}", f"{p['ipc']:.2f}", "same"],
            ["Branches", g(o["branches"]), g(p["branches"]), f"{o['branches'] / p['branches']:.2f}x fewer"],
            ["Cache-miss rate", f"{o['cm']:.2f}%", f"{p['cm']:.2f}%", note],
            ["Branch-miss rate", f"{o['bm']:.2f}%", f"{p['bm']:.2f}%", "higher"]]
    table(s, .6, 1.4, 8.2, [2.8, 1.65, 1.65, 2.1], rows, 15, .54, align=[L_, R_, R_, L_], colors={(1, 3): TEAL, (2, 3): TEAL, (4, 3): TEAL})
    card(s, 9.05, 1.4, 3.68, 3.78, "How it was measured", ["tangerine host, Xeon E5-2690 v4", f"perf stat -r 5, {loops} loops", "Pinned to one core", "Not in the VM"], AMBERT, AMBER, 15)
    banner(s, 5.5, "IPC did not change: the speedup comes from executing fewer instructions.", .72)

RT, RO = "bm_raytrace/run_benchmark.py", "opt_raytrace/run_benchmark.py"
PB, PO = "bm_pyflate/run_benchmark.py", "opt_pyflate/run_benchmark.py"
r_o, r_od, r_n = stats("raytrace_orig.json"); r_p, r_pd, _ = stats("raytrace_opt.json")
r_speed, r_red = r_o / r_p, 100 * (r_o - r_p) / r_o
pf_speed = f"{PF['speed']:.2f}x" if PF else "pending"

# ---------------------------------------------------------------- title
s = slide("raytrace and pyflate: Benchmark Optimization and Hardware Acceleration",
          "Introduce the team and the plan: two pyperformance benchmarks, software optimization for both, and a ray-sphere accelerator for raytrace.", True)
t = s.shapes.title; t.top, t.height = I(1.9), I(1.9)
t.text_frame.paragraphs[0].runs[0].font.size = Pt(42)
text(s, .6, 4.0, 11.5, .5, "Performance analysis, software optimization and a ray-sphere accelerator in SystemVerilog", 20, "F0B266")
text(s, .6, 5.45, 11, .4, "Muhameed Mhameed  ·  Ahmad Maatouq", 19, WHITE, bold=True)
text(s, .6, 5.92, 11, .4, "HW/SW Co-design · Course 00460882", 16, "AEB8C6")

# ---------------------------------------------------------------- summary
s = slide("Project at a glance",
          "One slide with the whole story. raytrace: object overhead, 1.52x, and a hardware proposal. pyflate: an algorithmic Huffman scan and byte-level loops.")
table(s, .6, 1.45, 12.13, [1.75, 3.95, 3.95, 1.1, 1.38], [
    ["Benchmark", "Main bottleneck", "Software change", "Speedup", "Hardware"],
    ["raytrace", "Object and call overhead in the interpreter", "__slots__, remove no-op checks, inline math", f"{r_speed:.2f}x", "Proposed"],
    ["pyflate", "Linear Huffman search, byte-at-a-time loops", "Lookup table, bit buffer, faster MTF and RLE", pf_speed, "No"]], 15, .62,
    align=[L_, L_, L_, C, C], colors={(1, 3): TEAL, (2, 3): TEAL})
for i, (n, t, d) in enumerate([("1", "Measure", "pyperf, perf, flame graphs"), ("2", "Locate", "Connect C frames to Python code"), ("3", "Optimize", "Change code, verify the output"), ("4", "Accelerate", "RTL, simulation, Amdahl estimate")]):
    x = .6 + i * 3.1
    box(s, x, 3.75, 2.8, 1.75, TINT)
    tag(s, x + .2, 3.95, .46, .46, n, AMBER, WHITE, 15, shape=S.OVAL)
    text(s, x + .78, 3.99, 1.95, .4, t, 18, bold=True)
    text(s, x + .22, 4.6, 2.4, .8, d, 14, GREY)
    if i < 3: arrow(s, x + 2.8, 4.5, .3)
banner(s, 5.95, "Both benchmarks spend their time on work around the computation, not on the computation.")

# ---------------------------------------------------------------- method
s = slide("Method: how every number was measured",
          "Timing and profiles ran in the course QEMU VM with Python 3.10. The VM uses software emulation, so runs are slow and noisy, and it does not support hardware counters. Those were measured separately on the tangerine host, also with Python 3.10.")
code(s, .6, 1.4, 7.5, 2.85, "commands, run inside the VM", [
    (0, "perf record -F 999 -g -- python3-dbg run_benchmark.py \\"), (0, "    --values 1 -w 0"),
    (0, "perf script | stackcollapse-perf.pl | flamegraph.pl"), (0, ""),
    (0, "python3 run_benchmark.py --values 3 -w 1 -o out.json"), (0, "python3 -m pyperf compare_to orig.json opt.json")], 13)
card(s, 8.35, 1.4, 4.38, 2.85, "Two environments", ["Times and profiles: QEMU VM", "The VM has no hardware counters", "perf stat counters: tangerine host"], AMBERT, AMBER)
table(s, .6, 4.5, 12.13, [2.4, 5.2, 4.53], [
    ["Tool", "What it gives us", "Limit"],
    ["pyperf", "Mean and spread with python3", "VM spread reached 16-20% on raytrace"],
    ["perf + FlameGraph", "Profiles with python3-dbg", "Debug build changes the percentages"],
    ["perf stat", "Instructions, cycles, IPC on the host", "Different machine from the VM timing"],
    ["Icarus Verilog", "Simulation of the RTL", "No synthesis, so timing is an assumption"]], 14, .42)

# ---------------------------------------------------------------- Part A
PART[0] = "Part A · raytrace"
divider("PART A", "raytrace", "A pure-Python ray tracer", "Part A covers the raytrace benchmark and its hardware proposal.")

s = slide("What raytrace does",
          "The scene has 7 spheres and a checkerboard floor at 100 by 100 pixels. Every pixel casts a ray, tests every object, then shades with shadow and reflection rays. Vector and Point are small Python objects.")
for i, t in enumerate(["For each pixel", "Cast a ray", "Test all objects", "Pick nearest hit", "Shade and reflect"]):
    x = .6 + i * 2.48
    tag(s, x, 1.45, 2.15, .95, t, AMBER if i == 2 else TEALT, WHITE if i == 2 else INK, 16, line=None if i == 2 else TEAL)
    if i < 4: arrow(s, x + 2.17, 1.81, .29)
card(s, .6, 2.75, 3.9, 3.65, "Scene", ["100 x 100 pixels", "7 spheres and a checkerboard half-space", "2 lights, with reflections"], TINT, TEAL, 17, 20)
card(s, 4.72, 2.75, 3.9, 3.65, "Data structures", ["Vector and Point: x, y, z", "Ray: point and vector", "Sphere, Halfspace, Scene, Canvas"], TINT, TEAL, 17, 20)
card(s, 8.83, 2.75, 3.9, 3.65, "Libraries", ["math.sqrt", "pyperf for timing", "No numeric library: all arithmetic is Python objects"], TINT, TEAL, 17, 20)

rows = self_rows("raytrace_orig_perf_report.txt")
top = rows[:8]
meaning = {"_PyEval_EvalFrameDefault": ("Interpreter", TEAL), "_PyEval_MakeFrameVector": ("Calls and frames", AMBER), "call_function": ("Calls and frames", AMBER), "binary_op1": ("Arithmetic", GREY), "PyTuple_GetItem": ("Tuple access", GREY), "PyFloat_FromDouble": ("Float objects", GREY),
           "insertdict": ("Attributes and dicts", RED), "frame_dealloc": ("Calls and frames", AMBER), "_PyObject_GetMethod": ("Attributes and dicts", RED),
           "_PyObject_MakeTpCall": ("Calls and frames", AMBER), "_PyObject_GenericSetAttrWithDict": ("Attributes and dicts", RED)}
s = slide("Profiling: where the self-time goes",
          "Self time from perf report on the original code. The interpreter loop is about a third. The rest is spread over many small costs from calls, frames, attributes and dictionaries.")
data = [["Self %", "Symbol", "Category"]] + [[f"{v:.2f}", n, meaning.get(n, ("Other", GREY))[0]] for v, n in top]
cols = {(i + 1, 2): meaning.get(n, ("", GREY))[1] for i, (v, n) in enumerate(top)}
table(s, .6, 1.4, 8.15, [1.0, 4.65, 2.5], data, 14, .47, align=[R_, L_, L_], colors=cols)
text(s, .6, 5.75, 8.1, .3, "perf report --stdio, python3-dbg, original code, 1,270,226 samples", 12, GREY)
cat = {"Interpreter": 0, "Calls and frames": 0, "Attributes and dicts": 0}
for v, n in rows:
    k = ("Interpreter" if n == "_PyEval_EvalFrameDefault" else "Attributes and dicts" if re.search("dict|Dict|Attr|GetMethod|Type_Lookup", n) else "Calls and frames" if re.search("frame|Frame|Vectorcall|Call|call_function|tp_init", n) else None)
    if k: cat[k] += v
stat(s, 9.0, 1.4, 3.73, 1.35, f"{cat['Interpreter']:.1f}%", "Interpreter loop", TEAL, TEALT)
stat(s, 9.0, 2.9, 3.73, 1.35, f"{cat['Calls and frames']:.1f}%", "Calls and frames, by symbol name", AMBER, AMBERT)
stat(s, 9.0, 4.4, 3.73, 1.35, f"{cat['Attributes and dicts']:.1f}%", "Attributes and dicts, by symbol name", RED, REDT)

s = slide("Profiling: flame graph of the original run",
          "Bottom rows of raytrace_orig.svg. Width is the share of samples. The profile is flat apart from the interpreter loop. Many stacks still pass through unknown frames, and it shows CPython C functions only, so we read the code to map this to Python.")
pic = s.shapes.add_picture("assets/raytrace_orig.png", I(.6), I(1.4), width=I(12.13))
pic._element.nvPicPr.cNvPr.set("descr", "Bottom rows of the raytrace flame graph. The widest frame is _PyEval_EvalFrameDefault.")
y = 1.4 + pic.height / 914400 + .3
card(s, .6, y, 5.95, 6.8 - y, "How to read it", ["Width is share of samples, not time order", "No single wide function except the interpreter loop", "This points to many small costs"])
card(s, 6.78, y, 5.95, 6.8 - y, "Limit of this profile", ["Many stacks still pass through [unknown]", "Python function names are not visible", "The Python mapping comes from reading the source"], AMBERT, AMBER)

n1 = find_line(RT, "def __sub__"); n2 = find_line(RT, "def dot"); ni = find_line(RT, "def intersectionTime")
s = slide("Bottlenecks: the code behind the hotspots",
          "Three sources of work. Each operation creates a Vector with a dictionary. mustBeVector just returns self, so it is a pure call cost. intersectionTime runs for every ray-sphere pair and builds a temporary. The conclusion: the arithmetic is cheap, and the cost is the Python objects around it.")
code(s, .6, 1.4, 6.0, 2.5, f"{RT} · Vector", [(22, "class Vector(object):"), (24, "    def __init__(self, initx, inity, initz):"), (25, "!        self.x = initx   # __dict__ write"), (26, "!        self.y = inity"), (27, "!        self.z = initz")], 13, "dict per object")
hot = src(RT, n2, n2 + 2)
code(s, 6.73, 1.4, 6.0, 2.5, f"{RT} · dot", [(hot[0][0], hot[0][1]), (hot[1][0], "!" + hot[1][1]), (hot[2][0], hot[2][1].replace("(self.x * other.x) + (self.y * other.y) + (self.z * other.z)", "self.x*other.x + ...")), (find_line(RT, "def mustBeVector"), "    def mustBeVector(self):"), (find_line(RT, "def mustBeVector") + 1, "!        return self")], 13, "no-op call")
L = src(RT, ni, ni + 6)
code(s, .6, 4.05, 12.13, 2.75, f"{RT} · Sphere.intersectionTime", [(a, ("!" + b) if i in (1, 2, 3) else b) for i, (a, b) in enumerate(L)], 13, "179,457 calls per render")

s = slide("Optimization: three targeted changes",
          "Each change maps to a cost from the profile. Output stayed byte-identical on a 60 by 60 render of the benchmark scene.")
table(s, .6, 1.45, 12.13, [.6, 3.55, 4.6, 3.38], [
    ["#", "Change", "What it removes", "Expected in profile"],
    ["1", "__slots__ on Vector, Point, Ray", "Per-object dictionary", "insertdict, dict_dealloc"],
    ["2", "Remove mustBeVector() in hot methods", "No-op Python calls", "Frames, method lookup"],
    ["3", "Inline math in Sphere.intersectionTime", "Temporary Vector and dot() calls", "Allocation, frames"]], 15, .56)
code(s, .6, 3.95, 5.95, 2.85, "original · lines 143-145", [(143, "cp = self.centre - ray.point"), (144, "v = cp.dot(ray.vector)"), (145, "disc = r*r - (cp.dot(cp) - v*v)")], 16, "objects and calls")
code(s, 6.78, 3.95, 5.95, 2.85, "optimized", [(0, "!cpx = c.x - p.x   # same for y, z"), (0, "!v = cpx*d.x + cpy*d.y + cpz*d.z"), (0, "!cp2 = cpx*cpx + cpy*cpy + cpz*cpz"), (0, "disc = r*r - (cp2 - v*v)")], 16, "local floats")

s = slide(f"Results: raytrace runs {r_speed:.2f}x faster",
          "Official pyperf comparison, 60 values each. The spread is large because of the VM, but the gain is well above it and far above the 7 percent target. perf sample count fell by 28 percent, consistent with the time saved.")
box(s, .6, 1.45, 3.9, 4.0, TINT)
text(s, .85, 1.62, 3.4, .3, "Mean ± std dev (pyperf)", 14, GREY, A.CENTER)
text(s, .85, 2.0, 3.4, .75, f"{r_o:.1f} s", 42, INK, A.CENTER, True)
text(s, .85, 2.8, 3.4, .3, f"original, ± {r_od:.1f} s", 14, GREY, A.CENTER)
text(s, .85, 3.55, 3.4, .75, f"{r_p:.1f} s", 42, TEAL, A.CENTER, True)
text(s, .85, 4.35, 3.4, .3, f"optimized, ± {r_pd:.1f} s", 14, GREY, A.CENTER)
fn = [("_PyEval_MakeFrameVector", "Frame creation"), ("insertdict", "Dict writes"), ("frame_dealloc", "Frame cleanup"), ("_PyObject_GetMethod", "Method lookup")]
tb = [["Measure", "Original", "Optimized", "Change"], ["Mean time", f"{r_o:.1f} s", f"{r_p:.1f} s", f"{r_red:.0f}% less"], ["perf samples", "1,270,226", "768,333", "40% fewer"]]
for sym, lab in fn:
    a, b = dict(map(reversed, self_rows("raytrace_orig_perf_report.txt"))).get(sym, 0), dict(map(reversed, self_rows("raytrace_opt_perf_report.txt"))).get(sym, 0)
    tb.append([lab, f"{a:.2f}%", f"{b:.2f}%", "lower" if b < a else "higher" if b > a else "same"])
table(s, 4.75, 1.45, 7.98, [3.0, 1.66, 1.66, 1.66], tb, 15, .57, align=[L_, R_, R_, L_], colors={(i, 3): TEAL for i in range(1, 7)})
banner(s, 5.75, "Output stayed byte-identical, and the gain is far above the 7% target.")

counter_slide("raytrace", 10, "about the same", "Results: hardware counters for raytrace")

s = slide("Results: flame graphs before and after",
          "Same shape, less work. The percentages are shares of a shorter run, so compare the shape and the sample counts, not raw widths.")
text(s, .6, 1.4, 5.9, .35, [[("Before: ", {"bold": True}), "1,270,226 samples"]], 16)
text(s, 6.83, 1.4, 5.9, .35, [[("After: ", {"bold": True}), "768,333 samples"]], 16)
for i, n in enumerate(("raytrace_orig", "raytrace_opt")):
    x = .6 + i * 6.23
    p = s.shapes.add_picture(f"assets/{n}.png", I(x), I(1.85), width=I(5.9))
    p._element.nvPicPr.cNvPr.set("descr", f"Bottom rows of the {n} flame graph")
    vals = [("_PyEval_EvalFrameDefault", "_PyEval_EvalFrameDefault"), ("_PyEval_MakeFrameVector", "_PyEval_MakeFrameVector"), ("insertdict", "insertdict")]
    svg = n + ".svg"
    y0 = 1.85 + p.height / 914400 + .3
    table(s, x, y0, 5.9, [1.2, 4.7], [["Share", "Frame"]] + [[f"{flame_pct(svg, a):.2f}%", b] for a, b in vals], 14, .44, align=[R_, L_])
text(s, .6, 6.05, 12.1, .6, "The interpreter share rises because other work shrank. Compare shape and sample count, not raw width.", 15, GREY)

s = slide("Hardware: why ray-sphere intersection",
          "This function is fixed arithmetic with no data-dependent memory access, and it runs 179,457 times per render. Worked example is Test 1 in the testbench. d must be a unit vector.")
code(s, .6, 1.4, 5.95, 3.1, "the computation", [(0, "cp   = c - p"), (0, "v    = cp . d"), (0, "disc = r^2 - (cp.cp - v^2)"), (0, ""), (0, "!disc < 0 : miss"), (0, "!t = v - sqrt(disc)")], 16)
card(s, 6.78, 1.4, 5.95, 3.1, "Worked example (Test 1)", ["Sphere at (0, 0, 10), r = 2", "Ray from origin along +z", "v = 10, cp.cp = 100, disc = 4", [("t = 10 - 2 = 8", {"bold": True, "color": RED})]], AMBERT, AMBER, 16)
stat(s, .6, 4.75, 3.89, 1.75, "179,457", "calls per 100x100 render", TEAL, TEALT, 30)
stat(s, 4.72, 4.75, 3.89, 1.75, "0.50 / 0.285", "share of runtime, original / optimized", TEAL, TINT, 30)
stat(s, 8.84, 4.75, 3.89, 1.75, "Q16.16", "32-bit signed fixed point", AMBER, AMBERT, 30)

s = slide("Hardware: accelerator block diagram",
          "Left is software: Python calls a driver that converts floats to Q16.16 and moves data by MMIO or DMA. Right is the block: one multi-cycle datapath, a square root unit, and an FSM. A miss skips the square root.")
box(s, .6, 1.4, 3.35, 5.35, TINT, line=LINE)
text(s, .6, 1.5, 3.35, .35, "Software (CPU)", 16, bold=True, align=C)
tag(s, .85, 2.0, 2.85, .85, ["Sphere.intersectionTime", ("Python", {"size": 12, "bold": False})], WHITE, INK, 14, line=LINE)
arrow(s, 2.14, 2.88, .28, .28, GREY, S.DOWN_ARROW)
tag(s, .85, 3.2, 2.85, .95, ["C extension and driver", ("float to Q16.16, batching", {"size": 12, "bold": False})], WHITE, INK, 14, line=LINE)
arrow(s, 2.14, 4.18, .28, .28, GREY, S.DOWN_ARROW)
tag(s, .85, 4.5, 2.85, .95, ["MMIO registers / DMA", ("descriptor list of pairs", {"size": 12, "bold": False})], WHITE, INK, 14, line=LINE)
text(s, .85, 5.65, 2.85, .9, "A start bit drives in_valid. Results return with hit and t_hit.", 13, GREY)
arrow(s, 3.98, 3.55, .55, .34); arrow(s, 3.98, 4.15, .55, .34, GREY, S.LEFT_ARROW)
box(s, 4.56, 1.4, 8.17, 5.35, TEALT, line=TEAL)
text(s, 4.56, 1.5, 8.17, .35, "ray_sphere_intersect (SystemVerilog)", 16, TEAL, bold=True, align=C)
tag(s, 4.82, 2.05, 1.75, .95, ["Input regs", ("c, r, p, d", {"size": 12, "bold": False})], WHITE, INK, 14, line=TEAL)
tag(s, 6.95, 2.05, 1.75, .95, ["Subtract", ("cp = c - p", {"size": 12, "bold": False})], WHITE, INK, 14, line=TEAL)
tag(s, 9.08, 2.05, 1.75, .95, ["Multiply-add", ("v, cp.cp, r^2", {"size": 12, "bold": False})], WHITE, INK, 14, line=TEAL)
tag(s, 10.78, 3.45, 1.7, .95, ["disc and sign", ("r^2 - (cp.cp - v^2)", {"size": 12, "bold": False})], WHITE, INK, 13, line=TEAL)
arrow(s, 6.6, 2.4, .32); arrow(s, 8.73, 2.4, .32)
box(s, 10.86, 2.45, .95, .2, GREY, S.RIGHT_ARROW); arrow(s, 11.5, 2.75, .28, .66, GREY, S.DOWN_ARROW)
tag(s, 7.85, 3.45, 2.4, .95, ["q16_sqrt", ("restoring, 24 cycles", {"size": 12, "bold": False})], AMBERT, INK, 14, line=AMBER)
arrow(s, 10.3, 3.8, .44, .24, GREY, S.LEFT_ARROW)
tag(s, 4.82, 3.45, 2.5, .95, ["t = v - sqrt(disc)", ("output register", {"size": 12, "bold": False})], WHITE, INK, 14, line=TEAL)
arrow(s, 7.37, 3.8, .44, .24, GREY, S.LEFT_ARROW)
tag(s, 4.82, 4.75, 7.66, .72, ["Control FSM: IDLE, CALC_DOT, CALC_DISC, SQRT_WAIT, EMIT"], INK, WHITE, 15)
text(s, 4.82, 5.65, 7.66, .9, [[("disc < 0: ", {"bold": True, "color": RED}), "skip q16_sqrt and go straight to EMIT with hit = 0."], "valid/ready handshake on both the input and output sides."], 14)

s = slide("Hardware: interface and FSM latency",
          "All data is signed Q16.16. Latency is measured in simulation: 30 cycles for a hit and 4 for a miss. The 200 MHz clock is an assumption since we did not synthesize.")
table(s, .6, 1.4, 6.3, [2.55, .9, 2.85], [
    ["Signal", "Bits", "Meaning"], ["cx, cy, cz, radius", "32 each", "Sphere, Q16.16"], ["px, py, pz", "32 each", "Ray origin"], ["dx, dy, dz", "32 each", "Unit direction"],
    ["in_valid / in_ready", "1 each", "Input handshake"], ["out_valid / out_ready", "1 each", "Output handshake"], ["hit", "1", "Sphere was hit"], ["t_hit", "32", "Distance, 0 on miss"]], 13, .45, align=[L_, C, L_])
table(s, 7.15, 1.4, 5.58, [1.95, 2.55, 1.08], [
    ["State", "Work", "Cycles"], ["IDLE", "Capture cp = c - p", "1"], ["CALC_DOT", "v, cp.cp, r^2", "1"], ["CALC_DISC", "Scale, disc, sign", "1"],
    ["SQRT_WAIT", "24 root bits + handoff", "26"], ["EMIT", "Hold until ready", "1"]], 13, .45, align=[L_, L_, C])
stat(s, 7.15, 4.3, 2.68, 1.0, "30", "cycles, hit", AMBER, AMBERT, 26)
stat(s, 10.05, 4.3, 2.68, 1.0, "4", "cycles, miss", AMBER, AMBERT, 26)
banner(s, 5.55, "At an assumed 200 MHz: 150 ns per hit, 20 ns per miss. One request at a time, not a pipeline.", .75)

s = slide("Hardware: verification found a real bug",
          "Two nonblocking assignments in one cycle meant out_valid never held a high value. The old testbench caught a zero-width glitch, so it passed. The new testbench samples a settled level. The old RTL fails it. Not tested yet: out_ready low, tangent rays, negative t.")
code(s, .6, 1.4, 5.95, 2.5, "ray_sphere_intersect.sv · before", [(0, "EMIT: begin"), (0, "    out_valid <= 1'b1;"), (0, "!    if (out_ready) begin"), (0, "!        out_valid <= 1'b0;  // wins")], 14, "same cycle")
code(s, 6.78, 1.4, 5.95, 2.5, "ray_sphere_intersect.sv · after", [(0, "EMIT: begin"), (0, "    out_valid <= 1'b1;"), (0, "!    if (out_valid && out_ready) begin"), (0, "        out_valid <= 1'b0;")], 14, "hold until transfer")
table(s, .6, 4.15, 12.13, [4.5, 3.8, 3.83], [["Testbench run", "Result", "Why"], ["Old testbench, old RTL", "PASS", "@(posedge out_valid) saw a glitch"], ["New testbench, old RTL", "FAIL, timeout", "out_valid never settles high"], ["New testbench, fixed RTL", "PASS: t = 8.0, miss detected", "Real handshake"]], 14, .45, colors={(1, 1): AMBER, (2, 1): RED, (3, 1): TEAL})

s = slide("Hardware: estimated benefit (Amdahl's law)",
          "f and the per-call cost were measured on the tangerine host with Python 3.10, by replaying the real calls of one render. Against the optimized code the ceiling is 1.40x. With 0.74 microseconds in software and 150 nanoseconds in hardware at the 200 MHz target, s is 4.9, giving 1.29x before transfer costs. A device round trip from Python can take as long as the call it replaces, so batching is needed.")
text(s, .6, 1.42, 6.2, .5, "S = 1 / ((1 - f) + f / s)", 26, TEAL, bold=True)
table(s, .6, 2.1, 6.2, [2.6, 1.8, 1.8], [["tangerine, Python 3.10", "Original", "Optimized"], ["Render time", "0.710 s", "0.465 s"], ["Cost per call", "2.00 us", "0.74 us"], ["f", "0.50", "0.285"]], 14, .46, align=[L_, R_, R_])
cd = CategoryChartData(); cd.categories = ["s = 4.9, compute only", "s = infinity, upper bound"]; cd.add_series("Speedup", (1.29, 1.40))
g = s.shapes.add_chart(X.BAR_CLUSTERED, I(.6), I(4.1), I(6.2), I(2.3), cd); ch = g.chart
ch.has_legend = False; ch.has_title = False; ch.font.size = Pt(13); ch.font.color.rgb = rgb(INK)
pl = ch.plots[0]; pl.gap_width = 50; pl.has_data_labels = True; pl.data_labels.number_format = '0.00"x"'; pl.data_labels.number_format_is_linked = False; pl.data_labels.position = LP.OUTSIDE_END
ch.value_axis.visible = False; ch.value_axis.has_major_gridlines = False; ch.value_axis.minimum_scale = 0; ch.value_axis.maximum_scale = 1.9
ch.category_axis.reverse_order = True; ch.category_axis.format.line.color.rgb = rgb(LINE)
for i, c in enumerate((TEAL, AMBER)):
    pt = pl.series[0].points[i]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(c)
box(s, 7.05, 1.42, 5.68, 3.0, INK)
text(s, 7.32, 1.62, 5.1, .4, "Transfers decide the outcome", 19, "F0B266", bold=True)
text(s, 7.32, 2.2, 5.15, 2.1, ["The 1.29x excludes transfer and conversion", "A Python-to-device round trip can cost as much as the 0.74 us it replaces", "So calls must be sent in batches"], 15, WHITE, bullets=True, after=7)
card(s, 7.05, 4.6, 5.68, 1.85, "What makes it pay off", ["Batch ray-sphere pairs over DMA", "Pipeline the datapath for throughput"], TEALT, TEAL, 15)

s = slide("Hardware: performance, area and power trade-offs",
          "These are design estimates. We did not run synthesis, so area and frequency numbers are not measured.")
table(s, .6, 1.45, 12.13, [2.2, 4.75, 5.18], [
    ["Aspect", "Current design", "Alternative and cost"],
    ["Area", "8 multipliers of 32x32", "One shared multiplier: smaller, about 6 extra cycles"],
    ["Frequency", "Three products summed in one cycle", "More stages: higher clock, longer latency"],
    ["Throughput", "One result per 30 cycles", "Pipelined root: one per cycle, about 24 register stages"],
    ["Precision", "Q16.16, squares below 32768", "Floating point: more range, much more logic"],
    ["Power", "Fixed point, misses skip the root", "More parallel lanes raise power and throughput"],
    ["Integration", "MMIO or DMA, C extension", "Tighter CPU coupling lowers call cost, harder to build"]], 14, .62)
banner(s, 6.0, "The largest open choice is batching and pipelining, because transfer cost sets the real speedup.", .66)

# ---------------------------------------------------------------- Part B
PART[0] = "Part B · pyflate"
divider("PART B", "pyflate", "bzip2 decompression in pure Python", "Part B covers pyflate. Here the bottleneck is algorithmic, so the software change has more room.")

s = slide("What pyflate does",
          "pyflate decodes a bzip2 file with no compression library and checks an MD5 on every run. Bits are read through a Python class, and each stage is written in pure Python.")
for i, t in enumerate(["Huffman decode", "Move-to-front", "Expand runs", "Reverse BWT", "Final RLE"]):
    x = .6 + i * 2.48
    tag(s, x, 1.45, 2.15, .95, t, AMBER if i == 0 else TEALT, WHITE if i == 0 else INK, 16, line=None if i == 0 else TEAL)
    if i < 4: arrow(s, x + 2.17, 1.81, .29)
card(s, .6, 2.75, 3.9, 3.65, "Input and check", ["interpreter.tar.bz2, 67,562 bytes", "MD5 checked on every run"], TINT, TEAL, 17, 20)
card(s, 4.72, 2.75, 3.9, 3.65, "Data structures", ["RBitfield: bit reader", "HuffmanTable: list of codes", "Python lists and bytes"], TINT, TEAL, 17, 20)
card(s, 8.83, 2.75, 3.9, 3.65, "Libraries", ["hashlib, struct, pyperf", "No compression library in the decoder"], TINT, TEAL, 17, 20)

s = slide("Profiling: where the self-time goes",
          "Self time from perf report on the original pyflate code.")
cats = {"_PyEval_EvalFrameDefault": ("Interpreter", TEAL), "long_richcompare": ("Comparisons", RED), "__memset_sse2_unaligned_erms": ("Debug build", AMBER), "_PyMem_DebugCheckAddress": ("Debug build", AMBER), "_PyMem_DebugRawFree": ("Debug build", AMBER), "PyGILState_Check": ("Debug build", AMBER), "read_size_t": ("Debug build", AMBER), "_PyMem_DebugRawAlloc": ("Debug build", AMBER), "call_function": ("Calls", GREY), "PyTuple_GetItem": ("Tuple access", GREY), "list_dealloc": ("List churn", AMBER), "list_ass_slice": ("List churn", AMBER), "list_slice": ("List churn", AMBER), "_PyFunction_Vectorcall": ("Calls", GREY), "_PyObject_GetMethod": ("Calls", GREY), "binary_op1": ("Arithmetic", GREY), "object_dealloc": ("Objects", GREY)}
r = self_rows("pyflate_orig_perf_report.txt", 8)
table(s, .6, 1.4, 8.15, [1.0, 4.65, 2.5], [["Self %", "Symbol", "Category"]] + [[f"{v:.2f}", n, cats.get(n, ("Other", GREY))[0]] for v, n in r], 14, .47, align=[R_, L_, L_], colors={(i + 1, 2): cats.get(n, ("", GREY))[1] for i, (v, n) in enumerate(r)})
text(s, .6, 5.75, 8.1, .3, "perf report --stdio, python3-dbg, original code, 1,380,705 samples", 12, GREY)
card(s, 9.0, 1.4, 3.73, 4.25, "What stands out", ["Interpreter loop: 21.1%", "Debug-build allocator costs are large", "List frees fall from 1.47% to 0.19% after the fix"], TINT, TEAL)

s = slide("Profiling: flame graphs before and after",
          "Bottom rows of the pyflate flame graphs. Samples fall by 61 percent. List slicing and list frees shrink, which matches removing the scan and the list rebuild. In the optimized run re and memory-copy functions appear, as expected.")
if PF_SVG:
    for i, n in enumerate(("pyflate_orig", "pyflate_opt")):
        x = .6 + i * 6.23
        text(s, x, 1.4, 5.9, .35, [[("Before: " if i == 0 else "After: ", {"bold": True}), "1,380,705 samples" if i == 0 else "539,715 samples"]], 16)
        p = s.shapes.add_picture(f"assets/{n}.png", I(x), I(1.85), width=I(5.9))
        p._element.nvPicPr.cNvPr.set("descr", f"Bottom rows of the {n} flame graph")
        y0 = 1.85 + p.height / 914400 + .3
        sv = n + ".svg"
        table(s, x, y0, 5.9, [1.2, 4.7], [["Share", "Frame"]] + [[f"{flame_pct(sv, a):.2f}%", a] for a in ("_PyEval_EvalFrameDefault", "list_dealloc", "list_ass_slice")], 14, .44, align=[R_, L_])
else:
    pending(s, .6, 1.4, 12.13, 5.3)

nf = find_line(PB, "def find_next_symbol"); nm = find_line(PB, "def move_to_front")
s = slide("Bottlenecks: the code behind the hotspots",
          "find_next_symbol runs once per decoded symbol and scans the code table. move_to_front builds a new list each time. The RLE loop creates one small bytes object per output byte.")
L = src(PB, nf, nf + 8)
code(s, .6, 1.4, 7.4, 3.25, f"{PB} · find_next_symbol", [(a, ("!" + b.replace("(reversed and x.reverse_symbol == cached) or (not reversed and x.symbol == cached)", "... x.symbol == cached")) if "for x in self.table" in b or "x.symbol == cached" in b else b) for a, b in L], 13, "linear scan per symbol")
Lm = src(PB, nm, nm + 1)
code(s, 8.2, 1.4, 4.53, 1.5, "move_to_front", [(Lm[0][0], Lm[0][1]), (Lm[1][0], "!    l[:] = l[c:c+1] + l[0:c] + ...")], 12)
nr = find_line(PB, "Pointless/irritating")
code(s, .6, 4.8, 7.4, 2.0, f"{PB} · final RLE", [(nr + 1, "while i < len(nearly_there):"), (nr + 6, "    else:"), (nr + 7, "!        out.append(nearly_there[i:i + 1])"), (nr + 8, "        i += 1")], 13, "one object per byte")
card(s, 8.2, 3.05, 4.53, 3.75, "Root causes", ["Algorithmic: search cost grows with table size", "Bit reader pulls one byte at a time", "Byte-level Python loops create many objects"], TINT, RED, 15)

s = slide("Optimization: four changes, still pure Python",
          "We kept the decoder in Python. We did not replace it with the bz2 module, because that would remove the code under study. Each change maps to a root cause on the previous slide.")
table(s, .6, 1.45, 12.13, [.6, 3.6, 4.7, 3.23], [
    ["#", "Change", "What it removes", "Cost addressed"],
    ["1", "Huffman lookup table", "Scan over the code table", "Algorithmic"],
    ["2", "8-byte refill, local bit state", "Per-byte reads, method calls", "Call overhead"],
    ["3", "move_to_front with pop and insert", "New list per symbol", "Allocation"],
    ["4", "RLE with re, copy slices", "One bytes object per output byte", "Allocation, loop cost"]], 15, .56)
ne = find_line(PO, "width = t.fast_bits")
code(s, .6, 4.45, 12.13, 2.35, f"{PO} · main decode loop", [(ne, "width = t.fast_bits"), (ne + 1, "!entry = t.fast[(bitfield >> (nbits - width)) & ((1 << width) - 1)]"), (ne + 2, "if entry:"), (ne + 3, "!    r = entry >> 5"), (ne + 4, "!    nbits -= entry & 31")], 14, "one list lookup")

s = slide("How the lookup table works",
          "Toy example with four codes and a 3-bit table. Every index that begins with a code stores that symbol and its length. The next 3 bits index directly: no scan. Our table uses 10 bits, and longer codes use one dict per length.")
table(s, .6, 1.45, 3.9, [1.3, 1.3, 1.3], [["Symbol", "Code", "Length"], ["A", "0", "1"], ["B", "10", "2"], ["C", "110", "3"], ["D", "111", "3"]], 16, .52, align=[C, C, C])
text(s, .6, 4.25, 3.9, .3, "Toy example, 3-bit table", 13, GREY)
idx = ["000", "001", "010", "011", "100", "101", "110", "111"]; sym = ["A", "A", "A", "A", "B", "B", "C", "D"]; ln = ["1", "1", "1", "1", "2", "2", "3", "3"]
col = {"A": TEALT, "B": AMBERT, "C": REDT, "D": TINT}
arrow(s, 4.62, 2.4, .42, .32)
for i in range(8):
    x = 5.15 + i * .95
    tag(s, x, 1.45, .88, .5, idx[i], WHITE, GREY, 13, False, LINE)
    tag(s, x, 2.0, .88, 1.05, [(sym[i], {"size": 22}), (f"len {ln[i]}", {"size": 12, "bold": False})], col[sym[i]], INK, 14)
text(s, 5.15, 3.2, 7.5, .35, "Next bits 101... index 5: B, consume 2 bits. One step, no scan.", 16, TEAL, bold=True)
card(s, .6, 4.65, 5.95, 2.15, "In our decoder", ["Width: min(longest code, 10 bits)", "Entry: (symbol << 5) | code length", "Longer codes: one dict per length"])
card(s, 6.78, 4.65, 5.95, 2.15, "Why it is safe near the end", ["Longest code is 20 bits", "At least 80 bits follow every block", "So peeking cannot pass the end of the stream"], AMBERT, AMBER)

s = slide(f"Results: pyflate {'runs ' + pf_speed + ' faster' if PF else 'comparison'}",
          "Official pyperf comparison in the VM. MD5 passes on every run. The optimized decoder also matched the bz2 module on 14 test inputs, including multi-block files.")
box(s, .6, 1.45, 3.9, 4.0, TINT)
text(s, .85, 1.62, 3.4, .3, "Mean ± std dev (pyperf)", 14, GREY, A.CENTER)
text(s, .85, 2.0, 3.4, .75, f"{PF['o']:.1f} s" if PF else "pending", 42, INK, A.CENTER, True)
text(s, .85, 2.8, 3.4, .3, f"original, ± {PF['od']:.1f} s" if PF else "original", 14, GREY, A.CENTER)
text(s, .85, 3.55, 3.4, .75, f"{PF['p']:.1f} s" if PF else "pending", 42, TEAL, A.CENTER, True)
text(s, .85, 4.35, 3.4, .3, f"optimized, ± {PF['pd']:.1f} s" if PF else "optimized", 14, GREY, A.CENTER)
table(s, 4.75, 1.45, 7.98, [3.8, 4.18], [["Check", "Result"], ["Speedup", pf_speed], ["Runtime reduction", f"{PF['red']:.0f}%" if PF else "pending"], ["perf samples, python3-dbg", "1,380,705 to 539,715"], ["Target", "At least 7%"], ["MD5 of the output", "Passes on every run"], ["bz2 cross-check", "14 of 14 inputs match"]], 15, .57, colors={(1, 1): TEAL, (2, 1): TEAL})
banner(s, 5.75, "An algorithmic change gives more room than removing interpreter overhead alone.")

counter_slide("pyflate", 3, "lower, noisy", "Results: hardware counters for pyflate")

# ---------------------------------------------------------------- end
PART[0] = ""
s = slide("Conclusions", "Close with the three lessons and the open limits, then take questions.", True)
for i, (t, d) in enumerate([("Measure first", "Profiles showed where the extra work was, and reading the code linked it to Python."), ("Software first", f"Removing work gave {r_speed:.2f}x on raytrace and {pf_speed} on pyflate, with no new hardware."), ("Transfers decide", "An accelerator needs batching: the upper bound is 1.40x after optimization.")]):
    x = .6 + i * 4.12
    box(s, x, 1.45, 3.89, 2.45, "293243")
    text(s, x + .25, 1.68, 3.4, .45, t, 22, "F0B266", bold=True)
    text(s, x + .25, 2.3, 3.4, 1.4, d, 16, WHITE)
text(s, .6, 4.25, 6, .4, "Open limits", 20, WHITE, bold=True)
text(s, .6, 4.8, 6.2, 1.5, ["200 MHz is a design target: no synthesis", "Back-pressure is not tested", "Transfer costs are not measured"], 16, "C9D0DA", bullets=True)
text(s, 7.2, 4.25, 5.5, .4, "Repository", 20, WHITE, bold=True)
text(s, 7.2, 4.8, 5.5, .8, "github.com/muhameedm/hw-sw-codesign-project", 16, "C9D0DA")
text(s, 7.2, 5.55, 5.5, .6, "Thank you. Questions?", 26, "F0B266", bold=True)

prs.save(OUT)

theme = {"dk2": INK, "lt2": TINT, "accent1": TEAL, "accent2": AMBER, "accent3": GREY, "accent4": RED, "accent5": "6FB7AE", "accent6": "F2C27E"}
tmp = OUT + ".tmp"
with zipfile.ZipFile(OUT) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
    for it in zi.infolist():
        d = zi.read(it.filename)
        if it.filename.startswith("ppt/theme/"):
            t = d.decode()
            for k, v in theme.items():
                t = re.sub(rf'(<a:{k}>\s*<a:srgbClr val=")\w+', rf"\g<1>{v}", t)
            d = t.encode()
        zo.writestr(it, d)
shutil.move(tmp, OUT)
print("slides", len(prs.slides), "calls/frames", round(cat["Calls and frames"], 1), "attrs", round(cat["Attributes and dicts"], 1))
