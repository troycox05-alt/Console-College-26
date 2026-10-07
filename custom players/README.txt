CUSTOM PLAYERS
==============

Drop player database .json files in this folder. Before building a new world,
choose [P] Choose custom player database and the game will list them here.

IMPORTANT: custom players are applied AFTER the four-season (2022-25) history
simulation finishes. They therefore enter the roster in the 2026 world you
actually take over and cannot graduate, transfer, or be drafted during burn-in.

The bundled 2026_REAL_PLAYERS_476.json contains 476 real 2026 players across
120 FBS programs. Ratings and traits are game-scale editorial approximations,
not official ratings or factual claims about off-field personality.

Accepted JSON can be loose/modular. Examples:
  {"players": [{"player":"Name", "team":"Alabama", "position":"QB", "year":"SO",
                "traits":["Clutch"], "ratings":{"overall":91,"throw_accuracy":94}}]}

or:
  {"Alabama": [{"player":"Name", "position":"WR", "ratings":{"overall":88}}]}

or:
  {"teams": {"Alabama": [{...}], "Georgia": [{...}]}}

Missing fields inherit from the generated roster slot being replaced. Multiple
players at the same team and position are supported; every imported record gets
a separate generated roster slot.
