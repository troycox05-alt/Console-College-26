# Console College v52 — Mobile Web Stage 1

A zero-dependency mobile web shell around the real Console College Python simulation.

## Playable now
- Create a streamlined Coach Career (coach name, school, universe preset)
- Load the existing Autosave
- Mobile dashboard / next game / last result
- Starting lineup / roster overview
- Full team schedule
- Conference standings
- Sim the next week using the real simulation engine
- Autosave and manual Save Career

## Hosting
The server listens on `$PORT` and includes `Procfile` and `railway.json` for web hosting. Saves remain in `saves/`; hosted production should mount persistent storage at that directory before relying on long-term careers.

## Next stage
Recruiting, portal, inbox, interviews, full new-coach creator, game-mode choice, offseason and richer player/team pages.
