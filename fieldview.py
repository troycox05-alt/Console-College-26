"""
fieldview.py — The field, drawn in text, with the ball where it is.

Before every snap of a game you watch or coach, the field is drawn under the situation line:

      10   20   30   40   50   40   30   20   10
  ▐ AUB ║        │        │        │        ║        │        │        │        │ TROY ▌
  ▐     ║  ──────┃●▶      │        │        ║        │        │        │        │      ▌
  ▐     ║        │        │        │        ║        │        │        │        │      ▌
  Upcountry ball ▶  ·  UPC 34  ·  66 yards from the end zone  ·  first down at the UPC 44

  ●   the ball, on the line of scrimmage        ┃ (cyan)    the line of scrimmage
  ┃ (yellow)   the first-down line              ──▶         this drive so far, and the way it's headed
  The end zone the offense is attacking is lit orange; the one it's defending is gray.
  The away team's end zone is on the left, the home team's on the right, all game.

Settings [F] (Game day): FULL (five lines) · SLIM (two lines) · OFF.
It's drawn from the game itself (sim.yardline is the offense's yards from its own goal line), so the ball is
never anywhere but where the game says it is. Nothing here changes the game.
"""
from ui import C, paint

BODY = 80                      # columns for the 100 yards between the goal lines (default size)
EZ = 6                         # columns for each end zone


class Geo:
    """How big the field is drawn: `body` columns for the 100 yards, `ez` columns per end zone."""
    def __init__(self, body=BODY, ez=EZ):
        self.body, self.ez = int(body), int(ez)
        self.total = self.ez * 2 + self.body
        self.ypc = 100.0 / self.body

    def col(self, x):
        """Body column for a spot x yards from the LEFT goal line."""
        return max(0, min(self.body - 1, int(x / self.ypc)))


DEFAULT_GEO = Geo()

RESET = "\033[0m"
BAND = ("\033[48;5;22m", "\033[48;5;28m")      # the mowed stripes, every ten yards
EZ_HOT = "\033[48;5;166m"                      # the end zone the offense is attacking
EZ_COLD = "\033[48;5;238m"                     # the one it's defending
LINE = "\033[38;5;250m"
LINE_HI = "\033[1;38;5;231m"
LOS = "\033[1;38;5;51m"
FIRST = "\033[1;38;5;226m"
BALL = "\033[1;38;5;231m"
TRAIL = "\033[38;5;157m"
EZ_INK_HOT = "\033[1;38;5;16m"
EZ_INK_COLD = "\033[1;38;5;252m"

# The game view: AUTO / WIDE / COMPACT are the full tablet (tabletview.py); FIELD is just the field under
# the situation line; SLIM is a one-row field; OFF is the plain ticker.
MODES = ("auto", "wide", "compact", "field", "slim", "off")
MODE_WORDS = {"auto": "Tablet (auto size)", "wide": "Tablet, wide", "compact": "Tablet, compact",
              "field": "Field only", "slim": "Slim field", "off": "Off"}
TABLET_MODES = ("auto", "wide", "compact")


def mode():
    try:
        import settings
        m = settings.load().get("field_view", "auto")
    except Exception:
        m = "auto"
    if m == "full":
        m = "field"                                   # v22 saved it as "full"
    return m if m in MODES else "auto"


# ═══ Geometry ═══════════════════════════════════════════════════════════════

def x_of(sim, yardline, offense=None):
    """Yards from the left goal line. The away team defends the left end zone (it drives to the right);
    the home team defends the right one."""
    off = offense if offense is not None else sim.offense
    return float(yardline) if off is getattr(sim, "away", None) else 100.0 - float(yardline)


def drives_right(sim, offense=None):
    off = offense if offense is not None else sim.offense
    return off is getattr(sim, "away", None)


# ═══ Drawing ════════════════════════════════════════════════════════════════

def _blank_rows(sim, off, g):
    right = drives_right(sim, off)
    left_hot = not right                       # the offense attacks the left end zone when it drives left
    rows = []
    for r in range(3):
        row = []
        for c in range(g.total):
            if c < g.ez:
                row.append([EZ_HOT if left_hot else EZ_COLD, "", " "])
            elif c >= g.ez + g.body:
                row.append([EZ_COLD if left_hot else EZ_HOT, "", " "])
            else:
                b = c - g.ez
                row.append([BAND[int((b * g.ypc) // 10) % 2], "", " "])
        rows.append(row)
    for row in rows:                           # the goal lines
        row[g.ez - 1][1], row[g.ez - 1][2] = LINE_HI, "║"
        row[g.ez + g.body][1], row[g.ez + g.body][2] = LINE_HI, "║"
    for y in range(10, 100, 10):               # every ten yards
        c = g.ez + g.col(y)
        ch = "║" if y == 50 else "│"
        for row in rows:
            row[c][1], row[c][2] = (LINE_HI if y == 50 else LINE), ch
    for y in range(5, 100, 10):                # the fives, as hash ticks
        c = g.ez + g.col(y)
        rows[0][c][1], rows[0][c][2] = LINE, "╷"
        rows[2][c][1], rows[2][c][2] = LINE, "╵"
    return rows


def _put_text(row, start, text, ink):
    for i, ch in enumerate(text):
        if 0 <= start + i < len(row):
            row[start + i][1], row[start + i][2] = ink, ch


def _emit(row, indent):
    out, cur, buf = [], None, []
    for bg, fg, ch in row:
        st = (bg, fg)
        if st != cur:
            if buf:
                out.append(cur[0] + cur[1] + "".join(buf) + RESET)
            cur, buf = st, []
        buf.append(ch)
    if buf:
        out.append(cur[0] + cur[1] + "".join(buf) + RESET)
    return " " * indent + "".join(out)


def _labels(indent, g):
    s = [" "] * g.total
    for y in range(10, 100, 10):
        lab = str(min(y, 100 - y))
        c = g.ez + g.col(y) - 1
        for i, ch in enumerate(lab):
            if 0 <= c + i < g.total:
                s[c + i] = ch
    return " " * indent + paint("".join(s), C.GRAY)


def _spot_word(sim, yardline, offense):
    """'AUB 34', 'midfield' — from the offense's yardline."""
    if int(yardline) == 50:
        return "midfield"
    other = sim.other(offense)
    return f"{offense.abbr} {int(yardline)}" if yardline < 50 else f"{other.abbr} {100 - int(yardline)}"


def lines(sim, indent=2, slim=False, geo=None, spot=True):
    """The field as a list of printable lines, or [] when there's no ball in play.
    geo: how big to draw it (Geo). spot: include the 'whose ball / where / first down at' line under it."""
    g = geo or DEFAULT_GEO
    off = getattr(sim, "offense", None)
    if off is None or getattr(sim, "yardline", None) is None:
        return []
    right = drives_right(sim, off)
    rows = _blank_rows(sim, off, g)
    yl = max(0, min(100, sim.yardline))
    x = x_of(sim, yl, off)
    ball_c = g.ez + g.col(x)
    if yl >= 100:
        ball_c = (g.ez + g.body + 1) if right else (g.ez - 2)
    elif yl <= 0:
        ball_c = (g.ez - 2) if right else (g.ez + g.body + 1)
    # the drive so far
    d = getattr(sim, "drive", None) or {}
    if d.get("team") is off and d.get("plays", 0) and d.get("start") is not None:
        c0 = g.ez + g.col(x_of(sim, d["start"], off))
        lo, hi = sorted((c0, ball_c))
        for c in range(lo, hi):
            if rows[1][c][2] in (" ", "│", "║", "╷"):
                rows[1][c][1], rows[1][c][2] = TRAIL, "─"
    # the first-down line, unless it's goal to go
    goal_to_go = yl + sim.togo >= 100
    if not goal_to_go:
        fc = g.ez + g.col(x_of(sim, yl + sim.togo, off))
        for row in rows:
            row[fc][1], row[fc][2] = FIRST, "┃"
    # the line of scrimmage, and the ball on it
    if 0 < yl < 100:
        for r in (0, 2):
            rows[r][ball_c][1], rows[r][ball_c][2] = LOS, "┃"
    rows[1][ball_c][1], rows[1][ball_c][2] = BALL, "●"
    head = ball_c + 1 if right else ball_c - 1              # which way it's headed
    if g.ez <= head < g.ez + g.body and rows[1][head][2] in (" ", "─", "│", "╷", "║"):
        rows[1][head][1], rows[1][head][2] = BALL, "▶" if right else "◀"
    # who's who in the end zones: the team's abbreviation, centered in the columns beside the goal line
    away, home = getattr(sim, "away", None), getattr(sim, "home", None)
    for team, left in ((away, True), (home, False)):
        if team is None:
            continue
        room = g.ez - 1
        ab = team.abbr[:room]
        hot = (left and not right) or ((not left) and right)      # the end zone the offense is attacking
        start = (room - len(ab)) // 2 if left else g.ez + g.body + 1 + (room - len(ab)) // 2
        _put_text(rows[1], start, ab, EZ_INK_HOT if hot else EZ_INK_COLD)
    out = [_labels(indent, g)]
    out += [_emit(r, indent) for r in rows] if not slim else [_emit(rows[1], indent)]
    if spot and not slim:
        out.append(spot_line(sim, indent, g.total))
    return out


def spot_line(sim, indent=0, width=None):
    """'Upcountry ball ▶ · UPC 34 · 66 yards from the end zone · first down at UPC 44', centered when width is given.
    When it won't fit the width, it drops 'yards from the end zone', then uses the abbreviation."""
    import re
    off = sim.offense
    right = drives_right(sim, off)
    yl = max(0, min(100, sim.yardline))
    goal_to_go = yl + sim.togo >= 100
    arrow = "▶" if right else "◀"

    def build(long_name, yards):
        bits = [paint(f"{off.school if long_name else off.abbr} ball {arrow}", C.BWHITE, C.BOLD),
                paint(_spot_word(sim, yl, off), C.BYELLOW)]
        if yards:
            bits.append(paint(f"{max(0, 100 - yl)} yards from the end zone", C.GRAY))
        if goal_to_go:
            bits.append(paint("GOAL TO GO", C.BRED, C.BOLD))
        else:
            bits.append(paint(f"first down at {_spot_word(sim, yl + sim.togo, off)}", C.GRAY))
            if yl >= 80:
                bits.append(paint("RED ZONE", C.BRED, C.BOLD))
        return paint("  ·  ", C.GRAY).join(bits)

    vis = lambda t: len(re.sub(r"\x1b\[[0-9;]*m", "", t))
    text = build(True, True)
    if width:
        for long_name, yards in ((True, False), (False, True), (False, False)):
            if vis(text) <= width:
                break
            text = build(long_name, yards)
        return " " * (indent + max(0, (width - vis(text)) // 2)) + text
    return " " * indent + text


def _key(sim):
    return (getattr(sim, "plays_run", None), sim.yardline, sim.down, sim.togo, id(sim.offense), sim.quarter)


def show(sim, indent=2, force=False):
    """Print the field for this snap (once per snap, whoever asks first) unless Settings turned it off."""
    m = mode()
    if m in TABLET_MODES and not force:                # the tablet draws its own field (tabletview.show)
        return False
    if m == "off" and not force:
        return False
    if getattr(sim, "offense", None) is None:
        return False
    k = _key(sim)
    if not force and getattr(sim, "_fv_key", None) == k:
        return False
    body = lines(sim, indent, slim=(m == "slim"))
    if not body:
        return False
    sim._fv_key = k
    for ln in body:
        print(ln)
    return True
