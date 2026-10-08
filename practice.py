"""
practice.py — What practice tells you (Coach Career).

You don't see ratings. You see practice. Every week of the season (and in
fall camp) every player on your roster gets reps, and the reps produce a stat
line — rolled from what he really is, with real randomness, so a backup can
have a fluke week and a starter can have a bad one:

  QB   team period: 15 of 22, 1 INT, 2 sacks · deep shots 1 of 4 · scrambles
  RB   carries and yards · blitz pickups won · fumbles
  WR   one-on-ones won (short and deep) · catches on targets · drops
  TE   blocking reps won · catches · drops
  OL   pass-rush one-on-ones won · run-period reps won
  DL   pass-rush one-on-ones won · sacks · run stuffs
  LB   tackles · tackles for loss · coverage reps · blitz pressures
  CB   one-on-ones won (short and deep) · breakups · INTs
  S    deep balls allowed · breakups · INTs · run-fit tackles
  K    field goals by distance            P  average distance · inside the 20

Your staff writes the rest: two or three sentences built from what each player
actually does well and badly ("Accurate on short throws, but gets rattled when
the pocket collapses. A real threat with his legs."), a word for how good he
looks overall, and which way he's trending.

POSITION BATTLES
  Wherever the last starter and the first backup are close, the report says
  who's holding on and who's pushing — practice performance counts.

THE STAFF'S DEPTH CHART
  Your coordinators recommend a depth chart every week from what they see:
  real ability, blurred by how good your staff is at evaluating, nudged by
  this week's practice. [A] accepts it. A great staff is close to the truth;
  a poor one isn't.

On other teams, you get film instead of practice: the same kind of report on
their key players (the week hub, [O]).
"""
import math
import random

from ui import C, ask, clear, pad, paint, pause, rule, section, title_bar, truncate

GROUPS = [("QB", "Quarterbacks"), ("RB", "Running backs"), ("WR", "Receivers"), ("TE", "Tight ends"),
          ("OL", "Offensive line"), ("DL", "Defensive line"), ("LB", "Linebackers"), ("CB", "Cornerbacks"),
          ("S", "Safeties"), ("K", "Kicker"), ("P", "Punter")]

# (pos, sub): (when he's good at it, when he's bad at it)
PHRASE = {
    ("QB", "short"): ("has been accurate on quick, short throws", "misses too many easy short throws"),
    ("QB", "medium"): ("throws with anticipation over the middle", "is late and off-target in the intermediate game"),
    ("QB", "deep"): ("puts the deep ball right where it needs to be", "can't push the ball downfield with any accuracy"),
    ("QB", "pressure"): ("stays calm with rushers in his face — good pocket awareness",
                         "struggles to get around the pressure and gets rattled when the pocket collapses"),
    ("QB", "dual"): ("is a real threat with his legs", "is a statue when he has to move"),
    ("RB", "inside"): ("runs hard between the tackles and falls forward", "gets stood up in the middle"),
    ("RB", "outside"): ("gets to the edge in a hurry", "doesn't have the burst to turn the corner"),
    ("RB", "receiving"): ("catches it cleanly out of the backfield", "is a liability as a receiver"),
    ("RB", "pass_pro"): ("picks up the blitz and stones it", "whiffs on blitz pickups"),
    ("RB", "security"): ("protects the football", "has had the ball come out too often"),
    ("WR", "short_routes"): ("gets open underneath with sharp breaks", "can't shake press coverage on short routes"),
    ("WR", "deep_routes"): ("stacks corners and wins deep", "doesn't threaten anybody vertically"),
    ("WR", "hands"): ("has strong, reliable hands", "drops too many catchable balls"),
    ("WR", "yac"): ("makes people miss once he has the ball", "goes down at first contact"),
    ("TE", "run_block"): ("moves people in the run game", "gets pushed around as a blocker"),
    ("TE", "routes"): ("finds the soft spots in coverage", "runs sloppy routes"),
    ("TE", "hands"): ("catches everything thrown his way", "has shaky hands"),
    ("TE", "yac"): ("is a load to bring down after the catch", "doesn't create anything after the catch"),
    ("OL", "run_block"): ("drives defenders off the ball", "can't generate push in the run game"),
    ("OL", "pass_pro"): ("anchors well in pass protection", "gets beat in pass protection"),
    ("OL", "space"): ("gets out in space and finds a target", "is lost when he has to pull or climb"),
    ("DL", "pass_rush"): ("wins with quickness and gets home", "doesn't generate much of a pass rush"),
    ("DL", "run_def"): ("holds the point and eats double teams", "gets moved off the ball against the run"),
    ("DL", "pursuit"): ("chases plays down from the backside", "doesn't make plays outside his gap"),
    ("LB", "run_fits"): ("fills the right gap fast", "takes bad angles and overruns plays"),
    ("LB", "blitz"): ("times his blitzes and gets home", "telegraphs the blitz"),
    ("LB", "coverage"): ("carries backs and tight ends in coverage", "is a liability in coverage"),
    ("LB", "tackling"): ("wraps up and finishes", "misses too many tackles"),
    ("CB", "short_cover"): ("sticks to receivers on short routes", "gives up too much underneath"),
    ("CB", "deep_cover"): ("carries receivers deep without panic", "has a tendency to get beat on go routes"),
    ("CB", "ball_skills"): ("has great ball skills — gets his hands on everything", "never turns and finds the ball"),
    ("CB", "tackling"): ("is a physical tackler in run support", "is a sitting duck once the receiver has the ball"),
    ("S", "deep_help"): ("takes great angles over the top", "is late getting over the top"),
    ("S", "man_cover"): ("can match up in man coverage", "gets exposed in man coverage"),
    ("S", "run_support"): ("comes downhill and punishes ball carriers", "shies away from run support"),
    ("S", "ball_skills"): ("has a nose for the football", "drops the interceptions he gets"),
    ("K", "accuracy"): ("is automatic from inside 40", "has been spraying kicks"),
    ("K", "range"): ("has a big leg — 50 isn't a problem", "doesn't have the leg for long kicks"),
    ("P", "distance"): ("booms it", "struggles for distance"),
    ("P", "placement"): ("pins punts inside the 10", "outkicks his coverage"),
}
LOOKS = {"All-American": "Looks like one of the best players in the country.",
         "star": "Looks like a star.", "quality starter": "Looks like a quality starter.",
         "starter": "Looks like a starter.", "rotation player": "Looks like a rotation player.",
         "backup": "Looks like a backup right now.", "developmental": "Still developing.",
         "long shot": "A long way from the field."}


def _logit(x):
    return 1 / (1 + math.exp(-x))


def _base(p):
    from game_sim import build_profile
    return build_profile(p)


def _r(p, key):
    import subprof
    return subprof.ratio(p, key)


# ═══ Practice stats ═════════════════════════════════════════════════════════

def _reps(rank, n):
    """The ones get the most reps; the twos some; everyone else a handful."""
    return n if rank == 0 else max(1, int(n * 0.6)) if rank == 1 else max(1, int(n * 0.3))


def stat_line(p, rank, rng):
    """(text, form) — form is how the week went against his own normal (-2..2)."""
    b = dict(_base(p))
    from traits import mod as trait_mod
    pb = trait_mod(p, "practice", 0.0)
    if pb:
        b = {k: (v + pb * 6 if isinstance(v, (int, float)) else v) for k, v in b.items()}
    pos = p.position
    good = 0.0
    total = 0.0

    def rolls(n, prob):
        nonlocal good, total
        w = sum(1 for _ in range(n) if rng.random() < prob)
        good += w - n * prob
        total += n
        return w
    if pos == "QB":
        n = _reps(rank, 22)
        deep_n = max(1, n // 5)
        short_n = n - deep_n
        acc_s = b["accuracy"] * (_r(p, "short") + _r(p, "medium")) / 2
        acc_d = b["accuracy"] * _r(p, "deep")
        c1 = rolls(short_n, _logit((acc_s - 60) / 12 + 0.55))
        c2 = rolls(deep_n, _logit((acc_d - 66) / 12 - 0.3))
        ints = sum(1 for _ in range(n) if rng.random() < max(0.01, 0.05 - (b["iq"] - 60) / 800))
        sacks = sum(1 for _ in range(max(1, n // 6)) if rng.random() < _logit(-(b["pocket"] * _r(p, "pressure") - 58) / 12 - 0.9))
        good -= ints * 0.8 + sacks * 0.4
        runs = f" · scrambled for {int(rng.gauss(4, 3) * _r(p, 'dual') * 3)} yds" if _r(p, "dual") > 1.04 else ""
        text = f"Team period: {c1 + c2} of {n}, {ints} INT, {sacks} sack{'s' if sacks != 1 else ''} · deep shots {c2} of {deep_n}{runs}"
    elif pos == "RB":
        n = _reps(rank, 12)
        run = (b["elusive"] + b["power"] + b["vision"]) / 3 * (_r(p, "inside") + _r(p, "outside")) / 2
        yds = sum(max(-2, rng.gauss(3.2 + (run - 62) / 7, 3.2)) for _ in range(n))
        good += (yds / n - 3.2) / 2
        total += 1
        pk_n = max(1, _reps(rank, 6))
        pk = rolls(pk_n, _logit((b["pass_block"] * _r(p, "pass_pro") - 52) / 12))
        fum = sum(1 for _ in range(n) if rng.random() < max(0.004, 0.03 - (b["security"] * _r(p, "security") - 60) / 1500))
        good -= fum
        text = f"{n} carries, {int(yds)} yds · won {pk} of {pk_n} blitz pickups" + (f" · {fum} fumble" if fum else "")
    elif pos in ("WR", "TE"):
        n = _reps(rank, 10 if pos == "WR" else 6)
        if pos == "WR":
            s_n = n - n // 3
            w1 = rolls(s_n, _logit((b["route"] * _r(p, "short_routes") - 60) / 12))
            w2 = rolls(n - s_n, _logit((b["speed"] * _r(p, "deep_routes") - 66) / 12))
            first = f"Won {w1} of {s_n} short one-on-ones, {w2} of {n - s_n} deep"
        else:
            bl_n = _reps(rank, 8)
            w1 = rolls(bl_n, _logit((b["block"] * _r(p, "run_block") - 55) / 12))
            first = f"Won {w1} of {bl_n} blocking reps"
        t = _reps(rank, 7 if pos == "WR" else 5)
        catch = b["catch"] * _r(p, "hands")
        c = rolls(t, _logit((catch - 55) / 12 + 0.8))
        drops = sum(1 for _ in range(t - c) if rng.random() < _logit(-(catch - 55) / 10))
        good -= drops * 0.5
        text = f"{first} · {c} catch{'es' if c != 1 else ''} on {t} target{'s' if t != 1 else ''}" + (f", {drops} drop{'s' if drops != 1 else ''}" if drops else "")
    elif pos == "OL":
        n = _reps(rank, 10)
        w = rolls(n, _logit((b["pass_block"] * _r(p, "pass_pro") - 58) / 10 + 0.3))
        rn = _reps(rank, 8)
        wr = rolls(rn, _logit((b["block"] * _r(p, "run_block") - 58) / 10 + 0.2))
        text = f"Won {w} of {n} pass-pro one-on-ones · {wr} of {rn} run-period reps"
    elif pos == "DL":
        n = _reps(rank, 10)
        w = rolls(n, _logit((b["rush"] * _r(p, "pass_rush") - 62) / 10 - 0.3))
        sacks = sum(1 for _ in range(w) if rng.random() < 0.3)
        rn = _reps(rank, 8)
        st = rolls(rn, _logit((b["run_stop"] * _r(p, "run_def") - 60) / 10 - 0.2))
        text = f"Won {w} of {n} pass-rush one-on-ones, {sacks} sack{'s' if sacks != 1 else ''} in team · {st} run stuffs"
    elif pos == "LB":
        n = _reps(rank, 10)
        tk = rolls(n, _logit((b["tackle"] * _r(p, "tackling") + b["fit"] * _r(p, "run_fits") - 118) / 16 + 0.4))
        tfl = sum(1 for _ in range(tk) if rng.random() < 0.15 * _r(p, "run_fits"))
        cv_n = _reps(rank, 6)
        cv = rolls(cv_n, _logit((b["cover"] * _r(p, "coverage") - 58) / 12))
        text = f"{tk} tackles ({tfl} for loss) in team period · won {cv} of {cv_n} coverage reps"
    elif pos in ("CB", "S"):
        n = _reps(rank, 10)
        if pos == "CB":
            s_n = n - n // 3
            w1 = rolls(s_n, _logit((b["cover"] * _r(p, "short_cover") - 60) / 12))
            w2 = rolls(n - s_n, _logit((b["speed"] * _r(p, "deep_cover") - 66) / 12))
            first = f"Won {w1} of {s_n} short one-on-ones, {w2} of {n - s_n} deep"
        else:
            big = sum(1 for _ in range(max(1, n // 3)) if rng.random() < _logit(-(b["cover"] * _r(p, "deep_help") - 58) / 10 - 1.2))
            good -= big * 0.8
            tk = rolls(_reps(rank, 6), _logit((b["tackle"] * _r(p, "run_support") - 58) / 12))
            first = f"{big} deep ball{'s' if big != 1 else ''} allowed · {tk} run-fit tackles"
        pbu = sum(1 for _ in range(n) if rng.random() < 0.08 * _r(p, "ball_skills") * b["playmaker"] / 60)
        ints = sum(1 for _ in range(pbu) if rng.random() < 0.25 * _r(p, "ball_skills"))
        good += pbu * 0.3 + ints * 0.8
        text = f"{first} · {pbu} breakup{'s' if pbu != 1 else ''}" + (f", {ints} INT" if ints else "")
    elif pos == "K":
        out = []
        for lo, hi, n, base in ((20, 39, 6, 1.6), (40, 49, 3, 0.4), (50, 55, 2, -0.9)):
            skill = (b["kick_acc"] * _r(p, "accuracy") - 60) / 12 + (b["kick_power"] * _r(p, "range") - 60) / 14 * (1 if lo >= 40 else 0.3)
            out.append(f"{rolls(n, _logit(skill + base))}/{n} {'50+' if lo == 50 else f'{lo}-{hi}'}")
        text = "Field goals: " + ", ".join(out)
    elif pos == "P":
        n = 8
        avg = sum(rng.gauss(41 + (b["kick_power"] * _r(p, "distance") - 60) * 0.25, 5) for _ in range(n)) / n
        i20 = rolls(3, _logit((b["kick_acc"] * _r(p, "placement") - 60) / 12))
        good += (avg - 41) / 4
        text = f"{n} punts, {avg:.1f} avg · {i20} of 3 inside the 20 on pooch drills"
    else:
        text = "Worked with the scout team."
    form = max(-2.0, min(2.0, good / max(1.5, math.sqrt(max(total, 1))) + pb))
    if rank >= 2 and pos not in ("K", "P"):
        text = "Limited reps: " + text                   # the backups' lines are small samples, and say so
    return text, form


# ═══ The written report ═════════════════════════════════════════════════════

def report(p, seed=0, film=False):
    """Two or three sentences from what he actually does well and badly."""
    import subprof
    import scout
    subs = subprof.all_values(p)
    if not subs:
        return ""
    rng = random.Random(f"rep|{p.name}|{seed}")
    # what stands out is relative to the rest of HIS game, or flat-out great/bad in absolute terms
    off = subprof.offsets(p)
    ranked = sorted(subs, key=lambda x: -off.get(x[0], 0))
    strengths = [(k, v) for k, _, v in ranked if (off.get(k, 0) >= 0.035 and v >= 0.97) or v >= 1.06][:2]
    weaknesses = [(k, v) for k, _, v in reversed(ranked)
                  if ((off.get(k, 0) <= -0.035 and v < 1.03) or v < 0.86) and (k, v) not in strengths][:2]
    bits = []
    s = [PHRASE[(p.position, k)][0] for k, _ in strengths]
    w = [PHRASE[(p.position, k)][1] for k, _ in weaknesses]
    lead = "On film, he " if film else "He "
    if s and w:
        bits.append(f"{lead}{s[0]}, but {w[0]}.")
        extra = (s[1:] + w[1:])
        if extra:
            bits.append(extra[0][0].upper() + extra[0][1:] + ".")
    elif s:
        bits.append(f"{lead}{s[0]}" + (f" and {s[1]}." if len(s) > 1 else "."))
    elif w:
        bits.append(f"{lead}{w[0]}" + (f", and {w[1]}." if len(w) > 1 else "."))
    else:
        bits.append(lead + rng.choice(["does everything at about the same level — no glaring strengths, no holes.",
                                       "is solid across the board without one thing that jumps off the tape.",
                                       "is steady everywhere — nothing special, nothing to hide.",
                                       "doesn't win with one thing, and doesn't lose with one thing either."]))
    bits.append(LOOKS[scout.ovr_word(p.overall)])
    return " ".join(bits)


def trend(p):
    wk = p.__dict__.get("dev_weeks", [])
    if not wk:
        return ("· first look", C.GRAY)                  # camp: no weeks to trend yet
    t = sum(wk[-3:])
    return ("↑ trending up", C.BGREEN) if t >= 0.6 else ("↓ slipping", C.BRED) if t <= -0.2 else ("→ steady", C.GRAY)


# ═══ The week's practice ════════════════════════════════════════════════════

def week_key(league):
    return (league.year, league.week)


def run(league, team):
    """This week's practice for every player (cached: the same week reads the same)."""
    book = team.__dict__.setdefault("_practice", {})
    k = week_key(league)
    if k in book:
        return book[k]
    rng = random.Random(f"practice:{league.seed}:{team.school}:{k}")
    out = {}
    starts = starter_counts(team)
    for pos, _ in GROUPS:
        n1 = starts.get(pos, 1)
        for i, p in enumerate(team.players_at(pos)):
            if getattr(p, "inj_games", 0) > 0:
                out[id(p)] = ("Injured — didn't practice.", 0.0)
                continue
            # rep tier: the starters get the ones' reps, the next group the twos', everyone else a handful
            tier = 0 if i < n1 else 1 if i < 2 * n1 else 2
            out[id(p)] = stat_line(p, tier, rng)
    for old in [x for x in book if x != k]:
        del book[old]
    book[k] = out
    return out


def _staff_eval(team, pos):
    """How sharp your staff's read is (0.6 sloppy .. 1.4 sharp)."""
    import staff
    from models import OFFENSE
    try:
        iq = staff.game_iq(team, "off" if pos in OFFENSE else "def")
    except Exception:
        iq = 65
    import coach_profile
    from traits import mod as trait_mod
    c = team.coach
    eye = (coach_profile.value(c, "evaluation") / max(1, c.overall)) * trait_mod(c, "eye", 1.0) if c else 1.0
    return max(0.6, min(1.4, (iq - 30) / 40 * eye))


def perceived(league, team, p):
    """What your staff thinks he is: the truth, blurred by their eye, nudged by this week's practice."""
    prac = run(league, team).get(id(p), ("", 0.0))
    rng = random.Random(f"eye:{league.seed}:{team.school}:{p.name}:{league.year}:{league.week // 3}")
    blur = 2.0 / _staff_eval(team, p.position)          # a shaky staff misreads by a few points, not a full tier
    try:
        import offseason_cal
        blur *= offseason_cal.read_mult(league, team, p)
    except Exception:
        pass
    blur *= 1 - 0.3 * min(1, max(0, league.week) / 12)   # a season of film sharpens the read
    if getattr(p, "year", 1) >= 3:
        blur *= 0.8                                       # you've known the veterans for years
    hurt = -99 if getattr(p, "inj_games", 0) > 0 else 0
    small = str(prac[0]).startswith("Limited reps")            # a handful of reps is a small sample
    spring = 0.0
    try:
        import spring_cycle
        spring = spring_cycle.spring_form(league, p)
        # Spring tape matters most before Week 1 and fades as current-season film replaces it.
        spring *= max(0.0, 1.0 - max(0, getattr(league, "week", 0)) / 8.0)
    except Exception:
        pass
    return p.overall + rng.gauss(0, blur) + prac[1] * (0.6 if small else 1.6) + spring * 0.9 + hurt


def starter_counts(team):
    """Starters per position in your scheme's base personnel (Smashmouth starts 2 TE, 2 WR)."""
    from models import STARTING_LINEUP
    starts = dict(STARTING_LINEUP)
    try:
        import playbook as pb
        import staff as st
        scheme = st.play_caller(team, "off").offense_scheme
        pers = pb.OFFENSE_SCHEMES.get(scheme, {}).get("personnel", {"11": 1})
        base = max(pers, key=pers.get)
        starts.update(RB=int(base[0]), TE=int(base[1]), WR=5 - int(base[0]) - int(base[1]))
    except Exception:
        pass
    return starts


def recommend(league, team):
    """The staff's depth chart: {pos: [players]}."""
    starts = starter_counts(team)
    out = {}
    for pos, _ in GROUPS:
        room = team.players_at(pos)
        n = starts.get(pos, 1)
        inc = {id(p) for p in room[:n]}                  # the job is theirs to lose: a 2-point edge
        out[pos] = sorted(room, key=lambda p: -(perceived(league, team, p) + (2.0 if id(p) in inc else 0)))
    return out


def battles(league, team):
    """[(pos, starter, challenger, text)] where it's close."""
    prac = run(league, team)
    starts = starter_counts(team)
    out = []
    for pos, _ in GROUPS:
        n = starts.get(pos, 1)
        room = [p for p in team.players_at(pos) if getattr(p, "inj_games", 0) <= 0]
        if len(room) <= n:
            continue
        per = {id(p): perceived(league, team, p) for p in room}
        last = min(room[:n], key=lambda p: per[id(p)])           # the starter on the hottest seat
        nxt = max(room[n:], key=lambda p: per[id(p)])            # the backup closest to the job
        gap = per[id(last)] - per[id(nxt)]
        if gap > 3.5:
            continue
        f1, f2 = prac.get(id(last), ("", 0))[1], prac.get(id(nxt), ("", 0))[1]
        if gap + 2.0 < 0:                                  # the same incumbent's edge the staff chart uses
            txt = f"{nxt.name} has passed {last.last_name} — the staff has him ahead right now."
            if f2 <= -0.8:
                txt += " (On what they've seen all camp — not this week.)"
        elif f2 > f1 + 0.5:
            txt = f"{nxt.name} had the better week. {last.last_name} is still holding on — barely."
        elif f1 > f2 + 0.5:
            txt = f"{last.name} answered the challenge this week. {nxt.last_name} is still close."
        else:
            txt = f"{last.name} and {nxt.name} are neck and neck."
        out.append((pos, last, nxt, txt))
    return out


# ═══ The screen ═════════════════════════════════════════════════════════════

def screen(league, team=None):
    try:
        import guide
        guide.tip(league, "practice")
    except Exception:
        pass
    import scout
    team = team or league.user_team
    msg = ""
    while True:
        clear()
        when = "FALL CAMP" if league.week == 0 else f"WEEK {league.week}"
        print(title_bar(f"PRACTICE REPORT  ·  {team.school.upper()}  ·  {when}"))
        run(league, team)
        print()
        print(section("POSITION BATTLES", C.BYELLOW))
        bs = battles(league, team)
        for pos, a, b, txt in bs:
            print(f"   {paint(pad(pos, 4), C.BCYAN, C.BOLD)}{txt}")
        if not bs:
            print(paint("   No real battles this week — the depth chart is settled.", C.GRAY))
        rec = recommend(league, team)
        prac = run(league, team)
        starts = starter_counts(team)
        changes = []
        for pos, _ in GROUPS:
            n = starts.get(pos, 1)
            cur = [p for p in team.players_at(pos)][:n]
            new = rec[pos][:n]
            outs = [q for q in cur if q not in new]
            for p in new:
                if p not in cur:
                    out = outs.pop(0) if outs else None
                    line = f"{pos}: start {p.name}" + (f" over {out.last_name}" if out else "")
                    if prac.get(id(p), ("", 0))[1] <= -0.8:
                        line += paint("  (a rough week — they like his whole camp)", C.GRAY)
                    changes.append(line)
        print()
        print(section("POSITION ROOMS", C.BCYAN))
        print(paint("   Practice tells you who's coming on. To act on it, open the depth chart: [D] here, or [H] on the team page.", C.GRAY))
        items = [f"{paint(f'[{i}]', C.BYELLOW, C.BOLD)} {label}" for i, (_, label) in enumerate(GROUPS, 1)]
        for row in (items[:6], items[6:]):
            print("   " + "   ".join(row))
        print(rule())
        if msg:
            print(paint("   " + msg, C.BCYAN)); msg = ""
        import webview
        if webview.on():
            try:
                webview.emit("practice", {"school": team.school, "when": when.title(),
                                          "battles": [{"pos": pos, "text": webview.plain(txt)} for pos, a, b, txt in bs],
                                          "groups": [{"key": str(i), "label": label} for i, (_, label) in enumerate(GROUPS, 1)],
                                          "msg": webview.plain(msg)})
            except Exception:
                pass
        c = ask("A position group #, [D] depth chart, Enter = back:").strip().lower()
        if c in ("", "b"):
            return
        if c == "d":
            import screens
            screens.depth_chart(league, team)
            continue
        if c.isdigit() and 1 <= int(c) <= len(GROUPS):
            _room(league, team, GROUPS[int(c) - 1])


def _room(league, team, group):
    import scout
    import textwrap
    pos, label = group
    prac = run(league, team)
    clear()
    print(title_bar(f"{label.upper()}  ·  PRACTICE"))
    for i, p in enumerate(team.players_at(pos)):
        text, form = prac.get(id(p), ("", 0.0))
        tr, tcol = trend(p)
        wk = paint("  good week" if form >= 0.8 else "  rough week" if form <= -0.8 else "", C.BGREEN if form > 0 else C.BRED)
        print()
        print(f"   {paint(f'{i + 1:>2}.', C.GRAY)} {paint(pad(p.name, 22), C.BWHITE, C.BOLD)}{pad(paint(p.class_label, C.GRAY), 8)}"
              f"{pad(scout.ovr(p), 30)} {paint(tr, tcol)}{wk}")
        print(paint(f"       {text}", C.BCYAN))
        for ln in textwrap.wrap(report(p, league.week), 88):
            print(paint(f"       {ln}", C.GRAY))
    import webview
    if webview.on():
        try:
            rows = []
            for i, p in enumerate(team.players_at(pos)):
                text, form = prac.get(id(p), ("", 0.0))
                tr, _ = trend(p)
                rows.append({"i": i + 1, "id": webview.pid(p), "name": p.name, "yr": p.class_label,
                             "ovr": webview.plain(scout.ovr(p)), "trend": webview.plain(tr), "form": round(form, 1),
                             "text": webview.plain(text), "report": webview.plain(report(p, league.week))})
            webview.emit("proom", {"label": label, "rows": rows})
        except Exception:
            pass
    pause()


def film(league, opp, n=8):
    """Opponent film: their best players, in words."""
    import scout
    import textwrap
    clear()
    print(title_bar(f"FILM  ·  {opp.school.upper()}"))
    import playbook as pb
    import staff as sf
    from career import MAN_CALLS, PRESSURE_CALLS, _tempo_word
    oc_, dc_ = sf.play_caller(opp, "off"), sf.play_caller(opp, "def")
    off_s, def_s = oc_.offense_scheme, dc_.defense_scheme
    spec = pb.OFFENSE_SCHEMES.get(off_s, {"run": 0.5, "tempo": 26})
    calls = pb.DEFENSE_SCHEMES.get(def_s, {})
    tot = sum(calls.values()) or 1
    press = sum(v for kk, v in calls.items() if kk in PRESSURE_CALLS) / tot
    man = sum(v for kk, v in calls.items() if kk in MAN_CALLS) / tot
    aggr = sf.aggression(opp, "off")
    print(paint(f"   {opp.school} tendencies ({scout.team(opp.team_ovr)} team)", C.BWHITE, C.BOLD))
    print(paint(f"   Offense  {off_s}: runs about {spec['run'] * 100:.0f}% of the time · {_tempo_word(spec['tempo'])}"
                f" · {'goes for it on fourth down' if aggr >= 65 else 'punts it away' if aggr <= 35 else 'picks its fourth downs'}",
                C.GRAY))
    print(paint(f"   Defense  {def_s}: pressure on about {press * 100:.0f}% of snaps · "
                f"{'man' if man >= 0.5 else 'zone'}-first ({man * 100:.0f}% man)", C.GRAY))
    tips = []
    if spec["run"] >= 0.6:
        tips.append("they'll run it — an extra man in the box")
    elif spec["run"] <= 0.4:
        tips.append("they'll throw it — keep two safeties deep")
    if press >= 0.3:
        tips.append("they bring pressure — quick game and hot routes")
    elif man >= 0.5:
        tips.append("they play man — rub routes and your best receiver on their worst corner")
    else:
        tips.append("they sit in zone — take the underneath stuff and stay patient")
    print(paint("   Staff says: " + "; ".join(tips) + ".", C.BCYAN))
    print()
    print(paint(f"   What the tape says about their best players:\n", C.GRAY))
    starters = [p for grp in opp.starters().values() for p in grp if p.position not in ("K", "P")]
    for p in sorted(starters, key=lambda x: -x.overall)[:n]:
        print(f"   {paint(pad(p.position, 4), C.BCYAN, C.BOLD)}{paint(pad(p.name, 22), C.BWHITE, C.BOLD)}"
              f"{pad(paint(p.class_label, C.GRAY), 8)}{scout.ovr(p)}")
        for ln in textwrap.wrap(report(p, league.week, film=True), 88):
            print(paint(f"       {ln}", C.GRAY))
    pause()
