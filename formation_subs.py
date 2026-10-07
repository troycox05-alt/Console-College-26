"""Formation and play-specific substitutions for Coach Career.

Saved on the Team so they work whether set in fall camp, during the week, or from
an in-game substitution menu.  The game engine applies a personnel package first,
then a play-specific override.  Only healthy/available roster players are honored;
otherwise the normal depth chart falls through automatically.
"""
from ui import C, ask, clear, pad, paint, pause, title_bar, truncate

PACKAGES = ("10", "11", "12", "21", "22")
PACKAGE_NAMES = {"10": "10 personnel · 1 RB, 0 TE, 4 WR", "11": "11 personnel · 1 RB, 1 TE, 3 WR",
                 "12": "12 personnel · 1 RB, 2 TE, 2 WR", "21": "21 personnel · 2 RB, 1 TE, 2 WR",
                 "22": "22 personnel · 2 RB, 2 TE, 1 WR"}
ROLES = ("QB", "RB", "X", "Z", "SLOT", "Y", "FB")
PACKAGE_ROLES = {
    "10": ("QB", "RB", "X", "Z", "SLOT", "Y"),
    "11": ("QB", "RB", "X", "Z", "SLOT", "Y"),
    "12": ("QB", "RB", "X", "Z", "SLOT", "Y"),
    "21": ("QB", "RB", "X", "Z", "Y", "FB"),
    "22": ("QB", "RB", "X", "Z", "Y", "FB"),
}
ROLE_POS = {"QB": ("QB",), "RB": ("RB",), "FB": ("RB", "TE"),
            "X": ("WR", "TE"), "Z": ("WR", "TE"), "SLOT": ("WR", "TE", "RB"), "Y": ("TE", "WR")}


def state(team):
    d = team.__dict__.setdefault("formation_subs", {})
    d.setdefault("personnel", {})
    d.setdefault("plays", {})
    return d


def _valid_player(team, p, role):
    return p in team.roster and not p.__dict__.get("redshirt_plan") and p.position in ROLE_POS.get(role, ()) and getattr(p, "inj_games", 0) <= 0


def overrides(team, personnel, play_name=None):
    """Merged role->Player overrides for a snap; play-specific wins over package."""
    d = state(team)
    out = dict(d["personnel"].get(str(personnel), {}) or {})
    if play_name:
        out.update(d["plays"].get(str(play_name), {}) or {})
    return {r: p for r, p in out.items() if r in ROLES and _valid_player(team, p, r)}


def apply_lineup(team, lineup, personnel, play_name=None):
    """Apply saved substitutions to engine lineup without ever duplicating one player."""
    wanted = overrides(team, personnel, play_name)
    if not wanted:
        return lineup
    out = dict(lineup)
    current = {r: out.get(r) for r in ROLES if out.get(r) is not None}
    for role in ROLES:
        p = wanted.get(role)
        if p is None or (role == "FB" and out.get("FB") is None):
            continue
        # Do not put one player at two skill spots. If his old role exists, swap/fall through there.
        old_role = next((r for r, q in current.items() if q is p and r != role), None)
        replaced = out.get(role)
        if old_role is not None:
            out[old_role] = replaced
            current[old_role] = replaced
        out[role] = p
        current[role] = p
    labels = dict(out.get("label") or {})
    for role in ("QB", "RB", "X", "Z", "SLOT", "Y", "FB"):
        p = out.get(role)
        if p is not None:
            labels[id(p)] = role
    out["label"] = labels
    return out


def _pool(team, role):
    pos = ROLE_POS.get(role, ())
    return [p for q in pos for p in team.players_at(q) if getattr(p, "inj_games", 0) <= 0]


def _pick_player(team, role):
    pool = _pool(team, role)
    if not pool:
        pause("No eligible players for that role. Press Enter:")
        return None
    print()
    for i, p in enumerate(pool, 1):
        rs = " · REDSHIRT PLAN" if p.__dict__.get("redshirt_plan") else ""
        print(f"   {i:>2}. #{p.number:<3} {pad(truncate(p.name, 26), 27)} {p.position:<3} {p.class_label}{paint(rs, C.BYELLOW)}")
    c = ask("Player # (Enter cancels):").strip()
    if not c.isdigit() or not (1 <= int(c) <= len(pool)):
        return None
    p = pool[int(c) - 1]
    if p.__dict__.get("redshirt_plan"):
        yn = ask(f"{p.name} is protected for a redshirt. Use him in this package anyway? [y/N]:").strip().lower()
        if yn != "y":
            return None
        p.__dict__.pop("redshirt_plan", None)
    return p


def _edit_map(team, label, mp, roles=None):
    roles = tuple(roles or ROLES)
    while True:
        clear()
        print(title_bar(f"FORMATION SUBS · {team.school.upper()} · {label.upper()}"))
        print(paint("   These are standing substitutions. If a selected player is hurt, the normal depth chart fills in.", C.GRAY))
        print()
        for i, role in enumerate(roles, 1):
            p = mp.get(role)
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(role, 6)} " +
                  (f"#{p.number} {p.name} ({p.position})" if p else paint("depth chart default", C.GRAY)))
        print(rule_line())
        c = ask("Role # to set · [R] reset all · Enter = back:").strip().lower()
        if not c:
            return
        if c == "r":
            mp.clear()
            continue
        if c.isdigit() and 1 <= int(c) <= len(roles):
            role = roles[int(c) - 1]
            cur = mp.get(role)
            if cur is not None:
                z = ask(f"{role} is {cur.name}. [C] change  [R] reset to depth chart: ").strip().lower()
                if z == "r":
                    mp.pop(role, None)
                    continue
                if z != "c":
                    continue
            p = _pick_player(team, role)
            if p is not None:
                mp[role] = p


def rule_line():
    return paint("   " + "─" * 94, C.GRAY)


def _scheme_plays(team):
    import playbook
    import staff
    scheme = playbook.OFFENSE_SCHEMES.get(staff.play_caller(team, "off").offense_scheme, {})
    names = list((scheme.get("plays") or {}).keys())
    # Some scheme dictionaries use concept weights instead of exact play names; the playbook itself is canonical.
    if not names or not all(isinstance(x, str) for x in names):
        names = []
    available = sorted(playbook.ALL_PLAYS)
    if names:
        available = [n for n in available if n in names] or available
    return sorted(dict.fromkeys(available))


def _play_screen(team):
    plays = _scheme_plays(team)
    while True:
        clear()
        print(title_bar(f"FORMATION SUBS · {team.school.upper()} · PLAY PACKAGES"))
        configured = state(team)["plays"]
        print(paint("   A play override is applied after the personnel package, so it is the most specific instruction.", C.GRAY))
        print()
        for i, name in enumerate(plays, 1):
            tag = paint("SET", C.BGREEN, C.BOLD) if configured.get(name) else paint("—", C.GRAY)
            print(f"   {i:>2}. {pad(truncate(name, 34), 35)} {tag}")
        c = ask("Play # · [R] clear every play override · Enter = back:").strip().lower()
        if not c:
            return
        if c == "r":
            configured.clear()
        elif c.isdigit() and 1 <= int(c) <= len(plays):
            name = plays[int(c) - 1]
            mp = configured.setdefault(name, {})
            _edit_map(team, name, mp)
            if not mp:
                configured.pop(name, None)


def screen(league, team=None):
    team = team or getattr(league, "user_team", None)
    if team is None:
        return
    d = state(team)
    while True:
        clear()
        print(title_bar(f"FORMATION SUBS · {team.school.upper()}"))
        print(paint("   Set these during the week or in fall camp. They carry into every game until you change them.", C.GRAY))
        print(paint("   Personnel package first; play-specific override second; injuries always fall through to your depth chart.", C.GRAY))
        print()
        for i, pk in enumerate(PACKAGES, 1):
            n = len(d["personnel"].get(pk, {}))
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(PACKAGE_NAMES[pk], 42)} " +
                  (paint(f"{n} override{'s' if n != 1 else ''}", C.BGREEN) if n else paint("depth chart defaults", C.GRAY)))
        print(f"   {paint('[P]', C.BYELLOW, C.BOLD)} Play-specific packages                 " +
              (paint(f"{len(d['plays'])} configured", C.BGREEN) if d["plays"] else paint("none", C.GRAY)))
        print(rule_line())
        c = ask("Package # · [P] plays · [R] reset all · Enter = back:").strip().lower()
        if not c:
            return
        if c == "p":
            _play_screen(team)
        elif c == "r":
            d["personnel"].clear(); d["plays"].clear()
        elif c.isdigit() and 1 <= int(c) <= len(PACKAGES):
            pk = PACKAGES[int(c) - 1]
            mp = d["personnel"].setdefault(pk, {})
            _edit_map(team, PACKAGE_NAMES[pk], mp, PACKAGE_ROLES[pk])
            if not mp:
                d["personnel"].pop(pk, None)
