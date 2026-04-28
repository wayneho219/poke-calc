import base64
from pathlib import Path
from shared.config import TYPE_SPRITES_DIR

_TYPE_COLORS: dict[str, str] = {
    "normal":   "#A8A77A", "fire":     "#EE8130", "water":    "#6390F0",
    "electric": "#F7D02C", "grass":    "#7AC74C", "ice":      "#96D9D6",
    "fighting": "#C22E28", "poison":   "#A33EA1", "ground":   "#E2BF65",
    "flying":   "#A98FF3", "psychic":  "#F95587", "bug":      "#A6B91A",
    "rock":     "#B6A136", "ghost":    "#735797", "dragon":   "#6F35FC",
    "dark":     "#705746", "steel":    "#B7B7CE", "fairy":    "#D685AD",
}

_DARK_TEXT_TYPES = {"electric", "ice", "ground", "steel"}


def type_badge_html(type_en: str, type_name: str) -> str:
    """Return an HTML <span> badge for a single type, with optional embedded PNG."""
    color = _TYPE_COLORS.get(type_en, "#888888")
    text_color = "#333333" if type_en in _DARK_TEXT_TYPES else "#ffffff"
    img_tag = ""
    sprite_path: Path = TYPE_SPRITES_DIR / f"{type_en}.png"
    if sprite_path.exists():
        b64 = base64.b64encode(sprite_path.read_bytes()).decode()
        img_tag = (
            f'<img src="data:image/png;base64,{b64}" '
            f'style="width:16px;height:16px;vertical-align:middle;'
            f'border-radius:2px;margin-right:3px;image-rendering:pixelated">'
        )
    return (
        f'<span style="display:inline-flex;align-items:center;background:{color};'
        f'border-radius:4px;padding:2px 8px;font-size:11px;font-weight:bold;'
        f'color:{text_color};font-family:monospace;margin:2px">'
        f"{img_tag}{type_name}</span>"
    )


def types_html(types: tuple[str, ...], translator) -> str:
    """Return concatenated badge HTML for a list of types."""
    return "".join(type_badge_html(tp, translator.type_name(tp)) for tp in types)
