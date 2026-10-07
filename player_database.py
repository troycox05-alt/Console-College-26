"""Forgiving JSON player-database import for new worlds.

Supported shapes include a flat list, {"players": [...]}, {"teams": {"Alabama": [...]}}
or simply {"Alabama": [{...}], "Georgia": [{...}]}. Missing fields are inherited
from the generated roster slot being replaced.
"""
import json, os, re

ALIASES = {"name":"name","player":"name","player_name":"name","school":"team","team":"team",
           "pos":"position","position":"position","class":"year","yr":"year","year":"year",
           "traits":"traits","trait":"traits","ratings":"ratings"}
YEARS = {"FR":0,"FRESHMAN":0,"SO":1,"SOPHOMORE":1,"JR":2,"JUNIOR":2,"SR":3,"SENIOR":3}


def _norm(s): return re.sub(r"[^a-z0-9]", "", str(s).lower())

def _records(data):
    if isinstance(data, list): return [(None, x) for x in data if isinstance(x, dict)]
    if not isinstance(data, dict): return []
    if isinstance(data.get("players"), list): return [(None,x) for x in data["players"] if isinstance(x,dict)]
    if isinstance(data.get("teams"), dict):
        return [(team,x) for team, xs in data["teams"].items() if isinstance(xs,list) for x in xs if isinstance(x,dict)]
    out=[]
    for k,v in data.items():
        if isinstance(v,list): out += [(k,x) for x in v if isinstance(x,dict)]
        elif isinstance(v,dict) and any(_norm(z) in ("name","player","playername") for z in v): out.append((k,v))
    return out


def _field(rec, *names):
    wanted={_norm(x) for x in names}
    for k,v in rec.items():
        if _norm(k) in wanted: return v
    return None


def _team(league, name):
    if not name: return None
    n=_norm(name)
    exact=[t for t in league.teams if _norm(t.school)==n or _norm(getattr(t,"full_name",t.school))==n]
    if exact: return exact[0]
    partial=[t for t in league.teams if n in _norm(t.school) or _norm(t.school) in n]
    return partial[0] if len(partial)==1 else None


def _year(v, fallback):
    if v is None: return fallback
    if isinstance(v,(int,float)):
        i=int(v); return max(0,min(3,i-1 if 1 <= i <= 4 else i))
    s=str(v).upper().replace("RS-","").strip()
    return YEARS.get(s, fallback)


def _trait_keys(vals):
    import traits
    if vals is None: return []
    if isinstance(vals,str): vals=[x.strip() for x in re.split(r"[,;|]", vals) if x.strip()]
    if not isinstance(vals,list): return []
    labels={_norm(v[0]):k for k,v in traits.PLAYER_TRAITS.items()}
    keys={_norm(k):k for k in traits.PLAYER_TRAITS}
    out=[]
    for x in vals:
        k=keys.get(_norm(x)) or labels.get(_norm(x))
        if k and k not in out: out.append(k)
    return out




def _infer_position(rec, ratings):
    """Best-effort position inference when a modular file omits `position`."""
    keys = {_norm(k) for k in list(rec) + list(ratings)}
    groups = [
        ("QB", {"throwpower","throwaccuracy","passing","arm","passaccuracy"}),
        ("K", {"kickpower","kickaccuracy","fieldgoal"}),
        ("P", {"puntpower","puntaccuracy","punting"}),
        ("WR", {"catching","route","routerunning","reception"}),
        ("RB", {"carrying","elusiveness","breaktackle","rushing"}),
        ("OL", {"passblock","runblock","blocking"}),
        ("CB", {"mancoverage","press","corner"}),
        ("S", {"zonecoverage","safety"}),
        ("DL", {"passrush","blockshedding","defensiveline"}),
        ("LB", {"tackling","linebacker"}),
        ("TE", {"tightend"}),
    ]
    for pos, hints in groups:
        if keys & hints:
            return pos
    return None
def _ratings(rec):
    raw=_field(rec,"ratings","attributes","fundamentals")
    d=dict(raw) if isinstance(raw,dict) else {}
    # Also accept ratings directly at player level.
    for k,v in rec.items():
        nk=_norm(k)
        if nk in ("strength","str","speed","spd","quickness","quick","qck","iq","awareness","injury","durability","playmaker","playmaking","overall","ovr"):
            d[k]=v
    return d


def _num(d, names):
    for k,v in d.items():
        if _norm(k) in {_norm(x) for x in names}:
            try:return float(v)
            except Exception:return None
    return None


def _apply_ratings(p, d):
    from models import POSITION_WEIGHTS
    fmap={"strength":("strength","str","power","throw power","throw_power","tackle power","block strength"),
          "speed":("speed","spd"),
          "quickness":("quickness","quick","qck","agility","acceleration","route running","route_running"),
          "iq":("iq","awareness","throw accuracy","throw_accuracy","coverage","zone coverage","zone_coverage","football iq"),
          "injury":("injury","durability","health"),
          "playmaker":("playmaker","playmaking","catching","carrying","break tackle","break_tackle","pass rush","pass_rush")}
    supplied=set()
    for f,names in fmap.items():
        v=_num(d,names)
        if v is not None:
            p.fundamentals[f]=int(max(1,min(99,round(v)))); supplied.add(f)
    target=_num(d,("overall","ovr"))
    if target is None:
        return
    target=int(max(1,min(99,round(target))))
    if not supplied:
        for f in ("strength","speed","quickness","iq","playmaker"):
            p.fundamentals[f]=target
        p.proficiency[p.position]=1.0
        return
    weights=POSITION_WEIGHTS[p.position]
    def raw(): return sum(p.fundamentals[f]*w for f,w in weights.items())
    # First preserve explicitly supplied attributes and use position proficiency to bridge the gap.
    rr=raw() or 1
    need=target/rr
    if need <= 1.2:
        p.proficiency[p.position]=max(.55,min(1.2,need)); return
    # If that is not enough, lift only omitted position-relevant ratings until the requested OVR is reachable.
    omitted=[f for f,w in weights.items() if w>0 and f not in supplied]
    goal_raw=target/1.2
    for _ in range(4):
        rr=raw()
        if rr >= goal_raw-.1 or not omitted: break
        capacity=sum(weights[f] for f in omitted if p.fundamentals[f] < 99)
        if capacity <= 0: break
        inc=(goal_raw-rr)/capacity
        for f in omitted:
            if p.fundamentals[f] < 99:
                p.fundamentals[f]=int(max(1,min(99,round(p.fundamentals[f]+inc))))
    rr=raw() or 1
    p.proficiency[p.position]=max(.55,min(1.2,target/rr))


def apply(league, path):
    """Apply a custom player database to the *finished* generated world.

    The caller invokes this after League's four-season burn-in.  Multiple imported
    players may share the same team/position; each record reserves a different
    generated roster slot so later records cannot silently overwrite earlier ones.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rows = _records(data)
    imported, warnings = [], []
    used_slots = {}                       # team id -> ids of generated slots already claimed by this import

    for default_team, rec in rows:
        name = _field(rec, "name", "player", "player name")
        school = _field(rec, "team", "school") or default_team
        if not name or not school:
            warnings.append("Skipped a record missing player/name or team/school.")
            continue
        team = _team(league, school)
        if team is None:
            warnings.append(f"{name}: couldn't match team '{school}'.")
            continue

        ratings = _ratings(rec)
        pos = _field(rec, "position", "pos")
        pos = str(pos).upper().strip() if pos else _infer_position(rec, ratings)
        yr_raw = _field(rec, "year", "class", "yr")
        claimed = used_slots.setdefault(id(team), set())
        available = [p for p in team.roster if id(p) not in claimed]
        if not available:
            warnings.append(f"{name}: {team.school} has no unclaimed generated roster slot left.")
            continue

        same_pos = [p for p in available if not pos or p.position == pos]
        candidates = same_pos or available
        target_year = _year(yr_raw, candidates[0].year)
        target_ovr = _num(ratings, ("overall", "ovr"))
        slot = min(candidates, key=lambda p: (
            0 if p.year == target_year else 1,
            0 if (not pos or p.position == pos) else 1,
            abs(p.overall - target_ovr) if target_ovr is not None else p.overall,
        ))
        claimed.add(id(slot))

        bits = str(name).strip().split()
        slot.first_name = bits[0]
        slot.last_name = " ".join(bits[1:]) if len(bits) > 1 else bits[0]
        slot.year = _year(yr_raw, slot.year)
        if pos and pos in __import__("models").POSITIONS:
            slot.position = pos
        tr = _trait_keys(_field(rec, "traits", "trait"))
        if tr:
            slot.traits = tr
        _apply_ratings(slot, ratings)
        slot.__dict__["database_player"] = True
        slot.__dict__["database_source"] = os.path.basename(path)
        imported.append((slot, team))

    # Imported names/positions can change jersey and depth-chart assumptions.
    for team in league.teams:
        team.fix_numbers()
    league.__dict__["player_database"] = {
        "file": os.path.basename(path),
        "count": len(imported),
        "warnings": warnings[:30],
        "applied_after_burn_in": True,
        "season": getattr(league, "year", None),
    }
    return imported, warnings


CUSTOM_PLAYERS_DIR = "custom players"


def custom_players_dir():
    """Folder beside the game code where importable player databases live."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, CUSTOM_PLAYERS_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def list_files():
    """Return available JSON player databases in the dedicated folder."""
    path = custom_players_dir()
    try:
        names = [n for n in os.listdir(path) if n.lower().endswith(".json") and os.path.isfile(os.path.join(path, n))]
    except OSError:
        return []
    return sorted(names, key=lambda n: n.lower())


def _database_summary(path):
    """Best-effort one-line description for the picker; malformed files remain selectable and report on import."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        meta = data.get("metadata", {}) if isinstance(data, dict) else {}
        title = meta.get("title") or os.path.splitext(os.path.basename(path))[0].replace("_", " ")
        rows = _records(data)
        teams = set()
        for default_team, rec in rows:
            school = _field(rec, "team", "school") or default_team
            if school:
                teams.add(str(school))
        bits = [f"{len(rows)} players"]
        if teams:
            bits.append(f"{len(teams)} teams")
        return str(title), " · ".join(bits)
    except Exception:
        return os.path.splitext(os.path.basename(path))[0].replace("_", " "), "could not preview"


def choose_path():
    """Choose a JSON database from the game's `custom players` folder. No OS file picker is used."""
    from ui import C, ask, paint
    files = list_files()
    folder = custom_players_dir()
    print(paint("\n   CUSTOM PLAYER DATABASES", C.BCYAN, C.BOLD))
    print(paint("   Put .json files in the game's 'custom players' folder. They will appear here automatically.", C.GRAY))
    if not files:
        print(paint("\n   No player databases found.", C.BYELLOW, C.BOLD))
        print(paint(f"   Folder: {folder}", C.GRAY))
        return None
    print()
    for i, name in enumerate(files, 1):
        title, summary = _database_summary(os.path.join(folder, name))
        print(f"   {paint(f'[{i}]', C.BCYAN, C.BOLD)} {paint(title, C.BWHITE, C.BOLD)}")
        print(paint(f"       {name} · {summary}", C.GRAY))
    print(paint("\n   [Enter] Cancel", C.GRAY))
    while True:
        raw = ask("Choose player database:").strip()
        if not raw:
            return None
        try:
            idx = int(raw)
        except ValueError:
            print(paint("   Enter the number beside a database, or press Enter to cancel.", C.BYELLOW))
            continue
        if 1 <= idx <= len(files):
            return os.path.join(folder, files[idx - 1])
        print(paint("   That database number is not listed.", C.BYELLOW))
