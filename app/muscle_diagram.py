"""
Muscle anatomy diagram using polygon data extracted from body-highlighter library.
Renders real anatomical muscle shapes as SVG — no external JS needed.
"""

import os
import re

# ── Parse polygon data from body-highlighter.min.js ────────────────────────

_JS_PATH = os.path.join(os.path.dirname(__file__), "body-highlighter.min.js")

def _parse_polygons() -> tuple[dict, dict]:
    """Returns (anterior_polygons, posterior_polygons).
    Each dict: {muscle_key: [polygon_points_string, ...]}
    """
    with open(_JS_PATH, encoding="utf-8") as f:
        src = f.read()

    pattern = r'muscle:e\.(\w+),svgPoints:\[(.*?)\](?=\})'
    all_matches = re.findall(pattern, src)

    def build_dict(matches):
        d: dict[str, list[str]] = {}
        for name, pts_str in matches:
            key = name.lower().replace("_", "-")
            pts = re.findall(r'"([^"]+)"', pts_str)
            d.setdefault(key, []).extend(pts)
        return d

    # First HEAD appearance splits anterior (0-12) from posterior (13+)
    anterior  = build_dict(all_matches[:13])
    posterior = build_dict(all_matches[13:])
    return anterior, posterior


_ANTERIOR, _POSTERIOR = _parse_polygons()

# Drawing order (back → front so muscles layer correctly)
_FRONT_ORDER = [
    "forearm", "calves", "knees", "quadriceps", "abductors",
    "abs", "obliques", "chest", "biceps", "triceps",
    "front-deltoids", "neck", "head",
]
_BACK_ORDER = [
    "forearm", "left-soleus", "right-soleus", "calves", "knees",
    "hamstring", "abductor", "gluteal", "lower-back",
    "upper-back", "triceps", "back-deltoids", "trapezius", "head",
]

# ── Muscle group → highlighted muscle keys ──────────────────────────────────

MUSCLE_MAP: dict[str, list[str]] = {
    # Russian
    "Грудь":        ["chest"],
    "Спина":        ["upper-back", "lower-back", "trapezius"],
    "Плечи":        ["front-deltoids", "back-deltoids", "trapezius"],
    "Бицепс":       ["biceps"],
    "Трицепс":      ["triceps"],
    "Пресс":        ["abs", "obliques"],
    "Квадрицепс":   ["quadriceps"],
    "Бицепс бедра": ["hamstring"],
    "Ягодицы":      ["gluteal"],
    "Икры":         ["calves", "left-soleus", "right-soleus"],
    # English
    "Chest":        ["chest"],
    "Back":         ["upper-back", "lower-back", "trapezius"],
    "Shoulders":    ["front-deltoids", "back-deltoids", "trapezius"],
    "Biceps":       ["biceps"],
    "Triceps":      ["triceps"],
    "Abs":          ["abs", "obliques"],
    "Quadriceps":   ["quadriceps"],
    "Hamstrings":   ["hamstring"],
    "Glutes":       ["gluteal"],
    "Calves":       ["calves", "left-soleus", "right-soleus"],
    # Spanish
    "Pecho":           ["chest"],
    "Espalda":         ["upper-back", "lower-back", "trapezius"],
    "Hombros":         ["front-deltoids", "back-deltoids", "trapezius"],
    "Bíceps":          ["biceps"],
    "Tríceps":         ["triceps"],
    "Abdomen":         ["abs", "obliques"],
    "Cuádriceps":      ["quadriceps"],
    "Isquiotibiales":  ["hamstring"],
    "Glúteos":         ["gluteal"],
    "Pantorrillas":    ["calves", "left-soleus", "right-soleus"],
    # German
    "Brust":        ["chest"],
    "Rücken":       ["upper-back", "lower-back", "trapezius"],
    "Schultern":    ["front-deltoids", "back-deltoids", "trapezius"],
    "Bizeps":       ["biceps"],
    "Trizeps":      ["triceps"],
    "Bauch":        ["abs", "obliques"],
    "Quadrizeps":   ["quadriceps"],
    "Oberschenkel": ["hamstring"],
    "Gesäß":        ["gluteal"],
    "Waden":        ["calves", "left-soleus", "right-soleus"],
    # French
    "Poitrine":        ["chest"],
    "Dos":             ["upper-back", "lower-back", "trapezius"],
    "Épaules":         ["front-deltoids", "back-deltoids", "trapezius"],
    "Abdos":           ["abs", "obliques"],
    "Ischio-jambiers": ["hamstring"],
    "Fessiers":        ["gluteal"],
    "Mollets":         ["calves", "left-soleus", "right-soleus"],
    # Hebrew
    "חזה":        ["chest"],
    "גב":         ["upper-back", "lower-back", "trapezius"],
    "כתפיים":     ["front-deltoids", "back-deltoids", "trapezius"],
    "ביצפס":      ["biceps"],
    "טריצפס":     ["triceps"],
    "בטן":        ["abs", "obliques"],
    "קוודריצפס":  ["quadriceps"],
    "ירך אחורית": ["hamstring"],
    "ישבן":       ["gluteal"],
    "שוק":        ["calves", "left-soleus", "right-soleus"],
}

# ── SVG rendering ───────────────────────────────────────────────────────────

_ACTIVE  = "#e74c3c"
_BODY    = "#e8c9a0"
_OUTLINE = "#b89060"
_ACTIVE_OUTLINE = "#c0392b"


def _render_view(polygons: dict, order: list, highlights: set) -> str:
    """Render one body view (anterior or posterior) as SVG content."""
    parts = []
    for key in order:
        pts_list = polygons.get(key, [])
        is_active = key in highlights
        fill    = _ACTIVE  if is_active else _BODY
        stroke  = _ACTIVE_OUTLINE if is_active else _OUTLINE
        sw      = "1.5" if is_active else "0.6"
        opacity = "1" if is_active else "0.9"
        for pts in pts_list:
            parts.append(
                f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{sw}" opacity="{opacity}"/>'
            )
    return "\n".join(parts)


def get_muscle_html(muscle_group: str, height: int = 380) -> str:
    highlights = set(MUSCLE_MAP.get(muscle_group, []))

    front_svg = _render_view(_ANTERIOR, _FRONT_ORDER, highlights)
    back_svg  = _render_view(_POSTERIOR, _BACK_ORDER,  highlights)

    label_color = _ACTIVE if highlights else "#555"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ margin:0; background:transparent;
          display:flex; flex-direction:column; align-items:center;
          font-family:sans-serif; }}
  .views {{ display:flex; gap:16px; justify-content:center; }}
  .view-label {{ font-size:10px; color:#888; text-align:center; margin-top:2px; }}
  .muscle-label {{ font-size:13px; color:{label_color}; font-weight:700;
                   text-align:center; margin-top:6px; }}
</style>
</head><body>
<div class="views">
  <div>
    <svg viewBox="0 0 100 210" width="130" height="273"
         xmlns="http://www.w3.org/2000/svg">
      {front_svg}
    </svg>
    <div class="view-label">спереди</div>
  </div>
  <div>
    <svg viewBox="0 0 100 210" width="130" height="273"
         xmlns="http://www.w3.org/2000/svg">
      {back_svg}
    </svg>
    <div class="view-label">сзади</div>
  </div>
</div>
<div class="muscle-label">{muscle_group}</div>
</body></html>"""
