from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
INPUT_DIR = ROOT / "input"
SRC_DIR = ROOT / "src"
DOCS_DIR = ROOT / "docs"
OOF_DIR = ROOT / "oof"
SUBMISSION_DIR = ROOT / "submissions"
MODELS_DIR = ROOT / "models"
ENVIRONMENTS_DIR = INPUT_DIR / "environment_files"
WHEELS_DIR = INPUT_DIR / "arc_agi_3_wheels"

SEED = 42

PUBLIC_GAMES = [
    "ar25",
    "bp35",
    "cd82",
    "cn04",
    "dc22",
    "ft09",
    "g50t",
    "ka59",
    "lf52",
    "lp85",
    "ls20",
    "m0r0",
    "r11l",
    "re86",
    "s5i5",
    "sb26",
    "sc25",
    "sk48",
    "sp80",
    "su15",
    "tn36",
    "tr87",
    "tu93",
    "vc33",
    "wa30",
]
