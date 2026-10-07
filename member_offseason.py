"""
member_offseason.py — Commissioner Mode, Phase 6: a member's staff, money and season-end decisions,
made from his orders instead of the AI's.

STAFF ("staff" section, standing orders)
  fire   coordinators or position coaches to let go (offseason only): the chair opens for the carousel
  lists  for each chair (OC, DC, QB, RB, WR, TE, OL, DL, LB, DB) a ranked list of up to 10 names, used
         if that chair opens this winter (he left, retired, was let go), with his best package:
           coordinators  max salary, years, play-calling, the assistant-head-coach title, a head-job out-clause
           position      the most he'll pay over standard: 0%, 15% or 30%
  When the member's chair comes up in the staff carousel, his list is worked top to bottom with Coach
  Career's own rules: each candidate's interest and terms (coord_search.profile), the package judged by
  coord_search.evaluate (counter-offers he can live with are accepted inside the max), his school's
  retention bid (topped only if the max allows), and the AD's funding check. Nobody on the list says yes
  → the AD hires, exactly as when a Coach Career coach hands his search over.

MONEY ("money" section, one cycle's asks)
  facility  build up recruiting or training facilities (one project a season)
  restructure / coordcut / poscut / stretch   the Find the Money asks: a player takes 25% less NIL, a
            coordinator 15% less, a position coach 10% less, a buyout spread over three years. Each answer
            uses the same odds and the same once-a-year rule as Coach Career.

SEASON END ("nil" section, after the title game)
  nil    each NIL raise demand: pay, counter or refuse (unanswered: the staff decides, as for any program)
  draft  each draft-eligible player: urge him to stay, tell him to go, or leave it to him
"""
import random

SEARCH = 10


def _member(league, team):
    import commissioner as cm
    return cm.active(league) and cm.is_player_team(league, team)


def _standing(league, team):
    import commissioner as cm
    return cm.team_row(league, team).setdefault("orders", {})


def report(league, team, line):
    """What happened with his staff and money, for the website and the inbox."""
    import commissioner as cm
    row = cm.team_row(league, team)
    book = row.setdefault("staff_report", [])
    book.append([league.year, line])
    del book[:-30]


# ═══ Staff: the member's search, run headless ═══════════════════════════════

def fill_coord(car, team, role):
    """The staff carousel reached a member's coordinator chair. Returns True when it's filled."""
    import coord_search as cs
    import finance as fi
    lg = car.league
    plan = (_standing(lg, team).get("staff") or {}).get("lists", {}).get(role) or {}
    names = list(plan.get("names") or [])[:SEARCH]
    mx = dict({"salary": 0, "years": 3, "calls": 0, "title": 0, "out": 0}, **(plan.get("max") or {}))
    if not names:
        return False
    opts = {c.name: (c, tie) for c, tie in car.coord_cands(team, role)}
    for name in names:
        got = opts.get(name)
        if got is None:
            report(lg, team, f"{role}: {name} wasn't on the market for this job")
            continue
        c, tie = got
        if getattr(c, "moved_year", None) == lg.year:
            report(lg, team, f"{role}: {name} already took another job")
            continue
        prof = cs.profile(lg, team, role, c, tie)
        if prof["interest"] < 8 and not tie and prof["kind"] != "own":
            report(lg, team, f"{role}: {name}'s agent wouldn't return the call")
            continue
        cap_sal = int(mx["salary"] or 0) or int(fi.COORD_SHARE * fi.budget(team) * 1.2)
        base = {"salary": int(min(cap_sal, max(prof["floor"], prof["opening"]))), "years": max(1, int(mx["years"] or 3)),
                "calls": bool(mx["calls"]), "title": bool(mx["title"]), "out": bool(mx["out"])}
        o = None
        score, problems = cs.evaluate(prof, 0, base)
        if score >= cs.ACCEPT_AT and not ("calls" in problems and prof["calls"] == "must") \
                and base["salary"] >= prof["floor"] * 0.97:
            o = base
        else:
            want = cs._counter(prof, base)
            fits = (want["salary"] <= cap_sal and want["years"] <= max(base["years"], 6)
                    and (not want["calls"] or mx["calls"]) and (not want["out"] or mx["out"]))
            if fits and cs.evaluate(prof, 0, want)[0] >= cs.ACCEPT_AT:
                o = want
        if o is None:
            why = ("the money" if "money" in problems else "play-calling" if "calls" in problems
                   else "the fit" if prof["interest"] < 45 else "the package")
            report(lg, team, f"{role}: {name} said no ({why})")
            continue
        if prof["match"] > 0 and prof["match_roll"] < prof["match"]:
            theirs = fi._round(o["salary"] * 1.12, 5_000)
            need = fi._round(theirs * 1.03, 5_000)
            cap = fi.COORD_CAP * fi.budget(team) * 1.25
            loyal = getattr(c, "personality", "") == "loyalist"
            if need > cap_sal or need > cap or (loyal and cs._rng(lg, team, role, c, "retain").random() < 0.5):
                report(lg, team, f"{role}: {name} said yes, then took {prof['current']}'s counteroffer")
                continue
            o = dict(o, salary=int(need))
            report(lg, team, f"{role}: {prof['current']} tried to keep {name}; you topped it at {fi.money(need)}")
        est = fi.COORD_SHARE * fi.budget(team)
        if o["salary"] - est > max(0, fi.available(lg, team)):
            report(lg, team, f"{role}: the AD couldn't fund {name} at {fi.money(o['salary'])}")
            continue
        offer = cs._to_contract(team, role, o)
        car.hire_coord(team, role, c, offer)
        report(lg, team, f"{role}: hired {name} — {fi.terms(offer)}")
        return True
    report(lg, team, f"{role}: nobody on your list said yes; the AD made the hire")
    return False


def _pos_pool(lg, team, group):
    """Every position coach a member can name for a chair (real people only: out of work, or coaching
    the same room at a smaller program)."""
    import poscoach
    out = [poscoach.fields(c) for c in lg.__dict__.get("pos_pool", []) if c.group == group]
    for t in lg.teams:
        if t is team or t.prestige >= team.prestige - 3:
            continue
        c = poscoach.staff_of(t).get(group)
        if c is not None:
            out.append(c)
    return out


def fill_pos(car, team, group):
    """The staff carousel reached a member's position-coach chair. Returns True when it's filled."""
    import finance as fi
    import hiring_market as hm
    import poscoach
    lg = car.league
    plan = (_standing(lg, team).get("staff") or {}).get("lists", {}).get(group) or {}
    names = list(plan.get("names") or [])[:SEARCH]
    mult = {0: 1.0, 15: 1.15, 30: 1.30}.get(int(plan.get("premium", 0) or 0), 1.0)
    if not names:
        return False
    pool = {c.name: c for c in _pos_pool(lg, team, group)}
    for name in names:
        c = pool.get(name)
        if c is None:
            report(lg, team, f"{group} coach: {name} wasn't available")
            continue
        src = next((t for t in lg.teams if t.school == c.school), None)
        if src is not None and src.prestige > team.prestige - 2 and c.kind != "Loyalist":
            report(lg, team, f"{group} coach: {name} would rather stay at {src.school}")
            continue
        final = hm.pos_interest(lg, team, c, mult)
        if final < 14 or not hm._roll(f"pos-offer:{lg.seed}:{lg.year}:{team.school}:{c.name}:{mult}", final):
            report(lg, team, f"{group} coach: {name} turned you down")
            continue
        if src is not None and random.Random(f"pos-retain:{lg.seed}:{lg.year}:{team.school}:{c.name}:{mult}").random() < 0.14:
            report(lg, team, f"{group} coach: {src.school} kept {name}")
            continue
        extra = poscoach.salary(c, team) * mult - poscoach.POS_SHARE * fi.budget(team)
        if extra > max(0, fi.available(lg, team)):
            report(lg, team, f"{group} coach: the AD couldn't fund {name}")
            continue
        was = c.group
        poscoach.hire(lg, team, group, c, refill=False)
        if mult > 1.0:
            c.bonus = int(poscoach.salary(c, team) * (mult - 1.0))
        report(lg, team, f"{group} coach: hired {name}" + (f" from {src.school}" if src else "")
               + (f" at a {round((mult - 1) * 100)}% premium" if mult > 1 else ""))
        if src is not None:
            car.open(src, "pos", was, f"{c.name} left for {team.school}")
        return True
    report(lg, team, f"{group} coach: nobody on your list said yes; the AD made the hire")
    return False


def run_fires(league):
    """Inside the offseason, right before the staff carousel opens: every member's let-go orders."""
    import commissioner as cm
    for team in cm.player_teams(league):
        st = _standing(league, team).get("staff") or {}
        for k in st.pop("fire", []) or []:
            report(league, team, fire_now(league, team, k))


def fire_now(league, team, what):
    """A member lets a coach go (offseason). Returns a result line."""
    import poscoach
    import staff
    if what in ("OC", "DC"):
        c = getattr(team, "oc" if what == "OC" else "dc", None)
        if c is None:
            return f"{what}: the chair is already empty"
        staff.fire(league, team, what, "fired")
        return f"{what}: let {c.name} go"
    c = poscoach.staff_of(team).get(what)
    if c is None:
        return f"{what} coach: the chair is already empty"
    poscoach.fire(league, team, what)
    return f"{what} coach: let {c.name} go"


# ═══ Money: the Find the Money asks, answered the way Coach Career answers them ═

def money(league, team, sec):
    import budget_fix as bf
    import facilities
    import finance as fi
    import morale
    import orders
    import poscoach
    lines = []
    kind = sec.get("facility")
    if kind in ("recruiting", "training"):
        ok, _cost, why = facilities.can_upgrade(league, team, kind)
        if ok:
            ok2, msg = facilities.upgrade(league, team, kind, "you")
            lines.append(msg if ok2 else f"facilities: {msg}")
        else:
            lines.append(f"facilities: {why}")
    roster = orders.roster_map(league, team)
    starters = {id(p) for g in team.starters().values() for p in g}
    for pid in sec.get("restructure", [])[:6]:
        p = roster.get(pid)
        if p is None or not getattr(p, "nil", 0):
            continue
        if bf._asked(p, "nil", league):
            lines.append(f"{p.name}: already asked this year")
            continue
        bf._mark(p, "nil", league)
        odds = 0.45 + (morale.get(p) - 55) / 120 + (0.15 if id(p) not in starters else -0.05) \
            - 0.15 * (fi.player_appetite(p) - 1)
        if bf._roll(f"restructure:{p.name}:{league.year}") < max(0.08, min(0.85, odds)):
            cut = fi._round(p.nil * 0.25, 1_000)
            p.nil -= cut
            morale.nudge(p, -5, "took less NIL to help the budget", league)
            lines.append(f"{p.name} took 25% less NIL ({fi.money(p.nil)}/yr now)")
        else:
            morale.nudge(p, -12, "was asked to take less NIL", league)
            lines.append(f"{p.name} said no to less NIL, and he won't forget you asked")
    for role in sec.get("coordcut", [])[:2]:
        c = getattr(team, "oc" if role == "OC" else "dc", None) if role in ("OC", "DC") else None
        if c is None or not fi.contract(c) or bf._asked(c, "cut", league):
            continue
        bf._mark(c, "cut", league)
        odds = {"homebody": 0.6, "builder": 0.5, "climber": 0.2}.get(getattr(c, "personality", ""), 0.4)
        if bf._roll(f"coordcut:{c.name}:{league.year}") < odds:
            fi.contract(c)["salary"] = int(fi.salary(c) * 0.85)
            lines.append(f"{role} {c.name} took a 15% pay cut")
        else:
            c.stay_lean = (league.year, 1)
            lines.append(f"{role} {c.name} said no to a pay cut; he'll listen when other schools call")
    for g in sec.get("poscut", [])[:8]:
        c = poscoach.staff_of(team).get(g)
        if c is None or bf._asked(c, "cut", league):
            continue
        bf._mark(c, "cut", league)
        odds = {"Loyalist": 0.7, "Players' coach": 0.55, "Climber": 0.2}.get(c.kind, 0.45)
        if bf._roll(f"poscut:{c.name}:{league.year}") < odds:
            c.bonus = int(getattr(c, "bonus", 0) - poscoach.salary(c, team) * 0.10)
            lines.append(f"{g} coach {c.name} took a 10% pay cut")
        else:
            c.unhappy = (league.year, "a pay cut request")
            lines.append(f"{g} coach {c.name} said no to a pay cut, and he's unsettled now")
    if sec.get("stretch"):
        y = bf._y(league)
        for b in [b for b in getattr(team, "buyouts", []) if b["start"] <= y <= b["end"] and b.get("per_year", 0) > 0
                  and b.get("kind") not in ("release", "deferred") and not b.get("stretched")]:
            b["stretched"] = True
            if bf._roll(f"stretch:{b['name']}:{league.year}:{b['per_year']}") < 0.75:
                each = int(b["per_year"] * 1.1 / 3)
                b["per_year"] = each
                for k in (1, 2):
                    team.buyouts.append({"name": b["name"], "role": b.get("role", ""), "per_year": each,
                                         "start": y + k, "end": y + k, "coach": b.get("coach"), "stretched": True})
                lines.append(f"{b['name']}'s buyout is spread over three years ({fi.money(each)}/yr)")
            else:
                lines.append(f"{b['name']}'s agent said no to stretching the buyout")
    for ln in lines:
        report(league, team, ln)
    return lines


def money_view(league, team):
    """What the website's Money tab needs: facilities, deals, staff pay, buyouts, the free money."""
    import budget_fix as bf
    import facilities
    import finance as fi
    import orders
    import poscoach
    out = {"budget": fi.budget(team), "free": fi.available(league, team), "facilities": {}}
    for kind in ("recruiting", "training"):
        ok, cost, why = facilities.can_upgrade(league, team, kind)
        out["facilities"][kind] = {"level": facilities.ensure(team)[kind], "ok": bool(ok), "cost": cost or 0, "why": why or ""}
    out["deals"] = [[orders.pid(league, p), p.nil, bool(bf._asked(p, "nil", league))]
                    for p in sorted(team.roster, key=lambda p: -(getattr(p, "nil", 0) or 0))
                    if (getattr(p, "nil", 0) or 0) > 0 and bf._counts(league, p)][:20]
    out["coords"] = []
    for role in ("OC", "DC"):
        c = getattr(team, "oc" if role == "OC" else "dc", None)
        if c is not None and fi.contract(c):
            out["coords"].append([role, c.name, fi.salary(c), bool(bf._asked(c, "cut", league))])
    out["pos"] = [[g, c.name, poscoach.salary(c, team), bool(bf._asked(c, "cut", league))]
                  for g, c in poscoach.staff_of(team).items() if c is not None]
    y = bf._y(league)
    out["buyouts"] = [[b["name"], b.get("per_year", 0), bool(b.get("stretched"))] for b in getattr(team, "buyouts", [])
                      if b["start"] <= y <= b["end"] and b.get("per_year", 0) > 0 and b.get("kind") not in ("release", "deferred")]
    return out


# ═══ Staff: what the website shows ══════════════════════════════════════════

def staff_view(league, team):
    """The member's staff, and for every chair the names he could put on a list, with what his staff
    knows before anyone has called: public buzz, résumé, age, the coach's ratings the game shows."""
    import carousel as cz
    import coord_search as cs
    import finance as fi
    import hiring_market as hm
    import poscoach
    import staff
    rng = random.Random(f"staffview:{league.seed}:{league.year}:{team.school}")
    now = []
    for role in ("OC", "DC"):
        c = getattr(team, "oc" if role == "OC" else "dc", None)
        now.append({"key": role, "name": c.name if c else None, "age": getattr(c, "age", None),
                    "cov": getattr(c, "overall", None), "pay": fi.salary(c) if c is not None and fi.contract(c) else 0,
                    "pot": staff.potential_word(c) if c else "", "calls": bool(c and staff.calls(team).get("off" if role == "OC" else "def") == role)})
    for g, c in poscoach.staff_of(team).items():
        now.append({"key": g, "name": c.name if c else None, "age": getattr(c, "age", None), "cov": getattr(c, "overall", None),
                    "pay": poscoach.salary(c, team) if c else 0, "kind": getattr(c, "kind", ""),
                    "dev": getattr(c, "dev", None), "rec": getattr(c, "rec", None), "spec": poscoach.spec_line(c) if c else ""})
    markets = {}
    for role in ("OC", "DC"):
        seen, rows = set(), []
        cands = staff.candidates_for(league, team, role, rng) + [(poscoach.as_coordinator(league, pc, role), False)
                                                                 for pc, _t in poscoach.coord_candidates(league, team, role)]
        cands = [(c, tie) for c, tie in cands if not c.__dict__.get("_generated")]
        cands.sort(key=lambda x: -staff._score(team, x[0], role, league))
        for c, tie in cands:
            if c.name in seen or len(rows) >= 30:
                continue
            seen.add(c.name)
            prof = cs.profile(league, team, role, c, tie)
            if prof["interest"] < 8 and not tie and prof["kind"] != "own":
                continue
            rows.append({"name": c.name, "age": c.age, "cov": c.overall, "side": cs._side(c, role),
                         "rec": c.ratings.get("recruiting"), "pot": staff.potential_word(c),
                         "now": cs._now(c, prof["kind"]), "buzz": cs._read(prof["interest"] + prof["fuzz"], cs.FUZZY),
                         "tie": bool(tie), "calls": bool(cs._calls_now(c)), "unit": cs._last_unit(c),
                         "pers": cz.PERSONALITIES.get(getattr(c, "personality", ""), ("",))[0]})
        markets[role] = rows
    for g in poscoach.GROUPS:
        rows = []
        for c in sorted(_pos_pool(league, team, g), key=lambda c: -c.overall)[:15]:
            rows.append({"name": c.name, "age": c.age, "cov": c.overall, "dev": c.dev, "rec": c.rec, "eye": c.eye,
                         "kind": c.kind, "now": f"{c.school} {poscoach.TITLE[g]} coach" if c.school else "out of work",
                         "buzz": hm.word(hm.pos_interest(league, team, c)), "spec": poscoach.spec_line(c),
                         "ask": poscoach.salary(c, team)})
        markets[g] = rows
    st = _standing(league, team).get("staff") or {}
    return {"now": now, "markets": markets, "lists": st.get("lists", {}), "std": {"coord": int(fi.COORD_SHARE * fi.budget(team)),
            "pos": int(poscoach.POS_SHARE * fi.budget(team))}, "report": [ln for y, ln in
            __import__("commissioner").team_row(league, team).get("staff_report", []) if y >= league.year - 1][-15:]}


# ═══ Season end: NIL raises and the draft ═══════════════════════════════════

def nil_view(league, team):
    """Open NIL raise demands and draft-eligible players, with what the staff would do."""
    import orders
    import personalities as pz
    out = {"room": pz._raise_room(league, team), "nil": [], "draft": []}
    for p in team.roster:
        d = getattr(p, "nil_demand", None)
        if d and d.get("year") == league.year and d.get("status") == "open":
            cost = d["ask"] - d["was"]
            out["nil"].append({"id": orders.pid(league, p), "ask": d["ask"], "was": d["was"], "threat": bool(d["threat"]),
                               "staff": "pay" if cost <= out["room"] * 0.5 else "refuse", "counter": (d["ask"] + d["was"]) // 2})
    if league.season_complete:
        board = pz.projected_spots(league)
        for p in team.roster:
            spot = board.get(id(p))
            if (p.year == 2 or (p.year == 1 and p.redshirt)) and spot is not None and spot <= 160:
                out["draft"].append({"id": orders.pid(league, p), "round": min(7, 1 + (spot - 1) // 32),
                                     "pitch": getattr(p, "draft_pitch", None) or ""})
    return out


def answer_nil(league, team, sec):
    import orders
    import personalities as pz
    roster = orders.roster_map(league, team)
    lines = []
    for pid, choice in sec.get("nil", []):
        p = roster.get(pid)
        if p is None:
            continue
        msg = pz._answer_nil(league, team, {"ref": p}, {"pay": "nil_pay", "counter": "nil_counter", "refuse": "nil_refuse"}[choice])
        lines.append(f"{p.name}: {msg}")
    for pid, choice in sec.get("draft", []):
        p = roster.get(pid)
        if p is None:
            continue
        msg = pz._answer_draft(league, team, {"ref": p}, {"stay": "draft_stay", "go": "draft_go", "neutral": "draft_neutral"}[choice])
        lines.append(f"{p.name}: {msg}")
    for ln in lines:
        report(league, team, ln)
    return lines
