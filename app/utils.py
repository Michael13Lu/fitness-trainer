import datetime as _dt


def calc_realistic_date(current_weight: float, target_weight: float) -> _dt.date | None:
    """Возвращает реалистичную дату цели (~0.5 кг/нед для похудения, 0.3 для набора)."""
    if not target_weight or target_weight <= 0:
        return None
    kg_diff = abs(current_weight - target_weight)
    rate = 0.5 if current_weight > target_weight else 0.3
    weeks = kg_diff / rate
    return _dt.date.today() + _dt.timedelta(weeks=weeks)


def calc_tdee(weight_kg: float, height_cm: float, age_yr: int,
              goal_idx: int, level_idx: int) -> int:
    """Суточная норма калорий (Mifflin-St Jeor + коэффициент активности)."""
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age_yr + 5
    activity = [1.375, 1.55, 1.725][min(level_idx, 2)]
    tdee = bmr * activity
    adj = [-300, 300, 0, -100][min(goal_idx, 3)]
    return int(tdee + adj)
