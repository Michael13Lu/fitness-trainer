"""SVG muscle group diagram — front and back body views with highlighted muscles."""

MUSCLE_HIGHLIGHTS: dict[str, list[str]] = {
    # Russian
    "Грудь":        ["pec_l", "pec_r", "front_delt_l", "front_delt_r"],
    "Спина":        ["upper_back", "lat_l", "lat_r", "lower_back", "trap"],
    "Плечи":        ["front_delt_l", "front_delt_r", "rear_delt_l", "rear_delt_r", "trap"],
    "Бицепс":       ["bicep_l", "bicep_r"],
    "Трицепс":      ["tricep_l", "tricep_r"],
    "Пресс":        ["abs"],
    "Квадрицепс":   ["quad_l", "quad_r"],
    "Бицепс бедра": ["ham_l", "ham_r"],
    "Ягодицы":      ["glute_l", "glute_r"],
    "Икры":         ["calf_l", "calf_r"],
    # English
    "Chest":        ["pec_l", "pec_r", "front_delt_l", "front_delt_r"],
    "Back":         ["upper_back", "lat_l", "lat_r", "lower_back", "trap"],
    "Shoulders":    ["front_delt_l", "front_delt_r", "rear_delt_l", "rear_delt_r", "trap"],
    "Biceps":       ["bicep_l", "bicep_r"],
    "Triceps":      ["tricep_l", "tricep_r"],
    "Abs":          ["abs"],
    "Quadriceps":   ["quad_l", "quad_r"],
    "Hamstrings":   ["ham_l", "ham_r"],
    "Glutes":       ["glute_l", "glute_r"],
    "Calves":       ["calf_l", "calf_r"],
    # Spanish
    "Pecho":           ["pec_l", "pec_r", "front_delt_l", "front_delt_r"],
    "Espalda":         ["upper_back", "lat_l", "lat_r", "lower_back", "trap"],
    "Hombros":         ["front_delt_l", "front_delt_r", "rear_delt_l", "rear_delt_r", "trap"],
    "Bíceps":          ["bicep_l", "bicep_r"],
    "Tríceps":         ["tricep_l", "tricep_r"],
    "Abdomen":         ["abs"],
    "Cuádriceps":      ["quad_l", "quad_r"],
    "Isquiotibiales":  ["ham_l", "ham_r"],
    "Glúteos":         ["glute_l", "glute_r"],
    "Pantorrillas":    ["calf_l", "calf_r"],
    # German
    "Brust":       ["pec_l", "pec_r", "front_delt_l", "front_delt_r"],
    "Rücken":      ["upper_back", "lat_l", "lat_r", "lower_back", "trap"],
    "Schultern":   ["front_delt_l", "front_delt_r", "rear_delt_l", "rear_delt_r", "trap"],
    "Bizeps":      ["bicep_l", "bicep_r"],
    "Trizeps":     ["tricep_l", "tricep_r"],
    "Bauch":       ["abs"],
    "Quadrizeps":  ["quad_l", "quad_r"],
    "Oberschenkel":["ham_l", "ham_r"],
    "Gesäß":       ["glute_l", "glute_r"],
    "Waden":       ["calf_l", "calf_r"],
    # French
    "Poitrine":        ["pec_l", "pec_r", "front_delt_l", "front_delt_r"],
    "Dos":             ["upper_back", "lat_l", "lat_r", "lower_back", "trap"],
    "Épaules":         ["front_delt_l", "front_delt_r", "rear_delt_l", "rear_delt_r", "trap"],
    "Abdos":           ["abs"],
    "Ischio-jambiers": ["ham_l", "ham_r"],
    "Fessiers":        ["glute_l", "glute_r"],
    "Mollets":         ["calf_l", "calf_r"],
    # Hebrew
    "חזה":      ["pec_l", "pec_r", "front_delt_l", "front_delt_r"],
    "גב":       ["upper_back", "lat_l", "lat_r", "lower_back", "trap"],
    "כתפיים":   ["front_delt_l", "front_delt_r", "rear_delt_l", "rear_delt_r", "trap"],
    "ביצפס":    ["bicep_l", "bicep_r"],
    "טריצפס":   ["tricep_l", "tricep_r"],
    "בטן":      ["abs"],
    "קוודריצפס":["quad_l", "quad_r"],
    "ירך אחורית":["ham_l", "ham_r"],
    "ישבן":     ["glute_l", "glute_r"],
    "שוק":      ["calf_l", "calf_r"],
}

ACTIVE   = "#e74c3c"
BODY     = "#f0d9c0"
OUTLINE  = "#c49a6c"
TEXT_CLR = "#4a4a4a"


def get_muscle_svg(muscle_group: str) -> str:
    highlights = MUSCLE_HIGHLIGHTS.get(muscle_group, [])

    def f(pid: str) -> str:      # fill
        return ACTIVE if pid in highlights else BODY

    def s(pid: str) -> str:      # stroke
        return "#c0392b" if pid in highlights else OUTLINE

    def w(pid: str) -> str:      # stroke-width
        return "2.5" if pid in highlights else "1"

    return f"""
<svg width="290" height="320" viewBox="0 0 290 320" xmlns="http://www.w3.org/2000/svg"
     style="background:#f8f9fa;border-radius:10px;display:block;margin:auto">

  <!-- Labels -->
  <text x="68"  y="312" text-anchor="middle" font-size="10" fill="{TEXT_CLR}" font-family="sans-serif">Вид спереди</text>
  <text x="218" y="312" text-anchor="middle" font-size="10" fill="{TEXT_CLR}" font-family="sans-serif">Вид сзади</text>
  <line x1="145" y1="8" x2="145" y2="298" stroke="#dee2e6" stroke-width="1"/>

  <!-- ══════════ FRONT VIEW (center x≈68) ══════════ -->

  <!-- Head -->
  <ellipse cx="68" cy="22" rx="17" ry="20" fill="{BODY}" stroke="{OUTLINE}" stroke-width="1"/>
  <!-- Neck -->
  <rect x="62" y="42" width="12" height="11" fill="{BODY}" stroke="{OUTLINE}" stroke-width="1"/>

  <!-- Front deltoids -->
  <ellipse id="front_delt_l" cx="39" cy="63" rx="14" ry="11"
           fill="{f('front_delt_l')}" stroke="{s('front_delt_l')}" stroke-width="{w('front_delt_l')}"/>
  <ellipse id="front_delt_r" cx="97" cy="63" rx="14" ry="11"
           fill="{f('front_delt_r')}" stroke="{s('front_delt_r')}" stroke-width="{w('front_delt_r')}"/>

  <!-- Pecs -->
  <rect id="pec_l" x="42" y="53" width="26" height="30" rx="4"
        fill="{f('pec_l')}" stroke="{s('pec_l')}" stroke-width="{w('pec_l')}"/>
  <rect id="pec_r" x="68" y="53" width="26" height="30" rx="4"
        fill="{f('pec_r')}" stroke="{s('pec_r')}" stroke-width="{w('pec_r')}"/>

  <!-- Biceps -->
  <rect id="bicep_l" x="30" y="74" width="12" height="34" rx="6"
        fill="{f('bicep_l')}" stroke="{s('bicep_l')}" stroke-width="{w('bicep_l')}"/>
  <rect id="bicep_r" x="94" y="74" width="12" height="34" rx="6"
        fill="{f('bicep_r')}" stroke="{s('bicep_r')}" stroke-width="{w('bicep_r')}"/>

  <!-- Forearms front -->
  <rect x="28" y="108" width="12" height="34" rx="5" fill="{BODY}" stroke="{OUTLINE}" stroke-width="1"/>
  <rect x="96" y="108" width="12" height="34" rx="5" fill="{BODY}" stroke="{OUTLINE}" stroke-width="1"/>

  <!-- Abs -->
  <rect id="abs" x="44" y="83" width="46" height="48" rx="5"
        fill="{f('abs')}" stroke="{s('abs')}" stroke-width="{w('abs')}"/>

  <!-- Pelvis front -->
  <rect x="42" y="131" width="52" height="16" rx="5" fill="{BODY}" stroke="{OUTLINE}" stroke-width="1"/>

  <!-- Quads -->
  <rect id="quad_l" x="42" y="147" width="22" height="66" rx="8"
        fill="{f('quad_l')}" stroke="{s('quad_l')}" stroke-width="{w('quad_l')}"/>
  <rect id="quad_r" x="72" y="147" width="22" height="66" rx="8"
        fill="{f('quad_r')}" stroke="{s('quad_r')}" stroke-width="{w('quad_r')}"/>

  <!-- Shins front -->
  <rect x="42" y="213" width="22" height="58" rx="6" fill="{BODY}" stroke="{OUTLINE}" stroke-width="1"/>
  <rect x="72" y="213" width="22" height="58" rx="6" fill="{BODY}" stroke="{OUTLINE}" stroke-width="1"/>

  <!-- ══════════ BACK VIEW (center x≈218) ══════════ -->

  <!-- Head -->
  <ellipse cx="218" cy="22" rx="17" ry="20" fill="{BODY}" stroke="{OUTLINE}" stroke-width="1"/>
  <!-- Neck back -->
  <rect x="212" y="42" width="12" height="11" fill="{BODY}" stroke="{OUTLINE}" stroke-width="1"/>

  <!-- Traps -->
  <rect id="trap" x="180" y="53" width="76" height="16" rx="4"
        fill="{f('trap')}" stroke="{s('trap')}" stroke-width="{w('trap')}"/>

  <!-- Rear deltoids -->
  <ellipse id="rear_delt_l" cx="178" cy="66" rx="13" ry="10"
           fill="{f('rear_delt_l')}" stroke="{s('rear_delt_l')}" stroke-width="{w('rear_delt_l')}"/>
  <ellipse id="rear_delt_r" cx="258" cy="66" rx="13" ry="10"
           fill="{f('rear_delt_r')}" stroke="{s('rear_delt_r')}" stroke-width="{w('rear_delt_r')}"/>

  <!-- Upper back -->
  <rect id="upper_back" x="186" y="69" width="68" height="22" rx="4"
        fill="{f('upper_back')}" stroke="{s('upper_back')}" stroke-width="{w('upper_back')}"/>

  <!-- Lats -->
  <rect id="lat_l" x="178" y="88" width="20" height="40" rx="5"
        fill="{f('lat_l')}" stroke="{s('lat_l')}" stroke-width="{w('lat_l')}"/>
  <rect id="lat_r" x="238" y="88" width="20" height="40" rx="5"
        fill="{f('lat_r')}" stroke="{s('lat_r')}" stroke-width="{w('lat_r')}"/>

  <!-- Triceps -->
  <rect id="tricep_l" x="165" y="74" width="12" height="34" rx="6"
        fill="{f('tricep_l')}" stroke="{s('tricep_l')}" stroke-width="{w('tricep_l')}"/>
  <rect id="tricep_r" x="259" y="74" width="12" height="34" rx="6"
        fill="{f('tricep_r')}" stroke="{s('tricep_r')}" stroke-width="{w('tricep_r')}"/>

  <!-- Forearms back -->
  <rect x="163" y="108" width="12" height="34" rx="5" fill="{BODY}" stroke="{OUTLINE}" stroke-width="1"/>
  <rect x="261" y="108" width="12" height="34" rx="5" fill="{BODY}" stroke="{OUTLINE}" stroke-width="1"/>

  <!-- Lower back -->
  <rect id="lower_back" x="192" y="112" width="52" height="20" rx="4"
        fill="{f('lower_back')}" stroke="{s('lower_back')}" stroke-width="{w('lower_back')}"/>

  <!-- Glutes -->
  <rect id="glute_l" x="186" y="132" width="24" height="30" rx="8"
        fill="{f('glute_l')}" stroke="{s('glute_l')}" stroke-width="{w('glute_l')}"/>
  <rect id="glute_r" x="226" y="132" width="24" height="30" rx="8"
        fill="{f('glute_r')}" stroke="{s('glute_r')}" stroke-width="{w('glute_r')}"/>

  <!-- Hamstrings -->
  <rect id="ham_l" x="186" y="162" width="24" height="52" rx="8"
        fill="{f('ham_l')}" stroke="{s('ham_l')}" stroke-width="{w('ham_l')}"/>
  <rect id="ham_r" x="226" y="162" width="24" height="52" rx="8"
        fill="{f('ham_r')}" stroke="{s('ham_r')}" stroke-width="{w('ham_r')}"/>

  <!-- Calves -->
  <rect id="calf_l" x="186" y="214" width="24" height="57" rx="6"
        fill="{f('calf_l')}" stroke="{s('calf_l')}" stroke-width="{w('calf_l')}"/>
  <rect id="calf_r" x="226" y="214" width="24" height="57" rx="6"
        fill="{f('calf_r')}" stroke="{s('calf_r')}" stroke-width="{w('calf_r')}"/>

</svg>"""
