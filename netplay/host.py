"""
netplay/host.py — the world server (Online LAN mode).

One copy of the game hosts. Its league is the only truth: it takes everyone's orders,
runs the week, and hands every client the new world. The server runs on its own thread
(ThreadingHTTPServer), so the host's own screens stay live; the host plays as a client too,
over localhost.

    host = Host(league, port=protocol.DEFAULT_PORT)
    host.start()                  # serving; host.address() / host.code to read out
    ...
    host.stop()

Before START the room is a lobby: players join with the code and pick programs (the sitting
coach, or one of their own built from the career form). START turns the world into an online
world (convert) and puts every player on his program; the world then belongs to everyone.

Every touch of the league happens under host.lock: an order being applied and a snapshot
being taken never overlap. Seats live in league.online["seats"], so they're saved with the
world and a player who drops off the Wi-Fi rejoins with his token.
"""
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from netplay import protocol, sync


def lan_address():
    """This computer's address on the home network (what the others type), or 127.0.0.1."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))          # no packet is sent: this only picks the interface
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class Host:
    def __init__(self, league, port=protocol.DEFAULT_PORT, bind=None, code=None):
        import title
        self.league = league
        self.port = int(port)
        self.bind = bind or "0.0.0.0"
        self.code = code or protocol.new_code()
        self.version = title.VERSION
        self.lock = threading.RLock()
        self.cond = threading.Condition()
        self.events = []
        self.event_n = 0
        self.rev = 1
        self._snap = (0, None)                 # (rev, bytes): built once per rev
        self.wrong_codes = 0
        self.phase = "planning"                # planning -> games (kicked off, coaches play theirs) -> planning
        self.week_games = []
        self.reports = {}                      # school -> the client's report of his game
        self.results = {}                      # school -> {"sig": ..., "match": bool} for the last week
        self.worker = threading.Lock()         # one kickoff / one week at a time
        self._offseason_pending = False        # de-dupe Ready/Force clicks while an offseason step starts
        self.server = None
        self.thread = None
        on = league.__dict__.setdefault("online", {})
        on.setdefault("seats", {})             # token -> {name, school, ready, joined}
        self.world = sync.world_id(league)
        self.universe = sync.universe_name(league)
        self.universe_hash = sync.universe_hash(self.universe)

    # ── seats ───────────────────────────────────────────────────────────────
    @property
    def seats(self):
        return self.league.online["seats"]

    def seat_of(self, token):
        return self.seats.get(str(token or ""))

    def team_of(self, seat):
        school = seat.get("school") if seat else None
        return next((t for t in self.league.teams if t.school == school), None) if school else None

    def taken(self):
        return {s["school"] for s in self.seats.values() if s.get("school")}

    # ── events (the long-poll feed) ─────────────────────────────────────────
    def emit(self, kind, **data):
        with self.cond:
            self.event_n += 1
            self.events.append(dict(data, n=self.event_n, kind=kind, at=round(time.time(), 1)))
            del self.events[:-200]
            self.cond.notify_all()

    def events_since(self, n, wait):
        deadline = time.time() + max(0.0, min(float(wait), protocol.MAX_WAIT))
        with self.cond:
            while True:
                out = [e for e in self.events if e["n"] > n]
                left = deadline - time.time()
                if out or left <= 0:
                    return out, self.event_n
                self.cond.wait(left)

    # ── the world ───────────────────────────────────────────────────────────
    def snapshot(self):
        """(rev, bytes) of the current world; built once per rev."""
        with self.lock:
            if self._snap[0] != self.rev:
                self._snap = (self.rev, sync.snapshot(self.league))
            return self._snap

    def bump(self, why=""):
        """The world moved (a week played, a stage run): clients should fetch it."""
        with self.lock:
            self.rev += 1
            self.league.online.pop("last_error", None)
            for s in self.seats.values():
                s["ready"] = False
        self.emit("world", rev=self.rev, why=why)

    def status(self):
        """Read without the world's lock: a player answering a question mid-offseason still sees the room."""
        from netplay import replay
        lg = self.league
        ost = (lg.__dict__.get("online") or {}).get("offseason") or {}
        labels = {"wrap": "Season wrap", "january": "January · coaching market", "staffcar": "January · staff carousel",
                  "portal4": "January · portal opens", "portal5": "January · portal market",
                  "portal6": "January · portal deadline", "recruit7": "February · signing push",
                  "signing8": "National Signing Day", "after1": "February–April · spring",
                  "spring14": "May · spring portal", "spring15": "May · portal deadline",
                  "after2": "June–July · summer and Media Days", "done": "Offseason complete"}
        return {"screens": sorted(n for n, b in replay.BRIDGES.items() if b.live),"world": self.world, "rev": self.rev, "game_version": self.version, "started": self.started,
                    "phase": self.phase, "offseason_stage": ost.get("stage"), "offseason_label": labels.get(ost.get("stage")),
                    "online_error": lg.online.get("last_error"),
                    "played": sorted(self.reports), "expect": sorted(self.expected_reports()),
                    "results": {k: v["match"] for k, v in self.results.items()},
                    "universe": self.universe, "year": lg.year, "week": lg.week,
                    "week_name": lg.week_name(lg.week + 1) if not lg.season_complete else "Offseason",
                    "seats": [{"name": s["name"], "school": s.get("school"), "coach": s.get("coach"),
                               "ready": bool(s.get("ready")),
                               "seen": round(time.time() - s.get("seen", 0))} for s in list(self.seats.values())]}

    # ── requests ────────────────────────────────────────────────────────────
    def join(self, req):
        info = {"code": self.code, "game_version": self.version, "universe": self.universe,
                "universe_hash": self.universe_hash, "world": self.world}
        with self.lock:
            seat = self.seat_of(req.get("token"))
            if req.get("token") and seat is None:
                return {"error": "That seat isn't in this world any more. Join with the code as a new coach."}
            why = protocol.join_refusal(req, info)
            if why == "Wrong join code.":
                self.wrong_codes += 1
                delay = min(2.0, 0.2 * self.wrong_codes)
            elif why:
                return {"error": why}
            elif seat is not None:                                  # a reconnect: same seat
                seat["seen"] = time.time()
                token = req["token"]
            else:
                token = protocol.new_token()
                seat = {"name": self._unique(protocol.clean_name(req.get("name"))), "school": None,
                        "coach": "adopt", "form": None, "ready": False, "joined": time.time(), "seen": time.time()}
                if req.get("school"):
                    why = self._pick(seat, str(req["school"]), "adopt", None)
                    if why:
                        return {"error": why}
                self.seats[token] = seat
        if why:                                                     # a wrong code, outside the lock:
            time.sleep(delay)                                       # guessing 10,000 codes gets slow
            return {"error": why}
        self._bridge(seat["name"])
        self.emit("join", name=seat["name"], school=seat.get("school"))
        return {"token": token, "seat": {"name": seat["name"], "school": seat.get("school")},
                "world": self.world, "rev": self.rev, "started": self.started}

    def _bridge(self, name):
        from netplay import replay
        b = replay.BRIDGES.get(name)
        if b is None:
            b = replay.Bridge(name)
            replay.BRIDGES[name] = b
        b.on_live = lambda who: self.emit("screen", name=who)
        if not b.live:                         # reconnecting during a live question must not erase it
            b.begin()

    def screen(self, req):
        """GET /screen: a player's screen while the host's world needs him (see replay.Bridge)."""
        from netplay import replay
        seat = self.seat_of(req.get("token"))
        b = replay.BRIDGES.get(seat["name"]) if seat else None
        if b is None:
            return {"chunks": [], "waiting": False, "live": False, "last": 0}
        return b.since(int(req.get("since") or 0), float(req.get("wait") or 0))

    def answer(self, req):
        """POST /answer: what he typed at the question on his screen."""
        from netplay import replay
        seat = self.seat_of(req.get("token"))
        b = replay.BRIDGES.get(seat["name"]) if seat else None
        if b is None or not b.waiting:
            return {"error": "Nothing is waiting on you."}
        b.answer(req.get("text") or "")
        return {"ok": True}

    def _unique(self, name):
        names = {s["name"].lower() for s in self.seats.values()}
        base, n = name, 2
        while name.lower() in names:
            name = f"{base[:protocol.NAME_MAX - 3]} {n}"
            n += 1
        return name

    @property
    def started(self):
        return bool(self.league.online.get("started"))

    def _pick(self, seat, school, coach, form):
        """A seat picks a program (lobby). Returns why not, or None. After START the pick is
        made in the world right away."""
        team = next((t for t in self.league.teams if t.school == school), None)
        if team is None:
            return f"There's no program called {school}."
        if school in self.taken() and seat.get("school") != school:
            return f"{school} already has a coach in this world."
        if coach not in ("adopt", "new"):
            return "Choose the sitting coach or a coach of your own."
        if coach == "adopt" and (team.coach is None or getattr(team.coach, "interim", None)):
            return f"{school} has no permanent head coach to take over. Bring your own coach."
        if self.started and seat.get("school"):
            return "You already coach a program in this world. (Changing jobs comes with the coaching market.)"
        seat.update(school=school, coach=coach, form=protocol.clean_form(form) if coach == "new" else None)
        if self.started:
            claim_seat(self.league, seat)
            self.bump(f"{seat['name']} takes over {school}")
        return None

    def set_seat(self, req):
        with self.lock:
            seat = self.seat_of(req.get("token"))
            if seat is None:
                return {"error": "Unknown seat. Join again."}
            why = self._pick(seat, str(req.get("school") or ""), str(req.get("coach") or "adopt"), req.get("form"))
            if why:
                return {"error": why}
            out = {"ok": True, "school": seat["school"], "coach": seat["coach"]}
        self.emit("seat", name=seat["name"], school=seat["school"], coach=seat["coach"])
        return out

    def programs(self):
        """The lobby's program list: every FBS program, who coaches it, who's picked it."""
        by = {s["school"]: s["name"] for s in self.seats.values() if s.get("school")}
        with self.lock:
            rows = []
            for t in self.league.teams:
                if getattr(t, "fcs", False):
                    continue
                c = t.coach
                rows.append({"school": t.school, "conf": t.conference, "prestige": t.prestige,
                             "coach": c.name if c is not None else None,
                             "interim": bool(c is not None and getattr(c, "interim", None)),
                             "taken": by.get(t.school)})
            return {"programs": rows, "started": self.started}

    def start_world(self):
        """START: an online world from here on, every player on his program."""
        with self.lock:
            if self.started:
                return "Already started."
            coached = [s for s in self.seats.values() if s.get("school")]
            if not coached:
                return "Nobody has picked a program yet."
            waiting = [s["name"] for s in self.seats.values() if not s.get("school")]
            if waiting:
                return "Still picking a program: " + ", ".join(waiting) + "."
            convert(self.league)
            for s in coached:
                claim_seat(self.league, s)
                self._bridge(s["name"])
            self.league.online["started"] = True
        self.bump("the world starts")
        self.emit("start", rev=self.rev)
        return None

    def post_orders(self, req):
        import orders
        with self.lock:
            seat = self.seat_of(req.get("token"))
            if seat is None:
                return {"error": "Unknown seat. Join again."}
            if not self.started:
                return {"error": "The world hasn't started yet."}
            if self.phase != "planning":
                return {"error": "The week is under way: orders open again when it's played."}
            team = self.team_of(seat)
            if team is None:
                return {"error": "You don't coach a program yet."}
            if int(req.get("rev") or 0) != self.rev:
                return {"error": "stale", "rev": self.rev,
                        "message": "The world moved on since you made these. Fetch it and make them again."}
            seat["seen"] = time.time()
            from netplay import moments, replay
            with replay.host_thread():
                clean, warn = orders.validate(self.league, team, req.get("orders") or {})
                lines = orders.apply(self.league, team, clean) if clean else []
                warn += moments.apply(self.league, team, req.get("moments"))
                if (self.league.__dict__.get("online") or {}).get("offseason"):
                    follow_coaches(self.league)
        return {"ok": True, "warnings": warn, "lines": lines}

    def set_ready(self, req):
        with self.lock:
            seat = self.seat_of(req.get("token"))
            if seat is None:
                return {"error": "Unknown seat. Join again."}
            if self.phase != "planning" and req.get("ready"):
                return {"error": "The week is already under way."}
            seat["ready"] = bool(req.get("ready"))
            seat["seen"] = time.time()
            name, ready = seat["name"], seat["ready"]
        self.emit("ready", name=name, ready=ready)
        if ready and self.all_ready():
            from netplay import offseason
            self._queue_offseason() if offseason.active(self.league) else self._in_background(self.kickoff)
        return {"ok": True}

    # ── the week ────────────────────────────────────────────────────────────
    def _in_background(self, fn):
        def run():
            try:
                fn()
            except Exception as e:  # keep a worker failure visible to every player instead of silently hanging
                with self.lock:
                    self.league.online["last_error"] = "%s: %s" % (type(e).__name__, e)
                self.emit("error", message=self.league.online["last_error"])
        threading.Thread(target=run, name="cc-week", daemon=True).start()

    def _queue_offseason(self):
        """Schedule at most one offseason world step. Ready/Force can arrive more than once."""
        with self.lock:
            if self._offseason_pending:
                return False
            self._offseason_pending = True

        def run():
            try:
                from netplay import offseason
                offseason.host_advance(self)
            finally:
                with self.lock:
                    self._offseason_pending = False
        self._in_background(run)
        return True

    def _humans(self):
        return {s["school"]: s for s in self.seats.values() if s.get("school")}

    def expected_reports(self):
        """The schools whose coach has a game this week (his report brings what he typed, and his
        postgame podium; two players' meeting is the staffs' game, but their podiums still count)."""
        humans = self._humans()
        return {t.school for g in self.week_games for t in (g.home, g.away) if t.school in humans}

    def kickoff(self):
        """Everyone's ready (or the host said go): this week's plans go in and the week starts.
        Each coach then plays his own game on his own copy."""
        from netplay import replay
        with replay.host_thread():
            self._kickoff()

    def _kickoff(self):
        import orders
        import people
        import preseason
        from netplay import seat
        with self.worker:
            with self.lock:
                if self.phase != "planning" or self.league.season_complete:
                    return
                lg = self.league
                if lg.week == 0:
                    preseason.mark_done(lg)             # fall camp was each coach's, on his copy
                for school in self._humans():
                    t = next(x for x in lg.teams if x.school == school)
                    with seat.acting_as(lg, t):
                        people.weekly(lg)             # his week's mail, if he never opened his hub
                    orders.apply_calls(lg, t)
                    orders.apply_plan(lg, t)
                self.week_games = lg.start_week()
                lg.online["kick_order"] = [(g.home.school, g.away.school) for g in self.week_games]
                self.reports, self.phase = {}, "games"
            self.bump("kickoff")
            self.emit("kickoff", week=self.league.week, expect=sorted(self.expected_reports()))
            if not self.expected_reports():
                self._in_background(self.play_week)

    def post_report(self, req):
        """A coach played his game: authoritative result/box score plus postgame moments."""
        with self.lock:
            seat = self.seat_of(req.get("token"))
            if seat is None:
                return {"error": "Unknown seat. Join again."}
            if self.phase != "games" or int(req.get("rev") or 0) != self.rev:
                return {"error": "That week isn't being played."}
            school = seat.get("school")
            rep = req.get("game")
            if isinstance(rep, dict) and school:
                self.reports[school] = {k: rep.get(k) for k in ("result", "moments")}
            done = self.expected_reports() <= set(self.reports)
            name = seat["name"]
        self.emit("played", name=name)
        if done:
            self._in_background(self.play_week)
        return {"ok": True}

    def play_week(self):
        """Finish the official week in kickoff order: import connected coaches' submitted games,
        simulate every other matchup, then run the normal week's business."""
        from netplay import replay
        with replay.host_thread():
            self._play_week()

    def _play_week(self):
        import career_plus
        import hotseat
        from netplay import moments
        with self.worker:
            with self.lock:
                if self.phase != "games":
                    return
                lg = self.league
                results = {}
                humans = self._humans()
                from netplay import result as game_result
                for g in self.week_games:
                    mine = [t for t in (g.home, g.away) if t.school in humans]
                    reps = [(t, self.reports.get(t.school)) for t in mine]
                    submitted = [(t, rep) for t, rep in reps if rep is not None and rep.get("result")]
                    if submitted:
                        # A connected coach's played game is authoritative.  In a user-vs-user
                        # matchup prefer the home coach's copy, otherwise the only submitted copy.
                        team, rep = next(((t, r) for t, r in submitted if t is g.home), submitted[0])
                        game_result.apply(lg, g, rep["result"])
                        for t, _r in submitted:
                            results[t.school] = {"imported": True}
                    else:
                        lg.play_game(g)
                    for team, rep in reps:
                        if rep is not None:
                            moments.apply(lg, team, rep.get("moments"))   # his postgame podium
                lg.finish_week(self.week_games)
                games = self.week_games
                hotseat.each_seat(lg, lambda: career_plus.weekly(lg, games))   # each coach's storylines
                self.results, self.phase, self.week_games = results, "planning", []
            self.bump("week played")
            self.emit("week", week=self.league.week,
                      results={k: True for k in results})

    def force(self):
        """The host doesn't wait: the week kicks off, or plays (a missing coach's staff takes his game)."""
        from netplay import offseason
        if offseason.active(self.league):
            self._queue_offseason()
        elif self.phase == "planning":
            self._in_background(self.kickoff)
        elif self.phase == "games":
            self._in_background(self.play_week)

    def all_ready(self):
        with self.lock:
            coached = [s for s in self.seats.values() if s.get("school")]
            return bool(coached) and all(s.get("ready") for s in coached)

    # ── the server ──────────────────────────────────────────────────────────
    def start(self):
        host = self

        class Handler(_Handler):
            pass
        Handler.host = host
        self.server = ThreadingHTTPServer((self.bind, self.port), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]           # port 0 = any free one
        self.thread = threading.Thread(target=self.server.serve_forever, name="cc-host", daemon=True)
        self.thread.start()
        return self

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        # Bridges are process-global because input()/stdout are patched once. Do not let a later
        # hosted world inherit callbacks, buffered text, or answers from this one.
        from netplay import replay
        for s in list(self.seats.values()):
            replay.BRIDGES.pop(s.get("name"), None)

    def address(self):
        ip = lan_address() if self.bind in ("0.0.0.0", "") else self.bind
        return f"{ip}:{self.port}"


def convert(league):
    """A world becomes an online world. Like Commissioner Mode, every program is a player's
    (his orders run it) or the CPU's; there is no single user on the host. A career coach the
    world came with stays in it: his program is a player's only if someone picks it."""
    import commissioner as cm
    import orders
    from netplay import seat
    me = getattr(league, "user_coach", None)
    seat.adopt_career(league, me.team.school if me is not None and me.team is not None else None)
    league.mode = "online"
    league.user_team = None
    league.user_coach = None
    league.__dict__.pop("user_offer_hook", None)
    league.__dict__.pop("portal_hook", None)
    league.__dict__.pop("hotseat", None)
    if me is not None:
        me.is_user = False                    # the CPU runs him now, unless a player adopts him
    cm.state(league)                          # the team registry (owners) and standing orders
    orders.ensure_ids(league)


def claim_seat(league, seat):
    """Put a seat's player on his program: the sitting coach, or his own from the form."""
    import commissioner as cm
    team = next(t for t in league.teams if t.school == seat["school"])
    member = seat["name"]
    ok, msg = cm.claim(league, team, member)
    if not ok:
        raise ValueError(msg)
    cm.take_over(league, team, member, "new" if seat.get("coach") == "new" else "adopt", seat.get("form") or {})
    seat["coach_name"] = team.coach.name if team.coach is not None else None
    if team.coach is not None:
        team.coach.is_user = True                   # a player's coach is a career coach: his tree, his calls
        team.coach.online_player = member           # and he's this player's wherever he goes
    from netplay import seat as seats
    seats.claim_career(league, member, team.school)


def follow_coaches(league):
    """After anything that moves coaches (the carousel, a job taken, a firing): each player goes
    where his coach went. Returns [(name, old school, new school or None)]."""
    import commissioner as cm
    moves = []
    seats = league.online.get("seats", {}).values()
    everyone = [t.coach for t in league.teams if t.coach is not None] + list(getattr(league, "coach_pool", []))
    for s in seats:
        c = next((x for x in everyone if getattr(x, "online_player", None) == s["name"]), None)
        now = c.team.school if c is not None and c.team is not None else None
        if now == s.get("school"):
            continue
        old = s.get("school")
        if old:
            t = next((x for x in league.teams if x.school == old), None)
            if t is not None and cm.is_player_team(league, t):
                cm.release(league, t, "left")
        if now:
            t = next(x for x in league.teams if x.school == now)
            cm.claim(league, t, s["name"])
            cm.team_row(league, t)["coach_name"] = c.name
        s["school"] = now
        moves.append((s["name"], old, now))
    return moves


def replay_game(league, g, team, rep):
    """A coach's game on the official world, exactly as he played it on his copy. True when it
    came out the same (the fingerprints match)."""
    import coach_mode
    import staff
    from commentary import Narrator
    from netplay import replay
    from netplay import seat
    hvh = replay.both_human(league, g)
    acting = seat.acting_as(league, team)                         # as him, as his copy did
    acting.__enter__()
    try:
        calls = rep.get("calls") or {}
        staff.set_calls(team, off=calls.get("off"), df=calls.get("def"))
        if not hvh:
            g.halftime_team = team
        mode = rep.get("mode") or "sim"
        narr = None
        if mode != "sim":
            narr = Narrator(booth_index=int(rep.get("booth") or 0), delay=0, rng=replay.narr_rng(league, g),
                            league=league)
            if mode in ("full", "moments"):
                g.controller = coach_mode.setup_for_game(league, g, mode=mode, call_defense=bool(rep.get("call_d")))
            if mode == "moments":
                narr.muted = True
        with replay.replaying(rep.get("keys"), rep.get("settings")):
            league.play_game(g, narr)
    finally:
        g.controller = None
        g.__dict__.pop("halftime_team", None)
        acting.__exit__(None, None, None)
    return replay.signature(g) == rep.get("sig")


def replay_sig(g):
    from netplay import replay
    return replay.signature(g)


class _Handler(BaseHTTPRequestHandler):
    host = None
    protocol_version = "HTTP/1.1"
    server_version = "ConsoleCollege"

    def log_message(self, fmt, *args):         # the host's screen isn't a web log
        pass

    def _send(self, code, body=b"", ctype="application/json", headers=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, str(v))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, protocol.dumps(obj))

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > protocol.MAX_BODY:
            raise ValueError("too big")
        return protocol.loads(self.rfile.read(n)) if n else {}

    def do_GET(self):
        url = urlparse(self.path)
        q = {k: v[-1] for k, v in parse_qs(url.query).items()}
        h = self.host
        try:
            if url.path == "/status":
                return self._json(h.status())
            if url.path == "/programs":
                return self._json(h.programs())
            if url.path == "/screen":
                return self._json(h.screen(q))
            if url.path == "/world":
                since = int(q.get("since") or 0)
                if since and since >= h.rev:
                    return self._send(204)
                rev, blob = h.snapshot()
                return self._send(200, blob, "application/octet-stream", {"X-Rev": rev})
            if url.path == "/events":
                evs, last = h.events_since(int(q.get("since") or 0), float(q.get("wait") or 0))
                return self._json({"events": evs, "last": last})
            return self._json({"error": "not found"}, 404)
        except (ValueError, TypeError):
            return self._json({"error": "bad request"}, 400)

    def do_POST(self):
        h = self.host
        try:
            req = self._body()
        except ValueError:
            return self._json({"error": "bad request"}, 400)
        route = {"/join": h.join, "/seat": h.set_seat, "/orders": h.post_orders,
                 "/ready": h.set_ready, "/report": h.post_report, "/answer": h.answer}.get(urlparse(self.path).path)
        if route is None:
            return self._json({"error": "not found"}, 404)
        out = route(req)
        return self._json(out, 200 if "error" not in out else 409 if out.get("error") == "stale" else 403)
