"""Per-save Customize Your Universe gameplay switches."""
DEFAULTS = {
    "inbox": True, "realignment": True, "violations": True, "personalities": True,
    "morale": True, "weather": True, "injuries": True, "carousel": True,
    "nil_pressure": True, "media": True,
}
LABELS = {
    "inbox": ("Inbox & decisions", "messages, requests and consequential replies"),
    "realignment": ("Conference realignment", "leagues expand, poach and reshape the map"),
    "violations": ("Violations & compliance", "rule-breaking, investigations, grades and sanctions"),
    "personalities": ("Player personalities", "locker-room incidents and player-driven events"),
    "morale": ("Morale & portal drama", "role happiness, chemistry and transfer pressure"),
    "weather": ("Dynamic weather", "rain, snow, wind, heat and cold affect Saturdays"),
    "injuries": ("Injuries", "players can be hurt and miss time"),
    "carousel": ("Coach carousel & firings", "AI coaches can be fired, hired and move jobs"),
    "nil_pressure": ("NIL & booster pressure", "player NIL demands and booster-driven pressure"),
    "media": ("Media obligations", "pregame/postgame press conferences and their effects"),
}
PRESETS = {
    "balanced": dict(DEFAULTS),
    "chaos": dict(DEFAULTS),
    "stable": {**DEFAULTS, "realignment": False, "violations": False, "personalities": False,
               "morale": False, "carousel": False, "nil_pressure": False},
}

def normalize(rules=None):
    out = dict(DEFAULTS); out.update(rules or {}); return out

def install(league, rules=None):
    league.world_rules = normalize(rules); return league.world_rules

def enabled(league, key):
    return bool(normalize(getattr(league, "world_rules", None)).get(key, True))
