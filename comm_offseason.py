"""
comm_offseason.py — Commissioner Mode, Phase 7: the offseason a cycle at a time.

Coach Career stages the offseason over 17 weeks; a Commissioner league runs the same steps, in the
same order (season.OFFSEASON_STAGES), as nine cycles with members' orders in between:

  1  Coaching carousel        firings, the members' job market, contracts, staffs (their lists)
  2  Awards and winter        records, awards, the draft, graduation, development, NIL raises settled
  3  Portal Window I opens    every program learns who's leaving
  4  Portal market            members' retention talks and transfer offers; the window closes
  5  Signing push             one last full recruiting week (members' standing orders and visits)
  6  National Signing Day     classes sign; freshmen, late transfers and walk-ons arrive
  7  Roster week              members' position changes and cuts, then rosters trimmed to size;
                              realignment; the new year begins
  8  Spring ball and A-Day    two practice blocks on each member's emphasis, then the spring game
  9  Portal Window II         the post-spring window; then summer, and fall camp is the next cycle

Every stage is the game's own code: run end to end it equals the one-call offseason exactly.
"""
import random

STAGES = (
    ("carousel", "Coaching carousel and staffs"),
    ("awards", "Awards, the draft and winter workouts"),
    ("portal_open", "Transfer portal opens"),
    ("portal_close", "Portal market and deadline"),
    ("signing_push", "Signing push"),
    ("signing", "National Signing Day"),
    ("roster", "Roster week"),
    ("spring", "Spring ball and A-Day"),
    ("portal2", "Portal Window II and summer"),
)
SECTIONS = {                                     # what members can send before each stage runs
    "carousel": ["jobs", "staff", "money", "nil"],
    "awards": ["staff", "money", "nil"],
    "portal_open": ["money"],
    "portal_close": ["portal", "money"],
    "signing_push": ["rec", "money"],
    "signing": ["rec"],
    "roster": ["roster", "money"],
    "spring": ["spring", "depth"],
    "portal2": ["depth"],
}
EMPHASES = ("fundamentals", "competition", "young", "physical", "chemistry", "passing")


def _st(league):
    import commissioner as cm
    return cm.state(league)


def in_offseason(league):
    return "off" in _st(league) or league.season_complete


def stage_key(league):
    """The stage the next cycle will run, or None in season."""
    off = _st(league).get("off")
    if off is not None:
        return STAGES[off["i"]][0]
    if league.season_complete:
        return STAGES[0][0]
    return None


def label(league):
    k = stage_key(league)
    if k is None:
        return None
    return f"{league.year} offseason: {dict(STAGES)[k]}"


def sections(league):
    k = stage_key(league)
    return list(SECTIONS.get(k, [])) if k else None


def run_stage(league):
    """Run the next offseason stage. Returns a summary line."""
    import season
    st = _st(league)
    if "off" not in st:
        st["off"] = {"i": 0, "ctx": season.offseason_begin(league)}
    off = st["off"]
    key = STAGES[off["i"]][0]
    ctx = off["ctx"]
    rng = league.rng
    summary = globals()["_" + key](league, rng, ctx)
    off["i"] += 1
    if off["i"] >= len(STAGES):
        del st["off"]
    return summary


# ═══ The stages ═════════════════════════════════════════════════════════════

def _carousel(league, rng, ctx):
    import season
    season.off_carousel(league, rng, ctx)
    moves = [m for m in league.carousel.get(league.year, [])] if hasattr(league, "carousel") else []
    return f"Coaching carousel: {sum(1 for k, _ in moves if k == 'hired')} head coaches hired; staffs rebuilt."


def _awards(league, rng, ctx):
    import season
    season.off_awards(league, rng, ctx)
    season.off_winter(league, rng, ctx)
    r = ctx["report"]
    return f"Awards and the draft are in; {len(r.graduated)} seniors graduated and {r.redshirted} redshirted."


def _portal_open(league, rng, ctx):
    """Every program learns who's leaving. Members get a seat at the table for the market cycle."""
    import portal
    import season
    season._YEAR[0] = ctx["next_year"]
    rep = portal.PortalReport(ctx["next_year"])
    portal.open_portal(league, rng, rep)
    rep.users = []                     # a member who sends portal orders works his own board; the rest, their staffs do
    ctx["report"].portal = rep
    return f"Portal Window I: {len(rep.entries)} players entered."


def _portal_close(league, rng, ctx):
    import gray_area
    import portal
    import season
    season._YEAR[0] = ctx["next_year"]
    rep = ctx["report"].portal
    portal.resolve_portal(league, rng, rep)
    try:
        gray_area.after_portal(league, rep)
    except Exception:                                       # noqa: BLE001, S110 — as the career calendar does
        pass
    league.last_portal = rep
    return f"Portal Window I closes: {len(rep.moves)} transfers landed, {len(rep.unsigned)} unsigned."


def _signing_push(league, rng, ctx):
    import season
    season._YEAR[0] = ctx["next_year"]
    league.recruiting.weekly_tick(14, user_team=None)        # members' queues, autopilot and visits run here
    return "The signing push: one last recruiting week."


def _signing(league, rng, ctx):
    import season
    season.off_signing(league, rng, ctx)
    season.off_arrivals(league, rng, ctx)
    sig = ctx["signing"]
    n = sum(len(v) for v in getattr(sig, "classes", {}).values())
    return f"National Signing Day: {n} signees; the new classes are on campus."


def _roster(league, rng, ctx):
    import season
    season.off_rollover(league, rng, ctx)
    league.after_offseason(ctx["report"])
    return f"Roster week: {len(ctx['report'].cut)} cut to size. The {league.year} season begins."


def _spring(league, rng, ctx):
    import commissioner as cm
    for t in cm.player_teams(league):
        plan = (cm.team_row(league, t).get("orders") or {}).get("spring") or {}
        spring_for(league, t, plan.get("emphasis") or "fundamentals", plan.get("focus") or [])
    return "Spring ball and A-Day are done."


def _portal2(league, rng, ctx):
    rep = spring_portal(league, rng)
    return f"Portal Window II: {len(rep.entries)} entered, {len(rep.moves)} moved. Summer: fall camp is next."


# ═══ Spring, headless, one member at a time ═════════════════════════════════

def spring_for(league, team, emphasis, focus):
    """Spring Ball I and II on the member's emphasis, then A-Day. Uses spring_cycle's own pieces; the
    spring notes live on the team (Coach Career keeps one team's, so each member's is swapped in)."""
    import offseason_cal
    import spring_cycle as sc
    st = offseason_cal._state(league)
    keep = st.get("spring")
    st["spring"] = sp = {"year": league.year, "emphasis": emphasis if emphasis in EMPHASES else "fundamentals",
                         "focus_positions": list(focus)[:3], "weeks": {}, "standouts": [], "stock_up": [],
                         "stock_down": [], "injuries": [], "aday": {}}
    team.spring_focus = {"year": league.year, "pos": set(focus), "emphasis": sp["emphasis"]}
    try:
        for block in (1, 2):
            tiers = sc._tier_map(team)
            results = []
            rng = random.Random(f"spring-dev:{league.seed}:{league.year}:{team.school}:{block}")
            for p in list(team.roster):
                if getattr(p, "inj_games", 0) > 0:
                    avg, gain, inj = 0.0, 0, None
                    lines, forms = ["Limited by injury."], [0.0]
                else:
                    lines, forms, avg = sc._practice_player(league, team, p, block, tiers.get(id(p), 2), sp["emphasis"])
                    gain = sc._develop(league, team, p, block, sp["emphasis"], rng)
                    inj = sc._injury_roll(league, team, p, block, sp["emphasis"], rng)
                if sp["emphasis"] == "chemistry":
                    import morale
                    morale.nudge(p, 2, "spring leadership work", league)
                hist = p.__dict__.setdefault("spring_form", {})
                hist[league.year] = max(-2.5, min(2.5, float(hist.get(league.year, 0.0)) + avg * 0.60))
                sess = p.__dict__.setdefault("spring_sessions", {}).setdefault(league.year, {})
                sess[block] = [(lines[i] if i < len(lines) else "", forms[i] if i < len(forms) else 0.0) for i in range(len(forms))]
                results.append({"name": p.name, "pos": p.position, "avg": round(avg, 2), "gain": gain, "injury": inj})
                if inj:
                    sp["injuries"].append(f"{p.position} {p.name}: {inj}")
            sp["weeks"][str(block)] = results
            sc._refresh_stock(league, team)
        _a_day(league, team, sp)
        import depth
        depth.staff_sort_yours(league, team)
        import orders
        orders.apply_depth(league, team)                  # his own depth chart still stands
    finally:
        team.__dict__["spring_report"] = {k: sp.get(k) for k in ("year", "emphasis", "focus_positions", "standouts",
                                                                  "stock_up", "stock_down", "injuries", "aday")}
        st["spring"] = keep if keep is not None else {}


def _a_day(league, team, sp):
    import offseason_cal
    import spring_cycle as sc
    from game_sim import GameSim
    from season import Game
    blue, white = offseason_cal._split(team)
    g = Game(0, blue, white, False, game_type="Spring Game", bowl_name=f"{team.school} A-Day", venue=team.stadium,
             neutral=False)
    try:
        sim = GameSim(g, random.Random(f"aday:{team.school}:{league.year}"), None, persist_injuries=False)
        sim.play()
    except Exception:                                       # noqa: BLE001 — an exhibition never breaks the offseason
        sp["aday"]["score"] = "called off for weather"
        return
    sc.apply_aday_film(league, team, sim)
    sp["aday"]["score"] = f"Blue {g.home_score}, White {g.away_score}"


# ═══ Portal Window II, headless (offseason_cycle.run_spring_portal without the screens) ═

def spring_portal(league, rng):
    import gray_area
    import offseason_cycle as oc
    import portal
    rep = portal.PortalReport(league.year)
    rep.__dict__["weekly"] = True
    rep.__dict__["window_name"] = "Post-Spring Window"
    oc._open_spring(league, rng, rep)
    trng = oc._seed(league, "portal2", league.year)
    rep.__dict__["decision_week"] = {e: oc._decision_week(e, trng, 14, 15) for e in rep.entries}
    rep.__dict__["commit_log"] = []
    batch = [e for e in rep.entries if rep.decision_week[e] <= 14]
    oc._resolve_batch(league, rng, rep, batch, room_left=max(0, int(len(batch) * .88)), rounds=2)
    remaining = [e for e in rep.entries if e.destination is None]
    target = int(len(rep.entries) * portal.LAND_RATE)
    oc._resolve_batch(league, rng, rep, remaining, room_left=max(0, target - len(rep.moves)), rounds=3)
    rep.unsigned = [e for e in rep.entries if e.destination is None]
    for t in league.teams:
        portal.fill_gaps(t, rep, rng)
    league.__dict__["last_portal2"] = rep
    try:
        gray_area.after_portal(league, rep)
    except Exception:                                       # noqa: BLE001, S110
        pass
    return rep


# ═══ Members' orders for these stages ══════════════════════════════════════

def portal_orders(league, team, sec):
    """Retention talks for his own players who entered, and offers (with NIL) to anyone in the portal."""
    import finance as fi
    import morale
    import orders
    import staff
    off = _st(league).get("off")
    rep = off["ctx"]["report"].portal if off and off["ctx"]["report"].portal is not None else None
    if rep is None:
        return ["portal: the window isn't open"]
    user = next((u for u in getattr(rep, "users", []) if u["team"] is team), None)
    if user is None:
        user = {"team": team, "offers": set(), "interest": {}, "known": {}, "visited": set(), "hours": 0,
                "kept": [], "lost_keep": [], "portal_week": 4}
        rep.users.append(user)
    by_pid = {orders.pid(league, e.player): e for e in rep.entries}
    lines = []
    for pid, raise_ in sec.get("keep", [])[:6]:
        e = by_pid.get(pid)
        if e is None or e.origin is not team or e.destination is not None or e.player in user["kept"]:
            continue
        p = e.player
        odds = 0.35 + 0.2 * (e.depth <= 1) + staff.recruiting_rating(team) / 400
        if "playing" in e.reason or "depth" in e.reason:
            odds -= 0.15
        amt = int(max(0, raise_ or 0))
        free = fi.portal_room(league, team, rep)
        amt = min(amt, max(0, free))
        if amt:
            odds += 0.3 * min(1, amt / max(1, fi.transfer_market(p))) * fi.player_appetite(p)
        r = random.Random(f"keep:{league.seed}:{league.year}:{team.school}:{p.name}")
        if r.random() < min(0.92, odds):
            rep.entries.remove(e)
            rep.by_team_out[team].remove(e)
            team.add_player(p)
            p.nil = getattr(p, "nil_before_portal", 0) + amt
            user["kept"].append(p)
            morale.nudge(p, 4, "his coach fought to keep him", league)
            lines.append(f"{p.name} stays" + (f" (+{fi.money(amt)}/yr)" if amt else ""))
        else:
            user["lost_keep"].append(p)
            lines.append(f"{p.name} is still leaving")
    for pid, nil in sec.get("offer", [])[:8]:
        e = by_pid.get(pid)
        if e is None or e.origin is team or e.destination is not None:
            continue
        user["offers"].add(e)
        user["interest"][e] = max(user["interest"].get(e, 0), 0.2)
        amt = int(max(0, nil or 0))
        if amt:
            amt = min(amt, max(0, fi.portal_room(league, team, rep)))
            rep.nil[(team, e)] = amt
        lines.append(f"offered {e.player.name} ({e.position}, {e.origin.school})" + (f" with {fi.money(amt)}/yr" if amt else ""))
    return lines


def roster_orders(league, team, sec):
    """Roster week: position changes, then cuts (walk-ons and scholarship players alike)."""
    import depth
    import morale
    import orders
    from models import POSITIONS
    roster = orders.roster_map(league, team)
    lines = []
    for pid, pos in sec.get("move", [])[:8]:
        p = roster.get(pid)
        if p is None or pos not in POSITIONS or pos == p.position:
            continue
        old = p.position
        depth.apply_move(league, team, p, pos)
        lines.append(f"{p.name}: {old} → {pos}")
    starters = {id(p) for g in team.starters().values() for p in g}
    for pid in sec.get("cut", [])[:15]:
        p = roster.get(pid)
        if p is None or p not in team.roster:
            continue
        team.roster.remove(p)
        p.team = None
        for q in team.roster:
            morale.nudge(q, -2 if id(p) in starters else -1, "a teammate was cut", league)
        lines.append(f"cut {p.name} ({p.position})")
    return lines


def roster_view(league, team):
    """Roster week on the website: the room counts against the template, and the staff's move ideas."""
    import depth
    import orders
    from roster import ROSTER_SIZE
    counts = {}
    for p in team.roster:
        counts[p.position] = counts.get(p.position, 0) + 1
    ideas = []
    try:
        for p, old, new, why in depth.move_ideas(league, team)[:8]:
            ideas.append([orders.pid(league, p), old, new, why])
    except Exception:                                       # noqa: BLE001, S110
        pass
    return {"size": dict(ROSTER_SIZE), "count": counts, "ideas": ideas}


def portal_view(league, team):
    """Portal Window I on the website: who's leaving you, and the whole board."""
    import knowledge as kn
    import orders
    off = _st(league).get("off")
    rep = off["ctx"]["report"].portal if off and off["ctx"]["report"].portal is not None else None
    if rep is None:
        return {}
    mine, board = [], []
    for e in rep.entries:
        p = e.player
        row = {"id": orders.pid(league, p), "n": p.name, "p": e.position, "yr": p.class_label, "from": kn.slug(e.origin.school),
               "why": e.reason, "stars": getattr(p, "hs_stars", None), "dest": kn.slug(e.destination.school) if e.destination else None}
        if e.origin is team:
            row["looks"] = __import__("scout").ovr_word(p.overall)
            row["nil"] = getattr(p, "nil_before_portal", 0)
            mine.append(row)
        else:
            row["looks"] = kn._approx_word(league, p)
            try:
                import portal as po
                scored = []
                for t in league.teams:
                    if t is e.origin:
                        continue
                    rr = random.Random(f"portal-market:{league.seed}:{league.year}:{p.name}:{t.school}")
                    scored.append((po.player_choice(league, league.recruiting, t, e, rr), t))
                scored.sort(key=lambda x: -x[0])
                top = scored[:5]
                best = top[0][0] if top else 0
                serious = sum(1 for score, _ in scored if best and score >= best * .90)
                row["market"] = "National frenzy" if serious >= 8 else "Heavy" if serious >= 5 else "Active" if serious >= 3 else "Light"
                row["top5"] = [kn.slug(t.school) for _, t in top]
            except Exception:
                row["market"], row["top5"] = "Unknown", []
            board.append(row)
    import finance as fi
    return {"mine": mine, "board": board[:400], "room": max(0, fi.portal_room(league, team, rep))}
