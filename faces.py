"""
faces.py — Procedural color-block faces for players, recruits and coaches.

Every face is a 20x20 grid of colored pixels built from one seed (a hash of the person's name, so a face never has
to be saved, a recruit keeps his face when he signs, and a drafted player or a coach in the record book looks the same
as on his card). A 10x5 "mini" of the same face fills lists and small cards. In a terminal two pixel rows are one row of
half-block characters (▀), so a face is 20 columns x 10 rows. The window draws the same cells without seams.

WHAT SHAPES A FACE
  skin tone      follows the NAME: surnames come from heritage pools (names.py), first names from the lists below;
                 the two are combined into odds over nine tones, so "Tavita Mata'afa", "Emeka Okafor", "Cody Brennan"
                 and "Diego Reyes" each come out the way their names suggest, with real variety inside every group.
                 Tune it in FIRST_PROFILE / SURNAME_SECTIONS below.
  hair, brows,   from the seed. Players: 12 hair styles, headbands, eye black, facial hair that fills in with class year
  face shape     (a freshman is clean-shaven or stubbly; a senior may have a full beard).
  coaches        a team cap in the school's colors and a headset, and their AGE shows: the hair goes salt-and-pepper
                 from the mid-thirties on and silver-white by the late sixties, some go bald, and the lines come in.
  mood           a smile after good times, a frown when morale is low, a bandage when he's hurt.
  jersey         the school's colors (TEAM_COLORS).

Settings -> "Show faces" turns it all off (the screens fall back to the old layout).
"""
import os
import random
import re
import zlib

W = H = 20
TRUECOLOR = None                       # play.py sets True (the window); None = detect the terminal


def hx(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def mix(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


SOFT_FULL_PORTRAITS = True          # full-size cards show the softer downsampled/upscaled version on purpose


def _clamp_rgb(c):
    return tuple(max(0, min(255, int(v))) for v in c)


def _avg_rgb(colors):
    colors = [c for c in colors if c is not None]
    if not colors:
        return None
    n = len(colors)
    return tuple(sum(c[i] for c in colors) // n for i in range(3))


def _rgb_dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def _blend_many(colors, weights=None):
    colors = [c for c in colors if c is not None]
    if not colors:
        return None
    if weights is None:
        weights = [1.0] * len(colors)
    tot = float(sum(weights)) or 1.0
    return tuple(int(sum(c[i] * w for c, w in zip(colors, weights)) / tot) for i in range(3))


def _filled_rgb(grid, bg):
    top_bg, bot_bg = bg
    rgb = []
    for y in range(H):
        row = []
        for x in range(W):
            row.append(grid[y][x] or mix(top_bg, bot_bg, y / (H - 1)))
        rgb.append(row)
    return rgb


def _blur_rgb(rgb, passes=1):
    cur = [row[:] for row in rgb]
    for _ in range(max(1, passes)):
        nxt = [[None] * len(cur[0]) for _ in range(len(cur))]
        for y in range(len(cur)):
            for x in range(len(cur[0])):
                cells, weights = [], []
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < len(cur) and 0 <= nx < len(cur[0]):
                            cells.append(cur[ny][nx])
                            weights.append(4.0 if (dx, dy) == (0, 0) else 2.0 if dx == 0 or dy == 0 else 1.0)
                nxt[y][x] = _blend_many(cells, weights)
        cur = nxt
    return cur


def _downsample_rgb(rgb, factor=2):
    h, w = len(rgb), len(rgb[0])
    out = [[None] * (w // factor) for _ in range(h // factor)]
    for y in range(0, h, factor):
        for x in range(0, w, factor):
            cells = [rgb[yy][xx] for yy in range(y, min(y + factor, h)) for xx in range(x, min(x + factor, w))]
            out[y // factor][x // factor] = _avg_rgb(cells)
    return out


def _upsample_rgb(rgb, factor=2):
    h, w = len(rgb), len(rgb[0])
    out = [[None] * (w * factor) for _ in range(h * factor)]
    for y in range(h):
        for x in range(w):
            c = rgb[y][x]
            for dy in range(factor):
                for dx in range(factor):
                    out[y * factor + dy][x * factor + dx] = c
    return out


def _resize_bilinear_rgb(rgb, out_w, out_h):
    in_h, in_w = len(rgb), len(rgb[0])
    if in_h == out_h and in_w == out_w:
        return [row[:] for row in rgb]
    out = [[None] * out_w for _ in range(out_h)]
    for y in range(out_h):
        sy = 0.0 if out_h <= 1 else float(y) * (in_h - 1) / float(out_h - 1)
        y0 = int(sy)
        y1 = min(y0 + 1, in_h - 1)
        fy = sy - y0
        for x in range(out_w):
            sx = 0.0 if out_w <= 1 else float(x) * (in_w - 1) / float(out_w - 1)
            x0 = int(sx)
            x1 = min(x0 + 1, in_w - 1)
            fx = sx - x0
            c00, c10 = rgb[y0][x0], rgb[y0][x1]
            c01, c11 = rgb[y1][x0], rgb[y1][x1]
            row0 = _blend_many((c00, c10), (1.0 - fx, fx))
            row1 = _blend_many((c01, c11), (1.0 - fx, fx))
            out[y][x] = _blend_many((row0, row1), (1.0 - fy, fy))
    return out


def _sharpen_rgb(rgb, amount=.55):
    blur = _blur_rgb(rgb, passes=1)
    out = [[None] * len(rgb[0]) for _ in range(len(rgb))]
    for y in range(len(rgb)):
        for x in range(len(rgb[0])):
            base, soft = rgb[y][x], blur[y][x]
            out[y][x] = _clamp_rgb(base[i] + amount * (base[i] - soft[i]) for i in range(3))
    return out


def _soft_full_rgb(grid, bg):
    # Keep the softened portrait look, but smooth it with a higher-quality
    # resize and then put edge detail back where it matters most.
    full = _filled_rgb(grid, bg)
    small = _downsample_rgb(full, factor=2)
    smooth = _resize_bilinear_rgb(small, W, H)
    smooth = _sharpen_rgb(smooth, amount=.38)
    out = [[None] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            detail = 0.58 if _rgb_dist(full[y][x], smooth[y][x]) >= 52 else 0.42
            out[y][x] = mix(smooth[y][x], full[y][x], detail)
    return out


def _render_rgb(rgb, truecolor=None):
    tc = _truecolor() if truecolor is None else truecolor

    def col(c, fg):
        if tc:
            return f"\033[{38 if fg else 48};2;{c[0]};{c[1]};{c[2]}m"
        return f"\033[{38 if fg else 48};5;{_c256(c)}m"

    lines = []
    for cy in range(len(rgb) // 2):
        out, last = [], (None, None)
        for x in range(len(rgb[0])):
            a = rgb[cy * 2][x]
            b = rgb[cy * 2 + 1][x]
            if not tc:
                aa, bb = (_c256(a),), (_c256(b),)
                key = (aa, bb)
                if key != last:
                    out.append(f"\033[38;5;{aa[0]}m\033[48;5;{bb[0]}m")
                    last = key
            else:
                key = (a, b)
                if key != last:
                    out.append(col(a, True) + col(b, False))
                    last = key
            out.append("▀")
        out.append("\033[0m")
        lines.append("".join(out))
    return lines


SKINS = [hx(x) for x in ("fbe0cc", "f3cfb3", "e8b98f", "d99e6c", "bd7d4f", "a2623a", "7d4528", "5a301c", "3f2214")]
HAIRS = [hx(x) for x in ("0e0b0a", "24170f", "3b2616", "5a3a1e", "7a4a22", "a8531f", "c9a24a", "e3cf8a")]
MOUTH = hx("8a3b3b")
INK = hx("151210")
HEADSET = (96, 104, 118)
GRAY_HAIR = (190, 190, 196)
SILVER = (228, 228, 232)

# ═══ Skin tone follows the name ═════════════════════════════════════════════
# Odds over the nine tones in SKINS (light -> dark). A first name and a surname each carry a profile; their product
# is the face's odds. Wide overlap on purpose: nobody is decided by one name.
_P = {
    "euro":       [4.0, 5.0, 3.5, 1.5, 0.5, 0.1, 0.0, 0.0, 0.0],
    "med":        [1.5, 3.5, 5.0, 3.5, 1.5, 0.5, 0.1, 0.0, 0.0],
    "hispanic":   [0.8, 2.5, 4.5, 5.0, 3.5, 1.8, 0.6, 0.1, 0.0],
    "polynesian": [0.0, 0.2, 1.2, 3.5, 5.0, 3.5, 1.5, 0.3, 0.0],
    "w_african":  [0.0, 0.0, 0.0, 0.1, 0.4, 1.6, 4.0, 5.0, 4.5],
    "mideast":    [0.4, 2.0, 4.0, 4.5, 3.0, 1.2, 0.3, 0.0, 0.0],
    "e_asian":    [1.5, 4.5, 4.0, 1.5, 0.3, 0.0, 0.0, 0.0, 0.0],
    "s_asian":    [0.0, 0.3, 1.5, 3.5, 5.0, 3.5, 1.2, 0.2, 0.0],
    "american":   [2.5, 3.0, 3.0, 2.5, 2.2, 2.0, 1.6, 1.0, 0.5],      # a common surname tells you little
    "american_b": [0.5, 0.8, 1.5, 2.5, 3.5, 4.0, 3.5, 2.5, 1.2],      # common among Black American families
    "f_black":    [0.0, 0.0, 0.2, 0.6, 1.8, 4.0, 5.0, 4.0, 2.2],      # first names strongly tied to Black American families
    "f_blackish": [0.8, 1.0, 1.5, 2.2, 3.0, 3.5, 3.0, 2.0, 1.0],
    "f_anglo":    [3.0, 3.5, 3.0, 2.0, 1.2, 0.8, 0.5, 0.3, 0.15],
    "flat":       [1.0] * 9,
}


def _names(s):
    return {n.strip() for n in s.split(",") if n.strip()}


FIRST_PROFILE = {}
for _profile, _list in (
    ("f_black", "Alijah, Amari, Andre, Armani, Cortez, Damari, Darius, Darnell, Davion, DeAndre, Deion, Demarcus, "
                "Demetrius, Denzel, DeShawn, Desmond, Jabari, Jahmir, Jalen, Jamal, Jamarcus, Jamari, Jaylen, Javon, "
                "Jermaine, Kamari, Kareem, Keon, Keshawn, Khalil, Kendrick, Lamar, Malik, Marquis, Maurice, Montel, "
                "Rashad, Reggie, Terrance, Terrell, Tavion, Tyrese, Zaire, Ja'Marr, Jalin, Jaquan, Anfernee, Akeem, "
                "Keenan, Kelvin, Cedric, Damon, Donovan, Dorian, Lathan"),
    ("f_blackish", "Dante, Quincy, Isaiah, Elijah, Marcus, Terrance, Kendall, Malcolm, Gabriel, Josiah, Micah, "
                   "Xavier, Solomon, Ezekiel, Elias, Jonah, Nehemiah, Bishop, Emmanuel, Jamal, Zion, Devon, Devin"),
    ("polynesian", "Sione, Tavita, Pono, Kalani, Makai, Keanu"),
    ("w_african", "Emeka, Chidi, Obi, Kofi"),
    ("hispanic", "Alonzo, Carlos, Diego, Jose, Juan, Lorenzo, Mario, Mateo, Oscar, Santana, Nico, Manny, Antonio, "
                 "Ricky, Armando"),
    ("med", "Rocco, Luca, Dominic, Vince"),
    ("euro", "Matthias, Marek, Stefan, Fabian, Ivan, Teague, Gus, Rhett"),
    ("mideast", "Ahmad, Amir, Omar, Yusuf, Nasir"),
):
    for _n in _names(_list):
        FIRST_PROFILE.setdefault(_n, _profile)

# surnames: section of names.py -> profile (parsed from the file, so the pools stay the single source of truth)
SURNAME_SECTIONS = {
    "Irish, Scottish, English": "euro", "German, Dutch, Scandinavian": "euro", "Eastern European": "euro",
    "Italian, French, Portuguese": "med", "Hispanic": "hispanic", "Pacific Islander": "polynesian",
    "West African": "w_african",
}
SURNAME_SPECIAL = {}
for _n in _names("Haddad, Hakim, Kassab, Mansour, Nassar, Saleh"):
    SURNAME_SPECIAL[_n] = "mideast"
for _n in _names("Chen, Kim, Nguyen, Park, Tran, Yamamoto, Tanaka, Watanabe"):
    SURNAME_SPECIAL[_n] = "e_asian"
for _n in _names("Singh, Patel"):
    SURNAME_SPECIAL[_n] = "s_asian"
for _n in _names("Banks, Booker, Bolden, Crenshaw, Dorsey, Gaines, Hawkins, Hines, Jefferson, Jackson, Washington, "
                 "Freeman, Franklin, Coleman, Dixon, Gaither, Grimes, Colbert, Blackmon, Brunson, Cleveland, Chaney, "
                 "Holloway, Hudson, Mitchell, Robinson, Simmons, Tillman, Turner, Whitfield, Wiggins, Williams, "
                 "Boykin, Burrell, Dupree, Easley, Cotton, Crockett, Dabney, Mosley, Moseley, Pickett, Rhodes"):
    SURNAME_SPECIAL.setdefault(_n, "american_b")
_SURNAME_CACHE = {}


def _surname_table():
    if _SURNAME_CACHE:
        return _SURNAME_CACHE
    try:
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "names.py"), encoding="utf-8").read()
        a = src.index("LAST_NAMES = [")
        blk = src[a:src.index("]\n", a)]
        parts = re.split(r"\n\s*#\s*([^\n]*)\n", blk)
        for i in range(1, len(parts), 2):
            prof = SURNAME_SECTIONS.get(parts[i].strip(), None)
            if prof:
                for n in re.findall(r'"([^"]+)"', parts[i + 1]):
                    _SURNAME_CACHE[n] = prof
    except (OSError, ValueError):
        pass
    for n, p in SURNAME_SPECIAL.items():
        _SURNAME_CACHE[n] = p
    _SURNAME_CACHE["_loaded"] = "flat"
    return _SURNAME_CACHE


def split_name(name):
    parts = [x for x in str(name).replace(",", " ").split() if x]
    while len(parts) > 2 and parts[-1].strip(".").lower() in ("jr", "sr", "ii", "iii", "iv", "v"):
        parts.pop()
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[0], parts[-1]


def skin_for(name):
    """The skin tone (an entry of SKINS) this name comes with — the same every time."""
    first, last = split_name(name)
    fp = _P[FIRST_PROFILE.get(first, "f_anglo" if first not in FIRST_PROFILE else "flat")]
    lp = _P[_surname_table().get(last, "american")]
    w = [fp[i] * lp[i] + 0.04 for i in range(9)]
    rng = random.Random(zlib.crc32(("tone|" + str(name)).encode("utf-8")))
    x = rng.random() * sum(w)
    for i, v in enumerate(w):
        x -= v
        if x <= 0:
            return SKINS[i]
    return SKINS[4]


# ═══ School colors ══════════════════════════════════════════════════════════
TEAM_COLORS = {
    "Air Force": ("003087", "b1b3b3"), "Akron": ("041e42", "a89968"), "Alabama": ("9e1b32", "e8e8e8"),
    "App State": ("222222", "ffcc00"), "Arizona": ("cc0033", "003366"), "Arizona State": ("8c1d40", "ffc627"),
    "Arkansas": ("9d2235", "ffffff"), "Arkansas State": ("cc092f", "000000"), "Army": ("000000", "d4bf91"),
    "Auburn": ("0c2340", "e87722"), "BYU": ("002e5d", "ffffff"), "Ball State": ("ba0c2f", "ffffff"),
    "Baylor": ("154734", "ffb81c"), "Boise State": ("0033a0", "d64309"), "Boston College": ("98002e", "bc9b6a"),
    "Bowling Green": ("fe5000", "4f2c1d"), "Buffalo": ("005bbb", "ffffff"), "California": ("003262", "fdb515"),
    "Central Michigan": ("6a0032", "ffc82e"), "Charlotte": ("046a38", "b9975b"), "Cincinnati": ("e00122", "000000"),
    "Clemson": ("f56600", "522d80"), "Coastal Carolina": ("006f71", "a27752"), "Colorado": ("000000", "cfb87c"),
    "Colorado State": ("1e4d2b", "c8c372"), "Delaware": ("00539f", "ffd200"), "Duke": ("003087", "ffffff"),
    "East Carolina": ("592a8a", "ffc72c"), "Eastern Michigan": ("006633", "ffffff"), "FIU": ("081e3f", "b6862c"),
    "Florida": ("0021a5", "fa4616"), "Florida Atlantic": ("003366", "cc0000"), "Florida State": ("782f40", "ceb888"),
    "Fresno State": ("db0032", "002e6d"), "Georgia": ("ba0c2f", "000000"), "Georgia Southern": ("011e41", "ffffff"),
    "Georgia State": ("0039a6", "cc0000"), "Georgia Tech": ("003057", "b3a369"), "Hawai'i": ("024731", "ffffff"),
    "Houston": ("c8102e", "ffffff"), "Illinois": ("e84a27", "13294b"), "Indiana": ("990000", "eeedeb"),
    "Iowa": ("ffcd00", "000000"), "Iowa State": ("c8102e", "f1be48"), "Jacksonville State": ("cc0000", "ffffff"),
    "James Madison": ("450084", "cbb677"), "Kansas": ("0051ba", "e8000d"), "Kansas State": ("512888", "d1d1d1"),
    "Kennesaw State": ("fdbb30", "000000"), "Kent State": ("002664", "eaab00"), "Kentucky": ("0033a0", "ffffff"),
    "LSU": ("461d7c", "fdd023"), "Liberty": ("002d62", "c41230"), "Louisiana": ("ce181e", "ffffff"),
    "Louisiana Tech": ("002f8b", "e31b23"), "Louisville": ("ad0000", "000000"), "Marshall": ("00b140", "ffffff"),
    "Maryland": ("e03a3e", "ffd520"), "Memphis": ("003087", "898d8d"), "Miami": ("f47321", "005030"),
    "Miami (OH)": ("b61f2d", "ffffff"), "Michigan": ("00274c", "ffcb05"), "Michigan State": ("18453b", "ffffff"),
    "Middle Tennessee": ("0066cc", "ffffff"), "Minnesota": ("7a0019", "ffcc33"), "Mississippi State": ("660000", "ffffff"),
    "Missouri": ("f1b82d", "000000"), "Missouri State": ("5e0009", "ffffff"), "NC State": ("cc0000", "ffffff"),
    "Navy": ("00205b", "c5b783"), "Nebraska": ("e41c38", "ffffff"), "Nevada": ("003366", "a2aaad"),
    "New Mexico": ("ba0c2f", "a7a8aa"), "New Mexico State": ("8c0b42", "ffffff"), "North Carolina": ("7bafd4", "ffffff"),
    "North Dakota State": ("0a5640", "ffc72c"), "North Texas": ("00853e", "ffffff"), "Northern Illinois": ("ba0c2f", "000000"),
    "Northwestern": ("4e2a84", "ffffff"), "Notre Dame": ("0c2340", "c99700"), "Ohio": ("00694e", "ffffff"),
    "Ohio State": ("bb0000", "a7b1b7"), "Oklahoma": ("841617", "fdf9d8"), "Oklahoma State": ("ff7300", "000000"),
    "Old Dominion": ("003057", "7c878e"), "Ole Miss": ("14213d", "ce1126"), "Oregon": ("154733", "fee123"),
    "Oregon State": ("dc4405", "000000"), "Penn State": ("041e42", "ffffff"), "Pittsburgh": ("003594", "ffb81c"),
    "Purdue": ("000000", "ceb888"), "Rice": ("00205b", "5e6062"), "Rutgers": ("cc0033", "5f6a72"),
    "SMU": ("c8102e", "0033a0"), "Sacramento State": ("00563f", "b79257"), "Sam Houston": ("f56600", "ffffff"),
    "San Diego State": ("a6192e", "000000"), "San Jose State": ("0055a2", "e5a823"), "South Alabama": ("00205b", "bf0d3e"),
    "South Carolina": ("73000a", "000000"), "South Florida": ("006747", "cfc493"), "Southern Miss": ("000000", "ffab00"),
    "Stanford": ("8c1515", "ffffff"), "Syracuse": ("f76900", "000e54"), "TCU": ("4d1979", "a3a9ac"),
    "Temple": ("9d2235", "ffffff"), "Tennessee": ("ff8200", "ffffff"), "Texas": ("bf5700", "f2f2f2"),
    "Texas A&M": ("500000", "ffffff"), "Texas State": ("501214", "8d734a"), "Texas Tech": ("cc0000", "000000"),
    "Toledo": ("15397f", "ffd100"), "Troy": ("8a2432", "a2aaad"), "Tulane": ("006747", "4b92db"),
    "Tulsa": ("003d7c", "c8102e"), "UAB": ("1e6b52", "f2a900"), "UCF": ("000000", "ffc904"),
    "UCLA": ("2774ae", "ffd100"), "UConn": ("000e2f", "e4002b"), "ULM": ("840029", "c5b358"),
    "UMass": ("881c1c", "ffffff"), "UNLV": ("cf0a2c", "666666"), "USC": ("990000", "ffc72c"),
    "UTEP": ("ff8200", "041e42"), "UTSA": ("0c2340", "f15a22"), "Utah": ("cc0000", "ffffff"),
    "Utah State": ("0f2439", "ffffff"), "Vanderbilt": ("000000", "cfae70"), "Virginia": ("232d4b", "f84c1e"),
    "Virginia Tech": ("861f41", "e5751f"), "Wake Forest": ("000000", "9e7e38"), "Washington": ("4b2e83", "b7a57a"),
    "Washington State": ("981e32", "5e6a71"), "West Virginia": ("002855", "eaaa00"),
    "Western Kentucky": ("c60c30", "ffffff"), "Western Michigan": ("6c4023", "b5a167"),
    "Wisconsin": ("c5050c", "ffffff"), "Wyoming": ("492f24", "ffc425"),
}
NEUTRAL_COLORS = ("2b3345", "9aa5b8")


def team_colors(school):
    """(primary, secondary) as RGB. A school we've never heard of gets a stable made-up pair."""
    c = TEAM_COLORS.get(school)
    if c is None:
        if not school:
            return hx(NEUTRAL_COLORS[0]), hx(NEUTRAL_COLORS[1])
        rng = random.Random(zlib.crc32(str(school).encode("utf-8")))
        import colorsys
        h = rng.random()
        p = tuple(int(255 * v) for v in colorsys.hsv_to_rgb(h, .75, .55))
        s = tuple(int(255 * v) for v in colorsys.hsv_to_rgb((h + .5) % 1, .25, .95))
        return p, s
    return hx(c[0]), hx(c[1])


# ═══ The face ═══════════════════════════════════════════════════════════════
STYLES = ["buzz", "short", "flattop", "afro", "long", "bald", "mohawk", "curly", "locs", "braids", "waves", "bun"]
# Odds by skin group (light / medium / dark): hair color and texture follow the person, with overlap.
HAIR_W = [[1.2, 2.5, 2.5, 2.0, 1.2, 0.8, 1.2, 1.2],
          [3.5, 3.0, 1.5, 0.8, 0.3, 0.1, 0.2, 0.15],
          [6.0, 2.0, 0.4, 0.1, 0.0, 0.0, 0.03, 0.02]]
STYLE_W = [[3.6, 6.0, 0.8, 0.1, 1.3, 0.4, 0.2, 1.8, 0.1, 0.05, 0.8, 0.12],
           [3.8, 4.8, 0.8, 0.5, 0.9, 0.5, 0.2, 1.7, 0.4, 0.25, 1.2, 0.08],
           [3.0, 1.8, 0.8, 2.5, 0.2, 0.6, 0.15, 0.7, 1.8, 1.1, 2.6, 0.04]]
IRIS = [hx("3c2416"), hx("6b4a2b"), hx("5c7a3a"), hx("3f6fa8")]          # brown, hazel, green, blue
IRIS_W = [[3.0, 1.5, 1.0, 2.0], [6.0, 1.5, 0.4, 0.3], [1.0, 0.0, 0.0, 0.0]]


def _wchoice(r, items, weights):
    x = r.random() * sum(weights)
    for it, w in zip(items, weights):
        x -= w
        if x <= 0:
            return it
    return items[0]
FACIAL = ["none", "none", "none", "stubble", "stubble", "mustache", "soulpatch", "goatee", "beard", "beard", "chinstrap"]


def _choose_style(r, grp, bulk, requested=None):
    if requested:
        return requested
    style = _wchoice(r, STYLES, STYLE_W[grp])
    # Reroll the few styles that look the harshest in a 20x20 portrait so they still appear, just less often.
    if style in ("bun", "mohawk") and r.random() < 0.75:
        style = _wchoice(r, STYLES, [w if s not in ("bun", "mohawk") else 0.0 for s, w in zip(STYLES, STYLE_W[grp])])
    if bulk >= 0.72 and style in ("long", "bun") and r.random() < 0.6:
        style = _wchoice(r, ["buzz", "short", "waves", "curly", "bald", "afro"], [3.2, 3.8, 1.8, 1.4, 0.8, 1.2])
    return style


def _cleanup_grid(px):
    # fill tiny interior holes and remove isolated speckle pixels that read as glitches rather than features
    out = [row[:] for row in px]
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            here = px[y][x]
            orth = [px[y - 1][x], px[y + 1][x], px[y][x - 1], px[y][x + 1]]
            nonnull = [c for c in orth if c is not None]
            if here is None and len(nonnull) >= 3:
                if max(_rgb_dist(c, nonnull[0]) for c in nonnull[1:]) < 90:
                    out[y][x] = _avg_rgb(nonnull)
            elif here is not None and not nonnull:
                out[y][x] = None
    return out


def make_face(seed, skin, year=3, expr="neutral", colors=None, role="player", age=None, style=None, facial=None,
              tie=None, weight=None):
    """-> (grid of RGB/None, (bg_top, bg_bottom)). year 0 FR .. 3 SR (players). role 'coach' wears the cap and shows age."""
    r = random.Random(seed)
    P1, P2 = colors or (hx(NEUTRAL_COLORS[0]), hx(NEUTRAL_COLORS[1]))
    px = [[None] * W for _ in range(H)]

    def put(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            px[y][x] = c

    def row(y, x0, x1, c):
        for x in range(x0, x1 + 1):
            put(x, y, c)

    sh, hl = shade(skin, .78), shade(skin, 1.14)
    coach = role in ("coach", "exec")                            # both show their age; only a coach wears the cap
    age = int(age) if age else 50
    tone = SKINS.index(skin) if skin in SKINS else 4
    grp = 0 if tone <= 2 else 1 if tone <= 4 else 2              # light / medium / dark
    bulk = 0.5 if weight is None else max(0.0, min(1.0, (weight - 180) / 120.0))   # a kicker 0 .. a lineman 1
    base = _wchoice(r, HAIRS, HAIR_W[grp])
    gray_f = max(0.0, min(1.0, (age - 33) / 38.0)) if coach else 0.0     # 0 at 33 .. 1 at 71
    hair = base
    if coach:
        if gray_f >= .88:
            hair = SILVER
        elif gray_f > .08:
            hair = mix(base, GRAY_HAIR, gray_f)
    elif sum(abs(hair[i] - skin[i]) for i in range(3)) < 110:
        hair = shade(hair, .45)
    hh = mix(hair, (160, 150, 140), .32) if lum(hair) < 90 else shade(hair, 1.12)
    hd = shade(hair, .72)
    hs = _choose_style(r, grp, bulk, style)
    fh = facial or r.choice(FACIAL)
    h_roll, jaw_roll = r.choice([5, 5, 5, 6]), r.random()          # keep the face varied, but prefer the more natural mid shape
    h = 6 if bulk >= .66 else 5 if bulk <= .25 else h_roll        # big men have big faces
    jaws = (["square", "round", "square", "long", "round"] if bulk >= .66 else
            ["long", "pointy", "round", "square", "pointy"] if bulk <= .25 else
            ["round", "square", "long", "round", "pointy"])
    jaw = jaws[min(4, int(jaw_roll * 5))]
    g = r.choice([1, 2]) if h == 5 else r.choice([2, 3])
    wide = r.random() < .32
    eye_black = r.random() < .16 and not coach
    headband = r.random() < .06 and not coach
    bald_roll = r.random()
    iris = _wchoice(r, IRIS, IRIS_W[grp])
    wide_nose = r.random() < (.12, .22, .38)[grp]
    full_lips = r.random() < (.18, .28, .42)[grp]
    freckles = grp == 0 and r.random() < .18
    thick_brows = r.random() < .16
    eye_shape = r.choice(["round", "almond", "hooded", "narrow"])
    eye_tilt = -1 if r.random() < .14 else 1 if r.random() < .14 else 0
    nose_shape = r.choice(["straight", "button", "broad", "roman"])
    dimples = r.random() < .16
    top = 4
    bald = coach and bald_roll < (0 if age < 40 else .08 if age < 50 else .2 if age < 60 else .32)
    if coach and fh in ("none", "stubble"):
        fh = r.choice(["none", "none", "mustache", "stubble"])
    if not coach:
        if year == 0 and fh in ("beard", "goatee", "chinstrap", "mustache", "soulpatch"):
            fh = "stubble" if r.random() < .5 else "none"
        if year == 1 and fh == "beard":
            fh = "goatee"
    L, R = 10 - h, 9 + h
    widths = [h - 2, h - 1, h, h, h, h, h, h]
    widths += {"round": [h, h - 1, h - 2, h - 2], "square": [h, h, h - 1, h - 2],
               "long": [h, h - 1, h - 1, h - 2, h - 2], "pointy": [h - 1, h - 1, h - 2, h - 3]}[jaw]
    chin = top + len(widths) - 1
    brow, eye, nose, mouth = top + 3, top + 4, top + 6, top + 9

    def dither(y, a, b, c1, c2):
        for x in range(a, b + 1):
            put(x, y, c1 if (x + y) % 2 == 0 else c2)

    def speckle(cells):
        for (x, y) in cells:
            v = r.random()
            put(x, y, hh if v < .18 else hd if v < .36 else hair)

    # ── back hair (players)
    back = hs if not coach else "none"
    if back == "afro":
        spans = [(6, 13), (4, 15), (3, 16), (2, 17), (2, 17), (2, 17), (2, 17), (2, 17), (3, 16)]
        speckle([(x, y) for y, (a, b) in enumerate(spans) for x in range(a, b + 1)])
    elif back == "long":
        row(top - 1, L, R, hair)
        for y in range(top, top + 11):
            for x in (L - 2, L - 1, R + 1, R + 2):
                put(x, y, hair if (x + y) % 5 else hh)
    elif back == "locs":
        for y in range(top - 2, top + 1):
            dither(y, L - 1, R + 1, hair, hd)
        for y in range(top, top + 9):
            for x in range(L - 3, L):
                put(x, y, hair if (x + L) % 2 == 0 else hh)
            for x in range(R + 1, R + 4):
                put(x, y, hair if (x + R) % 2 == 0 else hh)
    elif back == "braids":
        for y in range(top - 2, top + 1):
            for x in range(L - 1, R + 2):
                put(x, y, hair if x % 2 == 0 else hh)
        for y in range(top, top + 8):
            for x in (L - 2, L - 1, R + 1, R + 2):
                put(x, y, hair if (y % 2 == 0) else hh)
    elif back == "curly":
        for y, (a, b) in zip(range(top - 3, top + 1), [(L + 1, R - 1), (L, R), (L - 1, R + 1), (L - 1, R + 1)]):
            speckle([(x, y) for x in range(a, b + 1)])
        for y in range(top + 1, top + 4):
            put(L - 1, y, hair)
            put(R + 1, y, hair)
    elif back == "bun":
        for y, (a, b) in zip(range(0, 3), [(9, 10), (8, 11), (8, 11)]):
            row(y, a, b, hair)
        put(9, 1, hh)
    # ── the face
    for i, w in enumerate(widths):
        y = top + i
        row(y, 10 - w, 9 + w, skin)
        put(9 + w, y, sh)
        if i >= 2:
            put(8 + w, y, mix(skin, sh, .35))
        if 1 <= i <= 4:
            put(11 - w, y, hl)
    for xx in (L - 1, R + 1):                                    # ears
        for yy in (eye - 1, eye, eye + 1):
            put(xx, yy, skin if xx < 10 else sh)
        put(xx, eye, sh)
    for xx in (L + 1, L + 2, R - 2, R - 1):                      # a little color in the cheeks
        put(xx, nose + 2, mix(skin, (225, 90, 95), .16))
    put(L + 1, nose - 1, hl)                                     # cheekbone catching the light
    for i, w in enumerate(widths):                               # the jawline in shadow
        y = top + i
        if y >= mouth:
            put(10 - w, y, mix(skin, sh, .5))
    if freckles:
        for xx, yy in ((L + 1, nose), (L + 3, nose), (L + 2, nose + 1), (R - 1, nose), (R - 3, nose), (R - 2, nose + 1)):
            put(xx, yy, mix(skin, (160, 80, 50), .35))
    # ── eyes, brows, nose, mouth
    la, ra = (9 - g - 1, 9 - g), (10 + g, 10 + g + 1)
    eye_white = (242, 242, 240)
    eye_dark = mix(INK, iris, .30)
    lid = mix(skin, sh, .55)
    if eye_shape == "narrow":
        put(la[0], eye, eye_dark)
        put(la[1], eye, iris)
        put(ra[0], eye, iris)
        put(ra[1], eye, eye_dark)
    elif eye_shape == "hooded":
        put(la[0], eye, mix(eye_white, iris, .25))
        put(la[1], eye, iris)
        put(ra[0], eye, iris)
        put(ra[1], eye, mix(eye_white, iris, .25))
        put(la[0], eye - 1, lid)
        put(ra[1], eye - 1, lid)
    else:
        put(la[0], eye, eye_white if eye_shape == "round" else mix(eye_white, iris, .18))
        put(la[1], eye, iris)
        put(ra[0], eye, iris)
        put(ra[1], eye, eye_white if eye_shape == "round" else mix(eye_white, iris, .18))
    for x in (*la, *ra):
        put(x, eye + 1, mix(skin, INK, .85) if eye_black else lid)
    if coach or expr in ("sad", "hurt") or eye_shape == "hooded":
        put(la[0], eye + 2, mix(skin, sh, .24))
        put(ra[1], eye + 2, mix(skin, sh, .24))
    bc = shade(hair, .85) if coach else shade(hair, .75)
    lb0, lb1 = 9 - g - 2, 9 - g
    rb0, rb1 = 10 + g, 10 + g + 2
    row(brow + min(0, eye_tilt), lb0, lb1, bc)
    row(brow - max(0, eye_tilt), rb0, rb1, bc)
    if thick_brows:
        row(brow - 1 + min(0, eye_tilt), lb0 + 1, lb1, bc)
        row(brow - 1 - max(0, eye_tilt), rb0, rb1 - 1, bc)
    if expr == "angry":
        put(lb1, brow + 1, bc)
        put(lb1, brow, skin)
        put(rb0, brow + 1, bc)
        put(rb0, brow, skin)
    if expr in ("sad", "hurt"):
        put(lb1, brow - 1, bc)
        put(rb0, brow - 1, bc)
    bridge = mix(skin, hl, .58)
    put(9, nose - 1, bridge)
    put(9, nose, hl)
    put(10, nose, mix(skin, sh, .4))
    nsh = mix(skin, (80, 35, 25), .30)
    put(9, nose + 1, nsh)
    put(10, nose + 1, nsh)
    if nose_shape == "roman":
        put(10, nose - 1, mix(skin, sh, .22))
        put(9, nose + 2, mix(skin, nsh, .32))
    elif nose_shape == "button":
        put(9, nose + 2, mix(skin, nsh, .40))
        put(10, nose + 2, mix(skin, nsh, .30))
    if wide_nose or nose_shape == "broad":
        put(8, nose + 1, mix(skin, nsh, .6))
        put(11, nose + 1, mix(skin, nsh, .6))
    mc = mix(skin, MOUTH, .9)
    lip = mix(skin, MOUTH, .45)
    m0, m1 = (7, 12) if wide else (8, 11)
    if full_lips and m0 > 7:
        m0 -= 1
        m1 += 1
    if expr == "smile":
        row(mouth, max(7, m0), min(12, m1), mc)
        put(max(6, m0 - 1), mouth - 1, mc)
        put(min(13, m1 + 1), mouth - 1, mc)
        row(mouth + 1, 8 if full_lips else 9, 11 if full_lips else 10, lip)
    elif expr in ("frown", "sad"):
        row(mouth, max(7, m0), min(12, m1), mc)
        put(max(6, m0 - 1), mouth + 1, mc)
        put(min(13, m1 + 1), mouth + 1, mc)
    elif expr == "shout":
        row(mouth - 1, max(7, m0), min(12, m1), mc)
        row(mouth, max(7, m0), min(12, m1), shade(MOUTH, .55))
        row(mouth, 9, 10, (240, 240, 240))
        row(mouth + 1, 9, 10, lip)
    else:
        row(mouth, m0, m1, mc)
        row(mouth + 1, 8 if full_lips else 9, 11 if full_lips else 10, lip)
    if dimples and expr == "smile":
        put(max(6, m0 - 1), mouth, mix(skin, sh, .25))
        put(min(13, m1 + 1), mouth, mix(skin, sh, .25))
    if px[mouth + 2][9] in (skin, sh):                           # the shadow under the lower lip
        put(9, mouth + 2, mix(skin, sh, .35))
        put(10, mouth + 2, mix(skin, sh, .35))
        put(9, mouth + 1, mix(skin, MOUTH, .18))
    if coach:                                                    # the years show: lines on the forehead, at the eyes, by the mouth
        if age >= 38:
            for x in range(L + 2, R - 1, 2):
                put(x, top + 2, mix(skin, sh, .3))
        if age >= 45:
            put(la[0] - 1, eye + 1, mix(skin, sh, .4))
            put(ra[1] + 1, eye + 1, mix(skin, sh, .4))
        if age >= 55:
            put(L + 1, mouth - 1, mix(skin, sh, .45))
            put(R - 1, mouth - 1, mix(skin, sh, .45))
        if age >= 62:
            put(L + 2, mouth + 1, mix(skin, sh, .35))
            put(R - 2, mouth + 1, mix(skin, sh, .35))
    # ── facial hair
    fc = shade(hair, .95)
    if fh == "stubble":
        for y in range(top + 7, chin + 1):
            for x in range(L + 1, R):
                if px[y][x] in (skin, sh, hl) and ((x * 7 + y * 11 + seed) % 4 != 0):
                    put(x, y, mix(px[y][x], hair, .22 if y < mouth else .34))
    if fh in ("mustache", "goatee", "beard"):
        for x in range(max(7, m0), min(12, m1) + 1):
            put(x, mouth - 1, fc if x not in (m0, m1) else mix(fc, skin, .18))
    if fh == "soulpatch":
        put(9, mouth + 2, fc)
        put(10, mouth + 2, fc)
    if fh == "goatee":
        for y in range(mouth + 2, chin + 1):
            row(y, 9, 10, fc)
    if fh == "beard":
        for y in range(top + 7, chin + 1):
            for x in range(L, R + 1):
                if px[y][x] is not None and not (y in (mouth, mouth + 1) and 8 <= x <= 11)                         and not (y == mouth - 1 and 7 <= x <= 12):
                    mixf = .82 if y >= mouth + 1 else .62
                    put(x, y, mix(px[y][x], fc, mixf) if not (y == top + 7 and L < x < R) else px[y][x])
        row(mouth - 1, 7, 12, fc)
        row(mouth, m0 if m0 > 7 else 8, m1 if m1 < 12 else 11, mc)
        row(mouth + 1, 9, 10, lip)
    if fh == "chinstrap":
        for y in range(mouth - 1, chin + 1):
            put(L, y, fc)
            put(R, y, fc)
        row(chin, L, R, fc)
    # ── front hair (players)
    front = hs if not coach else "none"
    if front == "buzz":
        c = mix(hair, skin, .42)
        row(top - 1, L + 1, R - 1, c)
        row(top, L, R, c)
        put(L, top + 1, c)
        put(R, top + 1, c)
    elif front == "short":
        row(top - 2, L + 2, R - 2, hair)
        row(top - 1, L + 1, R - 1, hair)
        row(top, L, R, hair)
        row(top + 1, L, L + 1, hair)
        row(top + 1, R - 1, R, hair)
        put(L, top + 2, hair)
        put(R, top + 2, hair)
        row(top - 2, L + 3, L + 5, hh)
        if r.random() < .5:
            row(top + 1, 8, 9, hair)
    elif front == "flattop":
        row(top - 4, L + 2, R - 2, hair)
        row(top - 3, L + 1, R - 1, hair)
        row(top - 2, L + 1, R - 1, hair)
        row(top - 1, L + 1, R - 1, mix(hair, skin, .25))
        row(top, L + 1, R - 1, mix(hair, skin, .5))
        put(L, top, mix(hair, skin, .65))
        put(R, top, mix(hair, skin, .65))
        row(top - 4, L + 3, L + 6, hh)
    elif front == "afro":
        row(top - 1, L, R, hair)
        row(top, L + 1, R - 1, hair)
        speckle([(x, top - 1) for x in range(L, R + 1)])
    elif front == "long":
        row(top - 2, L + 1, R - 1, hair)
        row(top - 1, L, R, hair)
        row(top, L, R, hair)
        gap = 9 if r.random() < .5 else 10
        put(gap, top, skin)
        put(gap, top - 1, hd)
        put(L, top + 1, hair)
        put(R, top + 1, hair)
        row(top - 2, L + 3, L + 5, hh)
    elif front == "bald":
        row(top - 1, L + 1, R - 1, skin)
        row(top - 2, L + 3, R - 3, skin)
        row(top - 2, L + 3, L + 4, hl)
        put(L + 2, top - 1, hl)
    elif front == "mohawk":
        c = mix(hair, skin, .55)
        row(top - 1, L + 1, R - 1, c)
        row(top, L + 1, R - 1, c)
        for y in range(top - 5, top + 1):
            put(9, y, hair)
            put(10, y, hh)
    elif front == "curly":
        for y in (top - 1, top):
            speckle([(x, y) for x in range(L, R + 1)])
    elif front == "locs":
        for y in (top - 1, top):
            dither(y, L, R, hair, hd)
        put(9, top + 1, hd)
        put(10, top + 1, hd)
    elif front == "braids":
        for y in (top - 1, top):
            for x in range(L, R + 1):
                put(x, y, hair if x % 2 == 0 else hh)
    elif front == "waves":
        for y in (top - 2, top - 1, top):
            for x in range(L + (1 if y == top - 2 else 0), R + 1 - (1 if y == top - 2 else 0)):
                put(x, y, hair if (x + y) % 2 == 0 else hh)
        put(L, top + 1, hair)
        put(R, top + 1, hair)
    elif front == "bun":
        row(top - 2, L + 2, R - 2, hair)
        row(top - 1, L + 1, R - 1, hair)
        row(top, L, R, hair)
        put(L, top + 1, hair)
        put(R, top + 1, hair)
        row(top - 2, L + 3, L + 5, hh)
    if headband:
        row(top + 1, L, R, P2)
        put(L - 1, top + 1, P2)
        put(R + 1, top + 1, P2)
    # ── coaches: what's left of the hair under the cap, then the cap
    if coach:
        if not bald:
            for y in (top, top + 1, top + 2):
                put(L - 1, y, hair)
                put(R + 1, y, hair)
            for y in (top + 1, top + 2):
                put(L, y, hair)
                put(R, y, hair)
            put(L - 1, top + 3, hair)
            put(R + 1, top + 3, hair)
        else:
            put(L - 1, top + 1, mix(skin, hair, .35))
            put(R + 1, top + 1, mix(skin, hair, .35))
    if role == "exec" and not bald:                              # an AD: a neat short cut, no cap
        row(top - 2, L + 2, R - 2, hair)
        row(top - 1, L + 1, R - 1, hair)
        row(top, L, R, hair)
        row(top - 2, L + 3, L + 5, hh)
    # ── forehead shadow under whatever sits on it
    for x in range(L, R + 1):
        for y in range(top, top + 3):
            if px[y][x] == skin and px[y - 1][x] not in (None, skin, sh, hl):
                put(x, y, mix(skin, sh, .55))
    if role == "coach":
        row(top - 4, L + 2, R - 2, P1)
        row(top - 3, L + 1, R - 1, P1)
        row(top - 2, L, R, P1)
        row(top - 1, L, R, P1)
        row(top - 4, L + 3, L + 5, mix(P1, (255, 255, 255), .22))
        row(top, L - 1, R + 1, shade(P1, .72))                   # the brim
        row(top + 1, L + 1, R - 1, mix(skin, sh, .5)) if px[top + 1][L + 1] == skin else None
        for xx in (9, 10):                                       # the logo
            put(xx, top - 3, P2)
            put(xx, top - 2, P2)
        for y in range(eye - 1, mouth + 1):                      # the headset (steel gray, never mistaken for hair)
            put(L - 1, y, HEADSET)
        row(mouth - 1, L, L + 2, HEADSET)
        put(L + 2, mouth - 1, (210, 60, 60))
    if expr == "hurt":                                           # a bandage and a bruise
        row(top + 1, L + 2, L + 4, (240, 235, 220))
        put(L + 3, top + 1, (200, 60, 60))
        put(ra[0], eye + 1, mix(skin, (110, 60, 130), .6))
    # ── salt and pepper: a coach's hair, brows and beard go gray in step with his age
    if coach and .2 < gray_f < .88:
        pepper, salt = shade(base, .9), (205, 205, 210)
        hairset = {hair, hh, hd, bc, fc}
        for y in range(H):
            for x in range(W):
                if px[y][x] in hairset:
                    v = (((x * 73856093) ^ (y * 19349663) ^ seed) % 100) / 100.0
                    px[y][x] = salt if v < gray_f else pepper
    px = _cleanup_grid(px)
    # ── neck and jersey
    nk = shade(skin, .74)
    n0, n1 = (7, 12) if bulk >= .55 else (8, 11)                 # a lineman's neck
    for y in range(chin + 1, 17):
        row(y, n0, n1, nk if y > chin + 1 else shade(skin, .6))
    row(17, 3 if bulk >= .6 else 5 if bulk <= .2 else 4, 16 if bulk >= .6 else 14 if bulk <= .2 else 15, P1)
    row(18, 1, 18, P1)
    row(19, 0, 19, P1)
    row(17, 9, 10, nk)
    row(18, 9, 10, nk)
    for yy in (17, 18):
        put(8, yy, P2)
        put(11, yy, P2)
    if role == "exec":                                           # suit, white collar, a tie in the school's color
        for y in (17, 18, 19):
            row(y, 9, 10, tie or P2)
        row(18, 6, 7, shade(P1, 1.5))
        row(18, 12, 13, shade(P1, 1.5))
        row(19, 0, 0, shade(P1, .8))
    else:
        row(18, 2, 3, P2)
        row(18, 16, 17, P2)
        row(19, 0, 0, shade(P1, .8))
    # ── a dark edge around everything, so dark skin and dark hair never melt into the backdrop
    edge = []
    for y in range(H):
        for x in range(W):
            if px[y][x] is None:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and px[ny][nx] is not None:
                        edge.append((x, y, shade(px[ny][nx], .42)))
                        break
    for x, y, c in edge:
        px[y][x] = c
    top_bg = mix(shade(P1, .55), (100, 112, 132), .55)
    return px, (top_bg, shade(top_bg, .72))


# ═══ Terminal / window output ═══════════════════════════════════════════════
def _truecolor():
    if TRUECOLOR is not None:
        return TRUECOLOR
    env = os.environ
    if env.get("COLORTERM", "").lower() in ("truecolor", "24bit") or env.get("WT_SESSION") \
            or env.get("TERM_PROGRAM") in ("iTerm.app", "vscode", "WezTerm", "ghostty", "Hyper") \
            or "kitty" in env.get("TERM", "") or env.get("KONSOLE_VERSION"):
        return True
    return False


def _c256(c):
    r, g, b = c
    if abs(r - g) < 9 and abs(g - b) < 9:
        gr = (r + g + b) // 3
        if gr < 8:
            return 16
        if gr > 248:
            return 231
        return 232 + int((gr - 8) / 247 * 23 + .5)
    return 16 + 36 * int(r / 255 * 5 + .5) + 6 * int(g / 255 * 5 + .5) + int(b / 255 * 5 + .5)


def render(grid, bg, truecolor=None):
    """The face as H//2 lines of half-block characters with 24-bit (or 256-color) escapes.
    Full portraits intentionally use a softened, downsampled/upscaled pass because the blurrier version reads better.
    """
    rgb = _soft_full_rgb(grid, bg) if SOFT_FULL_PORTRAITS else _filled_rgb(grid, bg)
    return _render_rgb(rgb, truecolor=truecolor)


def render_mini(grid, bg, truecolor=None):
    """The same face at half size: 10 columns x 5 rows (each cell averages a 2x2 block of the 20x20 face)."""
    small = _downsample_rgb(_filled_rgb(grid, bg), factor=2)
    return _render_rgb(small, truecolor=truecolor)


_CACHE = {}


def _cached(key, build):
    v = _CACHE.get(key)
    if v is None:
        if len(_CACHE) > 900:
            _CACHE.clear()
        v = _CACHE[key] = build()
    return v


def _lines(key, maker, mini):
    def build():
        grid, bg = maker()
        return render_mini(grid, bg) if mini else render(grid, bg)
    return _cached(key + (_truecolor(), bool(mini)), build)


def enabled():
    try:
        import settings
        return bool(settings.load().get("faces", True))
    except Exception:
        return True


def _seed(name, extra=""):
    return zlib.crc32((str(name) + "|" + str(extra)).encode("utf-8"))


def _mood(p):
    try:
        if getattr(p, "inj_games", 0) > 0:
            return "hurt"
        import morale
        m = morale.get(p)
        return "smile" if m >= 78 else "sad" if m < 32 else "frown" if m < 46 else "neutral"
    except Exception:
        return "neutral"


def player_portrait(p, team=None, year=None, expr=None, mini=False):
    """A player's face: skin from his name, class year in his hair, mood from morale (a bandage when he's hurt).
    mini=True: the 10x5 version for lists and small cards."""
    team = team or getattr(p, "team", None)
    colors = team_colors(getattr(team, "school", None))
    yr = max(0, min(3, int(getattr(p, "year", 3) if year is None else year)))
    expr = expr or _mood(p)
    name = getattr(p, "name", "Player")
    wt = getattr(p, "weight", None)
    return _lines(("p", name, yr, expr, colors, wt),
                  lambda: make_face(_seed(name), skin_for(name), yr, expr, colors, weight=wt), mini)


def coach_portrait(c, expr=None, mini=False):
    """A coach: school cap and headset, hair that grays with his age."""
    team = getattr(c, "team", None)
    colors = team_colors(getattr(team, "school", None)) if team is not None else (hx("3a414f"), hx("aab3c2"))
    age = getattr(c, "age", 50)
    if expr is None:
        seat = getattr(c, "seat", 40) if team is not None else 40
        expr = "sad" if seat >= 72 else "smile" if seat <= 22 else "neutral"
    return _lines(("c", c.name, age, expr, colors),
                  lambda: make_face(_seed(c.name, "coach"), skin_for(c.name), 3, expr, colors, role="coach", age=age),
                  mini)


def recruit_portrait(r, mini=False):
    p = r.player
    try:
        import recruit_plus as rp
        kind = rp.g(r, "kind", "hs")
    except Exception:
        kind = "hs"
    yr = 2 if kind == "juco" else 1 if kind == "intl" else 0
    return player_portrait(p, team=None, year=yr, expr="neutral", mini=mini)


_CLASS_YEAR = {"FR": 0, "SO": 1, "JR": 2, "SR": 3}


def class_year(label):
    """'RS-JR' / 'JR (early)' / 'SR' -> 0..3."""
    s = str(label or "SR").upper()
    return next((v for k, v in _CLASS_YEAR.items() if k in s), 3)


def name_portrait(name, school=None, year=3, expr="neutral", role="player", age=None, mini=False, weight=None):
    """A face for someone known only by name: a drafted player, a coach in the carousel's record book. The same name
    always gets the same face a player or coach card shows."""
    colors = team_colors(school) if school else (hx("3a414f"), hx("aab3c2"))
    yr = max(0, min(3, int(year)))
    if role == "coach":
        return _lines(("nc", name, age, expr, colors),
                      lambda: make_face(_seed(name, "coach"), skin_for(name), 3, expr, colors, role="coach",
                                        age=age or 50), mini)
    return _lines(("np", name, yr, expr, colors, weight),
                  lambda: make_face(_seed(name), skin_for(name), yr, expr, colors, weight=weight), mini)


def vivid_tie(p1, p2):
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(p1[0] / 255, p1[1] / 255, p1[2] / 255)
    if s < .25:
        h, s, v = colorsys.rgb_to_hsv(p2[0] / 255, p2[1] / 255, p2[2] / 255)
    return tuple(int(255 * x) for x in colorsys.hsv_to_rgb(h, min(1, max(s, .5)), max(v, .75)))


def exec_portrait(name, age=55, school=None, mini=False):
    """An athletic director: a suit and a tie in the school's color."""
    p1, p2 = team_colors(school) if school else (hx("3a414f"), hx("aab3c2"))
    suit = hx("2a2f3a")
    tie = vivid_tie(p1, p2)
    return _lines(("ex", name, age, school),
                  lambda: make_face(_seed(name, "ad"), skin_for(name), 3, "neutral", (suit, hx("e8e8ec")), role="exec",
                                    age=age, tie=tie), mini)
