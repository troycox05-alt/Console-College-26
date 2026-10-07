"""
commissioner.py — Commissioner Mode: run a Discord league from one copy of the game.

Every program is either a PLAYER team (a Discord member coaches it; his decisions arrive
as imported orders) or a CPU team (the game's AI runs it exactly as in any other mode).
You, the commissioner, are the only one at the keyboard. There is no user coach: the
dashboard, the inbox, press conferences and every other one-human screen stay dark.

PHASE 1 (this file today) is the foundation the later phases build on:
  * the mode and its versioned state block (league.commish), saved with the league
  * the switches: sanctions, rule-bending and discipline off; no player inboxes, press
    conferences, rivalry-week moments or skill points; difficulty locked at Varsity
  * the team registry: who owns each program (a Discord name, or CPU)
  * AI recruiting skipped for player teams (their orders take over in Phase 2)
  * per-cycle seeding: a rolled-back cycle re-runs to exactly the same results
  * the Commissioner Desk: status, teams, the Commissioner Inbox, advance, save

Later phases add orders and codes (2), the website (3), the full in-season loop (4),
the coaching market (5), staff and money (6) and the offseason calendar (7).
"""
import os
import random
import secrets

MODE = "commissioner"
SCHEMA = 1

# Feature switches. False = that system never runs in this league.
SWITCHES = {
    "sanctions":       ("Sanctions",            "NCAA cases, investigations, penalties, academic holds"),
    "rule_bending":    ("Rule-bending",         "recruiting overtime, back-channel tampering"),
    "discipline":      ("Discipline",           "locker-room incidents and team-rules suspensions"),
    "player_inboxes":  ("Player inboxes",       "messages and choices for player coaches"),
    "press":           ("Press conferences",    "weekly pressers for player coaches"),
    "rivalry_moments": ("Rivalry-week moments", "rivalry-week scenes for player coaches"),
    "skills":          ("Skill points",         "the coaching tree for player coaches"),
}
DEFAULT_SETTINGS = {k: False for k in SWITCHES}
DEFAULT_SETTINGS["difficulty"] = "varsity"

INBOX_KINDS = {"note": "Note", "import": "Import problems", "inactive": "Inactive member", "fired": "Member fired",
               "vacancy": "Member left", "claim": "New member", "offer": "Job offer", "hired": "Member hired",
               "contract": "Contract"}
ASK = [None]          # the desk sets a callback while a cycle runs: decisions that need you, right now


# ═══ State ══════════════════════════════════════════════════════════════════

def active(league):
    return getattr(league, "mode", None) == MODE


def _team_row():
    return {"owner": None, "since": None, "secret": secrets.token_hex(16), "orders": {},
            "last_cycle": None, "missed": 0}


def _new_state(league):
    return {
        "version": SCHEMA,
        "league_id": f"CC-{league.seed}-{secrets.token_hex(3)}",
        "settings": dict(DEFAULT_SETTINGS),
        "cycle": {"n": 0, "label": "", "history": []},
        "teams": {t.school: _team_row() for t in league.teams},
        "members": {},
        "inbox": [],
        "inbox_seq": 0,
        "imports": [],
        "jobs": {},
        "staff_searches": {},
        "log": [],
    }


def state(league):
    """The commissioner block, created or migrated on first touch."""
    st = league.__dict__.get("commish")
    if st is None:
        st = league.__dict__["commish"] = _new_state(league)
    migrate(league)
    return st


def migrate(league):
    """Bring an older commissioner block up to SCHEMA. Safe to run every load."""
    st = league.__dict__.get("commish")
    if st is None:
        return
    ver = int(st.get("version", 1))
    # (future schema bumps go here: if ver < 2: ...; ver = 2)
    st["version"] = max(ver, SCHEMA)
    for k, v in _new_state(league).items():
        if k not in st:
            st[k] = v
    for k, v in DEFAULT_SETTINGS.items():
        st["settings"].setdefault(k, v)
    st["settings"]["difficulty"] = "varsity"                 # locked
    schools = {t.school for t in league.teams}
    for s in schools:
        st["teams"].setdefault(s, _team_row())
    for row in st["teams"].values():
        for k, v in _team_row().items():
            row.setdefault(k, v)


def shared(league):
    """Commissioner Mode or an online (LAN) world: programs have human owners whose orders run
    them. The online host keeps the same team registry (league.commish), keyed by player name."""
    return getattr(league, "mode", None) in (MODE, "online")


def allows(league, switch):
    """Is this system allowed to run? Always True outside Commissioner Mode."""
    if getattr(league, "mode", None) != MODE:
        return True
    st = league.__dict__.get("commish")
    if st is None:
        return True
    return bool(st["settings"].get(switch, True))


def log(league, text):
    st = state(league)
    st["log"].append({"cycle": st["cycle"]["n"], "year": league.year, "week": league.week, "text": text})


# ═══ Team registry ══════════════════════════════════════════════════════════

def team_row(league, team):
    st = state(league)
    school = team.school if hasattr(team, "school") else str(team)
    return st["teams"].setdefault(school, _team_row())


def owner(league, team):
    if not shared(league):
        return None
    st = league.__dict__.get("commish")
    if st is None:
        return None
    row = st["teams"].get(team.school)
    return row.get("owner") if row else None


def staff_recruits(league, team):
    """A player team whose member has missed 2+ cycles in a row: the staff works a basic board
    on top of his standing orders until he's back."""
    if not is_player_team(league, team):
        return False
    return int(team_row(league, team).get("missed", 0)) >= 2


def is_player_team(league, team):
    """True when a Discord member (Commissioner Mode) or an online player coaches this program."""
    return owner(league, team) is not None


def player_teams(league):
    return [t for t in league.teams if is_player_team(league, t)]


def cpu_teams(league):
    return [t for t in league.teams if not is_player_team(league, t)]


def team_of(league, member):
    m = (member or "").strip().lower()
    return next((t for t in league.teams if (owner(league, t) or "").lower() == m), None)


def claim(league, team, member):
    """Hand a program to a Discord member. Returns (ok, message)."""
    member = (member or "").strip()
    if not member:
        return False, "No Discord name given."
    other = team_of(league, member)
    if other is not None and other is not team:
        return False, f"{member} already coaches {other.school}."
    row = team_row(league, team)
    prev = row.get("owner")
    st = state(league)
    row.update(owner=member, since=st["cycle"]["n"], last_cycle=None, grace=st["cycle"]["n"] + 1, missed=0, orders={},
               pw=None, salt=None, keys=None, nagged=None)    # a new password is issued at the next export
    if team.coach is not None and not _is_interim(team.coach):
        team.coach.commish_member = member                    # until he chooses a new coach, he coaches as the sitting one
        row["coach_name"] = team.coach.name
    else:
        row["coach_name"] = None
    row["secret"] = secrets.token_hex(16)                    # every owner gets his own signing key
    mem = st["members"].setdefault(member, {"joined": st["cycle"]["n"], "teams": []})
    mem["team"] = team.school
    mem["status"] = "coaching"
    mem["teams"].append((st["cycle"]["n"], team.school))
    if prev and prev != member:
        st["members"].get(prev, {})["team"] = None
    log(league, f"{member} takes over {team.school}" + (f" (was {prev})" if prev and prev != member else "") + ".")
    return True, f"{team.school} is now coached by {member}."


def release(league, team, why="released"):
    row = team_row(league, team)
    prev = row.get("owner")
    if not prev:
        return False, f"{team.school} is already a CPU team."
    st = state(league)
    row.update(owner=None, since=None, orders={}, missed=0, pw=None, salt=None, keys=None, coach_name=None, nagged=None)
    row["secret"] = secrets.token_hex(16)                    # an old code can never sign for the next owner
    c = team.coach
    if c is not None and getattr(c, "commish_member", None) == prev:
        c.commish_member = None                              # he stays on as the CPU's coach
    if prev in st["members"]:
        st["members"][prev]["team"] = None
        st["members"][prev]["status"] = why if why in ("fired", "kicked", "retired") else "free"
    log(league, f"{prev} leaves {team.school} ({why}); it's a CPU team.")
    return True, f"{team.school} is a CPU team again."


# ═══ Cycles and seeding ═════════════════════════════════════════════════════

def cycle_label(league):
    import comm_offseason
    off = comm_offseason.label(league)
    if off:
        return off
    if league.week == 0:
        return f"{league.year} fall camp → Week 1"
    return f"{league.year} {league.week_name(league.week + 1)}"


def fresh_reads(league):
    """Drop the recruiting caches that remember values computed earlier in the week, so what
    happens next depends only on the world, not on what someone (the website exporter, a
    screen) happened to look at first."""
    cyc = getattr(league, "recruiting", None)
    if cyc is not None:
        cyc.pitch_cache.clear()
        cyc.depth_cache.clear()


def seed_cycle(league, n):
    """Every random draw a cycle makes starts from (world, cycle). Re-running a cycle from the
    same save replays it exactly; nothing a cycle does depends on how earlier ones were run."""
    key = f"{league.seed}:commish:{n}"
    league.rng.seed(key)
    random.seed(key)


def advance(league):
    """Run one cycle: the next week, or (after the title game) the whole offseason.
    Phase 7 splits the offseason into its ten cycles. Returns a short summary."""
    st = state(league)
    n = st["cycle"]["n"] + 1
    label = cycle_label(league)
    seed_cycle(league, n)
    fresh_reads(league)
    import comm_offseason
    offseason = comm_offseason.in_offseason(league)
    if not offseason:
        _count_missed(league, n)                              # offseason cycles aren't counted against anyone
        _inactivity(league, n)
    if offseason:
        summary = comm_offseason.run_stage(league)
    else:
        import screens
        before = league.week
        _prepare_week(league)
        screens._sim_week(league)
        games = [g for g in league.schedule.get(league.week, []) if g.played]
        summary = f"{league.week_name(league.week)}: {len(games)} games played."
        if before == league.week:
            summary = "Nothing to play this week."
    st["cycle"]["n"] = n
    st["cycle"]["label"] = label
    st["cycle"]["history"].append({"n": n, "label": label, "year": league.year, "week": league.week,
                                   "summary": summary})
    del st["cycle"]["history"][:-60]
    lost = check_coaches(league)
    if lost:
        summary += f" {len(lost)} player coach{'es' if len(lost) != 1 else ''} lost {'their jobs' if len(lost) != 1 else 'his job'}: see the inbox."
    import orders
    orders.ensure_ids(league)                                # ids the website shows = ids the next import reads
    log(league, f"Cycle {n} ({label}) run. {summary}")
    return summary


def _count_missed(league, n):
    """A player team with no accepted code for this cycle has missed it (counted in a row)."""
    for t in player_teams(league):
        row = team_row(league, t)
        fresh = row.get("last_cycle") == n or row.get("grace") == n      # a new owner's first cycle isn't a miss
        row["missed"] = 0 if fresh else int(row.get("missed", 0)) + 1


def _prepare_week(league):
    """Standing orders that act on Saturday: play-calling, the depth chart, the game plan."""
    import orders
    for t in player_teams(league):
        orders.apply_calls(league, t)
        orders.apply_depth(league, t)
        orders.apply_plan(league, t)


# ═══ The Commissioner Inbox (Phase 1: the container; later phases fill it) ══

def add_inbox(league, kind, text, team=None, options=None, default=None, due=None, acts=None):
    st = state(league)
    st["inbox_seq"] += 1
    item = {"id": f"{kind.upper()}-{league.year}-{st['inbox_seq']:03d}", "kind": kind, "team": getattr(team, "school", team),
            "text": text, "options": list(options or []), "default": default, "due": due, "acts": dict(acts or {}),
            "status": "open", "resolution": None, "cycle": st["cycle"]["n"]}
    st["inbox"].append(item)
    return item


def open_items(league):
    return [m for m in state(league)["inbox"] if m["status"] == "open"]


def resolve(league, item, answer, by="commissioner"):
    """Close an inbox item. Some answers do something (kick an inactive member); the result is returned."""
    item["status"], item["resolution"], item["by"] = "resolved", answer, by
    log(league, f"{item['id']} resolved by {by}: {answer}")
    act = (item.get("acts") or {}).get(answer)
    if act == "kick":
        team = next((t for t in league.teams if t.school == item.get("team")), None)
        if team is not None and is_player_team(league, team):
            _ok, text = release(league, team, "kicked")
            return text
    return ""


def ask(league, kind, text, options, default=0, team=None):
    """A decision for a member that his code didn't answer: asked on the desk while the cycle runs
    (ASK callback), or the default when nobody is at the keyboard. Every one is kept in the inbox."""
    ans = default
    if ASK[0] is not None:
        try:
            got = ASK[0](kind, text, options, default)
            if isinstance(got, int) and 0 <= got < len(options):
                ans = got
        except Exception:                                   # noqa: BLE001 — a broken prompt falls back to the default
            ans = default
    item = add_inbox(league, kind, text, team=team, options=list(options), default=options[default])
    item["status"], item["resolution"], item["by"] = "resolved", options[ans], "commissioner" if ASK[0] else "default"
    return ans


def note(league, kind, text, team=None):
    """A record for the inbox's history that needs no answer."""
    item = add_inbox(league, kind, text, team=team)
    item["status"], item["resolution"], item["by"] = "resolved", "noted", "auto"
    return item


def has_open(league, kind, team):
    school = getattr(team, "school", team)
    return any(m for m in open_items(league) if m["kind"] == kind and m.get("team") == school)


# ═══ Inactivity (Phase 4) ════════════════════════════════════════════════════

INACTIVE_AFTER = 5


def _inactivity(league, n):
    """Five missed cycles in a row: ask the commissioner, and ask again every cycle after."""
    for t in player_teams(league):
        row = team_row(league, t)
        missed = int(row.get("missed", 0))
        if missed < INACTIVE_AFTER or row.get("nagged") == n:
            continue
        for m in open_items(league):                          # last cycle's question is replaced, not stacked
            if m["kind"] == "inactive" and m.get("team") == t.school:
                m["status"], m["resolution"], m["by"] = "superseded", "asked again", "system"
        add_inbox(league, "inactive", f"@{row['owner']} has missed {missed} cycles in a row at {t.school}. "
                  f"Kick him and make {t.school} a CPU team, or keep waiting?", team=t,
                  options=[f"Kick @{row['owner']}: {t.school} goes CPU", "Keep him (ask again next cycle)"],
                  default="keep", acts={f"Kick @{row['owner']}: {t.school} goes CPU": "kick"})
        row["nagged"] = n


# ═══ Coaches for members (Phase 4) ═══════════════════════════════════════════

def _is_interim(c):
    return bool(getattr(c, "interim", None))


def member_coach(league, member):
    """The Coach object a member coaches as (employed, in the pool, or retired), or None."""
    for t in league.teams:
        c = t.coach
        if c is not None and getattr(c, "commish_member", None) == member:
            return c
    for c in list(getattr(league, "coach_pool", [])) + list(getattr(league, "retired_coaches", [])):
        if getattr(c, "commish_member", None) == member:
            return c
    return None


FORM_HELP = ("first name", "last name", "age 30-60", "background 1-6", "offense scheme", "defense scheme",
             "fourth down 1-3", "blitz 1-3")


def new_coach(league, member, first, last, age=38, background="1", offense=None, defense=None, fourth="2", blitz="2"):
    """A coach for a member, built from his Discord form exactly as Coach Career builds yours:
    the background sets his strengths and first trait, then his schemes and his two tendencies."""
    import career
    import carousel as cz
    import playbook as pb
    from league import make_coach
    from models import Team
    random.seed(f"{league.seed}:new-coach:{member}:{state(league)['cycle']['n']}")   # the same form makes the same coach
    bg = str(background) if str(background) in career.BACKGROUNDS else "1"
    label, _blurb, tilt, trait, off_default, def_default = career.BACKGROUNDS[bg]
    off_s = _pick(offense, list(pb.OFFENSE_SCHEMES), off_default)
    def_s = _pick(defense, list(pb.DEFENSE_SCHEMES), def_default)
    age = int(age) if str(age).isdigit() and 30 <= int(age) <= 60 else 38
    shell = Team("—", "—", "—", 0, "—", None, "", {k: 60 for k in Team.RATING_KEYS})
    shell.ratings["coach"] = 60
    coach = make_coach(f"{(first or 'Chris').strip().title()} {(last or 'Walker').strip().title()}", shell)
    for k in coach.ratings:
        coach.ratings[k] = 55
    for k, v in tilt.items():
        coach.ratings[k] = int(max(35, min(90, coach.ratings[k] + v)))
    coach.overall = 60
    coach.offense_scheme, coach.defense_scheme = off_s, def_s
    coach.aggression = career.PHILOSOPHY.get(str(fourth), career.PHILOSOPHY["2"])[1]
    coach.blitz = career.BLITZ.get(str(blitz), career.BLITZ["2"])[1]
    coach.team = None
    coach.traits = [trait]
    cz.init_coach(coach, league.year, origin=f"{label} (@{member})")
    coach.age = age
    coach.ceiling = 96
    coach.personality = "builder"
    coach.retire_age = 99                                     # the member decides when he's done
    coach.background = label
    coach.commish_member = member
    coach.status = "unemployed"
    log(league, f"Coach {coach.name} created for @{member} ({label}, {off_s} / {def_s}).")
    return coach


def _pick(value, names, default):
    v = str(value or "").strip()
    if v.isdigit() and 1 <= int(v) <= len(names):
        return names[int(v) - 1]
    for n in names:
        if v and n.lower() == v.lower():
            return n
    return default


def install(league, team, coach):
    """Put a member's coach in charge of a program now, in season or out. The sitting head coach is let
    go (an interim goes back to his coordinator job)."""
    import carousel as cz
    cur = team.coach
    if cur is coach:
        return
    if cur is not None:
        if _is_interim(cur):
            cz.end_interim(league, team)
        else:
            cz.vacate(league, team, "fired")
            if getattr(cur, "_last_exit", None) is not None:
                cur._last_exit["note"] = "replaced by the commissioner"
    if coach in getattr(league, "coach_pool", []):
        league.coach_pool.remove(coach)
    if coach.team is not None and coach.team is not team and coach.team.coach is coach:
        cz.vacate(league, coach.team, "left")
    cz.hire(league, team, coach, "commissioner")
    if not league.season_complete:
        coach.hired_year = league.year                        # his tenure starts with these games
    team_row(league, team)["coach_name"] = coach.name


def take_over(league, team, member, mode="adopt", form=None):
    """After a claim: who's on the headset. adopt = the sitting coach; new = a coach from the form;
    own = the member's existing coach (say, after a firing). Returns a message."""
    row = team_row(league, team)
    if mode == "own":
        c = member_coach(league, member)
        if c is None or c.status == "retired":
            return f"@{member} has no coach on file; adopted the sitting coach."
        install(league, team, c)
        msg = f"{c.name} takes over {team.school}."
    elif mode == "new":
        c = new_coach(league, member, **(form or {}))
        install(league, team, c)
        msg = f"{c.name} is the new head coach at {team.school}."
    else:
        c = team.coach
        if c is None or _is_interim(c):
            return f"{team.school} has only an interim coach; give @{member} a coach of his own (new or own)."
        msg = f"@{member} coaches {team.school} as {c.name}."
    c.commish_member = member
    row["coach_name"] = c.name
    import recruit_plus as rp
    rp.queue(league.recruiting, team).clear()              # a new member starts from the staff's board, not the last owner's orders
    inherit_board(league, team)
    log(league, msg)
    return msg


def inherit_board(league, team):
    """A new member doesn't start from zero: the CPU staff's board becomes his standing orders
    (a call every week to recruits he's offered, an evaluation for the rest) and both coordinators
    work their side of the board until he changes it."""
    import recruit_plus as rp
    cyc = league.recruiting
    q = rp.queue(cyc, team)
    if q:
        return 0
    board = sorted((r for r in team.recruiting_targets if not r.signed and r.committed_to in (None, team)),
                   key=lambda r: -r.interest.get(team, 0))
    n = 0
    for r in board[:16]:
        if team in r.offers:
            rp.add_order(cyc, team, r, "contact", rule="weekly")
        else:
            rp.add_order(cyc, team, r, "evaluate", rule="once")
        n += 1
    ap = rp.autopilot(cyc, team)
    for side in ("OC", "DC"):
        ap[side]["on"], ap[side]["hours"] = True, 10
    return n


def check_coaches(league):
    """After a cycle: did any member lose his job (fired mid-season or in the offseason, or retired)?
    His program goes CPU and the inbox says so. Returns [(team, member, what)]."""
    import carousel as cz
    lost = []
    for t in player_teams(league):
        row = team_row(league, t)
        member = row["owner"]
        want = row.get("coach_name")
        c = t.coach
        if not want:                                         # claimed before Phase 4: the sitting coach is his
            if c is not None and not _is_interim(c):
                c.commish_member = member
                row["coach_name"] = c.name
            continue
        if c is not None and c.name == want and not _is_interim(c):
            continue
        mine = member_coach(league, member)
        if mine is not None and mine.status == "retired":
            what = "retired"
        elif mine is not None and mine.team is not None and mine.team is not t:
            what = f"left for {mine.team.school}"
        else:
            what = "fired"
        w, l_ = t.wins, t.losses
        interim = f"{c.name} is the interim" if c is not None and cz.is_interim(c) else (f"{c.name} is the new coach" if c else "the job is open")
        release(league, t, "fired" if what == "fired" else "retired" if what == "retired" else "left")
        add_inbox(league, "fired" if what == "fired" else "vacancy",
                  f"{t.school}'s AD {('fired @' + member) if what == 'fired' else ('@' + member + ' ' + what)} ({w}-{l_}). "
                  f"{t.school} is a CPU team now; {interim}. Hand it to a member with [T] C, and @{member} can claim an open program "
                  f"(he keeps his coach, {want}, if you choose 'his own coach').", team=t, options=["Got it"])
        lost.append((t, member, what))
    return lost


# ═══ Starting a league ══════════════════════════════════════════════════════

def start(league):
    """New Game → Commissioner Mode, after the world is built."""
    league.mode = MODE
    league.user_team = None
    league.user_coach = None
    league.__dict__.pop("hotseat", None)
    state(league)
    import orders
    orders.ensure_ids(league)
    log(league, f"Commissioner league created ({len(league.teams)} programs, all CPU until claimed).")


# ═══ League setup: members from a file (Phase 8) ═══════════════════════════

MEMBER_COLUMNS = ("discord", "school", "first", "last", "age", "background", "offense", "defense", "fourth", "blitz")


def load_members(league, path):
    """Claim programs for a list of members: a CSV (a Discord/Google form export works) with a Discord name
    and a school in each row, and optionally the coach form's answers (first, last, age, background,
    offense, defense, fourth, blitz). With a first and last name the member gets a new coach; without,
    he takes over the sitting one. Returns [(row number, ok, message)]."""
    import csv
    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows:
        return out
    head = [h.strip().lower() for h in rows[0]]

    def col(name):
        for i, h in enumerate(head):
            if h == name or h.startswith(name):
                return i
        return None
    idx = {k: col(k) for k in MEMBER_COLUMNS}
    if idx["discord"] is None or idx["school"] is None:
        idx = {k: i for i, k in enumerate(MEMBER_COLUMNS)}         # no header: columns in the documented order
        data = rows
    else:
        data = rows[1:]
    by_name = {t.school.lower(): t for t in league.teams}
    for n, r in enumerate(data, 2 if data is not rows else 1):
        get = lambda k, r=r: (r[idx[k]].strip() if idx.get(k) is not None and idx[k] < len(r) else "")
        member, school = get("discord").lstrip("@"), get("school")
        if not member or not school:
            continue
        team = by_name.get(school.lower()) or next((t for t in league.teams if school.lower() in t.school.lower()), None)
        if team is None:
            out.append((n, False, f"@{member}: no program called {school}"))
            continue
        if is_player_team(league, team) and owner(league, team) != member:
            out.append((n, False, f"@{member}: {team.school} already belongs to @{owner(league, team)}"))
            continue
        ok, msg = claim(league, team, member)
        if not ok:
            out.append((n, False, msg))
            continue
        if get("first") and get("last"):
            msg = take_over(league, team, member, "new", {k: get(k) for k in ("first", "last", "age", "background",
                                                                           "offense", "defense", "fourth", "blitz")})
        else:
            msg = take_over(league, team, member, "adopt")
        out.append((n, True, msg))
    return out


# ═══ Printable league directory ═════════════════════════════════════════════

def directory_lines(league):
    """Every program, who coaches it, and which are open. Plain text: paste anywhere."""
    out = [f"LEAGUE DIRECTORY — {league.year} · cycle {state(league)['cycle']['n']}", ""]
    confs = {}
    for t in league.teams:
        confs.setdefault(t.conference, []).append(t)
    n_player = len(player_teams(league))
    out.append(f"{n_player} player teams · {len(league.teams) - n_player} open (CPU)")
    for conf in sorted(confs, key=lambda c: (c == "Independent", c)):
        out.append("")
        out.append(conf.upper())
        for t in sorted(confs[conf], key=lambda t: t.school):
            who = owner(league, t)
            out.append(f"  {t.school:<26}{('@' + who) if who else 'OPEN (CPU)'}")
    return out


def write_directory(league, folder=None):
    folder = folder or os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"league_directory_{league.year}_cycle{state(league)['cycle']['n']}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(directory_lines(league)) + "\n")
    return path


# ═══ Snapshots: before/after every import and every cycle ════════════════════

SNAP_DIR = "commissioner_snapshots"
SNAP_KEEP = 24


def _snap_dir():
    import saves
    path = os.path.join(saves.SAVE_DIR, SNAP_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def snapshot(league, label):
    """Write a rollback point. Never stops the league if the disk complains."""
    import pickle
    import re
    import sys
    import time

    import saves
    st = state(league)
    seq = st.setdefault("snap_seq", 0) + 1
    st["snap_seq"] = seq
    slug = re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_")[:60]
    path = os.path.join(_snap_dir(), f"{seq:05d}_{slug}{saves.EXT}")
    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limit, saves.RECURSION_FLOOR))
    try:
        head = saves._header(league, label)
        head["snapshot"] = {"label": label, "cycle": st["cycle"]["n"], "at": time.time(), "league": st["league_id"]}
        with open(path + ".tmp", "wb") as f:
            pickle.dump(head, f, protocol=pickle.HIGHEST_PROTOCOL)
            pickle.dump(league, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(path + ".tmp", path)
    except Exception as e:                                   # noqa: BLE001 — a snapshot is insurance, not a gate
        log(league, f"Snapshot '{label}' failed: {e}")
        return None
    finally:
        sys.setrecursionlimit(limit)
    snaps = sorted(f for f in os.listdir(_snap_dir()) if f.endswith(saves.EXT))
    for old in snaps[:-SNAP_KEEP]:
        try:
            os.remove(os.path.join(_snap_dir(), old))
        except OSError:
            pass
    return path


def list_snapshots(league=None):
    """[(path, label, cycle, saved_at)] newest first; only this league's when a league is given."""
    import saves
    out = []
    for f in sorted(os.listdir(_snap_dir()), reverse=True):
        if not f.endswith(saves.EXT):
            continue
        h = saves.read_header(os.path.join(_snap_dir(), f))
        if not h or "snapshot" not in h:
            continue
        if league is not None and h["snapshot"].get("league") != state(league)["league_id"]:
            continue
        s = h["snapshot"]
        out.append((h["path"], s["label"], s["cycle"], s["at"]))
    return out


# ═══ Website passwords (Phase 3) ═════════════════════════════════════════════

def issue_password(league, team, rotate_secret=False):
    """A new website password for a player team. With rotate_secret, its signing key changes too,
    so codes built with the old login stop working."""
    import sitecrypto
    row = team_row(league, team)
    pw = sitecrypto.new_password()
    salt = sitecrypto.new_salt()
    enc, mac = sitecrypto.derive(pw, salt)
    row.update(pw=pw, salt=salt.hex(), keys=(enc + mac).hex(), pw_cycle=state(league)["cycle"]["n"])
    if rotate_secret:
        row["secret"] = secrets.token_hex(16)
    log(league, f"New website password issued for {team.school}" + (" (signing key rotated)" if rotate_secret else "") + ".")
    return pw


def ensure_passwords(league):
    """Every player team has a password; returns the teams that just got one."""
    fresh = []
    for t in player_teams(league):
        if not team_row(league, t).get("pw"):
            issue_password(league, t)
            fresh.append(t)
    return fresh
