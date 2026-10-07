"""
theme.py — Team colors for the interface.

  * Every screen ABOUT a team (its page, depth chart, recruiting board, schedule, budget, stadium, matchup card...)
    is drawn in that team's color: League.team_color(team).
  * Every menu is drawn in the color of the team you coach or follow: the dashboard and its tabs, the key badges
    ([K] Label) everywhere, the settings and new-game menus, and the title screen (which uses the team in your latest
    save). Hot Seat gives each coach his own.

A school's color is its primary or secondary, brightened until it reads on a dark screen:
  - a bright, colorful primary is used as it is (Georgia red, Texas burnt orange, Clemson orange);
  - a very dark primary (navy, forest, black) hands the job to a colorful secondary (Auburn orange, Michigan maize,
    Oregon yellow, Notre Dame gold) — or, with no colorful secondary (Penn State), a vivid version of itself;
  - a dark-red or purple primary is brightened but keeps its hue (Alabama crimson, LSU purple).
The other color is the second accent (the logo's second word, the window's second highlight).

Settings -> [T] Team colors turns all of this off (the game's usual yellow and conference colors return).
"""
import colorsys

import faces
import ui

WHITEISH = (232, 232, 238)


def _hsv(c):
    return colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)


def _rgb(h, s, v):
    return tuple(int(round(255 * x)) for x in colorsys.hsv_to_rgb(h, s, v))


def vivid(c):
    """The same hue, bright enough to read on a dark screen."""
    h, s, v = _hsv(c)
    return _rgb(h, min(s, .92), max(v, .88))


def _choose(primary, secondary):
    """-> (accent, accent2) as RGB."""
    ph, ps, pv = _hsv(primary)
    sh, ss, sv = _hsv(secondary)
    sec_color = ss > .30 and sv > .45
    if ps < .22:                                   # a black/gray/white primary: lean on the secondary
        if sec_color:
            return vivid(secondary), (210, 214, 222)
        return (205, 210, 218), WHITEISH
    if pv < .36 and sec_color:                     # navy, forest, maroon... with a real second color
        return vivid(secondary), vivid(primary)
    acc = vivid(primary)
    return acc, (vivid(secondary) if sec_color else WHITEISH)


class Theme:
    def __init__(self, school):
        self.school = school
        self.primary, self.secondary = faces.team_colors(school)
        self.accent, self.accent2 = _choose(self.primary, self.secondary)

    @staticmethod
    def code(rgb):
        """An ANSI foreground code: 24-bit if the terminal can, else the nearest of 256."""
        if faces._truecolor():
            return f"\033[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m"
        return f"\033[38;5;{faces._c256(rgb)}m"

    @property
    def accent_fg(self):
        return self.code(self.accent)

    @property
    def accent2_fg(self):
        return self.code(self.accent2)

    def ramp(self, rgb=None, n=6):
        """Light-to-dark shades of the accent for the big title letters."""
        c = rgb or self.accent
        w = (255, 255, 255)
        steps = [faces.mix(c, w, .55), faces.mix(c, w, .35), faces.mix(c, w, .15), c, faces.shade(c, .85),
                 faces.shade(c, .70)]
        return [self.code(x) for x in steps[:n]]

    def hex(self, rgb=None):
        c = rgb or self.accent
        return "#%02x%02x%02x" % tuple(c)


CURRENT = None
_CACHE = {}


def enabled():
    try:
        import settings
        return bool(settings.load().get("team_theme", True))
    except Exception:
        return True


def for_school(school):
    if not school:
        return None
    t = _CACHE.get(school)
    if t is None:
        t = _CACHE[school] = Theme(school)
    return t


def for_team(team):
    return for_school(getattr(team, "school", team if isinstance(team, str) else None))


def accent_for(team):
    """The ANSI color for a screen about `team` (None when Team colors is off or the team is unknown)."""
    if not enabled():
        return None
    t = for_team(team)
    return t.accent_fg if t is not None else None


def set_current(team, persist=True):
    """Menus now wear this team's color. `persist` remembers it so the title screen next launch does too."""
    global CURRENT
    t = for_team(team) if enabled() else None
    CURRENT = t
    ui.ACCENT = t.accent_fg if t is not None else ui.C.BYELLOW
    if persist and t is not None:
        try:
            import settings
            s = settings.load()
            if s.get("theme_school") != t.school:
                s["theme_school"] = t.school
                settings.save()
        except Exception:
            pass
    return t


def clear():
    set_current(None, persist=False)


def init():
    """At launch: wear the team of the last game (until the title screen reads the latest save)."""
    try:
        import settings
        school = settings.load().get("theme_school")
    except Exception:
        school = None
    set_current(school, persist=False)


def logo_ramps():
    """(top word ramp, bottom word ramp) for the title letters, or None for the classic gold/white."""
    if CURRENT is None:
        return None
    return CURRENT.ramp(CURRENT.accent), CURRENT.ramp(CURRENT.accent2)


def window_colors():
    """For the window's chrome: hex accent and second accent (None when the theme is off)."""
    if CURRENT is None:
        return None
    return {"a": CURRENT.hex(CURRENT.accent), "b": CURRENT.hex(CURRENT.accent2), "school": CURRENT.school}
