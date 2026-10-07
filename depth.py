"""
depth.py — How staffs build and manage depth charts.

EVERY PRESEASON every staff builds its depth chart from scratch:
  - the grade: each player as the staff sees him — his real ability, blurred by
    how good the staff is at evaluating (a sharp staff is close to the truth,
    a shaky one misses by a few points), veterans read better than freshmen
  - the scheme: starters per position follow the offense's base personnel
    (a Smashmouth team starts two tight ends)
  - position moves: a thin or weak room gets help from a crowded one — a third
    safety who'd start at corner moves to corner (a few moves a year, never
    leaving the room he came from short)
  - redshirts: a true freshman who isn't starting sits behind a veteran who's
    close, to save his year

EVERY WEEK OF THE SEASON the staff re-sorts: players develop, the read gets
sharper with film, and a backup who has passed a starter takes the job. The
starter has an edge (the job is his to lose), so charts don't flip every week
over a point. Injured players keep their spot and get it back when healthy.

YOUR TEAM (Coach Career): your staff builds your chart every preseason — with
the same eye your practice report uses — and lists any position moves it would
make. From there the chart is yours: the staff doesn't touch it during the
season (the practice report still recommends changes; [A] accepts them).
"""
import random

from models import POSITIONS

INCUMBENT = 2.0            # the starter's edge in the weekly re-sort
MAX_MOVES = 3              # position moves a staff makes in a preseason
# Where a player can realistically move (from -> to).
MOVES = {"S": ("CB", "LB"), "CB": ("S", "WR"), "LB": ("S", "DL"), "DL": ("LB", "OL"), "OL": ("DL", "TE"),
         "TE": ("OL", "WR", "DL"), "WR": ("CB", "TE", "RB", "S"), "RB": ("WR", "LB", "S", "CB"),
         "QB": ("WR", "RB", "S")}
ROOM_MIN = {"QB": 3, "RB": 3, "WR": 6, "TE": 3, "OL": 8, "DL": 7, "LB": 5, "CB": 5, "S": 4, "K": 1, "P": 1}


def starters(team):
    """Starters per position in the scheme's base personnel."""
    import practice
    return practice.starter_counts(team)


def _eye(team, pos):
    import practice
    return practice._staff_eval(team, pos)


def grade(league, team, p, pos=None, week=None):
    """The staff's read of a player at a position (a CPU staff's eye: no practice report)."""
    pos = pos or p.position
    week = league.week if week is None else week
    rng = random.Random(f"depth:{league.seed}:{team.school}:{p.first_name}:{p.last_name}:{pos}:{league.year}:{week // 4}")
    from traits import mod as trait_mod
    import coach_profile
    c = team.coach
    eye = (coach_profile.value(c, "evaluation") / max(1, c.overall)) * trait_mod(c, "eye", 1.0) if c else 1.0
    blur = 1.2 / max(0.5, _eye(team, pos) * eye)
    try:
        import offseason_cal
        blur *= offseason_cal.read_mult(league, team, p, pos)
    except Exception:
        pass
    blur *= 1 - 0.35 * min(1, max(0, week) / 12)          # film sharpens the read as the season goes
    if p.year >= 2:
        blur *= 0.75                                        # they've coached the veterans for years
    v = p.overall_at(pos) + rng.gauss(0, blur)
    if pos in ("QB", "OL"):
        v += min(1.5, p.year * 0.5)                         # the positions where experience matters most
    return v


def _order_room(league, team, pos, room, keep_starters, grader):
    n = starters(team).get(pos, 1)
    current = team.players_at(pos)[:n] if keep_starters else []
    inc = {id(p) for p in current}
    val = {id(p): grader(p) + (INCUMBENT if id(p) in inc else 0) for p in room}
    ranked = sorted(room, key=lambda p: -val[id(p)])
    # Save a redshirt: a true freshman below the starters sits behind a veteran within 2 points.
    top, rest = ranked[:n], ranked[n:]
    rest.sort(key=lambda p: -(val[id(p)] - (2.0 if p.year == 0 and not p.redshirt else 0)))
    return top + rest


def move_ideas(league, team, grader=None, limit=MAX_MOVES):
    """[(player, from, to, why)] — the position moves a staff would make."""
    raw = grader or (lambda p, pos: grade(league, team, p, pos))
    memo = {}

    def grader(p, pos):
        k = (id(p), pos)
        if k not in memo:
            memo[k] = raw(p, pos)
        return memo[k]
    counts = starters(team)
    rooms = {pos: sorted((p for p in team.roster if p.position == pos), key=lambda p: -grader(p, pos))
             for pos in POSITIONS}
    ideas, moved = [], set()
    for _ in range(limit):
        best = None
        for pos in POSITIONS:
            if pos in ("K", "P", "QB"):
                continue
            n = counts.get(pos, 1)
            room = rooms[pos]
            short = len(room) < ROOM_MIN.get(pos, n + 1)
            weakest = grader(room[n - 1], pos) if len(room) >= n else 0
            for q, others in MOVES.items():
                if pos not in others:
                    continue
                qn = counts.get(q, 1)
                qroom = rooms[q]
                if len(qroom) - 1 < ROOM_MIN.get(q, qn + 1):
                    continue                                   # don't leave his room short
                for p in qroom[qn + 1:]:                       # never a starter or the first backup
                    if id(p) in moved or p.year >= 3 and not short or getattr(p, "inj_games", 0) > 0:
                        continue                               # seniors stay put unless it's an emergency
                    there = grader(p, pos)
                    here = grader(p, q)
                    if short and there >= 45 and there >= here - 12:
                        gain = 10 + there - weakest - max(0, here - there) * 0.5
                        why = f"{pos} is short on bodies"
                    elif there >= weakest + 3 and there >= here - 4:
                        gain = there - weakest - max(0, here - there) * 0.5
                        why = f"he'd start at {pos}"
                    else:
                        continue
                    if best is None or gain > best[0]:
                        best = (gain, p, q, pos, why)
        if best is None:
            break
        _, p, q, pos, why = best
        moved.add(id(p))
        ideas.append((p, q, pos, why))
        rooms[q].remove(p)
        rooms[pos].append(p)
        rooms[pos].sort(key=lambda x: -grader(x, pos))
    return ideas


def apply_move(league, team, p, new):
    old = p.position
    order = team.__dict__.setdefault("depth_order", {})
    if old in order and p in order[old]:
        order[old].remove(p)
    p.position = new
    p.events[league.year].append(f"Moved from {old} to {new}")


def sort_team(league, team, preseason=False):
    """A CPU staff builds (preseason) or manages (in season) its depth chart."""
    if preseason:
        for p, q, pos, why in move_ideas(league, team):
            apply_move(league, team, p, pos)
    order = team.__dict__.setdefault("depth_order", {})
    for pos in POSITIONS:
        room = [p for p in team.roster if p.position == pos]
        order[pos] = _order_room(league, team, pos, room, not preseason, lambda p: grade(league, team, p, pos))


def staff_sort_yours(league, team):
    """Your staff builds your depth chart for fall camp: their eye (the practice report's), and a list of
    position moves they'd make — yours to accept on the depth chart screen."""
    import practice
    counts = starters(team)
    team._last_starters = [p for pos in POSITIONS for p in team.players_at(pos)[:counts.get(pos, 1)]]
    rec = practice.recommend(league, team)             # last year's starters keep their edge
    order = team.__dict__.setdefault("depth_order", {})
    order.clear()
    for pos, lst in rec.items():
        order[pos] = list(lst)
    ideas = move_ideas(league, team, grader=lambda p, pos: (practice.perceived(league, team, p) if pos == p.position
                                                            else grade(league, team, p, pos)))
    team.depth_ideas = [(p, q, pos, why, league.year) for p, q, pos, why in ideas]
    team.depth_set = league.year
    starts = starters(team)
    return sum(1 for pos in POSITIONS for p in order.get(pos, [])[:starts.get(pos, 1)]), ideas


def yours(league, team):
    """True when this is your team and you set the depth chart (not while seasons sim)."""
    import hotseat
    if getattr(league, "mode", None) == "online":            # an online coach's chart is his, as in a career
        import commissioner
        return commissioner.is_player_team(league, team)
    return (getattr(league, "mode", None) == "career" and hotseat.is_human(league, team)
            and not getattr(league, "autosim", False))


def preseason(league):
    """Every program's staff builds its depth chart for the new season."""
    for team in league.teams:
        if yours(league, team):
            staff_sort_yours(league, team)
            if getattr(league, "mode", None) != "career":
                continue                                        # online: no single career log on the host
            import hotseat
            with hotseat.acting_as(league, team):               # Hot Seat: into HIS career log
                league.__dict__.setdefault("career_log", []).append(
                    (league.year, "Fall camp opened: your staff handed you its first depth-chart read."))
        else:
            sort_team(league, team, preseason=True)
            _commissioner_locks(league, team)


def _commissioner_locks(league, team):
    """Commissioner Mode: a player's own depth chart sits on top of the staff's sort."""
    import commissioner
    if commissioner.is_player_team(league, team):
        import orders
        orders.apply_depth(league, team)


def weekly(league):
    """After every week: CPU staffs re-sort (development, film, a backup who's passed a starter)."""
    for team in league.teams:
        if not yours(league, team):
            sort_team(league, team, preseason=False)
            _commissioner_locks(league, team)
