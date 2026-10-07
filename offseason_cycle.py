"""Phase 2 offseason processes: weekly recruiting, portal windows, and national movement.

The hub owns the calendar.  This module owns the systems that change while the
calendar advances.  It deliberately keeps the public PortalReport/ClassReport
objects used elsewhere so old screens, saves and exports continue to work.
"""
from collections import Counter
import random


def interactive(league):
    try:
        import offseason_cal
        return offseason_cal.active(league)
    except Exception:
        return False


def _seed(league, tag, extra=""):
    return random.Random(f"{getattr(league, 'year', 0)}:{tag}:{extra}")


def _state(league):
    import offseason_cal
    return offseason_cal._state(league)


def _news(league, week, text, kind="offseason"):
    st = _state(league)
    item = {"week": week, "kind": kind, "text": text}
    if item not in st.setdefault("news", []):
        st["news"].insert(0, item)
        del st["news"][80:]


def _release_settled_offers(report):
    for u in getattr(report, "users", None) or []:
        team = u.get("team")
        for e in list(u.get("offers", set())):
            if e.destination is not None:
                u["offers"].discard(e)
                report.nil.pop((team, e), None)


def _portal_rankings(league, report):
    import offseason_cal
    team = getattr(league, "user_team", None)
    st = _state(league)
    st["portal_summary"].update({
        "entries": len(report.entries),
        "moves": len(report.moves),
        "rank": offseason_cal._portal_rank(league, report, team),
        "recruit_rank": offseason_cal._recruit_rank(league, team),
        "overall_rank": offseason_cal._overall_class_rank(league, team, report, None),
        "in": len(report.by_team_in.get(team, []) or []) if team is not None else 0,
        "out": len(report.by_team_out.get(team, []) or []) if team is not None else 0,
    })
    offseason_cal._CONTEXT["portal"] = report


def _decision_week(entry, rng, start=4, end=6):
    """Hidden timing. Stars/older players often move quicker, but not always."""
    p = entry.player
    overall = getattr(p, "overall", 65)
    year = getattr(p, "year", 1)
    personality = str(getattr(p, "personality", "")).lower()
    fast = 0.18 + max(0, overall - 70) / 120 + (0.08 if year >= 2 else 0)
    slow = 0.18 + (0.12 if personality in ("patient", "loyal", "methodical") else 0)
    x = rng.random()
    if x < fast:
        return start
    if x > 1 - slow:
        return end
    return min(end, start + 1)


def _resolve_batch(league, rng, report, entries, room_left=None, rounds=2):
    """Use the existing market pricing/choice engine, but only for this week's decisions."""
    import portal
    if not entries:
        return 0
    incoming = Counter()
    for e, team in report.moves:
        if e.destination is team:
            incoming[team] += 1
    landed = 0
    room = len(entries) if room_left is None else max(0, room_left)
    remaining = [e for e in entries if e.destination is None]
    for rnd in range(rounds):
        if not remaining or landed >= room:
            break
        got = portal._portal_round(league, rng, report, remaining, incoming, room - landed, min(2, rnd))
        landed += got
        remaining = [e for e in entries if e.destination is None]
    return landed


def _backouts(league, rng, report, current_week, final_week):
    """A small slice of verbal portal commitments reopen before enrollment."""
    if current_week >= final_week:
        return 0
    candidates = [(e, t) for e, t in list(report.moves)
                  if e.destination is t and t is not e.origin and getattr(e.player, "team", None) is t]
    rng.shuffle(candidates)
    n = 0
    for e, t in candidates:
        # Better offers are more stable; NIL shoppers are a little more volatile.
        odds = 0.035 + (0.035 if getattr(e, "priority", None) == "money" else 0) + (0.02 if e.overall >= 80 else 0)
        if rng.random() >= odds:
            continue
        try:
            t.roster.remove(e.player)
        except ValueError:
            continue
        e.player.team = None
        e.destination = None
        if e in report.by_team_in.get(t, []):
            report.by_team_in[t].remove(e)
        try:
            report.moves.remove((e, t))
        except ValueError:
            pass
        report.__dict__.setdefault("backouts", []).append((e, t, current_week))
        report.__dict__.setdefault("decision_week", {})[e] = final_week
        _news(league, current_week, f"{e.position} {e.player.name} backs off his pledge to {t.school} and reopens his portal recruitment.", "portal")
        n += 1
        if n >= max(1, len(candidates) // 30):
            break
    return n


def begin_winter_portal(league, rng, year):
    """Create the winter market without advancing any of its three calendar weeks."""
    import portal
    report = portal.PortalReport(year)
    portal.open_portal(league, rng, report)
    report.__dict__["weekly"] = True
    report.__dict__["window_name"] = "Winter Window"
    trng = _seed(league, "portal1", year)
    report.__dict__["decision_week"] = {e: _decision_week(e, trng, 4, 6) for e in report.entries}
    report.__dict__["commit_log"] = []
    _portal_rankings(league, report)
    return report


def winter_portal_world_step(league, rng, report, week):
    """Resolve only the national movement for one winter portal week."""
    trng = _seed(league, "portal1", report.year)
    if week == 4:
        batch = [e for e in report.entries if report.decision_week[e] <= 4]
        room, rounds = max(1, int(len(batch) * .90)), 2
    elif week == 5:
        _backouts(league, trng, report, 5, 6)
        batch = [e for e in report.entries if e.destination is None and report.decision_week[e] <= 5]
        room, rounds = max(1, int(len(batch) * .88)), 2
    elif week == 6:
        batch = [e for e in report.entries if e.destination is None]
        import portal
        target_total = int(len(report.entries) * portal.LAND_RATE)
        room, rounds = max(0, target_total - len(report.moves)), 3
    else:
        raise ValueError("winter portal week must be 4, 5 or 6")
    before = len(report.moves)
    _resolve_batch(league, rng, report, batch, room_left=room, rounds=rounds)
    for e, t in report.moves[before:]:
        report.commit_log.append((week, e, t))
    _release_settled_offers(report)
    _portal_rankings(league, report)


def finish_winter_portal(league, report):
    report.unsigned = [e for e in report.entries if e.destination is None]
    _release_settled_offers(report)
    _portal_rankings(league, report)
    import offseason_cal
    offseason_cal._CONTEXT["portal"] = report
    try:
        import gray_area
        gray_area.after_portal(league, report)
    except Exception:
        pass
    league.__dict__["last_portal"] = report
    return report


def run_winter_portal(league, rng, year, window=None):
    """Winter portal over Weeks 4-6. CPU destinations resolve in waves."""
    import offseason_cal
    report = begin_winter_portal(league, rng, year)
    labels = {4: ("portal", "Work the live winter portal board", True),
              5: ("portal_market", "Revisit the winter portal market", False),
              6: ("portal_deadline", "Make final winter portal calls", False)}
    for week in (4, 5, 6):
        phase, label, required = labels[week]
        def board(rep=report):
            if window is not None:
                window(league, rep)
        offseason_cal._phase(league, phase, board if window is not None else None,
                              required=required, label=label)
        winter_portal_world_step(league, rng, report, week)
    return finish_winter_portal(league, report)

def recruiting_finish_board(league):
    """Week 7 player's recruiting-board work only; the national tick is a host world step online."""
    import offseason_cal
    def work_board():
        try:
            import recruiting_screens
            recruiting_screens.recruiting_menu(league)
        except Exception:
            pass
    return offseason_cal._phase(league, "recruit_finish", work_board, required=False,
                                 label="Work the final recruiting week")


def recruiting_finish_world(league, cycle, before=None):
    """Advance the one national recruiting tick after every coach has finished Week 7."""
    before = before or {t: cycle.class_rank(t) for t in league.teams}
    cycle.weekly_tick(14, user_team=None)
    after = {t: cycle.class_rank(t) for t in league.teams}
    return before, after


def run_recruiting_finish(league, cycle, rng):
    """Week 7 recruiting push. The user gets one final full-staff week before NSD."""
    team = getattr(league, "user_team", None)
    before = {t: cycle.class_rank(t) for t in league.teams}
    recruiting_finish_board(league)
    _, after = recruiting_finish_world(league, cycle, before)
    st = _state(league)
    rank = after.get(team) if team is not None else None
    st["class_summary"].update({"rank": rank, "movement": (before.get(team), rank)})
    if team is not None and before.get(team) and rank and before[team] != rank:
        arrow = "up" if rank < before[team] else "down"
        _news(league, 7, f"{team.school}'s recruiting class moves {arrow} from #{before[team]} to #{rank} entering Signing Day.", "recruiting")

def signing_week(league):
    """Week 8 hub before the existing signing-day resolver fires."""
    import offseason_cal
    def final_board():
        try:
            import recruiting_screens
            recruiting_screens.recruiting_menu(league)
        except Exception:
            pass
    offseason_cal._phase(league, "signing", final_board, required=False,
                          label="Make final Signing Day checks")


def _open_spring(league, rng, report):
    """Smaller post-spring window: depth-chart disappointment drives most entries."""
    import portal
    for team in league.teams:
        for player in list(team.roster):
            rank = portal.depth_chart_rank(team, player)
            base = portal.entry_odds(team, player, rank)
            # The second window is smaller, but losing a spring battle is especially dangerous.
            starters = portal.STARTER_DEPTH.get(player.position, 2)
            spring_buried = rank > starters
            try:
                import spring_cycle
                spring_form = spring_cycle.spring_form(league, player)
            except Exception:
                spring_form = 0.0
            # A player who lost ground all spring is far more likely to use the second window; a breakout is steadier.
            stock = max(-0.02, min(0.05, -spring_form * 0.018))
            odds = base * 0.20 + (0.015 if spring_buried else 0.0) + stock
            if rng.random() < min(.18, max(0.0, odds)):
                e = portal.PortalEntry(player, team, portal.reason_for(team, player, rank, rng), rank)
                report.entries.append(e)
                report.by_team_out[team].append(e)
                team.roster.remove(player)
                player.team = None
                player.nil_before_portal = getattr(player, "nil", 0)
                player.nil = 0
    report.entries.sort(key=lambda e: -e.overall)


def begin_spring_portal(league, rng, year):
    """Open the post-spring market without resolving either calendar week."""
    import portal
    import offseason_cal
    report = portal.PortalReport(year)
    report.__dict__["weekly"] = True
    report.__dict__["window_name"] = "Post-Spring Window"
    _open_spring(league, rng, report)
    trng = _seed(league, "portal2", year)
    report.__dict__["decision_week"] = {e: _decision_week(e, trng, 14, 15) for e in report.entries}
    report.__dict__["commit_log"] = []
    offseason_cal._CONTEXT["portal2"] = report
    return report


def spring_portal_world_step(league, rng, report, week):
    """Resolve one national wave of the post-spring portal."""
    if week == 14:
        batch = [e for e in report.entries if report.decision_week[e] <= 14]
        _resolve_batch(league, rng, report, batch, room_left=max(0, int(len(batch) * .88)), rounds=2)
    elif week == 15:
        remaining = [e for e in report.entries if e.destination is None]
        import portal
        target = int(len(report.entries) * portal.LAND_RATE)
        _resolve_batch(league, rng, report, remaining, room_left=max(0, target - len(report.moves)), rounds=3)
    else:
        raise ValueError("spring portal week must be 14 or 15")


def finish_spring_portal(league, report):
    import portal
    import offseason_cal
    report.unsigned = [e for e in report.entries if e.destination is None]
    for t in league.teams:
        portal.fill_gaps(t, report, league.rng)
    league.__dict__["last_portal2"] = report
    try:
        import gray_area
        gray_area.after_portal(league, report)
    except Exception:
        pass
    st = _state(league)
    team = getattr(league, "user_team", None)
    rank2 = offseason_cal._portal_rank(league, report, team) if team is not None else None
    winter = getattr(league, "last_portal", None) or offseason_cal._CONTEXT.get("portal")
    try:
        import recruiting
        scored = []
        for t in league.teams:
            recruits = list(league.recruiting.commitments(t))
            rp = recruiting.class_points(recruits)
            pp1 = offseason_cal._portal_score(list(getattr(winter, "by_team_in", {}).get(t, []))) if winter else 0
            pp2 = offseason_cal._portal_score(list(report.by_team_in.get(t, [])))
            score = rp + (pp1 + pp2) * 1.75
            if score > 0:
                scored.append((t, score))
        scored.sort(key=lambda x: -x[1])
        overall = next((i for i, (t, _) in enumerate(scored, 1) if t is team), None)
    except Exception:
        overall = None
    st["portal2_summary"] = {"entries": len(report.entries), "moves": len(report.moves),
                             "rank": rank2, "overall_rank": overall,
                             "in": len(report.by_team_in.get(team, [])) if team else 0,
                             "out": len(report.by_team_out.get(team, [])) if team else 0}
    if overall:
        st.setdefault("class_summary", {})["overall_rank"] = overall
    return report


def run_spring_portal(league, rng, year, window=None):
    """Weeks 14-15 post-spring window. Returns a second PortalReport."""
    import offseason_cal
    report = begin_spring_portal(league, rng, year)
    def board():
        if window is not None:
            window(league, report)
    offseason_cal._phase(league, "postspring", board if window is not None else None,
                          required=False, label="Work Portal Window II")
    spring_portal_world_step(league, rng, report, 14)
    offseason_cal._phase(league, "draft", board if window is not None else None,
                          required=False, label="Make final post-spring portal calls")
    spring_portal_world_step(league, rng, report, 15)
    return finish_spring_portal(league, report)


# ─── Head-coach market staged across the opening weeks ─────────────────────

def job_market_preview(league):
    """Week 1: show the calls/interview interest without forcing a final decision yet."""
    market = league.__dict__.get("_offseason_user_job_market") or {}
    offers = market.get("offers", [])
    if not offers and not market.get("fired_now"):
        try:
            import hc_search
            hc_search.tracker(league, league.year)
        except Exception:
            pass
        return
    from ui import C, clear, paint, pause, section, title_bar
    clear()
    print(title_bar("COACHING MARKET · INTERVIEW WEEK"))
    if market.get("fired_now"):
        print(paint("   You are on the market after being let go. These programs are considering you.", C.BYELLOW, C.BOLD))
    else:
        print(paint("   Your agent has calls. No decision is due today — these searches are moving toward finalists.", C.GRAY))
    print(section("PROGRAMS CALLING", C.BCYAN))
    for i, item in enumerate(offers, 1):
        t, kind = item if isinstance(item, tuple) else (item, "opening")
        note = "would move on from its current coach" if kind == "poach" else "open job"
        print(f"   [{i}] {t.full_name} · {t.conference} · prestige {round(t.prestige)} · {note}")
    print(paint("\n   The final offer decision comes with next week's agenda. You can still review the national search tracker.", C.GRAY))
    market["interviewed"] = True
    _news(league, 1, f"{len(offers)} program{'s' if len(offers) != 1 else ''} have contacted your agent as the head-coach market opens.", "coaching")
    pause()


def resolve_job_market(league):
    """Week 2: the staged calls become real offers. Accepting changes schools immediately."""
    market = league.__dict__.get("_offseason_user_job_market") or {}
    if market.get("resolved"):
        return
    offers = list(market.get("offers", []))
    fired_now = bool(market.get("fired_now"))
    coach = getattr(league, "user_coach", None)
    hook = getattr(league, "user_offer_hook", None)
    if coach is None or hook is None:
        market["resolved"] = True
        league.__dict__.pop("_reserved_user_jobs", None)
        return
    league._user_offer_terms = dict(market.get("terms", {}) or {})
    choice = hook(league, offers, fired_now)
    if choice is not None:
        offered_kind = next((kind for item in offers for t, kind in [item if isinstance(item, tuple) else (item, "opening")]
                             if t is choice), "opening")
        # Online offers are settled in arrival order. Once another player has taken an open
        # chair, a later replay cannot displace him; that coach sees the miss on the next snapshot.
        if getattr(league, "mode", None) == "career" and league.__dict__.get("online_client") is None \
                and (league.__dict__.get("online") or {}).get("started") and offered_kind != "poach" \
                and getattr(choice, "coach", None) is not None:
            _news(league, 2, f"{choice.school} filled its opening before your call was final.", "coaching")
            choice = None
    if choice is not None:
        import carousel
        import finance
        was = coach.team
        offer = getattr(league, "_user_offer_terms", {}).get(choice.school)
        carousel.hire(league, choice, coach, "poach" if was else "pool", offer)
        league.__dict__.setdefault("career_log", []).append((league.year, f"Took the head coaching job at {choice.school}"
                                               f"{' (left ' + was.school + ')' if was else ''}"
                                               f"{' — ' + finance.terms(offer) if offer else ''}."))
        _news(league, 2, f"{coach.name} accepts the head coaching job at {choice.school}.", "coaching")
    else:
        _news(league, 2, f"{coach.name} stays put as the head-coach market moves on.", "coaching")
    try:
        import career
        career.after_carousel(league)
    except Exception:
        pass
    # If the user changed jobs, the offseason hub should immediately describe
    # the new program rather than keep showing the old school's prior-season panel.
    if choice is not None:
        try:
            import offseason_cal
            now = getattr(league, "user_team", None)
            if now is not None:
                offseason_cal._state(league).setdefault("snapshots", {})["last_season"] = offseason_cal._last_season_snapshot(league, now)
        except Exception:
            pass
    market["resolved"] = True
    league.__dict__.pop("_user_offer_terms", None)
    league.__dict__.pop("_reserved_user_jobs", None)
