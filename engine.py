"""
engine.py — Resolves one play, granularly.

Every rating used here is a *composite of applied fundamentals*: the raw
fundamental x the player's proficiency at the position he's playing. A
95-speed receiver with 0.8 WR proficiency runs routes like a 76.

RUNS   point of attack (OL vs DL at the chosen gap, box count, pullers and
       lead blockers) → unblocked / shedding second-level defenders reading
       and fitting their gap → secondary pursuit angles → open-field chase.
       Every tackle records who made it and why.

PASSES protection (every rusher vs his blocker gives a time-to-pressure,
       unblocked blitzers get home fast) → routes (each receiver's route has
       a depth and a break time; separation comes from route running vs the
       defender in man or the zone defender responsible for that area, plus
       scheme matchups) → QB progression (reads in order, read speed from
       IQ, stepping up / sliding / escaping when pressure arrives, throw,
       scramble, throw away, or eat the sack) → throw (accuracy, arm vs depth,
       window, pressure) → catch / breakup / INT → yards after catch.
"""
import weather
import math

import sideline

from playbook import CROSSERS, DOUBLE_MOVES, ROUTE_BEATERS, ROUTES, ZONE_MOD

def _penalty_norm():
    """The average player's penalty multiplier, given how often each trait is dealt."""
    from traits import PLAYER_TRAITS, TRAIT_ODDS
    return 1 + TRAIT_ODDS * sum(fx.get("penalty", 1.0) - 1 for _, _, fx in PLAYER_TRAITS.values())


PENALTY_NORM = _penalty_norm()

OL_LABELS = ("LT", "LG", "C", "RG", "RT")

# ── TUNING ──────────────────────────────────────────────────────────────────
# League-wide knobs, measured over full simulated seasons against real FBS
# averages (per team, per game): ~28 points, ~7.3 yards per pass attempt,
# ~62% completions, ~2.2 sacks, ~6 tackles for loss; single-season leaders
# around 14-16 sacks and 20-25 TFL, 1,800-2,100 rushing yards.
RUN_BASE_MOD = 1.6          # log-odds edge for the blockers at the point of attack
RUN_PENETRATE = 0.5         # when the lineman wins, how often he's in the backfield
TFL_CLEANUP = 0.4            # a penetration stop finished by the next man in
DL_ROTATION = 0.35           # per snap, per spot: a fresh lineman rotates in
RUN_VISION_DIV = 55.0        # vision points per log-odds of slipping a second-level defender
RB_ROTATION = 0.38           # the second back takes the carry
# Compressed field: inside the 10 the defense has less grass to cover, so
# windows shrink and lanes close. Scales from nothing at the 10 to full at the goal.
COMPRESS_ZONE = 10
COMPRESS_PASS = 0.18        # max share of completion chance lost
COMPRESS_RUN = 0.40         # max run-modifier lost (a stacked run front is 0.35)


def _squeeze(sim):
    return max(0, COMPRESS_ZONE - (100 - sim.yardline)) / COMPRESS_ZONE


PASS_DEPTH_PEN = 0.022       # completion log-odds lost per air yard
YAC_FIRST_TACKLE = 1.6       # log-odds the first defender makes the tackle on the catch
YAC_BASE = 0.2               # extra yards after the catch before the first hit (x route.yac)
RUSH_TIME_SLOPE = 0.013       # seconds of protection per point of blocker-vs-rusher edge
RUSH_TIME_NOISE = 0.6
SACK_CLEANUP = 0.35           # the QB is flushed into another rusher, who finishes it
OPEN_FIELD_BASE = 2.1        # log-odds the last man runs him down, speeds equal
SECONDARY_SPEED_DIV = 40.0   # how much a speed edge helps a runner through the last level
SPEED_EDGE_CAP = 12.0        # a runner's speed edge over the last defenders stops counting past this
PILEUP_SHARE = 0.55           # tackles finished (and credited) by whoever else arrives
OPEN_FIELD_SLOPE = 14.0       # speed points per log-odds when the last man chases a runner down
RED_ZONE_SQUEEZE = 0.0       # separation lost when the field shrinks inside the 20
SCREEN_SNIFF = 1.3           # higher = linebackers read screens less often
OPTION_READ_EDGE = 0.6       # log-odds for the blockers when an option read took the point-of-attack man away
DL_LABELS = ("RE", "DT", "NT", "LE")          # RE lines up over the LT


def chance(x):
    if x > 30:
        return 1.0
    if x < -30:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def nm(p):
    return p.last_name


def jn(p):
    return f"#{p.number} {p.last_name}"


class PlayResult:
    def __init__(self, call=None, dcall=None, personnel=None):
        self.call, self.dcall, self.personnel = call, dcall, personnel
        self.kind = call.kind if call else "special"
        self.yards = 0
        self.td = False
        self.safety = False
        self.turnover = None          # "int" | "fumble" | None
        self.return_yards = 0         # after a turnover, from the spot of the change
        self.return_td = False
        self.incomplete = False
        self.out_of_bounds = False
        self.sack = False
        self.duration = 6
        self.lines = []
        self.color = []               # (tag, data) for the color analyst
        self.penalty = None           # (name, team, yards, auto_first_down, replay_down)
        self.flag_option = None       # a flag the other side can accept or decline (sideline.flag_decision)
        self.first_down = False
        self.carrier = self.passer = self.target = self.tackler = None
        self.big = False
        self.complete = False
        # structured detail for the broadcast booth
        self.inc_reason = None        # pbu | drop | over | behind | under | away | low
        self.defender = None          # coverage man on the throw / breakup / pick
        self.pressured = False
        self.scramble = False
        self.air_yards = None
        self.route = None
        self.tackle_why = ""
        self.flag_player = None
        self.missed = []              # defenders the runner made miss
        self.side = None              # run direction
        self.qb_moved = None          # climb | slide | escape
        self.contested = False
        self.option = None            # option plays: "give" | "keep" | "pitch" (what the QB did with it)
        self.read = None              # "checkdown" | "progression" | "rpo_throw" | "rpo_give": the QB's decision
        self.first_look = None        # (receiver, route, defender) on the first read he came off
        self.read_key = None          # RPO: the conflict defender he read

    def say(self, text):
        self.lines.append(text)


# ═══ Lineups ════════════════════════════════════════════════════════════════

def _depth(sim, team):
    return sim.lineup_depth(team)


def offense_lineup(sim, team, personnel, play=None):
    d = _depth(sim, team)
    wr, te, rb = list(d["WR"]), d["TE"], list(d["RB"])
    rng = sim.rng
    if not sim.resting(team):                       # keep legs fresh: backs and slots rotate
        if len(rb) > 1 and rng.random() < RB_ROTATION:
            if personnel in ("21", "22") and len(rb) > 2:
                rb[0], rb[2] = rb[2], rb[0]          # the fullback stays; the second tailback spells the first
            elif personnel in ("10", "11", "12"):
                rb[0], rb[1] = rb[1], rb[0]
        if personnel == "11" and len(wr) > 3 and rng.random() < 0.12:
            wr[2], wr[3] = wr[3], wr[2]
    rb = sideline.feature_rb(sim, team, rb)          # your order: feed him
    L = {"QB": d["QB"][0], "RB": rb[0], "OL": d["OL"][:5], "FB": None}
    if personnel == "10":
        L.update(X=wr[0], Z=wr[1], SLOT=wr[2], Y=wr[3])
    elif personnel == "12":
        L.update(X=wr[0], Z=wr[1], SLOT=te[1], Y=te[0])
    elif personnel == "21":
        L.update(X=wr[0], Z=wr[1], SLOT=rb[1], Y=te[0], FB=rb[1])
    elif personnel == "22":
        L.update(X=wr[0], Z=te[1], SLOT=rb[1], Y=te[0], FB=rb[1])
    else:
        L.update(X=wr[0], Z=wr[1], SLOT=wr[2], Y=te[0])
    labels = {id(p): OL_LABELS[i] for i, p in enumerate(L["OL"])}
    for role in ("X", "Z", "SLOT", "Y"):
        labels.setdefault(id(L[role]), L[role].position)
    labels[id(L["QB"])] = "QB"
    labels[id(L["RB"])] = "RB"
    if L["FB"] is not None:
        labels[id(L["FB"])] = "FB"
    L["label"] = labels
    try:
        import formation_subs
        L = formation_subs.apply_lineup(team, L, personnel, getattr(play, "name", None))
    except Exception:
        pass
    return L


def defense_lineup(sim, team, personnel):
    d = _depth(sim, team)
    rng = sim.rng
    dl = list(d["DL"][:4])
    if not sim.resting(team) and len(d["DL"]) > 4:  # the D-line rotates in waves
        subs = list(d["DL"][4:7])
        for i in range(4):
            if subs and rng.random() < DL_ROTATION:
                dl[i] = subs.pop(0)
    lbs = list(d["LB"])
    if len(lbs) > 3 and rng.random() < 0.08:
        lbs[2], lbs[3] = lbs[3], lbs[2]
    d = dict(d, LB=lbs)
    D = {"DL": dl, "S": d["S"][:2]}
    if personnel == "nickel":
        D["LB"], D["CB"] = d["LB"][:2], d["CB"][:3]
        lb_labels = ("MIKE", "WILL")
    elif personnel == "dime":
        D["LB"], D["CB"] = d["LB"][:1], d["CB"][:4]
        lb_labels = ("MIKE",)
    else:
        D["LB"], D["CB"] = d["LB"][:3], d["CB"][:2]
        lb_labels = ("WILL", "MIKE", "SAM")
    labels = {}
    for i, p in enumerate(D["DL"]):
        labels[id(p)] = DL_LABELS[i]
    for i, p in enumerate(D["LB"]):
        labels[id(p)] = lb_labels[i]
    for i, p in enumerate(D["CB"]):
        labels[id(p)] = ("CB", "CB", "NICKEL", "DIME")[i]
    labels[id(D["S"][0])] = "FS"
    labels[id(D["S"][1])] = "SS"
    D["label"] = labels
    D["NB"] = D["CB"][2] if len(D["CB"]) > 2 else None
    D["FS"], D["SS"] = D["S"][0], D["S"][1]
    return D


def lab(L, p):
    return f"{L['label'].get(id(p), p.position)} {p.last_name}"


# ═══ Entry point ═══════════════════════════════════════════════════════════

def resolve(sim, call, personnel, dcall):
    rng = sim.rng
    sim._ctx = None                                   # the play sets its moment (sub-proficiencies)
    call, dcall = sideline.adjust(sim, call, dcall)  # standing orders from the sideline
    O = offense_lineup(sim, sim.offense, personnel, call)
    D = defense_lineup(sim, sim.defense, dcall.personnel)
    # Every player actually on the field gets a snap. Besides making participation
    # accurate for redshirts, this is how in-season role promises are measured.
    seen = set()
    for value in list(O.values()) + list(D.values()):
        players = value if isinstance(value, list) else [value]
        for p in players:
            if p is not None and hasattr(p, "position") and id(p) not in seen:
                seen.add(id(p)); sim.stat(p, "snaps")
    r = PlayResult(call, dcall, personnel)

    if call.kind == "kneel":
        r.yards, r.duration = -1, 3
        r.say(f"{nm(O['QB'])} takes the knee.")
        r.carrier = O["QB"]
        sim.stat(O["QB"], "rush_att")
        sim.stat(O["QB"], "rush_yds", -1)
        return r

    # Pre-snap flags.
    roll = rng.random()
    from traits import mod as trait_mod
    crowd = (sim.momentum.false_start_bump(sim.offense) + sideline.crowd_bump(sim)) \
        * trait_mod(sim.offense.coach, "discipline")
    o_line = O["OL"] + [O["Y"]]
    # Hotheads jump; the disciplined don't. Divided by the league-wide average so
    # traits move flags between players and teams without adding flags overall.
    o_flags = sum(trait_mod(p, "penalty") for p in o_line) / len(o_line) / PENALTY_NORM
    d_flags = sum(trait_mod(p, "penalty") for p in D["DL"]) / max(1, len(D["DL"])) / PENALTY_NORM
    if roll < 0.03 * o_flags + crowd:
        bad = rng.choices(o_line, weights=[trait_mod(p, "penalty") for p in o_line])[0]
        r.kind = "penalty"
        r.penalty = ("False Start", sim.offense, -5, False, True)
        r.flag_player = bad
        r.duration = 0
        r.say(f"Flag before the snap — false start, {lab(O, bad)}.")
        return r
    if roll < 0.03 * o_flags + 0.018 * d_flags + crowd:
        bad = rng.choices(D["DL"], weights=[trait_mod(p, "penalty") for p in D["DL"]])[0]
        r.kind = "penalty"
        r.penalty = ("Offside", sim.defense, 5, False, True)
        r.flag_player = bad
        r.duration = 0
        r.say(f"Flag — {lab(D, bad)} jumped. Offside, defense.")
        return r

    sim.touch(rng.choice(O["OL"]), 0.22)            # trench wear
    sim.touch(rng.choice(D["DL"]), 0.22)
    holding = rng.random() < 0.045 * sum(trait_mod(p, "penalty") for p in O["OL"]) / len(O["OL"]) / PENALTY_NORM
    if call.kind == "run":
        run_play(sim, O, D, call, dcall, r)
    elif call.rpo:
        rpo_play(sim, O, D, call, dcall, r)
    else:
        pass_play(sim, O, D, call, dcall, r)

    if holding and not r.turnover and not r.sack and r.yards > 2:
        bad = rng.choices(O["OL"], weights=[trait_mod(p, "penalty") for p in O["OL"]])[0]
        r.say(f"But there's a flag — holding on {lab(O, bad)}. That wipes it out.")
        sim.discard_stats()
        r.kind = "penalty"
        r.td = False
        r.penalty = ("Holding", sim.offense, -10, False, True)
        r.flag_player = bad
        r.color.append(("holding", {"blocker": bad}))
    elif holding and not r.turnover and not r.td and not r.safety and r.kind != "penalty" and rng.random() < 0.2:
        # Holding on a play that went nowhere: the defense can take the yards or the down.
        bad = rng.choices(O["OL"], weights=[trait_mod(p, "penalty") for p in O["OL"]])[0]
        r.flag_option = ("Holding", sim.offense, -10, False, True, bad)
    elif r.kind == "pass" and not r.turnover and not r.td and not r.sack and not r.penalty \
            and rng.random() < 0.008 * d_flags:
        # Defensive holding downfield: the offense takes the play or ten yards and a first down.
        bad = r.defender if r.defender is not None else rng.choice(D["CB"])
        r.flag_option = ("Defensive Holding", sim.defense, 10, True, False, bad)
    return r


# ═══ Run game ═══════════════════════════════════════════════════════════════

MISDIRECTION = {"counter": 0.8, "draw": 0.8, "jet": 0.7, "triple": 0.9, "zone_read": 0.3, "trap": 0.5,
               "reverse": 1.2, "speed_option": 0.4, "midline": 0.6, "qb_draw": 0.8, "crack_toss": 0.3}


def _gap_setup(O, D, gap, side):
    """Blockers and the defensive lineman at the point of attack."""
    OL, DL = O["OL"], D["DL"]
    lt, lg, c, rg, rt = OL
    if side == "left":
        if gap == "A":
            return [lg, c], DL[1], "A"
        if gap == "B":
            return [lt, lg], DL[1], "B"
        return [lt], DL[0], "C"
    if gap == "A":
        return [c, rg], DL[2], "A"
    if gap == "B":
        return [rg, rt], DL[2], "B"
    return [rt], DL[3], "C"


def run_play(sim, O, D, call, dcall, r):
    rng = sim.rng
    sim._ctx = "run_in"
    concept = call.concept
    qb, rb = O["QB"], O["RB"]
    side = rng.choice(("left", "right"))
    r.duration = rng.randint(5, 7)

    if concept == "qb_sneak":
        return qb_sneak(sim, O, D, r)
    if concept == "triple":
        return triple_option(sim, O, D, dcall, r, side)

    carrier, removed = rb, set()
    gap = {"inside_zone": rng.choice("AB"), "power": "B", "counter": "B", "iso": "A", "draw": rng.choice("AB"),
           "qb_power": rng.choice("BC"), "zone_read": "B", "duo": "A", "trap": "A", "midline": "A",
           "qb_draw": rng.choice("AB")}.get(concept, "edge")
    lead = None
    bonus = 0.0

    if concept == "zone_read":
        carrier, gap, removed, stop = zone_read(sim, O, D, r, side)
        if stop:
            return
    elif concept == "qb_power":
        carrier = qb
        r.say(f"{nm(qb)} keeps it on QB power, {nm(rb)} leading the way {side}.")
        lead = rb
    elif concept == "jet":
        carrier = O["SLOT"]
        r.say(f"Jet motion — {nm(carrier)} takes the handoff at full speed going {side}.")
    elif concept == "power":
        puller = O["OL"][3] if side == "left" else O["OL"][1]
        lead = puller
        r.say(f"Power {side} — {lab(O, puller)} pulls to lead through the hole.")
    elif concept == "counter":
        side = "right" if side == "left" else "left"
        lead = O["OL"][1] if side == "right" else O["OL"][3]
        r.say(f"Counter — {nm(rb)} jab-steps away, then cuts back {side} behind the pulling {lab(O, lead)}.")
    elif concept == "iso":
        lead = O["FB"]
        r.say(f"Iso — fullback {nm(lead)} leads up the middle for {nm(rb)}.")
    elif concept == "draw":
        r.say(f"{nm(qb)} shows pass... it's a draw to {nm(rb)}!")
    elif concept == "toss":
        r.say(f"Toss {side} to {nm(rb)}, trying to get to the edge.")
    elif concept == "outside_zone":
        r.say(f"Outside zone {side} — {nm(rb)} presses the edge.")
    elif concept == "duo":
        bonus = 0.25
        r.say(f"Duo — double teams all across the front, {nm(rb)} reading the Mike.")
    elif concept == "trap":
        trapper = O["OL"][1] if side == "right" else O["OL"][3]
        if rng.random() < 0.12:
            bonus = -0.8
            r.say(f"Trap — but {lab(O, trapper)} can't find the man he's supposed to kick out!")
        else:
            bonus = 0.5 if (dcall.rush >= 5 or "run" in dcall.tags) else 0.15
            r.say(f"Trap — {lab(O, trapper)} pulls and kicks out the tackle, {nm(rb)} hits it downhill.")
    elif concept == "pin_pull":
        lead = O["OL"][1] if side == "left" else O["OL"][3]
        r.say(f"Pin-and-pull sweep {side} — {lab(O, lead)} leads around the corner.")
    elif concept == "speed_option":
        carrier, gap, removed, stop = speed_option(sim, O, D, r, side)
        if stop:
            return
    elif concept == "midline":
        carrier, gap, removed, stop = midline(sim, O, D, r, side)
        if stop:
            return
    elif concept == "qb_draw":
        carrier = qb
        bonus = 0.5 if (dcall.rush >= 5 or dcall.coverage == "man") else 0.0
        r.say(f"{nm(qb)} drops like it's a pass... QB draw! He takes off up the middle.")
    elif concept == "crack_toss":
        cracker = O["SLOT"]
        target = D["SS"] if dcall.box >= 7 else (D["LB"][-1] if D["LB"] else D["SS"])
        r.say(f"Crack toss {side} — {nm(cracker)} comes down to crack {lab(D, target)}.")
        if rng.random() < chance((sim.prof(cracker)["strength"] - sim.prof(target)["fit"]) / 22 + 0.6):
            removed.add(target)
            r.say(f"{nm(cracker)} seals him inside!")
    elif concept == "reverse":
        carrier = O["Z"]
        side = "right" if side == "left" else "left"
        home = D["DL"][0] if side == "left" else D["DL"][3]
        r.say(f"Handoff to {nm(rb)}... he gives it to {nm(carrier)} coming back — REVERSE {side}!")
        if rng.random() < 0.3:
            r.color.append(("trick_busted", {"def": home}))
            return _finish_tackle(sim, O, D, r, carrier, home, -rng.uniform(3, 9),
                                  f"{jn(home)} stayed home on the backside and smelled out the reverse")
        r.color.append(("trick", {"play": "reverse"}))
        bonus = 0.4
    else:
        r.say(f"Handoff to {nm(rb)} on inside zone.")

    bonus += sideline.run_bonus(sim, concept, carrier)      # orders and the game plan
    ball_carrier(sim, O, D, dcall, r, carrier, concept, gap, side, lead=lead, removed=removed, bonus=bonus)


def speed_option(sim, O, D, r, side):
    rng = sim.rng
    qb, rb = O["QB"], O["RB"]
    key = D["DL"][0] if side == "left" else D["DL"][3]
    r.say(f"Speed option {side} — {nm(qb)} attacks the edge with {nm(rb)} trailing for the pitch.")
    on_qb = rng.random() < 0.5
    right = rng.random() < chance((sim.prof(qb)["iq"] - 55) / 22 + 1.3)
    pitch = on_qb if right else not on_qb
    if pitch:
        if rng.random() < 0.025 * weather.fumble_mult(sim, sim.offense):
            r.say("The pitch is on the ground!")
            _fumble(sim, O, D, r, rb, key, rng.uniform(-5, -1), forced=False)
            r.carrier = rb
            sim.stat(rb, "rush_att")
            sim.stat(rb, "rush_yds", r.yards)            # the box score has to match the team total
            return rb, None, set(), True
        r.option = "pitch"
        r.say(f"{lab(D, key)} {'takes the quarterback' if on_qb else 'hesitates'} — pitch to {nm(rb)}!")
        return rb, "edge", {key}, False
    r.option = "keep"
    if on_qb:
        r.say(f"{nm(qb)} keeps it — but {lab(D, key)} was waiting for him!")
        return_gain = rng.uniform(-3, 1.5)
        if _tackle_attempt(sim, key, qb, 1.2):
            _finish_tackle(sim, O, D, r, qb, key, return_gain, f"{jn(key)} played the quarterback all the way")
            return qb, None, set(), True
        return qb, "C", {key}, False
    r.say(f"{lab(D, key)} widens for the pitch — {nm(qb)} turns it up himself!")
    return qb, "C", {key}, False


def midline(sim, O, D, r, side):
    """Midline: the QB rides the B-back (fullback) straight up the A-gap and reads
    the tackle over the guard. Give or keep — there is no pitch on a midline."""
    rng = sim.rng
    qb, back = O["QB"], O["FB"] or O["RB"]
    key = D["DL"][1] if side == "left" else D["DL"][2]
    r.say(f"Midline — {nm(qb)} rides {nm(back)} and reads {lab(D, key)} right over the ball...")
    squeeze = rng.random() < 0.5
    right = rng.random() < chance((sim.prof(qb)["iq"] - 50) / 22 + 1.5)
    keep = squeeze if right else not squeeze
    if keep:
        r.option = "keep"
        r.say(f"...{'pulls it as the tackle squeezes' if squeeze else 'keeps it'}, {nm(qb)} up the gut!")
        return qb, "B", ({key} if squeeze else set()), False
    r.option = "give"
    r.say(f"...gives to {nm(back)} on the dive!")
    return back, "A", ({key} if not squeeze else set()), False


def zone_read(sim, O, D, r, side):
    rng = sim.rng
    qb, rb = O["QB"], O["RB"]
    read = D["DL"][0] if side == "right" else D["DL"][3]     # backside end is left unblocked
    crash = rng.random() < 0.5 + (sim.prof(read)["iq"] - 60) / 250
    correct = rng.random() < chance((sim.prof(qb)["iq"] - 55) / 22 + 1.4)
    keep = crash if correct else not crash
    r.option = "keep" if keep else "give"
    rlab = lab(D, read)
    if keep and crash:
        r.say(f"Zone read — {rlab} crashes on the dive, {nm(qb)} pulls it and bounces outside!")
        r.color.append(("read_right", {"qb": qb, "read": read}))
        return qb, "edge", {read}, False
    if not keep and not crash:
        r.say(f"Zone read — {rlab} sits on the quarterback, so {nm(qb)} gives to {nm(rb)} inside.")
        return rb, "B", {read}, False
    carrier = qb if keep else rb
    r.say(f"Zone read — {nm(qb)} {'keeps' if keep else 'gives'}... but {rlab} {'stayed home' if keep else 'crashed down'}!")
    r.color.append(("read_wrong", {"qb": qb, "read": read}))
    gain = rng.uniform(-2, 1.5)
    if _tackle_attempt(sim, read, carrier, 1.2):
        _finish_tackle(sim, O, D, r, carrier, read, gain,
                       f"{jn(read)} was the read man and made the QB pay for the wrong decision")
        return carrier, None, set(), True
    r.say(f"{nm(carrier)} slips out of {nm(read)}'s grasp!")
    return carrier, "edge" if keep else "B", {read}, False


def qb_sneak(sim, O, D, r):
    rng = sim.rng
    qb = O["QB"]
    ol = sum(sim.prof(p)["block"] for p in O["OL"][1:4]) / 3
    dl = sum(sim.prof(p)["run_stop"] for p in D["DL"][1:3]) / 2
    gain = rng.gauss(1.4 + (ol - dl) / 25 + (sim.prof(qb)["strength"] - 60) / 50, 1.1)
    gain = max(-1.0, min(5.0, gain))
    tackler = rng.choice(D["DL"][1:3] + D["LB"][:1])
    r.say(f"{nm(qb)} takes the snap and plunges forward on the sneak.")
    reason = ("met him in the pile" if gain < 1 else "finally stopped the push")
    _finish_tackle(sim, O, D, r, qb, tackler, gain, f"{jn(tackler)} {reason}")


def triple_option(sim, O, D, dcall, r, side):
    rng = sim.rng
    qb, fb, rb = O["QB"], O["FB"] or O["RB"], O["RB"]
    iq = sim.prof(qb)["iq"]
    dive_key = D["DL"][0] if side == "left" else D["DL"][3]
    pitch_key = D["SS"] if dcall.box >= 8 else (D["LB"][-1] if D["LB"] else D["SS"])
    r.say(f"Triple option {side}. {nm(qb)} rides the fullback {nm(fb)}, reading {lab(D, dive_key)}...")
    de_takes_dive = rng.random() < 0.5
    right_read = rng.random() < chance((iq - 50) / 22 + 1.6)
    give = (not de_takes_dive) if right_read else de_takes_dive
    if give:
        r.option = "give"
        r.say(f"...and gives. {nm(fb)} hits the dive.")
        removed = set() if de_takes_dive else {dive_key}
        return ball_carrier(sim, O, D, dcall, r, fb, "triple", "A", side, removed=removed)
    r.say(f"...pulls it! {lab(D, dive_key)} bit on the dive. {nm(qb)} attacks the pitch key, {lab(D, pitch_key)}.")
    key_on_qb = rng.random() < 0.5
    right_read = rng.random() < chance((iq - 50) / 22 + 1.4)
    pitch = key_on_qb if right_read else not key_on_qb
    if pitch:
        if rng.random() < 0.02 * weather.fumble_mult(sim, sim.offense):
            r.say(f"He pitches — it's on the ground! Loose ball!")
            _fumble(sim, O, D, r, rb, pitch_key, rng.uniform(-4, 0), forced=False)
            r.carrier = rb
            sim.stat(rb, "rush_att")
            sim.stat(rb, "rush_yds", r.yards)
            return
        r.option = "pitch"
        r.say(f"Pitch to {nm(rb)} on the perimeter!")
        return ball_carrier(sim, O, D, dcall, r, rb, "triple", "edge", side, removed={dive_key, pitch_key})
    r.option = "keep"
    return ball_carrier(sim, O, D, dcall, r, qb, "triple", "edge", side, removed={dive_key})


def _elusive_blend(sim, carrier):
    p = sim.prof(carrier)
    return p["elusive"] * 0.6 + p["power"] * 0.4


def _tackle_attempt(sim, tackler, carrier, base, extra=0.0):
    x = (sim.prof(tackler)["tackle"] - _elusive_blend(sim, carrier)) / 22 + base + extra
    return sim.rng.random() < chance(x)


def ball_carrier(sim, O, D, dcall, r, carrier, concept, gap, side, lead=None, removed=frozenset(), bonus=0.0):
    """Runs the ball carrier through the trenches, the second level and the secondary."""
    rng = sim.rng
    r.side = side
    edge = gap in ("edge", "C")
    sim._ctx = "run_out" if edge else "run_in"        # inside or outside run: the sub-proficiencies that apply
    P = sim.prof
    cp = P(carrier)
    gap_label = "edge" if gap == "edge" else f"{gap}-gap"

    blockers, dl, gap_letter = _gap_setup(O, D, "C" if gap == "edge" else gap, side)
    te_blocks = O["Y"].position == "TE"
    if edge and te_blocks:
        blockers = blockers + [O["Y"]]

    # Box math.
    box = list(D["DL"]) + list(D["LB"])
    for extra in (D["SS"], D["NB"], D["FS"]):
        if len(box) < dcall.box and extra is not None and extra not in box:
            box.append(extra)
    box = [p for p in box if p not in removed and p is not carrier]
    n_blockers = 5 + (1 if te_blocks else 0) + (1 if O["SLOT"].position == "TE" else 0) \
        + (1 if O["FB"] is not None and O["FB"] is not carrier else 0)
    surplus = n_blockers - len(box)

    mod = RUN_BASE_MOD + max(-1 if 100 - sim.yardline <= 5 else -2, min(1, surplus)) * 0.25
    mod -= COMPRESS_RUN * _squeeze(sim)              # nowhere to hide near the goal line
    if "run" in dcall.tags:
        mod -= 0.35
    if concept in MISDIRECTION and dcall.rush >= 5:
        mod += 0.35
    if concept == "draw" and (dcall.rush >= 5 or dcall.personnel == "dime"):
        mod += 0.6
    if edge:
        mod += (cp["speed"] - P(dl)["speed"]) / 40
    mod += bonus
    foot, speed_k = weather.footing(sim)                        # a sloppy field takes the speed out of it
    mod += foot
    ol_val = sum(P(b)["block"] for b in blockers) / len(blockers) + (6 if len(blockers) >= 2 else 0)

    gain = 0.0
    tackled = False

    # An option read took the man at the point of attack out of the play. The hole
    # isn't free: the scrape linebacker (or the next lineman down) fills it, and the
    # offense has the edge for reading it right. It used to be 2-4.5 free yards,
    # untouched by either roster, and the option out-ran talent every Saturday.
    scrape = None
    if dl in removed:
        scrape = next((p for p in list(D["LB"]) + list(D["DL"])
                       if p not in removed and p is not carrier and p is not dl), None)
        if scrape is not None:
            dl = scrape
            mod += OPTION_READ_EDGE

    # ── Phase 1: point of attack ─────────────────────────────────────────
    if dl in removed:
        gain = rng.uniform(2, 4.5)
    elif rng.random() > chance((ol_val - P(dl)["run_stop"]) / 22 + mod):
        beaten = min(blockers, key=lambda b: P(b)["block"])
        penetrate = rng.random() < (RUN_PENETRATE + (0.2 if "run" in dcall.tags else 0))
        gain = -rng.uniform(1, 4) if penetrate else rng.uniform(-0.5, 2.0)
        if _tackle_attempt(sim, dl, carrier, 1.3 if penetrate else 1.0):
            why = (f"{jn(dl)} knifed past {lab(O, beaten)} and blew it up in the backfield" if penetrate
                   else f"{jn(dl)} shed {lab(O, beaten)}'s block at the {gap_label} and wrapped him up")
            r.color.append(("stuffed_dl", {"dl": dl, "ol": beaten}))
            if penetrate and rng.random() < TFL_CLEANUP:
                # He blew up the play; the next man in finishes it (the lineman still wrecked it).
                mates = [p for p in D["DL"] + D["LB"] if p is not dl and p not in removed]
                if mates:
                    finisher = rng.choice(mates)
                    why = (f"{jn(dl)} knifed past {lab(O, beaten)} and blew it up — "
                           f"{jn(finisher)} cleaned it up in the backfield")
                    return _finish_tackle(sim, O, D, r, carrier, finisher, gain, why)
            return _finish_tackle(sim, O, D, r, carrier, dl, gain, why)
        r.say(f"{lab(D, dl)} gets into the backfield, but {nm(carrier)} spins out of it!")
        r.missed.append(dl)
        sim.stat(dl, "missed_tkl")
        gain = max(gain, 0) + rng.uniform(0.5, 2.5)
    else:
        gain = rng.uniform(0.5, 3.5) if edge else rng.uniform(1.5, 4.0)
        names = " and ".join(lab(O, b) for b in blockers[:2])
        if rng.random() < 0.5:
            r.say(f"{names} win at the point of attack — there's a crease!")

    # ── Phase 2: second level ────────────────────────────────────────────
    second = [p for p in box if p not in D["DL"] and p is not scrape]
    spare = n_blockers - 4 - (1 if lead is not None and lead in O["OL"] else 0)
    climbers = [b for b in O["OL"] if b not in blockers][:max(0, spare)]
    if lead is not None:
        climbers = [lead] + climbers
    free = []
    for i, defender in enumerate(second):
        if i < len(climbers):
            blocker = climbers[i]
            bonus = 0.3 if blocker is lead else 0.1
            if rng.random() > chance((P(blocker)["block"] - P(defender)["fit"]) / 22 + bonus):
                free.append((defender, f"beat {lab(O, blocker)}'s block at the second level"))
        else:
            if len(box) > n_blockers:
                free.append((defender, f"was unblocked — {len(box)} in the box against {n_blockers} blockers"))
            else:
                free.append((defender, "slipped through untouched — nobody climbed to him"))
    rng.shuffle(free)
    if carrier.position == "QB" and "spy" in dcall.tags and D["LB"] and D["LB"][0] not in removed:
        free.insert(0, (D["LB"][0], "was spying the quarterback the whole way"))
    misdirect = MISDIRECTION.get(concept, 0)
    vision = (cp["vision"] - 60) / RUN_VISION_DIV
    for defender, how in free[:2]:
        if rng.random() > chance((P(defender)["fit"] - 55) / 22 + 0.9 - misdirect - vision):
            if rng.random() < 0.55:
                r.say(f"{lab(D, defender)} {'bites on the misdirection' if misdirect else 'overruns the gap'} "
                      f"— {nm(carrier)} cuts behind him.")
            continue
        at = gain + rng.uniform(0.5, 2.5)
        if _tackle_attempt(sim, defender, carrier, 1.5):
            if "unblocked" in how:
                r.color.append(("unblocked", {"def": defender, "box": len(box), "blockers": n_blockers}))
            return _finish_tackle(sim, O, D, r, carrier, defender, at,
                                  f"{jn(defender)} {how} and filled the {gap_label}")
        sim.stat(defender, "missed_tkl")
        r.say(f"{nm(carrier)} makes {lab(D, defender)} miss!")
        r.missed.append(defender)
        gain = at + rng.uniform(1, 3)

    # ── Phase 2b: pursuit — blocked defenders fight off blocks, backside flows ──
    engaged = [p for p in second if p not in [f[0] for f in free]] + [p for p in D["DL"] if p not in removed]
    if engaged:
        chaser = rng.choice(engaged)
        at = gain + rng.uniform(1, 3.5)
        if _tackle_attempt(sim, chaser, carrier, 0.35 + max(0.0, 0.5 - misdirect)):
            how = ("fought off his block and got a hand on him" if chaser in second
                   else "chased it down from the backside")
            return _finish_tackle(sim, O, D, r, carrier, chaser, at, f"{jn(chaser)} {how}")
        gain = at

    # ── Phase 2c: alley — light boxes rotate a DB down to fill ────────────
    if dcall.box <= 6:
        alley = next((p for p in (D["NB"], D["SS"]) if p is not None and p not in box and p not in removed), None)
        if alley is not None:
            at = gain + rng.uniform(1, 3.5)
            if _tackle_attempt(sim, alley, carrier, 1.3):
                return _finish_tackle(sim, O, D, r, carrier, alley, at,
                                      f"{jn(alley)} rotated down from the {dcall.name.lower()} shell and filled the alley")
            sim.stat(alley, "missed_tkl")
            gain = at

    # ── Phase 3: secondary ───────────────────────────────────────────────
    gain = max(gain, 5.0) + rng.uniform(1, 3)
    if edge:
        cb = D["CB"][0] if side == "left" else D["CB"][1]
        secondary = [p for p in (cb, D["SS"], D["FS"]) if p not in box and p not in removed]
    else:
        secondary = [p for p in (D["SS"], D["FS"], D["CB"][0]) if p not in box and p not in removed]
    for s in secondary[:2]:
        speed_edge = min(SPEED_EDGE_CAP, max(0.0, cp["speed"] - P(s)["speed"])) / SECONDARY_SPEED_DIV * speed_k
        if _tackle_attempt(sim, s, carrier, 1.35, -speed_edge):
            at = gain + rng.uniform(0, 4)
            if s.position == "CB":
                why = f"{jn(s)} set the edge and forced him back inside into the tackle"
            else:
                zone = "deep half" if dcall.shell >= 2 else "middle of the field"
                why = f"{jn(s)} came downhill from the {zone} and squared him up"
            if edge and rng.random() < 0.4:
                r.out_of_bounds = True
                why += " — shoved out of bounds"
            return _finish_tackle(sim, O, D, r, carrier, s, at, why)
        sim.stat(s, "missed_tkl")
        r.say(f"{nm(carrier)} runs right through the arm tackle of {lab(D, s)}!")
        r.missed.append(s)
        gain += rng.uniform(3, 7)

    # ── Phase 4: open field ──────────────────────────────────────────────
    gain += rng.uniform(4, 14)
    chasers = [p for p in (D["FS"], D["CB"][0], D["CB"][1]) if p not in removed]
    chaser = max(chasers, key=lambda p: P(p)["speed"])
    ytg = 100 - sim.yardline
    if gain < ytg and rng.random() < chance(max(-SPEED_EDGE_CAP, P(chaser)["speed"] - cp["speed"]) / OPEN_FIELD_SLOPE + OPEN_FIELD_BASE):
        at = min(ytg - 1, gain + rng.uniform(0, 10))
        r.big = True
        return _finish_tackle(sim, O, D, r, carrier, chaser, at,
                              f"{jn(chaser)} ran him down from behind — took a perfect angle")
    r.big = True
    r.color.append(("breakaway", {"carrier": carrier, "blockers": blockers}))
    _finish_run(sim, O, r, carrier, ytg)


def _finish_run(sim, O, r, carrier, gain):
    gain = int(round(gain))
    ytg = 100 - sim.yardline
    if gain >= ytg:
        gain, r.td = ytg, True
    if sim.yardline + gain <= 0:
        r.safety = True
        gain = -sim.yardline
    r.yards = gain
    r.carrier = carrier
    sim.stat(carrier, "rush_att")
    sim.stat(carrier, "rush_yds", gain)
    sim.stat_max(carrier, "rush_long", gain)
    if r.td:
        sim.stat(carrier, "rush_td")
        r.say(f"{nm(carrier)} is gone — nobody's catching him!")


def _finish_tackle(sim, O, D, r, carrier, tackler, gain, why, rushing=True):
    rng = sim.rng
    gain = int(round(gain))
    ytg = 100 - sim.yardline
    if gain >= ytg:
        return _finish_run(sim, O, r, carrier, ytg) if rushing else _finish_catch_td(sim, r, carrier, ytg)
    if sim.yardline + gain <= 0:
        gain = -sim.yardline
        r.safety = True
    # Pile-ups: a lot of tackles are finished by whoever else arrives. Spread the credit
    # so one linebacker doesn't end up with 180 tackles.
    if tackler.position in ("LB", "DL", "S") and gain >= 0 and rng.random() < PILEUP_SHARE:
        near = D["DL"] + D["LB"] + [D["SS"]] if gain < 8 else D["LB"] + list(D["S"]) + list(D["CB"])
        others = [p for p in near if p is not None and p is not tackler]
        if others:
            tackler = rng.choice(others)
    r.yards = gain
    r.carrier = carrier
    r.tackler = tackler
    r.tackle_why = why
    sim.touch(carrier, 1.2 if gain >= 15 else 1.0)
    sim.touch(tackler, 0.8)
    if rushing:
        sim.stat(carrier, "rush_att")
        sim.stat(carrier, "rush_yds", gain)
        sim.stat_max(carrier, "rush_long", gain)
    sim.stat(tackler, "tkl")
    if gain < 0:
        sim.stat(tackler, "tfl")
    r.say(f"Brought down {'for a loss of ' + str(-gain) if gain < 0 else 'after a gain of ' + str(gain) if gain > 0 else 'for no gain'}"
          f" — {why}.")
    fumble_p = 0.008 + max(0, sim.prof(tackler)["strength"] - sim.prof(carrier)["security"]) / 3000
    fumble_p *= weather.fumble_mult(sim, sim.offense)           # a wet ball, a frozen one
    if rng.random() < fumble_p:
        _fumble(sim, O, D, r, carrier, tackler, gain, forced=True)


def _finish_catch_td(sim, r, receiver, ytg):
    r.yards = ytg
    r.td = True
    sim.stat(receiver, "rec_yds", 0)
    r.say(f"{nm(receiver)} walks into the end zone!")


def _fumble(sim, O, D, r, carrier, forcer, gain, forced=True):
    rng = sim.rng
    r.yards = int(round(gain))
    sim.stat(carrier, "fumbles")
    if forced:
        sim.stat(forcer, "ff")
        r.say(f"BALL'S OUT! {jn(forcer)} punches it loose!")
    if rng.random() < 0.55:
        recoverer = rng.choice(D["DL"] + D["LB"] + [forcer])
        sim.stat(recoverer, "fr")
        r.recoverer = recoverer
        r.turnover = "fumble"
        r.say(f"{lab(D, recoverer)} falls on it — {sim.defense.school} ball!")
        r.color.append(("fumble", {"carrier": carrier, "forcer": forcer, "forced": forced}))
    else:
        r.say(f"{nm(carrier)} jumps on his own fumble. Offense keeps it.")


# ═══ Pass game ══════════════════════════════════════════════════════════════

def _rushers(D, dcall):
    if "sim" in dcall.tags and D["LB"]:            # creeper: a linebacker replaces a dropping end
        return list(D["DL"][1:4]) + [D["LB"][-1]]
    rushers = list(D["DL"][:min(4, dcall.rush)])
    need = dcall.rush - len(rushers)
    pool = []
    for b in dcall.blitzers:
        if b == "LB":
            pool += list(D["LB"][::-1])
        elif b == "S":
            pool.append(D["SS"])
        elif b == "NB" and D["NB"] is not None:
            pool.append(D["NB"])
        elif b == "CB":
            pool.append(D["CB"][1])
    for p in pool:
        if need <= 0:
            break
        if p not in rushers:
            rushers.append(p)
            need -= 1
    return rushers


def _protection(sim, O, D, call, dcall, rushers, r):
    """Returns (time_to_pressure, rusher, beaten_blocker_or_None, protectors)."""
    rng = sim.rng
    P = sim.prof
    protectors = list(O["OL"])
    if call.protection >= 6:
        protectors.append(O["RB"])
    if call.protection >= 7 and O["Y"].position == "TE":
        protectors.append(O["Y"])
    ol = O["OL"]
    pairing = {}
    dl = [p for p in rushers if p in D["DL"]]
    order = {0: ol[0], 1: ol[1], 2: ol[2], 3: ol[4]}
    for p in dl:
        pairing[p] = order[D["DL"].index(p)]
    spare = [b for b in protectors if b not in pairing.values()]
    for p in rushers:
        if p not in pairing and spare:
            pairing[p] = spare.pop(0)
    if "sim" in dcall.tags and rng.random() < 0.3:  # protection confusion vs the creeper
        creeper = rushers[-1]
        pairing.pop(creeper, None)
    times = []
    for p in rushers:
        b = pairing.get(p)
        if b is None:
            t = 1.55 + rng.gauss(0, 0.25) - (P(p)["speed"] - 60) * 0.006
            times.append((max(0.9, t), p, None))
            continue
        pb = P(b)["pass_block"] * (0.8 if b.position in ("RB", "TE") else 1.0)
        t = 3.25 + (pb - P(p)["rush"]) * RUSH_TIME_SLOPE + rng.gauss(0, RUSH_TIME_NOISE)
        times.append((max(1.2, t), p, b))
    times.sort(key=lambda x: x[0])
    if spare and times and times[0][2] is not None:          # an extra blocker helps on the quickest rusher
        t, p, b = times[0]
        times[0] = (t + 0.6, p, b)
        times.sort(key=lambda x: x[0])
    if call.play_action:
        times = [(t + 0.25, p, b) for t, p, b in times]
    shift = sideline.pressure_time(sim)                # quick game, pinned ears, the game plan
    t, p, b = times[0]
    return max(0.8, t + shift), p, b, protectors


def _coverage_map(sim, O, D, dcall, runners, rushers):
    """Receiver -> (primary defender, help defender or None)."""
    rng = sim.rng
    cover = [p for p in D["CB"] + D["S"] + D["LB"] if p not in rushers]
    assign = {}
    if dcall.coverage == "man":
        want = {"X": D["CB"][0], "Z": D["CB"][1],
                "SLOT": D["NB"] if D["NB"] is not None else D["SS"],
                "Y": (D["CB"][3] if len(D["CB"]) > 3 else D["SS"]) if D["NB"] is not None else
                     (D["LB"][-1] if D["LB"] else D["SS"]),
                "RB": D["LB"][0] if D["LB"] else D["SS"]}
        if D["NB"] is not None and O["Y"].position == "TE":
            want["Y"] = D["SS"]
        help_def = None
        if dcall.shell >= 1:
            help_def = D["FS"] if D["FS"] not in rushers else None
        for role, rec in runners.items():
            d = want.get(role)
            if d in rushers or d is None:
                assign[role] = (None, help_def)
            else:
                assign[role] = (d, help_def)
        return assign

    zone = dcall.zone
    fs, ss, cb = D["FS"], D["SS"], D["CB"]
    deep = {"cover3": [cb[0], fs, cb[1]], "firezone": [cb[0], fs, cb[1]],
            "cover2": [fs, ss], "tampa2": [fs, ss],
            "cover4": [cb[0], fs, ss, cb[1]], "prevent": [cb[0], fs, ss, cb[1]],
            "cover6": [cb[0], fs, ss], "cover3buzz": [cb[0], fs, cb[1]]}[zone]
    deep = [p for p in deep if p not in rushers]
    under = [p for p in cover if p not in deep]
    if zone == "tampa2" and D["LB"]:
        mike = next((p for p in D["LB"] if D["label"][id(p)] == "MIKE"), D["LB"][0])
        if mike not in rushers:
            deep.insert(1, mike)
            under = [p for p in under if p is not mike]
    outside_under = [p for p in under if p.position == "CB"] or [p for p in under if p in (D["NB"], ss)] or under
    inside_under = [p for p in under if p.position == "LB"] or under
    for role, rec in runners.items():
        route = ROUTES[rec[1]]
        left = role in ("X",)
        if not (deep or under):
            assign[role] = (None, None)                # everybody rushed: he's uncovered
            continue
        if route.area == "deep":
            pool = deep or under
            d = pool[0] if left else (pool[-1] if role == "Z" else pool[len(pool) // 2])
        elif route.area == "mid":
            pool = inside_under or deep
            d = pool[0] if left else pool[-1]
            if len(pool) > 2 and rng.random() < 0.4:
                d = rng.choice(pool)
            if zone in ("cover4", "prevent") and deep:
                d = deep[1] if len(deep) > 2 and not left else d
        elif route.area in ("flat", "behind") or route.sideline:
            pool = outside_under or under or deep
            d = pool[0] if left else pool[-1]
        else:
            pool = inside_under or under or deep
            d = pool[0] if left else pool[-1]
            if len(pool) > 2 and rng.random() < 0.4:
                d = rng.choice(pool)
        assign[role] = (d, None)
    return assign


def _separation(sim, rec, route, defender, help_def, dcall, stacked):
    rng = sim.rng
    P = sim.prof
    import subprof
    area = "deep" if route.area == "deep" else "short" if route.area in ("short", "flat", "behind") else "mid"
    rp = dict(P(rec))
    if rec.position == "WR":                          # short or deep routes (sub-proficiencies)
        m = {"deep": subprof.ratio(rec, "deep_routes"), "short": subprof.ratio(rec, "short_routes")}.get(
            area, (subprof.ratio(rec, "deep_routes") + subprof.ratio(rec, "short_routes")) / 2)
        for k in ("route", "speed", "quick"):
            rp[k] *= m
    if defender is None:
        return 4.0 + rng.uniform(0, 3)            # uncovered — blitzer vacated his man
    dp = dict(P(defender))
    dm = _cover_mult(defender, area)
    for k in ("cover", "speed", "quick"):
        dp[k] *= dm
    if route.area == "deep":
        diff = (rp["speed"] * 0.6 + rp["route"] * 0.4) - (dp["speed"] * 0.6 + dp["cover"] * 0.4)
    elif route.area in ("short", "flat", "behind"):
        diff = (rp["quick"] * 0.5 + rp["route"] * 0.5) - (dp["quick"] * 0.5 + dp["cover"] * 0.5)
    else:
        diff = rp["route"] - dp["cover"]
    sep = 0.5 + diff * 0.03 + rng.gauss(0, 0.9)
    if route.name in DOUBLE_MOVES:
        sep += 1.1 if dcall.coverage == "man" else -0.2
    if dcall.coverage == "man":
        if route.name in CROSSERS:
            sep += 0.6
        if "robber" in dcall.tags and route.area in ("short", "mid"):
            sep -= 0.45                              # the robber sits in the middle and jumps it
        if route.area == "deep":
            sep += {0: 1.3, 1: 0.0, 2: -0.4}[min(2, dcall.shell)]
    else:
        sep += ZONE_MOD[dcall.zone][route.area]
        sep += ROUTE_BEATERS.get((route.name, dcall.zone), 0)
        if stacked:
            sep += 0.8                              # high-low: one defender, two routes
    if help_def is not None and route.area == "deep":
        sep -= 0.5 + (P(help_def)["cover"] * _cover_mult(help_def, "deep") - 60) / 60
    return sep


def _cover_mult(d, area):
    """A defender's coverage on this route, by depth (sub-proficiencies)."""
    import subprof
    if d.position == "CB":
        return {"deep": subprof.ratio(d, "deep_cover"), "short": subprof.ratio(d, "short_cover")}.get(
            area, (subprof.ratio(d, "deep_cover") + subprof.ratio(d, "short_cover")) / 2)
    if d.position == "S":
        return subprof.ratio(d, "deep_help") if area == "deep" else subprof.ratio(d, "man_cover")
    return 1.0


def pass_play(sim, O, D, call, dcall, r, forced_role=None):
    sim._ctx = "pass"                                 # protection, rush, routes, hands (sub-proficiencies)
    return _pass_play(sim, O, D, call, dcall, r, forced_role)


def _pass_play(sim, O, D, call, dcall, r, forced_role=None):
    rng = sim.rng
    P = sim.prof
    qb = O[call.passer]
    qp = P(qb)
    r.passer = qb

    if call.passer == "RB":
        r.say(f"Toss to {nm(qb)} running {rng.choice(('left', 'right'))}... he pulls up — HALFBACK PASS!")
    if call.name == "Flea Flicker":
        r.say(f"Handoff to {nm(O['RB'])}... he pitches it BACK to {nm(O['QB'])} — flea flicker!")
        if rng.random() < 0.02:
            r.say("The pitch back is on the turf!")
            return _fumble(sim, O, D, r, O["QB"], D["DL"][1], -rng.uniform(4, 9), forced=False)

    route_map = call.route_map
    runners = {}
    for role, route_name in route_map.items():
        if role == "RB" and call.protection >= 6:
            continue
        if role == "Y" and call.protection >= 7 and O["Y"].position == "TE":
            continue
        player = O[role]
        if player.position == "RB" and role == "SLOT" and ROUTES[route_name].area in ("deep", "mid"):
            route_name = "flat"                     # fullback leaks to the flat
        runners[role] = (player, route_name)
    if call.screen:
        return screen_play(sim, O, D, call, dcall, r, runners)

    rushers = _rushers(D, dcall)
    t_press, rusher, beaten, protectors = _protection(sim, O, D, call, dcall, rushers, r)
    cmap = _coverage_map(sim, O, D, dcall, runners, rushers)
    counts = {}
    for d, _ in cmap.values():
        if d is not None:
            counts[id(d)] = counts.get(id(d), 0) + 1

    seps = {}
    for role, (rec, route_name) in runners.items():
        route = ROUTES[route_name]
        d, h = cmap[role]
        stacked = d is not None and counts.get(id(d), 0) > 1 and dcall.coverage == "zone"
        seps[role] = _separation(sim, rec, route, d, h, dcall, stacked) + sideline.sep_bonus(sim, rec, route)

    ytg_end = 100 - sim.yardline
    if ytg_end <= 20:                               # compressed field: no room behind the defense
        for role, (rec, route_name) in runners.items():
            seps[role] -= RED_ZONE_SQUEEZE + (0.5 if ROUTES[route_name].area == "deep" else 0)
    if "bracket" in dcall.tags:
        wide = [ro for ro in ("X", "Z") if ro in runners]
        if wide:
            star = max(wide, key=lambda ro: P(runners[ro][0])["route"])
            for ro in seps:
                seps[ro] += -1.2 if ro == star else 0.2
            if rng.random() < 0.3:
                r.say(f"They're bracketing {nm(runners[star][0])} — two defenders on him.")
    if call.name == "Flea Flicker":
        if rng.random() < chance((72 - P(D["FS"])["iq"]) / 15 + 0.5):
            r.say(f"{lab(D, D['FS'])} bit on the run fake!")
            for ro, (rec, route_name) in runners.items():
                if ROUTES[route_name].area == "deep":
                    seps[ro] += 1.6
        r.color.append(("trick", {"play": "flea flicker"}))

    drop = {"quick": 0.9, "normal": 1.5, "deep": 2.0}[call.drop] + (0.45 if call.play_action else 0) \
        + (0.6 if call.trick else 0)
    read_time = max(0.3, 0.62 - (qp["iq"] - 50) * 0.005)
    noise = max(0.25, (85 - qp["iq"]) / 40)
    drop_txt = {"quick": "takes a quick drop", "normal": "drops back", "deep": "takes a deep drop"}[call.drop]
    if call.play_action:
        r.say(f"Play-action fake to {nm(O['RB'])}, {nm(qb)} {'rolls out' if 'Boot' in call.name else 'sets up deep'}...")
    else:
        r.say(f"{nm(qb)} {drop_txt}.")

    unblocked = beaten is None and t_press < 2.0
    if dcall.rush >= 5:
        if unblocked:
            r.say(f"{dcall.rush}-man pressure — {lab(D, rusher)} comes free!")
        else:
            r.say(f"They're sending {dcall.rush}.")

    # Hot read vs an unblocked blitzer.
    progression = [role for role in call.progression if role in runners]
    fed = sideline.feature_role(sim, runners)           # your order: look for him first
    if fed is not None and fed in progression and progression[0] != fed:
        progression = [fed] + [p for p in progression if p != fed]
    need_shift = sideline.read_need(sim)
    if forced_role:
        rec, route_name = runners[forced_role]
        return _throw(sim, O, D, call, dcall, r, qb, forced_role, runners, seps, cmap, False, on_run=False)
    if unblocked and rng.random() < chance((qp["iq"] - 60) / 22 + 0.4):
        quick = min(progression, key=lambda ro: ROUTES[runners[ro][1]].brk)
        progression = [quick] + [p for p in progression if p != quick]
        r.say(f"{nm(qb)} sees it and goes hot —")
        r.color.append(("hot_read", {"qb": qb, "rusher": rusher}))

    t = drop
    pressured, stepped = False, False
    target = None
    for i, role in enumerate(progression):
        rec, route_name = runners[role]
        route = ROUTES[route_name]
        t = max(t + (read_time if i else 0), route.brk)
        if t >= t_press:
            outcome, t_press = _handle_pressure(sim, O, D, r, qb, rusher, beaten, runners, seps, stepped, dcall,
                                                rushers, t_now=t)
            if outcome in ("sack", "scramble", "away", "done"):
                return
            if outcome == "throw":
                target = max(runners, key=lambda ro: seps[ro])
                pressured = True
                break
            stepped = True
        perceived = seps[role] + rng.gauss(0, noise)
        need = 1.25 + need_shift
        if sim.down >= 3 and route.depth < sim.togo - 1 and i < len(progression) - 1:
            need = 2.6
        if perceived >= need:
            target = role
            break
        if i < len(progression) - 1 and rng.random() < 0.35:
            d, _ = cmap[role]
            if d is not None:
                r.say(f"Looks at {nm(rec)} on the {route_name} — {lab(D, d)} is right there.")
    if target is None:
        rb_role = "RB" if "RB" in runners else None
        best = max(runners, key=lambda ro: seps[ro])
        if rb_role and seps[rb_role] > 0.6 and rng.random() < 0.5:
            target = rb_role
            r.say(f"Nothing downfield — checks it down to {nm(O['RB'])}.")
        elif seps[best] > 0.4 and rng.random() < 0.4:
            target = best
            r.say(f"Nobody really open — he tries to fit it in to {nm(runners[best][0])}.")
        else:
            outcome, _ = _handle_pressure(sim, O, D, r, qb, rusher, beaten, runners, seps, True, dcall, rushers,
                                          coverage_sack=not getattr(r, "pressure_seen", False))
            if outcome in ("sack", "scramble", "away", "done"):
                return
            target = max(runners, key=lambda ro: seps[ro])
            pressured = True
    if progression and target != progression[0] and not r.read \
            and ROUTES[runners[progression[0]][1]].area not in ("flat", "behind") \
            and ROUTES[runners[progression[0]][1]].depth > 4:
        first = progression[0]
        frec, froute = runners[first]
        tr = ROUTES[runners[target][1]]
        r.read = "checkdown" if (tr.area in ("flat", "behind") or tr.depth <= 4) else "progression"
        r.first_look = (frec, froute, cmap[first][0])
    _throw(sim, O, D, call, dcall, r, qb, target, runners, seps, cmap, pressured, on_run=False)


def _handle_pressure(sim, O, D, r, qb, rusher, beaten, runners, seps, stepped, dcall, rushers,
                     coverage_sack=False, t_now=0.0):
    """Pocket movement. Returns (outcome, new_time_to_pressure)."""
    rng = sim.rng
    P = sim.prof
    qp, rp = P(qb), P(rusher)
    rl = lab(D, rusher)
    edge = D["label"].get(id(rusher)) in ("RE", "LE")
    if coverage_sack:
        r.say(f"Nobody open... {nm(qb)} holds it, and {rl} finally gets home.")
    elif beaten is not None and not getattr(r, "pressure_seen", False):
        move = rng.choice(("speed rush", "bull rush", "swim move", "spin move", "long-arm"))
        r.say(f"{rl} beats {lab(O, beaten)} with a {move}.")
    elif getattr(r, "pressure_seen", False):
        r.say(f"{rl} is still coming — the pocket collapses.")
    r.pressure_seen = True
    if not stepped:
        p_step = chance((qp["pocket"] - rp["rush"]) / 22 + (0.4 if edge else -0.7))
        if rng.random() < p_step:
            r.say(f"{nm(qb)} {'climbs the pocket' if edge else 'slides away from the pressure'}, eyes still downfield...")
            r.qb_moved = "climb" if edge else "slide"
            return "continue", t_now + rng.uniform(0.6, 1.1)
    best = max(runners, key=lambda ro: seps[ro])
    if not coverage_sack and seps[best] > 0.6 and rng.random() < 0.55:
        return "throw", 99
    if rng.random() < chance((qp["elusive"] - rp["tackle"]) / 22 - 0.2):
        r.say(f"{nm(qb)} escapes {rl}! He's out of the pocket...")
        r.qb_moved = "escape"
        if seps[best] > 1.5 and rng.random() < 0.6:
            return "throw", 99
        lanes = dcall.coverage == "man" or dcall.rush >= 5
        if qp["speed"] >= 55 and (lanes or rng.random() < 0.4):
            scramble(sim, O, D, r, qb, dcall, rushers)
            return "scramble", 99
        if qp["iq"] >= 50:
            r.say(f"Nobody open — he throws it away out of bounds.")
            r.inc_reason = "away"
            sim.stat(qb, "pass_att")
            r.incomplete = True
            r.kind = "pass"
            r.duration = 6
            return "away", 99
        return "throw", 99
    # Under heavy pressure a smart QB eats fewer of them: he throws it away, and more so
    # the more he's been sacked today (a line that's losing every rep changes his clock).
    taken = sim.stats.get(qb, {}).get("sacked", 0) if hasattr(sim, "stats") else 0
    p_away = 0.08 + max(0, qp["iq"] - 50) / 200 + min(0.35, taken * 0.06)
    if not coverage_sack and rng.random() < p_away:
        r.say(f"{nm(qb)} feels it and throws it away before {rl} can get him.")
        r.inc_reason = "away"
        sim.stat(qb, "pass_att")
        r.incomplete = True
        r.kind = "pass"
        r.duration = 5
        return "away", 99
    # Sack.
    loss = rng.uniform(4, 9)
    r.sack = True
    r.kind = "sack"
    r.duration = 6
    gain = -int(round(loss))
    if sim.yardline + gain <= 0:
        gain = -sim.yardline
        r.safety = True
    r.yards = gain
    r.tackler = rusher
    sim.touch(qb, 1.4)
    sim.touch(rusher, 0.4)
    sim.stat(qb, "sacked")
    sim.stat(qb, "rush_att")                           # CAB scoring: a sack is a run for a loss
    sim.stat(qb, "rush_yds", gain)
    mates = [p for p in (rushers or []) if p is not rusher and p is not None]
    flusher = None
    if mates and not coverage_sack and rng.random() < SACK_CLEANUP:
        flusher, rusher = rusher, rng.choice(mates)    # flushed out of the pocket, into someone else
        mates = [p for p in (rushers or []) if p is not rusher and p is not None]
        r.tackler = rusher
    if mates and rng.random() < 0.3:
        mate = rng.choice(mates)                       # two got there together: a split sack
        r.sack_mate = mate                             # the call says so, and the box matches it
        sim.stat(rusher, "sack", 0.5)
        sim.stat(mate, "sack", 0.5)
        sim.stat(rusher, "tfl", 0.5)
        sim.stat(mate, "tfl", 0.5)
    else:
        sim.stat(rusher, "sack")
        sim.stat(rusher, "tfl")
    sim.stat(rusher, "tkl")
    why = ("had all day in coverage — nobody came open" if coverage_sack
           else "came unblocked on the blitz" if beaten is None
           else f"won his rep against {lab(O, beaten)}")
    if flusher is not None:
        r.say(f"SACKED by {jn(rusher)}! Loss of {-gain}. {rl} flushed him right into it.")
    else:
        r.say(f"SACKED by {jn(rusher)}! Loss of {-gain}. {rl.split()[0]} {why}.")
    r.color.append(("sack", {"rusher": rusher, "beaten": beaten, "blitz": dcall.rush >= 5, "coverage": coverage_sack,
                             "flusher": flusher}))
    if rng.random() < 0.08 * weather.fumble_mult(sim, sim.offense):
        _fumble(sim, O, D, r, qb, rusher, gain, forced=True)
    return "sack", 99


def scramble(sim, O, D, r, qb, dcall, rushers):
    rng = sim.rng
    sim._ctx = "scramble"
    P = sim.prof
    r.kind = "run"
    r.scramble = True
    r.duration = 6
    qp = P(qb)
    gain = rng.uniform(1, 5) + (qp["speed"] - 60) / 10
    spies = [p for p in D["LB"] if p not in rushers]
    if spies:
        lb = spies[0]
        backs_turned = dcall.coverage == "man" and "spy" not in dcall.tags
        base = 1.4 if "spy" in dcall.tags else (0.9 if not backs_turned else 0.3)
        if _tackle_attempt(sim, lb, qb, base):
            r.say(f"{nm(qb)} takes off!")
            return _finish_tackle(sim, O, D, r, qb, lb, gain,
                                  f"{jn(lb)} {'turned and ran with him' if backs_turned else 'kept his eyes on the QB from his zone'}")
    gain += rng.uniform(3, 9)
    r.say(f"{nm(qb)} takes off and finds room!")
    if qp["speed"] < 70 and gain > 6 and rng.random() < 0.55:
        r.say(f"He slides down to protect himself.")
        return _finish_run(sim, O, r, qb, gain)
    s = D["SS"]
    if _tackle_attempt(sim, s, qb, 1.0):
        return _finish_tackle(sim, O, D, r, qb, s, gain + rng.uniform(0, 3),
                              f"{jn(s)} came up from the secondary to cut off the scramble")
    r.big = True
    _finish_run(sim, O, r, qb, gain + rng.uniform(4, 16))


# Completion model. A great quarterback throwing to great receivers should land
# in the low-to-mid 70s over a season (the FBS record is about 77%), a bad one in
# the low 50s, and the country as a whole around 62-63%.
# Tuned against real FBS per-team averages (see TUNING below).
PASS_ACC_SCALE = 46.0      # rating points of accuracy per unit of log-odds (higher = flatter)
PASS_CATCH_SCALE = 55.0
PASS_SEP_W = 0.45
PASS_BASE = 0.0
PASS_FLOOR = 0.0
PASS_CEIL = 0.87


def _throw(sim, O, D, call, dcall, r, qb, role, runners, seps, cmap, pressured, on_run):
    rng = sim.rng
    P = sim.prof
    qp = P(qb)
    rec, route_name = runners[role]
    route = ROUTES[route_name]
    sep = seps[role]
    defender, help_def = cmap[role]
    rp = P(rec)
    r.target = rec
    r.kind = "pass"
    r.pressured = pressured
    r.defender = defender
    r.route = route_name
    r.duration = rng.randint(5, 8)
    depth = max(-2, route.depth + int(round(rng.gauss(0, 1.5))))
    r.air_yards = depth

    import subprof
    band = "short" if depth <= 7 else "medium" if depth <= 17 else "deep"      # sub-proficiencies
    arm = qp["arm"] * (subprof.ratio(qb, "deep") if band == "deep" else 1.0)
    arm_need = max(0, depth) * 1.6 + 22
    arm_short = max(0.0, arm_need - arm)
    base_acc = qp["accuracy"] * subprof.ratio(qb, band) * (subprof.ratio(qb, "pressure") if pressured else 1.0) \
        * (subprof.ratio(qb, "dual") ** 0.5 if on_run else 1.0)
    acc = base_acc - (10 if pressured else 0) - (8 if on_run else 0) - arm_short * 0.5
    w_acc, w_catch, w_drop = weather.pass_penalty(sim, sim.offense, depth)   # rain, snow, wind, cold
    acc -= w_acc
    x = ((acc - 62) / PASS_ACC_SCALE + sep * PASS_SEP_W - max(0, depth) * PASS_DEPTH_PEN
         + (rp["catch"] - w_catch - 62) / PASS_CATCH_SCALE + PASS_BASE)
    # Even a perfect read to an open man isn't automatic — tipped balls, drops,
    # throwaways that count as attempts. Real throws top out around 90%.
    p_catch = PASS_FLOOR + (PASS_CEIL - PASS_FLOOR) * chance(x)
    p_catch *= 1 - COMPRESS_PASS * _squeeze(sim)    # tight windows near the goal line
    if call.name == "Hail Mary":                   # jump ball in a crowd at the goal line
        depth = 100 - sim.yardline
        p_catch = 0.09 + max(0.0, rp["catch"] - 65) / 200
        sep = 0.3

    sim.stat(qb, "pass_att")
    sim.stat(rec, "targets")
    throw_txt = rng.choice(("fires", "throws", "lets it go", "delivers"))
    r.say(f"{'Under pressure, ' if pressured else ''}{nm(qb)} {throw_txt} to {nm(rec)} on the {route_name}...")

    if defender is not None:
        sim.stat(defender, "tgt_d")                        # thrown at in coverage
    if rng.random() < p_catch:
        sim.stat(qb, "pass_cmp")
        sim.stat(rec, "rec")
        if defender is not None:
            sim.stat(defender, "cmp_d")
        r.complete = True
        r.contested = sep < 0.6 and depth >= 8
        _yac(sim, O, D, dcall, r, qb, rec, route, defender, help_def, sep, depth)
        return

    r.incomplete = True
    int_p = 0.06 + max(0.0, 1.2 - sep) * 0.08 + (0.05 if pressured else 0) + max(0, 65 - qp["iq"]) * 0.0015
    hawk = help_def if (route.area == "deep" and help_def is not None and rng.random() < 0.5) else defender
    if hawk is not None:
        int_p *= 0.55 + P(hawk)["playmaker"] / 110          # ball skills: the great ones take it away
    int_p = min(int_p, 0.13)
    if hawk is not None and rng.random() < int_p:
        r.incomplete = False
        r.turnover = "int"
        r.yards = 0
        sim.stat(qb, "pass_int")
        sim.stat(hawk, "int")
        ret = max(0, int(rng.gauss(8, 10)))
        r.return_yards = ret
        why = ("jumped the route" if hawk is defender and sep < 0.8 else
               "read the quarterback's eyes and broke on it" if hawk is not defender else
               "was sitting right in the throwing lane")
        r.say(f"INTERCEPTED! {jn(hawk)} {why}!")
        r.defender = hawk
        r.color.append(("int", {"def": hawk, "pressured": pressured, "sep": sep, "dcall": dcall}))
        return
    pbu_p = 0.0
    if defender is not None:
        skill = P(defender)["playmaker"] / 100
        pbu_p = (0.45 + skill * 0.35) if sep < 1.2 else (0.2 + skill * 0.2) if sep < 2.2 else 0.0
    if defender is not None and rng.random() < pbu_p:
        sim.stat(defender, "pbu")
        r.inc_reason = "pbu"
        r.say(f"Incomplete — broken up by {jn(defender)}, who was glued to him.")
    elif sep >= 1.5 and rng.random() < 0.35 * (1.2 - rp["catch"] / 100) * w_drop:
        r.inc_reason = "drop"
        r.say(f"Right in his hands — and he drops it!")
        r.color.append(("drop", {"rec": rec}))
    elif arm_short > 8:
        r.inc_reason = "under"
        r.say(f"Underthrown — didn't have the arm for it. Incomplete.")
    else:
        r.inc_reason = rng.choice(("over", "behind", "over", "fingertips"))
        r.say({"over": "Overthrown. Incomplete.", "behind": "Thrown behind him — incomplete.",
               "fingertips": "Off his fingertips — incomplete."}[r.inc_reason])
    if route.area == "deep" and defender is not None and sep < 1.0 and rng.random() < 0.08:
        r.say(f"Flag on the play — pass interference on {lab(D, defender)}!")
        r.kind = "penalty"
        r.penalty = ("Pass Interference", sim.defense, max(10, depth), True, False)
        r.flag_player = defender
        sim.discard_stats()


def _yac(sim, O, D, dcall, r, qb, rec, route, defender, help_def, sep, depth):
    rng = sim.rng
    sim._ctx = "yac"
    P = sim.prof
    rp = P(rec)
    ytg = 100 - sim.yardline
    if depth >= ytg:
        _complete(sim, r, qb, rec, ytg, td=True)
        r.say(f"CAUGHT in the end zone! {nm(rec)} beat {lab(D, defender) if defender else 'the coverage'}!")
        r.color.append(("td_pass", {"rec": rec, "def": defender, "dcall": dcall, "route": route.name}))
        return
    r.say(f"Caught at {'the line' if depth <= 0 else str(depth) + (' yard' if depth == 1 else ' yards') + ' downfield'}.")
    first = defender or help_def or D["SS"]
    closing = max(0.0, sep)
    yac = 0.0
    if rng.random() < chance((P(first)["tackle"] - rp["elusive"]) / 22 + YAC_FIRST_TACKLE - closing * 0.1):
        yac = (closing * rng.uniform(0.4, 1.8) + rng.uniform(0, YAC_BASE)) * route.yac
        if depth <= 0:
            yac += rng.uniform(0.5, 3.0)             # caught behind the line, already moving downhill
        why = (f"{jn(first)} was in his hip pocket the whole route and made the tackle on the catch" if sep < 1.0
               else f"{jn(first)} drove on the throw from his zone and wrapped him up" if dcall.coverage == "zone"
               else f"{jn(first)} recovered in man coverage and made the tackle")
        return _catch_tackle(sim, O, D, r, qb, rec, depth + yac, first, why, route)
    sim.stat(first, "missed_tkl")
    r.say(f"{nm(rec)} makes {lab(D, first)} miss!")
    r.missed.append(first)
    yac = rng.uniform(2, 6) * route.yac
    pursuit = [p for p in (D["FS"], D["SS"], *D["LB"]) if p is not first]
    second = rng.choices(pursuit, weights=[max(1.0, P(p)["speed"] - 40) for p in pursuit])[0]
    if rng.random() < chance((P(second)["tackle"] - rp["elusive"]) / 22 + 1.7):
        return _catch_tackle(sim, O, D, r, qb, rec, depth + yac + rng.uniform(0, 4), second,
                             f"{jn(second)} rallied from the {'deep middle' if second is D['FS'] else 'second level'} to clean it up", route)
    sim.stat(second, "missed_tkl")
    yac += rng.uniform(5, 18)
    chaser = max((D["FS"], D["CB"][0], D["CB"][1]), key=lambda p: P(p)["speed"])
    total = depth + yac
    r.big = True
    if total < ytg and rng.random() < chance((P(chaser)["speed"] - rp["speed"]) / 7 + 1.0):
        return _catch_tackle(sim, O, D, r, qb, rec, min(ytg - 1, total), chaser,
                             f"{jn(chaser)} chased him down from the other side of the field", route)
    _complete(sim, r, qb, rec, ytg, td=True)
    r.say(f"{nm(rec)} breaks free — he's GONE!")
    r.color.append(("td_pass", {"rec": rec, "def": first, "dcall": dcall, "route": route.name}))


def _catch_tackle(sim, O, D, r, qb, rec, total, tackler, why, route):
    rng = sim.rng
    ytg = 100 - sim.yardline
    total = int(round(total))
    if total >= ytg:
        _complete(sim, r, qb, rec, ytg, td=True)
        r.say(f"{nm(rec)} slips {nm(tackler)}'s tackle and gets into the end zone!")
        return
    _complete(sim, r, qb, rec, total, td=False)
    r.tackler = tackler
    r.tackle_why = why
    sim.touch(rec, 1.2 if total >= 20 else 1.0)
    sim.touch(tackler, 0.8)
    sim.stat(tackler, "tkl")
    if total < 0:
        sim.stat(tackler, "tfl")
    oob = route.sideline and rng.random() < 0.45
    if oob:
        r.out_of_bounds = True
    r.say(f"{'Pushed out' if oob else 'Tackled'} after a gain of {total} — {why}.")
    if rng.random() < 0.006 * weather.fumble_mult(sim, sim.offense):
        _fumble(sim, O, D, r, rec, tackler, total, forced=True)


def _complete(sim, r, qb, rec, yards, td):
    r.yards = yards
    r.td = td
    r.carrier = rec
    sim.stat(qb, "pass_yds", yards)
    sim.stat(rec, "rec_yds", yards)
    sim.stat_max(rec, "rec_long", yards)
    if td:
        sim.stat(qb, "pass_td")
        sim.stat(rec, "rec_td")


def screen_play(sim, O, D, call, dcall, r, runners):
    rng = sim.rng
    sim._ctx = "screen"                               # linemen out in space (sub-proficiencies)
    P = sim.prof
    qb = O["QB"]
    role = call.progression[0]
    rec, route_name = runners[role]
    r.passer, r.target, r.kind = qb, rec, "pass"
    r.duration = rng.randint(5, 7)
    blitz = dcall.rush >= 5
    readers = [p for p in D["LB"] + [D["NB"]] if p is not None] or [D["SS"]]
    sniff = rng.choices(readers, weights=[max(5.0, P(p)["iq"] - 30) for p in readers])[0]
    snuffed = rng.random() < chance((P(sniff)["iq"] - 65) / 22 - (0.8 if blitz else 0) - SCREEN_SNIFF)
    what = {"RB": "screen to the back", "X": "tunnel screen", "SLOT": "bubble screen"}.get(role, "screen")
    r.route = route_name
    r.air_yards = ROUTES[route_name].depth
    r.say(f"{nm(qb)} {'lets the rush come and ' if role == 'RB' else ''}flips a {what} to {nm(rec)}.")
    sim.stat(qb, "pass_att")
    sim.stat(rec, "targets")
    if rng.random() > 0.9:
        r.incomplete = True
        r.inc_reason = "low"
        r.say("Low throw — can't handle it. Incomplete.")
        return
    sim.stat(qb, "pass_cmp")
    sim.stat(rec, "rec")
    r.complete = True
    depth = ROUTES[route_name].depth
    if snuffed:
        return _catch_tackle(sim, O, D, r, qb, rec, depth + rng.uniform(-1, 2), sniff,
                             f"{jn(sniff)} sniffed out the screen and beat the blockers to the spot", ROUTES[route_name])
    blockers = [b for b in O["OL"] if P(b)["quick"] > 45][:3]
    r.say(f"{' and '.join(lab(O, b) for b in blockers[:2]) or 'The blockers'} get out in front...")
    if blitz:
        r.color.append(("screen_vs_blitz", {"rec": rec}))
    fake_route = ROUTES[route_name]
    first = rng.choice([p for p in D["CB"] + D["LB"] if p is not None])
    blocked = blockers and rng.random() < chance((P(blockers[0])["block"] - P(first)["fit"]) / 22 + (0.8 if blitz else 0.2))
    if not blocked and rng.random() < chance((P(first)["tackle"] - P(rec)["elusive"]) / 22 + 1.0):
        return _catch_tackle(sim, O, D, r, qb, rec, depth + rng.uniform(1, 5), first,
                             f"{jn(first)} {'shed the lineman' if blockers else 'came off his man'} and made the play", fake_route)
    gain = depth + rng.uniform(6, 14) + (8 if blitz else 0)
    s = D["SS"]
    if rng.random() < chance((P(s)["tackle"] - P(rec)["elusive"]) / 22 + 0.8):
        return _catch_tackle(sim, O, D, r, qb, rec, gain, s,
                             f"{jn(s)} fought through the traffic to make the stop", fake_route)
    r.big = True
    ytg = 100 - sim.yardline
    total = gain + rng.uniform(10, 40)
    if total >= ytg:
        _complete(sim, r, qb, rec, ytg, td=True)
        r.say(f"Wall of blockers — {nm(rec)} is in the end zone!")
        return
    _catch_tackle(sim, O, D, r, qb, rec, total, D["FS"],
                  f"{jn(D['FS'])} was the last man and saved the touchdown", fake_route)


def rpo_play(sim, O, D, call, dcall, r):
    rng = sim.rng
    qb = O["QB"]
    box = len(D["DL"]) + len(D["LB"]) + (1 if dcall.box >= 8 else 0)
    conflict = D["LB"][-1] if D["LB"] else D["SS"]
    crash = rng.random() < (0.6 if box >= 7 else 0.3)
    correct = rng.random() < chance((sim.prof(qb)["iq"] - 55) / 22 + 1.2)
    throw = crash if correct else not crash
    r.read, r.read_key = ("rpo_throw" if throw else "rpo_give"), conflict
    r.read_correct = correct
    if throw:
        r.say(f"RPO — {lab(D, conflict)} triggers on the run fake, {nm(qb)} pulls it to throw.")
        if not correct:
            r.say("…but he was wrong — the defender dropped.")
        quick = min(call.progression, key=lambda ro: ROUTES[call.route_map[ro]].brk)
        return pass_play(sim, O, D, call, dcall, r, forced_role=quick)
    r.say(f"RPO — {nm(qb)} reads {lab(D, conflict)} {'sitting in coverage' if correct else '… and hands off anyway'}.")
    r.kind = "run"
    ball_carrier(sim, O, D, dcall, r, O["RB"], "inside_zone", rng.choice("AB"), rng.choice(("left", "right")))


# ═══ Special teams ═════════════════════════════════════════════════════════

def _returner(sim, team, kind):
    d = sim.depth[team]
    pool = d["RB"][1:3] + d["WR"][2:6] + d["CB"][2:4]
    pool = pool or d["RB"][:1] + d["WR"][:2] + d["CB"][:2]         # a thin roster: the starters return kicks
    return max(pool, key=lambda p: sim.prof(p)["speed"] + sim.prof(p)["elusive"])


def _coverage_man(sim, team):
    d = sim.depth[team]
    pool = d["LB"][3:6] + d["S"][2:4] + d["CB"][4:6] + d["WR"][5:7]
    pool = pool or d["LB"][:3] + d["S"][:2] + d["CB"][:2]          # a thin roster: the starters cover kicks
    return sim.rng.choice(pool)


def kickoff(sim, kicking, onside=False, style=None):
    """Returns (receiving team yardline, text lines, touchdown?). style: the head coach's call
    ('squib', 'onside', 'surprise') or None for the usual."""
    rng = sim.rng
    receiving = sim.other(kicking)
    k = sim.depth[kicking]["K"][0]
    sim._ctx = "kick"
    kp = sim.prof(k)
    lines = []
    if style == "surprise":
        seen = (getattr(sim, "sl", None) and sim.sl.onsides.get(kicking, 0)) or 0
        if rng.random() < max(0.2, 0.45 - 0.2 * seen):
            lines.append(f"Wait — {nm(k)} squibs it off the side of his foot... SURPRISE ONSIDE! {kicking.school} RECOVERS!")
            return ("kicking", 44, lines, False)
        lines.append(f"A surprise onside kick by {nm(k)} — but {receiving.school} was ready for it. Great field position.")
        return ("receiving", 56, lines, False)
    if style == "onside":
        onside = True
    if onside:
        if rng.random() < 0.14:
            lines.append(f"ONSIDE KICK by {nm(k)}... {kicking.school} RECOVERS!")
            return ("kicking", 46, lines, False)
        lines.append(f"Onside kick by {nm(k)} — {receiving.school} covers it.")
        return ("receiving", 54, lines, False)
    lead = sim.score[kicking] - sim.score[receiving]
    squib = 0 < lead <= 8 and ((sim.quarter == 4 and sim.clock < 120) or (sim.quarter == 2 and sim.clock < 30))
    if style == "squib":
        squib = True
    if not squib and rng.random() < 0.012:
        lines.append(f"{nm(k)}'s kickoff hooks out of bounds. Flag — {receiving.school} takes it at the 35.")
        return ("receiving", 35, lines, False)
    if not squib and rng.random() < chance((kp["kick_power"] - 70) / 8 + 0.4 + weather.kickoff_mod(sim, kicking)):
        lines.append(rng.choice((f"{nm(k)} boots it through the end zone. Touchback.",
                                 f"{nm(k)} gets all of it — out of the back of the end zone.",
                                 f"Deep kick from {nm(k)}, and they'll take the touchback.",
                                 f"{nm(k)} launches it — deep in the end zone, nobody's bringing that out.",
                                 f"No return. {nm(k)} put it through the back line.",
                                 f"{nm(k)} with a boomer. Touchback, ball at the 25.",
                                 f"High and deep from {nm(k)}. The returner kneels it.",
                                 f"{nm(k)} kicks it away… touchback.",
                                 f"That one's in the fourth row. Touchback off the foot of {nm(k)}.")))
        return ("receiving", 25, lines, False)
    ret = _returner(sim, receiving, "kick")
    cov = _coverage_man(sim, kicking)
    sim.touch(ret, 1.0)
    sim.touch(cov, 0.7)
    if squib:
        yard = rng.randint(24, 36)
        lines.append(f"{nm(k)} squibs it — no chance for a big return. {receiving.school} starts at the {yard}.")
        return ("receiving", yard, lines, False)
    if rng.random() < 0.008 * weather.muff_mult(sim, receiving):
        spot = rng.randint(12, 30)
        lines.append(f"{nm(ret)} takes it... and FUMBLES at the {spot}!")
        sim.stat(ret, "fumbles")
        if rng.random() < 0.55:
            sim.stat(cov, "fr")
            lines.append(f"{jn(cov)} recovers for {kicking.school}!")
            return ("kicking", 100 - spot, lines, False, "muff")
        lines.append(f"{nm(ret)} falls on it. Whew.")
        return ("receiving", spot, lines, False)
    start = rng.randint(0, 4)
    yards = rng.gauss(21, 6) + (sim.prof(ret)["elusive"] - sim.prof(cov)["tackle"]) * 0.25
    at = start if start else "goal line"
    lines.append(rng.choice((f"{nm(k)} kicks off. {nm(ret)} fields it at the {at}...",
                             f"The kick is short of the end zone — {nm(ret)} brings it out...",
                             f"{nm(ret)} takes it at the {at} and starts up the middle...",
                             f"A high, short kick — {nm(ret)} gathers it in at the {at}...",
                             f"{nm(k)} drops it inside the 10. {nm(ret)} is going to bring it out...",
                             f"{nm(ret)} catches it at the {at}, finds a seam...",
                             f"Line drive kick, and {nm(ret)} scoops it at the {at}...")))
    sim.stat(ret, "kr")
    if rng.random() < 0.012 + max(0, sim.prof(ret)["speed"] - 80) / 1000:
        sim.stat(ret, "kr_yds", 100 - start)
        sim.stat(ret, "kr_td")
        sim.last_returner = ret
        lines.append(f"...he's through the first wave... HE'S GONE! Kickoff return touchdown, {nm(ret)}!")
        return ("receiving", 100, lines, True)
    yard = int(max(8, min(60, start + yards)))
    sim.stat(ret, "kr_yds", yard - start)
    sim.stat(cov, "tkl")
    lines.append(rng.choice((f"...returned to the {yard}, where {jn(cov)} made the stop.",
                             f"...and he's dragged down at the {yard} by {jn(cov)}.",
                             f"...up to the {yard} before the coverage gets him. {jn(cov)} with the tackle.",
                             f"...but {jn(cov)} sheds a blocker and drops him at the {yard}.",
                             f"...to the {yard}. Good coverage — {jn(cov)} was first down there.",
                             f"...cuts it back, and {jn(cov)} wraps him up at the {yard}.")))
    return ("receiving", yard, lines, False)


def punt(sim):
    """Returns (receiving team yardline, lines, return TD?, blocked?)."""
    rng = sim.rng
    sim._ctx = "kick"
    kicking, receiving = sim.offense, sim.defense
    p = sim.depth[kicking]["P"][0]
    pp = sim.prof(p)
    lines = []
    if rng.random() < 0.006:
        blocker = rng.choice(sim.depth[receiving]["LB"][:3] + sim.depth[receiving]["S"][:2])
        lines.append(f"BLOCKED! {jn(blocker)} got a hand on it!")
        return (100 - max(1, sim.yardline - 5), lines, False, True)
    w_d, w_sd = weather.punt_mod(sim, kicking)                  # the wind, the cold, the thin air
    dist = int(rng.gauss(42 + (pp["kick_power"] - 60) * 0.25 + w_d, 6 + w_sd))
    dist = max(15, dist)
    land = sim.yardline + dist
    sim.stat(p, "punts")
    sim.stat(p, "punt_yds", dist)
    lines.append(rng.choice((f"{nm(p)} punts it away — {dist} yards.",
                             f"{nm(p)} gets it off, a {dist}-yarder.",
                             f"Good hang time from {nm(p)} — {dist} yards." if dist >= 40 else f"{nm(p)} gets it off — {dist} yards.",
                             f"{nm(p)} boots it {dist}.",
                             f"Here's the punt from {nm(p)}… {dist} yards" + (", and it's a good one." if dist >= 45 else "."),
                             f"{nm(p)} spirals it {dist} yards downfield.",
                             f"{nm(p)} gets under it — {dist} yards.",
                             f"The snap is good, {nm(p)} gets it away. {dist} yards.")))
    import subprof
    place = subprof.ratio(p, "placement")                  # placement: pin them, or kick it into the end zone
    if land >= 100 and rng.random() < max(0.0, (place - 0.95) * 3):
        land = rng.randint(92, 97)
        lines.append("He dropped it just short of the goal line!")
    if land >= 100:
        lines.append("Into the end zone. Touchback.")
        return (20, lines, False, False)
    if land >= 90 and rng.random() < min(0.85, 0.55 * place):
        lines.append(rng.choice((f"Downed at the {100 - land}! Great punt.",
                                 f"They pin them at the {100 - land}. Terrific field position flip.",
                                 f"Downed inside the {100 - land + 2}. That's a weapon right there.",
                                 f"The gunner gets there and downs it at the {100 - land}!",
                                 f"It bounces… and stops at the {100 - land}. What a punt.")))
        return (100 - land, lines, False, False)
    ret = _returner(sim, receiving, "punt")
    cov = _coverage_man(sim, kicking)
    if rng.random() < 0.012 * weather.muff_mult(sim, receiving):
        spot = 100 - land
        lines.append(f"{nm(ret)} MUFFS the punt! It's loose at the {spot}!")
        sim.stat(ret, "fumbles")
        if rng.random() < 0.55:
            sim.stat(cov, "fr")
            lines.append(f"{jn(cov)} jumps on it — {kicking.school} gets it back!")
            return (spot, lines, False, False, "muff")
        lines.append(f"{nm(ret)} recovers his own muff.")
        return (spot, lines, False, False)
    if rng.random() < min(0.7, 0.4 * place):
        lines.append(rng.choice((f"{nm(ret)} calls for the fair catch.",
                                 f"{nm(ret)} waves his hand — fair catch.",
                                 "Fair catch signal, and they'll take it there.",
                                 f"No room to run — {nm(ret)} signals for the fair catch.",
                                 f"The coverage is right on him. {nm(ret)} fair-catches it.")))
        return (100 - land, lines, False, False)
    sim.touch(ret, 1.0)
    sim.touch(cov, 0.7)
    ry = int(rng.gauss(6, 5) + (sim.prof(ret)["elusive"] - sim.prof(cov)["tackle"]) * 0.15)
    sim.stat(ret, "pr")
    if rng.random() < 0.012:
        sim.stat(ret, "pr_yds", 100 - land)
        sim.stat(ret, "pr_td")
        sim.last_returner = ret
        lines.append(f"{nm(ret)} fields it... makes one man miss... he's got a lane... TOUCHDOWN on the punt return!")
        return (100, lines, True, False)
    ry = max(-3, ry)
    sim.stat(ret, "pr_yds", ry)
    sim.stat(cov, "tkl")
    lines.append(rng.choice((f"{nm(ret)} returns it {ry} yards before {jn(cov)} brings him down.",
                             f"{nm(ret)} brings it back {ry} yards. {jn(cov)} makes the tackle.",
                             f"{nm(ret)} picks up {ry} on the return before {jn(cov)} gets him.",
                             f"{ry}-yard return for {nm(ret)}, and {jn(cov)} was there to stop it.")))
    return (max(1, 100 - land + ry), lines, False, False)


def field_goal(sim, distance, kicking=None, pat=False):
    rng = sim.rng
    kicking = kicking or sim.offense
    k = sim.depth[kicking]["K"][0]
    sim._ctx = "kick"                                  # accuracy and range (sub-proficiencies)
    kp = sim.prof(k)
    w_rng, w_acc = weather.fg_mods(sim, kicking)               # wind at his back or in his face, cold, altitude
    rng_limit = 48 + (kp["kick_power"] - 60) * 0.3 + w_rng
    x = (kp["kick_acc"] - 60) / 15 + (50 - distance) / 8 + 0.2 - max(0, distance - rng_limit) * 0.4 + w_acc
    x -= sim.__dict__.pop("_iced", 0.0) if not pat else 0.0          # iced (sideline.ice)
    if pat:
        # College PATs go in about 96% of the time (blocks included). Keep a bad
        # kicker below that, a good one above it, and never let a PAT be a coin flip.
        x = max(2.4, min(4.6, 3.4 + (kp["kick_acc"] - 60) / 20))
        x = max(1.8, x + w_acc * 0.5)
    # Every try is an attempt — a block counts against the kicker's line too.
    sim.stat(k, "xp_att" if pat else "fg_att")
    if rng.random() < (0.006 if pat else 0.012):
        return False, f"{nm(k)}'s {'extra point' if pat else f'{distance}-yard attempt'} is BLOCKED!"
    good = rng.random() < chance(x)
    if not pat:
        if good:
            sim.stat(k, "fg_made")
            sim.stat_max(k, "fg_long", distance)
    elif good:
        sim.stat(k, "xp_made")
    if good:
        return True, f"{nm(k)}'s {distance}-yard kick is... GOOD!" if not pat else f"{nm(k)} adds the extra point."
    miss = rng.choice(("wide left", "wide right", "short" if not pat else "wide right"))
    return False, (f"{nm(k)}'s {distance}-yard try is NO GOOD — {miss}." if not pat
                   else f"{nm(k)}'s extra point is NO GOOD — {miss}.")
