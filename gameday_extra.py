"""
gameday_extra.py — More for the Campus Countdown crew to say. Folded into the base pools
once, at show time (gameday_show._merge_content). One line per entry; add freely.
"""

# ── The one-on-one: more questions, each with its own answers ────────────────
# topic -> [(question, [(answer, follow-up question or None, follow-up answer or None)])]
INTERVIEW_QA_EXTRA = {
    "opponent": [
        ("Who's the one guy on {opp} you've circled on the film?",
         [("Their middle linebacker. He's everywhere. You have to know where he is on every snap.", "Every snap?",
           "Every single one. He's the kind of player who ruins a game plan."),
          ("Their best corner. I asked to see his tape specifically. I want that matchup.", None, None)]),
        ("What does {opp} do that nobody talks about?",
         [("They're patient. They'll run the same play six times until you get bored and make a mistake.", None, None),
          ("They communicate better than anybody on our schedule. On film you can hear them calling out plays.", "Do they get it right?",
           "More than I'd like.")]),
    ],
    "season": [
        ("What's one play from this season you've watched more than any other?",
         [("A fumble I had in the first half against a team we beat. I watch it every Sunday. Never again.", None, None),
          ("A block a freshman made for me on a touchdown. Nobody noticed but us. I showed the whole room.", None, None)]),
        ("If this season were a movie, what part are we in?",
         [("The montage. Training, sweating, some inspirational music.", "What's the song?", "I can't say on TV. Coach would kill me."),
          ("Right before the big scene. Everybody's watching. Nobody knows how it ends.", None, None)]),
    ],
    "pressure": [
        ("How do you handle the noise — social media, the talk shows, all of it?",
         [("I deleted everything in August. My roommate tells me if something important happens.", "Does he?",
           "Mostly memes. He's bad at the job."),
          ("I read all of it. The mean ones are the best fuel.", None, None)]),
        ("What's your routine the night before a game like this?",
         [("Same hotel room setup every week. Shoes by the door, playbook on the nightstand, lights out at ten.", None, None),
          ("I call my grandmother. She tells me to tackle somebody. Then I sleep like a baby.", "Even on offense?",
           "She doesn't care what side of the ball I'm on.")]),
    ],
    "teammate": [
        ("Who's the funniest guy in your locker room?",
         [("Our long snapper. He does impressions of every coach. Every coach.", "Even the head coach?",
           "Especially the head coach. He's heard it. He laughed. Kind of."),
          ("Our backup quarterback. He should have his own show.", None, None)]),
        ("Who's the most underrated player on your team?",
         [("{mate}. He never shows up in a box score and he wins us games.", None, None),
          ("Our right guard. You'll never hear his name. That means he's doing his job.", None, None)]),
    ],
    "coach": [
        ("What's the best piece of advice {hc} has given you?",
         [("'Be where your feet are.' I didn't get it until this year.", "What does it mean to you now?",
           "Don't live in the last play. Don't live in the next game. Be here."),
          ("'Nobody cares, work harder.' It's on a sign in our weight room.", None, None)]),
    ],
    "home": [
        ("What would the people back home in {home_state} say about you playing in this game?",
         [("My whole church is watching. The pastor moved the service up an hour.", None, None),
          ("That I owe them all tickets. I've heard that a lot this week.", "How many?", "About four hundred.")]),
    ],
    "fun": [
        ("What's the worst haircut you've ever had?",
         [("Freshman year, I let a teammate do it. We lost that week. I blame him.", None, None),
          ("There's a picture from eighth grade that my mom uses as her phone background. It's a crime.", None, None)]),
        ("Who's the best cook on the team?",
         [("Our nose tackle. He makes a gumbo that'll change your life.", "Is he coming on the show next week?",
           "Only if Boom lets him in the tailgate segment."),
          ("Nobody. We eat at the dining hall and we're grateful.", None, None)]),
        ("If you could play one other position for one snap, what would it be?",
         [("Quarterback. Just one throw. Deep. I'd miss it by ten yards and be happy.", None, None),
          ("Kicker. For the attention. Kickers get so much attention.", None, None)]),
        ("What's on your pregame playlist that would surprise people?",
         [("Country. Old country. Don't tell my teammates.", None, None),
          ("Disney songs. I'm not ashamed. Okay, I'm a little ashamed.", "Which one?", "I'll take that to my grave.")]),
    ],
}

# ── More banter between the regulars ────────────────────────────────────────
BANTER_EXTRA = [
    [("boom", "{film}, what's the most film you've ever watched in one day?"), ("film", "Nineteen hours."),
     ("boom", "That's a cry for help."), ("film", "It was a bye week.")],
    [("defender", "When I played, we didn't have analytics. We had a guy named Dale."), ("host", "What did Dale do?"),
     ("defender", "Dale told us if the other team looked scared.")],
    [("host", "{coach}, is it true you timed your own wedding toast?"), ("coach", "Two minutes, forty seconds."),
     ("host", "How long was it supposed to be?"), ("coach", "Three minutes. I left time for a two-minute drill.")],
    [("boom", "I've decided I'm going to walk on next year."), ("coach", "At what position?"),
     ("boom", "Emotional support."), ("coach", "We have that. It's called the band.")],
    [("film", "I charted every blitz in the country this week."), ("defender", "All of them?"),
     ("film", "Four hundred and twelve."), ("defender", "And what did you learn?"), ("film", "That I need a hobby.")],
    [("host", "{boom_first}, why are you wearing two watches?"), ("boom", "One's for Eastern, one's for the West Coast games."),
     ("host", "Your phone does that."), ("boom", "My phone doesn't look this good.")],
    [("coach", "In my day, we practiced in two-a-days in August."), ("boom", "In my day, I practiced two naps a day."),
     ("coach", "That explains a lot.")],
    [("defender", "Somebody asked me for my autograph this morning."), ("film", "That's great."),
     ("defender", "They thought I was you."), ("film", "That's… also great, actually.")],
    [("host", "{coach}, what's the one thing you'd change about college football?"), ("coach", "Halftime."),
     ("host", "What's wrong with halftime?"), ("coach", "It's twenty minutes. I only need eight.")],
    [("boom", "I think I figured out the playoff formula."), ("film", "Let's hear it."),
     ("boom", "Win."), ("film", "…That's it?"), ("boom", "It's elegant.")],
]
