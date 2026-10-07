"""
gray_area.py — Bending the rules (Coach Career). Both open from the recruiting hub.

OVERTIME [O]  Once a week: ten more recruiting hours than the rules allow. Every use is a
              roll — about 6% the first time, more each time you do it in a season — that
              someone notices and a recruiting-violation case opens. Not caught can still leave
              a trace that surfaces later.

TAMPERING [T] Reach out to a player on another roster — in season or in the offseason —
              before he's in the portal. Three ways in: through his trainer (quiet, small
              push), his high-school coach (a real push, some risk), or a direct call with an
              NIL number (big push, real risk). Once per player per season. It makes him likelier
              to enter the portal and likelier to pick you when he does. Get caught and his school
              reports you for tampering — and if he does transfer to you, that's another chance
              for it all to come out.
"""
import random

from ui import C, ask, clear, pad, paint, pause, rule, title_bar, truncate

OT_HOURS = 10
OT_BASE, OT_STEP = 0.06, 0.03
APPROACHES = [("trainer", "Through his trainer — a quiet word", 0.10, 0.06, 3),
              ("hs", "Through his high-school coach", 0.18, 0.13, 3),
              ("direct", "Call him yourself, with an NIL number", 0.32, 0.26, 2)]


def _log(league, text):
    league.__dict__.setdefault("career_log", []).append((league.year, text))


def _case(league, team, kind, level, text, caught, evidence=60):
    try:
        import compliance as co
        if not co.active(league):
            return None
        rng = random.Random(f"{kind}:{team.school}:{league.year}:{league.week}:{text}")
        c = co.new_case(league, team, kind, level, rng, user=True, text=text, evidence=evidence, players=[])
        if caught:
            co.discover(league, c, "report", rng)
        return c
    except Exception:
        return None


# ═══ Overtime ═══════════════════════════════════════════════════════════════

def overtime_used(league, team):
    book = league.recruiting.__dict__.setdefault("overtime", {})
    return book.get((team.school, league.week), 0)


def bonus_hours(cycle, team):
    import commissioner
    if not commissioner.allows(cycle.league, "rule_bending"):
        return 0
    return cycle.__dict__.get("overtime", {}).get((team.school, cycle.league.week), 0)


def _blocked(league):
    """Commissioner Mode with rule-bending switched off: the option simply isn't there."""
    import commissioner
    if commissioner.allows(league, "rule_bending"):
        return False
    print(paint("   Rule-bending is switched off in this league.", C.GRAY))
    pause()
    return True


def overtime(league, team):
    if _blocked(league):
        return
    cyc = league.recruiting
    if league.week < 1:
        print(paint("   Hours don't start until Week 1.", C.GRAY))
        pause()
        return
    if overtime_used(league, team):
        print(paint("   You already pushed the staff this week.", C.BYELLOW))
        pause()
        return
    uses = cyc.__dict__.setdefault("ot_uses", {}).get(team.school, 0)
    risk = min(0.6, OT_BASE + OT_STEP * uses)
    print(paint(f"\n   Ten more hours this week: extra calls, a few texts after the dead period ends...\n"
                f"   This season you've done it {uses} time{'s' if uses != 1 else ''}. "
                f"Chance someone notices this time: about {round(risk * 100)}%.", C.BYELLOW))
    if ask("Do it? (y/n)").strip().lower() not in ("y", "yes"):
        return
    cyc.overtime[(team.school, league.week)] = OT_HOURS
    cyc.ot_uses[team.school] = uses + 1
    rng = random.Random(f"ot:{team.school}:{league.year}:{league.week}")
    if rng.random() < risk:
        level = 2 if uses >= 4 else 3
        _case(league, team, "recruiting", level, "impermissible recruiting contact beyond the allowed hours", True)
        _log(league, f"Week {league.week}: caught going over the recruiting hours limit.")
        print(paint("   You get your ten hours — and a compliance officer at a rival school gets a tip.\n"
                    "   A recruiting-violation case is open.", C.BRED, C.BOLD))
    else:
        if rng.random() < 0.3:
            trace = cyc.__dict__.setdefault("ot_trace", {})
            cid = trace.get((team.school, league.year))
            import compliance as co
            c = co.case_by_id(league, cid) if cid else None
            if c is None or c.get("closed"):
                c = _case(league, team, "recruiting", 3, "recruiting contact beyond the allowed hours", False, 30)
                if c:
                    trace[(team.school, league.year)] = c["id"]
            else:
                c["evidence"] = min(99, c["evidence"] + 12)
                if c["evidence"] >= 80 and c["level"] > 2:
                    c["level"] = 2
        _log(league, f"Week {league.week}: ten extra recruiting hours, off the books.")
        print(paint(f"   Ten more hours on the board this week. Nobody said anything... yet.", C.BGREEN))
    pause()


# ═══ Tampering ══════════════════════════════════════════════════════════════

def _targets(league, team):
    import portal
    import morale
    needs = portal.team_needs(team)
    out = []
    for t in league.teams:
        if t is team:
            continue
        for p in t.roster:
            short, quality, _ = needs.get(p.position, (0, 99, 0))
            if p.overall < quality - 2 and short <= 0:
                continue
            rank = portal.depth_chart_rank(t, p)
            unhappy = morale.get(p) < 50 or rank > portal.STARTER_DEPTH.get(p.position, 2)
            if p.year >= 3 and not getattr(league, "nil_rolled", False) and league.week >= 1:
                continue                                   # a senior isn't transferring anywhere
            out.append((p.overall + (6 if unhappy else 0), p, t, rank, unhappy))
    out.sort(key=lambda x: -x[0])
    return out[:14]


def tamper(league, team):
    if _blocked(league):
        return
    while True:
        rows = _targets(league, team)
        clear()
        print(title_bar("THE BACK CHANNEL  ·  PLAYERS ON OTHER ROSTERS"))
        print(paint("   Players at your positions of need who'd be an upgrade — and whether they look restless.\n"
                    "   Reaching out before he's in the portal is tampering. People do it. People get caught.\n", C.GRAY))
        import morale
        for i, (_, p, t, rank, unhappy) in enumerate(rows, 1):
            done = paint("  contacted", C.GRAY) if (p.__dict__.get("tampered") or {}).get("year") == league.year else ""
            mood = paint("restless", C.BYELLOW) if unhappy else paint("settled", C.GRAY)
            print(f"   {paint(f'[{i:>2}]', C.BYELLOW)} {pad(truncate(p.name, 21), 22)}{p.position:<4}"
                  f"{__import__('scout').ovr_short(p.overall)}  {p.class_label:<7}{pad(truncate(t.school, 17), 18)}"
                  f"{'starter' if rank <= __import__('portal').STARTER_DEPTH.get(p.position, 2) else 'backup':<9}{mood}{done}")
        ch = ask("Player # (Enter = back):").strip()
        if not ch:
            return
        if not ch.isdigit() or not 1 <= int(ch) <= len(rows):
            continue
        _, p, t, rank, unhappy = rows[int(ch) - 1]
        if (p.__dict__.get("tampered") or {}).get("year") == league.year:
            print(paint(f"   You've already reached out to {p.name} this season.", C.BYELLOW))
            pause()
            continue
        print()
        for i, (k, label, s, risk, lvl) in enumerate(APPROACHES, 1):
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(label, 44)}"
                  f"{paint(f'push: ' + ('small' if s < 0.15 else 'real' if s < 0.25 else 'big'), C.BGREEN)}   "
                  f"{paint(f'risk: about {round(risk * 100)}%', C.BRED)}")
        sel = ask("How (Enter = forget it):").strip()
        if not (sel.isdigit() and 1 <= int(sel) <= len(APPROACHES)):
            continue
        k, label, s, risk, lvl = APPROACHES[int(sel) - 1]
        if unhappy:
            s *= 1.4
        p.tampered = {"school": team.school, "s": round(s, 3), "year": league.year, "risk": risk, "level": lvl,
                      "fresh": True}
        rng = random.Random(f"tamper:{p.name}:{league.year}:{k}")
        if rng.random() < risk:
            _case(league, team, "tampering", lvl, f"contact with {t.school}'s {p.position} {p.name} before he "
                                                  f"entered the transfer portal", True, 70)
            p.tampered["s"] *= 0.5
            _log(league, f"Caught tampering with {t.school}'s {p.name}.")
            print(paint(f"\n   {t.school}'s compliance office files a complaint. The CAB opens a tampering case.\n"
                        f"   {p.name} heard from you, at least.", C.BRED, C.BOLD))
        else:
            _log(league, f"Back-channel contact with {t.school}'s {p.name}.")
            print(paint(f"\n   Word gets to {p.name}. He knows {team.school} wants him.", C.BGREEN, C.BOLD))
        pause()


def after_portal(league, report):
    """A tampered-with player who actually lands at the school that tampered: another roll."""
    for entry, dest in getattr(report, "moves", []):
        t = entry.player.__dict__.get("tampered")
        if not t:
            continue
        t["fresh"] = False
        if dest.school != t.get("school"):
            continue
        rng = random.Random(f"tamperland:{entry.player.name}:{report.year}")
        if rng.random() < t.get("risk", 0.1) * 1.5:
            _case(league, dest, "tampering", t.get("level", 3),
                  f"recruiting {entry.player.name} away from {entry.origin.school} before he entered the portal",
                  rng.random() < 0.5, 55)
    for e in getattr(report, "entries", []):
        t = e.player.__dict__.get("tampered")
        if t:
            t["fresh"] = False
