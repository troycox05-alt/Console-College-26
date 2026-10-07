"""
ui.py — Console rendering helpers for Console College.

Colors (ANSI escape codes), padding that ignores color codes, rating bars,
stars, the big title font, and small bits of ASCII art.
"""
import os
import re
import sys

WIDTH = 100
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def init_console():
    """Turn on ANSI colors on Windows, make sure box characters print, and keep every
    line inside the 100-column screen."""
    if os.name == "nt":
        os.system("")  # enables virtual-terminal (ANSI) processing on Windows 10+
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    if not isinstance(sys.stdout, WidthGuard):
        sys.stdout = WidthGuard(sys.stdout)


_SGR = re.compile(r"\x1b\[[0-9;]*m")
_ANY_ESC = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def fold(line, width=None):
    """Break one (colored) line that's wider than the screen: at the last space that fits,
    carrying its colors and indentation onto the next line. Returns a list of lines."""
    width = width or WIDTH
    if visible_len(_ANY_ESC.sub("", line)) <= width:
        return [line]
    plain = _ANY_ESC.sub("", line)
    indent = min(len(plain) - len(plain.lstrip(" ")), 24) + 2
    out, rest = [], line
    first = True
    while True:
        limit = width if first else width
        vis, i, last_space, active = 0, 0, None, []
        while i < len(rest):
            m = _ANY_ESC.match(rest, i)
            if m:
                code = m.group(0)
                if code.endswith("m"):
                    active = [] if code in ("\x1b[0m", "\x1b[m") else active + [code]
                i = m.end()
                continue
            if vis >= limit:
                break
            if rest[i] == " ":
                last_space = (i, list(active), vis)
            vis += 1
            i += 1
        if i >= len(rest):
            out.append(rest)
            break
        cut, act, at = (last_space if last_space and last_space[2] > (indent + 10 if not first else 20)
                        else (i, active, vis))
        out.append(rest[:cut] + "\x1b[0m")
        tail = rest[cut:].lstrip(" ")
        rest = " " * indent + "".join(act) + tail
        first = False
        if visible_len(_ANY_ESC.sub("", rest)) <= width:
            out.append(rest)
            break
    return out


FOLD_SLACK = 4        # a line a few columns over is left alone (it fits any terminal wider than 100)

# How many columns the screen really has, when the game knows better than the terminal does.
# play.py sets it (the window is laid out for the 100-column screen); None means "ask the terminal".
DISPLAY_COLS = None
_ALLOW = [0]          # a wider allowance while a deliberately wide screen (the WIDE tablet) prints


class allow_width:
    """with ui.allow_width(124): lines up to 124 columns print as they are (no folding)."""

    def __init__(self, cols):
        self.cols = int(cols or 0)

    def __enter__(self):
        self.prev = _ALLOW[0]
        _ALLOW[0] = max(self.prev, self.cols)
        return self

    def __exit__(self, *exc):
        _ALLOW[0] = self.prev
        return False


def display_cols():
    """Columns the player can actually see: the window's, or the terminal's."""
    if DISPLAY_COLS:
        return DISPLAY_COLS
    try:
        import shutil
        return shutil.get_terminal_size((0, 0)).columns
    except Exception:
        return 0


def _tr(text):
    """The universe's display terms (universe.py); untouched when it has none."""
    u = sys.modules.get("universe")
    return u.translate(text) if u is not None else text


class WidthGuard:
    """Wraps stdout: any line wider than the screen folds onto the next line instead of
    running off the edge (or wrapping mid-word at the terminal's edge)."""

    def __init__(self, stream):
        self._s = stream
        self._col = 0

    def write(self, text):
        if not text:
            return 0
        text = _tr(text)
        parts = text.split("\n")
        out = []
        for j, part in enumerate(parts):
            if part:
                limit = max(WIDTH, _ALLOW[0])
                if self._col == 0 and visible_len(_ANY_ESC.sub("", part)) > limit + FOLD_SLACK and "\r" not in part:
                    lines = fold(part, width=limit)
                    part = "\n".join(lines)
                    self._col = visible_len(_ANY_ESC.sub("", lines[-1]))
                else:
                    self._col += visible_len(_ANY_ESC.sub("", part))
            out.append(part)
            if j < len(parts) - 1:
                self._col = 0
        self._s.write("\n".join(out))
        return len(text)

    def flush(self):
        try:
            self._s.flush()
        except (OSError, ValueError):
            pass

    def __getattr__(self, name):
        return getattr(self._s, name)


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDER = "\033[4m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BLACK = "\033[38;5;16m"             # true black: stays black when bold (30 turns gray)
    GRAY = "\033[90m"
    BRED = "\033[91m"
    BGREEN = "\033[92m"
    BYELLOW = "\033[93m"
    BBLUE = "\033[94m"
    BMAGENTA = "\033[95m"
    BCYAN = "\033[96m"
    BWHITE = "\033[97m"

    @staticmethod
    def fg256(n):
        return f"\033[38;5;{n}m"


def paint(text, *styles):
    return "".join(styles) + str(text) + C.RESET


def visible_len(text):
    return len(ANSI_RE.sub("", str(text)))


def pad(text, width, align="left"):
    """Pad to a visible width, ignoring ANSI color codes."""
    text = str(text)
    gap = max(0, width - visible_len(text))
    if align == "right":
        return " " * gap + text
    if align == "center":
        left = gap // 2
        return " " * left + text + " " * (gap - left)
    return text + " " * gap


def truncate(text, width):
    text = str(text)
    return text if len(text) <= width else text[: width - 1] + "…"


def clear():
    """Wipe the screen (and the scrollback) without spawning a shell: no flicker."""
    if os.name == "nt" and not os.environ.get("WT_SESSION") and not os.environ.get("TERM"):
        os.system("cls")                         # the classic console: let Windows do it
        return
    try:
        sys.stdout.write("\033[H\033[2J\033[3J")
        sys.stdout.flush()
    except (OSError, ValueError):
        os.system("cls" if os.name == "nt" else "clear")


def pause(msg="Press Enter to continue..."):
    input(_tr("\n  " + paint(" ⏎ ", C.BLACK, bg(C.BWHITE)) + paint(f" {msg}", C.GRAY)))


_ENTER_BACK = re.compile(r"enter\s*(=|to|goes)\s*(go\s+)?(back|cancel|done|never mind|not now|later|no change|close)",
                         re.I)


def ask(prompt):
    """The prompt at the bottom of every screen. Wherever Enter means back (or cancel, or
    done), B and 'back' mean it too — the same way out on every screen."""
    ans = input(_tr("\n  " + paint(" ▶ ", "\033[38;5;16m", bg(C.BCYAN), C.BOLD)
                    + paint(f" {prompt} ", C.BCYAN, C.BOLD))).strip()
    if ans.lower() in ("b", "back", "esc") and _ENTER_BACK.search(str(prompt)):
        return ""
    return ans


def rule(char="─", color=C.GRAY, width=WIDTH):
    return paint(char * width, color)


def bg(color):
    """The background version of a foreground color code."""
    if "38;5;" in color:
        return color.replace("38;5;", "48;5;")
    if "38;2;" in color:
        return color.replace("38;2;", "48;2;")
    m = re.match(r"\x1b\[(\d+)m", color)
    if not m:
        return "\033[100m"
    n = int(m.group(1))
    if 30 <= n <= 37:
        return f"\033[{n + 10}m"
    if 90 <= n <= 97:
        return f"\033[{n + 10}m"
    return "\033[100m"


def on(color):
    """Readable text on a background of this color: black on bright, white on dark."""
    m = re.match(r"\x1b\[(\d+)m", color)
    ink = "\033[38;5;16m"              # true black: bold never turns it gray
    if m and 90 <= int(m.group(1)) <= 97 and int(m.group(1)) != 90:
        return ink
    if m and int(m.group(1)) in (33, 36, 37):
        return ink
    t = re.match(r"\x1b\[38;2;(\d+);(\d+);(\d+)m", color)
    if t:
        r_, g_, b_ = (int(x) for x in t.groups())
        return ink if 0.299 * r_ + 0.587 * g_ + 0.114 * b_ > 140 else C.BWHITE
    n = re.match(r"\x1b\[38;5;(\d+)m", color)
    if n:
        v = int(n.group(1))
        light = (v >= 250) or (16 <= v <= 231 and (((v - 16) // 36) * 3 + ((v - 16) // 6 % 6) * 5 + (v - 16) % 6) >= 20)
        return ink if light else C.BWHITE
    return C.BWHITE


BRAND = "CONSOLE COLLEGE"
BAR_BG = "\033[48;5;235m"          # the charcoal every header sits on
BAR_EDGE = "\033[38;5;235m"
ACCENT = C.BYELLOW                  # key badges, highlights
MUTED = "\033[38;5;244m"


def _t(color):
    """Use the current team's accent wherever the classic menu yellow would appear."""
    return ACCENT if color == C.BYELLOW else color


CRUMB = [None]                      # the dashboard tab you came from: every screen shows its way home


def title_bar(text, color=C.BYELLOW, width=WIDTH, sub=None):
    """Every screen's header: a charcoal bar with the screen's color as a tab on the left,
    the title in white, and (on the right) where you are — or the game's name."""
    color = _t(color)
    text = str(text).replace("  ·  ", " · ")
    right = f"{sub or (CRUMB[0] and '◂ ' + CRUMB[0]) or BRAND}  "
    room = width - 4 - len(right) - 1
    t = text if len(text) <= room else text[:room - 1] + "…"
    left = paint("  ", bg(color)) + paint(f"  {t}", BAR_BG, "\033[1;97m")
    fill = width - visible_len(left) - len(right)
    top = left + paint(" " * max(0, fill), BAR_BG) + paint(right, BAR_BG, MUTED)
    bottom = paint("▀▀", color) + paint("▀" * (width - 2), BAR_EDGE)
    return top + "\n" + bottom


def section(text, color=C.BCYAN):
    color = _t(color)
    tail = max(4, WIDTH - visible_len(text) - 8)
    return paint("  ▌", color, C.BOLD) + paint(f" {text} ", color, C.BOLD) + paint("─" * tail, C.GRAY)


# ─── Panels, tabs, chips: the dashboard toolkit ─────────────────────────────

def clip(text, width):
    """Cut colored text to a visible width without breaking its colors."""
    text = str(text)
    if visible_len(text) <= width:
        return text
    out, seen, i = [], 0, 0
    while i < len(text) and seen < width - 1:
        m = ANSI_RE.match(text, i)
        if m:
            out.append(m.group(0))
            i = m.end()
            continue
        out.append(text[i])
        seen += 1
        i += 1
    return "".join(out) + "…" + C.RESET


def panel(title, lines, width, color=C.GRAY, title_color=C.BWHITE, height=None):
    """A rounded box with a title in the top border. Returns a list of lines."""
    color = _t(color)
    inner = width - 4
    head = f" {title} " if title else ""
    top = paint("╭─", color) + paint(head, title_color, C.BOLD) + paint("─" * max(0, width - 3 - len(head)) + "╮", color)
    body = [paint("│ ", color) + pad(clip(ln, inner), inner) + paint(" │", color) for ln in lines]
    if height is not None:
        while len(body) < height:
            body.append(paint("│ ", color) + " " * inner + paint(" │", color))
        body = body[:height]
    return [top] + body + [paint("╰" + "─" * (width - 2) + "╯", color)]


def columns(*blocks, gap=1):
    """Lay panels side by side."""
    widths = [max((visible_len(ln) for ln in b), default=0) for b in blocks]
    tall = max((len(b) for b in blocks), default=0)
    rows = []
    for i in range(tall):
        parts = [pad(b[i] if i < len(b) else "", w) for b, w in zip(blocks, widths)]
        rows.append((" " * gap).join(parts))
    return rows


def chip(text, color=C.BCYAN):
    """A small solid label: a key, a tag, a status."""
    color = _t(color)
    return paint(f" {text} ", on(color), bg(color), C.BOLD)


_KEY_KEEP = (C.BGREEN, C.BRED, C.GRAY)      # primary, destructive, quiet — everything else wears the accent
QUIET = "\033[38;5;250m"


def key(k, label, color=C.BYELLOW, dim=False):
    """A command: [K] Label. One accent for every key on every screen; green marks the
    main thing to do next, red something you can't take back, gray a way out."""
    if dim:
        return paint(f"[{k}] {label}", C.GRAY)
    col = color if color in _KEY_KEEP else ACCENT
    low = str(label).lower().strip()
    if (low.split(" ")[0] == "back" or low in ("cancel", "done", "close", "never mind")) and color != C.BGREEN:
        col = C.GRAY                                    # the way out always looks the same
    lab = paint(label, QUIET) if col == C.GRAY else paint(label, C.BWHITE)
    return paint(f"[{k}]", col, C.BOLD) + " " + lab


def back_key(label="Back"):
    return key("B", label, C.GRAY)


WINDOW = [False]                    # set by play.py: the window shows commands as buttons of its own


def command_bar(items, width=WIDTH):
    """Footer strip of commands, wrapped to the screen. In the window each line carries an
    invisible mark (U+2063) so the window can fold it into its button row instead of
    showing every command twice."""
    lines, cur = [], "  "
    for it in items:
        if not it:
            continue
        piece = it + "   "
        if visible_len(cur) + visible_len(piece) > width:
            lines.append(cur.rstrip())
            cur = "  "
        cur += piece
    if cur.strip():
        lines.append(cur.rstrip())
    out = [paint("─" * width, "\033[38;5;238m")] + lines
    return ["\u2063" + ln for ln in out] if WINDOW[0] else out


def footer(*items, width=WIDTH):
    """Print a command strip at the bottom of a screen."""
    for ln in command_bar([i for i in items if i], width):
        print(ln)


def tabs(names, active, color=C.BYELLOW, width=WIDTH):
    """A tab strip: the active tab is a solid chip in the screen's color, the rest quiet,
    with a thin rule underneath that lights up under the active tab."""
    color = _t(color)
    cells, under = [], []
    for i, name in enumerate(names, 1):
        label = f" {i} {name} "
        if i == active:
            cells.append(paint(label, on(color), bg(color), C.BOLD))
            under.append(paint("▀" * len(label), color))
        else:
            cells.append(paint(f" {i} ", "\033[38;5;240m") + paint(f"{name} ", "\033[38;5;248m"))
            under.append(paint("─" * len(label), "\033[38;5;238m"))
    line = " ".join(cells)
    rule_ = paint("─", "\033[38;5;238m").join(under)
    rest = width - visible_len(rule_)
    return pad(line, width) + "\n" + rule_ + paint("─" * max(0, rest), "\033[38;5;238m")


def meter(value, width=10, maximum=100, color=None):
    """A slim segmented meter: ▰▰▰▱▱."""
    filled = max(0, min(width, int(round(value / maximum * width))))
    col = color or rating_color(value)
    return paint("▰" * filled, col) + paint("▱" * (width - filled), C.GRAY)


def heat_meter(value, width=12, maximum=100):
    """A hot-seat meter that reads left (cool) to right (hot): every segment wears
    the color of the heat it stands for, so a filling bar visibly runs toward red."""
    filled = max(0, min(width, int(round(value / maximum * width))))
    out = []
    for i in range(width):
        at = (i + 0.5) / width * maximum
        col = C.BGREEN if at < 50 else C.BYELLOW if at < 70 else C.BRED
        out.append(paint("▰", col) if i < filled else paint("▱", C.GRAY))
    return "".join(out)


# ─── Ratings ────────────────────────────────────────────────────────────────

def rating_color(value):
    if value >= 90:
        return C.BMAGENTA
    if value >= 80:
        return C.BGREEN
    if value >= 70:
        return C.GREEN
    if value >= 60:
        return C.BYELLOW
    if value >= 50:
        return C.YELLOW
    return C.BRED


def rating(value, width=3):
    return paint(pad(str(value), width, "right"), rating_color(value), C.BOLD)


TRACK = "\033[38;5;238m"            # the empty part of a bar: a faint track, not a block


def bar(value, width=25, maximum=100, color=None):
    filled = max(0, min(width, int(round(value / maximum * width))))
    col = color or rating_color(value)
    return paint("━" * filled, col, C.BOLD) + paint("─" * (width - filled), TRACK)


def stars(n):
    n = max(0, min(5, n))
    return paint("★" * n, C.BYELLOW) + paint("☆" * (5 - n), C.GRAY)


def proficiency_color(value):
    if value >= 1.05:
        return C.BMAGENTA
    if value >= 0.90:
        return C.BGREEN
    if value >= 0.70:
        return C.BYELLOW
    if value >= 0.45:
        return C.YELLOW
    return C.BRED


# ─── Title art ──────────────────────────────────────────────────────────────

BIG_FONT = {
    "C": [" ████", "█    ", "█    ", "█    ", " ████"],
    "O": [" ███ ", "█   █", "█   █", "█   █", " ███ "],
    "N": ["█   █", "██  █", "█ █ █", "█  ██", "█   █"],
    "S": [" ████", "█    ", " ███ ", "    █", "████ "],
    "L": ["█    ", "█    ", "█    ", "█    ", "█████"],
    "E": ["█████", "█    ", "████ ", "█    ", "█████"],
    "G": [" ████", "█    ", "█  ██", "█   █", " ████"],
    " ": ["   ", "   ", "   ", "   ", "   "],
}


def big_text(word, colors):
    rows = []
    for i in range(5):
        line = "  ".join(BIG_FONT[ch][i] for ch in word.upper())
        rows.append(paint(line, colors[i % len(colors)], C.BOLD))
    return rows


FOOTBALL = [
    "        ____________        ",
    "     .-'  |  |  |  '-.     ",
    "    <  ===|==|==|===  >    ",
    "     '-.__|__|__|__.-'     ",
]


def title_screen_lines():
    warm = [C.fg256(214), C.fg256(208), C.fg256(202), C.fg256(196), C.fg256(160)]
    cool = [C.fg256(51), C.fg256(45), C.fg256(39), C.fg256(33), C.fg256(27)]
    lines = [""]
    for row in big_text("CONSOLE", warm):
        lines.append(pad(row, WIDTH, "center"))
    lines.append("")
    for row in big_text("COLLEGE", cool):
        lines.append(pad(row, WIDTH, "center"))
    lines.append("")
    for row in FOOTBALL:
        lines.append(pad(paint(row, C.fg256(130), C.BOLD), WIDTH, "center"))
    lines.append("")
    lines.append(pad(paint("C O L L E G E   F O O T B A L L   ·   2 0 2 6   S E A S O N", C.GRAY), WIDTH, "center"))
    return lines


# How newspapers fit a school on one line. Applied in order until the name fits.
_SHORTEN = (("Georgia Southern", "Ga. Southern"), ("Mississippi State", "Miss. State"),
            ("Northern Illinois", "N. Illinois"), ("Western Michigan", "W. Michigan"),
            ("Central Michigan", "C. Michigan"), ("Eastern Michigan", "E. Michigan"),
            ("Western Kentucky", "W. Kentucky"), ("Middle Tennessee", "Middle Tenn."),
            ("Southern California", "S. California"), ("South Carolina", "S. Carolina"),
            ("North Carolina", "N. Carolina"), ("East Carolina", "E. Carolina"), ("Florida Atlantic", "Fla. Atlantic"),
            ("San Diego State", "SD State"), ("San Jose State", "San José St."), ("Sacramento State", "Sac State"),
            ("Jacksonville State", "Jax State"), ("Kennesaw State", "Kennesaw St."), ("Appalachian State", "App. State"),
            ("New Mexico State", "NM State"), ("Oklahoma State", "Okla. State"), ("Michigan State", "Mich. State"),
            ("Washington State", "Wash. State"), ("Arizona State", "Ariz. State"), ("Mississippi", "Miss."),
            ("Lowcountry Military", "Lowcountry"), (" State", " St."), ("Southern ", "S. "), ("Northern ", "N. "),
            ("Western ", "W. "), ("Eastern ", "E. "), ("Central ", "C. "))


def short_school(name, width):
    """A school name that fits: 'Georgia Southern' → 'Ga. Southern' before anything gets cut."""
    name = str(name)
    if len(name) <= width:
        return name
    for long, short in _SHORTEN:
        if long in name:
            name = name.replace(long, short)
            if len(name) <= width:
                return name
    return truncate(name, width)


# Newspaper names: what a school is called when a column is tight (13 characters or less).
SHORT_NAMES = {
    'Mississippi State': 'Miss. State', 'South Carolina': 'S. Carolina', 'Michigan State': 'Michigan St.',
    'Southern California': 'S. California', 'North Carolina': 'N. Carolina', 'Oklahoma State': 'Oklahoma St.',
    'Florida Atlantic': 'Fla. Atlantic', 'Appalachian State': 'App. State', 'Georgia Southern': 'Ga. Southern',
    'Arkansas State': 'Arkansas St.', 'Central Michigan': 'C. Michigan', 'Eastern Michigan': 'E. Michigan',
    'Sacramento State': 'Sac State', 'Western Michigan': 'W. Michigan', 'Jacksonville State': 'Jax State',
    'Kennesaw State': 'Kennesaw St.', 'Middle Tennessee': 'Middle Tenn.', 'Missouri State': 'Missouri St.',
    'New Mexico State': 'NM State', 'Western Kentucky': 'W. Kentucky', 'Colorado State': 'Colorado St.',
    'San Diego State': 'San Diego St.', 'Washington State': 'Wash. State', 'North Dakota State': 'N. Dakota St.',
    'Northern Illinois': 'N. Illinois', 'San Jose State': 'San José St.', 'Lowcountry Military': 'Lowcountry',
    'Youngstown State': 'Youngstown', 'Illinois State': 'Illinois St.', 'South Dakota State': 'S. Dakota St.',
    'Eastern Washington': 'E. Washington', 'Portland State': 'Portland St.', 'Northern Arizona': 'N. Arizona',
    'Southern Illinois': 'S. Illinois', 'Southeast Missouri State': 'SE Missouri', 'San Luis Obispo': 'SLO',
    'Northern Colorado': 'N. Colorado', 'Central Arkansas': 'C. Arkansas', 'Eastern Kentucky': 'E. Kentucky',
    'Southeastern Louisiana': 'SE Louisiana', 'Tennessee State': 'Tennessee St.', 'East Tennessee State': 'E. Tenn. State',
    'Western Carolina': 'W. Carolina', 'Boiling Springs': 'Boiling Spr.', 'West Long Branch': 'W. Long Branch',
    'Grambling State': 'Grambling', 'Blacksburg': 'Blacksburg', 'West Virginia': 'West Virginia',
    'East Carolina': 'East Carolina', 'South Florida': 'South Florida', 'Georgia State': 'Georgia State',
    'South Alabama': 'South Alabama', 'Southern Miss': 'Southern Miss', 'Bowling Green': 'Bowling Green',
    'Arizona State': 'Arizona St.', 'Florida State': 'Florida St.', 'New Hampshire': 'New Hampshire',
    'Alabama State': 'Alabama St.', 'Murray State': 'Murray State', 'Montana State': 'Montana St.',
    'Indiana State': 'Indiana St.', 'Winston-Salem': 'Winston-Salem', 'Chattanooga': 'Chattanooga',
}

# Scoreboard abbreviations: 'BOS 19, BBG 14' (one table for the whole game, in teams_data).
from teams_data import ABBREVIATIONS  # noqa: E402


_SQUEEZE = ((" State", " St."), ("South ", "S. "), ("North ", "N. "), ("Eastern ", "E. "), ("Western ", "W. "),
            ("Central ", "C. "), ("Northern ", "N. "), ("Southern ", "S. "), ("Southeast ", "SE "),
            ("Southeastern ", "SE "), ("College", "Coll."), ("Tennessee", "Tenn."), ("Carolina", "Car."),
            ("Virginia", "Va."), ("Georgia", "Ga."), ("Louisiana", "La."), ("Military", "Mil."),
            ("Washington", "Wash."), ("Kentucky", "Ky."), ("Missouri", "Mo."), ("Alabama", "Ala."),
            ("Florida", "Fla."), ("Dakota", "Dak."), ("Illinois", "Ill."), ("Colorado", "Colo."),
            ("Michigan", "Mich."), ("Arkansas", "Ark."), ("Arizona", "Ariz."), ("Hampshire", "Hamp."),
            ("Island", "Isl."), ("Texas", "Tex."), ("Chattanooga", "Chatt."), ("Montana", "Mont."),
            ("Portland", "Port."), ("Kennesaw", "Kenn."), ("Jackson", "Jax."), ("Springs", "Spr."), ("Branch", "Br."))


def short_name(school, width=13):
    """A school in a tight column, the way a newspaper prints it — never cut mid-word if avoidable."""
    school = str(school)
    if len(school) <= width:
        return school
    s = SHORT_NAMES.get(school)
    if s and len(s) <= width:
        return s
    name = s or school
    for long, short in _SQUEEZE:
        if long in name:
            name = name.replace(long, short)
            if len(name) <= width:
                return name
    a = ABBREVIATIONS.get(school)
    if a and len(a) <= width:
        return a
    return truncate(name, width)


def abbr(school):
    """'Boston' → 'BC'. Schools without one keep a short name."""
    s = str(school)
    if s in ABBREVIATIONS:
        return ABBREVIATIONS[s]
    # No scoreboard abbreviation on file (mostly FCS): build one the same way — initials,
    # so a crawl never mixes "MIA" with "S. Utah".
    words = [w for w in s.replace("-", " ").split() if w[0].isalpha() and w.lower() not in ("of", "the", "&")]
    if len(words) >= 2:
        return "".join(w[0].upper() for w in words)[:4]
    return s[:4].upper()


# ═══ Menus: one look for every list of choices ═══════════════════════════════

def menu_item(k, label, desc="", value=None, color=None, width=WIDTH, label_w=26, indent=3, value_w=12):
    """One row of a menu: [K]  Label           value   description (wrapped under itself)."""
    import textwrap
    col = color if color in _KEY_KEEP else ACCENT
    badge = paint(f"[{k}]", col, C.BOLD)
    kw = max(3, len(str(k)) + 2)
    lab = paint(label, QUIET) if col == C.GRAY else paint(label, C.BWHITE, C.BOLD)
    head = " " * indent + pad(badge, kw) + "  " + pad(lab, label_w)
    if value is not None:
        head += pad(value, value_w) + " "
    room = width - visible_len(head) - 1
    lines = textwrap.wrap(desc, max(20, room)) if desc else []
    out = [head + (paint(lines[0], MUTED) if lines else "")]
    for ln in lines[1:]:
        out.append(" " * visible_len(head) + paint(ln, MUTED))
    return "\n".join(out)


def on_off(v, on_word="ON", off_word="OFF"):
    """A small status chip."""
    return paint(f" {on_word} ", "\033[1;38;5;16;48;5;78m") if v else paint(f" {off_word} ", "\033[1;38;5;250;48;5;238m")


def stepper(step, total, label=""):
    """'NEW CAREER · STEP 3 OF 8' for the right side of a title bar."""
    return f"{label + ' · ' if label else ''}STEP {step} OF {total}"


def confirm(prompt, default=False):
    """A yes/no question. Enter takes the default."""
    hint = "Y/n" if default else "y/N"
    a = ask(f"{prompt} ({hint})").strip().lower()
    if not a:
        return default
    return a in ("y", "yes")


def center(text, width=WIDTH):
    return pad(text, width, "center")


def note(text, color=None):
    """A one-line message after an action (saved, can't do that...)."""
    print(paint("   " + text, color or MUTED))


# ═══ The logo ════════════════════════════════════════════════════════════════
_SHADOW = {
    "C": [" ██████╗", "██╔════╝", "██║     ", "██║     ", "╚██████╗", " ╚═════╝"],
    "O": [" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "N": ["███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"],
    "S": ["███████╗", "██╔════╝", "███████╗", "╚════██║", "███████║", "╚══════╝"],
    "L": ["██╗     ", "██║     ", "██║     ", "██║     ", "███████╗", "╚══════╝"],
    "E": ["███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"],
    "G": [" ██████╗ ", "██╔════╝ ", "██║  ███╗", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
}


def _shadow_word(word, shades, edge):
    rows = []
    for i in range(6):
        raw = "".join(_SHADOW[ch][i] for ch in word)
        out, cur, run = [], None, ""

        def flush(kind, text):
            if kind == "b":
                return paint(text, shades[i], C.BOLD)
            if kind == "e":
                return paint(text, edge)
            return text
        for ch in raw:
            kind = "b" if ch == "█" else "e" if ch != " " else " "
            if kind != cur and run:
                out.append(flush(cur, run))
                run = ""
            cur = kind
            run += ch
        if run:
            out.append(flush(cur, run))
        rows.append("".join(out))
    return rows


def logo_lines(width=WIDTH):
    """CONSOLE over COLLEGE: gold on top, white below, with a charcoal drop shadow."""
    gold = [C.fg256(n) for n in (229, 228, 221, 220, 214, 208)]
    white = [C.fg256(n) for n in (255, 254, 253, 251, 249, 247)]
    try:
        import theme
        ramps = theme.logo_ramps()
        if ramps:
            gold, white = ramps
    except Exception:
        pass
    edge = C.fg256(239)
    lines = [center(r, width) for r in _shadow_word("CONSOLE", gold, edge)]
    lines += [center(r, width) for r in _shadow_word("COLLEGE", white, edge)]
    return lines
