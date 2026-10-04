TASKS_PER_ROUND = 7
WIN_THRESHOLD = 5  # correct tasks needed to win
TIME_EASY_S = 13
TIME_MEDIUM_S = 10
TIME_HARD_S = 7
XP_CORRECT_TASK = 1
XP_WIN_BONUS = 5
LEVEL_THRESHOLDS = [0, 30, 80, 150, 250, 400, 600, 850, 1150, 1500]
LEVEL_PREFIXES_RU = [
    "ути-пути",
    "микро",
    "мини",
    "настоящий",
    "супер",
    "мега",
    "убер",
    "великий",
    "величайший",
    "божественный",
]
TROPHY_THRESHOLDS = [20, 100, 200, 500]
NOTE_RANGE = {
    "treble": [(name, octave) for octave in (4, 5) for name in "CDEFGAB"][:-1],
    "bass": [(name, octave) for octave in (2, 3, 4) for name in "CDEFGAB"][2:15],
}
ANIMAL_IDS = [
    "unicorn",
    "dragon",
    "phoenix",
    "griffin",
    "sphinx_cat",
    "kitsune_fox",
    "pegasus",
    "mermaid",
    "lion",
    "panda",
    "rhino",
]
AVATAR_WORKER_LOCK_ID = 710024007
