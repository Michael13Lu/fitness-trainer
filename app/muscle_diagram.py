"""Muscle anatomy diagram using body-highlighter library."""

# Maps app muscle group names → body-highlighter muscle identifiers
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
    "Икры":         ["calves"],
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
    "Calves":       ["calves"],
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
    "Pantorrillas":    ["calves"],
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
    "Waden":        ["calves"],
    # French
    "Poitrine":        ["chest"],
    "Dos":             ["upper-back", "lower-back", "trapezius"],
    "Épaules":         ["front-deltoids", "back-deltoids", "trapezius"],
    "Abdos":           ["abs", "obliques"],
    "Ischio-jambiers": ["hamstring"],
    "Fessiers":        ["gluteal"],
    "Mollets":         ["calves"],
    # Hebrew
    "חזה":       ["chest"],
    "גב":        ["upper-back", "lower-back", "trapezius"],
    "כתפיים":    ["front-deltoids", "back-deltoids", "trapezius"],
    "ביצפס":     ["biceps"],
    "טריצפס":    ["triceps"],
    "בטן":       ["abs", "obliques"],
    "קוודריצפס": ["quadriceps"],
    "ירך אחורית":["hamstring"],
    "ישבן":      ["gluteal"],
    "שוק":       ["calves"],
}


def get_muscle_html(muscle_group: str, height: int = 380) -> str:
    muscles = MUSCLE_MAP.get(muscle_group, [])
    muscles_json = str(muscles).replace("'", '"')

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin: 0; background: transparent; display: flex;
          flex-direction: column; align-items: center; font-family: sans-serif; }}
  #chart {{ display: flex; justify-content: center; gap: 10px; }}
  svg {{ max-width: 130px; }}
  .label {{ font-size: 12px; color: #e74c3c; font-weight: 600;
            text-align: center; margin-top: 4px; }}
</style>
</head>
<body>
<div id="chart"></div>
<div class="label">{muscle_group}</div>

<script src="https://unpkg.com/body-highlighter@2.2.0/dist/body-highlighter.min.js"></script>
<script>
  const muscles = {muscles_json};
  const data = muscles.map(m => ({{ muscles: [m], color: '#e74c3c' }}));

  const front = document.createElement('div');
  const back  = document.createElement('div');
  document.getElementById('chart').appendChild(front);
  document.getElementById('chart').appendChild(back);

  bodyHighlighter.init(data, front, {{ side: 'front' }});
  bodyHighlighter.init(data, back,  {{ side: 'back'  }});
</script>
</body>
</html>"""
