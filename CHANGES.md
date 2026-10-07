# v51.15 — RETENTION, ROLE PROMISES, FORMATION SUBS & PRESEASON REDSHIRTS

- **Retention conversations.** Transfer Watch and the weekly hub now lead into a retention board for the user's roster. A coach can listen, reassure, make a specific role promise, or tell the player to earn it. The resulting morale/retention effect feeds the existing portal-risk model instead of replacing it.
- **Tracked in-season role promises.** Designed-package, rotation-role and (for RB/WR/TE) featured-touch promises record a baseline and are graded from actual game usage over the next three games. Kept promises sharply reduce portal risk; broken promises can make it worse.
- **Formation/play substitutions.** Saved 10/11/12/21/22 personnel overrides and play-specific overrides can be built in fall camp, from the weekly hub, from the team page, or from the in-game substitution menu. The engine applies the personnel package first and the play override second; injuries fall through to the normal depth chart.
- **Snap accounting.** Every player actually on offense or defense receives a snap in the box-score stat map. This drives role-promise grading and improves participation accounting.
- **Preseason redshirt protection.** Fall camp has a redshirt-plan screen. Protected players are removed from ordinary lineup selection, but emergency usage and deliberate package usage can still happen. At season end the existing four-game rule decides whether the year was preserved; playing more than four games burns the plan.
- **Online synchronization.** Formation packages, redshirt protection, role promises, retention conversations and the resulting morale/retention state are harvested as standing client state and applied to the host world.
- **Team Context.** The team-context export now includes redshirt plans, retention/role-promise status and saved formation/play substitutions.
- Verification: all Python files parse under Python 3.8 grammar; touched modules import; focused lineup tests confirmed a saved 11-personnel slot override is honored and redshirt protection suppresses it; focused promise tests confirmed 30 snaps over three games fulfills an 8-snaps/game package promise.

# v51.14 — TEAM PODCAST DEEP-DIVE DOSSIER

- Team-focused Curate Stories prompts now automatically include a detailed program dossier for the selected team.
- The dossier includes the program snapshot, current record/rank/scoring context, preseason projection, conference expectation, athletic director and program goals, the complete coaching staff, full schedule/results, and the full roster in depth-chart order with public/contextual player details, season production, injuries, transfers, captains and NIL.
- Active recruiting targets are included when available. Raw hidden player ratings remain hidden in Coach Career; the AI packet uses the same public/scouting-safe context the player is meant to have.
- The team dossier is automatic for Team Podcast and is separate from the general coaching-staff-depth toggle used by national/conference kits.

# v51.13 — CURATE STORIES STAYS OPEN

- Curate Stories now remains on the curation screen after building/copying a story kit, so multiple prompts can be generated in one visit.
- All current section toggles, show choice, and coaching-staff depth stay in place between copies.
- Curate Stories exits only when the user explicitly chooses **B = back**; pressing Enter never leaves the workspace. Story-history/"already covered" state is committed when you leave, so earlier copies in the same visit do not make facts disappear from later prompts.

# v51.12 — CURATE STORIES: COACHING STAFF DEPTH

- Added an **S = staff depth** option to Curate Stories. It cycles through Off, Head Coaches, Head Coaches + Coordinators, and Head Coaches + Coordinators + Position Coaches.
- Staff reference is limited to teams actually present in the selected story-kit facts; team podcasts always include their team, and conference podcasts include the conference. This keeps full-staff prompts useful without dumping every FBS assistant into the kit.
- The generated AI prompt gets a dedicated **COACHING STAFFS** reference section and tells the writer to use those names only when coaching context matters.
- The preference is remembered with the other Curate Stories choices; existing saves default to Off.

# v51.11 — ONLINE IMPORTED GAME POSTGAME FIX

- Fixed the host worker crash after a connected coach finished a game: imported online box scores now implement the same `other(team)` helper as a normal `GameSim`.
- This keeps the authoritative-client-game design intact while allowing normal postgame records, rivalry, classic, and week-finalization code to consume the imported box score.
- Verified the touched module with Python 3.8 grammar and a focused imported-box compatibility smoke test.

# v51.10 — WINDOW INPUT PROMPTS STAY ON SCREEN
------------------------------------------------
A focused desktop-window readability fix, including online multiplayer/live host screens.
- **The question stays with the screen that asked it.** The desktop window no longer removes the active `input()` prompt from the game output. Long questions, option lists and explanatory text remain visible in the main scrollable game screen exactly where Coach Career printed them.
- **The bottom bar is only for typing.** Instead of duplicating and clipping the prompt to 55% of the footer, the bar now shows only a short “Your answer”/“Continue” cue beside the input field.
- **Applies everywhere.** This is the window renderer, so ordinary Career prompts, online client prompts and host-to-player live screens all get the same behavior without changing terminal-mode input.
- **Checked:** JavaScript syntax check passes with Node when available; all Python files still compile under the available runtime; release packaging exclusions unchanged.

# v51.9 — ONLINE GAMES PLAY ONCE
--------------------------------
Connected coaches' Saturday games are now authoritative client results instead of deterministic host replays.
- **No second simulation of your game.** After a connected coach finishes Saturday, the client sends the final score, complete box-score data, player season totals, injury status and postgame podium. The host imports that result into the matching scheduled game.
- **The host skips connected-user matchups.** It simulates only games for which no connected coach submitted a result, then runs the ordinary end-of-week rankings, recruiting, development, stories and other world work.
- **Box scores survive the trip.** Imported games rebuild the GameSim-shaped box used by results, recaps, records and media screens, including line score, team/player stats, scoring summary, weather and injuries. Normal postgame weather/rivalry/classic/record bookkeeping runs once on the host after import.
- **User-vs-user games do not create a third result.** Both players still finish/report so their postgame moments arrive; the host deterministically imports the home coach's submitted game when both copies are present.
- **Removed the replay mismatch warning.** There is no host replay to disagree with the game the coach just played.
- **Checked:** all Python files compile on the available Python runtime after the change; touched online modules import successfully.
- **Not checked:** two physical computers/Wi-Fi, a complete online season, user-vs-user divergence between two client copies, or ruff. The owner remains the primary gameplay tester.

# v51.8 — ONLINE MULTIPLAYER POLISH
------------------------------------
A reliability/UX pass across the existing LAN mode; no new multiplayer rules. Coach Career remains the screen set and the host remains authoritative.
- **Ready/Force cannot skip offseason steps.** Offseason advances are de-duplicated while one is starting, and the stage is now read only after the world-worker lock is held. Repeated Ready/Force requests can no longer queue a second calendar advance behind the first.
- **Failures are visible instead of looking frozen.** Background host-worker exceptions are stored in online status and shown on season/offseason wait screens. Host-side order validation and replay/fingerprint notes are returned as visible ONLINE NOTE messages. Game-report and ready failures now stop with the host's reason instead of dropping the response.
- **Stale copies recover cleanly.** If the host has already moved to a newer revision when a coach submits the week/offseason, the client fetches the current world rather than leaving the coach on a stale local copy.
- **Lobby/reconnect cleanup.** START now refuses while anybody in the room is still choosing a program. Live-screen bridges are rebound to the current host, stale queued answers are cleared between sessions, reconnecting during an active host-side question does not erase that question, and bridges are removed when hosting closes.
- **Small UI cleanup.** The game wait says “game finished” instead of the gendered “played his game”; Chapter 34 no longer labels the implemented online flow as a preview. Removed an unreachable leftover block after `follow_coaches()`.
- **Measured (one machine, Python 3):** all Python files parse with the Python 3.8 grammar; all nine netplay modules import cleanly; a bridge reset leaves zero stale answers; two overlapping offseason advance requests produce exactly one running step (`True`, `False`, 1 call); START correctly refuses a room with one unpicked seat; and ready/report server errors raise their host-provided reason.
- **Not checked:** two physical computers/Wi-Fi, window mode, a complete multi-season online career, or ruff. The owner remains the primary gameplay tester.

# v51.7 — ONLINE MODE, PHASE 6: THE OFFSEASON
------------------------------------
**The shared world now has the Coach Career offseason.** Every player works the same offseason calendar step on his own copy, readies up, and the host advances the national world once between steps.
- **Season wrap and January are synchronized.** Year-end career work is filed per seat; the head-coach market is staged before staff movement; each coach handles his own job/staff decisions; the host then runs the assistant carousel and follows a player wherever his coach goes. Conflicting open-job accepts settle in arrival order: first accepted wins.
- **Portal Window I is three real shared weeks.** Weeks 4, 5 and 6 now separate the player's portal board from the host's national commitment wave, so the world moves only after everyone is ready. Week 7 does the same for the final recruiting push.
- **Signing Day is one host world step.** The class resolves once. Room checks and the live hats/results screens use the v51.6 live bridge for the affected coach. The completed offseason report is kept in `league.online` for client snapshots.
- **February through A-Day is simultaneous per team, then Portal II syncs twice, then summer/Media Days are simultaneous.** The large per-team blocks replay with their own deterministic `league.rng` seed. Replayed offseason moments carry a team-state fingerprint; a mismatch is returned in the host's moment notes instead of being silent.
- **Career state follows the player through the calendar.** `offseason_state` is seat-private, along with the existing inbox/hub/job-market state. Client localization restores the normal Career job and portal hooks; host `acting_as` does the same while replaying or bridging a player's screens.
- Existing single-player offseason entry points still call the same portal/recruiting/spring functions; those functions were split into board work and world-step helpers rather than duplicated.
- **Measured (one machine, Python 3.12):** the new winter world-step API opened 1,279 portal entries and advanced Weeks 4–6 to 1,033 moves / 246 unsigned; the spring API opened 326 entries and advanced Weeks 14–15 to 286 moves / 40 unsigned. A compressed online snapshot containing an active winter portal report was 2,153,290 bytes, reloaded successfully, and the host/client team fingerprints matched (`4da104e406b4e847cb49`). All Python files parse with the Python 3.8 grammar and the touched modules import cleanly.
- **Not checked:** a full interactive season-to-Media-Days run, two physical computers/Wi-Fi, window mode, or ruff (not installed here). The owner remains the primary gameplay tester.

# v51.6 — ONLINE MODE, PHASE 5 (PART 1): LIVE SCREENS FROM THE HOST'S WORLD
------------------------------------
Groundwork for the coaching market. Nothing new to see in a week yet: in a career the coaching market lives in the offseason, and the online offseason is the next step.
- **Live screens.** Some career moments happen in the middle of the host's world work and can't be replayed afterwards: the phone ringing in the carousel, the AD's contract talk, the offseason's decisions. Those now run on the host, as that coach, with their screen drawn on his computer: what the career code prints goes to his client, and what he types comes back. They are the same screens as a career, live. A question waits up to 15 minutes for its player, then takes the career's default. A player sitting on any wait screen is pulled into his screen the moment it's asked.
- **Each player's career now follows the player, not the program.** His inbox, hub and log are kept under his name. When his coach changes jobs, the player goes with him: his seat, the owner list and his copy of the world all move to the new school. Wiring this to the carousel comes with the offseason.
- The room's status no longer waits on the world's lock, so it answers while someone is mid-question.
- **Measured (one machine, Python 3.12):** while a player sat on the "everyone's getting ready" screen, the host's world asked him a question as his coach. The text appeared on his screen, his "yes" came back to the host, and the week then played as normal.
- Not checked: Python 3.8 and ruff weren't available (the touched files parse under the 3.8 grammar, with no new unused imports); Wi-Fi; window mode.

# v51.5 — ONLINE MODE, PHASE 4: YOUR INBOX AND THE PODIUM (preview)
------------------------------------
**The inbox, the press conference and the postgame podium now count online,** exactly as in a career.
- **Moments.** Reading and answering a message, the Thursday press conference and the postgame podium happen on your copy, on the same screens. Each one is recorded as it happens: what you opened, and everything you typed. The host then runs the same conversation as you, so your replies, promises, NIL answers and podium effects land in the official world. The mail and the questions are seeded, so they're the same on both sides. A reply that opens another screen (an NIL offer from a message) travels as one moment; its recruiting moves aren't sent twice.
- **When moments are sent:**
  - In the week, each one goes to the host the moment you finish it, behind the orders you'd made before it, so their order is kept.
  - The postgame podium travels with your game.
- **Every player has his own career on the host:** inbox, hub, presser memory, career log and storylines. The places the game already handles "every human coach" (standing orders and coordinators, recruiting news, year-end mail, promises graded, the Weekly Wrap's storylines) now run once per player.
- A coach who never opens his hub still gets his week's mail. A question the host's world asks with nobody there takes the career's default, and never waits on the host's keyboard. The host's screen no longer shows the world's background work.
- If the world came from a career, that coach's inbox and log go with his program to whoever picks it.
- **Measured (one machine, Python 3.12):** a player went through fall camp and Week 1 using the real screens. He answered all 7 waiting messages, then played and simmed his game. On the host, the same 7 messages were read and answered with the same replies, his postgame podium was applied, and his game matched.
- **Not tested:** the Thursday press conference (same mechanism as the postgame podium), two players at once, Wi-Fi, window mode. Python 3.8 and ruff weren't available (the touched files parse under the 3.8 grammar, with no new unused imports).
- **Not done yet:** the coaching market (Phase 5), the offseason (Phase 6), saving the host's world (Phase 7).

# v51.4 — ONLINE MODE, PHASE 3: THE WEEK (preview)
------------------------------------
**An online week now plays like a Coach Career week.** The only difference is how the week advances.
- **[A] on an online dashboard** runs the career's own flow: fall camp in Week 0, your bowl week, then the week hub (film, inbox, practice, the presser, the game plan). Leaving the hub sends your orders and makes you ready.
- **When everyone's ready, the week kicks off.** Saturday plays on your copy: the show, then your game your way (sim it, big moments, every snap, or watch), with everyone else's games around it. Then the week's results, your Weekly Wrap and the Recap, from the host's world.
- **Your game is the official game.** Every copy seeds a game the same way, and the commentary has its own dice. Everything you type during your game, plus your game settings, goes to the host, which plays it again on its own thread with the screen thrown away. A fingerprint of the result (score, snaps, every player's numbers, the scoring) is compared. If it ever differs, the host's result stands and you're told.
- **Waits:** two screens, for everyone to be ready and for everyone to finish their games. Both move on by themselves.
  - Ctrl+C, or 45 seconds in window mode, offers "not ready after all".
  - The host also gets "don't wait: play it now"; a missing coach's staff plays his game.
- **When two players meet,** neither takes the headset. Both staffs call it from the game plans, and you watch or sim it.
- **Changes behind the scenes:**
  - The host's human coaches are career coaches, so their skill tree, play-calling and difficulty work as in a career.
  - Snapshots no longer carry other players' seat tokens.
  - [M] sim weeks and loading a save are off on an online dashboard.
- **Measured (one machine, Python 3.12):**
  - Two players went through Week 0 and Week 1 using the real screens with typed answers: join, pick, fall camp, hub, ready, kickoff, the game, results.
  - Auburn's coach called every snap (about 180 answers typed during the game); Georgia's simmed.
  - The host replayed both games and both fingerprints matched (Auburn 49-7, Georgia 69-7). Both clients finished their weeks in about 36 s.
  - Separately, the same game played in five separate programs (with and without commentary, with different hash seeds) came out identical.
- **Not done yet:** presser answers and inbox replies don't reach the host's world (Phase 4); the coaching market and the offseason; saving the host's world.
- **Not checked this build:** Python 3.8 and ruff weren't available (the touched files parse under the 3.8 grammar, with no new unused imports); a second computer on Wi-Fi; a game where two players meet; window mode.

# v51.3 — ONLINE MODE, PHASE 2: THE LOBBY (preview)
------------------------------------
**[7] Online on the title screen.** Friends on the same Wi-Fi can now host and join a shared world and pick their programs. The host playing the week arrives next build; until then [A] on an online dashboard only says you're ready.
- **Host a world:** a new world or any save. The lobby shows the address and the 4-digit join code, who's in the room and what each player picked. [S] starts the world. The host plays as a coach too, over his own connection.
- **Join a world:** type the address and the code, then your name and your program. Search by school, part of one or a conference. Coach as the sitting head coach, or bring your own (the Coach Career questions, built on the host from your answers). A program someone already picked is theirs. [W] waits for the start. The address is remembered, and the seat rejoins without the code.
- **Starting turns the world into an online world.** Every program is a player's or the CPU's, as in Commissioner Mode (the same owner list and standing orders, shared rather than copied). Player teams skip CPU recruiting; their standing orders and coordinators recruit. A depth chart belongs to the player, as in a career: no staff re-sort. A program you take over starts with its staff's recruiting board, a week of orders on it, and both coordinators on autopilot.
- If the world came from a career, that coach stays in it, run by the CPU unless someone picks his program.
- **Your copy of the world reads as your Coach Career,** so every screen works as before. It's never saved on your computer, so it can't overwrite your own autosave; [V] says the host keeps it.
- New manual chapter: 34, Online (preview).
- **Measured (one machine, Python 3.12):**
  - Three players (Auburn with the world's own career coach, Georgia with a new coach from the form, Texas with Steve Sarkisian) joined the host's lobby. Each picked, and a second claim on each program was refused. All three saw START within moments, received the world, and drew a dashboard of their own program: right school, right coach.
  - A fourth player went through the real screens with typed answers: address, code, name, search, pick, wait, dashboard, [A] ready. The host saw him ready.
  - The host then simmed two weeks of the online world with three player teams with no errors, about 8 s a week. The adopted program's board and orders were working.
  - Memory is about 130 MB per copy of the world, 170 MB while packing it.
  - The career mode check (two simmed weeks) still ran clean.
- **Not checked this build:**
  - Python 3.8 and ruff weren't available. The touched files parse under the 3.8 grammar, with no new unused imports.
  - A second computer on Wi-Fi.
  - Saving the online world (the host's world closes when the host leaves the lobby or the dashboard; resume comes with Phase 7).

# v51.2 — ONLINE MODE, PHASE 1: THE NETWORK CORE (no menu entry yet)
------------------------------------
The host and client pieces of the LAN shared world. Nothing on the title screen yet (that's Phase 2), and nothing changes in any mode you can play today.
- **`netplay/host.py`**: the world server, on its own thread so the host's screens stay live. It reads out its network address and a 4-digit join code, keeps the seats in the world (saved with it), takes each player's orders through the same validation Commissioner codes use, keeps a ready list, and runs a live feed of what's happening (joins, ready, a new world).
- **`netplay/client.py`**: join with the code and a program, fetch the world, send orders, ready up, follow the feed. The seat is kept in `online.json` next to the game, so dropping off the Wi-Fi or restarting rejoins the same seat.
- **`netplay/sync.py`**: the world travels compressed and loads exactly like a save, then the client's screens point at his own program. **Only join hosts you know**: like a save file, a world from a host can run code when it loads. The host never loads anything a client sends (orders are plain JSON).
- **Refused cleanly, with the reason:** wrong code (and each wrong guess slows the next), a different game version, a different or missing universe file (compared by fingerprint, not just name), a program that's taken or doesn't exist, and orders made on a world that has since moved on.
- **Measured (two processes on one machine, Python 3.12):** every refusal above worked; two seats joined; the client drew its dashboard with its own program; asking again returned "up to date" without resending; orders (board adds, a depth swap) arrived and the host's board and QB order matched the client's; ready showed on the host and in the other player's feed; a quiet long poll waited its full 1.5 s; the saved seat rejoined with the same token. Fall-camp world: 2.9 MB compressed, 0.6 s to pack on the host, 0.5 s to load on the client, 0.01 s to transfer over localhost. Wi-Fi wasn't tested; at typical home speeds 3–5 MB is about 1–2 seconds. (After Week 1 the world measured 4.7 MB in Phase 0.)
- Not checked this build: a Python 3.8 interpreter and ruff weren't available (the new files parse under the 3.8 grammar; no unused imports); a real second computer on Wi-Fi, and the Windows/macOS firewall prompt.

# v51.1 — ONLINE MODE, PHASE 0: ORDER CAPTURE (no networking yet)
------------------------------------
Groundwork for the LAN shared-world mode. Nothing changes in single-player, Commissioner or any other mode you can play today.
- **New `netplay/capture.py`.** On a future online client, everything a coach does during the week becomes orders the host can apply:
  - one-time recruiting moves (an action from a recruit's card, NIL offers and withdrawals, promises, official visits, walk-on invites, summer camp, skill-tree perks, coach development) are recorded by a one-line hook on the function that makes them, in the order they're made;
  - standing state (the board, the standing-orders queue, coordinator autopilot, the depth chart, position changes, the game plan and practice focus, play-calling) is read from the client's world and sent only when it changed, so every screen that edits it is covered;
  - inbox replies and press conferences are noted but not sent yet (they become answers to host items in Phase 4).
  - Offline the hooks are a single check.
- **Order codes (orders.py), additive:** `rec.acts` (moves in the order made: a visit can depend on the NIL offer before it), `rec.now`, `rec.camp`, and a `coach` section (tree perks, development). Position changes in the same code are applied before the depth chart, and the depth chart accepts a player at the position he's moving to.
- **Measured (headless, one machine, Python 3.12):** two career weeks at Auburn. Each week a client copy was made from the host's world, a scripted coach worked the board, queue, autopilot, a card offer then NIL, a promise and an official visit, three depth rooms, a position change, a room reset to the staff, the game plan and focus, and play-calling. The captured orders went over JSON, were validated and applied to the host's copy: board, queue, autopilot, depth chart, positions, plan, focus, play-calling, NIL, promises, visits, offers and hours left all matched, with no validation warnings, both weeks. World snapshots: 11.8 MB raw / 2.9 MB compressed in fall camp, 16.0 MB / 4.7 MB after Week 1; about 0.7–1.1 s to pack or unpack.
- Not checked this build: a Python 3.8 interpreter and ruff weren't available here (the touched files parse under the 3.8 grammar; no new unused imports).

# v51.0 — HOT SEAT AND LAN REMOVED
------------------------------------
- Hot Seat (2–6 coaches taking turns on one screen) and its LAN version (`play.py --lan`, play_lan.bat, play_lan.command) are gone. New Game now offers Coach Career, Athletic Director, Spectator and Commissioner.
- **Hot Seat saves still load.** They become a normal Coach Career with whichever coach was on the keyboard, and the other seats' coaches stay in the world.
- The single-player game runs through one code path now, so changes to the week flow, the offseason and saving don't have to work around shared turns.
- An online mode where every player runs their own copy of one shared world is being designed next.

# v50.1 — RIVALRIES, CONTEXT, AND SMARTER RECRUITING
------------------------------------
**Rivalry games are different**
- In a rivalry game the underdog plays above itself, and the day is less predictable for both teams.
- In a 150-game test the underdog's win rate rose by about 10 points (Iowa State over Iowa: 15% to 26%; East Alabama over Alabama: 31% to 43%). The edge was trimmed slightly after the test, so expect a little less than that.
- A big mismatch is still a big mismatch.

**Every trophy and rivalry (real universe)**
- Added the Foy-ODK Trophy (the Iron Bowl), the Hardee's Trophy (Clemson–South Carolina), the Thompson Cup (Army–Navy), the Magnolia Bowl Trophy, the Illibuck, the Legends Trophy, the Ram-Falcon Trophy, the Paniolo Trophy, the Beehive Boot, the Lone Star Showdown Trophy, the Victory Bell (Cincinnati–Miami), the Gansz Trophy and the George Jewett Trophy.
- Added 21 named rivalries, including LSU–Alabama, Miami–Florida State, Bedlam, the Tiger Bowl and Navy–Notre Dame.
- The Rivalry Trophies screen now lists the great rivalries with no physical trophy too (the Iron Bowl, The Game, the Red River Rivalry...), with who won the last meeting.
- Existing saves pick these up the next time they load.

**A booth that knows the day**
- The broadcast now talks about:
  - who came in hot or cold (streaks, bounce-backs);
  - rivalry heat ("throw the records out");
  - upset alerts when an underdog leads a ranked team in the second half;
  - trap games when a heavy favorite is sleepwalking, especially with a ranked team on deck;
  - bowl-eligibility math, revenge for last year's loss, and where a team sits in the playoff rankings in November.

**The Saturday morning show**
- New versions of 20 storylines that only had one to four, so a long save doesn't hear the same exchange every few weeks. These include rivalry, rematch, revenge, trap, conference race, shootout, defense duel, bowl push, big favorite, risers and fallers.

**Headlines that read like a sports desk**
- The verb fits the game: routs, handles, holds off, edges, survives, outlasts in overtime, stuns.
- The line adds the context: keeps or takes back a trophy, wins a named rivalry, stays unbeaten, a winning streak, snaps a skid, bowl eligible, a ranked team's first loss, a long losing streak.
- Each game always gets the same headline.

**Smarter CPU recruiting and portal**
- Staffs build their boards around their high-school pipelines and their own state and region.
- By November, staffs stop pouring hours into recruits who are clearly going elsewhere.
- Weekly hours go where a staff can actually win: its share of the recruit's interest against the leader's, with hard commits elsewhere mostly left alone.
- Kickers and punters are almost never blue-chip prospects any more.
- **Transfer portal:** players follow the head coach who recruited them when he moves to a new school.
- **Transfer portal:** staffs no longer read a transfer's true rating. They evaluate film, so their reads miss by a little (good recruiting staffs) or a lot (weak ones). The best transfer doesn't automatically land with the best team.

# v50.0 — THE WHOLE STORY, AND SEASON FORM
------------------------------------
**Program history: every season, nothing cut off**
- [Y] on any team page opens the program's whole history, a page at a time: [N] next, [P] previous, [O] oldest or newest first.
- **Seasons:** every season with record, conference record, league, final rank, postseason, head coach and recruiting class. ★ marks conference titles.
- **Coaches [C]:** each coaching era with record, win percentage, ranked seasons, playoff trips, conference titles and national titles.
- **Trophy case [T]:** titles, bowl wins, Heisman and award winners, All-Americans, and every draft class with its first-rounders.
- **Series [V]:** the all-time record against every opponent, rivals first, with the current streak and the last meeting.
- The program now keeps its own record of every season. Fired coaches who age out of the candidate pool no longer take a school's history with them. Older saves rebuild what they can from coaches' records and the game archive.

**Coach careers: every season, every job**
- [F] on any coach's page opens his full career, a page at a time: every head-coaching season, each job's totals, his coordinator years, every move and why, and his career before this world began (when the universe file has it).
- Type "Texas history", "program history" or "coach career" anywhere to jump there.

**Season form (team momentum)**
- Every result moves a team's run of form. Wins push it up and losses down; upsets and statement wins count more, and so do blowout losses. A narrow loss to a top-10 team barely hurts.
- It fades by about a third each week, so it reflects the last three or four games, and every season starts level.
- On game day it's worth up to +1.2 rating points for a red-hot team and −1.0 for a reeling one, about a field goal.
- **Guard rails:** a hot team gets half the boost against a much weaker opponent (the trap game). A reeling team carries only half the drag in a rivalry game or against a ranked opponent (nothing to lose).
- In a one-season test at midseason, form ranged from −0.87 to +0.94 and the median team was level (Red-hot 10, Rolling 34, Steady 43, Sliding 22, Reeling 29). The regular season ended with no undefeated teams and four winless.
- Team pages show it ("Season form: Rolling ▲ (last 5: W W L W W)"), and so does the Top 25 in the story kit.

# v49.5 — NO MORE BUTTON ROW
------------------------------------
- The window (play.py) no longer builds a row of buttons above the input from the keys it finds on screen. It took up room and often guessed the wrong keys.
- Each screen's own command lines now always stay visible at the bottom of the screen, instead of being folded into that row.
- Keys on screen are still clickable, and typing works as before.

# v49.4 — STORY KITS IN YOUR UNIVERSE'S NAMES
------------------------------------
- Story kits no longer describe the league as a simulated or fictional world. There's no "this world's AP poll" or "this world's Heisman".
- The whole kit now goes through your universe file's names. With the real universe it reads College Football Playoff, CFP Rankings, AP Poll, Heisman, NFL Draft, SEC, Big Ten, LSU, Auburn, Clemson, and so on.
- With the built-in world it keeps the built-in names.

# v49.3 — BOX SCORES IN THE STORY KIT
------------------------------------
- New story-kit section, on by default in season: the **full box score of every game a top-40 team played** that week. It includes the line score, player of the game, attendance and weather, team stats, every player's line, the scoring summary and injuries.
- The top 40 comes from the full poll order behind the Top 25, this week's or last week's, so a team that just fell out still counts. Teams ranked 26–40 are noted as "just outside the Top 25".
- That's about 35–40 games and roughly 24,000 words, so a full kit is now around 28,000 words. Toggle it off for a shorter kit.

# v49.2 — THE RECAP, ALL YEAR
------------------------------------
**A Recap for every moment (Spectator mode)**
- **In season:** the headline games, the polls, the Golden Helmet race, players of the week, the headlines and the recruiting wire, after every week.
- **After the title game:** the season in review, with the champion, the whole bracket, conference title games, the big bowls and the final poll.
- **The offseason, one stop at a time.** Spectator mode now stops at December (the coaching carousel and AD moves), January to April (awards, All-Americans, the Pro League Draft), the transfer portal, and National Signing Day. There's a Recap at every stop. The stages and results are exactly what they were; you can just see them now.
- **The Preseason Desk:** the preseason poll, the Golden Helmet watch list, new head coaches, conference contenders and the games of the year. It opens when the new season begins, and [C] on the dashboard opens it any time.

**Story kits that know where they are**
- The prompt says exactly where we are: the week of the regular season and what kind of stretch it is, conference championship weekend, a playoff round, or the offseason month with what's done and what's still to come.
- It also says what comes next, and whether the committee's rankings are out.
- **Real-network editorial rules.** Every game is sorted into LEAD, ALSO NOTABLE or REFERENCE: ranked matchups, upsets of ranked teams, top-15 teams in one-score games, rivalries, conference title games and playoff games lead. A mid-major blowout stays in the reference list, so the writer knows everything but covers what matters.
- **Since the last edition.** News you already curated isn't repeated. Headline games from weeks you skipped are added, and the writer is told to pick up the story from the previous edition. The first kit ever tells the writer to set the scene.
- **New sections for the time of year:**
  - In season: hot seat watch, recruiting news (4- and 5-stars).
  - Offseason: the season in review, carousel & AD moves, awards & All-Americans, the draft (all of round 1 and the schools that produced the most picks), the portal (the biggest moves with last season's stats, and the winners and losers), signing day (class rankings, the top 30 recruits and where they went, flips).
  - Preseason: preseason poll, new head coaches, conference contenders, games of the year, returning All-Americans.
- The writer is told to go long: 2,500–4,000 words in season, and 3,000–4,500 in the offseason and preseason.

# v49.1 — THE RECAP, AND STORIES FOR AN AI WRITER
------------------------------------
**The Recap (Spectator mode)**
- After every week you watch or simulate, the Recap opens on its own. After a multi-week sim it shows the last week.
- It has the scoreboard with upsets flagged, the Media Top 10, the Golden Helmet watch, players of the week, the NP Playoff top four (once the committee is out), and the headlines and recruiting wire.
- [S] shows every score, [T] the standings, [R] recruiting.
- [C] on the spectator dashboard opens it any time, or type "recap".

**Curate stories**
- [C] on the Recap. Toggle what goes in: game scores, headlines & notes, recruiting news & class rankings, conference standings, the Media Top 25, the NP Playoff Rankings, the Golden Helmet watch, players of the game & of the week, and notable stats (season lines for about 250 of the best players).
- Pick the show: national network (ESPN-style), conference podcast (you pick the conference), team podcast (you pick the team), or a Josh Pate-style independent show.
- Enter puts a writing prompt and every fact you chose on your clipboard, and in story_kit.txt. Paste it into Claude and get the article or the episode, written from the real results.
- The prompt tells the writer to use only the facts given and never invent scores or stats. Conference and team shows put their own teams first in every section.
- Your picks are remembered.

# v49.0 — HIRED ON A RÉSUMÉ
------------------------------------
Schools used to hire coaches by peeking at their ratings. Now nobody knows how good a coach really is until he coaches.

**Hiring on a résumé**
- An AD sees only what the world sees. That means results against what the roster should have done, the level he did it at, and rings and playoff trips. It also means his recruiting classes, a coordinator's units, his record before this world began, and how he interviews.
- A sharp AD reads that paper in context; a weak one reads last season, the rings and the interview. The hot name sometimes flops, and the quiet hire sometimes turns out great.
- Coordinators are hired on their résumés too, and pay follows the résumé.
- Coach pages show a **Résumé** grade: how the profession sees his record, not a rating.
- In Athletic Director mode your search shows RES (résumé) and CLS (his classes) instead of OVR and RCT. Opening a candidate shows only what an AD can see.

**Athletic directors are people, and a market**
- Every AD has a style, two of 16 character traits, an age, and a hidden competence. The traits include Numbers Person, Headline Reader, Alumni First, Old Network, Penny Pincher, Big Spender, Loyal to a Fault, Itchy Trigger, Youth Movement, Old School, Coordinator Scout, Gambler and Campus Politician.
- Competence shows in how well he reads a résumé and, over the years, in how his hires turn out.
- Presidents judge ADs on football against expectations and on the coaches they hired. Bad ones are fired into the pool of available ADs.
- A good AD at a smaller school gets hired away, and his job opens. Old ADs retire.
- Deputies, small-school ADs, outsiders and former coaches enter the pool every year.
- New screen: Coaches → [A] Athletic Directors. It lists every AD, the available pool, every move, and a profile with his earlier jobs and whether each of his hires was a hit or a miss.

**Coaches age differently**
- Every coach has a hidden age when the game starts to pass him by. Most start slipping in their early sixties.
- About one in six is fading by his mid-fifties. About one in ten stays great into his seventies, and keeps coaching longer.

**Checked:** a 3-season spectator test from the shipped 2026 world, with offseasons, hirings and the AD market running end to end.
- Hires were a real mix: a 90-rated coach hired on a B- résumé, and a 60 hired on a C+.
- The public résumé tracked true quality at about 0.8–0.9 correlation.
- After the test, AD firings were softened. The year everyone is first judged produced too many moves; it's now about 5% fired a year, plus retirements and the moves that follow.

# v48.1 — PARITY WITH A REASON
------------------------------------
Over long saves the same handful of programs kept winning, because star ratings decided almost everything and nothing shook loose. Now there's more movement at the top, and every rise or fall has a cause you can point to: a coach, or players.

**Stars can miss**
- About 10–12% of 1- to 3-star recruits are late bloomers, and about 9% of 4-stars and 12% of 5-stars have already peaked. Nobody is told which is which.
- A staff that develops players well gets more out of the bloomers and limits the busts.

**Teaching matters more**
- A coach's development rating has a bigger effect on growth: a 90 developer now gets about 44% more out of a player than a 50, up from about 32%.

**A coaching change rattles the class**
- When the coach a recruit committed to leaves, that recruit is much more likely to flip, even to a school he liked a little less.

**The pros come calling**
- A college coach who just won a title is a Pro League target: roughly 6–16% a year depending on recent titles and playoff runs, up from a flat 2%. Dynasties end the way they do in real life.

In an 18-season test of the first three changes (2026–2043), compared with v48.0:

| | v48.0 | v48.1 |
|---|---|---|
| Different national champions | 6 | 10 |
| Rises from outside the top 25 to the top 10 | 28 | 37 |
| New top-10 teams per year | 4.6 | 5.3 |
| Distinct top-10 teams, first decade | 27 | 34 |

Champions were still built on players and coaching: their median talent rank was 3.5 and their median coach rating was 90. That test showed two coaches rated 92–93 winning 6 and 4 titles; the Pro League change is aimed at that, and it hasn't been measured over a long save yet.

# v48.0 — GREAT COACHES ARE RARE AGAIN
------------------------------------
After a few decades every program had a coach in the 90s, even in the Group of Five. Coaches had stopped mattering and teams stopped moving. In a 15-season test on the old rules, the median head coach climbed from 70 to 89, and the number rated 90 or better went from 2 to 65. How good a coach was barely tracked how his team did any more.

**Potential is a tier now, not "a little more than today"**
- **Ordinary (about 58%):** tops out around 67. Plenty of coaches finish long careers in the 60s.
- **Good (about 29%):** tops out around 76.
- **Very good (about 10%):** around 84.
- **Elite (about 3%):** around 92.

Young coordinators get a slightly better draw. Position coaches promoted to coordinator start lower (running a room isn't running a side of the ball). Graduate assistants no longer arrive with huge upside.

**Coaches grow more slowly**
- Winning still makes a coach better, but at about 60% of the old rate.
- The climb past 85 is steep.
- Decline starts at 60 instead of 62.
- A coach's sideline strengths (motivation, adjustments, discipline) now grow and fade with him. Before, they shrank in relative terms as he improved.

**The profession doesn't inflate**
- Every offseason, and again after the new hires, coaches are measured against the field. The best stay the best, and the order never changes.
- The middle of the pack stays around 70, about one in ten head coaches is 84 or better, and only a handful are 90 or better.

In a 15-season test under the new rules, the head-coach curve held steady every year:

| | Old rules, year 15 | New rules, years 1–15 |
|---|---|---|
| Median head coach | 89 | 70–73 |
| 10th percentile | 70 | about 58 |
| 90th percentile | 92 | 82–85 |
| Coaches rated 90 or better | 65 | 3–5 |
| Group of Five median | 88 | 62–71 |

How good a coach is keeps predicting how his team does. The correlation between coach rating and win percentage stayed around 0.45–0.6; under the old rules it fell to about 0.1–0.2.

**Coaches matter on Saturday**
The head coach's own rating is now part of the game-day edge. An elite coach is worth about three points a week over an average one, and a poor one costs about two. Before, only his deviations from his own rating counted, so a 95 and a 60 coached the same game.

**Your save**
- Loading an older world re-rolls every CPU coach's ceiling from the new tiers.
- If that world's coaches had drifted into the 90s, it puts them back on a realistic curve, keeping their order.
- Your own coach is never touched.

# v47.1 — THE BOOTH, PROOFREAD
------------------------------------
I generated play-by-play for 200 games (about 73,000 booth lines), scanned all of it for broken lines and read several full games. Fixed:

**Pass calls**
- Garbled pass calls are gone: "puts it up up the seam", "airs it out out to the flat", "looks a quick throw for", "airs it out underneath".

**Touchdown reactions**
- A touchdown reaction now fits the throw. "Blown coverage. Nobody carried him deep." and "Nobody within ten yards of him" are only for deep balls.
- Screens, slants and short throws get their own lines ("He caught it short and did the rest himself").

**Game state**
- "Has taken this thing over" and "in control" are no longer said about a one-score lead.
- "The whole game has flipped" only after a run that took a team from behind.
- The crowd-noise take ("The road team can't hear a thing. Watch for procedure penalties.") is only said when the road team has the ball.
- After a game-ending interception in overtime, the booth no longer says the defense is "going to make them pay".
- "We're going to overtime!" is said once, not twice in a row.
- At the end of the half it's a knee, not "Victory formation".
- "That's 7 plays on this drive, 21 yards. Long drives like this demoralize a defense." now only comes after a drive that actually covered ground.

**Schedule talk**
- Next week's matchups, next week's marquee game and last week's results come up once a game instead of up to five times.
- Games on a different day are no longer called "later today". A Thursday-night booth says "on Saturday".

**Small fixes**
- "1 timeouts remaining", "1 touchdowns", "1 sacks".
- The mascot bit no longer claims the mascot "just ran" a flag when nobody had scored.
- A fourth-down tendency line that didn't follow from what came before it ("Old school. Punt it…").

# v47.0 — RELEASE
------------------------------------
A testing and polish build.

**How it was tested**
- An automated player ran the game end to end through the real menus: new game, world build, full seasons, the offseason and into the next season. It pressed every key it found along the way.
- It covered Coach Career (including the real 2026 player database), Athletic Director and Spectator modes.
- It ran on both Python 3.8 and Python 3.13.
- A screen crawler opened every key on every dashboard tab.

**Fixed**
- **Python 3.8–3.11 couldn't run the game.** Three modules (career, the offseason calendar, spring ball) and two v46 additions used syntax or functions only newer Pythons have. Every module now compiles and imports on Python 3.8, and full seasons run on it.
- **The Campus Countdown pregame show crashed** whenever a player was asked "How did you prepare for [opponent] this week?" (a missing answer line). All interview lines are now checked.
- The non-conference scheduler's distance column, the Media Center hot-seat and stat-leader panels, and the Weekly Wrap's scoring clock were tidied.

**Release cleanup**
- No saves ship in the zip. The saves folder is empty and the game creates your first autosave.
- No league exports or passwords ship either.
- The real 2026 universe and the real-player databases (476 and 876 players) are included unchanged.

# v46.1 — REAL-LIFE POLLS, AND A MEDIA CENTER DASHBOARD
------------------------------------
**The media poll moves the way the real one does.** Voters now start from last week's ballot and react to each result:
- **Losses** cost spots according to who they came to:
  - a close loss to a better team costs two or three spots;
  - a loss to a lower-ranked team costs five to eight;
  - a loss to an unranked team costs seven or more, and most teams below No. 15 fall out;
  - a loss to an FCS team costs most of the poll.

  The second and third losses cost more than the first, and a title-game loss to a good team is forgiven a little.
- **Wins** over a ranked team buy a few spots, and a top-five scalp buys more. Nobody leaps past more than four or five teams that won.
- **Byes:** a top team on a bye keeps its spot.
- **Upsets:** an unranked team that beats a top-12 team usually enters the poll in the teens or low 20s. Before, it almost never got in.
- **Bowl season:** there's no vote during the bowls, as with the real AP poll. The poll after the conference title games stands until the final poll.
- **The final poll:** the national champion is No. 1 and the runner-up No. 2, then the semifinal and quarterfinal losers. Before, the champion could finish second.
- **Group of Five:** slightly less of a discount, so three to five Group of Five teams make the poll in a typical year.

**The Playoff Rankings committee**
- It reads the loss column in tiers: each loss costs more than the one before.
- It stays consistent from week to week: a loser drops at least a few spots, a winner doesn't fall far, and nobody leaps more than four to six spots. Before, a conference champion could jump 12 or more.
- A Group of Five title counts less than a Power title.

Measured over several simulated seasons, the media poll and the committee rankings share about 23 of their 25 teams, and teams differ by two or three spots on average. That is close to how they compare in real life.

**The Media Center is a dashboard now.** Four pages of panels, like the main menu:
- **The Week:** the wire, players of the week, upsets and statements, and next week's big games.
- **The Races:** the playoff picture, the Golden Helmet, the other awards, every conference race, and the top 10 in both polls.
- **The Numbers:** stat leaders, team leaders, the toughest schedules, and the unbeaten and streaking teams.
- **The Sport:** the hot seat, who's hurt, the coaching carousel, off-the-field news, and the recruiting wire.

Every panel shows the key for its full screen, and every key works from every page. New full screens: **Upsets & Thrillers** (any week), **Games to Watch** (with favorites and win chances) and **Conference Races**. The Media tab on the main menu now also shows the week's upsets and next week's big games.

# v46.0 — THE STORY, DEEPER
------------------------------------
Every Coach Career feature from v45 now goes much further.

**The Weekly Wrap has five more pages**
- **G, the game:** the line score, team stats side by side, unit grades (offense, defense, special teams), the stars on both sides, and the scoring.
- **C, the conference race:** games back, streaks, who you need to lose, and your odds in every conference game left.
- **P, the playoff picture:** the field if it were picked today, the bubble, your résumé, and your chances of winning out.
- **N, next opponent:** a scouting page with their form, how the units match up, their leaders, injuries, the series and the line.
- **F, fans and the locker room:** the fan pulse and its trend, message-board posts, chemistry, morale, and who's unhappy.

**Storylines: 35 kinds, read four ways**
- New stories: win streaks and skids, upsets both ways, revenge games, shutouts, routs, comebacks, overtime and rivalry trophies.
- Landmarks: bowl eligibility, ten wins, the Top 25 and No. 1.
- Player stories: stat streaks, slumps, school-record chases, the Golden Helmet race, true freshmen, transfer debuts, returns from injury, and All-Americans.
- Off the field: big commitments and flips, and moves in your coaching tree.
- Ways to read them: by week, player arcs (every story about one man), the year in ten stories, or a filter.

**Heads Up, the alert center**
- Recruiting, roster, your job, schedule and money, sorted URGENT, SOON and FYI.
- New alerts include visits this week, signing day, unhappy starters, cold chemistry, the seat, your contract, story deadlines, trap games, rivalry week and NIL overruns.
- Dismiss alerts you've handled.

**Achievements, the legacy score and the Hall of Fame track**
- 109 achievements in nine groups, in Bronze, Silver, Gold and Platinum tiers.
- Progress bars for the counting ones, and hidden ones to find.
- Achievements are worked out from every game you've coached, so old saves earn what they already did.
- A legacy score, made of achievement points plus your résumé, puts you on a track from "Just getting started" to "Mount Rushmore".

**Report cards**
- Up to 13 graded areas, now including rivalry, home field, culture, discipline, money and program buzz.
- Each area is weighted by your AD's style, with trends against last year.
- A letter from him, plus the booster president, the beat writer and the student section.
- Real consequences: an A earns trust and cools your seat; a D or F costs you.
- A mid-season progress report after Week 7.

**Selection Day and bowl week**
- Selection Day adds the chair's statement, every team's case, the bracket, the debate (last four in and first four out), bids by conference, every bowl by tier, and your path with title odds.
- Bowl and playoff weeks add the matchup, the line, both schools' bowl history, and five days of decisions (practice, community day, media day, the last night) that land on the game-day plan.

**Coaching tree:** each coach has a page with his career and your games against him. Also new: the second generation (your assistants' assistants), the sport's biggest trees, and stories when a branch moves.

**Non-conference scheduling with real deals**
- Book games years out: home-and-home, 2-for-1, guarantee games, paycheck games and neutral-site kickoffs.
- Each opponent has odds of saying yes, and the money flows through your NIL pool.
- Buyouts, and an AD who reacts to what you book.

**Story starts: fifteen of them, each with three chapters and deadlines.** New starts include Homecoming, Clean Up the Mess, The Climb, The Boosters' Pick, Promoted From Within, No Quarterback, Fallen Giant, Little Brother, Dark Horse, Win Now or Else, The Long Game and Surprise Me. Finish them all for the epilogue.

# v45.0 — A COACH CAREER WITH A STORY
------------------------------------
**Every week**
- **The Weekly Wrap.** After every game you play, one screen shows what your week changed:
  - the result and your player of the game;
  - the poll and the Playoff Rankings, before and after;
  - your hot seat and AD trust, before and after;
  - recruits who committed, warmed up, cooled off, or changed leaders;
  - new injuries and players back;
  - the week's storylines, and anything you should act on.

  Settings → W turns it off.
- **Player storylines.** Your season now tells its stories:
  - breakout games, and big days;
  - season milestones: 1,000 yards, 3,000 passing, 10 sacks, 100 tackles;
  - walk-ons who become starters, the QB battle in camp, and QB changes;
  - the captains' vote, Senior Day with the class honored by name, and starters lost to injury.

  Each story also goes in the player's career timeline. Tab 3 → N, or L on the Weekly Wrap.
- **Alerts on the This Week panel:**
  - a board recruit who commits elsewhere;
  - a recruit who puts you in his top 3 or drops you from it;
  - a commit who's wavering;
  - a starter who's a real transfer risk;
  - next year's non-conference schedule, if you haven't set it.

**The season's big moments**
- **Selection Day.** After championship week the playoff field is revealed from 12 to 1, with the first four out. Then you see your seed (or your bowl) and the bowl lineup.
- **Bowl week.** Your bowl gets its own screen: the site and date, the bowl's lore, the week's trip, and who's sitting out on both sides (opt-outs and injuries).
- **The AD's report card.** At the end of every season your AD grades you:
  - winning against what this roster should have won;
  - big games, the conference, recruiting against what this program should sign;
  - development, the stands, the postseason;
  - an overall grade, the goals, and what he wants next year.

  Every card is kept.

**Your career**
- **Legacy & trophy case** (tab 6 → L):
  - national and conference titles, playoff trips, bowl wins and Coach of the Year awards;
  - your players' Golden Helmets, All-Americans and first-round picks;
  - every stop with your record there;
  - retired jerseys (Golden Helmet winners and two-time All-Americans), and a statue after 20 seasons or 3 titles at one school;
  - **19 achievements**, from First Win and Giant Killer to Back to Back and Cast in Bronze.
- **Your coaching tree** (tab 6 → W): every coordinator and position coach who has worked for you, what he did under you, and where he is now. For those who became head coaches it shows their record and yours against them. (The perks tree you spend points on is now called the Skill tree.)
- **Non-conference scheduling** (tab 2 → N):
  - choose next season's philosophy: an easy start, balanced, tough (two Power games and no FCS) or national (three Power games);
  - ask for a neutral-site **Kickoff Classic** against a Power program in Week 1, at a pro stadium;
  - name up to three programs you want on a home-and-home.

  Your AD books it when the season ends. The schedule marks the opener.
- **Story starts:** on the first-job screen, S picks one:
  - **The Rebuild:** one of the ten weakest rosters, with a patient AD;
  - **The Hot Seat:** a program that expects to win and hasn't, with a win-now AD, and you start warm;
  - **Replace a Legend:** a blue blood whose coach just retired, with a big-game AD and every loss compared to his.

**Fixes**
- Changing jobs could crash in a career whose coach took over a sitting head coach (no career log on file). Fixed everywhere the log is written.

# v44.1 — A CLEANER, EASIER COACH CAREER
---------------------------------------
**Finding things**
- **Go to anything:** on the dashboard, type / (or just start typing) and name a screen ("depth chart", "board", "standings", "hot seat"), a team ("Texas" opens its page, "Ohio State schedule" its schedule), a player or a coach. One clear match opens straight away; otherwise you pick from a short list.
- **THIS WEEK on Home:** what's waiting on you, each with the keys that get you there: unread messages, an empty board or unplanned recruiting hours, whether you've set a game plan, hurt starters, the staff's depth ideas, coaching-tree points to spend. In Coach Career it replaces the Team panel, which still lives on the Team tab.
- **Every screen shows its way home:** a screen opened from a tab says so on its header ("◂ TEAM TAB").

**The look**
- **Bars:** rating and progress bars are slim lines on a faint track instead of heavy blocks, on every screen.
- **Commands:** the schedule, the week hub, the Top 25 and the standings use the same command strip as the rest of the game.
- **Tables that ran past the screen** now fit: standings, the Top 25, the Heisman race, the hot seat, the injury report, the schedule and the recruit finder.

**The window (play.py)**
- **One set of commands:** a screen's command lines fold into the button row instead of appearing twice.
- **The buttons say what they are:** the main thing to do next is green and comes first, risky moves are outlined in red, and ways out are quiet.
- **More room:** the prompt isn't repeated inside the screen, and a screen that's a little too tall shrinks to fit instead of scrolling.
- **Light theme:** the charcoal header bars and gray text now turn light too, so headers no longer disappear.
- **Text:** a cleaner monospace font where you have one (JetBrains Mono, Cascadia or SF Mono) and slightly more line spacing.

# v44.0 — COACH CAREER MENUS, REVISITED
--------------------------------------
I went through every Coach Career tab and menu screen by screen, and fixed what was confusing, missing or a chore to reach.

**Schedules and rankings**
- **Your schedule has ranks.** Every opponent shows his rank: the poll at kickoff once a game is played, and this week's poll for games still ahead. A new THEM NOW column has each opponent's record and rank today (Mississippi was #14 when you played him and is #17 now). The columns line up again, and every game is numbered.
- **Moving between schedules:**
  - on any schedule, [T#] opens that opponent's team page, [S#] his schedule, and [O] any team's schedule;
  - the Schedule tab has [G] Another team's schedule;
  - the Top 25 and conference standings take [#] for a team page and [S#] for that team's schedule;
  - the roster screen takes [S];
  - the week hub takes [T] for the opponent's page and schedule and [S] for yours.
- **The dashboard's schedule panel** shows open dates as BYE, and played games carry the rank at kickoff.
- **Standings** show each team's poll rank. The column that read OVR (it was the overall record) now reads ALL, and "ordered by prestige" only shows before any games are played.
- **The week hub** shows both ranks and the right site: "#3 Alabama at #16 South Carolina", not "vs".
- **Scoreboards** explain their marks: c conference, N neutral, F vs FCS, ! upset, and that ranks are at kickoff.

**Team page and players**
- **Team page:** new Last game and Next game lines, with ranks. Long lines (home field, play-callers, captains) use the full width instead of being cut off. Its 15 keys are grouped into three rows: team, program, history.
- **Player card:** [N] and [P] walk the position room in depth-chart order.
- **Roster:** [H] opens your depth chart.
- **Practice report:** [D] opens the depth chart, and the note no longer points to screens that don't exist.
- **Depth chart:** [B] goes back, like everywhere else.

**Fixes**
- **My Career crashed** for a coach who took over the sitting head coach (no background on file). Fixed.
- **Records:** the coach profile said "no games coached" and My Career said 0-0 at 6-0 mid-season. Both now count the season in progress. "Records tracked from" uses your world's first year instead of always 2026.
- **The offseason hub's Last Season panel** read 0-0 with no stats in a world's first offseason. It now shows the real final record, rank and stat lines. Its class-rank line is labeled.

**Smaller fixes**
- National Champions says so when no champion has been crowned yet, instead of showing an empty table.
- The carousel news calls mid-season firings "the 2026 season so far".
- Transfer Watch has a title and column headers.
- The injury report's column reads LOOK when your staff speaks in words.
- Players of the Week, rivalry trophies, the playoff projection, Pursue a Job and the coordinator list no longer run columns together or cut words off.
- My Career's empty story section says what will appear there.

# v43.9 — EDIT THE RANKINGS
-------------------------
- **Edit the media Top 25 and the NP Playoff Rankings yourself.** You can do it from the Rankings tab ([E] Edit the rankings), the rankings menu (the Commissioner Desk's too) or the Playoff Rankings screen ([E]). In the editor you can:
  - move a team to any spot;
  - swap two teams;
  - add an unranked team at any spot;
  - drop a team out of the top 25;
  - undo your changes before saving.
  You can pick a team by its rank or by its name.
- **What an edit does:** your order replaces the current one, and the website shows it on the next export. Next week's vote starts from your order. Voters still move teams a step at a time, so your order carries forward and isn't thrown away.
- **Changing the playoff field:** if you edit the final Playoff Rankings after Selection Day but before the first round, you're asked whether to re-seed. A re-seed redoes the playoff field, the seeds and the bowls from your order. Conference champions still get their automatic bids.
- The Playoff Rankings can only be edited once the committee has released them (after week 9). Before that, the playoff reads the media poll.

# v43.8 — WEBSITE: BOX SCORES AND PLAYER PAGES
---------------------------------------------
- **Box score for every game:** every played game on the Scores page, the home page and each team's schedule links to its box score. It shows the line score by quarter, attendance, the scoring summary with the running score, team stats side by side (first downs, yards, third and fourth downs, red zone, turnovers, penalties, possession) and each team's passing, rushing, receiving, defense, kicking, punting and returns. A drive chart is folded at the bottom.
- **A page for every player:** click any name on any roster or in any box score. It shows his size, class, hometown, recruiting stars, the approximate tier and traits, this season's stats, a game-by-game log that links to each box score, and his career totals year by year. It still shows no ratings.
- **Your own players:** the staff card now has the game log too. A player page for one of your own players links to the full staff card.
- The website gets one small file per week of box scores, and loads it only when someone opens a game.

# v43.7 — COMMISSIONER MODE, PHASE 8: READY FOR A LEAGUE
---------------------------------------------------------
- **[N] League setup on the desk:**
  1. title and links;
  2. members from a CSV in the imports folder (Discord name, school, and optionally the coach form's answers, so a new coach is built for him), with any problem rows listed;
  3. the first website and its passwords.
- **COMMISSIONER_GUIDE.txt:** setup, the every-cycle checklist, what's open in each cycle, adding and removing people, troubleshooting.
- **The website's Guide page:** how a cycle works, the season and the nine offseason cycles (with what you can send in each), what the staff's words mean, recruiting hours, your job security.
- **Build stamps:** the title screen and every save header carry the build (v43.7) and the league id; the website shows the build on its Guide page.
- **Hosting walkthrough** in the MANUAL rewritten around GitHub Desktop (and a custom domain).
- **Bots are about 6× faster** writing a cycle's codes.
- **Release checks:**
  - **Two full years:** 138 bots played two seasons and offseasons into a third season, with joins (mid-season and mid-offseason), firings, departures and inactivity. There were no crashes and no screen opened. Every roster week left every room exactly at size.
  - **Cycle times:** about 5 s on average to run a cycle (32 s for the coaching carousel), 3-7 s to import, about 25 s to write the website.
  - **Saves:** saves from v42 (Coach Career) and every Commissioner build since v43.0 load, migrate and run a cycle.
  - **Code fuzzing:** 3,000 mutated codes (flipped, cut, padded, swapped characters, another team's signature) were all rejected, as were stale and key-reset codes.
  - **Leak scan:** 166 public files and every locked team file are clean.
  - **Website on a phone:** every page and tab works at phone width with no errors.
  - **Other modes:** they play exactly as before.

# v43.6 — COMMISSIONER MODE, PHASE 7: THE OFFSEASON CALENDAR
--------------------------------------------------------------
- **The offseason runs as nine cycles,** in the same order as Coach Career's calendar, with members' orders between them:
  1. coaching carousel and staffs
  2. awards, the draft and winter workouts
  3. Portal Window I opens
  4. portal market and deadline
  5. the signing push
  6. National Signing Day (the classes arrive)
  7. roster week (the new year begins)
  8. spring ball and A-Day
  9. Portal Window II and summer

  Fall camp → Week 1 is the cycle after that.
- **One offseason, two ways of running it:** the game's offseason is now a list of stages (season.OFFSEASON_STAGES). Every other mode runs them back to back, and that matches the old single call exactly (same world, same seed, same result). A Commissioner league runs them one per cycle, and re-running a stage from the same save gives the same result.
- **Portal (My team → Portal):** talk to your own players who entered (with a raise if you like; Coach Career's retention odds), and offer up to 8 players on the board a spot with NIL. Send nothing and your staff works the portal for you. Other programs' players show approximate tier words.
- **Signing push:** one more full recruiting week in the offseason: your standing orders, coordinators and visits run.
- **Roster week (My team → Roster week):** the new class is on campus. Move players to new positions (the staff's ideas are shown), cut anyone. Then every room is trimmed to its size and walk-ons fill the short ones.
- **Spring (My team → Spring):** choose the emphasis (fundamentals, competition, young players, physicality, chemistry, passing game) and up to three position battles to watch. Both practice blocks and A-Day run on the game's own spring code, then your spring report shows stock up, stock down, the A-Day score and film, and injuries.
- **Portal Window II** runs league-wide after spring, as in Coach Career.
- **Other changes:** offseason cycles don't count as missed cycles. The website opens the tab that's live each cycle.

# v43.5 — COMMISSIONER MODE, PHASE 6: STAFF, MONEY, NIL AND THE DRAFT
-----------------------------------------------------------------------
- **Staff (My team → Staff):** your staff with ages, ratings, pay, and in the offseason a box to let a coach go. For every chair (OC, DC and the eight position rooms) you keep a ranked list of up to 10 names to call if that chair opens. The market shows what your staff knows before anyone calls: public buzz, the résumé, potential, personality and the coach ratings the game shows. Coordinators come with your best package: the most money, years, play-calling, the assistant-head-coach title, a head-job out-clause. Position coaches come with a premium of 0, 15 or 30%.
- **The search runs on Coach Career's rules, headless:**
  - Each candidate's interest and terms come from coord_search.profile.
  - Your package is judged by coord_search.evaluate; his agent's counter is accepted if it fits inside your max.
  - His school's retention bid is topped only if your max allows it.
  - The AD's funding check applies.
  - If nobody on the list says yes, the AD hires, exactly as when you hand him a search.
  - Your let-go orders are carried out right before the staff carousel opens. The AI no longer fires or cleans out a member's coordinators.
  - The website's "What happened" list shows every call: who said no and why, who stayed for a counteroffer, who you hired and on what deal.
- **Money (My team → Money):** build up recruiting or training facilities (the AI no longer builds for members; the stadium stays the AD's call for now). Find the Money asks, with Coach Career's odds and its once-a-year rule:
  - a player takes 25% less NIL
  - a coordinator takes 15% less, a position coach 10% less
  - next season's buyouts are spread over three years
- **Season end (My team → Season end, after the title game):** each NIL raise demand (pay, counter or refuse, with what the staff would do and the room in next year's pool) and each draft-eligible junior (stay, go, or his call: it moves his odds, as in Coach Career). Unanswered ones are handled by the staff as for any program.
- After logging in the site opens the tab that's live this cycle.
- No screen opens anywhere in the offseason for a Commissioner league (tested with input disabled).

# v43.4 — COMMISSIONER MODE, PHASE 5: THE COACHING MARKET
-----------------------------------------------------------
- **job_market.py**, shared by Coach Career and Commissioner Mode. A job is open (no coach, or an interim finishing the year) or could open (the coach is within 10 points of his AD's firing line). Your standing for a job is where you'd land on that AD's list among the coaches he could actually land, judged the way the carousel judges everyone: their first call, on the shortlist, in the conversation, a long shot, or not on their list.
- **Coach Career: Coaches → Pursue a job.** Tell your agent to call up to three jobs a winter. When the carousel reaches one that opened, the AD decides: the higher you'd rank, the likelier the offer (going home to your alma mater, or coming from a bigger job, gets a longer look). Offers arrive with your other calls, marked "you went after this one", and the job is held for you until you decide. The ones that passed tell you why.
- **Commissioner Mode: the members' market,** inside the offseason cycle before the CPU fills its openings:
  - Members fired this winter lose their programs and keep their coach. The inbox says so.
  - The open jobs go in prestige order: each AD considers the members who are out of work or who ranked his job, and offers the best-placed one if he wants him.
  - **Answers come from codes:** a member ranks up to three jobs on the website (My team → Jobs); an offer from a ranked job is a yes. An offer he didn't plan for (a fired member, say) is put to you on the desk while the cycle runs, and with nobody at the keyboard a fired member takes it and anyone else passes.
  - **Chained vacancies:** a move opens his old chair (CPU) and the walk starts again until nobody moves.
  - **No member is ever hired without a yes:** CPU schools still can't hire members' coaches.
- **Contracts:** a member's AD offering a new deal or an extension goes to the Commissioner Inbox. The member's standing answer (sign, turn down, or ask) decides it, or you do on the desk. A deal that runs out on a hot seat isn't renewed.
- **Website:** a public Jobs page (open jobs and seats that could open, with the roster in words and the situation), your standing on every one when you're logged in, and My team → Jobs to rank three and set your contract answer. The jobs section is open every cycle, offseason included.
- Inbox records for hires, declines and contracts.

# v43.3 — COMMISSIONER MODE, PHASE 4: THE SEASON LOOP (and the full Coach Career view on the website)
-------------------------------------------------------------------------------------------------------
- **The website shows what Coach Career shows.** Words for every rating, never a number, exactly as your own coach sees them:
  - **Your players:** a full card for every player. It has his look (the game's own word), development grade, ceiling, durability, offseasons developed and trend. It shows morale (number and word, with the reasons lately), classroom and NIL. It includes this week's practice line and staff report, the depth room (staff board, coordinator and position-coach ranks with their notes, film grades, camp sessions), personality and traits explained, and season and career stats in full. The card also has the career timeline, position skills, athlete fundamentals, his best other positions and transfer-watch risk. The roster page adds position battles and the staff's depth ideas.
  - **Recruits:** the finder now shows your staff's projection, where you stand and the suggested-fit reasons (need, in-state, scheme fit, sleeper…) for every recruit, sorted by fit, rank or projection.
  - **The recruit card:** origin, senior season, official visits, crystal ball and commitment type. It also shows your projection and scouting level, what he wants (with ??? for what you haven't learned), how he reads, the race with every school's interest and the NIL picture (market, your scale, rival offers, his appetite). It ends with his room at your school, how each pitch would land, your pipeline and any can't-sign or room-is-tight warning.
  - **Program:** the program, staff room, budget, facilities, locker room and transfer watch, exactly as the game's screens print them, plus prestige, facilities and stadium at a glance.
  - **Game day:** the outlook in words, us vs them, venue and crowd, forecast, series and rivalry, the opponent's tendencies, the staff's tips and his best players with film notes.
  - **Public:** national recruiting class rankings on the Polls page; each team's overall/offense/defense stays a fuzzy word.
- **The export reads a private copy of the world,** so the game's own screens can be reused for the website without ever changing a result. It also leaves the random stream untouched. About 25 seconds for 138 teams.
- **Joining any time:** when you hand a program to a member ([T] C), choose his coach. He can take over the sitting coach, use his own coach (after a firing), or get a new coach from his Discord form (name, age, background, offense, defense, fourth-down and blitz tendencies, built exactly as Coach Career builds yours). Mid-season works: the sitting coach is let go (an interim goes back to his coordinator job). The member inherits the staff's board as standing orders (a weekly call to every recruit already offered, an evaluation for the rest) with both coordinators on autopilot.
- **Firings:** ADs can fire a member's coach mid-season, exactly as they fire CPU coaches. The program goes CPU under an interim, the member keeps his coach and the Commissioner Inbox tells you. Members' coaches can't be hired away by CPU schools or retire on the game's say-so (Phase 5 brings the job market).
- **Inactivity:** five missed cycles in a row puts a question in the inbox (kick him and make the program CPU, or keep waiting), and asks again every cycle after.
- **Commissioner Inbox v1:** import problems (every rejected code with its reason), member firings and departures, inactivity. Answers that do something (a kick) act right away.
- **[A] now writes the website after the cycle** (switch it off in [L]). **[E] members:** every member, his program or status, and his coach.
- **bots.py:** synthetic members (diligent, casual, lazy, ghost) that write real signed codes from what the website shows, for dry runs.

# v43.2 — COMMISSIONER MODE, PHASE 3: THE LEAGUE WEBSITE
----------------------------------------------------------
- **[W] Export the website:** writes `site/`, a static site to upload to GitHub Pages (or any static host), and `exports/`, which stays on your computer: every team's password (new ones marked), a ready-to-paste Discord post and the league directory. About 14 seconds for 138 teams. Exporting only reads the league: runs with and without an export between cycles match exactly.
- **Public pages:** home, scores by week, standings, polls (media top 25, committee, award watch), headlines and the recruiting wire, every recruit (search and filter by name, position, stars, state and status; each shows every school that offered and his top schools), every team (schedule, commits, roster), and the league directory with open programs.
- **No ratings, anywhere:** other teams' players show an approximate tier word (re-read every four weeks), traits and stats; a team's overall, offense and defense appear as fuzzy words. Your own players show your staff's eval word, this week's practice line, the staff's comments, trend, potential word, traits, mood, NIL and injuries.
- **Logins:** each player team gets a four-word password. Its file is locked with AES-256 and a 150,000-round key derivation, and unlocked in the coach's browser; nothing is sent anywhere. [K] issues a new password and signing key for one team.
- **My team:** recruiting (standing-orders queue with reordering, actions, repeat rules and pitches; coordinator autopilot; your board of up to 40; per-recruit visits, NIL, promises and walk-on invites), game day (opponent film notes, practice focus, offensive and defensive keys, scripted openers, play-calling, depth chart by position), roster, and coach (hot seat, contract, AD goals).
- **Hours bar:** the site knows your hours for the week and mirrors the game's queue rules, so it shows which orders run, which wait for their week, and which will be cut.
- **Build my code:** the site knows the cycle and which orders are open, builds and signs the code in the browser, and links to your form. Drafts are saved in the browser. What your staff learns appears after the week is played, on the next export.
- **[L] League title & links:** title, site address, submission form, a one-line note for the cycle and the export folder; all appear on the site and in the Discord post.
- Clean, phone-friendly layout with a dark mode.
- Every export is stamped, so a re-export mid-cycle (new password, new owner, new links) reaches players on a normal reload; nobody is served a stale copy.

# v43.1 — COMMISSIONER MODE, PHASE 2: THE ORDERS ENGINE
--------------------------------------------------------
- **Order codes:** a player's decisions for a cycle travel as one line of text (`CC1.…`), compressed and signed with his team's own secret. Hand-edited codes, codes signed for another team or by a previous owner, codes from another league, and codes for an earlier or later cycle are all rejected with a plain reason. Codes pasted with line breaks still read. A small code (a game plan) is about 160 characters; a full week of recruiting, plan and play-calling about 550.
- **Bulk import ([O], from the desk, the teams screen or the inbox):** drop the Google Form's responses CSV (or a .txt of codes) in the new `imports` folder. The report lists accepted teams with a one-line summary and warnings, rejected codes and why, older codes superseded by a newer one, and player teams with nothing in. Nothing applies until you confirm. 138 codes build a report in under a second and apply in about three.
- **What orders control (in season):** recruiting (board adds and drops, the standing-orders queue with once / weekly / every other week / until he commits / N weeks, pitches, coordinator autopilot, official visits, NIL offers, promises, preferred walk-ons), the depth chart by position (or "staff decides"), the game plan (practice focus, offensive and defensive keys, scripted openers) and who calls plays. If a code queues a scholarship offer and also attaches NIL, a promise or a visit to the same recruit, the offer is made first.
- **Standing orders:** the queue, autopilot, depth chart, game plan and play-calling stay in force until a newer code changes them. A team that misses two cycles in a row also gets a basic staff-run recruiting board until its member is back. The teams screen marks ✓ for orders in, and m1/m2… for consecutive misses.
- **[M] One team's orders by hand:** paste a late code (if it fails its checks you can still apply it on your authority) or the orders as JSON.
- **Snapshots and [U] roll back:** taken before and after every import and before every cycle (the last 24 are kept in saves/commissioner_snapshots).
- **Rerun-identical, regardless of who looked:** every import and cycle starts from cleared recruiting caches, so exporting or viewing data between cycles can't change results. Three separate runs of the same four cycles of imports matched exactly.
- Player depth charts survive the staff's weekly re-sort; injuries still move the next man up.
- Other modes unchanged: a same-seed regression run matches v42.3 exactly.

# v43.0 — COMMISSIONER MODE, PHASE 1: FOUNDATIONS
---------------------------------------------------
- New Game → **[5] Commissioner**: run a Discord league from one copy of the game. There's no coach of your own; the world runs from the new **Commissioner Desk** (cycle status, teams & owners, the Commissioner Inbox, advance one cycle, league directory, results, standings, polls, save).
- **Teams & owners:** hand any program to a Discord member ([C#]) or make it a CPU team again ([R#]). A member can coach only one program. Ownership, members and a full commissioner log are saved with the league (versioned, migrated on load).
- **Player teams get no AI recruiting**; their orders take over in Phase 2. Signing Day's safety nets (late offers, filling holes) still apply, as they do for a human in Coach Career.
- **Switched off in Commissioner leagues:** sanctions (cases, investigations, penalties, academic holds), rule-bending (recruiting overtime, the back channel), discipline (locker-room incidents and team-rules suspensions), player inboxes, press conferences, rivalry-week moments and skill points. Difficulty is locked at Varsity. Injuries and bowl opt-outs still happen.
- **Rerun-identical cycles:** every cycle is seeded from the world and the cycle number, so re-running a cycle from the same save gives exactly the same results.
- **League directory:** [D] prints every program, its owner or OPEN (CPU), and saves a text copy to exports/.
- One cycle = one week in season; the whole offseason is one cycle until Phase 7 splits it.
- Other modes are untouched: a same-seed regression run matches the previous build exactly.

# v42.3 — THE COORDINATOR SEARCH & AUDIT FIXES
------------------------------------------------
- Coordinator hiring is now a real search (coord_search.py). Each opening gets 5 quiet calls and 3 formal interviews. Calls reveal true interest, personality and top priority; interviews reveal what's pulling a coach toward and away from the job plus his camp's terms. Offers are packages (salary, years, play-calling, assistant head coach title, head-job out-clause) that are accepted, countered with specific terms, or declined; lowballs sour talks and three rounds end them.
- Interest draws on existing systems: program stature vs his level, step up/down, Power-conference jump, first coordinator job, coaching-tree ties, alma mater, Homebody regions, personality (Climber, Blue-Blood, Loyalist, Survivor, Fixer…), your hot seat, recent job changes and scheme fit. Position-coach promotions must be a raise over current pay.
- Each candidate's minimum and priorities are fixed per search, so re-offering a few dollars no longer re-rolls a decision; anyone who declines stays out if the same job reopens that winter. Unengaged candidates can leave your search as calls, interviews and offers take time.
- Sitting assistants' schools can match after a verbal yes (one chance to top it). Funding is checked only after agreement, so no budget cuts are made for a coach who then says no. The separate random 15% "matched" roll in the carousel was removed.
- Negotiated terms take effect: play-calling is handed over, the AHC title is set, the out-clause lowers the buyout and eases head-job departures. Taking play-calling back from a coordinator you promised it to makes him listen to other schools.
- Staff Room: "let your AD hire" now actually fills the chair instead of leaving it open.
- Fix: offseason inbox decisions from Weeks 8-17 had deadlines a full season late (the year rolls over at Signing Day); every offseason decision now closes at kickoff. Errors in offseason mail are no longer silently swallowed.
- Fix: coordinator extensions made coaches MORE likely to leave and refused pay cuts made them LESS likely (the stay/leave flag was inverted in negotiate.py and budget_fix.py).
- Fix: saves with no universe on record are matched to the universe their conferences actually use instead of always loading as real_2026 (the bundled Autosave loaded with every conference "unknown").
- Removed dead hiring code (hiring_market.negotiate_coord) and fixed a possible crash in the Week 3 offseason message.

# v42.2 — STAFF MARKET, LIVING OFFSEASON INBOX & PLAYER DATABASE IMPORT
--------------------------------------------------------------------------
- Staff hiring is now a pursuit instead of a click. Coordinator searches expose candidate interest, then go through contact, interview, salary/years and an acceptance decision. Program prestige, current job, résumé level, relationships, tenure and money all matter; elite assistants will not casually take major step-down jobs.
- Position-coach searches use the same philosophy: interest is shown on the board, choosing a coach begins an interview/offer process, premium offers cost real budget money, and candidates can decline.
- Same-offseason anti-poaching is enforced for both coordinator and position-coach movement. A coach who has just signed a new job is off the market until the next cycle, including coordinator attempts to bring newly hired assistants with them.
- Winter and spring now generate contextual inbox traffic every offseason week: AD expectations, staff-market notes, portal updates, player role questions, Signing Day reminders, winter-development notes, spring-practice/A-Day conversations, Portal II reactions, summer conditioning and the Media Days handoff. Several messages require actual player/staff decisions rather than serving as flavor only.
- New Game setup now offers **[P] Import player database JSON** before the world begins. The importer accepts loose/modular JSON shapes (flat players, `players`, `teams`, or team-name dictionaries), fuzzy-matches schools, replaces generated roster slots rather than expanding rosters, and accepts common aliases for name/team/year/position/traits/ratings. Missing fields inherit from the generated player being replaced.
- Imported traits can be either internal trait keys or the labels shown in game. Ratings may be nested or inline; six fundamentals are accepted individually, and an OVR-only record is also supported. The source/count/import notes are stored in the save.

# v42.1 — YEAR-ROUND CFB POLISH PASS
--------------------------------------
- Audited the full 17-week offseason loop, spring cycle, Portal II, Media Days and save persistence after the Phase 1–3 redesign.
- The hub now shows Week X/17, distinguishes winter and post-spring portal class ranks once Portal II opens, and recomputes the overall incoming-class rank with both transfer windows included.
- Taking a new head-coach job now immediately refreshes the hub's Last Season panel to the new program instead of leaving the old school's snapshot behind.
- A-Day now defaults to a compact score/team-stat snapshot plus standouts; the full exhibition box score is optional so spring remains meaningful without making the offseason drag.
- Cleaned stale phase-development wording, clarified spring practice/evaluation copy, wrapped long recruit/honors lines, and corrected the Media Days header to match the 15 teams actually displayed.
- Re-ran compilation/import checks, generated and simulated spring practices + A-Day, exercised Portal II ranking updates, and round-tripped the expanded spring/offseason state through save/load.

# v42 — YEAR-ROUND COLLEGE FOOTBALL (Phase 3)
------------------------------------------------
- Spring football now runs as two persistent practice blocks plus A-Day. Every player gets three practice samples per block, spring stock persists, and practice performance changes staff evaluation separately from true development.
- Six spring emphases now shape the work: Fundamentals, Competition, Young Players, Physicality, Chemistry and Passing Game. Focused position battles receive sharper staff reads, and the existing position-trial system remains available before A-Day.
- Spring development is intentionally smaller than winter development, while spring injuries, morale and evaluation movement can carry consequences into the post-spring portal.
- A-Day film now feeds player spring stock and staff depth order. Strong and poor spring-game performances can nudge morale, and Portal Window II explicitly reacts to players who were buried or lost ground during spring.
- The offseason hub's national board becomes spring-specific in Weeks 11-13, surfacing stock-up/stock-down names and A-Day results instead of generic offseason headlines.
- Summer now shows national roster-talent rank plus the strongest and weakest position rooms entering camp.
- Media Days now produces a real preseason information package: preseason poll, conference finish projection, projected win total, national roster-talent rank, best/weakest rooms, award watch-list players and projected preseason All-America / All-Conference mentions.
- Spring and preseason state are persisted in the offseason save state (v3) and migrate Phase-1/Phase-2 saves in place. Spring evaluation fades once real regular-season film begins replacing it.

# v41.5 — THE OFFSEASON RACE (Phase 2)
------------------------------------
- The winter transfer portal is now a live three-week process instead of one instant resolution. Entrants have hidden decision timing, the market resolves in waves, and a small number of verbal pledges can reopen before the deadline.
- Your portal work persists from week to week: contacts, visits, interest reads, NIL work and offers remain on the same board, with follow-up hours added in later portal weeks.
- Portal class status updates between weeks so the offseason hub can show the market moving instead of only the final result.
- High-school recruiting remains live through the final recruiting week. CPU staffs keep working, commitments and decommitments can still happen, and recruiting-class movement is recorded entering National Signing Day.
- National Signing Day is now a real Week 8 deadline on the offseason calendar rather than an event that silently resolves before the hub reaches it.
- Added a second, smaller post-spring portal window in Weeks 14-15. Spring depth-chart position directly increases the danger for buried players, and teams can replace losses before camp.
- Head-coach opportunities now stage across the opening offseason weeks in a normal one-coach career: Week 1 shows the programs calling/interview interest, open jobs that want you are held off the AI market, and Week 2 turns those calls into the real offer decision before you manage the staff at whichever school you chose. Carousel headlines are revealed across those weeks instead of one wall of transactions.
- Phase-2 offseason state is save-safe and migrates Phase-1 saves in place.

# v41.0 — Offseason Hub (Phase 1)

The offseason now runs on a 17-week calendar with the same advance-week rhythm as the regular season. This phase is the framework: existing portal, recruiting, carousel and spring mechanics are preserved, but each one now lives in a scheduled offseason week behind one persistent hub and agenda.

- **17-week offseason clock:** January through Media Days, with a labeled phase and deadline every week.
- **Dedicated offseason hub:** program status, the upcoming offseason schedule, national news/boards, last-season statistics and an ON YOUR DESK warning list stay visible from one home screen.
- **[A] Week Agenda:** every week has a consistent agenda showing required decisions, recommended items and deadlines before advancing. Required staff/portal/spring decisions cannot be accidentally skipped.
- **Persistent offseason state:** current week, completed weeks/tasks, last-season snapshot, portal summary and incoming-class summary are stored in the save for the later living-offseason phases. The old `off_cal` state migrates lazily.
- **Weekly information boards:** recruiting rank, transfer-class rank, combined incoming-class rank, roster/budget/staff state, coaching-carousel headlines and the preseason poll appear when they are relevant.
- **Last-season context:** the hub keeps the finished record and several national stat/rank snapshots visible even after the new schedule is built.
- **Real deadlines:** the winter portal opening/market/deadline, signing push, NSD, spring blocks, A-Day, roster review, summer and Media Days are represented as actual calendar weeks.
- **Safe integration:** the underlying one-shot recruiting/portal/carousel logic is intentionally unchanged in Phase 1; Phase 2 can now make those systems resolve week-by-week without rebuilding the UI or save architecture.

# v40.1 — Audited branch merge

- Second-pass audit against both source branches. Restored integrations that the first v40 merge had accidentally overwritten: Hot Seat/LAN hooks across menus, saves, recruiting, portal, finance, staff, facilities and spreadsheet export; per-coach career logging; coach portraits on matchup/carousel screens; and the v39 compact tablet renderer/order wrapping.
- Hot Seat save cards once again identify every coach, LAN games block one seat from loading/leaving the shared world, and multi-coach spreadsheet exports keep private "You" data separated while retaining the v39 Compliance sheets.
- Verified every Python module imports, both source branches' top-level Python symbols are represented, the 138-team world validates, game simulation produces weekly film grades, salary cuts execute, faces render at both sizes, and save/load migration round-trips.

# v40 — Branch merge restoration

- Merged the later v39 systems back together with the depth/personality/portrait branch instead of choosing one fork.
- Restored **Find the Money** and negotiation, including mid-contract salary cuts and salary deferrals; position coaches, the staff room/carousel, head-coach searches, the offseason calendar, spring practice and A-Day; compliance/integrity; portal priorities, overtime recruiting and back-channel tampering; signing-day capacity fixes; universes/custom programs; records/Hall of Fame; coach prestige, strength of schedule, field/tablet presentation, the expanded name pool, and the later overtime rules.
- Kept the newer **Decide Your Depth / Manage Depth Chart** workflow, three-session camp evaluations, weekly film grades, staff inbox depth suggestions, personality/trait effect hooks, coach sideline profiles, themed depth UI, procedural faces, History Lookup, and dashboard **Q → title screen** behavior.
- Depth management stays in fall camp and the weekly football workflow rather than returning to the old main-menu depth shortcut.
- Player cards keep trait explanations inside the player box; staff comments wrap to two lines and use a wider context-sensitive comment pool.

# v39 — More names

- The name pool roughly doubles where it matters: about 490 first names (up from 296) and about 1,600 surnames
  (up from 1,067), from across the country — Southern, Midwestern, Hispanic, Polynesian, Nigerian, German,
  Irish, Polish and Scandinavian families among them. New worlds and every new recruiting class draw from it.

# v38 — Overtime fix

- Overtime possessions now alternate like the real rules: whoever went second in one overtime goes first in the
  next (before, the same team started every period). From the second overtime on, every team — not just
  yours — has to go for two after a touchdown.

# v37 — Portal strategy, overtime, tampering

- Transfer portal: every entrant shops for one thing (a starting job, a winner, the best NIL deal, the right
  scheme, closer to home, a path to the NFL) and it weighs 2.5x in his decision; money-first players chase the
  bigger check. The portal list shows WANTS, and his card says what to sell him on. CPU staffs shop by style
  (Reload buys starters, Rebuild takes volume and youth, High-school-first barely shops) and keep some starters
  from entering with a raise.
- Overtime ([O] in the recruiting hub): +10 recruiting hours once a week, with a rising chance of a recruiting-
  violation case — and traces that can surface later.
- Back channel ([T]): reach out to players on other rosters, in season or offseason (trainer, high-school coach,
  or a direct call). It makes them likelier to enter the portal and to pick you; get caught and his school files a
  tampering complaint, and landing him gives the CAB another look.

# v36 — A cleaner game screen, and a lot more tradition

- The tablet redraws on a clean screen every snap (the call screen sits right under it), the situation line
  and the run/pass/defense play lists fit the 100-column screen, and picking a play opens on its own screen.
- Suggested for You: one line per recruit (the WHY tags that fit, no wrapping).
- Real 2026: 170+ more real traditions across almost every FBS program — entrances, mascots, songs, cannons,
  student sections, post-game rituals — and the booth can work more of them into a game. College GameDay's
  host opens with a local tradition at every stop.

# v35 — Deeper staff, the head coach search, spring ball, a smoother offseason

- Position coaches: a specialty each (QB whisperer, Line builder, Pipeline, Retention, Film junkie, Walk-on
  whisperer, Closer), a season-by-season room growth record against the nation, and a reputation that sets his
  price and his place on coordinator shortlists. Profiles, interviews and the hiring list show it all.
- Head coach search: a tracker for every opening (shortlist, turn-downs, matches, hire), and interviews with the
  AD when schools call you — answers that fit his style improve the offer; misses can pull it.
- Spring ball: an emphasis (Fundamentals, Competition, Chemistry), position trials with staff grades, and A-Day
  as a recruiting event.
- Offseason calendar: a line on what each phase is for, decision phases marked, an ON YOUR DESK to-do list,
  [$] budget from anywhere, and [F] to skip quiet phases to the next decision.

# v34 — Negotiation

- A real negotiating table (`negotiate.py`) from Find the Money and the staff room: players can defer NIL
  (paid back next year +15%) or take less for a role promise; coordinators can sign an extension for less
  now, defer pay (+12%), or take the assistant head coach title; you can defer your own salary (+10%). Odds
  are shown before you offer, each offer type once a year per person, near misses get counteroffers.
  Deferred money lands on next year's books and deferred salary/NIL returns to normal after.

# v33 — Signing day makes sense

- Why you lost him: if a recruit wants you most but you can't take him (no scholarship offer, class full, no
  room at his position, 85-scholarship limit), the game now says so — a weekly note while he's on the board,
  a warning on his recruit card, a reason in the signing-day ceremony, and a WHO YOU COULDN'T TAKE list.
- Signing day, your call: when that happens on signing day you choose — offer him on the spot, drop a signee
  to make room, or let him go.
- Fixed the swarm: late signing-day offers used to give a top recruit ~100 schools at low interest, and together
  they could outweigh the school he loved. Now only schools within reach of his favorite are in the running,
  the leader's edge counts for more, and the best prospects pick first.
- Position room is projected the same way all year as on signing day, so a kid who can commit in October can
  sign in February; transfer portal staffs count committed recruits before taking transfers.
- Honest crystal ball: only schools that offered him and have room, the real signing-day odds, the risk that
  higher-ranked kids take the last spot at his position — calibrated against simulated signing days.

# v32 — Find the money

- Every "not enough money" moment in Coach Career (coordinator and position coach salaries, recruit and
  transfer NIL, raises and counters, facilities, stadium deposits) opens a rebalance screen (`budget_fix.py`):
  restructure or release player NIL deals, coordinator and position coach pay cuts or firings, stretch buyouts,
  cut your own salary, cancel facilities spending, pull recruit NIL offers. The budget screen has [R] for it.

# v30 — Staff, the offseason calendar, and spring

## Position coaches and the staff room (`poscoach.py`, `staff_room.py`)
- Eight position coaches on every FBS staff (QB, RB, WR, TE, OL, DL, LB, DB) with DEV, REC and EVAL ratings:
  a quarter of development at their positions, up to ~12% recruiting interest at their positions, and a
  sharper or blurrier staff read (practice report, depth chart) on their players. They grow, age, retire and move.
- Staff room: fire, hire into open chairs, promote a position coach to coordinator. Position coach pay above
  (or below) a standard room comes out of (or goes back into) the money for players.

## Staff identity (`poscoach.py`)
- Position coaches are types — Developer, Recruiter, Technician, Players' coach, Climber, Loyalist — that shape
  their ratings. DEV is a real growth multiplier for the room (about +25% elite, -10% poor); recruiting adds a
  home region. Profiles, interviews, and the players each coach signed.
- Coordinators have their guys: they bring them when hired; firing one unsettles his guys (they may walk or
  follow him) and hurts the morale of the players he signed.

## The staff carousel (`staff_carousel.py`)
- A dated December-January carousel for every assistant job: interviews, turn-downs, counteroffers, position
  coaches landing first coordinator jobs, coordinators bringing their guys, and domino openings. Your openings
  come up in turn; programs call about your coaches (blessing or a raise). Feed and summary are saved.

## The offseason calendar (`offseason_cal.py`)
- Coach Career offseasons run on one calendar, January to July: carousel, staff, portal, Signing Day, awards,
  spring practice, A-Day, the draft, roster report, summer, Media Days. Finished phases can be reopened.
- Spring practice: pick up to three position battles; those positions read far sharper all season.
- A-Day: a simulated Blue-White spring game with a box score (no stats or injuries carry over).

## Also
- Transfer Watch (tab 4 -> [W]), a compressed field near the goal line, difficulty that changes the job
  instead of the football, the Real 2026 universe as the default for new worlds.

# v29 — Universes

## New: an original universe, and universe files (`universe.py`, `world.py`, `universes/`)
- **The built-in world is original.** All 138 FBS and 70 FCS programs have their own nicknames, abbreviations,
  stadiums and chants; schools named for a person, a brand or an acronym take a place name from their own town
  or region. Head coaches are new people who inherit each seat's pinned ratings and scheme, so programs play
  the same. Conferences, the 28 rivalry names, 48 trophies, team lore, tailgate dishes, bowls and venues, the
  playoff, the top award (the Golden Helmet), the pregame show (Campus Countdown) and its crew, the media poll
  and the pro league are renamed. Real coach résumés and pre-2026 history are left out of the built-in world.
- **Universe files** replace any of 77 tables by name, plus display-only "terms". Settings -> [U] picks the
  universe for new worlds; [X] exports one. A save stores its universe and switches to it on load.
- **Rules read names from `world.py`:** the Power four, the flagship independent, the Saturday-night and
  weeknight conferences, the noon showcase rivalry, the holiday games. A universe can set every one.
- **Display terms** are swapped wherever text is printed: the terminal, prompts, the window's labels and
  sidebar. Words right after a color code are matched too.
- **Older saves:** a pre-v29 save is treated as the real-world universe and its stored words are updated once
  (playoff round names, the award, TV windows, playoff appearances).
- **Team files** match their conference through the universe's terms, so one file works in any universe.

## New: almost every name in the window is a link (`links.py`, play.py, gui/app.js)
- Players, teams, head coaches and coordinators, conferences, stadiums, rivalries and trophies, recruits (when you
  coach a team) and this season's played bowls open their page in a card over the screen you're on. Before, only
  your roster and your next opponent's were links.
- They work on every screen, in the sidebar, and inside the cards; a card keeps a trail, so ◀ Back (Backspace)
  returns to the last one. Esc closes.
- Matching reads whole names, longest first: "Dallas Bonner" beats the team "Dallas", "Alabama's" links Alabama,
  "Texas A&M" and "Miami (OH)" stay whole. Schools in capitals ("SOUTH CAROLINA") and names cut to fit a column
  ("South Carol…") link when only one thing could be meant. FCS opponents are read whole but have no page, so
  "Alabama A&M" isn't a link to Alabama.
- The server builds the list once per change (about 11,400 names in ~20 ms) and the window only fetches it when it
  changes; a 270-line scoreboard renders in under 10 ms. A page opened from a link that keeps asking for input is
  stopped after a few prompts instead of hanging.
- Checked: every kind of link opens the right page in both universes; ~1,200 links per universe (every team,
  coach, conference, stadium, rivalry and bowl, 400 random players and recruits) open with no errors; in Chrome,
  the dashboard, rankings, scoreboard and cards link as described, Back and Esc work, `[K]` keys still click,
  and there are no page errors.

## Fixed: the recruiting board wrapped every other row
- Rows ran to about 115 columns, so any recruit who was committed or had a standing order or visit folded onto a
  second line. The columns are re-budgeted to exactly 100: an 8-segment interest meter, a narrower name and
  standing column, and the Q/V flags in their own small column before the leader. Leaders use the newspaper short
  name (Miss. State, NMSU, Jax State) instead of being cut mid-word. "OV" is now "V" (official visit booked).
- Checked with a full 40-man board of top recruits in every state (committed to you, hard/soft/early, committed
  elsewhere, both flags, the longest school names): widest line 100 in both universes.

## Checked
- Built-in and real-world universes: a world builds clean, validates, plays a full season with bowls and
  playoff, an offseason, and a save/load round trip that switches universes.
- A v28 save taken in the middle of the playoff loads into the real-world universe, finishes the playoff and
  starts 2027.
- 13 weeks of broadcast games and pregame shows per universe: no errors; no real names in the built-in
  universe's output, no built-in names in the real one's.
- Exporting a universe and loading it back gives identical tables, value for value and type for type.

---

# v28 — The tablet fits

## Fixed: the game tablet broke into two-line rows
- **Auto picked the wrong size in the window.** The tablet's AUTO setting asked the terminal that *launched*
  the game (play.command / play.bat) how wide it was, not the window. A wide launcher terminal meant the
  124-column WIDE tablet in a 100-column window. The window now tells the game it's a 100-column screen
  (`ui.DISPLAY_COLS`), so AUTO picks COMPACT there, as the manual always said.
- **WIDE was folded everywhere.** The v19 width guard folds any line past ~104 columns so text never runs off
  a 100-column screen, and it was folding the WIDE tablet's 124-column rows too, even in a terminal wide
  enough to show them. The tablet now prints under `ui.allow_width(...)`, so it's never folded; everything
  else still is.
- **WIDE in the window, on purpose:** the window measures the widest line on screen and shrinks the text to
  fit it (carriage-return progress lines don't count), so a WIDE tablet fits instead of running off the side.
- **Between-series orders** ran past 100 columns on defense ("[6] Double their best WR" wrapped); the orders
  now pack onto as many lines as they need inside the box.
- Checked over full broadcast games: in the window, 155 tablet frames, widest line 100, nothing folded; in a
  130-column terminal, the WIDE tablet at 124 columns, nothing folded.

---

# v27 — Strength of schedule

## New: strength of schedule for every team (`sos.py`)
- Measured the way the Selection Committee reads a schedule: each opponent's roster plus 25 x his winning
  percentage (an FCS school counts as a 40 roster at .300). A record is blended with last season's early in the
  year (three games' worth), so September isn't judged on one or two games. Matches the committee's own schedule
  measure at 0.99 (checked over the first six weeks of a season).
- Three ranks for every FBS team, 1 (hardest) to 138: **full season**, **played so far**, **still ahead**. Words:
  brutal (top 15), tough (16-40), average (41-85), soft (86-115), very soft. Opponents' combined record in
  their other games (FBS opponents only).
- **On every team's schedule**, under the record: "Strength of schedule No. 19 (tough) · played No. 98 · ahead
  No. 4 · opponents 34-19 (.642)". Also on the team page, in the dashboard's schedule panel title, and on the
  window sidebar's schedule card.
- **The rankings view** (tab 5 -> [O], tab 2 -> [O], rankings menu [7], or [S] on a team schedule): every FBS team
  with its rank, record, word, index, played and ahead ranks and opponents' record. [F] / [P] / [A] sort by full,
  played or ahead; [C] one conference; [T#] opens the team at that rank; [Y] a finished season.
- The final table is kept at the end of every season (`league.sos_history`), so past schedules and past seasons'
  rankings have it too.
- Coach Career shows ranks and words, never the index (it's built from ratings your staff can't see).

## Notes
- Older saves: this season's numbers are live right away; past seasons from before v27 have no table.
- Manual 4.1, 4.2, 20.7 and the keys reference; README; the guided week's Rankings card.

---

# v26 — Coach prestige

## New: how big a name you are (`coach_prestige.py`; Coach Career, step 7 of 8)
- Right after difficulty, pick your coach's prestige: **Unknown**, **Rising**, **Established** or **Elite**.
  It's your reputation, not your ability: ratings still come from your background.
- **Who calls with your first job** (FBS programs ranked by prestige, No. 1 = most prestigious):
  Unknown, the bottom 45 (the classic start, unchanged); Rising, No. 55-105; Established, No. 25-70;
  Elite, the top 30.
- **The first contract:** the first-timer discount and cap loosen with your name (Unknown x0.88 and capped
  at 75% of market share, as before; Rising x0.94 / 85%; Established x1.00 / 95%; Elite x1.06, no cap).
  Pay still scales with your ratings against the size of the job.
- **Negotiating:** before your first season, the AD sizes you up by your name (the level he thinks you've
  proven yourself at, and a little extra leverage on every ask: +0 / +3% / +6% / +10%).
- The job-offers screen's opening line matches your name, and your career log records it.
- Measured on one world: Unknown offers ran $0.7-1.4M at Akron-to-Liberty jobs; Rising $1.7-1.9M (New Orleans,
  Marshall); Established $3.8-5.3M (Arkansas, Lakeshore); Elite $3.9-8.2M (Oklahoma, Miami).

## Notes
- Older saves and CPU coaches are unaffected (a coach with no prestige set is Unknown: the old pool, the
  old contract math, no extra leverage). After your first season, only your record counts.
- Manual 1.2, 3.4 and new 3.6; README updated.

---

# v25 — The record book, the Hall of Fame, custom programs, and a guided first week

## New: the record book (`records.py`, `record_screens.py`; tab 5 -> [R], team page -> [E])
- Every record from the first game of 2026 on, national and for every school: single game, single season
  and career for players (passing, rushing, receiving, all-purpose, defense, kicking, and the longest run,
  catch and field goal); team game and season records (points, margin, yards, wins, points per game,
  fewest allowed, point differential, winning streaks, with active streaks listed); coaches' wins and titles.
- The season board mixes in this year's leaders while the season is on; the career board counts active
  players week by week. A transfer keeps one career (each school's book counts what he did there).
- Records make the headlines: a remarkable national record, a school record once the book has a season
  behind it, or the week a player passes a single-season mark.
- Career files (`league.record_book.files`): a permanent record of every player who did something worth
  remembering (season lines, schools, coaches, honors, titles, draft slot), kept after he leaves.
  Forgettable finished careers are pruned each offseason to keep saves small (about 1 MB a season).

## New: the Hall of Fame (`halloffame.py`; tab 5 -> [F], team page -> [G])
- The national Hall: players eligible two seasons after their last college game; head coaches with six or
  more seasons once they've stepped away. A case is honors, production against an elite career at the
  position, titles, the draft and records held (coaches: wins, percentage, titles, playoff trips).
- A panel of 20 named voters, each with a lean (numbers, rings, awards, linemen, regional, old school),
  votes every offseason after the draft: up to 8 players and 2 coaches each. 75% gets in; classes cap at
  6 players and 2 coaches; under 5% or 8 years on the ballot and you're off. Voters turn over.
- Screens: the latest class with speeches, every inductee, every ballot with each name's case and who
  voted for him, ballot watch (who's next, and active players building a case), program halls, the panel.
- Program halls for every school, judged on what a player or coach did there. Other schools' committees
  induct up to two a year. Yours (Coach Career, AD mode): the committee brings you nominees each offseason
  and you select up to three (offseason report [S], or the hub [S]); if you never do, the committee's
  picks go in at Week 1. National inductees go into their school's hall too.
- The offseason report has a Hall of Fame section.

## New: custom programs (`custom_teams.py`, `team_builder.py`; team page -> [J])
- Team files (.json in `custom_teams/`): everything the game keeps about a program, from identity, stadium
  (every part), ratings, facilities and budget, head coach (schemes, personality, all six ratings),
  coordinators and AD to rival, trophy, booth lore, tailgate dish, an optional program it replaces, and an
  optional full roster (every player's fundamentals, proficiency, traits, class, size). Missing fields
  are filled in; out-of-range values are pulled into range with a warning. Example file included.
- New world: [C] after picking a mode adds team files or builds new ones. A file replaces a program
  (rivals, trophies and protected games follow) or joins its conference as a new program (139+ teams
  work). Custom programs go through the burn-in, so they arrive with recruiting history; a file's roster
  is kept exactly.
- In a save: edit any program in place (players you edit keep their careers), export any program to a
  file, or load a file over a program. Renames carry the record book, the Hall of Fame, rivalry series
  and coaches' records with them.
- The team builder edits every section, including a full roster editor (edit, add, delete, filter,
  generate a whole roster from the ratings).
- The game's school-keyed tables (abbreviations, states, towns, rivals, trophies, altitude, lore,
  tailgate food) are filled from the files on every build and load, and reset between worlds.

## New: the guided first week (`guide.py`; Settings -> [G], on by default)
- The first time you open each screen in your first week (the dashboard tabs, fall camp, the week hub,
  practice, depth chart, game plan, presser, inbox, recruiting, Saturday, the postgame report), someone
  on your staff, by name, tells you what it's for and what to press. Once per screen; quiet after
  your first game. AD mode and Spectator get their own welcome. [G] on any card turns it off.

## Fixed
- The Home tab could crash after Week 1 when there was compliance news (the headline loop reused the
  variable holding the headline count).

## Notes
- Older saves load: the record book starts with the next game, the Hall of Fame's first ballot comes
  when someone qualifies, and the guide stays off (you're past your first week).
- Manual chapters 30 (record book and Hall of Fame), 31 (custom programs), 32 (the guided first week);
  keys reference and settings updated.

---

# v24 — Talent wins

Measured over four full seasons against the preseason program ratings (the OFF/DEF columns in `teams_data.py`),
compared with v23 on the same seeds:

| | v23 | v24 | real |
|---|---|---|---|
| Rating vs wins (correlation) | 0.48-0.53 | 0.61-0.65 | ~0.75 |
| Teams rated 82+ | 9.3 wins | 10.8 | ~11 |
| Teams rated 55 or lower | 5.3 wins | 4.8 | ~3 (see note) |
| G5 wins vs P4 | 18-26% | 13-19% (avg 16.7%) | 12-15% |
| Average margin | 19-20.5 | 18.0 | ~17 |
| Decided by 3 or fewer | 10.6-11.8% | 11.7-13.5% | ~17% |
| Decided by 28+ | 25.6-29.5% | 22.4-23.9% | ~22% |
| FCS beats FBS | 8-17% | 6-8% | — |

Yards, plays, points and turnovers per game are unchanged.

## Fixed
- **The burn-in forgot who was good.** Four years of pre-2026 recruiting pulled every roster toward prestige
  (tradition, academics, campus) and squeezed the league together: a 32-94 rating range became 60-81 on the field,
  and Front Range (54) fielded a 71-overall team. New `roster.settle_to_ratings()` runs at the end of the burn-in and
  puts each team's offense and defense back on a line through its rating (`SETTLE_SLOPE`), keeping 15% of each
  team's burn-in drift (`SETTLE_KEEP`). Each player on that side shifts by the same number of overall points, so depth charts and
  who's the star don't change. Rating vs roster overall correlation: 0.87-0.89 -> 0.99.
- **Coach fit was worth a touchdown.** The hidden coach-school fit rolled at 1.8 rating points (sd), permanently
  (about 3.5 points on the scoreboard per team, every week, uncorrelated with anything). Now 0.6 (`carousel.FIT_SD`).
  Older saves are rescaled once on load.
- **Game-day form** was up to +/-6 rating points, rolled fresh every game (sd 2.6). Now sd 1.3, capped at 3.5
  (`game_sim.FORM_SD`, `FORM_CAP`). Streaky and steady players still differ; the Saturday luck no longer beats talent.
- **The option ignored the roster.** When an option read took away the defender at the point of attack (most midline
  and speed-option snaps), the carrier got 2-4.5 free yards with no block to win. A triple-option staff was worth
  7-8 points a game over the same players in a pro-style offense. Now the scrape linebacker (or next lineman) fills
  the hole and the blockers get the read's edge (`engine.OPTION_READ_EDGE`). The option is still worth about 4-5
  points a game (it shortens the game, and it's efficient), and option runs get stuffed again (they were stopped for
  no gain 5-6% of the time, against about 15% for other runs).
- **FCS guarantee games**: FCS programs play 5 rating points under their listed ratings (was 2; `league.FCS_GAP`),
  since the bottom of FBS moved down to where its ratings say it should be.

## Notes
- **Teams rated 55 or lower:** these 49 programs play about 6.5 games a year against each other, and those games are
  zero-sum, so as a group they bank about 3.2 wins there plus most of their FCS game: about 3.9 wins before they
  beat anyone better. Around 4.5 is realistic for the group; 3 isn't reachable with this schedule.
- **The 0.75 correlation:** with this schedule (mostly conference games between similar teams), even a team's true
  strength, measured after the season, correlates only 0.72-0.76 with its win total. Preseason ratings can't beat
  that, so getting close to it would take making single games far more predictable than real football.
- Close games in even matchups are already realistic (18.8% decided by 3 or fewer, 5.4% overtime). League-wide
  close-game share is lower because of how wide the matchup mix is.
- Older saves keep their rosters (the burn-in is long over); coach fit, form, the option fix and the FCS gap apply
  from the next game on.

---

# v23 — The tablet view

## New
- `tabletview.py`: a full game screen drawn before every snap: scoreboard (big block-digit scores, clock, situation,
  timeouts, weather), the field, play-by-play, score by quarter, this drive, coach's clipboard (coached games) or top
  performers and scoring (broadcasts), and a team-stats footer. WIDE (124 columns, side column) and COMPACT (100 columns,
  stacked); AUTO picks by the terminal's width. Once per snap; the broadcast ticker and the coach's call header both use it.
- `fieldview.py` takes a `Geo` (field size) and draws its spot line at any width (it drops 'yards from the end zone',
  then uses the abbreviation, when it won't fit). Settings `field_view`: auto / wide / compact / field / slim / off (v22's
  'full' still works; it means 'field').
- The narrator keeps a play-by-play log (`Narrator.play_log`): one entry per snap (what the booth called, with the quarter,
  clock and down), plus entries for things said between snaps (kickoffs, reviews).
- `sideline.tablet_rows()` returns the sideline tablet's lines (`tablet()` still prints them), so the clipboard panel reuses them.

---

# v22 — The field

## New
- `fieldview.py`: a text football field drawn before every snap, from the game's own state (`sim.yardline` is the
  offense's yards from its own goal line, so the ball is exactly where the game says). Away team's end zone left,
  home team's right; the end zone under attack is lit. Ball with a direction arrow, line of scrimmage, first-down
  marker (none at goal to go), the drive's trail, end-zone labels, and a line with the spot, yards to go, RED ZONE / GOAL TO GO.
- Drawn under the ticker in the broadcast and under the call header in coached games; once per snap even when both
  ask. Settings [F]: Full / Slim / Off (saved as `field_view`). Manual 8.13.

---

# v21 — Compliance & Integrity

## New: the rules, and the people who catch you
- **Cases** (new `compliance.py`): six kinds (impermissible benefits, recruiting, NIL / pay-for-play, academic misconduct,
  transfer tampering, ineligible player), three levels. Every program, every week, from 2026. A case is hidden, then
  surfaces (self-report, media, whistleblower, tip), then moves through inquiry, Notice of Allegations and ruling,
  with an appeal. About 20 cases start a year; roughly 2 are Level I and 5 Level II. A hidden case nobody finds in
  four years disappears.
- **Risk** depends on the AD's style, the compliance office, integrity, program size, probation and shortcuts taken.
- **Rulings** are built from severity (cooperation, self-report, counsel, self-imposed penalties, contest, cover-up):
  fine, probation, recruiting hours, scholarship cuts, NIL restrictions, vacated wins (also on titles), players held
  out, a postseason ban, a head-coach suspension (Level I), seat heat and brand.
- **Replacing dice:** `dynasty.shocks` no longer rolls CAB sanctions. `team.sanctions` (read by the postseason,
  recruiting and Campus Countdown) is now folded from real cases and also carries `bans`, `probation_until` and `cases`.
- **Recruiting:** signing classes use `class_cap()` (25 less CAB scholarship cuts); the recruiting hub shows it.
  The NIL pool shrinks under booster/collective restrictions. Integrity moves recruiting pull by up to about +/-2.

## New: your decisions (`compliance_events.py`)
- Coach Career inbox: the story is about to run, notice of inquiry, Notice of Allegations, the ruling, "we found
  something" (self-report, bury, or look first), incidents, midterm grades, and temptations (booster, dead-period
  contact, collective deal, tampering). AD mode gets the same as desk events, before any other event that week; a
  message left unanswered has a defined default.
- Hiding a violation on purpose is a cover-up: if it surfaces, it can move up a level.

## New: academics and off the field
- GPA for every player (words in Coach Career), midterms in week 7 and finals each winter; below 2.0 is ineligible.
- APR per team; 930 is the line; a second year below it (or under 905) is a postseason ban. Academic support tiers.
- Incidents (arrest, DUI, failed test, conduct code, viral post, wagering); AI programs handle them in their own style.

## New: screens
- Hub with Cases, Academics, Compliance office, Sanctions & history, League wire, Under investigation, APR board and
  Internal audit. Compliance Wire is Media Center item 16; [Y] on tabs 3, 6 and 7. Player card: Classroom line.
- Sheets export: Compliance Cases, APR & Integrity, Academics (no spoilers: hidden cases stay hidden).
- Manual Chapter 29; keys, glossary and offseason chapters updated.

## Notes
- Older saves load: the compliance book starts empty and fills in from 2026 on. Nothing is converted.
- Real head coaches are never accused of wrongdoing; the head coach answers for the program, as the rules say.

---

# v20 — Export to Sheets

## New: Export to Sheets (tab 8 SYSTEM -> [E])
- One formatted .xlsx in `exports/`: an Overview tab (facts, a linked index of every sheet, notes, a header-color
  legend) and about 30 sheets, each with frozen headers, filters on every column, striped rows, and color scales on
  ratings, position fits and recruit interest.
- **League:** Teams, Rankings, Golden Helmet Watch, Schedule, Schedule Grid (green wins, red losses), Game History (every
  archived season), and optional Game Logs (every player's line in every game).
- **Players:** Rosters (every FBS player: six fundamentals, overall, potential, all 11 position fits, depth spot,
  bio, origin, injury, morale, NIL, traits, sub-skills), Player Stats, Career Stats, Rating History, Player Events,
  Coaches (ratings, schemes, contracts, past stops), Transfer Portal.
- **Recruiting:** Recruits (the whole pool, with public info, offers, visits, leaders, crystal ball, your standing and
  scouting, and — optionally — the hidden true ratings), Recruit Interest (every school's interest in every
  recruit), Recruiting Boards, Class Rankings, Signing History, Recruiting News.
- **You:** Recruit Orders, Recruit Actions, Recruit Notes, Week Decisions, Headset Calls, Inbox (with the answer you
  chose), Career Log, and your Bets in Spectator mode.
- **History:** Champions, Team History, Final Polls, Awards, Pro League Draft, Series, Carousel, Staff Moves.
- Options on the screen: [1] player game logs, [2] recruits' hidden ratings (on by default; off for a spoiler-free copy).
- Needs `openpyxl`; the screen offers to install it. If one sheet can't be built, the rest still export and the
  Overview lists what failed. Exporting is read-only.

## Recorded from now on
- Every recruiting move you make (calls, offers, evaluations, visit invites, camps, walk-on invites, and what your
  standing orders and coordinators ran) goes in `league.recruit_actions`.
- Every game's decisions (practice focus, routine, game plan, scripted openers, headset calls) go in
  `league.decision_log`, even for simmed weeks. Older saves start these empty; this season's game plans are rebuilt
  from the games' sideline records.

# v19 — Ready to publish: a front door, one look, clean navigation

## New: the main menu
- A title screen every launch: the logo, then **[1] Continue** (who, where, and when you saved), **[2] New Game**,
  **[3] Load Game**, **[4] Settings**, **[5] Manual**, **[6] About**, **[Q] Quit**. Enter continues your latest save.
- **New Game** starts with three mode cards (Coach Career · Spectator · Athletic Director) *before* the world is
  built, so backing out is free; the half-minute build shows a progress bar year by year.
- **Leaving:** [Q] on the dashboard opens a small menu — back to the main menu, save as, quit, or keep playing.
  Both ways out save first. Settings and the manual work from the main menu with no world loaded.

## One look on every screen
- **Headers:** a charcoal bar with the screen's color as a tab on the left, the title in white, and where you
  are on the right (NEW CAREER · STEP 3 OF 7, SETTINGS, 2 SAVED GAMES). The dashboard header matches.
- **Keys:** one accent color for every key. Green marks the main thing to do next, red something you can't
  take back, gray the way out. Tabs are chips with a rule underneath; command strips share one style.
- True black text on colored chips (bold black no longer turns gray), and no screen flicker: the screen is
  cleared with an escape code instead of a shell command.
- Anything wider than the 100-column screen folds onto the next line at a word, keeping its colors and indent,
  instead of running off the edge.

## Navigation
- **[B] goes back everywhere.** Wherever Enter means back, cancel or done, B does too. Crawled every key on
  every dashboard tab two screens deep: every first-level screen now exits with one [B], and nothing crashes.
- Picking a team: B cancels (it used to search for "b"). Bare "  >" prompts became real ones.

## Screens rebuilt
- **New career:** a step counter on every screen (1-7); the four job offers are a comparison table (program,
  conference, prestige, roster, contract, NIL left) with [V#] for the full offer.
- **Settings:** grouped (Game day · Your week · Tools) with ON/OFF chips and a line on what each does; Big
  moments, Sideline, the Campus Countdown cast and the default routine match. New numbering: 1 show, 2 speed, 3 cast,
  4 halftime, 5 big moments, 6 sideline, 7 week hub, 8 default routine, 9 answer hints, D difficulty,
  C auto copy.
- **Save / Load:** what's on file, where each save is and how long ago; **[X#] deletes a save** (type DELETE).
- **Fit to 100 columns:** the roster (skills colored by grade; columns size themselves when the staff reads
  in ranges), the schedule, national champions, toughest places, the team page and the career page.

## Fixes
- A head coach's profile showed your coaching-tree data as a raw dictionary under "Coaching tree".
- The team page's left column could run into the right one (Home field / Defense).
- Manual and README updated for the new menus and settings numbers.

---

# v18 — Four fixes: routines, credit, a fair grade, difficulty

## Fix — the weekly routine was long, and there were no presets
- **Routines: the week in one key.** A routine is a practice focus, a Friday game plan and the scripted openers,
  saved. Five come built in on the week hub — [1] Standard (the staff's focus, weather prep when it's coming),
  [2] Big game (game-plan heavy, openers scripted), [3] Banged up (rest & recover), [4] Recruiting, [5] Close games
  (situational football) — and [6]-[8] are yours.
- **"The film's plan"** means the two keys your staff recommends against whoever you play, so a routine works every
  week. A key you picked by hand is saved as that key.
- **[Y] Routines:** save this week's setup (name it), make any routine your **default**, delete one of yours. The
  hub opens with your default loaded (the ROUTINE line says which, and "(adjusted)" once you change something), so
  a normal week is Enter. Settings [R] picks the default too.
- **Sim weeks and a hub turned off use your default routine** — focus, plan and openers — instead of only your last
  practice focus.
- Leaving the hub and coming back keeps what you'd set (it used to reset the focus, and let you do the Thursday
  presser twice).

## Fix — the week's decisions weren't credited after the game
- **New postgame screen: THE WEEK'S WORK** (every game — coached, big moments or simmed). Each decision, in rating
  points of game-day form and in points on the scoreboard (~1.7 per rating point):
  - WED the practice focus, with what came of its side effects: injuries against its injury rate, whether the
    weather it prepared for showed up, late poise and whether there was a one-score fourth quarter to use it in,
    recruiting hours, who came back a week early;
  - THU the press conference (or "skipped"), TUE your inbox replies, LAST last week's postgame podium, ALL anything
    season-long; the other locker room's bulletin-board lift counts against you;
  - FRI the game plan — each key, how well it fit, whether it worked over the whole game — and the scripted
    openers (snaps, yards, first downs, touchdowns).
  - The total, set against the margin: "You won by 3. The week was worth about 4 — it was the difference."
- Boosts are now tagged by where they came from (the Thursday presser, the postgame podium, the inbox), so the
  credit can split them. The week hub shows last week's line and your season total; simmed weeks go in the
  ledger too.

## Fix — the process grade rewarded agreeing with the chart
- **Every call is priced in win chance** at the moment you made it (new `decisions.py`): the score, the clock,
  your kicker's real make chance, the matchup and the day's form. The model is calibrated to this engine over
  1,500 simulated games — drive outcomes by starting spot, fourth-down conversion by distance (4th & 1-2 81%,
  3 73%, 4 60%, 5 47%, 10+ 16%), two-point tries (~68%), onside (14%) and surprise onside odds, and a
  possession-by-possession endgame (including teams that only need a field goal) and overtime.
- **The grade is how much win chance your calls gave away**, not whether they matched the chart and not how they
  turned out: +1 for a call within 1.2 points of the best option, 0 at ~2 points given away, −1 at ~4. Close calls
  (every option within 1.2 points) aren't graded — anything goes. A call where the chart itself was wrong counts
  double, so following it there costs twice and beating it earns twice. A game with nothing riding on any call
  gets no grade. New letter scale (A 0.8, B 0.5, C 0.15).
- **The headset log** marks each call ✓ right call, ★ right call against the chart, ≈ close call, or ✗ −3.4% with
  the better call ("the chart missed this one too" when you followed it), and lists the options' win chances
  under the big ones. Below: how many calls were right, close and costly, how often you went against the chart
  and were backed by the numbers, how often the chart itself was wrong, and **what your calls were worth
  against simply following the chart every time**.
- **Challenges** are priced from what your guy upstairs told you (his words, not the replay) against the value of
  the reversal and the timeout; letting one go is graded the same way (it used to count only when the replay
  proved you wrong). **Sideline talk** is graded by the odds you were shown, not by whether the coin landed.
- Measured: the chart is wrong on about 2% of fourth downs, by about 4 points of win chance when it is — mostly
  short-yardage spots it punts or kicks from. Following the chart still grades well when it's right; it's no
  longer an automatic A.

## New — difficulty (Coach Career)
- **Freshman · Varsity · All-American · Golden Helmet**, chosen after your schemes, changeable any time (Settings [D],
  or [L] on your career page). It rides with your coach from job to job; only your program feels it.
  - Game day: +2.5 / 0 / −1.25 / −2.5 rating points of form every Saturday.
  - Hot seat: heats 35% slower / as tuned / 15% faster / 30% faster (weekly and in the December verdict).
  - Recruiting: ×1.12 / ×1 / ×0.93 / ×0.86 on the interest you earn.
  - The other sideline: how often the opposing staff's Friday plan reads you right (worse / as tuned / better / best).
- Measured against evenly matched teams (400 games each): Freshman won 70%, Varsity 48%, All-American 45%,
  Golden Helmet 38%. Existing careers are Varsity — exactly the game as it was. Changes are noted on the career page.

---

# v17 — The regulars

## New: the regulars at The Window, and the standings
- Twelve made-up former players and coaches bet every week, each his own way: THE FILM ROOM (his own number — the
  real buildings, the real coaching), THE MODEL (Kelly-sized moneylines), CHALK, THE DOG POUND, THE HOMER (his old
  school, every week), FADE THE PUBLIC (against favored blue bloods), UNDER THE WEATHER, POINTS PLEASE, THE LOTTERY
  (parlays, teasers, the Boost), HOT HAND (ATS trends), THE BOOSTER (long-shot futures, the game of the week) and
  YARDS GUY (player props). They bet the same numbers you see, as soon as a week's lines settle.
- Some strategies are real edges, some are superstitions. Over three simulated seasons the Film Room ran about +8% and
  Fade the Public +4%; the Homer (-22%), the Lottery (-20%) and Hot Hand (-11%) paid for everyone's drinks.
- D STANDINGS in the hub: everybody by this season's winnings (or all-time), bankroll, record, ROI, last week; a star
  for each season won; AT THE RAIL chatter (big hits, 4-0 weeks, the week's biggest ticket).
- Profiles: bio, what he looks for, record by bet type, bankroll chart, open tickets and recent results. Tail a
  ticket (T#) or fade it (F#) onto your slip at today's numbers.
- Game pages show the regulars' tickets on that game; the weekly results screen shows your place at the table; the
  HOME panel and the window sidebar show your rank.

## The book, recalibrated
- My v16 check (926-926 against the spread) counted both sides of every game, so it couldn't fail. Measured properly,
  favorites were covering 57%. The book now maps the rating gap to a margin on a curve fitted to 2,288 simulated
  games (moderate favorites win by more than a straight line says; mismatches flatten out), learns faster early in
  the season and carries half of it into the next, and tracks the league's scoring climate at the median.
  Favorites now cover 50.2%, 50.0% and 49.7% over three straight seasons; overs 49.0%, 50.8%, 48.7%.
- Moneylines use about 18 points of noise around the margin (what the results actually show).

# v16 — The Window

## New: a sportsbook for Spectator mode
- **The Window** — press [B] on the dashboard. Pick a starting bankroll ($1,000 / $10,000 / $100,000); it carries
  from season to season. A reload is there if you go broke (and it's counted).
- **Every game has a line all season.** Spreads, totals and moneylines on every game on the schedule, not just this
  week's — the look-ahead lines move every week as teams play, get hurt and get healthy. A bet locks your number; My
  Bets shows how the market has moved since (and settled tickets show whether you beat the closing line).
- **Markets:** spread, moneyline, total, first-half spread and total, team totals; player props in the featured games
  (passing, rushing and receiving yards, anytime touchdown); parlays (2-12 legs); 6-point teasers (2-4 legs); a weekly
  Boost; futures on the national title, every conference, making the playoff, the Golden Helmet, and preseason
  regular-season win totals.
- **How the numbers are set:** a power number per team (1.71 points of spread per rating point — the slope the games
  actually play to — plus what the season teaches the book, plus a point of public money on the big brands), a flat
  2.5 for home field, a 13.5-point spread of outcomes for the moneylines, totals from offense, defense and the weather.
  Futures come from simulating the rest of the season with the book's numbers. Checked over full seasons: favorites and
  underdogs cover about equally often (926-926), overs and unders split (920-916), moneylines are calibrated.
- **The hub:** bankroll (with its trend), action and record up top; tabs for the board, look-ahead, futures, props,
  the slip, my bets, your record (a bankroll chart and results by bet type and season) and every team against the
  spread. Quick picks from any board ("12h" adds the home spread to the slip, "12h 50" bets $50 on it now); a full
  page for every game (all its markets, line history, ATS records, recent results, injuries, forecast).
- **Around the game:** matchup cards show the line, your action on that game, and [B] Bet this game until kickoff; a
  results screen after every week shows what paid; the HOME tab has a Window panel; the window version's sidebar has
  a bankroll card (with a trend line) and a Sportsbook shortcut.
- Grading: bets pay the moment a game is final (a parlay loses the moment one leg does); win totals after Week 13,
  conference titles on championship Saturday, make-the-playoff on Selection Day, the Golden Helmet and the title when the
  season ends. Props on a player who doesn't play are void.

## Spectator mode: your team through a scout's eye
- The team you follow now shows words with estimate ranges instead of numbers ("quality starter (76-81)", "elite
  (79-83)") — roster, player cards, the team panel, schedule, matchup cards and the sidebar. Every other team keeps its
  numbers. The Window's options can hide every team's numbers the same way.

# v15 — The sideline

Coaching a game is more than picking plays. Everything below comes with the headset (Coach every snap, and the big
moments); Settings → [9] Sideline turns each part on or off.

## The tablet (every call screen)
- Momentum (them ━━━●━━━ us) and the crowd, this drive, your standing orders, and your challenge.
- What's working and what isn't today (quick game 7/9 · outside runs 1/6); on defense, what's hurting you.
- What they do in this down and distance, from what you've seen: their defense on 3rd & long (blitz 4 of 6, man,
  two-deep, eight in the box), their offense on 1st down (run 7 of 9, mostly outside runs).
- A line from your coordinator with the read and a play that beats it, your own tendencies ("we've run on 1st down 8
  of 10 — they know it"), and what the other sideline just changed ("their DC brought a safety down").
- Who's hot, who's cold, who's playing hurt.

## Series orders ([G], and a check-in between series)
- Offense: Normal · Max protect · Quick game · Pound it · Tempo · Take shots, plus feed one player the ball.
- Defense: Normal · Spy the QB · Two deep · Load the box · Pin your ears back · Double their best WR.
- Orders shape the staff's calls and change the snap itself (a back in to block, a spy, a safety in the box, a
  bracket, a faster release, tired defenders against tempo). They stand until you change them — and they're how you
  steer an OC or DC who calls a side for you.
- The coordinator comes over every series, only when he has something (default), or never.

## The people
- Trainer's report: shut him down, tape it and send him back (hobbled; a hit can make it twice as long), or only if
  it's close in the fourth.
- The quarterback: two picks and the QB coach asks; the backup for a series or the day, and back again later.
- On the sideline: after a pick, a lost fumble, a costly flag, a second drop or a blown coverage, the player comes off
  rattled (both teams). Arm around him, get in his face, let a captain handle it, or sit him a series. His position
  coach tells you who he is; head cases, divas and gamers answer differently.

## The calls that were the staff's
- The try: kick, go for two, or go for two with your play. Two is automatic from the second overtime (the rules).
- Kickoffs: deep, squib, onside, or a surprise onside.
- Flags with a real choice (holding on a play that went nowhere, defensive holding): accept or decline.
- The replay challenge: close catches, fumbles, spots a yard short. One a game (a win keeps it); a loss costs a
  timeout. CPU staffs challenge too; the booth calls the review.
- Fake punts and fake field goals on fourth down ([X] / [Z]), with a read on whether they'll be ready. A second fake in
  a game is harder.
- Ice the kicker. Stop the bleeding with a timeout (momentum cools). Get the crowd up on their third down at home.
- Overtime: the toss winner chooses (CPU staffs take defense first).
- The fourth-down chart's call shows on every fourth down.

## Friday game plan (week hub → [G])
- The film's read of the matchup, then one key on offense and one on defense, each rated for this opponent. A key
  that fits is worth more; every key costs something somewhere else. Script your openers (sharp first ten snaps, one
  practice period). Game-plan heavy practice sharpens both keys. CPU staffs game-plan too.
- Halftime shows whether each key is working.

## After the game
- The headset log: every fourth down, try, onside kick, flag, challenge, icing, trainer's call, QB change and sideline
  talk, next to the chart and the staff, with the result — and a process grade.
- The podium asks about the call that decided it.

## Under the hood
- League averages are unchanged (checked across ~1,200 CPU games: points, yards, run/pass split, sacks and picks
  within noise; a few more accepted penalties, from defensive holding and holding on plays that went nowhere).
- Old saves load; old box scores just have no headset log.

# v14 — The stadium, part by part

## New: modular stadiums (replaces the 1-10 stadium level)
- Every stadium is built from 19 parts with tiers: Lower Bowl, End Zone Stands, Upper Deck, Student Section, Club
  Seats, Luxury Suites, Roof Canopy, Video Board, Sound System, Stadium Lights, Team Entrance, Concourses, Fan Plaza,
  Hall of Fame, Press Box, Home Locker Room, Visitors' Locker Room, Recruiting Lounge and Playing Surface.
- Parts add capacity, noise (home-field edge), money (new seats, club seats, suites, concessions, board ads),
  recruiting appeal (pitches and game-day visits) and in-game effects (locker rooms, injuries on the surface).
- Every real stadium is broken into parts from its capacity and reputation: Michigan starts near the top, Husky
  Stadium and Autzen have roof overhangs, Kinnick has its pink visitors' locker room.
- One stadium project at a time; big ones take 2-3 seasons; many parts need others first.
- The stadium fund: booster giving every offseason, capital campaigns after big seasons, 6/10-season bonds, and
  NIL money you can move in.
- A fan base that grows slowly with prestige, winning, sellouts and amenities. Overbuild and the seats sit empty.
- CPU ADs build too: seats when they keep selling out, otherwise what their style likes.
- The old stadium grade (1-10) is now what the parts add up to; old saves convert automatically.

## New: Toughest Places to Play
- Live ranking of every FBS home field (noise, crowd, home record over four seasons, ranked scalps, home streak,
  tradition), with a per-team breakdown, every season's final list, and year-to-year movement.
- On tab 5 RANKINGS ([S]), the rankings menu ([6]), the stadium screen ([T]), team pages and game previews.
- The booth mentions new stadium parts and top-10 buildings.

## Coaching carousel continuity
- Early contract extensions now happen after the hiring market settles, so a coach is never extended and then
  hired away in the same offseason. Expiring deals are still redone before the market.
- A coach who just took a job this winter, or just signed to stay (an extension or a matched offer), can't be
  hired away again the same offseason, by CPU schools, splash-hire poaching or your AD search.
- AD mode: "fire him" / "let his deal run out" is tied to that coach, that school and that winter. If he retires,
  leaves, or you move to another school first, nobody else gets fired in his place.

## Depth charts
- Every preseason your staff rebuilds your depth chart (the practice report's eye, last year's starters keep an
  edge, freshmen who aren't starting are kept behind close veterans to save a redshirt). Fall camp shows new starters
  and suggested position moves; [D] opens the chart, [S1] takes a staff idea. After that it's yours to change.
- CPU staffs build a fresh chart every preseason (scheme-based starter counts, position moves when a room is short
  or a deep backup would start elsewhere) and re-sort every week as players develop — with a starter's edge so
  charts don't flip-flop, and a staff's eye that sharpens with film. Simmed seasons manage your team the same way.

## The window's sidebar (play.py)
- Five tabs — Home, Games, League, Team, News — under a hero card in your conference's colors (rank, record,
  streak, last five, season progress, points per game).
- Next game with a win-chance dial (an outlook dial in Coach Career), kickoff, venue noise and toughest-places
  rank, rivalry and series; last result; coach card with seat movement, contract and goals; inbox preview;
  AD meters in Athletic Director mode.
- One-click shortcuts that run from the dashboard (play the next week, save, inbox, depth chart, practice,
  recruiting, standings, poll, facilities, portal, carousel, media...).
- Poll-rank chart, schedule with results, conference standings, Top 25 with movement, NP, Golden Helmet, toughest
  places, starting lineup with fill-ins, injury report, leaders, program and recruiting cards, roster filters,
  national scoreboard, headlines, hot seat watch, recruiting wire, your story.
- Toasts for results, poll moves and mail; foldable cards, resizable width, Alt+1-5 — all remembered.

## Recruiting, deeper
- Standing orders: a visible, reorderable queue of repeated actions (once / weekly / every other week / N weeks /
  until he commits; the same recruit any number of times). It runs at the end of the week with the hours you
  didn't spend; the queue screen shows what will run and what will be cut. Coordinator autopilot by side of the
  ball. A weekly Recruiting report in your inbox.
- Official visits (5 per recruit) at your home games, graded on the result, the opponent, the crowd, the noise,
  the stadium and what he cares about, with a report for every visit. CPU staffs book them too.
- Pitch conversations on calls, position-coach visits and in-homes: sell what he cares about.
- The living trail: senior-season stats, ratings updates (Weeks 5/9/13, risers and fallers), summer camps and
  camp standouts.
- Hard, soft and silent commitments; crystal-ball predictions and trending news; an early signing period;
  signing-day flips; a live National Signing Day.
- Negative recruiting, NIL bidding wars and crowded-room objections.
- High-school pipelines that grow with signings and go cold with broken promises and cuts.
- JUCO transfers, international kickers and punters, preferred walk-ons who can earn a scholarship.
- The war room (ordered board, tiers, class goal, pipelines) and a hit-or-bust report on every class.
- The window's sidebar shows your standing orders (what runs, what's cut) and booked visits; new shortcuts for
  standing orders, the war room and official visits.

## New: weather
- Every outdoor game has real weather from where and when it's played: state and town climates through the
  season, kickoff time (night games are colder), regional weather systems, fronts, tropical storms. Domes and
  closed roofs have none.
- Conditions change quarter by quarter: rain starting and stopping, sleet turning to snow, the wind picking up,
  temperatures falling. Lightning delays. The field gets wet, sloppy or snow-covered (grass worse, heated hybrid
  grass better). Teams switch ends, so the wind helps each side in turn.
- On the field: accuracy, catching, drops, fumbles, muffed kicks, field-goal range and accuracy, punt distance,
  touchbacks, footing on runs, acclimation to cold and heat, altitude. Coaches run more, throw deep less and
  won't kick long into a gale.
- Forecasts that sharpen as the game gets closer (and are calibrated), on HOME, tab 2, the schedule, the week
  hub and the sidebar.
- The Weather Center (tab 2 → [F], week hub → [W]): your forecast and outlook, storm alerts, the country's
  weather games, last week's weather games, and your program's weather book.
- Weather prep: a new practice focus that halves the weather's effect on your team; the staff suggests it.
- Weather keeps some fans home (a roof canopy helps), shapes official visits, and gets talked about by the booth,
  the Campus Countdown crew and the headlines. Box scores list the conditions by quarter; your call screen shows them.
- The manual has a new chapter (10) on weather.

## The manual
- A full manual, in the game and as a text file (MANUAL.txt): 28 chapters from quick start to troubleshooting,
  covering every mode, screen, system and key.
- Open it anywhere on the dashboard with [?] (or tab 8 SYSTEM -> [H], or the sidebar's Manual shortcut). Browse
  by chapter, page with N/P, jump chapters with ] and [, and search every word with S.

# v13 — Playtest fixes

## Game
- Scheme identity survives a deficit: down three scores late, an offense still leans toward its scheme (half the
  pull, not none). Across 150 games, run rates land close to the scheme screen (Smashmouth ~62-64%).
- A backup QB you promised a role ("build him a package") gets real snaps: up to five a game on early downs, never
  in a two-minute drill or a close fourth quarter. They show in the box score.
- Sacks up to ~2 per team per game (6% of dropbacks), from ~1.5. Games with no sacks for either side are rare.
- The poll: a signature win still earns extra spots, but no more #23-to-#4 jumps. Unranked upset winners enter
  around #15-20.
- Rice's Scott Abell runs an option offense.

## Coach Career
- Your background is the best in the building: inherited coordinators sit below you in your signature skill.
- Coordinators recruit different regions, and one covers the school's own backyard (a Homebody keeps his).
- Roster goals start one rung above today's roster (never met on day one) and read in staff words.
- The hot seat panel shows how far it moved and why ("AD liked your press conference").
- Big moments: when you're behind late, up to two red-zone drives a game come to you ("get something going").
- Halftime: separate offense and defense calls, and a first-half scoring list.
- "← last time" on the game-mode picker only after a game in this career. The play-calling prompt only offers changes.

## Recruiting
- Promises check eligibility before the menu (no offer, no hours, already promised).
- Promise hints: start ▲▲▲, play ▲▲ ("6+ games next fall"), develop can't be broken.
- SCHEME FIT now fires for defensive fits; up to four WHY tags show (REACH no longer hides HARD SELL).
- Recruit card lines split instead of cutting off. Staff-read legend on recruit lists.

## Inbox, press and the locker room
- AD states the goals in his own voice; promise stakes say "a winning season (overall)".
- One shared leaders list for the locker room and the captain's camp message; a leader needs a real leadership
  tag. Grinder and Coasts can't share a player. Camp messages match the room's actual chemistry.
- Media day's seniors option shows its cost up front (your young star's morale), naming a real player.
- DC's corner options fit your coverage; the QB room note says the backup is "handling it — for now".
- Every sender shows a role, including dashboard previews. Answered messages show your reply.
- Inbox "Saturday" effects read "this Saturday"; postgame ones read "next Saturday".
- Podium: repeating a tone gets half the upside (costs still stack); the Enter default is named; "next man up"
  costs the injured player; the summary counts stacked effects ("recruits ▼ ×3"). Loss-aware answers.
- Locker room: one-per-line tag legend, "nobody's in trouble" header when no one is, a reason for every player,
  "no effect" instead of -0.0.

## Practice and film
- Battles and the staff chart use your scheme's starters. "Has passed" needs a real margin; a rough week is called out.
  Backup lines are marked "Limited reps" and weigh less. Staff misreads are smaller.
- The camp report lists this week's inbox calls and their effects.
- OL drills read "pass-pro"; plurals fixed; strength blurbs need at least an average skill; neutral blurbs vary;
  "first look" instead of "steady" in camp; punters "pin" punts.
- Opponent film shows tendencies (run rate, tempo, fourth downs, pressure, man %) and a staff tip.

## Screens
- Scheme screens: HARDER SELL columns, a defense summary table, "neutral" instead of "no edge", blitz pressure preview.
- Coaching tree: three branches per row (names fit), "needs N pts in branch" tiers, your starting trait shown.
- Develop: where the bank comes from, what Coach Skill does, why "up to three" stopped early.
- Staff-read legend (LS/DEV/BU/ROT/STR/QS/AA) on the lineup, payroll (column now READ, realigned) and budget.
- Budget shows two decimals on millions so the pieces add up.
- Scoreboard flags lead each line; ★ is in the legend; "For the book"; upsets flag at a 4-point roster gap.
- Truncation fixes: roster best/worst, depth chart practice (wraps), Golden Helmet schools, team leaders, AD goals,
  fall-camp goals (wrap), week-hub matchup, dashboard matchup ("Us below avg · Them good").
- The booth signs off (not "goodnight") from day games.

# v12 — A window of its own

## New: play.py (desktop window)
- `play.bat` / `play.command` / `python play.py` opens the game in its own desktop window (pywebview, offered as a
  one-time install; `--browser` runs it in your browser with no install).
- Clickable hotkeys and dashboard tabs, a quick-key bar, clickable player names that open cards in a pop-up,
  a live sidebar (record, rank, next game, hot seat, inbox, skill points, searchable roster), screen history,
  auto-fit text with zoom, light/dark themes, sounds, and copy screen.
- The game code runs unchanged. `main.py` still plays in the terminal.

## Fixes
- Wrapped a few lines that ran past 100 columns: the practice report's position menu, the week hub's keys,
  and the matchup card's team ratings in Coach Career.

# v11 — The staff's eye

## New: no numbers in Coach Career
- Player overalls, position proficiencies, fundamentals, team ratings and win chances show as words everywhere in
  Coach Career: roster, depth chart, player cards, schedule, dashboard, week hub, preseason scheduling, inbox,
  recruiting projections, the transfer portal, job offers and the offseason report. Stats still show.
- Other modes show the numbers, as before.

## New: practice reports with practice stats
- A weekly (and fall-camp) practice report: stat lines for every player from his real skills plus luck, position
  battles, and the staff's recommended depth chart ([A] to accept, or [R] per position on the depth chart).
- Staff scouting reports on every player card, and opponent film ([O] on the week hub).

## New: position skills (sub-proficiencies)
- 44 sub-skills across 11 positions, shown as words, and all used in the game engine: throw depth, pressure,
  throwing on the run, route depth, coverage depth, run direction, pass pro, YAC, tackling, kick range and punt
  placement. Balance across 200 games is unchanged: 28 points, 64% completions, 4.5 ypc.

## Changed: development timing
- One third of yearly growth now happens during the season, week by week. Two thirds happens in the offseason.

## New perk: Scout's Eye (Developer, tier 4)
- Shows estimate ranges next to the words.

# Console College — Coach Career playtest fixes

Everything from the Coach Career beta-test report (Temple, Walt Hargrove), grouped the way the report grouped it.

## Checked and not bugs
- **[T] add to board on a recruit card** and **adding kickers from a filtered list** both work (confirmed in a scripted
  run). The playtest's missed adds were inputs that never got entered.

## Bugs
- **Duplicate jersey numbers:** a player who joins a roster (transfer, signee) gets a free number if his is taken.
  New worlds are cleaned up after they're built, and older saves are cleaned up when they load. If two players
  ever do share a number, the jersey lookup asks which one you mean instead of guessing.
- **[C] on the Recruiting tab** opened Class, not your career. Class is now [K].
- **NIL before a scholarship offer:** the NIL prompt now checks first and says what to do ("Extending an offer
  costs 3h, from Week 1"), instead of taking an amount and then refusing it.
- **Inbox queue:** after [A], answering a message opens the next one that needs a reply, until you leave one for later.
- **[A] "from any tab"** now reads "[A] from any dashboard tab". Sub-screens go back with Enter/B.

## New: depth chart
- **Tab 3 TEAM → [H]** (or [H] on your team page). Reorder any position (`M 2 1`), move a player to a new
  position (`C 82 OL`), reset a position to best-overall (`R`). The order you set is what lineups, snaps and the
  two-deep use. Starters are marked for your scheme's base personnel.
- **The starting lineup follows your scheme:** Smashmouth shows its base 1 RB · 2 TE · 2 WR, not three receivers.

## Numbers that didn't add up
- **Job offers:** "leaves $X for player NIL" now takes out operations (20%), the same pool the budget screen shows.
- **Budget screen:** one AVAILABLE figure plus a separate "Suggested — plan to spend about" line, instead of
  two competing numbers. Coach salaries show exactly ($1.15M, not $1.1M). "Budget left" says it's after operations.
- **Facilities** in Program Ratings is on the same scale as the three facility tiers.
- **Team page** explains that Program Ratings are the school's reputation, not this year's roster.
- **Win chance vs an FCS team** says FCS on the same line.
- **Trench Guru / QB Whisperer** now only apply to their positions (OL/DL, QB) at +15% development, and the team
  page shows "+15%" next to the rating it boosts. Your coach starts from a level 55 across the board, so your
  background is what sets you apart (an O-line coach starts with Trench Dev 65).
- **Position proficiency** for positions nothing like a player's body (a 317-lb lineman at safety) is now
  near the floor (new worlds).
- **Recruiting needs** add one spot at any position where nobody coming back is good enough — a kicker in the 40s
  now shows as a need even with two kickers on the roster. The panel shows how many spots are flex (best available)
  and how many at each position are already on your board.
- **Standing vs. the race:** standing now accounts for how you compare to the school in front, so "Leader: Temple"
  and "ON THE FRINGE" can't sit on the same row. The race shows each school's interest (0-100), and says so when
  it's early and nobody has a real hold on him.

## Contradictions
- **Coordinator deals** show the years they run ("deal runs 2025–2026 · expires after this season") instead of a
  "signed" year that disagreed with the coordinator page.
- **Coordinators' schemes:** each coordinator page shows only his own side ("His offense: Air Raid"), and says when
  he was hired by the previous head coach and came with the job.
- **Homebody** names the states in his region ("Won't leave the Northeast (CT, DE, MA, …, WV)").
- **DC "faster than last year"** — a coordinator new to the school says "faster than the tape I watched from last
  year". The corner-depth worry only comes up when corners really are thin, and its new reply ("Corners go to the
  top of the board") actually flags corners as a staff priority in Suggested.
- **The camp leader** is picked by leadership, is labeled "one of your leaders", and sounds like the room — if
  chemistry is tense he says not everybody's bought in yet.
- **Locker room:** a player shows in one list only (leaders who are also trouble are marked "also a wild card");
  a Mentor only counts once he's an upperclassman.
- **The AD** now talks in his own voice ("I want us to post a winning season, …") and says which year he starts
  grading the goals. The AD text everywhere reads "every season moves your seat, but he won't judge you on the
  goals until year 3 — hit each one at least once in its window". Goals read "at least once in 3 yrs".
- **Media day** only mentions a quarterback battle when there is one (within 5 OVR); otherwise it's the starter's
  senior year. It posts before the coordinators' notes, so the inbox reads the OC's QB note first. Naming your QB
  gives chemistry a small bump.
- **Pro League Draft** line reads "N picks in the last N drafts".

## Truncation and alignment
- Dashboard: opponent names are shortened instead of cut ("EAST TENNESSEE ST."), the AD line drops its note when it
  won't fit, "Hot seat: stable (20/100)", team rating bars run on a 40-99 scale so 66 and 61 look different, and the
  standings have CONF / ALL headers (the Team tab shows 9 teams, like Home).
- Fall camp: goals wrap instead of cutting off; projected wins say bowl eligibility is 6.
- Recruit card NIL line, budget operations row, filter rows [10]-[12], locker room class column, coordinator
  resume ranks — all fit now.

## Clarity
- **Roster:** a legend for every column; kickers and punters show leg power (PWR) and accuracy (Seaboard); a note that
  the sim carries the working roster, not a 105-man camp roster; rows are in depth-chart order.
- **Player card:** "(+8 this offseason)", "raw → as OL, scaled by his 0.93 OL proficiency", "Durability durable (79)".
- **Job offers:** clauses a deal doesn't have say "offset: none" and "rollover: none"; a line says salary also
  pays for your coach's development.
- **Negotiation:** every ask shows before → after ("5 → 6-7 yrs", "65% → 80%"); a refusal comes with the AD's own
  line and says your seat didn't move but he's warier; your running seat pressure shows; after an ask you can
  [A] accept or [N] ask again without going back to the job list; "1 counter" → "1 ask".
- **Scheme screens:** a summary table (run rate, tempo, who wants to play there); "run rate 30%"; defenses show
  pressure % and man/zone, a real-world comp, where they give no recruiting edge, and why your background points
  there. The Veer & Shoot comp is the Houston run-and-shoot tree / mid-2010s Waco.
- **Blitz is its own choice** (Sit in coverage / Pick your spots / Bring it), separate from fourth down, and it's
  what your defense uses on Saturday. The team page shows "4th down: conservative · blitz: sits in coverage".
- **Coach creation:** age and background react to each other in a line of story; High School Legend no longer
  hedges.
- **Payroll:** DEV, star glyphs, a THRU column (last season he can be paid), the ⇄ transfer marker, walk-on /
  no-deal notes, and a note that NIL deals are fixed once signed.
- **Locker room:** who's pulling chemistry up and down (starters only, and why), what moves it, "rating points on
  Saturday", starter/backup tags, and a legend for every tag on screen.
- **Coordinator page:** what he does when you call plays, where to change play calling or let him go, and a
  plainer UNIT vs TALENT note.
- **Schedule:** RESULT header; for unplayed games, the opponent's OVR, last year's record and your win chance;
  rivalry games are marked.
- **Inbox:** every sender shows a role (Booster, OC, DC, SID); "wk 0" → "camp".
- **Dashboard Recruiting tab:** position needs on the panel; the options panel is "RECRUITING · OPTIONS".
- **Team leaders** before Week 1 show last season's leaders when there are stats, otherwise say stats start in Week 1.

## Recruiting lists
- **Suggested** weighs prospect quality and QB urgency, counts in-state less, tags SCHEME FIT / HARD SELL /
  OUT OF REGION / STAFF PRIORITY, and drops "REALISTIC" (everything that isn't a REACH is realistic).
- **No more pendulum:** at most 4 players at one position per page of Suggested; the list is the top 60, not the
  whole country.
- **Row numbers hold still** after you add players (they stay on the list, marked ●) until you change a filter.
- **"—" standing** is now "NO CONTACT", with a line explaining it.
- **Finder title** says "RECRUIT FINDER · QB" when you filter by position.
- **Board:** national rank column and [S] sort (rank / position / your standing).
- **Hub:** hours message once, AVG STARS "—" with no commits, menu numbered 1-6 ([7] still works).
- **Filters:** "Only positions I still need: on/off", "Only my region (shortcut)".
- **NIL prompt** shows the multi-year cost and warns when you haven't evaluated him.


---

# Console College — playtest fixes

Every item from the Week 1 Spectator playtest report, grouped the way the report grouped them.
Items marked (optional) in the report were done too, except where noted.

## Menus and navigation
- **Mode select** reads [1] Coach Career, [2] Spectator, [3] Athletic Director, in that order.
- **After a week sims** the dashboard lands on HOME, so the new poll, results, and news are on screen first.
- **Header** says "WEEK 1 OF 13 COMPLETE" once the week's games are final (postseason rounds say "complete" too).
- **Coordinator list:** Enter on a card returns to the list on the same page. The list now has page numbers,
  [N]/[P] paging, and only Enter/B leaves it, so a mistyped key no longer backs you out to Coaches.
- **Game preview:** "Last result" reads like a crawl: `BC 19, VT 14 · Final` (with poll ranks and OT).
- (optional) **[Y] Sim to the \<team\> game** on the game preview fast-sims everything before the team you follow.
- (optional) **Spectator mode asks which team to follow** (Enter keeps the preseason No. 1). You can change it
  any time from tab 3 TEAM or tab 6 COACH with [F].

## Home dashboard and Coach tab
- **The hot-seat meter** now runs "cool → hot", with each segment colored for the heat it stands for, plus the
  number (e.g. `Stable 28/100`). The coach card adds "(70+ is hot)".
- **An empty recruiting class** shows "Unranked", not "#26".
- (optional) **Preseason headlines:** the defending champion's preseason rank, Golden Helmet favorites, the hot-seat
  watch, big portal transfers, and new-era hires.
- (optional) **The Coach tab** now has a Record & Contract panel (age and personality, years at the school,
  record there and career, full contract with every clause and its current dollar figure) and a "What the AD
  expects" panel (style, when he fires, when he starts judging, and his goals). [P] opens the full profile.

## Coaches and carousel
- **Preseason seats** start from each program's expectations vs. its roster and the coach's tenure, so a new
  world has a real hot-seat list (a handful hot, a couple dozen warm). New hires get a honeymoon. Nobody starts
  a season already past his AD's firing line. Each seat carries its reason on the coach card.
- **Coordinators arrive with a past:** prior career stops, and unit rankings for the seasons they already
  coordinated. Rankings are unique per season and driven by roster talent plus the coordinator's skill.
  "First year as coord." now means exactly that.
- **Head-coach buzz** counts reputation as well as résumé: an elite coordinator at an elite program starts
  "on the lists" or as a "hot name".
- **Rising Coordinators** is a short list (the top 25 with real buzz). If it's ever empty it says why.
- **Ceilings tighten with age.** Room to grow shrinks from the late 30s and is gone by 60, e.g. a 55-year-old
  78 OVR now tops out around 81. Your own coach in Career mode is exempt.
- (optional) **Real head coaches with fictional coordinators:** left as is. It's how the game's data is built
  (real 2026 head coaches, generated staffs). The booth no longer pins negative reputations on real coaches (below).

## Coach detail card (contracts)
- **Contract totals round** instead of truncating, and salaries show two decimals ($1.98M) so the pieces add up.
  Deals with raises say "/yr to start".
- **"Owed if fired" is right:** before the season, this year counts in full; during the season, only the games
  left; in the offseason, it starts with next year. Raises are included. The buyout actually paid on a firing
  uses the same numbers, year by year.
- **The release clause shows its dollar figure** ("— $1.56M right now"). The buyout line shows its figure too.
  The report expected $1.5M, but the correct figure is $1.56M because it now includes the raises.
- **Homebody names his region** ("Won't leave the Midwest"). A Homebody's job, alma mater, and recruiting
  territory are all in that region, and Homebody coordinators turn down jobs outside it.
- **Background lists prior stops** (e.g. "Missouri DC (2022–24) · Dallas linebackers coach (2021)"), never the
  current job.
- **Every trait explains itself**, e.g. "Road Dog — His teams travel well — team plays better on the road".
  Player traits get the same treatment.

## Game preview
- "stadium 4/10" → "stadium facilities 4/10 (seats, suites & noise)".

## Game commentary: bugs
- **a/an** is chosen by how the next word sounds: "a Seaboard game", "an SCC title", "an 8-yard gain",
  "a Orlando win", "a one-score game". It works in all-caps chants too ("TO BE AN AGGIE"), and in the Campus Countdown show.
- **Weather is decided before the first word.** No "beautiful evening" in the rain, no "beautiful day" at a
  night game, no "blue skies" after dark. A rainy kickoff opens with rain, and "the rain's picked up" only
  comes later.
- **"Right at the marker — and he's got it!"** only plays when the gain barely reaches the sticks. Fourth-down
  conversions get their own lines (no "on third down!").
- **Red zone** counts trips once per drive. A touchdown counts only if it came on a red-zone trip. No more
  "only zero" or "one touchdowns".
- **Stat callouts** only cover players on the field: the QB and back for the offense, the pass rusher and
  tackler for the defense.
- **Catch spot, yards after catch, and final spot** are computed together. Screens behind the line are caught
  behind the line. "Wraps him up immediately" only happens when he really was wrapped up immediately. Otherwise
  the call says how much he picked up after the catch.
- **Punts and field goals** now show the fourth-down spot on screen before the kick. The punt numbers always
  matched, but the last spot shown was from the previous down.
- **Tacklers "from the wrong team"** were surname collisions (below). With unique names, and full names
  whenever two players in a game share a surname, every tackler is clearly identified.
- **No more "Parker Parker":** the name generator can't give a player the same first and last name.
- **"On the road" lines** never describe the home team.
- **Pressure talk follows the data:** "the blitzes have dried up" won't air right after sacks, "the blitz keeps
  getting home" needs a recent sack, and stale adjustments aren't voiced.
- **Tackle analysis** praises a defender only when the defense won the play. Effort plays ("ran him down") are
  still praised after a big gain.
- **"That's the last one"** now always says "timeout".
- **Coach reputations are spoken naturally** ("Bill O'Brien is a relationship guy — he recruits families, not
  players"), once per coach per game.
- **At halftime** there's one break prompt, and it offers "[Q] skip Q3".
- **Next-week hype** scales to the opponent: FCS or clearly weaker gets "don't look past it", ranked or a
  rival gets "a big one".
- **"Starting to see some backups"** only happens in real blowouts (17+, the backup QB at 21+). When the backup
  QB is in, the booth calls him by name on every play.
- **Momentum lines** follow the score: a trailing team is "climbing back into this", not "has taken this over".
- **Fourth-down setups** scale to the miss: "Inches away" for a yard, "Nowhere near the sticks" for a long miss,
  and a plain line after an incompletion.
- **Season-timing lines** ("this time of year", "November") wait until later weeks. A conference game in
  Week 1 is called a conference opener.
- **Also fixed while testing:** a half-the-distance penalty at the 1 could put the ball at the 0 (a "0 yd run"
  touchdown). Split sacks and 1.5 tackles for loss could crash the booth. A lowercase "tied at 14" after a PAT.
  "In a losing effort, too — uriah Pendleton". "and one scores". A "good one" punt of 30 yards.

## Game commentary: repetition and flow
- **Repeat cooldown:** anything said between plays can't come back word for word within about a quarter of
  snaps, and long lines (plugs, takes, stories) can't repeat at all in a game. The play calls themselves are
  exempt.
- **No back-to-back stat lines:** a milestone call ("a hundred-yard rusher") puts that player's stat topic on
  cooldown.
- **Bios and backstories** (bio, transfer, hometown, young-player lines) only play right after that player
  makes a play.
- **Halftime alternates voices:** Whitmore tees up each of Ruiz's adjustments.
- (optional) **Real coaches** aren't labeled "Can't Win the Big One" or given other knocks in the booth.
  Fictional coaches still can be.

## Name generation
- **Much bigger pools:** about 1,070 surnames (up from 150) and about 300 first names.
- **No duplicate surnames on a roster** in a new world. Duplicates with the head coach or coordinators are
  also cleared.
- **During play,** CPU schools rename a quiet three-star signee who'd be a second Brown. Recruits you've
  followed keep their names.
- **Coaches get surnames no other coach has.**
- **Broadcaster surnames are reserved** (no player named Whitmore, Davis, Howard, and so on).
- **Campus Countdown guests and tailgaters** never share a surname with anyone playing or coaching in the games the
  show covers.
- **When two players in a game share a surname,** the booth uses both names every time.

## Box score
- **Sack credit matches the call:** a split sack is announced as one ("Whitley and Schneider get there
  together"), and the box shows the halves.
- (optional) **CAB rules:** sack yardage counts against the QB's and the team's rushing.
- (optional) **Player of the Game** weighs a rushing yard and a receiving yard the same, gives a 100-yard
  rusher a bump, and credits big tackle games more.
- (optional) **New rows:** sacked-yards lost, interceptions thrown, fumbles lost, punts-average, and
  returns-yards, all shown even when zero. New PUNT, KR, and PR lines per team.
- **The scoring summary names** field-goal kickers, return men, and interception returners.

## Campus Countdown show
- **"Tommy" and "Brock"** were placeholders left in the scripts. They're now the actual cast's first names.
- **Hosts use first names** in dialogue ("Eight months, Rece"). Signs in the crowd still use last names.
- **The cold open introduces everybody,** including Coach Saban, before anyone talks to them.
- **No hard-coded clock times** ("seven o'clock tonight"). The kickoff line uses the real kickoff, and
  "a long afternoon" becomes "a long night" for night games.
- **The South Bend sign has a real punchline:** "FIGHTING IRISH: THE BUS LEAVES AT HALFTIME".
- **"Kolaches. They're gone by kickoff."** Plural desserts get "they're".
- **"Tent City, Row 35."**
- **"I'd take that bet" is gone.** The desk reaction now says clearly whether he agrees, and matches his own
  pick.
- **Interview questions are season-aware:** before a team has played, "this season" becomes "your career".
  Nobody claims history against an opponent. The desk's reaction waits until the tape ends.
- **Points-allowed and points-scored lines** need two games of data, and no line shape repeats in a show.
- **The picks table carries every pick made out loud,** including preview leans, disagreements, and the upset
  alert. The upset alert only runs when McAfee's table pick really is the upset.
- **Picking the better-ranked team is never called an "upset".**
- **The picks table** uses newspaper short names (no "Ohio Stat") and is sorted by kickoff.
- (optional) **The guest picker** gives three warm-up picks and a score on the big one. If his line was about
  the home team and he picks the visitor, he says something that fits.
- (optional) **Settings → Rename the Campus Countdown cast → [F]** switches to a fictional crew and show name
  ("Saturday Kickoff") for sharing the game. [R] restores the defaults, which are unchanged.
- **Pick reasons** don't claim history ("all year", "has been rolling") before a team has played.

## Rankings and world
- **The defending national champion** opens in the preseason top few, and the runner-up in the top ten.

## Week results screen
- **Two-column results use newspaper short names** (UNC, Boston Coll., Miss. State, Jax State) instead of cutting
  names off. The same short-name table is used in the Campus Countdown picks table.

---

# Second playtest report (Week 1 Spectator, Nashville)

Every item from the report, grouped the way the report grouped them.

## Contracts
- **Deals already running when a world is built now store this season's salary.** They used to store
  the first-year salary, which is why Clark Lea showed "owed if fired $10.44M" (60% of three flat
  years). Lea now shows $5.80M/yr and $10.86M preseason. That drops to about $10.57M after one game,
  because the games he's already coached this season come off. Pritchard's numbers follow the same
  fix. Older saves are corrected once on load.
- **One contract line everywhere:** "4-yr deal (2025–28) · 3 yrs left · $5.80M/yr". The salary is
  always this season's pay. "To start" is only used on offers.
- **Money shows two decimals everywhere** ($7.40M next to $5.58M).

## Coach profiles and seed data
- **New `coach_facts.py`** holds real ages, first seasons at the current school, alma maters, and prior
  stops for about 90 real head coaches not covered before. This fixes Pritchard (39, Palo Alto, first
  season 2026), Rodriguez (63), Fritz (66), Dykes (57), Chang (45), Martin (2014), Satterfield (2023),
  Newberry (2023) and others.
  **Please spot-check this file.** I wrote it from memory, not from a source. The least-known 2026
  hires (Hauser, Jacobs, Harley, Woods, Carter, Carney, Mortensen, Shephard, Beard, Kelly) are best
  guesses on age and have no prior stops.
- **Real coaches with no alma mater on file** show "—" instead of a random school.
- **Head coaches' Background** lists real prior stops.
- **New hires get their honeymoon** because their hire years are now right.
- **Elite recruiters and recent title or playoff coaches** (Lanning, Polasek, Cignetti and others)
  start the preseason with cool seats.
- **A seat can no longer warm up on its own.** The soft floor used to pull a seat of 9 back up to 12
  after a win. Now it only slows movement.
- **Clock Manager** no longer adds aggression. Trait text reads as sentences
  ("Never wastes a timeout. His teams draw fewer penalties.").
- **Goals read "Goal · window: N seasons"** with an "N of N left" tag. The blowout goal is reworded
  ("Get through a season without losing by 21+").
- **Wording fixes:**
  - "Seat based on: preseason expectations (no games yet)"
  - "% of the football program's yearly budget"
  - "Judges a coach from his year N · Lea is in year 6"
- **Personality text wraps** instead of truncating.
- **Hot Seat list:**
  - RCRT replaces REC.
  - School names use newspaper short names.
  - Empty records show "—", and the current season's record is included.

## Coordinators
- **Buzz weighs results more than name.** There's a bonus for a top-10 unit that beat its talent and
  for a young coordinator who's already producing.
- **Rising Coordinators** only lists coaches 50 or younger with real upside, sorted by buzz ▼.
  The Coordinators list shows BY OVR ▼.
- **Resume stat ranks come from ranking the season's actual numbers** against every other unit, so
  #1 passing plus #1 rushing is #1 in yards. The TALENT rank drifts year to year.
- **Minimum ages:** 25 for a position coach, 30 for a coordinator.
- **Coordinator ceilings** are capped at OVR + 18.

## Home dashboard
- **Around the Sport ranks news by importance:**
  - Your team's result comes first, then your team's recruiting news.
  - Next come top-10 showdowns, then upsets and FCS teams beating FBS teams (at most one of those
    near the top).
  - Big injuries on ranked teams follow, then the coaching carousel.
  - Recruiting news from other schools only shows for 4- and 5-star players.
  - Headlines wrap on whole words.
- **Win chance** stays between 1% and 99%.
- **Team Leaders** fall back to "B. Etheridge", then to the last name alone.
- **"1 commit"** is singular.
- **The AD line explains itself:** "AD: Fan Pulse (talk radio)".

## Campus Countdown
- **a/an in all-caps signs:** only known acronyms count, so it's "ON A MAP" but still "AN SCC TITLE".
- **Straight quotes only.**
- **Underdog signs** like "AGAINST ALL ODDS" only appear when the home team really is the underdog.
- **Last night's recap** reacts to the margin.
- **Season-awareness:** removed the "won their big games by double digits" claim. "The most
  confident all year" waits until Week 4.
- **Repeats:**
  - Phrasings rest for four weeks, across seasons and saves.
  - Scenes rest three weeks after they air.
  - "Pacing myself" has variants.
  - Tailgate signature lines rest or get swapped.
- **McAfee's fan at the desk** gets a punchline.
- **Small fixes:**
  - "Is on the line at noon."
  - Records are dropped when both teams are 0-0.
  - Davis's mismatched lead-in is removed.
  - The guest picker names a town instead of "the middle of nowhere".
  - The tailgater's year wobble is fixed.
- **Picks table:** scoreboard abbreviations in every cell.
- **The marquee pick** is split about 75% of weeks.
- **Pick records:** a panelist who hit an underdog last week gets called out with his record.
- **The headgear sign** from the opening gets a callback when Coach puts the head on.
- **Guests and tailgaters** never share a surname with your team.
- **Not done:** the GUEST column (optional). The guest isn't chosen until after the table prints.
- **Left alone:** Saban's invented anecdotes (optional). Gating them to the fictional cast would cut
  most of the coach stories by default.

## Game commentary
- **Kneels:** a team only kneels when the kneels can really run out the clock. "That'll do it" only
  plays when they will.
- **The trailing team** doesn't burn timeouts when down more than 16 in the fourth quarter.
- **Safety:**
  - Called on the play.
  - No developer note.
  - The free-kick spot matches the call.
  - The scoring summary names who made it.
- **Out-of-town scores** are timed against this game's clock. Games still going show their quarter
  and the score so far.
- **End-of-game fixes:**
  - No next-down call once time has expired.
  - "Needing" reads a field goal, a touchdown, or two scores, and nothing in a rout.
  - "Can't go three-and-out" only plays early in a drive within 16 points.
- **Ordinals:** 1st/2nd/3rd, 11th–13th, and "threeth" becomes "third".
- **Stats and names:**
  - Interceptions appear in QB callouts and summaries.
  - "To a hundred" replaces "over a hundred".
  - Strip-sacks name who forced and who recovered.
  - A QB change is announced once.
- **Catches with yards after the catch** say so and land on the final spot.
- **"Gets out of bounds to stop the clock"** only plays late in a half.
- **Tackle credit:** nobody is credited on an out-of-bounds play, and there's no defender praise
  after a big gain.
- **Sacks:**
  - Split sacks have their own lines.
  - "A problem all day" needs two sacks.
  - No duplicate sack or tackles-for-loss counts.
  - "Nothing's working" only follows a sack.
  - The flush and backside-pursuit lines have variants.
- **Context lines:**
  - The hot-read line never follows an incompletion.
  - The halftime "run it more" advice needs at least 4 yards a carry.
  - "Figure out how to convert" is fixed.
  - Tendency-breaker lines only describe the play that just happened.
  - The late "Sudden change!" line is removed.
  - The scheme intro stays in the first half.
  - No matchup talk between teammates.
- **Injuries:**
  - One broadcast sentence per injury, and no stray capital letter.
  - Players who return from a scare get a follow-up.
- **Encroachment** says when it's a first down.
- **Rewritten lines:** "No need to measure — he's got it, barely", and "Quietly efficient" replaces
  "a heck of a season".
- **Repeats within a game:**
  - Repeated kick lines become "Touchback."
  - Program talk (academics and the like) once a game, and never on a big down.
  - No doubled "three and out".
- **The desk's one-word "Pressure."** is now a full line.
- **Pass rush:** QBs under heavy pressure throw it away more, and more so the more they've been sacked.

## Names
- **Famous names:** about 150 real star players can't be generated, e.g. Keenan Allen.
- **One of each first name per roster,** and never the head coach's or a coordinator's.
- **Not fixed:** AD surnames can still match a player's (Winslow).

## Box score
- **Defense:** both teams get the same lines: TKL (top four), SACK (everyone with one), and INT.
- **QB rushing:** QBs are always named on their own line, with sacks noted.
- **The safety** is credited in the scoring summary.

## Week results
- **Alignment:** OT and flags sit in fixed-width columns.
- **Overtime:** "2OT" and "3OT" for multi-overtime games.
- **Upset markers:** a ranked team losing to an unranked one, or FCS beating FBS.
- **Crawl names:** schools without an abbreviation get initials.

## Rankings
- **Polls:**
  - Each ballot starts from last week's ranking.
  - A win costs at most about a spot, and a loss never moves a team up.
  - No 10-spot jumps for one ordinary win, and new teams enter near the bottom.
- **Golden Helmet:**
  - FCS stats count 30%, and weak FBS opponents are discounted.
  - A preseason watch list carries a fading head start, and Week 1 movement is measured from it.
  - A second player from one team is discounted, a third more.
  - Ranks are right-aligned, and the dashboard box uses team abbreviations.
- **[P], [C] and [H] on the Rankings tab** are wired. Before the committee's first release, [P]
  shows a notice screen.

---

# New: interviews, postgame, and more inbox (Career mode)

- **Postgame press conference (`postgame.py`).** After every game you coach, you take 2 questions at
  the podium (3 for rivalry and postseason games). They're built from the game itself: the upset, the
  rival, a close finish or blowout, turnovers, your QB's interceptions or touchdowns, a star's big day,
  injuries, and the run game.
  - **Tones matter:**
    - Fiery lifts next week's prep and can move your seat, depending on your AD.
    - Humble takes the heat off the players; patient ADs like it.
    - Confident helps recruiting, but some ADs dislike swagger after a loss.
    - Owning a blowout loss buys a little patience.
  - **Carries over:** the lift feeds into next week's Thursday presser.
- **Thursday presser** has new questions:
  - The season opener.
  - A ranked opponent ranked ahead of you.
  - Replacing an injured star.
  - A QB with too many interceptions.
  - The recruiting class.
  - Senior day.
  - A trap game against a losing team.
- **Inbox, preseason:**
  - The OC's QB-room report after camp (name the starter or keep it open).
  - The DC's camp report.
  - A media day notice.
  - A booster with your rival circled.
- **Inbox, Week 1:**
  - A player's mom after the opener.
  - The captain's take on the first game.
- **Inbox, in season:**
  - The AD's halfway-point check-in, with your record against expectations.
  - A captain after a three-game skid.
  - Sports information the first week you're ranked.
  - The student section before rivalry week.
  - A bye-week plan from the staff.
- **Inbox, end of season:**
  - The AD's year-in-review, with your goals marked met, missed, or still open.
  - A senior's goodbye.
  - A signing-day push from the recruiting office.
  - A heads-up from your OC if other schools are calling about head jobs.

---

# New: an inbox with real choices, and press conferences with real stakes (Career mode)

## Every reply is a trade
- **Every message that wants an answer now has 3–4 choices, and none of them is free.** Under each option,
  a colored line says what it does: green is what you get, red is what it costs, yellow is a risk or
  something riding on a later result. Settings → **[7]** hides the lines if you'd rather play it by feel.
- **What a reply can touch** (`effects.py`): your AD's patience; locker-room chemistry; this Saturday or the
  game after; late-game poise; injury risk (this week or all year); recruiting hours and interest (your
  whole board, one kid, or one state); next year's NIL money; a coordinator's loyalty (whether he takes the
  next job that calls); and single players — bought in (half as likely to transfer), unhappy (portal risk),
  a real role (less portal risk), or extra development this offseason.
- **Promises come due.** "Judge me after the rivalry game," "We'll meet every one of those," "Yes — I'm
  guaranteeing it": the verdict lands in your inbox after the game (or in December), and your AD, the
  boosters or the recruits react.
- **Gambles are labeled.** A players-only meeting, a legend's speech, an ultimatum to a wavering commit, a
  star playing hurt (35% he aggravates it): you see the odds before you roll.
- **No answer is an answer.** A message you leave for two weeks closes. Some people notice: the AD on the
  hot seat, a recruit, a player asking about his role, a discipline problem nobody dealt with.
- **Asking your AD for money** gets you less, and costs you more, every time you ask in the same season.
- **The week hub's THURSDAY panel** shows what your answers have banked for Saturday.

## Every old message, rebuilt
- **AD:** camp expectations (promise it, sell a surprise, or ask for time to build — your young players
  develop faster), bad losses (own it and he remembers you promised a fix; trust the process; ask for help
  and the players hear you blame the roster; full pads), big wins, rivalry week (circle it and it's on the
  line; open practice to the boosters), the hot seat (bet it on the rivalry game; shake up the depth chart),
  the halfway point, the year in review (or put your own staff on notice).
- **Players:** the buried backup (promise snaps, a special-teams role with a spring audition, "earn it," or
  help him find the right school), captains after skids and streaks, the players-only meeting.
- **Recruits:** the wavering commit (a call, a home visit, a teammate from back home, or an ultimatum), the
  NIL question, Saturday reactions (invite him to a game, have a player at his position call).
- **Staff and camp:** media day, the DC's report (live press for young corners, back off contact, install
  the pressure package), the QB room (name him, keep it open, rotate them), the booster's circled date, film
  review (their focus, rest, or scheme around it), the bye week, signing day (everybody on the road, the top
  five, or flip other schools' commits), the OC's head-coach calls, senior goodbyes (GA spot, host official
  visits, or mentor a young player at his spot), conference realignment.

## New situations (`inbox_scenarios.py`)
- **Camp:** team rules for the year — strict, player-led, or trust — changes how often trouble finds your
  locker room all season.
- **In season:** a starter who wants to play hurt · saving a pressure package for the big game next week ·
  the rival coach's radio comments · opening up the playbook as an underdog · travel plans for road games ·
  another school's collective tampering with your starter · a player's family emergency · the Golden Helmet
  campaign · the freshman plan · a walk-on who's earned a scholarship · a starter's grades · the big podcast ·
  Pro League scouts at practice · a program legend who wants to address the team · in-season lifting · a high school
  coaches' banquet · a donor whose gift comes with a favor · bowl eligibility (how to use the extra practices).
- **December:** your DC has a bigger offer and wants a raise.

## Press conferences, fleshed out (`podium.py`)
- **Every tone has an upside and a cost now:** confident sells to recruits (and fires up the other side if
  you're the underdog); measured keeps your team composed late but makes no headlines (and an AD who wants
  noise notices an all-measured podium); fiery lifts Saturday but plays a little emotional late; humble takes
  the heat off the players but doesn't sell. Every answer shows its full effect before you pick it, and the
  podium ends with a one-line summary.
- **Follow-up questions:** say you're ready for the rival or the ranked team and you'll be asked if you're
  guaranteeing it (say yes and it's on the record). Hedge on your QB and they'll ask if there's a
  competition. Own a blowout and they'll ask if staff changes are coming — and your coordinators hear the
  answer.
- **New Thursday questions:** locker-room friction, a suspended player, job rumors, NIL and roster
  retention, your OC's head-coach buzz. "Talk is cheap — watch us play Saturday" is now on the record.
- **New postgame questions:** the officiating after a close loss (blast them: a fine, and a locker room
  that loves it), a freshman's breakout, bowl eligibility ("We're not done" puts eight wins on the line), a
  defense that gave up 38+, your job security after a loss.
- **Fix:** postgame lift used to vanish if you skipped Thursday's presser; it now always carries into the
  next game.

---

# New: December, player morale, and halftime adjustments (Career mode)

## December and the postseason (`december.py`)
- **The postseason is known a week ahead.** Each postseason week is built as soon as the week before it is
  final, so the week before a conference title game, a bowl or a playoff game shows who it's against: the week
  hub, the Thursday presser, your practice plan and your inbox all know. (Older saves pick this up from the
  next postseason week on.)
- **Championship week:** keep the routine (steadier late), throw everything at it (Saturday ▲▲, injuries ▲), or
  bring every recruit to the game.
- **The bowl trip:** business trip (sharper, but the players feel the curfew), reward trip (morale and the room
  way up, prep down), or use the bowl practices on your young players.
- **Opt-outs:** your draft-bound starters ask whether to sit out the bowl. Support them (he sits; recruits hear
  you put players first), ask them to play (odds depend on how happy he is), or play him for a half. Around the
  country, projected picks opt out of their bowls too — it's on the Wire and in their player histories.
- **The playoff, every round:** lock it down, let them soak it in, or let the cameras in and sell the program.
- **Early signing period:** push every commit to sign (most lock in; the shakiest might balk), let them take
  their visits, or hold spots for flips.
- **Before the portal opens:** your unhappy players, by name, with their morale: meet with all of them, promise
  the best one a role, or let them go.
- **No bowl:** practice anyway for the young players, put the whole staff on the road, or send everyone home to
  heal and reset.

## Player morale (`morale.py`)
- **Every player has a morale score, 0–100,** shown on his player card with what moved it lately ("promised a
  bigger role +10; raise refused −18").
- **It moves every week:** starters climb; backups who expect to play sour (upperclassmen, blue-chippers, the
  kid one spot from the field); wins lift everyone, blowouts sting; a warm locker room pulls everyone up; on your
  team, a starter paid well under his market grumbles. Who he is matters: Loyal and Humble types sit higher,
  Divas and Mercenaries lower — and bad news hits them harder.
- **Your calls move it directly:** every inbox reply and podium answer about a player (promises, benchings,
  suspensions, NIL raises, backing him or hedging) — and at season's end, a kept promise is a big lift and a
  broken one is a bigger drop.
- **What it does:** below 40 a player is shopping the portal, below 25 he's very likely gone, above 75 he's
  hard to pry loose. The starters' average mood is worth about half a point on Saturday. Happy veterans get
  more captain votes. Unhappy draft-eligible players leave early more often. An unhappy starter asking for an
  NIL raise comes with a threat.
- **When one of your key players falls below 30,** his position coach tells you, with what set him off —
  sit down with him, tell him the truth, or promise him something.
- **Locker room screen** (tab 3 → [K]) shows the starters' average morale, who's sliding and why, and who's
  happiest.

## Halftime adjustments (`halftime.py`)
- **Every game you coach stops at the half** (simmed, big moments, every snap or the broadcast): the first-half
  numbers, what your staff is seeing, and two calls.
- **The adjustment:** trust the staff, lean on the run, air it out, bring pressure, sit back in coverage, and —
  depending on the score — protect the lead or go for broke. Each one really changes the second half (run/pass
  mix, which pass plays get called, blitz rate, coverage shells, fourth-down aggression, trick plays), and each
  shows its upside and its cost.
- **The message:** let the coordinators talk, calm and clear (a small, sure lift), or light into them — a big
  lift if it lands, a tighter team if it doesn't. The odds are shown; a warm locker room and a team that's
  behind take it better.
- **The postgame knows:** it shows your call with the first- and second-half scores, and a big second-half
  swing either way draws a question about it.
- Settings → **[8]** turns halftime stops off (the staff decides).

## Fix: games no longer crash when a roster runs out of healthy players
- When injuries (or opt-outs and suspensions) left a team without enough healthy players at a position, the
  emergency fill-in only borrowed from spare depth, so a lineup could come up short and the game crashed
  (most often on a run play toward a missing defensive lineman). Now a thin roster fills every spot: first with
  healthy players from other positions on the same side of the ball, then two-way players, then players who are
  hurt, and nobody is ever put in two spots at once. Kick coverage and returns fall back to starters, and a
  receiver facing an all-out blitz with nobody left to cover him is simply uncovered.
- Stress-tested with 70 games on gutted rosters (down to 15 players, or everyone injured): no crashes. Normal
  rosters play exactly as before.

---

# Deeper: recruiting promises, AD trust, and contagious morale (Career mode)

## Recruiting promises follow the player (`promises.py`)
- **[M] on any recruit's card makes a promise:** "You'll start as a freshman" (the biggest pull and the
  biggest bill), "You'll play real snaps" (easier to keep), or "Redshirt, develop, then compete" (a small pull,
  bigger with kids who care about development, and always kept). It takes an offer first, costs recruiting
  hours, and you only get one per kid.
- **Recruits see your depth chart.** The card shows his room: who'll still be there next fall at his position
  and how many are at or above his projection. Top targets with an offer will ask you straight out ("You've got
  Warner and Perkins coming back. Am I playing next year?") — promise him something, or tell him the truth.
- **The promise comes to campus with him.** He arrives happier (it's in his player history). Every week he isn't
  getting what he was told, his morale slides.
- **Graded after his first season.** Kept: a big morale lift, and recruits at his position hear about it.
  Broken: his morale craters, recruits at his position cool on you, and he wants a word ("You sat in my living
  room and told my mom...") — own it and promise next year, tell him he wasn't ready, or help him move on.
- **Your record follows you.** Every kept promise makes the next one land harder; every broken one makes it
  worth less, and recruits' families ask about it.

## Your AD remembers (`ad_trust.py`)
- **AD trust, 0–100, under your seat.** It rises when you keep your word (anything you promised him that rode on
  a game or a season), give answers he likes (in his inbox and at the podium), and meet his goals. It falls when
  you break your word, ask for money (more each time), miss goals, or leave him on read.
- **What it does:** a trusting AD takes bad results easier (up to 25% less seat heat) and good results count for
  more; a skeptical one reads every loss as a pattern (up to 25% more). When you ask for money, trust decides how
  much he finds. His messages sound like it ("You've earned some rope with me" / "I've heard promises before").
- **Where you see it:** next to his name on every AD message, and on your career page with the last few things
  that moved it.
- **A new AD starts over** — take a new job or have your AD replaced and trust resets; a little lower if he
  inherited you.

## Morale is contagious
- **Captains pull the whole locker room toward their own mood** — happy captains lift it, unhappy ones drag it.
- **An unhappy wild card in the two-deep** (Diva, Hothead, Headcase, Mercenary...) drags his whole position room
  down; a happy leader lifts his.
- **The captains vote is now your call too:** after the team votes, accept it, add a fourth captain of your
  choosing, or overrule it (swap out a wild card or an unhappy captain) — the room notices either way.
- **The locker room screen** shows the captains' mood and whether it's lifting or dragging the room, who's
  dragging down which position group, and who's lifting theirs.
- Morale reasons read as what happened ("you sat down with him", "stripped of the C", "a recruiting promise
  broken").
- Tuning: losing seasons wear on everybody a little more; a single broken promise to your AD no longer counts twice.

---

# From the rebuild experiment (Georgia State, 8 seasons, 4 runs)
What it showed: a well-run rebuild works (bottom of the Coastal Plains to 8–5 / 10–3 seasons with a safe seat), and
leaving the staff on autopilot got the coach fired in year five both times. But the money never followed the
winning, and AD trust maxed out and stayed there. Fixed:

- **Fix — simming seasons crashed when a school offered you a job.** Your agent read the offers in the wrong
  format. He now takes the best one when you're out of work or it's clearly bigger (and a school that pushes out
  its coach to hire you does it properly).
- **Budgets follow a winning small program.** New: *winning above its weight* — a program whose last three
  seasons beat what a school of its prestige usually does gets budget growth (about 2–3% a year), plus a little
  more for every bowl season, and a league title counts for more outside the Power 4. A 6–7 bowl team no longer
  counts as a losing season. Eight straight winning years now take Georgia State from $4.6M to about $5.9M —
  toward the middle of its league, not past it. Big programs grow as before.
- **AD trust is harder to max out.** The closer he is to all-in, the less each good moment adds, and every
  December last year's goodwill fades a fifth of the way back toward neutral ("the bar goes up every year").

---

# New: the coaching tree (Career mode — your coach only) (`skills.py`)
Money still buys your ratings (Develop your coach), and the world still hands out reputation traits. The tree
is the part you choose: 42 perks across six branches that change how the game's systems work for you.

- **Earning points (the December review):** +1 for finishing a season, +1/+2 for beating your expected wins by
  2/4, +1 for a bowl and +1 for winning it, +2 conference title, +2 playoff, +3 national title, +1 beating your
  rival, +1 per AD goal met, +1/+2 for a top-25/top-10 class. Plus +1 per first-round pick you coached (after the
  draft) and career milestones (first win, 50, 100, 150, 200). A rebuilding year is about 2, a good year 4–5, a
  title run 8+. The whole tree costs about 110; a long career earns 50–70, so you specialize.
- **How a branch works:** four tiers, opening at 0 / 4 / 7 / 13 points spent in that branch. Tier 2 is a fork:
  pick one, the other locks for good. Tier 4 is the capstone. Costs 2 / 3 / 3 / 5 (Position Guru has 3 ranks).
- **Respec:** free once whenever you take a new job; otherwise you get 75% back.
- **Where:** tab 6 COACH → [T] (it shows how many points you have), or [T] on your career page. Points you earn
  arrive in your inbox with the breakdown.

The six branches:
- **Recruiter:** Silver Tongue (+8% interest) · Film Junkie (evaluating costs 1 hour, often reveals two things) ·
  fork **Hometown Hero** (+15% in-state) / **National Brand** (distance hurts half as much) · Promise Keeper (+25%
  promise pull, first broken promise each year forgiven) · Flip Artist (no penalty pushing other schools' commits,
  flips +50%) · capstone **Machine** (+15% recruiting hours).
- **Developer:** Position Guru (+10% development per rank for a group you choose) · Strength Program (−8%
  injuries) · fork **Redshirt Factory** (freshmen who sit develop +20%) / **Plug and Play** (freshmen arrive ~3
  better) · Walk-on Magic (walk-ons +25%) · Pro League Pipeline (draft picks lift next year's recruits at their
  position) · capstone **Everybody Gets Better** (+6% development for everyone).
- **Motivator:** Open Door (player meetings cost no hours; morale boosts +25%) · Captain's Council (captains pull
  50% harder) · fork **Players' Coach** (portal odds −20%, discipline does half as much) / **Hard Nosed**
  (discipline does 50% more, morale settles 4 lower) · Halftime Speech (+15% to land) · Thick Skin (wild cards
  drag half as much) · capstone **Run Through a Wall** (chemistry worth up to 1.5 points).
- **Tactician:** Film Room (practice lift +25%) · Clock Manager (+poise late) · fork **Riverboat** (+20
  fourth-down aggression, more trick plays) / **Field Position** (+0.4 in the fourth quarter with a lead) ·
  Halftime Genius (your adjustments +50%) · Big-Game Coach (+0.5 vs ranked teams and your rival) · capstone
  **Schemer** (the other staff adapts half as well after halftime).
- **Politician:** Media Savvy (measured answers stop costing recruits; humble stops annoying win-now ADs) ·
  Booster Circuit (+25% when you ask for money) · fork **Teflon** (losses heat your seat 20% less) / **Lightning
  Rod** (seat moves 25% more both ways, recruits +10%) · Trusted Voice (AD trust gains +30%, losses −30%) ·
  Fundraiser (budget growth +50%, higher cap) · capstone **Face of the Program** (bigger jobs call; trust never
  below 40).
- **Program Builder:** Groundbreaker (facility upgrades −15%) · Collective Ties (+5% NIL pool) · fork **Coaching
  Tree** (coordinators more willing to join, slower to leave) / **Scheme Identity** (+15 scheme-fit pitch) ·
  Stadium Experience (+0.3 at home, +25% stadium revenue) · Staff Developer (coordinators count 50% more in
  development) · capstone **Blueprint** (facilities never slip; budget never shrinks).

### v40.1a — Inbox crash fix
- Fixed a merge regression where opening the Inbox crashed at the NEEDS YOUR REPLY divider because `section()` was not imported in `people.py`.
- Hardened inbox loading so messages from older/forked saves are normalized with safe defaults for newer UI fields instead of crashing on missing message metadata.
- Smoke-tested inbox list rendering, opening a message, leaving it for later, replying to it, and rendering deliberately incomplete legacy messages.

### v40.1b — Portrait Renderer Fix
- Restored the desktop window's 24-bit ANSI color parser used by procedural faces.
- Restored the special half-block face renderer so each `▀` correctly represents a top and bottom portrait pixel without line-gap artifacts.
- Fixes portraits appearing as scrambled color blocks after the branch merge.

## v40.2 — Saturday Statbook + In-Game Subs
- Added a TEAM STATISTICS screen from tab 3 with national FBS ranks for scoring, total/rush/pass offense and defense, yards per play, success rate, explosive plays, third/fourth down, red-zone TD rate, turnover margin, sacks/TFL, penalties, first downs and possession.
- Explosive plays are tracked from the actual snap results using the familiar college split: 10+ yard runs or 20+ yard passes. 20+ yard plays are also tracked separately.
- Box scores now include yards/play, success rate, explosive plays, 10+ runs, 20+ passes, fourth downs and red-zone TDs.
- Added in-game substitutions to the coach headset. [B] lets you switch two players within a position room or toggle mass subs; manual swaps persist through lineup rebuilds/injuries for the rest of the game.

## v42.2a — Custom Players Folder
- Removed the operating-system file picker from player-database import.
- Added a dedicated `custom players` folder beside the game files. Before creating a world, [P] now shows a numbered in-game list of every JSON database in that folder.
- Bundled the 299-player 2026 real-school database plus the small example database in that folder.

### v42.2b — Post-burn-in player databases
- Custom player databases are now applied only after the four-season world-history simulation completes, immediately before the 2026 career begins. Imported real players can no longer disappear during burn-in.
- The importer now reserves a unique generated roster slot for every record, so multiple imported players at the same school and position no longer overwrite each other.
- Bundled real-player database expanded from 299 to 476 players across 120 programs, adding more 2026 award-watch-list quarterbacks, backs, linebackers, defensive backs, centers, kickers and punters.
