"""
difficulty.py — How hard the job is (Coach Career).

Chosen when you create your coach; change it any time from Settings (tab 8 → [S] → [D])
or your career page ([L]). It follows your coach from job to job. Difficulty never touches
the football: your players play to their ratings and the other sideline is as smart as
it is on any level. What changes is the job around the games.

                 AD expects     Hot seat      Recruiting   NIL / player money
  Freshman       1 win fewer    heats 35%     +15% pull    +15%
                                slower
  Varsity        as it is       as it is      as it is     as it is
  All-American   +0.75 wins     heats 20%     -12%         -10%
                                faster
  Golden Helmet  +1.5 wins      heats 40%     -22%         -20%
                                faster

  AD expects    wins added to what your AD thinks you should win (per 12 games)
  Hot seat      how fast the seat warms when things go wrong (it cools as it does)
  Recruiting    interest you earn from every pitch, visit and call
  NIL           the money your program has left for players each year
"""
from ui import C, ask, clear, paint, pause, title_bar

LEVELS = {
    "freshman":     {"name": "Freshman", "expect": -1.0, "heat": 0.65, "recruit": 1.15, "nil": 1.15,
                     "blurb": "Learn the job. A patient AD, recruits who listen, boosters with deep pockets."},
    "varsity":      {"name": "Varsity", "expect": 0.0, "heat": 1.0, "recruit": 1.0, "nil": 1.0,
                     "blurb": "The job as it's tuned. Nothing added, nothing taken away."},
    "all_american": {"name": "All-American", "expect": 0.75, "heat": 1.2, "recruit": 0.88, "nil": 0.9,
                     "blurb": "A demanding AD, a shorter leash, recruits harder to move, tighter money."},
    "heisman":      {"name": "Golden Helmet", "expect": 1.5, "heat": 1.4, "recruit": 0.78, "nil": 0.8,
                     "blurb": "The job is uphill everywhere but the field. For coaches who've won a title or two."},
}
ORDER = list(LEVELS)
DEFAULT = "varsity"


def key_of(coach):
    k = getattr(coach, "difficulty", None) if coach is not None else None
    return k if k in LEVELS else DEFAULT


def of_coach(coach):
    """Your coach's level (Varsity for anyone else)."""
    if coach is None or not getattr(coach, "is_user", False):
        return LEVELS[DEFAULT]
    return LEVELS[key_of(coach)]


def of_team(team):
    return of_coach(getattr(team, "coach", None))


def form(team):
    """Retired: difficulty no longer changes how your team plays."""
    return 0.0


def expect(coach):
    """Extra wins (per 12 games) your AD expects."""
    return of_coach(coach)["expect"]


def nil(team):
    return of_team(team)["nil"]


def heat(coach):
    return of_coach(coach)["heat"]


def recruit(team):
    return of_team(team)["recruit"]


def read_vs(team):
    """Retired: the other sideline reads you the same on every level."""
    return 0.0


def name(coach):
    return LEVELS[key_of(coach)]["name"]


def _row(i, k, cur=None):
    lv = LEVELS[k]
    mark = paint("  ← current", C.BGREEN, C.BOLD) if k == cur else ""
    fx = (f"AD expects {lv['expect']:+.2f} wins · seat heats ×{lv['heat']:.2f} · "
          f"recruiting ×{lv['recruit']:.2f} · NIL ×{lv['nil']:.2f}")
    print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)}  {paint(lv['name'], C.BWHITE, C.BOLD):<30}{mark}")
    print(paint(f"        {lv['blurb']}", C.GRAY))
    print(paint(f"        {fx}", C.BCYAN))


def choose(cur=None, title="HOW HARD IS THE JOB?", sub=None):
    """The picker. Returns a level key (Enter keeps the current one, or Varsity)."""
    clear()
    print(title_bar(title, sub=sub))
    print(paint("\n   Only your job feels it: your AD, your seat, your recruiting, your money. The football itself\n"
                "   never changes. You can change it any time (Settings → [D]).\n", C.GRAY))
    for i, k in enumerate(ORDER, 1):
        _row(i, k, cur)
        print()
    c = ask(f"Difficulty (Enter = {LEVELS[cur or DEFAULT]['name']}):").strip()
    if c.isdigit() and 1 <= int(c) <= len(ORDER):
        return ORDER[int(c) - 1]
    return cur or DEFAULT


def set_level(league, coach, k):
    """Change it. The career page keeps a note of every change."""
    if coach is None or k not in LEVELS:
        return
    old = key_of(coach)
    coach.difficulty = k
    if old != k:
        coach.__dict__.setdefault("difficulty_log", []).append(
            (getattr(league, "year", None), getattr(league, "week", None), old, k))


def menu(league):
    """Settings → [D]: change your coach's difficulty (Coach Career only)."""
    coach = getattr(league, "user_coach", None) if league is not None else None
    if coach is None or getattr(league, "mode", None) != "career":
        clear()
        print(title_bar("DIFFICULTY"))
        print(paint("\n   Difficulty is a Coach Career setting — it rides with your coach. Start a career to set it.", C.GRAY))
        pause()
        return
    cur = key_of(coach)
    k = choose(cur, title=f"DIFFICULTY  ·  COACH {coach.name.upper()}")
    if k != cur:
        set_level(league, coach, k)
        print(paint(f"\n   {LEVELS[k]['name']} it is. It starts with your next game.", C.BGREEN))
        pause()
