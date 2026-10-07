"""
gameday_cast.py — The people on the Campus Countdown set, and the crowd behind them.

Names are the defaults; the Settings menu can rename anybody (saved to
settings.json). Everyone here is original. Each role is a seat at the desk, not a
particular person.

Adding guest pickers is meant to be easy: one line each in GUEST_PICKERS.
"""

# ═══ The regulars ═══════════════════════════════════════════════════════════
# weights: how much each analyst cares about each factor when picking a game
#   talent (roster overall)  qb  defense  coach  home (crowd)  form (record, streak)
# lean: extra personality — "contrarian" fades heavy favorites sometimes,
#       "upset" likes underdogs, "home" loves a home crowd

CAST = {
    "host": {"name": "Cal Merriman", "role": "Host",
             "bio": "Twenty years anchoring the show, a former sideline reporter",
             "weights": {"talent": .8, "qb": .4, "defense": .3, "coach": .3, "home": .5, "form": .6},
             "lean": "contrarian"},
    "film": {"name": "Trent Albright", "role": "Former QB, film analyst",
             "bio": "Four-year starting quarterback, the numbers-and-film voice",
             "weights": {"talent": 1.0, "qb": 1.2, "defense": .6, "coach": .2, "home": .3, "form": .3},
             "lean": None},
    "coach": {"name": "Harlan Voss", "role": "Legendary coach",
              "bio": "Thirty years as a head coach, famous for discipline, retired with titles",
              "weights": {"talent": .8, "qb": .3, "defense": .9, "coach": 1.2, "home": .4, "form": .4},
              "lean": None},
    "boom": {"name": "Jace Kowalski", "role": "Entertainer",
             "bio": "Former punter, now the loudest man on television",
             "weights": {"talent": .5, "qb": .3, "defense": .2, "coach": .1, "home": 1.4, "form": 1.0},
             "lean": "upset"},
    "defender": {"name": "Dorian Pettaway", "role": "Former star defender",
                 "bio": "All-American safety, the defense-first voice on the desk",
                 "weights": {"talent": .8, "qb": .3, "defense": 1.4, "coach": .3, "home": .4, "form": .5},
                 "lean": None},
}
ORDER = ("host", "film", "coach", "boom", "defender")

# What each analyst says his game comes down to. {h}/{a} home/away school.
KEYS = {
    "film": ["It's the trenches. {edge} has the better line, and the line decides this.",
             "Quarterback play. {qb_edge} has been more efficient, and that's the difference.",
             "Third down. Whoever stays ahead of the chains wins this one.",
             "I watched all their tape this week. {edge} is just a little cleaner everywhere."],
    "coach": ["Discipline. The team that doesn't beat itself wins this game.",
              "Depth. By the fourth quarter, {edge} has more bodies that can play.",
              "Coaching. I trust {coach_edge}'s staff to have the better plan.",
              "Special teams. Nobody talks about it, and it always matters in a game like this."],
    "boom": ["The crowd! Look around! You can't beat this crowd!",
             "Momentum, baby. {form_edge} is rolling and I'm riding it.",
             "It's a feeling. I have a FEELING about this one.",
             "Somebody's going to make a play that nobody in this building will ever forget."],
    "defender": ["Turnovers. {def_edge} gets its hands on the football more than anybody.",
                 "The defense wins. {def_edge} is going to take something away and dare them to beat it.",
                 "Tackling. You miss tackles in a game like this and it's a long day.",
                 "Whoever wins the explosive plays wins. {def_edge} doesn't give them up."],
    "host": ["I keep coming back to the records. {form_edge} has found ways to win all year.",
             "Everybody's picking the favorite. That always makes me nervous.",
             "It's the kind of game that comes down to one drive.",
             "I just think {edge} has a little more."],
}

# Banter between the regulars. {host} {film} {coach} {boom} {defender} are last names.
BANTER = [
    [("boom", "Coach, how many times did you coach in this stadium?"), ("coach", "A few. Won most of them."),
     ("boom", "Tell me about the ones you lost."), ("coach", "No."), ("crowd", "(laughter)")],
    [("host", "{film}, you had a bold pick last week."), ("film", "I don't want to talk about it."),
     ("defender", "I do."), ("crowd", "(laughter)")],
    [("boom", "I have a confession. I ate four breakfast burritos before the show."),
     ("host", "Four?"), ("boom", "Four. And I'd do it again."), ("crowd", "(cheering)")],
    [("defender", "When I played, we had a rule: if you dropped an interception, you owed the DBs dinner."),
     ("film", "How many dinners did you owe?"), ("defender", "We're not doing this."), ("crowd", "(laughter)")],
    [("coach", "Back in my day, we practiced twice a day in August, in pads, and we liked it."),
     ("boom", "Did you, though?"), ("coach", "...No."), ("crowd", "(laughter)")],
    [("host", "{boom} has picked the home team eleven weeks in a row."), ("boom", "Twelve after today."),
     ("film", "That's not analysis."), ("boom", "It's LOVE analysis.")],
    [("film", "I've got a stat for you. Teams that win the turnover battle win about eighty percent of the time."),
     ("defender", "So I've been right this whole time."), ("film", "About one thing, yes.")],
    [("boom", "I want everybody here to know that I once punted a ball sixty-one yards in a snowstorm."),
     ("coach", "Into the wind?"), ("boom", "...It was a crosswind."), ("crowd", "(laughter)")],
    [("host", "Somebody in the crowd has been holding up a cardboard cutout of {coach} all morning."),
     ("coach", "It's a good likeness."), ("defender", "It smiles more than you do, Coach.")],
    [("defender", "I got stopped at the airport yesterday by a fan who wanted me to sign his cast."),
     ("host", "What'd he break?"), ("defender", "His leg. Rushing the field last week."), ("crowd", "(cheering)")],
    [("film", "I went back and charted every snap of this matchup from last year."),
     ("boom", "Every snap?"), ("film", "Every snap."), ("boom", "{film_first}, you need a hobby."),
     ("film", "This IS my hobby.")],
    [("coach", "Young people ask me what the secret to coaching is."), ("host", "What do you tell them?"),
     ("coach", "Recruit great players. Then don't mess them up.")],
]

# ═══ The crowd ══════════════════════════════════════════════════════════════
# Signs: {h} home school, {a} visitor, {hn}/{an} nicknames, {qb} a home QB last
# name, {rival} the home team's rival, {host} {film} {coach} {boom} {defender}.

SIGNS = [
    "MY WIFE SAID PICK HER OR GAMEDAY. SEE YOU SATURDAY, LINDA.",
    "I SKIPPED MY MIDTERM FOR THIS. WORTH IT.",
    "{coach}, WEAR THE {HN} HEAD OR DON'T COME BACK",
    "{a} FANS: THE EXIT IS THAT WAY",
    "{boom} OWES ME $20",
    "HI MOM, PLEASE DON'T TELL DAD I SKIPPED CLASS",
    "{qb} FOR HEISMAN",
    "{a}'S DEFENSE HASN'T SEEN A REAL QB YET",
    "I'M HERE FOR THE FREE T-SHIRT",
    "MY DOG HAS A BETTER PICK RECORD THAN {host}",
    "{film}, SHOW US THE FILM",
    "ONE MORE {rival} LOSS AND I'M RENAMING MY KID",
    "WILL WORK FOR {h} TICKETS",
    "{h} > YOUR MORTGAGE PAYMENT",
    "{defender} SIGNED MY FOREHEAD IN 2015",
    "I DROVE 9 HOURS AND I'D DO IT AGAIN",
    "{a} HAS NEVER SEEN A CROWD LIKE THIS",
    "THIS SIGN IS SPONSORED BY NOBODY",
    "{boom}: MARRY ME (SERIOUSLY)",
    "FIRST GAMEDAY, FIRST SIGN, FIRST SUNBURN",
    "GRANDMA'S 80TH BIRTHDAY. SHE PICKED THE {HN}.",
    "{coach} > ALL OF YOU",
    "ASK ME ABOUT MY FANTASY TEAM (DON'T)",
    "IT'S NOT A REBUILD, IT'S A RELOAD",
    "HONK IF YOU'RE HERE FOR THE {HN}",
]
SIGN_REACTIONS = [
    ("defender", "That's a sign that'll age one way or the other by the fourth quarter today."),
    ("boom", "I love it. I love all of you."), ("film", "Bold. I respect it."),
    ("coach", "Young man, I've seen that sign before. It didn't work out."), ("host", "We'll see about that."),
    ("boom", "Somebody get that person a hot dog."), ("defender", "Man, that's cold."),
    ("film", "Statistically? Not wrong."), ("coach", "I like his confidence."),
]
CROWD_ROAR = ["(roaring)", "(deafening)", "(the whole lawn is jumping)", "(cheering)", "(a wall of noise)",
              "(going absolutely wild)", "(stomping and screaming)", "(a massive roar)", "(chanting the fight song)"]
CROWD_BOO = ["(booing)", "(loud booing)", "(a chorus of boos)"]
CROWD_LAUGH = ["(laughter)", "(laughing)"]

# ═══ Guest pickers ══════════════════════════════════════════════════════════
# One line each: (who they are, what they say when they pick, bias)
#   bias: "home" always picks the home team · "heart" home unless it's hopeless
#         "chalk" picks the favorite · "upset" picks the underdog · "coin" anything
# {school} {nick} {state} fill in for the host campus. Add as many as you like.

GUEST_PICKERS = [
    ("has driven the same ice cream truck to every {school} home game for twenty-six years",
     "I've got one pick, and it's the one I've made since 1999.", "home"),
    ("is the longest-serving tuba player in the {school} marching band", "The band never loses, and neither do we.",
     "home"),
    ("has painted his face for 300 straight {school} home games", "Three hundred games. Three hundred wins in my heart.",
     "home"),
    ("is the {school} campus bus driver who knows every student by name", "Everybody on my route says the same thing.",
     "home"),
    ("runs the barbecue stand across from the stadium", "The smoker told me this morning. It's never wrong.", "heart"),
    ("is a 94-year-old season ticket holder since the Truman administration", "I've seen them all, young man.",
     "heart"),
    ("is the town's high school football coach", "I tell my kids to play for the team in front of them.", "chalk"),
    ("is the {school} mascot's mom", "I'm legally obligated to pick this one.", "home"),
    ("is a kindergarten teacher who got 26 kids to write the fight song", "The kids voted. It was unanimous.", "home"),
    ("proposed to his wife on the 50-yard line", "She said yes. That's a good omen.", "home"),
    ("is the local weatherman, forecasting a {nick} storm", "Hundred percent chance of a win.", "home"),
    ("is the {school} team chaplain", "I've been praying on it all week.", "heart"),
    ("is the {school} equipment manager for 31 years", "I've packed every bag. I know what's in them.", "chalk"),
    ("is the best tailgate chef in {state}, by her own count", "Ribs don't lie.", "home"),
    ("won the {school} student pie-eating contest", "I'm running on nine pies. I've never felt clearer.", "coin"),
    ("is the town fire chief", "We've got trucks on standby for the celebration.", "home"),
    ("is the {school} head groundskeeper who mowed the field this morning", "Grass knows who it wants to win.",
     "home"),
    ("is a nursing student who works nights at the local hospital", "Somebody's going to need a doctor. Not us.",
     "home"),
    ("is the {school} student body president", "This is the only thing everybody agrees on.", "home"),
    ("is a retired sheriff who worked stadium security for 30 years", "I've seen the underdog get lucky.", "upset"),
    ("is the country singer from just down the road", "I wrote a song about this pick. It's short.", "home"),
    ("owns the diner where the team eats breakfast", "They clean their plates. That's all you need to know.",
     "home"),
    ("is the {school} library's longest-tenured librarian", "I've read up on this. Quietly.", "chalk"),
    ("is a veteran who hasn't missed a home game since coming back", "Home. Always home.", "home"),
    ("won the regional hot dog-eating title", "Twelve dogs. One pick.", "coin"),
    ("is the youngest season ticket holder, at six months", "(points at the helmet)", "coin"),
    ("is the local dentist who gives free mouthguards to the youth leagues", "Brush, floss, and win.", "home"),
    ("is the grandma who knits a scarf for every senior on the roster", "My boys are ready.", "home"),
    ("drove a tractor 200 miles to be here", "Took me three days. I'm not leaving disappointed.", "home"),
    ("is the {school} campus's resident cat whisperer", "The cats have spoken.", "coin"),
    ("is a professional wrestler from {state}", "OHHHH YEAH, it's the {nick}!", "home"),
    ("is the high school band director whose kids opened the show", "The drums don't lie.", "home"),
    ("coaches the local Little League champions", "We know a thing or two about upsets.", "upset"),
    ("is the math professor who predicted last year's score exactly", "The model says...", "chalk"),
    ("has been to every bowl game the {school} {nick} ever played", "I've seen the big stage. We belong there.", "heart"),
    ("is the {school} alumnus who flew in from Tokyo", "Fourteen hours on a plane. Home team.", "home"),
    ("runs the campus bookstore that sold out of hats this week", "Inventory's gone. So's the other team.", "home"),
    ("is a paramedic on the stadium medical team", "We're ready for anything. Including a win.", "heart"),
    ("was a walk-on who never played a down and still has his jersey", "Once a {nick}, always a {nick}.", "home"),
    ("is the town mayor, who declared today a local holiday", "By order of this office...", "home"),
    ("is a farmer who planted the team logo in his cornfield", "You can see it from the planes.", "home"),
    ("is the {school} cheerleading coach", "We've got the spirit. They've got nothing.", "home"),
    ("is a stand-up comedian from {state}", "My pick is the funniest thing I'll say all day.", "upset"),
    ("is the {school} president's secretary for 22 years", "I know things. I can't say what.", "home"),
    ("is a truck driver who listens to every game on the radio", "Four million miles, all of them with this team.",
     "home"),
    ("won the school's rock-paper-scissors championship", "Rock. Always rock. And the {nick}.", "coin"),
    ("is the family that's tailgated in the same spot since 1972", "Three generations, one pick.", "home"),
    ("is a baseball coach who wandered over from practice", "I only know one thing about football.", "chalk"),
    ("is the {school} student who lives in a tent outside the stadium", "Forty-one nights. I earned this pick.",
     "home"),
    ("is the {school} team's oldest living letterman", "We played both ways in my day. Pick the tough team.",
     "heart"),
    ("is a TikTok star with more followers than the town has people", "Link in bio. And the {nick}.", "home"),
    ("repairs every broken seat in the stadium", "I know every seat. They'll all be full of happy people.",
     "home"),
    ("is the chef at the athletes' dining hall", "I've seen what they eat. They're ready.", "home"),
    ("is the {school} team's former punter, now a middle school principal", "Punters don't get enough credit.",
     "heart"),
    ("is a {state} state trooper who escorts the team bus", "I've seen their faces on the bus. They're locked in.",
     "home"),
    ("is a psychology professor who studies crowd behavior", "This crowd? Home team, easy.", "home"),
    ("is the kid who caught a touchdown ball in the stands last year", "It was destiny. So is this.", "home"),
    ("is a retired referee who swears he never had a favorite", "I never had a favorite. Until today.", "home"),
    ("is the {school} beekeeping club president", "The bees are buzzing about it.", "coin"),
    ("is a veterinarian who cares for the live mascot", "The mascot ate breakfast well. Good sign.", "home"),
]
