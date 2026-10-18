import os, math, random

OUT = r"G:\Claude code\PlayMate\static\img"
FONT = 'font-family="Segoe UI, Arial, sans-serif"'
BG0, BG1, BG2 = "#070b10", "#0b1219", "#121b25"
GREEN, LIME, CYAN, RED, AMBER, TEXT = "#2dffb3", "#b6ff5c", "#2ee6ff", "#ff4d6d", "#ffb547", "#eef5f7"
PURPLE = "#a855f7"


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    A, B = rgb(a), rgb(b)
    return "#%02x%02x%02x" % tuple(round(A[i] + (B[i] - A[i]) * t) for i in range(3))


def save(rel, s):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}">{body}</svg>\n')


def glow(fid, sd):
    return (f'<filter id="{fid}" x="-50%" y="-50%" width="200%" height="200%">'
            f'<feGaussianBlur stdDeviation="{sd}" result="b"/><feMerge>'
            f'<feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')


def blur(fid, sd):
    return (f'<filter id="{fid}" x="-50%" y="-50%" width="200%" height="200%">'
            f'<feGaussianBlur stdDeviation="{sd}"/></filter>')


def f1(x):
    return ("%.1f" % x).rstrip("0").rstrip(".")


# ---------------------------------------------------------------- figures
OP = ("M34 6C46 4 54 12 54 22V30L50 36 46 40 58 46 92 44 96 50 62 56 60 70 58 96 62 150H48"
      "L42 108 36 150H22L24 96 18 62C16 50 22 42 28 40L24 34 22 22C22 12 26 7 34 6Z")
RIFLE = "M40 43H112V48H74L68 58H58L60 48H40Z"
STAND = ("M20 0C27 0 31 5 31 12 31 18 28 22 24 23L34 27C38 29 40 33 40 38L38 64 33 64 32 44 31 66 30 100"
         "H23L20 70 17 100H10L9 66 8 44 7 64H2L0 38C0 33 2 29 6 27L16 23C12 22 9 18 9 12 9 5 13 0 20 0Z")


def op(x, y, s, fill, rim, flip=False, visor=None):
    sx = -s if flip else s
    sw = f1(1.6 / s)
    v = f'<rect x="40" y="15" width="15" height="5" rx="2" fill="{visor}" filter="url(#gl)"/>' if visor else ""
    return (f'<g transform="translate({x} {y}) scale({f1(sx)} {f1(s)})">'
            f'<path d="{RIFLE}" fill="{fill}" stroke="{rim}" stroke-opacity=".5" stroke-width="{sw}"/>'
            f'<path d="{OP}" fill="{fill}" stroke="{rim}" stroke-opacity=".55" stroke-width="{sw}"/>{v}</g>')


def stand(x, y, s, fill, rim, extra=""):
    return (f'<g transform="translate({x} {y}) scale({f1(s)})"><path d="{STAND}" fill="{fill}" '
            f'stroke="{rim}" stroke-opacity=".6" stroke-width="{f1(1.6 / s)}"/>{extra}</g>')


# ---------------------------------------------------------------- covers
def cover(gid, name, genre, accent, scene, defs=""):
    tagw = len(genre) * 7.4 + 26
    d = (f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG1}"/>'
         f'<stop offset="1" stop-color="{BG0}"/></linearGradient>'
         f'<radialGradient id="ag" cx=".72" cy=".38" r=".62"><stop offset="0" stop-color="{accent}" stop-opacity=".45"/>'
         f'<stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient>'
         f'<pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" '
         f'stroke="{TEXT}" stroke-opacity=".05"/></pattern>'
         f'<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset=".45" stop-color="{BG0}" stop-opacity="0"/>'
         f'<stop offset="1" stop-color="{BG0}" stop-opacity=".95"/></linearGradient>'
         f'<linearGradient id="side" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{BG0}" stop-opacity=".8"/>'
         f'<stop offset=".55" stop-color="{BG0}" stop-opacity="0"/></linearGradient>'
         f'<linearGradient id="bar" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{accent}"/>'
         f'<stop offset="1" stop-color="{accent}" stop-opacity="0"/></linearGradient>'
         f'{glow("gl", 3)}{glow("gl2", 7)}{blur("bl", 10)}{blur("bl2", 3)}{defs}</defs>')
    b = (f'<rect width="640" height="360" fill="url(#bg)"/><rect width="640" height="360" fill="url(#ag)"/>'
         f'<rect width="640" height="360" fill="url(#grid)"/>{scene}'
         f'<rect width="640" height="360" fill="url(#fade)"/><rect width="640" height="360" fill="url(#side)"/>'
         f'<rect x="28" y="258" width="{f1(tagw)}" height="22" rx="11" fill="{accent}" fill-opacity=".16" '
         f'stroke="{accent}" stroke-opacity=".7"/>'
         f'<text x="{f1(28 + tagw / 2)}" y="273.5" text-anchor="middle" {FONT} font-size="11" font-weight="800" '
         f'letter-spacing="1.6" fill="{accent}">{genre.upper()}</text>'
         f'<text x="28" y="322" {FONT} font-size="40" font-weight="900" fill="{TEXT}" letter-spacing="-.5">{name}</text>'
         f'<rect x="28" y="334" width="120" height="4" rx="2" fill="url(#bar)"/>'
         f'<rect x="1" y="1" width="638" height="358" rx="14" fill="none" stroke="{accent}" stroke-opacity=".3" stroke-width="2"/>')
    save(f"games/{gid}.svg", svg(640, 360, d + b))


def star_pts(cx, cy, r1, r2, n, rot=0):
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r2
        a = rot + math.pi * i / n
        pts.append(f"{f1(cx + r * math.cos(a))},{f1(cy + r * math.sin(a))}")
    return " ".join(pts)


def scene_battlefield(a):
    rnd = random.Random(1)
    heli = ('<g id="heli" fill="#06090d" stroke="%s" stroke-opacity=".35">'
            '<path d="M0 20C0 10 14 4 34 4C52 4 64 12 66 20C64 28 50 32 32 32C14 32 0 28 0 20Z"/>'
            '<path d="M-60 14L0 16V24L-60 18Z"/><path d="M-66 4H-58L-54 18H-62Z"/>'
            '<path d="M-14 -6H82" stroke="#06090d" stroke-width="3" stroke-opacity="1"/><rect x="30" y="-6" width="4" height="10"/>'
            '<path d="M8 40H58M18 32V40M46 32V40" stroke="#06090d" stroke-width="3" stroke-opacity="1"/>'
            '<path d="M44 8C54 10 62 14 64 20H46Z" fill="%s" fill-opacity=".45" stroke="none"/></g>') % (a, a)
    defs = (f'<radialGradient id="ex"><stop offset="0" stop-color="#fff6d8"/><stop offset=".22" stop-color="#ffd27a"/>'
            f'<stop offset=".5" stop-color="{a}" stop-opacity=".75"/><stop offset="1" stop-color="{a}" stop-opacity="0"/></radialGradient>'
            f'<linearGradient id="haze" x1="0" y1="0" x2="0" y2="1"><stop offset=".2" stop-color="{a}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{a}" stop-opacity=".35"/></linearGradient>')
    smoke = "".join(f'<circle cx="{rnd.randint(150, 640)}" cy="{rnd.randint(70, 190)}" r="{rnd.randint(30, 60)}"/>' for _ in range(9))
    fire = "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="22"/>' for x, y, rx in [(250, 245, 70), (430, 240, 60), (590, 250, 50)])
    sky = ("M0 250V212H34V184H62V204H92V160H112V146H128V160H152V214H192V188H232V226H262V170H280V150H298V170H318V230"
           "H352V196H392V176H408V196H430V236H468V182H500V208H530V160H560V220H600V192H640V360H0Z")
    embers = "".join(f'<circle cx="{rnd.randint(160, 640)}" cy="{rnd.randint(60, 250)}" r="{rnd.choice([1, 1.5, 2])}"/>' for _ in range(26))
    s = (f'<rect width="640" height="360" fill="url(#haze)"/>'
         f'<g fill="#1c2027" opacity=".85" filter="url(#bl)">{smoke}</g>'
         f'<g fill="{a}" opacity=".55" filter="url(#bl)">{fire}</g>'
         f'<circle cx="300" cy="200" r="90" fill="url(#ex)"/>'
         f'<polygon points="{star_pts(300, 200, 46, 16, 9, .2)}" fill="#ffd27a" opacity=".7" filter="url(#bl2)"/>'
         f'<path d="{sky}" fill="#0a0e13"/>'
         f'<defs>{heli}</defs><use href="#heli" transform="translate(470 66)"/>'
         f'<use href="#heli" transform="translate(220 46) scale(.55)"/>'
         f'<g fill="#05080b" stroke="{a}" stroke-opacity=".45" stroke-width="1.5">'
         f'<rect x="340" y="282" width="170" height="20" rx="10"/><path d="M330 282L350 262H500L520 282Z"/>'
         f'<path d="M390 262L405 242H465L475 262Z"/><rect x="465" y="246" width="92" height="6" rx="2"/></g>'
         f'<g fill="none" stroke="{a}" stroke-opacity=".35">' + "".join(f'<circle cx="{x}" cy="292" r="6"/>' for x in range(356, 500, 22)) + '</g>'
         f'{op(560, 222, .52, "#05080b", a)}{op(598, 236, .44, "#05080b", a)}'
         f'<g fill="{a}" filter="url(#gl)">{embers}</g>')
    return s, defs


def scene_cs2(a):
    defs = ('<pattern id="br" width="40" height="20" patternUnits="userSpaceOnUse"><path d="M0 0H40M0 10H40M20 0V10M0 10V20" '
            'stroke="#000" stroke-opacity=".3" fill="none"/></pattern>'
            f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG1}"/>'
            f'<stop offset="1" stop-color="{mix(a, BG0, .55)}"/></linearGradient>')
    s = (f'<rect width="640" height="300" fill="url(#sky)"/><circle cx="330" cy="120" r="60" fill="{a}" opacity=".35" filter="url(#bl)"/>'
         f'<path d="M0 110L250 140V300L0 320Z" fill="#1d1710"/><path d="M0 110L250 140V300L0 320Z" fill="url(#br)"/>'
         f'<path d="M0 110L250 140" stroke="{a}" stroke-opacity=".5" stroke-width="2"/>'
         f'<rect x="370" y="70" width="270" height="230" fill="#18130d"/><rect x="370" y="70" width="270" height="230" fill="url(#br)"/>'
         f'<path d="M370 70H640" stroke="{a}" stroke-opacity=".5" stroke-width="2"/>'
         f'<rect x="392" y="180" width="62" height="120" fill="{BG0}"/>'
         f'<circle cx="548" cy="165" r="50" fill="none" stroke="{a}" stroke-width="6" filter="url(#gl)" opacity=".9"/>'
         f'<text x="548" y="190" text-anchor="middle" {FONT} font-size="74" font-weight="900" fill="{a}" filter="url(#gl)">A</text>'
         f'<path d="M0 320L250 300H640V360H0Z" fill="#0f0b07"/>'
         f'<g fill="#2a2014" stroke="#000" stroke-opacity=".5"><rect x="256" y="246" width="56" height="56"/><rect x="266" y="210" width="38" height="36"/></g>'
         f'<path d="M256 246L312 302M312 246L256 302" stroke="#000" stroke-opacity=".35"/>'
         f'{op(330, 150, .98, "#07090c", a)}{op(240, 176, .8, "#07090c", a, flip=True)}'
         f'<path d="M560 40l8 8M568 40l-8 8" stroke="{a}" stroke-width="2" opacity=".6"/>')
    return s, defs


def scene_fortnite(a):
    rnd = random.Random(3)
    defs = (f'<radialGradient id="storm" cx=".5" cy=".5" r=".5"><stop offset=".82" stop-color="{a}" stop-opacity="0"/>'
            f'<stop offset=".97" stop-color="{a}" stop-opacity=".55"/><stop offset="1" stop-color="{a}" stop-opacity=".9"/></radialGradient>'
            f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#160a2a"/><stop offset="1" stop-color="#2a1450"/></linearGradient>')
    grid = ""
    for c in range(3):
        for r in range(4):
            grid += f'<rect x="{440 + c * 40}" y="{140 + r * 40}" width="40" height="40"/>'
    conf = "".join(f'<rect x="{rnd.randint(150, 620)}" y="{rnd.randint(20, 240)}" width="5" height="5" fill="{rnd.choice([CYAN, LIME, AMBER, RED, a])}" '
                   f'transform="rotate({rnd.randint(0, 80)} 0 0)" opacity=".0"/>' for _ in range(0))
    s = (f'<rect width="640" height="360" fill="url(#sky)" opacity=".85"/>'
         f'<g fill="{TEXT}" opacity=".07" filter="url(#bl)"><ellipse cx="200" cy="70" rx="90" ry="20"/><ellipse cx="560" cy="50" rx="80" ry="16"/></g>'
         f'<circle cx="470" cy="210" r="230" fill="url(#storm)"/>'
         f'<circle cx="470" cy="210" r="230" fill="none" stroke="{a}" stroke-width="4" filter="url(#gl2)"/>'
         f'<path d="M210 120l-12 30 18-6-6 26" stroke="{TEXT}" stroke-width="3" fill="none" opacity=".6" filter="url(#gl)"/>'
         f'<g fill="{CYAN}" fill-opacity=".08" stroke="{CYAN}" stroke-opacity=".8" stroke-width="2">{grid}</g>'
         f'<g fill="{LIME}" fill-opacity=".14" stroke="{LIME}" stroke-width="2"><path d="M300 300L440 180H460L320 300Z"/>'
         f'<path d="M560 300L600 260V240L560 280Z"/><path d="M560 140L620 90H640L580 140Z"/></g>'
         f'<path d="M420 300H640" stroke="{CYAN}" stroke-width="3" opacity=".7"/>'
         f'<path d="M440 140H560" stroke="{AMBER}" stroke-width="3" opacity=".8" filter="url(#gl)"/>'
         f'<g transform="translate(250 70) rotate(-8)">'
         f'<path d="M-56 0Q0 -26 56 0Q0 -12 -56 0Z" fill="{a}" stroke="{TEXT}" stroke-opacity=".6"/>'
         f'<path d="M-56 0L0 36M56 0L0 36M0 -12V36" stroke="{TEXT}" stroke-opacity=".5"/>'
         f'<circle cx="0" cy="40" r="5" fill="{TEXT}"/><path d="M-5 44H5L4 62H-4Z" fill="{TEXT}"/></g>'
         f'{conf}')
    s += "".join(f'<rect x="{rnd.randint(170, 620)}" y="{rnd.randint(20, 250)}" width="5" height="5" '
                 f'fill="{rnd.choice([CYAN, LIME, AMBER, RED, a])}" opacity=".8"/>' for _ in range(16))
    return s, defs


def scene_apex(a):
    defs = (f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG1}"/>'
            f'<stop offset="1" stop-color="{mix(a, BG0, .45)}"/></linearGradient>')
    hood = '<path d="M9 12L20 -6 31 12Z"/>'
    pack = '<rect x="30" y="26" width="14" height="30" rx="3"/><path d="M38 26V8" stroke="#06080b" stroke-width="2"/>'
    gun = '<path d="M-14 40H40V45H-14Z"/>'
    s = (f'<rect width="640" height="360" fill="url(#sky)"/><circle cx="520" cy="250" r="90" fill="{AMBER}" opacity=".35" filter="url(#bl)"/>'
         f'<path d="M370 75Q250 98 110 66" stroke="{a}" stroke-width="2" stroke-dasharray="6 8" fill="none" opacity=".7"/>'
         f'<path d="M370 76Q250 100 110 70" stroke="{a}" stroke-width="10" fill="none" opacity=".2" filter="url(#bl2)"/>'
         f'<path d="M370 58L556 36L622 48L604 68L424 90L362 80Z" fill="#090c11" stroke="{a}" stroke-opacity=".5"/>'
         f'<path d="M430 88L470 104H560L590 70Z" fill="#090c11"/><path d="M450 46L520 40L516 54Z" fill="{a}" opacity=".5"/>'
         + "".join(f'<circle cx="{x}" cy="{y}" r="2" fill="{AMBER}" filter="url(#gl)"/>' for x, y in [(400, 74), (470, 70), (540, 62), (600, 54)]) +
         f'<ellipse cx="520" cy="104" rx="40" ry="5" fill="{a}" opacity=".7" filter="url(#gl)"/>'
         f'<path d="M300 360L330 266L380 246L520 240L600 255L640 248V360Z" fill="#07090d"/>'
         f'<path d="M330 266L380 246L520 240L600 255L640 248" stroke="{a}" stroke-opacity=".6" stroke-width="2" fill="none"/>'
         f'{stand(402, 158, .84, "#06080b", a, hood)}{stand(446, 140, 1, "#06080b", a, gun)}{stand(500, 156, .84, "#06080b", a, pack)}')
    return s, defs


def chute(x, y, s, col):
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M-20 0Q0 -20 20 0Q10 -5 0 0Q-10 -5 -20 0Z" fill="{col}"/>'
            f'<path d="M-20 0L0 22M20 0L0 22M0 0V22" stroke="{TEXT}" stroke-opacity=".45" fill="none"/>'
            f'<circle cx="0" cy="25" r="3" fill="#06080b"/><path d="M-3 27H3L2 36H-2Z" fill="#06080b"/></g>')


def scene_pubg(a):
    defs = (f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG1}"/>'
            f'<stop offset="1" stop-color="{mix(a, BG2, .55)}"/></linearGradient>'
            f'<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d2230"/><stop offset="1" stop-color="{BG0}"/></linearGradient>')
    s = (f'<rect width="640" height="226" fill="url(#sky)"/><rect y="222" width="640" height="138" fill="url(#sea)"/>'
         f'<circle cx="300" cy="222" r="70" fill="{a}" opacity=".35" filter="url(#bl)"/>'
         f'<path d="M200 238Q260 218 300 224Q340 200 390 214Q440 196 480 214Q540 206 600 232L640 236V246H190Z" fill="#0b130f"/>'
         + "".join(f'<path d="M{x} 260H{x + w}" stroke="{a}" stroke-opacity=".25"/>' for x, w in [(220, 60), (330, 90), (480, 40), (560, 70)]) +
         f'<path d="M160 50L260 44" stroke="{TEXT}" stroke-opacity=".25" stroke-dasharray="4 6"/>'
         f'<path d="M262 40H300L310 44L300 48H262L256 44Z M276 44L270 34H280L288 44Z M276 44L270 54H280L288 44Z" fill="#06080b" stroke="{a}" stroke-opacity=".5"/>'
         f'{chute(240, 110, 1, a)}{chute(320, 80, .8, mix(a, TEXT, .4))}{chute(380, 140, .7, a)}{chute(200, 170, .6, mix(a, BG2, .3))}'
         f'<g transform="translate(500 70)"><path d="M-46 0Q0 -40 46 0Q23 -8 0 0Q-23 -8 -46 0Z" fill="{RED}" opacity=".9"/>'
         f'<path d="M-46 0L-16 60M46 0L16 60M0 0V60" stroke="{TEXT}" stroke-opacity=".5"/>'
         f'<rect x="-26" y="60" width="52" height="40" rx="3" fill="#1d2a3a" stroke="{a}" stroke-width="2"/>'
         f'<path d="M-26 80H26M0 60V100" stroke="{a}" stroke-width="3"/></g>'
         f'<rect x="150" y="18" width="476" height="324" rx="40" fill="none" stroke="{a}" stroke-opacity=".35" stroke-width="3"/>'
         f'<rect x="604" y="150" width="6" height="60" rx="3" fill="{a}" opacity=".35"/>')
    return s, defs


def scene_codm(a):
    rnd = random.Random(7)
    defs = (f'<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><path d="M0 0H4" stroke="{a}" stroke-opacity=".07"/></pattern>')
    tr = ""
    for _ in range(7):
        x1 = rnd.randint(380, 640); y1 = rnd.randint(40, 300); ln = rnd.randint(120, 260)
        tr += f'<path d="M{x1} {y1}L{x1 - ln} {y1 - ln // 3}" stroke="{rnd.choice([a, AMBER, a])}" stroke-width="{rnd.choice([1.5, 2, 3])}" opacity="{rnd.choice([.4, .6, .8])}"/>'
    s = (f'<g filter="url(#gl)" stroke-linecap="round">{tr}</g>'
         f'<path d="M330 360C340 290 400 268 480 262C560 268 610 290 620 360Z" fill="#070c0a" stroke="{a}" stroke-opacity=".4" stroke-width="2"/>'
         f'<path d="M436 190H524L518 252C510 276 494 284 480 284C466 284 450 276 442 252Z" fill="#0c1511" stroke="{a}" stroke-opacity=".3"/>'
         f'<path d="M406 182C406 124 444 96 480 96C516 96 554 124 554 182L558 200H402Z" fill="#0a120f" stroke="{a}" stroke-opacity=".5" stroke-width="2"/>'
         f'<path d="M450 252C466 262 494 262 510 252L506 272C494 280 466 280 454 272Z" fill="#050807"/>'
         f'<rect x="462" y="112" width="36" height="30" rx="6" fill="#050807" stroke="{a}" stroke-opacity=".5"/>'
         f'<rect x="442" y="138" width="34" height="50" rx="10" fill="#050807" stroke="{a}" stroke-opacity=".5"/>'
         f'<rect x="484" y="138" width="34" height="50" rx="10" fill="#050807" stroke="{a}" stroke-opacity=".5"/>'
         f'<g filter="url(#gl2)"><circle cx="459" cy="186" r="13" fill="{a}"/><circle cx="501" cy="186" r="13" fill="{a}"/></g>'
         f'<circle cx="455" cy="182" r="4" fill="#eaffef"/><circle cx="497" cy="182" r="4" fill="#eaffef"/>'
         f'<g stroke="{a}" stroke-width="2" fill="none" opacity=".7"><circle cx="240" cy="130" r="22"/><path d="M240 98V116M240 144V162M208 130H226M254 130H272"/></g>'
         f'<rect width="640" height="360" fill="url(#scan)"/>'
         f'<rect x="150" y="18" width="476" height="324" rx="40" fill="none" stroke="{a}" stroke-opacity=".3" stroke-width="3"/>'
         f'<path d="M170 50V38H182M606 50V38H594M170 310V322H182M606 310V322H594" stroke="{a}" stroke-width="2" fill="none" opacity=".6"/>')
    return s, defs


def scene_minecraft(a):
    def cube(cid, top, left, right):
        return (f'<g id="{cid}"><path d="M0 -16L32 0 0 16-32 0Z" fill="{top}"/><path d="M-32 0L0 16V48L-32 32Z" fill="{left}"/>'
                f'<path d="M32 0L0 16V48L32 32Z" fill="{right}"/><path d="M0 -16L32 0 0 16-32 0Z" fill="none" stroke="#000" stroke-opacity=".25"/></g>')
    g = cube("cg", "#4fbf4f", "#5a3d25", "#47301d") + '<path d="M-32 0L0 16 32 0V6L0 22-32 6Z" fill="#3c9e3c"/>'
    defs = (f'<g id="cg"><path d="M0 -16L32 0 0 16-32 0Z" fill="#4fbf4f"/><path d="M-32 0L0 16V48L-32 32Z" fill="#5a3d25"/>'
            f'<path d="M32 0L0 16V48L32 32Z" fill="#47301d"/><path d="M-32 0L0 16 32 0V7L0 23-32 7Z" fill="#3c9e3c"/></g>'
            + cube("cs", "#59636e", "#3f4750", "#333a42") + cube("cw", "#2b8fd6", "#1f6aa0", "#195784") +
            f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG1}"/>'
            f'<stop offset="1" stop-color="{mix(a, BG1, .7)}"/></linearGradient>')
    N = 7
    hts = {}
    for i in range(N):
        for j in range(N):
            hts[(i, j)] = max(0, round(1.3 + 1.2 * math.sin(i * .9) + 1.1 * math.cos(j * .8 + 1) - (0.6 if i + j > 9 else 0)))
    uses = []
    for sd in range(2 * N - 1):
        for i in range(N):
            j = sd - i
            if not 0 <= j < N:
                continue
            h = hts[(i, j)]
            x = 440 + (i - j) * 32
            for k in range(h + 1):
                y = 150 + (i + j) * 16 - k * 32
                cid = "cw" if h == 0 else ("cg" if k == h else "cs")
                uses.append(f'<use href="#{cid}" x="{x}" y="{y}"/>')
    s = (f'<rect width="640" height="360" fill="url(#sky)"/>'
         f'<rect x="520" y="40" width="54" height="54" fill="{TEXT}" opacity=".85" filter="url(#gl2)"/>'
         f'{"".join(uses)}'
         f'<g transform="translate(150 96) rotate(-35)" filter="url(#gl)">'
         f'<rect x="-5" y="-26" width="10" height="110" rx="2" fill="#8a6440" stroke="{a}" stroke-opacity=".6"/>'
         f'<path d="M-62 -6Q0 -48 62 -6L54 2Q0 -30 -54 2Z" fill="{TEXT}" stroke="{a}" stroke-width="2"/></g>'
         f'<use href="#cg" transform="translate(270 70) scale(.5)"/><use href="#cs" transform="translate(320 40) scale(.35)"/>')
    return s, defs


def scene_lol(a):
    c45 = math.cos(math.pi / 4)

    def T(x, y):
        return 470 + (x - y) * c45, 70 + (x + y) * c45 * .55
    spiral = []
    for i in range(90):
        t = i / 89 * 4 * math.pi
        r = 8 + t * 14
        spiral.append(f"{f1(470 + r * math.cos(t))} {f1(165 + r * .5 * math.sin(t))}")
    tw = ""
    for lx, ly in [(20, 150), (20, 80), (90, 20), (160, 20), (220, 90), (220, 160), (150, 220), (80, 220), (85, 155), (155, 85)]:
        x, y = T(lx, ly)
        tw += f'<circle cx="{f1(x)}" cy="{f1(y)}" r="4"/>'
    n1 = T(20, 220); n2 = T(220, 20)

    def crystal(x, y, col):
        return (f'<g filter="url(#gl2)"><path d="M{f1(x)} {f1(y - 30)}L{f1(x + 11)} {f1(y - 6)}L{f1(x)} {f1(y + 6)}L{f1(x - 11)} {f1(y - 6)}Z" fill="{col}"/></g>'
                f'<path d="M{f1(x)} {f1(y - 30)}V{f1(y + 6)}" stroke="#fff" stroke-opacity=".6"/>')
    defs = (f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#08101c"/><stop offset="1" stop-color="#0b1a2a"/></linearGradient>')
    s = (f'<rect width="640" height="360" fill="url(#sky)"/>'
         f'<path d="M{" L".join(spiral)}" fill="none" stroke="{a}" stroke-width="2" opacity=".45" filter="url(#gl)"/>'
         f'<g transform="matrix({f1(c45)} {f1(c45 * .55)} {f1(-c45)} {f1(c45 * .55)} 470 70)">'
         f'<rect width="240" height="240" rx="10" fill="#0d1a26" stroke="{a}" stroke-opacity=".5" stroke-width="2"/>'
         f'<g fill="#122a1f" opacity=".9"><circle cx="70" cy="90" r="22"/><circle cx="150" cy="170" r="22"/><circle cx="165" cy="65" r="16"/><circle cx="70" cy="175" r="16"/></g>'
         f'<path d="M20 20L220 220" stroke="{a}" stroke-opacity=".35" stroke-width="14"/>'
         f'<path d="M20 220V20H220M20 220H220V20M20 220L220 20" fill="none" stroke="{TEXT}" stroke-opacity=".28" stroke-width="9" stroke-linecap="round"/></g>'
         f'<g fill="{a}" filter="url(#gl)">{tw}</g>'
         f'{crystal(n1[0], n1[1], a)}{crystal(n2[0], n2[1], RED)}'
         f'<circle cx="470" cy="165" r="6" fill="{TEXT}" filter="url(#gl2)"/>')
    return s, defs


def scene_helldivers(a):
    defs = (f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG1}"/>'
            f'<stop offset="1" stop-color="{mix(a, BG0, .72)}"/></linearGradient>'
            f'<radialGradient id="pl" cx=".35" cy=".35"><stop offset="0" stop-color="{mix(a, "#ff8a3d", .4)}"/>'
            f'<stop offset="1" stop-color="#3a1f0a"/></radialGradient>'
            f'<linearGradient id="trail" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{a}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{a}"/></linearGradient>')

    def pod(x, y, s):
        return (f'<g transform="translate({x} {y}) rotate(28) scale({s})"><rect x="-6" y="-120" width="12" height="96" fill="url(#trail)" filter="url(#bl2)"/>'
                f'<path d="M-9 -32H9L13 18L0 34L-13 18Z" fill="#1a1f26" stroke="{a}" stroke-width="1.5"/>'
                f'<circle cx="0" cy="34" r="7" fill="{a}" filter="url(#gl)"/></g>')

    def bug(x, y, s):
        return (f'<g transform="translate({x} {y}) scale({s})" fill="#08090b" stroke="#08090b" stroke-width="2.5">'
                f'<path d="M0 0C10 -14 34 -14 44 0C34 8 10 8 0 0Z"/><circle cx="48" cy="-2" r="7"/>'
                f'<path d="M10 2L2 18M18 4L14 20M28 4L32 20M36 2L44 18M8 -6L-4 -18M38 -8L50 -20" fill="none"/></g>')
    s = (f'<rect width="640" height="360" fill="url(#sky)"/>'
         f'<circle cx="510" cy="92" r="62" fill="url(#pl)"/><ellipse cx="510" cy="92" rx="98" ry="16" fill="none" stroke="{a}" stroke-opacity=".5" stroke-width="3" transform="rotate(-14 510 92)"/>'
         f'<circle cx="400" cy="50" r="10" fill="{mix(a, BG2, .5)}"/>'
         f'{pod(250, 120, 1)}{pod(340, 70, .7)}{pod(600, 180, .8)}'
         f'<path d="M380 270Q450 236 520 246Q580 230 640 240V300H380Z" fill="#100d08"/>'
         f'{bug(450, 246, .7)}{bug(520, 240, .9)}{bug(585, 238, .6)}'
         f'<path d="M0 300Q120 262 240 280Q330 272 420 296Q520 282 640 300V360H0Z" fill="#090806" stroke="{a}" stroke-opacity=".35"/>'
         f'{op(150, 140, .9, "#07080a", a, visor=a)}{op(220, 156, .82, "#07080a", a, visor=a)}'
         f'{op(290, 162, .76, "#07080a", a, visor=a)}{op(354, 176, .66, "#07080a", a, visor=a)}')
    return s, defs


def scene_fc(a):
    defs = (f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#06111a"/>'
            f'<stop offset="1" stop-color="{mix(a, BG0, .7)}"/></linearGradient>'
            f'<linearGradient id="pitch" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d3a24"/>'
            f'<stop offset="1" stop-color="#06180f"/></linearGradient>'
            f'<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{TEXT}" stop-opacity=".35"/>'
            f'<stop offset="1" stop-color="{TEXT}" stop-opacity="0"/></linearGradient>')
    stripes = "".join(f'<path d="M{120 + i * 80} 360L{250 + i * 56} 190H{278 + i * 56}L{200 + i * 80} 360Z" fill="#fff" opacity=".035"/>' for i in range(7))
    crowd = "".join(f'<circle cx="{x}" cy="{150 + (x * 7) % 9}" r="3"/>' for x in range(150, 640, 9))

    def light(x):
        return (f'<path d="M{x - 18} 40L{x - 140} 200H{x + 140}Z" fill="url(#beam)" opacity=".5"/>'
                f'<rect x="{x - 22}" y="28" width="44" height="16" rx="3" fill="#0b1219" stroke="{TEXT}" stroke-opacity=".5"/>'
                + "".join(f'<circle cx="{f1(x - 14 + k * 9.5)}" cy="36" r="3" fill="{TEXT}" filter="url(#gl)"/>' for k in range(4)))
    s = (f'<rect width="640" height="360" fill="url(#sky)"/>'
         f'{light(300)}{light(560)}'
         f'<path d="M140 190Q390 120 640 150V200H140Z" fill="#0b141c"/><g fill="{a}" opacity=".35">{crowd}</g>'
         f'<path d="M80 360L250 190H640V360Z" fill="url(#pitch)"/>{stripes}'
         f'<g fill="none" stroke="{TEXT}" stroke-opacity=".45" stroke-width="2">'
         f'<path d="M250 190H640"/><path d="M330 360L410 190"/><ellipse cx="470" cy="262" rx="70" ry="22"/></g>'
         f'<g fill="none" stroke="{TEXT}" stroke-width="4" stroke-linejoin="round"><path d="M520 196V140H624V196"/></g>'
         f'<path d="M520 140H624V196H520Z" fill="{TEXT}" opacity=".06"/>'
         f'<g stroke="{TEXT}" stroke-opacity=".18">' + "".join(f'<path d="M{x} 140V196"/>' for x in range(530, 624, 10)) + '</g>'
         f'<g transform="translate(400 270)" filter="url(#gl)"><circle r="22" fill="{TEXT}"/>'
         f'<path d="M0 -9L8.5 -2.8 5.3 7.3H-5.3L-8.5 -2.8Z" fill="#0b1219"/>'
         f'<path d="M0 -9V-21M8.5 -2.8L19 -7M5.3 7.3L12 17M-5.3 7.3L-12 17M-8.5 -2.8L-19 -7" stroke="#0b1219" stroke-width="2"/></g>'
         f'<path d="M378 280Q300 300 220 292" stroke="{a}" stroke-width="3" fill="none" stroke-dasharray="4 8" opacity=".8"/>'
         f'{stand(250, 200, .9, "#05080b", a)}')
    return s, defs


def scene_gta(a):
    defs = (f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1a0d2e"/>'
            f'<stop offset=".55" stop-color="{mix(a, "#ff8a3d", .35)}"/><stop offset="1" stop-color="#ffb547"/></linearGradient>')
    sun_lines = "".join(f'<rect x="380" y="{150 + k * 12}" width="200" height="{3 + k}" fill="url(#sky)"/>' for k in range(6))
    sky = ("M150 360V250H178V200H200V180H220V230H246V150H262V120H276V150H292V236H320V196H344V172H360V214H390"
           "V160H414V110H426V160H446V220H476V190H500V232H530V170H556V140H572V170H588V226H612V204H640V360Z")
    wins = "".join(f'<rect x="{x}" y="{y}" width="3" height="4"/>' for x in range(250, 290, 8) for y in range(160, 230, 12)) + \
        "".join(f'<rect x="{x}" y="{y}" width="3" height="4"/>' for x in range(396, 440, 8) for y in range(122, 210, 12))

    def palm(x, y, s):
        return (f'<g transform="translate({x} {y}) scale({s})" fill="#07040c"><path d="M-3 0Q4 -60 2 -110H8Q12 -60 5 0Z"/>'
                f'<path d="M5 -110Q-30 -120 -60 -90Q-30 -108 5 -104Z"/><path d="M5 -110Q40 -124 70 -96Q38 -110 5 -104Z"/>'
                f'<path d="M5 -110Q-10 -140 -40 -146Q-14 -130 2 -106Z"/><path d="M5 -110Q24 -142 54 -140Q26 -128 8 -106Z"/>'
                f'<path d="M5 -110Q-26 -96 -44 -60Q-20 -92 5 -104Z"/></g>')
    s = (f'<rect width="640" height="360" fill="url(#sky)"/>'
         f'<circle cx="480" cy="180" r="92" fill="#ffd27a" opacity=".9"/>{sun_lines}'
         f'<path d="{sky}" fill="#0b0614"/><g fill="{AMBER}" opacity=".7">{wins}</g>'
         f'<path d="M150 300H640V360H150Z" fill="#06030a"/>'
         f'<path d="M150 318H640" stroke="{a}" stroke-width="2" stroke-dasharray="20 14" opacity=".7"/>'
         f'<g transform="translate(330 268)"><path d="M0 30L14 12Q30 0 70 0H120Q150 0 168 16L196 22Q210 26 210 36V44H0Z" fill="#0d0716" stroke="{a}" stroke-width="2"/>'
         f'<path d="M40 14Q52 4 76 4H112Q136 4 150 16Z" fill="{a}" opacity=".35"/>'
         f'<circle cx="44" cy="44" r="14" fill="#06030a" stroke="{a}" stroke-width="2"/><circle cx="164" cy="44" r="14" fill="#06030a" stroke="{a}" stroke-width="2"/>'
         f'<path d="M206 30H214" stroke="{AMBER}" stroke-width="4" filter="url(#gl)"/></g>'
         f'{palm(190, 300, 1)}{palm(610, 300, .8)}')
    return s, defs


def scene_rocket(a):
    rnd = random.Random(11)
    defs = (f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#060c1c"/>'
            f'<stop offset="1" stop-color="{mix(a, BG0, .6)}"/></linearGradient>'
            f'<linearGradient id="boost" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="{AMBER}"/>'
            f'<stop offset=".4" stop-color="{a}" stop-opacity=".8"/><stop offset="1" stop-color="{a}" stop-opacity="0"/></linearGradient>')
    stars = "".join(f'<circle cx="{rnd.randint(150, 640)}" cy="{rnd.randint(10, 120)}" r="{rnd.choice([.8, 1.2, 1.6])}"/>' for _ in range(30))
    hexes = "".join(f'<path d="M{x} {y}l10 -6 10 6v12l-10 6 -10 -6z"/>' for x in range(150, 640, 24) for y in (40, 58) if (x // 24 + y) % 2)
    s = (f'<rect width="640" height="360" fill="url(#sky)"/><g fill="{TEXT}" opacity=".6">{stars}</g>'
         f'<g fill="none" stroke="{a}" stroke-opacity=".18">{hexes}</g>'
         f'<path d="M150 130Q395 96 640 130V250H150Z" fill="#0a1426" stroke="{a}" stroke-opacity=".35"/>'
         f'<path d="M100 360L190 230H640V360Z" fill="#0b1a2e"/>'
         f'<g fill="none" stroke="{a}" stroke-opacity=".5" stroke-width="2"><path d="M190 230H640"/><path d="M380 360L420 230"/>'
         f'<ellipse cx="470" cy="292" rx="80" ry="24"/></g>'
         f'<g transform="translate(520 120)" filter="url(#gl2)"><circle r="40" fill="#cfd8e3"/>'
         f'<g fill="none" stroke="#7f8ea3" stroke-width="3"><path d="M-40 0H40M0 -40V40"/><ellipse rx="40" ry="16"/><ellipse rx="16" ry="40"/></g></g>'
         f'<g transform="translate(300 228) rotate(-12)"><rect x="-150" y="8" width="150" height="16" rx="8" fill="url(#boost)" filter="url(#bl2)"/>'
         f'<path d="M0 26L10 6Q20 0 48 0H96Q120 0 132 12L150 16Q160 20 160 28V36H0Z" fill="#0d1626" stroke="{a}" stroke-width="2.5"/>'
         f'<path d="M34 8Q44 2 62 2H92Q108 2 118 12Z" fill="{a}" opacity=".45"/>'
         f'<circle cx="34" cy="38" r="12" fill="#05080f" stroke="{a}" stroke-width="2"/><circle cx="128" cy="38" r="12" fill="#05080f" stroke="{a}" stroke-width="2"/></g>'
         f'<path d="M380 196Q450 140 486 136" stroke="{TEXT}" stroke-width="2" stroke-dasharray="3 7" fill="none" opacity=".6"/>')
    return s, defs


def scene_default(a):
    pad = ("M-100 -30C-100 -55 -80 -60 -60 -60H60C80 -60 100 -55 100 -30L118 40C124 66 100 80 82 64L56 40H-56L-82 64"
           "C-100 80 -124 66 -118 40Z")
    s = (f'<g transform="translate(440 160)"><path d="{pad}" fill="#0b131b" stroke="{a}" stroke-width="3" filter="url(#gl2)"/>'
         f'<path d="M-72 -14H-60V-26H-48V-14H-36V-2H-48V10H-60V-2H-72Z" fill="{a}" opacity=".85"/>'
         f'<g filter="url(#gl)"><circle cx="58" cy="-24" r="8" fill="{CYAN}"/><circle cx="76" cy="-8" r="8" fill="{RED}"/>'
         f'<circle cx="40" cy="-8" r="8" fill="{LIME}"/><circle cx="58" cy="8" r="8" fill="{AMBER}"/></g>'
         f'<circle cx="-28" cy="22" r="13" fill="none" stroke="{a}" stroke-opacity=".6" stroke-width="3"/>'
         f'<circle cx="28" cy="22" r="13" fill="none" stroke="{a}" stroke-opacity=".6" stroke-width="3"/></g>'
         f'<g fill="{a}" opacity=".5">' + "".join(f'<circle cx="{x}" cy="{y}" r="2"/>' for x, y in [(250, 70), (600, 60), (320, 260), (610, 280), (280, 150)]) + '</g>')
    return s, ""


GAMES = [
    ("battlefield", "Battlefield 6", "Large-scale FPS", "#ff8a3d", scene_battlefield, "BF6"),
    ("cs2", "Counter-Strike 2", "Tactical shooter", "#f5b942", scene_cs2, "CS2"),
    ("fortnite", "Fortnite", "Battle royale", "#a855f7", scene_fortnite, "FN"),
    ("apex", "Apex Legends", "Squad battle royale", "#ff4d4d", scene_apex, "APX"),
    ("pubg-mobile", "PUBG Mobile", "Mobile battle royale", "#f2c14e", scene_pubg, "PUBG"),
    ("codm", "Call of Duty: Mobile", "Mobile shooter", "#3ddc84", scene_codm, "COD"),
    ("minecraft", "Minecraft", "Sandbox", "#5bd65b", scene_minecraft, "MC"),
    ("lol", "League of Legends", "MOBA", "#4fc3f7", scene_lol, "LOL"),
    ("helldivers2", "Helldivers 2", "Co-op shooter", "#ffd23f", scene_helldivers, "HD2"),
    ("fc", "EA SPORTS FC 27", "Football", "#3fe0c5", scene_fc, "FC"),
    ("gta", "GTA Online", "Open-world crime", "#ff5fa2", scene_gta, "GTA"),
    ("rocket-league", "Rocket League", "Car soccer", "#3b8bff", scene_rocket, "RL"),
    ("default", "Game", "Any genre", GREEN, scene_default, "GG"),
]

MOTIF = {
    "battlefield": f'<polygon points="{star_pts(100, 28, 12, 5, 7)}"/>',
    "cs2": '<g fill="none" stroke-width="3"><circle cx="100" cy="28" r="8"/><path d="M100 14V22M100 34V42M86 28H94M106 28H114"/></g>',
    "fortnite": '<path d="M88 40H112V16Z"/>',
    "apex": '<path d="M100 14L114 40H86ZM100 26L94 36H106Z" fill-rule="evenodd"/>',
    "pubg-mobile": '<path d="M86 28Q100 10 114 28Q107 24 100 28Q93 24 86 28ZM99 28H101V40H99Z"/>',
    "codm": '<path d="M95 42V26Q100 12 105 26V42Z"/>',
    "minecraft": '<path d="M100 14L112 20V34L100 40L88 34V20Z"/>',
    "lol": '<path d="M100 12L109 28L100 44L91 28Z"/>',
    "helldivers2": '<path d="M95 14H105L108 34L100 42L92 34Z"/>',
    "fc": '<circle cx="100" cy="28" r="11" fill="none" stroke-width="3"/>',
    "gta": '<path d="M100 12L104 24H116L106 31L110 43L100 36L90 43L94 31L84 24H96Z"/>',
    "rocket-league": '<path d="M84 34L96 20H110L116 26V34Z"/>',
    "default": '<circle cx="100" cy="28" r="9"/>',
}


def icon(gid, accent, mono):
    dark = mix(accent, BG0, .62)
    size = {1: 60, 2: 52, 3: 40, 4: 32}[len(mono)]
    d = (f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{mix(accent, TEXT, .15)}"/>'
         f'<stop offset=".55" stop-color="{accent}"/><stop offset="1" stop-color="{dark}"/></linearGradient>'
         f'<linearGradient id="gloss" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".35"/>'
         f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
         f'<pattern id="p" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M0 10L10 0" stroke="#000" stroke-opacity=".08"/></pattern></defs>'
         f'<rect width="128" height="128" rx="28" fill="url(#g)"/><rect width="128" height="128" rx="28" fill="url(#p)"/>'
         f'<path d="M28 0H100A28 28 0 0 1 128 28V52Q64 70 0 52V28A28 28 0 0 1 28 0Z" fill="url(#gloss)"/>'
         f'<g fill="{BG0}" stroke="{BG0}" fill-opacity=".55" stroke-opacity=".55">{MOTIF[gid]}</g>'
         f'<text x="64" y="{f1(76 + size * .12)}" text-anchor="middle" {FONT} font-size="{size}" font-weight="900" '
         f'letter-spacing="-1" fill="{BG0}">{mono}</text>'
         f'<rect x="2" y="2" width="124" height="124" rx="26" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width="2"/>')
    save(f"games/{gid}-icon.svg", svg(128, 128, d))


# ---------------------------------------------------------------- banners
def banner(n, defs, body):
    d = (f'<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG1}"/>'
         f'<stop offset="1" stop-color="{BG0}"/></linearGradient>{glow("gl", 3)}{blur("bl", 18)}{defs}</defs>'
         f'<rect width="1200" height="300" fill="url(#bg)"/>{body}')
    save(f"banners/banner-{n}.svg", svg(1200, 300, d))


def banners():
    # 1 circuit
    r = random.Random(11)
    tr, dots = [], []
    for _ in range(34):
        x = r.randrange(0, 1200, 20); y = r.randrange(20, 290, 20)
        p = f"M{x} {y}"
        for _ in range(r.randint(2, 4)):
            mv = r.choice(["h", "d", "u"]); L = r.randrange(40, 160, 20)
            if mv == "h": x += L; p += f"H{x}"
            elif mv == "d": x += 30; y += 30 if y < 250 else -30; p += f"L{x} {y}"
            else: x += 30; y -= 30 if y > 50 else -30; p += f"L{x} {y}"
        tr.append(f'<path d="{p}" stroke="{r.choice([GREEN, CYAN, GREEN])}"/>')
        dots.append(f'<circle cx="{x}" cy="{y}" r="4"/>')
    chips = "".join(f'<rect x="{x}" y="{y}" width="70" height="46" rx="6"/>' for x, y in [(240, 120), (820, 80), (560, 200)])
    banner(1, f'<radialGradient id="rg" cx=".5" cy=".5" r=".7"><stop offset="0" stop-color="{GREEN}" stop-opacity=".18"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></radialGradient>',
           f'<rect width="1200" height="300" fill="url(#rg)"/><g fill="none" stroke-width="2" opacity=".55" filter="url(#gl)">{"".join(tr)}</g>'
           f'<g fill="{BG0}" stroke="{CYAN}" stroke-width="2" filter="url(#gl)">{"".join(dots)}</g>'
           f'<g fill="{BG2}" stroke="{GREEN}" stroke-width="2" filter="url(#gl)">{chips}</g>')
    # 2 hex grid
    R = 22; w = math.sqrt(3) * R

    def hexp(cx, cy, rr):
        return " ".join(f"{f1(cx + rr * math.cos(math.pi / 6 + k * math.pi / 3))},{f1(cy + rr * math.sin(math.pi / 6 + k * math.pi / 3))}" for k in range(6))
    pat = "".join(f'<polygon points="{hexp(cx, cy, R)}"/>' for cx, cy in [(w / 2, R), (0, 2.5 * R), (w, 2.5 * R), (0, -.5 * R), (w, -.5 * R)])
    hl = ""
    r = random.Random(5)
    for _ in range(26):
        col = r.randrange(0, 36); row = r.randrange(0, 5)
        cx = w / 2 + col * w + (0 if row % 2 == 0 else -w / 2); cy = R + row * 1.5 * R
        hl += f'<polygon points="{hexp(cx, cy, R - 3)}" fill="{r.choice([CYAN, GREEN, CYAN])}" opacity="{r.choice([.12, .2, .35, .6])}"/>'
    banner(2, f'<pattern id="hx" width="{f1(w)}" height="{3 * R}" patternUnits="userSpaceOnUse"><g fill="none" stroke="{CYAN}" stroke-opacity=".18">{pat}</g></pattern>'
              f'<linearGradient id="sw" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset=".5" stop-color="{CYAN}" stop-opacity=".22"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>',
           f'<rect width="1200" height="300" fill="url(#sw)"/><rect width="1200" height="300" fill="url(#hx)"/><g filter="url(#gl)">{hl}</g>')
    # 3 aurora
    r = random.Random(9)
    stars = "".join(f'<circle cx="{r.randint(0, 1200)}" cy="{r.randint(0, 300)}" r="{r.choice([.8, 1, 1.4])}" opacity="{r.choice([.4, .7, 1])}"/>' for _ in range(60))
    bands = ""
    for i, (c1, c2, y0) in enumerate([(GREEN, CYAN, 120), (CYAN, PURPLE, 90), (LIME, GREEN, 160)]):
        bands += (f'<linearGradient id="a{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c1}" stop-opacity="0"/>'
                  f'<stop offset=".5" stop-color="{c1}" stop-opacity=".7"/><stop offset="1" stop-color="{c2}" stop-opacity="0"/></linearGradient>')
    paths = (f'<path d="M0 140C200 60 380 200 600 110S1000 60 1200 130V210C1000 150 820 220 600 190S200 140 0 230Z" fill="url(#a0)"/>'
             f'<path d="M0 80C240 20 420 140 680 60S1040 40 1200 70V140C1020 110 860 160 660 130S220 90 0 150Z" fill="url(#a1)"/>'
             f'<path d="M0 200C260 150 500 250 760 180S1080 170 1200 200V260C1060 230 900 270 720 250S260 220 0 270Z" fill="url(#a2)"/>')
    banner(3, bands, f'<g fill="{TEXT}">{stars}</g><g filter="url(#bl)" opacity=".85">{paths}</g>'
                     f'<path d="M0 140C200 60 380 200 600 110S1000 60 1200 130" fill="none" stroke="{GREEN}" stroke-opacity=".5" stroke-width="2" filter="url(#gl)"/>')
    # 4 city skyline
    r = random.Random(4)
    far, near, win = "", "", ""
    x = 0
    while x < 1200:
        bw = r.randint(30, 70); bh = r.randint(60, 150); far += f'<rect x="{x}" y="{300 - bh - 40}" width="{bw}" height="{bh + 40}"/>'; x += bw + r.randint(0, 6)
    x = 0
    while x < 1200:
        bw = r.randint(40, 90); bh = r.randint(70, 200); near += f'<rect x="{x}" y="{300 - bh}" width="{bw}" height="{bh}"/>'
        for wx in range(x + 6, x + bw - 8, 12):
            for wy in range(300 - bh + 10, 296, 16):
                if r.random() < .16: win += f"M{wx} {wy}h5v7h-5z"
        if r.random() < .3: near += f'<rect x="{x + bw // 2 - 1}" y="{300 - bh - 24}" width="2" height="24"/>'
        x += bw + r.randint(2, 10)
    banner(4, f'<linearGradient id="sk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a0f1e"/><stop offset=".7" stop-color="#1a1240"/><stop offset="1" stop-color="{CYAN}" stop-opacity=".5"/></linearGradient>',
           f'<rect width="1200" height="300" fill="url(#sk)"/><circle cx="960" cy="70" r="34" fill="{TEXT}" opacity=".9" filter="url(#gl)"/>'
           f'<circle cx="960" cy="70" r="70" fill="{CYAN}" opacity=".18" filter="url(#bl)"/><g fill="#101a2a">{far}</g><g fill="#070b12">{near}</g>'
           f'<path d="{win}" fill="{AMBER}" opacity=".75"/><rect y="296" width="1200" height="4" fill="{CYAN}" opacity=".6" filter="url(#gl)"/>')
    # 5 topographic
    paths = ""
    for (cx, cy, col, ph) in [(260, 150, LIME, 0), (760, 120, AMBER, 1.3), (1080, 230, LIME, 2.6)]:
        for k in range(7):
            pts = []
            for i in range(26):
                t = 2 * math.pi * i / 26
                rr = 18 + k * 22 + 9 * math.sin(3 * t + ph + k * .3) + 6 * math.sin(5 * t - ph)
                pts.append((cx + rr * 1.5 * math.cos(t), cy + rr * math.sin(t)))
            mids = [((pts[i][0] + pts[(i + 1) % 26][0]) / 2, (pts[i][1] + pts[(i + 1) % 26][1]) / 2) for i in range(26)]
            dd = f"M{mids[-1][0]:.0f} {mids[-1][1]:.0f}" + "".join(f"Q{pts[i][0]:.0f} {pts[i][1]:.0f} {mids[i][0]:.0f} {mids[i][1]:.0f}" for i in range(26)) + "Z"
            paths += f'<path d="{dd}" stroke="{col}" stroke-opacity="{f1(.75 - k * .08)}"/>'
    banner(5, "", f'<g fill="none" stroke-width="1.5">{paths}</g><circle cx="260" cy="150" r="5" fill="{LIME}" filter="url(#gl)"/>'
                  f'<circle cx="760" cy="120" r="5" fill="{AMBER}" filter="url(#gl)"/>')
    # 6 nebula
    r = random.Random(21)
    stars = "".join(f'<circle cx="{r.randint(0, 1200)}" cy="{r.randint(0, 300)}" r="{r.choice([.6, .9, 1.2, 1.6])}" opacity="{r.choice([.35, .6, .9])}"/>' for _ in range(110))
    glints = "".join(f'<path d="M{x - 9} {y}H{x + 9}M{x} {y - 9}V{y + 9}" stroke="{TEXT}" stroke-width="1.5"/><circle cx="{x}" cy="{y}" r="2.5" fill="{TEXT}"/>' for x, y in [(310, 80), (880, 200), (1050, 60)])
    banner(6, blur("nb", 34),
           f'<g filter="url(#nb)"><ellipse cx="380" cy="150" rx="260" ry="80" fill="{PURPLE}" opacity=".45"/>'
           f'<ellipse cx="620" cy="120" rx="200" ry="70" fill="{CYAN}" opacity=".3"/><ellipse cx="860" cy="190" rx="240" ry="70" fill="{RED}" opacity=".3"/>'
           f'<ellipse cx="520" cy="170" rx="120" ry="40" fill="{GREEN}" opacity=".22"/></g>'
           f'<g fill="{TEXT}">{stars}</g><g filter="url(#gl)">{glints}</g>')
    # 7 digital camo
    r = random.Random(8)
    cols = {1: "#121b25", 2: "#0f2a24", 3: "#13333a", 4: GREEN}
    ps = {k: "" for k in cols}
    S = 30
    for i in range(40):
        for j in range(10):
            v = math.sin(i * .45) + math.cos(j * .9 + i * .2) + math.sin((i + j) * .3) + r.uniform(-.8, .8)
            k = 0 if v < -.4 else 1 if v < .3 else 2 if v < .9 else 3 if v < 1.9 else 4
            if k: ps[k] += f"M{i * S} {j * S}h{S}v{S}h-{S}z"
    op35 = ' opacity=".35"'
    camo = "".join(f'<path d="{ps[k]}" fill="{c}"{op35 if k == 4 else ""}/>' for k, c in cols.items())
    banner(7, f'<linearGradient id="vg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{BG0}" stop-opacity=".7"/><stop offset=".5" stop-color="{BG0}" stop-opacity="0"/><stop offset="1" stop-color="{BG0}" stop-opacity=".7"/></linearGradient>',
           f'{camo}<path d="M-20 260L300 40M820 300L1100 20" stroke="{GREEN}" stroke-width="2" opacity=".5" filter="url(#gl)"/><rect width="1200" height="300" fill="url(#vg)"/>')
    # 8 synthwave
    stripes = "".join(f'<rect x="460" y="{y}" width="280" height="{h}" fill="#000"/>' for y, h in [(150, 4), (166, 6), (182, 8), (198, 10)])
    vl = "".join(f'<path d="M{600 + i * 9} 210L{600 + i * 110} 300"/>' for i in range(-12, 13))
    hl = "".join(f'<path d="M0 {f1(210 + 90 * (k / 7) ** 2)}H1200"/>' for k in range(1, 8))
    banner(8, f'<linearGradient id="sk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#12082a"/><stop offset=".55" stop-color="#3a1046"/><stop offset="1" stop-color="{RED}" stop-opacity=".8"/></linearGradient>'
              f'<linearGradient id="sun" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{AMBER}"/><stop offset="1" stop-color="{RED}"/></linearGradient>'
              f'<mask id="m"><rect width="1200" height="300" fill="#fff"/>{stripes}</mask>',
           f'<rect width="1200" height="210" fill="url(#sk)"/><circle cx="600" cy="200" r="150" fill="{RED}" opacity=".35" filter="url(#bl)"/>'
           f'<circle cx="600" cy="170" r="110" fill="url(#sun)" mask="url(#m)"/>'
           f'<path d="M0 210L120 150L210 190L330 120L450 210H760L860 140L960 186L1060 130L1200 200V210Z" fill="#14082a" stroke="{PURPLE}" stroke-width="2"/>'
           f'<rect y="210" width="1200" height="90" fill="#0b0618"/><g stroke="{RED}" stroke-opacity=".7" stroke-width="1.5" filter="url(#gl)">{vl}{hl}</g>'
           f'<path d="M0 210H1200" stroke="{AMBER}" stroke-width="2" filter="url(#gl)"/>')


# ---------------------------------------------------------------- avatars
SHOULDERS = "M24 256C30 204 74 182 128 182C182 182 226 204 232 256Z"


def avatar(n, c, body, sh="#0c121a", bgc=None):
    bgc = bgc or c
    d = (f'<defs><radialGradient id="bg" cx=".5" cy=".42" r=".7"><stop offset="0" stop-color="{mix(bgc, BG0, .45)}"/>'
         f'<stop offset=".7" stop-color="{mix(bgc, BG0, .85)}"/><stop offset="1" stop-color="{BG0}"/></radialGradient>'
         f'<linearGradient id="v" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{mix(c, TEXT, .35)}"/><stop offset="1" stop-color="{c}"/></linearGradient>'
         f'<pattern id="p" width="16" height="16" patternUnits="userSpaceOnUse"><path d="M16 0H0V16" fill="none" stroke="{TEXT}" stroke-opacity=".05"/></pattern>'
         f'{glow("gl", 4)}</defs>'
         f'<rect width="256" height="256" fill="url(#bg)"/><rect width="256" height="256" fill="url(#p)"/>'
         f'<circle cx="128" cy="118" r="96" fill="none" stroke="{bgc}" stroke-opacity=".25" stroke-width="2" stroke-dasharray="4 10"/>'
         f'<path d="{SHOULDERS}" fill="{sh}" stroke="{c}" stroke-opacity=".55" stroke-width="2"/>'
         f'<path d="M104 196L128 214L152 196" fill="none" stroke="{c}" stroke-opacity=".6" stroke-width="3"/>{body}')
    save(f"avatars/avatar-{n}.svg", svg(256, 256, d))


def avatars():
    D = "#121b25"
    avatar(1, GREEN,
           f'<path d="M74 120C74 74 100 54 128 54C156 54 182 74 182 120V150C182 166 168 176 152 176H104C88 176 74 166 74 150Z" fill="{D}" stroke="{GREEN}" stroke-opacity=".6" stroke-width="2"/>'
           f'<rect x="64" y="112" width="12" height="34" rx="5" fill="#1b2633"/><rect x="180" y="112" width="12" height="34" rx="5" fill="#1b2633"/>'
           f'<path d="M84 104H172C177 104 179 109 177 114L170 134C168 138 165 140 160 140H96C91 140 88 138 86 134L79 114C77 109 79 104 84 104Z" fill="url(#v)" filter="url(#gl)"/>'
           f'<path d="M92 112H140" stroke="#fff" stroke-opacity=".6" stroke-width="3" stroke-linecap="round"/><path d="M128 56V90" stroke="{GREEN}" stroke-opacity=".4" stroke-width="3"/>')
    avatar(2, CYAN,
           f'<path d="M128 48L178 74L186 140L160 178H96L70 140L78 74Z" fill="{D}" stroke="{CYAN}" stroke-opacity=".7" stroke-width="2"/>'
           f'<path d="M88 104L128 128L168 104L164 124L128 148L92 124Z" fill="url(#v)" filter="url(#gl)"/>'
           f'<path d="M128 48V96M78 74L100 92M178 74L156 92" stroke="{CYAN}" stroke-opacity=".5" stroke-width="2"/>'
           f'<path d="M108 160H148" stroke="{CYAN}" stroke-opacity=".6" stroke-width="3"/>')
    avatar(3, RED,
           f'<path d="M76 116C76 70 100 52 128 52C156 52 180 70 180 116C180 150 166 178 128 180C90 178 76 150 76 116Z" fill="#141a22" stroke="{RED}" stroke-opacity=".5" stroke-width="2"/>'
           f'<circle cx="104" cy="110" r="20" fill="#0a0e13"/><circle cx="152" cy="110" r="20" fill="#0a0e13"/>'
           f'<g filter="url(#gl)"><circle cx="104" cy="110" r="14" fill="url(#v)"/><circle cx="152" cy="110" r="14" fill="url(#v)"/></g>'
           f'<path d="M112 140H144L152 172H104Z" fill="#1d252f"/><circle cx="128" cy="168" r="16" fill="#252f3b" stroke="{RED}" stroke-opacity=".6" stroke-width="2"/>'
           f'<path d="M118 168H138M128 158V178" stroke="{RED}" stroke-opacity=".7" stroke-width="2"/>')
    avatar(4, AMBER,
           f'<path d="M66 56L104 92L80 122Z" fill="{AMBER}"/><path d="M190 56L152 92L176 122Z" fill="{AMBER}"/>'
           f'<path d="M74 70L96 92L82 108Z" fill="#7a3d12"/><path d="M182 70L160 92L174 108Z" fill="#7a3d12"/>'
           f'<path d="M80 104C84 76 104 66 128 66C152 66 172 76 176 104L172 140L128 184L84 140Z" fill="url(#v)" filter="url(#gl)"/>'
           f'<path d="M84 140L128 184L172 140L152 130L128 150L104 130Z" fill="{TEXT}"/>'
           f'<path d="M96 112L120 118L102 126Z" fill="{BG0}"/><path d="M160 112L136 118L154 126Z" fill="{BG0}"/>'
           f'<circle cx="128" cy="178" r="7" fill="{BG0}"/>', sh="#1a1410")
    avatar(5, LIME,
           f'<path d="M128 70V46" stroke="{LIME}" stroke-width="3"/><circle cx="128" cy="42" r="6" fill="{LIME}" filter="url(#gl)"/>'
           f'<rect x="64" y="108" width="14" height="30" rx="4" fill="#1b2633"/><rect x="178" y="108" width="14" height="30" rx="4" fill="#1b2633"/>'
           f'<rect x="78" y="70" width="100" height="104" rx="20" fill="{D}" stroke="{LIME}" stroke-opacity=".7" stroke-width="2"/>'
           f'<rect x="90" y="86" width="76" height="50" rx="12" fill="{BG0}"/>'
           f'<g filter="url(#gl)"><circle cx="111" cy="111" r="10" fill="{LIME}"/><circle cx="145" cy="111" r="10" fill="{LIME}"/></g>'
           f'<rect x="102" y="148" width="52" height="12" rx="3" fill="{BG0}"/><path d="M112 148V160M122 148V160M132 148V160M142 148V160" stroke="{LIME}" stroke-opacity=".6" stroke-width="2"/>')
    avatar(6, PURPLE,
           f'<path d="M64 150C60 84 92 46 128 46C164 46 196 84 192 150L184 194H72Z" fill="#141026" stroke="{PURPLE}" stroke-opacity=".6" stroke-width="2"/>'
           f'<path d="M90 110C90 84 106 70 128 70C150 70 166 84 166 110C166 128 160 138 152 144V162H104V144C96 138 90 128 90 110Z" fill="{TEXT}" opacity=".93"/>'
           f'<path d="M100 104C102 94 120 94 122 106C122 120 102 122 100 104ZM156 104C154 94 136 94 134 106C134 120 154 122 156 104Z" fill="{BG0}"/>'
           f'<g filter="url(#gl)"><circle cx="111" cy="107" r="4" fill="{PURPLE}"/><circle cx="145" cy="107" r="4" fill="{PURPLE}"/></g>'
           f'<path d="M128 120L121 134H135Z" fill="{BG0}"/><path d="M110 148V162M119 148V162M128 148V162M137 148V162M146 148V162" stroke="{BG0}" stroke-width="2"/>')
    avatar(7, CYAN,
           f'<path d="M58 196C54 112 80 54 128 50C176 54 202 112 198 196Z" fill="#0f1620" stroke="{CYAN}" stroke-opacity=".6" stroke-width="2"/>'
           f'<path d="M90 100C100 86 156 86 166 100L160 152C150 168 106 168 96 152Z" fill="{BG0}"/>'
           f'<path d="M92 128H164L160 152C150 168 106 168 96 152Z" fill="#1a2430"/>'
           f'<g filter="url(#gl)"><path d="M100 112L122 116L104 122Z" fill="{RED}"/><path d="M156 112L134 116L152 122Z" fill="{RED}"/></g>'
           f'<path d="M100 140H156" stroke="{CYAN}" stroke-opacity=".4"/>', bgc="#4f7cff")
    avatar(8, AMBER,
           f'<path d="M70 118C70 70 98 50 128 50C158 50 186 70 186 118L184 160H72Z" fill="#1a222c" stroke="{AMBER}" stroke-opacity=".5" stroke-width="2"/>'
           f'<path d="M80 96C90 80 166 80 176 96L172 130C150 140 106 140 84 130Z" fill="url(#v)" filter="url(#gl)"/>'
           f'<path d="M92 94C110 86 130 86 146 90" stroke="#fff" stroke-opacity=".55" stroke-width="3" fill="none" stroke-linecap="round"/>'
           f'<path d="M106 140C110 128 146 128 150 140L146 170C140 182 116 182 110 170Z" fill="#0c1117" stroke="{AMBER}" stroke-opacity=".6" stroke-width="2"/>'
           f'<path d="M146 162C170 170 172 190 160 204" fill="none" stroke="#2a3542" stroke-width="7"/><path d="M128 56V80" stroke="{RED}" stroke-width="4"/>', bgc=RED)
    avatar(9, GREEN,
           f'<path d="M78 118C78 72 100 56 128 56C156 56 178 72 178 118C178 156 160 182 128 184C96 182 78 156 78 118Z" fill="#1b2622" stroke="{GREEN}" stroke-opacity=".4" stroke-width="2"/>'
           f'<path d="M76 90C96 74 160 74 180 90L178 104C158 90 98 90 78 104Z" fill="#26342e"/>'
           f'<rect x="74" y="106" width="108" height="10" fill="#0b100e"/>'
           f'<rect x="86" y="100" width="36" height="24" rx="9" fill="url(#v)" filter="url(#gl)"/><rect x="134" y="100" width="36" height="24" rx="9" fill="url(#v)" filter="url(#gl)"/>'
           f'<g fill="#0b100e"><circle cx="118" cy="160" r="2.5"/><circle cx="128" cy="160" r="2.5"/><circle cx="138" cy="160" r="2.5"/><circle cx="123" cy="168" r="2.5"/><circle cx="133" cy="168" r="2.5"/></g>', bgc=LIME)
    avatar(10, CYAN,
           f'<defs><radialGradient id="bub" cx=".35" cy=".3"><stop offset="0" stop-color="{CYAN}" stop-opacity=".35"/><stop offset="1" stop-color="{PURPLE}" stop-opacity=".25"/></radialGradient></defs>'
           f'<ellipse cx="128" cy="182" rx="56" ry="12" fill="#1b2633" stroke="{CYAN}" stroke-opacity=".6" stroke-width="2"/>'
           f'<circle cx="128" cy="116" r="40" fill="{BG0}"/><path d="M108 112H148" stroke="{CYAN}" stroke-width="4" stroke-linecap="round" filter="url(#gl)"/>'
           f'<circle cx="128" cy="112" r="64" fill="url(#bub)" stroke="{CYAN}" stroke-width="3" filter="url(#gl)"/>'
           f'<path d="M86 86C96 68 114 60 132 60" stroke="#fff" stroke-opacity=".6" stroke-width="5" fill="none" stroke-linecap="round"/>'
           f'<path d="M188 92L204 66" stroke="{CYAN}" stroke-width="3"/><circle cx="205" cy="64" r="4" fill="{PURPLE}"/>', bgc=PURPLE)
    avatar(11, RED,
           f'<path d="M72 50L106 86L82 106Z" fill="#2a2f3a"/><path d="M184 50L150 86L174 106Z" fill="#2a2f3a"/>'
           f'<path d="M80 62L98 84L86 96Z" fill="{RED}" opacity=".6"/><path d="M176 62L158 84L170 96Z" fill="{RED}" opacity=".6"/>'
           f'<path d="M78 98C82 74 104 64 128 64C152 64 174 74 178 98L172 138L146 168L128 186L110 168L84 138Z" fill="#2a2f3a" stroke="{RED}" stroke-opacity=".5" stroke-width="2"/>'
           f'<path d="M106 136L128 186L150 136L138 128L128 140L118 128Z" fill="#aeb8c2"/>'
           f'<g filter="url(#gl)"><path d="M96 110L120 116L102 124Z" fill="{RED}"/><path d="M160 110L136 116L154 124Z" fill="{RED}"/></g>'
           f'<path d="M116 84L128 98L140 84" stroke="{RED}" stroke-width="3" fill="none"/><circle cx="128" cy="180" r="6" fill="{BG0}"/>')
    avatar(12, AMBER,
           f'<path d="M90 76C76 58 74 38 84 24C88 44 98 56 108 66Z" fill="{TEXT}"/><path d="M166 76C180 58 182 38 172 24C168 44 158 56 148 66Z" fill="{TEXT}"/>'
           f'<path d="M84 90C84 70 104 60 128 60C152 60 172 70 172 90L176 130C174 160 154 182 128 184C102 182 82 160 80 130Z" fill="{RED}" stroke="{AMBER}" stroke-opacity=".6" stroke-width="2"/>'
           f'<path d="M92 98L120 108M164 98L136 108" stroke="{BG0}" stroke-width="7" stroke-linecap="round"/>'
           f'<g filter="url(#gl)"><path d="M98 116L120 120L104 128Z" fill="{AMBER}"/><path d="M158 116L136 120L152 128Z" fill="{AMBER}"/></g>'
           f'<path d="M100 150C112 160 144 160 156 150L150 168C140 174 116 174 106 168Z" fill="{BG0}"/>'
           f'<path d="M108 156L114 168L118 157ZM148 156L142 168L138 157Z" fill="{TEXT}"/>', bgc=AMBER, sh="#1a0f12")


# ---------------------------------------------------------------- badges
HEX = " ".join(f"{f1(64 + 54 * math.cos(-math.pi / 2 + k * math.pi / 3))},{f1(64 + 54 * math.sin(-math.pi / 2 + k * math.pi / 3))}" for k in range(6))
HEXI = " ".join(f"{f1(64 + 46 * math.cos(-math.pi / 2 + k * math.pi / 3))},{f1(64 + 46 * math.sin(-math.pi / 2 + k * math.pi / 3))}" for k in range(6))
SHIELD = "M64 8L110 24V60C110 90 90 110 64 120C38 110 18 90 18 60V24Z"
SHIELDI = "M64 17L101 30V60C101 85 85 101 64 110C43 101 27 85 27 60V30Z"


def badge(bid, c1, c2, shape, icon, glowing=True):
    outer = f'<polygon points="{HEX}"' if shape == "hex" else f'<path d="{SHIELD}"'
    inner = f'<polygon points="{HEXI}"' if shape == "hex" else f'<path d="{SHIELDI}"'
    gf = ' filter="url(#gl)"' if glowing else ""
    d = (f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>'
         f'<linearGradient id="gloss" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".3"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/></linearGradient>'
         f'{glow("gl", 5)}</defs>'
         f'{outer} fill="url(#g)"{gf}/>{inner} fill="{BG0}" fill-opacity=".28" stroke="#fff" stroke-opacity=".35" stroke-width="2"/>'
         f'{outer} fill="url(#gloss)"/>{icon}')
    save(f"badges/{bid}.svg", svg(128, 128, d))


def badges():
    badge("early-member", LIME, "#0fa878", "hex",
          f'<path d="M64 28C77 39 81 56 77 74H51C47 56 51 39 64 28Z" fill="{TEXT}"/><circle cx="64" cy="52" r="7" fill="{GREEN}" stroke="{BG0}" stroke-width="2"/>'
          f'<path d="M51 64L41 80L52 78ZM77 64L87 80L76 78Z" fill="{TEXT}"/><path d="M56 76Q64 100 72 76Z" fill="{AMBER}"/>'
          f'<path d="M36 38l2 5 5 2-5 2-2 5-2-5-5-2 5-2zM92 36l1.5 4 4 1.5-4 1.5-1.5 4-1.5-4-4-1.5 4-1.5z" fill="{TEXT}"/>')
    badge("verified", CYAN, "#1176c8", "shield",
          f'<path d="M44 64L58 78L86 48" fill="none" stroke="{TEXT}" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>')
    badge("squad-leader", "#ffd77a", "#d9790f", "hex",
          f'<path d="M38 56L50 70L64 46L78 70L90 56L85 82H43Z" fill="{BG0}"/><circle cx="64" cy="44" r="4" fill="{BG0}"/>'
          f'<path d="M44 90L64 99L84 90M44 101L64 110L84 101" fill="none" stroke="{BG0}" stroke-width="5" stroke-linejoin="round"/>')
    badge("legendary", PURPLE, "#f5b942", "hex",
          f'<path d="M64 22C78 38 92 50 88 72C86 92 74 104 64 106C54 104 42 92 40 72C36 50 50 38 64 22Z" fill="{AMBER}" opacity=".65"/>'
          f'<path d="M64 38L84 56L64 96L44 56Z" fill="{TEXT}"/><path d="M44 56H84M64 38L56 56L64 96L72 56Z" fill="#d8b4fe" stroke="{PURPLE}" stroke-width="1.5"/>')
    badge("first-match", "#ff7a93", "#c0163f", "shield",
          f'<path d="M64 90C40 74 34 60 34 50C34 40 42 34 50 34C57 34 62 38 64 44C66 38 71 34 78 34C86 34 94 40 94 50C94 60 88 74 64 90Z" fill="{TEXT}"/>'
          f'<g fill="none" stroke="{RED}" stroke-width="4.5"><rect x="46" y="54" width="24" height="12" rx="6" transform="rotate(-35 58 60)"/>'
          f'<rect x="58" y="54" width="24" height="12" rx="6" transform="rotate(-35 70 60)"/></g>')
    badge("locked", "#3a434f", "#161b22", "hex",
          f'<path d="M50 62V52C50 42 56 36 64 36C72 36 78 42 78 52V62" fill="none" stroke="#8a96a3" stroke-width="7"/>'
          f'<rect x="42" y="60" width="44" height="34" rx="8" fill="#8a96a3"/><circle cx="64" cy="74" r="5" fill="#161b22"/><rect x="62" y="76" width="4" height="10" rx="2" fill="#161b22"/>',
          glowing=False)


# ---------------------------------------------------------------- logo + og
P = "M22 42V14H34A12 12 0 0 1 34 38H22"


def logo():
    d = (f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{GREEN}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>'
         f'{glow("gl", 1.5)}</defs><g filter="url(#gl)"><path d="{P}" fill="none" stroke="url(#g)" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
         f'<circle cx="22" cy="52" r="4.2" fill="{CYAN}"/></g>')
    save("logo.svg", svg(64, 64, d))
    d = (f'<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG1}"/><stop offset="1" stop-color="{BG0}"/></linearGradient>'
         f'<radialGradient id="r1" cx=".2" cy=".3" r=".6"><stop offset="0" stop-color="{GREEN}" stop-opacity=".28"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></radialGradient>'
         f'<radialGradient id="r2" cx=".85" cy=".8" r=".6"><stop offset="0" stop-color="{CYAN}" stop-opacity=".22"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>'
         f'<linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{GREEN}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>'
         f'<linearGradient id="t" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{GREEN}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>'
         f'<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{TEXT}" stroke-opacity=".05"/></pattern>'
         f'{glow("gl", 6)}{glow("gl2", 3)}</defs>'
         f'<rect width="1200" height="630" fill="url(#bg)"/><rect width="1200" height="630" fill="url(#r1)"/><rect width="1200" height="630" fill="url(#r2)"/>'
         f'<rect width="1200" height="630" fill="url(#grid)"/>'
         f'<g transform="translate(80 170) scale(3.6)" filter="url(#gl2)"><path d="{P}" fill="none" stroke="url(#g)" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
         f'<circle cx="22" cy="52" r="4.2" fill="{CYAN}"/></g>'
         f'<text x="330" y="330" {FONT} font-size="132" font-weight="900" letter-spacing="-3" fill="{TEXT}">Play<tspan fill="url(#t)">Mate</tspan></text>'
         f'<text x="336" y="400" {FONT} font-size="40" font-weight="800" fill="{TEXT}" fill-opacity=".78">Find your squad. Stop playing solo.</text>'
         f'<rect x="336" y="436" width="180" height="6" rx="3" fill="url(#t)" filter="url(#gl2)"/>'
         f'<g fill="none" stroke="{GREEN}" stroke-opacity=".35" stroke-width="2"><path d="M960 120L1060 170L1010 260L920 230Z"/></g>'
         + "".join(f'<circle cx="{x}" cy="{y}" r="16" fill="{BG2}" stroke="{c}" stroke-width="4" filter="url(#gl)"/>'
                   for x, y, c in [(960, 120, GREEN), (1060, 170, CYAN), (1010, 260, LIME), (920, 230, AMBER)]) +
         f'<rect x="12" y="12" width="1176" height="606" rx="28" fill="none" stroke="url(#t)" stroke-opacity=".4" stroke-width="2"/>')
    save("og-image.svg", svg(1200, 630, d))


if __name__ == "__main__":
    for gid, name, genre, acc, fn, mono in GAMES:
        sc, df = fn(acc)
        cover(gid, name, genre, acc, sc, df)
        icon(gid, acc, mono)
    banners()
    avatars()
    badges()
    logo()
    print("done")
