"""
scout.py — What you're allowed to see (Coach Career).

In Coach Career you never see a player's real numbers — yours or anyone
else's. You see what a head coach sees: practice, film, and his staff's word
for it. Every screen that shows a rating asks this module first:

  ovr(p)          a player's overall        "quality starter"   (78 in other modes)
  sub(v)          a sub-proficiency         "good"              (1.06)
  prof(v)         a position proficiency    "great"             (1.09)
  fund(v)         a fundamental (speed...)  "great"             (84)
  team(v)         a team rating             "strong"            (77)
  odds(wp)        your chance to win        "slight underdog"   ("you win 42%")
  proj(lo, hi)    a recruit's projection    "a backup to a starter"  ("62-71")

Athletic Director mode and simmed seasons show the numbers.

SPECTATOR MODE shows the numbers for everyone except the team you follow:
that one you see through a scout's eye — the words, with an estimate range
next to each ("quality starter (76-81)"). The sportsbook's options can hide
every team's numbers the same way (the sharper game: you and the book both
work from what you can see). Screens say whose ratings they're showing by
passing who= (a team or a player); a screen about one team can set focus().

SCOUT'S EYE (Developer capstone in your coaching tree) adds an estimate next
to every word: "quality starter (76-81)", "good (1.03-1.09)". Estimates are a
range around the truth, a little off-center — never the number itself.

THE SCALES (fixed — a word always means the same range)
  player overall   long shot <48 · developmental 48 · backup 56 · rotation player 64 ·
                   starter 70 · quality starter 76 · star 82 · All-American 88+
  sub/proficiency  horrible <0.80 · bad 0.80 · below average 0.90 · average 0.97 ·
                   good 1.03 · great 1.08 · elite 1.13+
  fundamentals     very poor <40 · poor 40 · below average 50 · average 60 · good 70 ·
                   great 80 · elite 90+
  team             very weak <58 · weak 58 · below average 62 · average 66 · good 70 ·
                   strong 75 · elite 80+
"""
import random

from ui import C, paint, pad, rating

_LG = [None]
_FOCUS = [None]                       # the team the current screen is about (spectator mode)
_FORCE = [False]                      # the league website's export: words for everyone, never a number

OVR = ((48, "long shot"), (56, "developmental"), (64, "backup"), (70, "rotation player"), (76, "starter"),
       (82, "quality starter"), (88, "star"), (999, "All-American"))
FUND = ((40, "very poor"), (50, "poor"), (60, "below average"), (70, "average"), (80, "good"), (90, "great"),
        (999, "elite"))
TEAM = ((58, "very weak"), (62, "weak"), (66, "below average"), (70, "average"), (75, "good"), (80, "strong"),
        (999, "elite"))


def bind(league):
    _LG[0] = league


def _team_of(who):
    if who is None:
        return _FOCUS[0]
    if hasattr(who, "roster"):
        return who
    return getattr(who, "team", None) or _FOCUS[0]


def spectating(lg):
    return lg is not None and getattr(lg, "mode", None) == "spectator"


def hidden(league=None, who=None):
    """Words instead of numbers? who: the team (or a player) whose ratings are on screen."""
    if _FORCE[0]:
        return True
    lg = league or _LG[0]
    if lg is None:
        return False
    if (getattr(lg, "mode", None) == "career" and not getattr(lg, "autosim", False)
            and getattr(lg, "user_coach", None) is not None):
        return True
    if spectating(lg):
        if lg.__dict__.get("hide_all_ratings"):
            return True
        t = _team_of(who)
        return t is not None and t is getattr(lg, "follow_team", None)
    return False


def eye(league=None, who=None):
    """Scout's Eye: estimates next to the words (your coaching tree; in spectator mode, always)."""
    if _FORCE[0]:
        return False
    lg = league or _LG[0]
    if lg is None:
        return False
    if spectating(lg):
        return True
    import skills
    return skills.has(getattr(lg, "user_coach", None), "scouts_eye")


def set_focus(team):
    """The team the current screen is about. Returns the old one (put it back when you leave)."""
    prev = _FOCUS[0]
    _FOCUS[0] = team
    return prev


def focused(fn, get_team):
    """Wrap a screen function so its ratings are judged as belonging to one team."""
    def wrapper(*a, **k):
        try:
            t = get_team(*a, **k)
        except Exception:
            t = None
        prev = set_focus(t)
        try:
            return fn(*a, **k)
        finally:
            set_focus(prev)
    wrapper.__name__ = getattr(fn, "__name__", "screen")
    wrapper.__doc__ = fn.__doc__
    return wrapper


def _w(scale, v):
    return next(w for cut, w in scale if v < cut)


def _col(frac):
    return C.BRED if frac < 0.3 else C.BYELLOW if frac < 0.5 else C.BWHITE if frac < 0.65 else \
        C.BGREEN if frac < 0.85 else C.BMAGENTA


def ovr_word(v):
    return _w(OVR, v)


def _range(v, width, seed, lo=1, hi=99):
    r = random.Random(f"eye|{seed}|{v}")
    mid = v + r.randint(-(width // 2), width // 2)
    a = max(lo, mid - width // 2)
    return a, min(hi, a + width)


def _who(p, who):
    return who if who is not None else (p if hasattr(p, "overall") else None)


def ovr(p, width=0, league=None, who=None):
    """A player's overall as you're allowed to see it (painted)."""
    v = p.overall if hasattr(p, "overall") else p
    if not hidden(league, _who(p, who)):
        return rating(v, max(3, width))
    w = ovr_word(v)
    txt = w
    if eye(league):
        a, b = _range(v, 5, getattr(p, "name", v))
        txt = f"{w} ({a}-{b})"
    idx = [x for _, x in OVR].index(w)
    return paint(pad(txt, width) if width else txt, _col(idx / (len(OVR) - 1)), C.BOLD)


def ovr_plain(p, league=None, who=None):
    v = p.overall if hasattr(p, "overall") else p
    return str(v) if not hidden(league, _who(p, who)) else ovr_word(v)


def sub(v, seed="", league=None, width=0, who=None):
    import subprof
    if not hidden(league, who):
        return paint(pad(f"{v:.2f}", width) if width else f"{v:.2f}", subprof.color(v), C.BOLD)
    w = subprof.word(v)
    txt = w + (f" ({subprof.estimate(v, seed)})" if eye(league) else "")
    return paint(pad(txt, width) if width else txt, subprof.color(v), C.BOLD)


prof = sub


def fund(v, league=None, width=0, who=None):
    if not hidden(league, who):
        return rating(v, max(3, width))
    w = _w(FUND, v)
    txt = w + (f" ({_range(v, 6, 'f')[0]}-{_range(v, 6, 'f')[1]})" if eye(league) else "")
    idx = [x for _, x in FUND].index(w)
    return paint(pad(txt, width) if width else txt, _col(idx / (len(FUND) - 1)), C.BOLD)


def team(v, league=None, width=0, who=None):
    if not hidden(league, who):
        return rating(v, max(3, width))
    w = _w(TEAM, v)
    txt = w
    if eye(league) and spectating(league or _LG[0]):
        a, b = _range(v, 4, f"team|{getattr(_team_of(who), 'school', '')}")
        txt = f"{w} ({a}-{b})"
    idx = [x for _, x in TEAM].index(w)
    return paint(pad(txt, width) if width else txt, _col(idx / (len(TEAM) - 1)), C.BOLD)


TEAM_SHORT = {"elite": "ELT", "strong": "STR", "good": "GD", "average": "AVG", "below average": "BLW",
              "weak": "WK", "very weak": "VWK"}


def team_short(v, league=None, who=None):
    """Three characters wide, for tables."""
    if not hidden(league, who):
        return rating(v)
    w = _w(TEAM, v)
    idx = [x for _, x in TEAM].index(w)
    return paint(pad(TEAM_SHORT[w], 3, "right"), _col(idx / (len(TEAM) - 1)), C.BOLD)


def odds(wp, league=None, who=None):
    """Your chance to win, as a phrase."""
    if not hidden(league, who):
        return f"you win this {wp * 100:.0f}% of the time"
    return ("you're a heavy favorite" if wp >= 0.85 else "you're the favorite" if wp >= 0.65 else
            "you're a slight favorite" if wp >= 0.55 else "it's a toss-up" if wp >= 0.45 else
            "you're a slight underdog" if wp >= 0.35 else "you're the underdog" if wp >= 0.15 else
            "you're a heavy underdog")


def odds_short(wp, league=None, who=None):
    if not hidden(league, who):
        return f"{wp * 100:.0f}%"
    return ("big fav" if wp >= 0.85 else "fav" if wp >= 0.65 else "slight fav" if wp >= 0.55 else
            "toss-up" if wp >= 0.45 else "slight dog" if wp >= 0.35 else "dog" if wp >= 0.15 else "big dog")


def proj(lo, hi, league=None):
    """A recruit's (or transfer's) projection range, in words."""
    if not hidden(league):
        return f"{lo}-{hi}"
    a, b = ovr_word(lo), ovr_word(hi)
    return a if a == b else f"{a} to {b}"


def ovr_tag(p, league=None, who=None):
    """Plain text for inbox/card tags: '78 OVR' or 'looks like a starter'."""
    v = p.overall if hasattr(p, "overall") else p
    return f"{v} OVR" if not hidden(league, _who(p, who)) else f"looks like a {ovr_word(v)}" if ovr_word(v) != "All-American" \
        else "looks like an All-American"


OVR_SHORT = {"long shot": "LS", "developmental": "DEV", "backup": "BU", "rotation player": "ROT", "starter": "STR",
             "quality starter": "QS", "star": "STAR", "All-American": "AA"}
LEGEND = "LS long shot · DEV developmental · BU backup · ROT rotation · STR starter · QS quality starter · STAR · AA"


def ovr_short(p, league=None, who=None):
    """Four characters wide, for tables."""
    v = p.overall if hasattr(p, "overall") else p
    if not hidden(league, _who(p, who)):
        return rating(v)
    w = ovr_word(v)
    idx = [x for _, x in OVR].index(w)
    return paint(pad(OVR_SHORT[w], 4), _col(idx / (len(OVR) - 1)), C.BOLD)


def proj_short(lo, hi, league=None):
    """Eight characters wide at most: '62-71' or 'BU-STR'."""
    if not hidden(league):
        return f"{lo}-{hi}"
    a, b = OVR_SHORT[ovr_word(lo)], OVR_SHORT[ovr_word(hi)]
    return a if a == b else f"{a}-{b}"
