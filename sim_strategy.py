"""User-controlled simulation playcalling tendencies.

Stored on Team so it survives saves.  These are preferences, not hard scripts:
the normal scheme, coordinator IQ, opponent looks and game state still matter.
"""
from ui import C, ask, clear, paint, rule, section, title_bar

DEFAULTS = {
    "identity": 0,          # -2 run heavy .. +2 pass heavy
    "first_down": 0,        # -2 run .. +2 pass
    "second_short": -1,
    "second_long": 1,
    "third_short": -1,
    "third_long": 2,
    "red_zone": -1,
    "leading": -1,
    "trailing": 1,
    "tempo": "normal",     # slow / normal / fast
    "shots": "balanced",   # conservative / balanced / aggressive
    "play_action": "setup",# rare / balanced / setup / aggressive
    "pa_runs": 5,           # run calls needed for full setup
    "screens": "balanced",
    "fourth": "coach",     # conservative / coach / aggressive
}

LABELS = {-2: "Run ++", -1: "Run +", 0: "Balanced", 1: "Pass +", 2: "Pass ++"}

def ensure(team):
    s = team.__dict__.setdefault("sim_strategy", {})
    for k, v in DEFAULTS.items():
        s.setdefault(k, v)
    return s

def _cycle(v, vals):
    try: return vals[(vals.index(v) + 1) % len(vals)]
    except ValueError: return vals[0]

def run_shift(team, sim):
    """Positive = more run. Kept modest so scheme/game intelligence still breathe."""
    s = ensure(team)
    shift = -0.055 * s["identity"]
    if 100 - sim.yardline <= 20:
        v = s["red_zone"]
    elif sim.down == 1: v = s["first_down"]
    elif sim.down == 2: v = s["second_short"] if sim.togo <= 4 else s["second_long"]
    else: v = s["third_short"] if sim.togo <= 3 else s["third_long"]
    shift += -0.04 * v
    d = sim.score[team] - sim.score[sim.other(team)]
    if sim.quarter >= 3 and d >= 8: shift += -0.035 * s["leading"]
    elif sim.quarter >= 3 and d <= -8: shift += -0.035 * s["trailing"]
    return max(-0.22, min(0.22, shift))

def family_mult(team, sim, plan, fam):
    s = ensure(team); m = 1.0
    if fam == "play_action":
        mode = s["play_action"]
        m *= {"rare": .55, "balanced": 1.0, "setup": .78, "aggressive": 1.35}.get(mode, 1.0)
        if mode == "setup":
            runs = plan.kind.get("run", [0])[0]
            target = max(3, int(s.get("pa_runs", 5)))
            setup = min(1.0, runs / target)
            m *= .75 + 1.25 * setup
            if runs >= target and fam == "play_action":
                plan.note("pa_setup", sim.plays_run, f"{runs} runs")
    elif fam == "screen":
        m *= {"rare": .6, "balanced": 1.0, "aggressive": 1.45}.get(s["screens"], 1.0)
    elif fam == "deep":
        m *= {"conservative": .68, "balanced": 1.0, "aggressive": 1.45}.get(s["shots"], 1.0)
    return m

def fourth_aggression(team):
    return {"conservative": -18, "coach": 0, "aggressive": 18}.get(ensure(team)["fourth"], 0)

def screen(league, team):
    s = ensure(team); msg = ""
    while True:
        clear(); print(title_bar("SIM PLAYCALLING STRATEGY", C.BMAGENTA))
        print(paint("   These are staff tendencies when games are simulated. They bend your scheme; they do not replace it.", C.GRAY))
        print(paint("   Opponent looks, score, clock and coordinator adjustments can still override a preference.", C.GRAY)); print()
        rows = [
            ("1", "Base identity", LABELS[s["identity"]]),
            ("2", "1st down", LABELS[s["first_down"]]),
            ("3", "2nd & short", LABELS[s["second_short"]]),
            ("4", "2nd & long", LABELS[s["second_long"]]),
            ("5", "3rd & short", LABELS[s["third_short"]]),
            ("6", "3rd & long", LABELS[s["third_long"]]),
            ("7", "Red zone", LABELS[s["red_zone"]]),
            ("8", "Playing with lead", LABELS[s["leading"]]),
            ("9", "Playing from behind", LABELS[s["trailing"]]),
        ]
        print(section("SITUATIONAL RUN / PASS", C.BMAGENTA))
        for k, lab, val in rows: print(f"   {paint('['+k+']', C.BYELLOW)} {lab:<24} {paint(val, C.BWHITE)}")
        print(); print(section("SEQUENCING & AGGRESSION", C.BMAGENTA))
        print(f"   {paint('[A]', C.BYELLOW)} Play-action plan         {s['play_action'].title()}" + (f" · fully set up after {s['pa_runs']} runs" if s['play_action']=='setup' else ""))
        print(f"   {paint('[X]', C.BYELLOW)} Shot plays               {s['shots'].title()}")
        print(f"   {paint('[S]', C.BYELLOW)} Screens                  {s['screens'].title()}")
        print(f"   {paint('[F]', C.BYELLOW)} Fourth downs             {s['fourth'].title()}")
        print(f"   {paint('[T]', C.BYELLOW)} Tempo philosophy         {s['tempo'].title()}")
        if msg: print(paint("\n   " + msg, C.BGREEN))
        print(rule()); c = ask("Change a setting (R reset, B back):").strip().lower()
        if c in ("b", "back", ""): return
        if c == "r":
            team.sim_strategy = dict(DEFAULTS); s = team.sim_strategy; msg = "Reset to balanced defaults."; continue
        nums = {str(i+1): k for i,k in enumerate(("identity","first_down","second_short","second_long","third_short","third_long","red_zone","leading","trailing"))}
        if c in nums:
            k=nums[c]; s[k] = _cycle(s[k], [-2,-1,0,1,2]); msg=f"{k.replace('_',' ').title()}: {LABELS[s[k]]}."; continue
        if c == "a":
            s["play_action"]=_cycle(s["play_action"],["rare","balanced","setup","aggressive"])
            if s["play_action"] == "setup":
                v=ask("Runs before play-action is fully set up (3-8, Enter = 5):").strip()
                s["pa_runs"] = int(v) if v.isdigit() and 3 <= int(v) <= 8 else 5
            msg="Play-action plan updated."; continue
        if c == "x": s["shots"]=_cycle(s["shots"],["conservative","balanced","aggressive"]); msg="Shot-play appetite updated."; continue
        if c == "s": s["screens"]=_cycle(s["screens"],["rare","balanced","aggressive"]); msg="Screen tendency updated."; continue
        if c == "f": s["fourth"]=_cycle(s["fourth"],["conservative","coach","aggressive"]); msg="Fourth-down override updated."; continue
        if c == "t": s["tempo"]=_cycle(s["tempo"],["slow","normal","fast"]); msg="Tempo philosophy updated."; continue
