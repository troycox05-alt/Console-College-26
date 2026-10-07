"""Transfer watch: who might hit the portal. Your staff's read on your own guys,
a rumor-mill read on everyone else. Words only, never numbers."""
import random
import portal
from portal import STARTER_DEPTH
from ui import C, ask, clear, pad, paint, pause, title_bar

YEARS = {0: "FR", 1: "SO", 2: "JR", 3: "SR"}
OWN = [(0.03, None, None), (0.08, "Settled", C.GREEN), (0.16, "Some chatter", C.YELLOW),
       (0.28, "Restless", C.BYELLOW), (0.42, "Likely gone", C.BRED), (9, "Halfway out the door", C.BRED)]
RUMOR = [(0.05, None, None), (0.15, "Quiet whispers", C.YELLOW), (0.30, "Rumored unhappy", C.BYELLOW),
         (9, "Expected to bolt", C.BRED)]


def _label(odds, scale):
    for cap, name, col in scale:
        if odds < cap:
            return name, col


def _role(team, p):
    r, s = portal.depth_chart_rank(team, p), STARTER_DEPTH.get(p.position, 2)
    return "starter" if r <= s else "next up" if r == s + 1 else "buried"


def _why(team, p):
    out = []
    if _role(team, p) == "buried":
        out.append("buried on the depth chart")
    d = getattr(p, "nil_demand", None)
    if d and d.get("status") == "refused":
        out.append("NIL talks broke down")
    if getattr(p, "disgruntled", None) is not None:
        out.append("unhappy with his role")
    try:
        import morale
        if morale.get(p) < 36:
            out.append("low morale")
    except Exception:
        pass
    if getattr(p, "fit_bonus", 1.0) < 1.0:
        out.append("bad scheme fit")
    if team.win_pct < 0.34:
        out.append("tired of losing")
    return ", ".join(out[:2])


def _rows(league, team, mine):
    rows = []
    for p in team.roster:
        odds = portal.entry_odds(team, p, portal.depth_chart_rank(team, p))
        rng = random.Random(f"{p.name}|{team.school}|{league.year}|{league.week}")
        if mine:
            odds *= rng.uniform(0.85, 1.15)              # a good staff is close, not perfect
            name, col = _label(odds, OWN)
        else:
            odds = odds * rng.uniform(0.4, 1.8) + rng.uniform(-0.04, 0.05)   # the rumor mill
            name, col = _label(odds, RUMOR)
        if name:
            rows.append((odds, p, name, col))
    rows.sort(key=lambda r: -r[0])
    return rows


def screen(league, team):
    mine = team is getattr(league, "user_team", None)
    while True:
        clear()
        title = "YOUR STAFF'S READ" if mine else "AROUND THE LEAGUE (rumors, not gospel)"
        print(title_bar(f"TRANSFER WATCH · {team.school.upper()} · {title}"))
        rows = _rows(league, team, mine)
        if rows:
            print(paint(f"   {'POS':<4}{'PLAYER':<24}{'YR':<4}{'ROLE':<9}{'RISK':<22}" + ("WHY" if mine else ""), C.GRAY, C.BOLD))
        if not rows:
            print(paint("   Nobody's making noise right now.", C.GRAY))
        for _, p, name, col in rows[:25]:
            line = f"   {pad(p.position, 4)}{pad(p.name, 24)}{pad(YEARS.get(p.year, ''), 4)}{pad(_role(team, p), 9)}{paint(pad(name, 22), col)}"
            if mine:
                line += paint(_why(team, p), C.GRAY)
            print(line)
        if not mine:
            print(paint("\n   Outside reads are guesses from message boards and agents. Expect misses.", C.GRAY))
        prompt = "\n  [T] Another team  [M] My team" + ("  [R] Retention conversations" if mine else "") + "  [Enter] Back"
        c = ask(prompt).strip().lower()
        if c == "r" and mine:
            import retention
            retention.screen(league, team)
        elif c == "t":
            import screens
            t = screens.pick_team(league)
            if t is not None:
                team, mine = t, t is getattr(league, "user_team", None)
        elif c == "m" and getattr(league, "user_team", None) is not None:
            team, mine = league.user_team, True
        else:
            return
