from pathlib import Path

ROOT             = Path(__file__).parent.parent
CSV_PATH         = ROOT / "data" / "pokemon_names.csv"
DATA_JSON_PATH   = ROOT / "data" / "pokemon_data.json"
SPRITES_DIR      = ROOT / "data" / "sprites"
MEGA_SPRITES_DIR = ROOT / "data" / "sprites" / "mega"
TYPE_SPRITES_DIR = ROOT / "data" / "sprites" / "types"
CACHE_DIR        = ROOT / "adapters" / "cache"
I18N_DIR         = ROOT / "shared" / "i18n"
