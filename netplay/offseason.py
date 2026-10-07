"""Online offseason: the Coach Career calendar, synchronized one world step at a time."""
import contextlib
import hashlib
import random

from ui import C, paint, pause
from netplay import moments

STAGES = ("wrap", "january", "staffcar", "portal4", "portal5", "portal6",
          "recruit7", "signing8", "after1", "spring14", "spring15", "after2", "done")


def state(league):
    on = league.__dict__.setdefault("online", {})
    st = on.setdefault("offseason", {})
    st.setdefault("stage", "wrap")
    st.setdefault("season", league.year)
    return st


def active(league):
    on = league.__dict__.get("online") or {}
    online_copy = getattr(league, "mode", None) == "online" or bool(league.__dict__.get("online_client"))
    ost = on.get("offseason") or {}
    return online_copy and bool(on.get("started")) and (getattr(league, "season_complete", False) or bool(ost)) \
        and ost.get("stage", "wrap") != "done"


def stage(league):
    return state(league).get("stage", "wrap") if active(league) else None


@contextlib.contextmanager
def seeded(league, tag):
    """Replayable offseason screens get their own deterministic league.rng stream."""
    rng = getattr(league, "rng", None)
    if rng is None or not hasattr(rng, "getstate"):
        yield
        return
    old = rng.getstate()
    rng.seed("online-offseason:%s:%s:%s" % (getattr(league, "seed", ""), state(league).get("season"), tag))
    try:
        yield
    finally:
        rng.setstate(old)


def fingerprint(league, team=None):
    """Small deterministic fingerprint for the team state changed by replayed offseason screens."""
    team = team or getattr(league, "user_team", None)
    if team is None:
        return "none"
    roster = sorted((getattr(p, "name", ""), getattr(p, "position", ""), getattr(p, "year", 0),
                     getattr(p, "overall", 0), getattr(p, "nil", 0)) for p in team.roster)
    staff = tuple(getattr(getattr(team, k, None), "name", None) for k in ("coach", "oc", "dc"))
    depth = sorted((k, tuple(getattr(p, "name", "") for p in v))
                   for k, v in (team.__dict__.get("depth_order") or {}).items())
    targets = sorted((getattr(getattr(r, "player", None), "name", ""), getattr(r, "national_rank", 0))
                     for r in (getattr(team, "recruiting_targets", None) or []))
    raw = repr((team.school, roster, staff, depth, targets))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _report(league):
    return state(league).get("report")


def _portal_window(league, key):
    report = _report(league)
    if report is None:
        return
    rep = report.portal if key.startswith("portal") else getattr(report, "portal2", None)
    hook = getattr(league, "portal_hook", None)
    if rep is None or hook is None:
        return
    import offseason_cal
    labels = {"portal4": ("portal", "Work the live winter portal board", True),
              "portal5": ("portal_market", "Revisit the winter portal market", False),
              "portal6": ("portal_deadline", "Make final winter portal calls", False),
              "spring14": ("postspring", "Work Portal Window II", False),
              "spring15": ("draft", "Make final post-spring portal calls", False)}
    phase, label, required = labels[key]
    offseason_cal._phase(league, phase, lambda: hook(league, rep), required=required, label=label)


@moments.moment("offseason")
def client_step(league, key):
    """One player's ordinary Career screens for the current synchronized offseason step."""
    with seeded(league, key):
        if key == "january":
            import offseason_cal
            offseason_cal.january(league, league.user_team)
        elif key == "staffcar":
            import offseason_cal
            import staff_carousel
            offseason_cal._phase(league, "staffcar",
                                  lambda: staff_carousel.summary(league, state(league).get("season"), pause_after=True),
                                  required=False, label="Review the assistant-coach carousel")
        elif key in ("portal4", "portal5", "portal6", "spring14", "spring15"):
            _portal_window(league, key)
        elif key == "recruit7":
            import offseason_cycle
            offseason_cycle.recruiting_finish_board(league)
        elif key == "signing8":
            import offseason_cycle
            offseason_cycle.signing_week(league)
        elif key == "after1":
            import offseason_cal
            offseason_cal.after_part1(league, _report(league))
        elif key == "after2":
            import offseason_cal
            offseason_cal.after_part2(league, _report(league))


def play(league):
    """Client-side offseason turn. Returns a newer world, or None if the player backs out."""
    from netplay import lobby
    c = lobby.SESSION["client"]
    key = stage(league) or "wrap"
    if key == "done":
        return c.fetch_world(force=True) or league
    from netplay import capture
    if key == "wrap":
        import screens
        screens.season_wrap(league, advance=False)
    else:
        client_step(league, key)
    res = c.post_orders(capture.take(league, league.user_team), moments.take())
    if "error" in res:
        print(paint("\n   " + (res.get("message") or res["error"]), C.BRED))
        pause()
        if res.get("error") == "stale":
            return c.fetch_world(force=True)
        return None
    from netplay.turn import _notices
    _notices(res)
    c.ready(True)
    return _wait(c, key)


def _wait(c, key):
    import time
    from netplay.turn import WAIT_SLICE, remote_session
    from netplay import lobby
    deadline = time.time() + WAIT_SLICE
    c.events()
    while True:
        st = c.status()
        if c.name in st.get("screens", []):
            remote_session(c)
            continue
        if int(st.get("rev") or 0) > c.rev:
            w = c.fetch_world()
            if w is not None:
                return w
        from ui import ask, clear, title_bar
        clear()
        print(title_bar("OFFSEASON · EVERYONE TOGETHER", sub=(st.get("offseason_label") or key).upper()))
        print()
        for s in st.get("seats", []):
            if not s.get("school"):
                continue
            mark = paint("✓ ready", C.BGREEN, C.BOLD) if s.get("ready") else paint("… working", C.GRAY)
            print("   %-18s%-22s%s" % (s["name"], s["school"], mark))
        if st.get("online_error"):
            print(paint("\n   Host worker error: " + str(st["online_error"]), C.BRED))
            if lobby.SESSION.get("host") is not None:
                print(paint("   You can force this calendar step to retry once the cause is clear.", C.GRAY))
        print(paint("\n   The calendar advances when everyone is ready. (Ctrl+C for options.)", C.GRAY), flush=True)
        try:
            left = deadline - time.time()
            if left > 0:
                c.events(wait=min(20, left))
                continue
        except KeyboardInterrupt:
            pass
        host = lobby.SESSION.get("host")
        opts = ["[Enter] keep waiting", "[U] not ready after all"]
        if host is not None:
            opts.append("[F] don't wait: advance now")
        ch = ask("  ·  ".join(opts) + ":").strip().lower()
        deadline = time.time() + WAIT_SLICE
        if ch == "u":
            if int(c.status().get("rev") or 0) <= c.rev:
                c.ready(False)
                return None
        elif ch == "f" and host is not None:
            host.force()


def host_advance(host):
    """Run exactly one authoritative world step between player ready-ups."""
    from netplay import replay
    with replay.host_thread():
        _host_advance(host)


def _host_advance(host):
    from netplay import seat
    import season
    import offseason_cycle
    lg = host.league
    with host.worker:
        with host.lock:
            st = state(lg)
            key = st.get("stage", "wrap")
            ctx = st.get("ctx")
            if key == "wrap":
                import career_plus
                for t in list(seat.humans(lg)):
                    with seat.acting_as(lg, t):
                        career_plus.season_end(lg)
                ctx = season.offseason_begin(lg)
                st["ctx"] = ctx
                lg.online["defer_staff_offseason"] = True
                try:
                    season.off_carousel(lg, lg.rng, ctx)
                finally:
                    lg.online.pop("defer_staff_offseason", None)
                st["stage"] = "january"
            elif key == "january":
                import staff
                staff.offseason(lg, lg.rng)
                import netplay.host as nh
                nh.follow_coaches(lg)
                st["stage"] = "staffcar"
            elif key == "staffcar":
                season.off_awards(lg, lg.rng, ctx)
                season.off_winter(lg, lg.rng, ctx)
                report = ctx["report"]
                report.portal = offseason_cycle.begin_winter_portal(lg, lg.rng, ctx["next_year"])
                st["report"] = report
                st["stage"] = "portal4"
            elif key in ("portal4", "portal5", "portal6"):
                report = st["report"].portal
                week = int(key[-1])
                offseason_cycle.winter_portal_world_step(lg, lg.rng, report, week)
                if week < 6:
                    st["stage"] = "portal%d" % (week + 1)
                else:
                    offseason_cycle.finish_winter_portal(lg, report)
                    st["stage"] = "recruit7"
            elif key == "recruit7":
                offseason_cycle.recruiting_finish_world(lg, lg.recruiting)
                st["stage"] = "signing8"
            elif key == "signing8":
                # The board work is already replayed per seat. Resolve signing once, with any
                # room checks bridged live to the relevant player.
                ctx["interactive"] = False
                season.off_signing(lg, lg.rng, ctx)
                report = ctx["report"]
                st["report"] = report
                try:
                    import recruit_ui
                    for t in list(seat.humans(lg)):
                        with seat.acting_as(lg, t):
                            recruit_ui.signing_day_live(lg, report.recruiting, getattr(lg, "user_team", None))
                except Exception as e:
                    lg.__dict__.setdefault("error_log", []).append("online signing live: %r" % (e,))
                season.off_arrivals(lg, lg.rng, ctx)
                season.off_rollover(lg, lg.rng, ctx)
                lg.after_offseason(report)
                st["stage"] = "after1"
            elif key == "after1":
                report = st["report"]
                report.portal2 = offseason_cycle.begin_spring_portal(lg, lg.rng, lg.year)
                st["stage"] = "spring14"
            elif key in ("spring14", "spring15"):
                report = st["report"].portal2
                week = 14 if key == "spring14" else 15
                offseason_cycle.spring_portal_world_step(lg, lg.rng, report, week)
                if week == 14:
                    st["stage"] = "spring15"
                else:
                    offseason_cycle.finish_spring_portal(lg, report)
                    st["stage"] = "after2"
            elif key == "after2":
                st["stage"] = "done"
            else:
                return
            try:
                import netplay.host as nh
                nh.follow_coaches(lg)
            except Exception:
                pass
        host.bump("offseason: " + st.get("stage", "done"))
        host.emit("offseason", stage=st.get("stage"), rev=host.rev)
