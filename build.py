#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка публичной страницы «Сплавные ребята» из заметок сплава.

Источник истины — markdown-заметки в родительской папке (01/03/04/05).
Скрипт парсит их и рендерит site/index.html. Правишь заметку → пересобираешь:

    .venv/bin/python "Personal/Сплав 2026/site/build.py"

Зависимостей нет (только стандартная библиотека). Публикуются 5 разделов:
Маршрут (+ карта) · Тайминги · Общее снаряжение · Личные вещи · Меню.
Траты и логистика из/до Москвы НЕ выкладываются (приватные данные).
"""
import html
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent      # .../Сплав 2026/site
NOTES = BASE.parent                          # .../Сплав 2026

# --- Редактируемые факты для hero (собраны из заметок, но разбросаны) ---
CONFIG = {
    "brand": "Сплавные ребята",
    "tagline": "Сплав по Пра · 14–16 августа 2026",
    "dates": "14–16 августа 2026",
    "facts": [
        ("Река", "Пра, Мещера"),
        ("Дистанция", "~43 км"),
        ("Формат", "3 дня / 2 ночи"),
        ("Экипаж", "6 человек"),
    ],
    "intro": "Пятница вечер — воскресенье день. Спокойный ПВД по Мещере "
             "с поправкой на завалы, разрешения нацпарка и уровень воды. "
             "Главная идея: не добивать до Деулино в субботу, а встать "
             "после Горок и в воскресенье спокойно доплыть.",
}


# ----------------------------- утилиты -----------------------------
def read_note(prefix: str) -> str:
    for p in NOTES.glob(f"{prefix} *.md"):
        return p.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Заметка {prefix} не найдена в {NOTES}")


def inline(text: str) -> str:
    """Лёгкий инлайн-markdown: escape → code → ссылки → bold."""
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">{m.group(1)}</a>',
        text,
    )
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def split_sections(text: str, level: int = 2):
    """Разбить на секции по заголовкам данного уровня.
    Возвращает [(heading|None, [строки тела])]; первый элемент — преамбула."""
    marker = "#" * level + " "
    out, head, cur = [], None, []
    for line in text.splitlines():
        if line.startswith(marker):
            out.append((head, cur))
            head, cur = line[len(marker):].strip(), []
        else:
            cur.append(line)
    out.append((head, cur))
    return out


def parse_checklist(lines):
    """Пункты `- [ ] текст #тег` → [(текст, [теги])]."""
    items = []
    for line in lines:
        m = re.match(r"\s*-\s*\[[ xX]?\]\s*(.+)", line)
        if not m:
            continue
        body = m.group(1).strip()
        tags = re.findall(r"#(\S+)", body)
        body = re.sub(r"\s*#\S+", "", body).strip()
        items.append((body, tags))
    return items


def parse_bullets(lines):
    """Простые пункты `- текст` (без чекбоксов) → [текст]."""
    out = []
    for line in lines:
        m = re.match(r"\s*-\s+(.+)", line)
        if m and not re.match(r"\s*-\s*\[", line):
            out.append(m.group(1).strip())
    return out


def parse_ordered(lines):
    out = []
    for line in lines:
        m = re.match(r"\s*\d+\.\s+(.+)", line)
        if m:
            out.append(m.group(1).strip())
    return out


def paragraphs(lines):
    """Собрать непустые не-списочные строки в абзацы (по пустой строке)."""
    paras, buf = [], []
    for line in lines:
        s = line.strip()
        if not s:
            if buf:
                paras.append(" ".join(buf))
                buf = []
        elif re.match(r"\s*[-|>#]", line) or s.startswith("|"):
            if buf:
                paras.append(" ".join(buf))
                buf = []
        else:
            buf.append(s)
    if buf:
        paras.append(" ".join(buf))
    return paras


# --------------------------- маршрут (01) ---------------------------
def marker_style(name: str):
    n = name.lower()
    if "антистапель" in n:
        return "finish", "#d64545", "Антистапель"
    if "стапель" in n or "кемпинг" in n:
        return "start", "#2f9e44", "Стапель"
    if "гидропост" in n:
        return "gauge", "#1c7ed6", "Гидропост"
    if "горки" in n:
        return "village", "#e8590c", "Деревня"
    if "лагерь" in n:
        return "camp1", "#7048e8", "Проверенная ночёвка"
    return "camp", "#868e96", "Стоянка"


def parse_route(text):
    sections = {h: b for h, b in split_sections(text) if h}

    # опорные точки
    points = []
    for line in sections.get("Опорные точки", []):
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or "Координаты" in cells[1] or set(cells[1]) <= set("-: "):
            continue
        coord = cells[1].strip("` ")
        m = re.match(r"(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)", coord)
        if not m:
            continue
        cat, color, label = marker_style(cells[0])
        points.append({
            "name": cells[0], "lat": float(m.group(1)), "lon": float(m.group(2)),
            "purpose": cells[2], "cat": cat, "color": color, "label": label,
        })

    # краткий план по дням
    plan = []
    day = None
    for line in sections.get("Краткий план", []):
        top = re.match(r"-\s+(\S.+)", line)
        sub = re.match(r"\s+-\s+(\S.+)", line)
        if top and not line.startswith(" "):
            day = {"day": top.group(1).strip(), "rows": []}
            plan.append(day)
        elif sub and day is not None:
            txt = sub.group(1).strip()
            if ":" in txt:
                k, v = txt.split(":", 1)
                day["rows"].append((k.strip(), v.strip()))
            else:
                day["rows"].append(("", txt))

    # детальные тайминги по дням
    days = []
    for name in ("Пятница", "Суббота", "Воскресенье"):
        body = sections.get(name)
        if not body:
            continue
        desc, timeline, seen_timing = [], [], False
        for line in body:
            if "Черновой тайминг" in line:
                seen_timing = True
                continue
            if not seen_timing:
                s = line.strip()
                if s and not s.startswith("-"):
                    desc.append(s)
            else:
                m = re.match(r"-\s*([0-9:–\-]+)\s*-\s*(.+)", line)
                if m:
                    timeline.append((m.group(1).strip(), m.group(2).strip()))
        days.append({"day": name, "desc": " ".join(desc), "timeline": timeline})

    # ссылки
    links = []
    for line in sections.get("Ссылки", []):
        m = re.match(r"\s*-\s*\[([^\]]+)\]\(([^)]+)\)", line)
        if m:
            links.append((m.group(1), m.group(2)))

    return {"points": points, "plan": plan, "days": days, "links": links}


# ------------------------ снаряжение / вещи ------------------------
def parse_gear(text, skip_intro=False):
    intro = []
    result = []
    for head, body in split_sections(text):
        if head is None:
            if not skip_intro:
                intro = paragraphs([ln for ln in body if not ln.startswith("#")])
            continue
        items = parse_checklist(body)
        if items:
            result.append({"title": head, "items": items})
    return {"intro": intro, "sections": result}


# ----------------------------- меню (05) -----------------------------
def parse_menu(text):
    top = {h: b for h, b in split_sections(text)}
    # преамбула
    pre = top.get(None, [])
    intro = paragraphs([ln for ln in pre if not ln.startswith("#") and "Вводные" not in ln])
    vvod = parse_bullets(pre)

    meals = []
    for h, b in split_sections("\n".join(top.get("Меню по приемам пищи", [])), level=3):
        if h:
            meals.append({"title": h, "items": parse_bullets(b)})

    shopping = []
    for h, b in split_sections("\n".join(top.get("Закупка", [])), level=3):
        if h:
            shopping.append({"title": h, "items": parse_checklist(b)})

    recipes = []
    for h, b in split_sections("\n".join(top.get("Рецепты", [])), level=3):
        if h:
            recipes.append({"title": h, "steps": parse_ordered(b)})

    return {"intro": intro, "vvod": vvod, "meals": meals,
            "shopping": shopping, "recipes": recipes}


# ------------------------------ рендер ------------------------------
def tag_badge(tag):
    t = tag.lower()
    if t == "купить":
        return '<span class="tag tag-buy">купить</span>'
    return f'<span class="tag tag-who">{html.escape(tag)}</span>'


def checklist_html(items, key_prefix):
    rows = []
    for i, (text, tags) in enumerate(items):
        key = f"{key_prefix}-{i}"
        badges = "".join(tag_badge(t) for t in tags)
        rows.append(
            f'<li><label><input type="checkbox" data-key="{key}">'
            f'<span class="ci-text">{inline(text)}</span>{badges}</label></li>'
        )
    return (
        f'<ul class="checklist" data-list="{key_prefix}">'
        f'<li class="ci-progress" data-progress="{key_prefix}"></li>'
        + "".join(rows) + "</ul>"
    )


def render(route, gear, personal, menu):
    F = CONFIG
    # hero facts
    facts = "".join(
        f'<div class="fact"><span class="fact-k">{html.escape(k)}</span>'
        f'<span class="fact-v">{html.escape(v)}</span></div>'
        for k, v in F["facts"]
    )

    # --- Маршрут ---
    plan_cards = []
    for d in route["plan"]:
        rows = "".join(
            f'<div class="plan-row"><span class="pk">{html.escape(k)}</span>'
            f'<span class="pv">{inline(v)}</span></div>' if k else
            f'<div class="plan-row"><span class="pv">{inline(v)}</span></div>'
            for k, v in d["rows"]
        )
        plan_cards.append(
            f'<div class="card plan-card"><h3>{html.escape(d["day"])}</h3>{rows}</div>'
        )

    pts_rows = "".join(
        f'<tr><td><span class="dot" style="background:{p["color"]}"></span>{html.escape(p["name"])}</td>'
        f'<td class="mono"><a href="https://yandex.ru/maps/?pt={p["lon"]},{p["lat"]}&z=15&l=sat" '
        f'target="_blank" rel="noopener">{p["lat"]}, {p["lon"]}</a></td>'
        f'<td>{html.escape(p["purpose"])}</td></tr>'
        for p in route["points"]
    )

    links = "".join(
        f'<li><a href="{u}" target="_blank" rel="noopener">{html.escape(t)}</a></li>'
        for t, u in route["links"]
    )

    # легенда карты (уникальные категории)
    seen, legend = set(), []
    for p in route["points"]:
        if p["label"] not in seen:
            seen.add(p["label"])
            legend.append(
                f'<span class="leg"><span class="dot" style="background:{p["color"]}"></span>'
                f'{html.escape(p["label"])}</span>'
            )

    # --- Тайминги ---
    timing_cards = []
    for d in route["days"]:
        tl = "".join(
            f'<li><span class="t-time">{html.escape(t)}</span>'
            f'<span class="t-desc">{inline(desc)}</span></li>'
            for t, desc in d["timeline"]
        )
        desc = f'<p class="muted">{inline(d["desc"])}</p>' if d["desc"] else ""
        timing_cards.append(
            f'<div class="card"><h3>{html.escape(d["day"])}</h3>{desc}'
            f'<ol class="timeline">{tl}</ol></div>'
        )

    # --- Снаряжение ---
    gear_cards = "".join(
        f'<div class="card"><h3>{html.escape(s["title"])}</h3>'
        f'{checklist_html(s["items"], "gear-" + str(i))}</div>'
        for i, s in enumerate(gear["sections"])
    )
    gear_intro = "".join(f"<p>{inline(p)}</p>" for p in gear["intro"])

    # --- Личные вещи ---
    pers_cards = "".join(
        f'<div class="card"><h3>{html.escape(s["title"])}</h3>'
        f'{checklist_html(s["items"], "pers-" + str(i))}</div>'
        for i, s in enumerate(personal["sections"])
    )
    pers_intro = "".join(f"<p>{inline(p)}</p>" for p in personal["intro"])

    # --- Меню ---
    meal_cards = "".join(
        f'<div class="card"><h3>{html.escape(m["title"])}</h3>'
        f'<ul class="dish">{"".join(f"<li>{inline(x)}</li>" for x in m["items"])}</ul></div>'
        for m in menu["meals"]
    )
    shop_cards = "".join(
        f'<div class="card"><h4>{html.escape(s["title"])}</h4>'
        f'{checklist_html(s["items"], "shop-" + str(i))}</div>'
        for i, s in enumerate(menu["shopping"])
    )
    recipe_cards = "".join(
        f'<details class="recipe"><summary>{html.escape(r["title"])}</summary>'
        f'<ol>{"".join(f"<li>{inline(x)}</li>" for x in r["steps"])}</ol></details>'
        for r in menu["recipes"]
    )
    menu_intro = "".join(f"<p>{inline(p)}</p>" for p in menu["intro"])
    vvod = ("<ul class='note-list'>"
            + "".join(f"<li>{inline(x)}</li>" for x in menu["vvod"]) + "</ul>") if menu["vvod"] else ""

    points_json = json.dumps(route["points"], ensure_ascii=False)

    return TEMPLATE.format(
        brand=html.escape(F["brand"]),
        tagline=html.escape(F["tagline"]),
        dates=html.escape(F["dates"]),
        intro=html.escape(F["intro"]),
        facts=facts,
        plan_cards="".join(plan_cards),
        legend="".join(legend),
        pts_rows=pts_rows,
        links=links,
        timing_cards="".join(timing_cards),
        gear_intro=gear_intro,
        gear_cards=gear_cards,
        pers_intro=pers_intro,
        pers_cards=pers_cards,
        menu_intro=menu_intro,
        vvod=vvod,
        meal_cards=meal_cards,
        shop_cards=shop_cards,
        recipe_cards=recipe_cards,
        points_json=points_json,
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{brand} — {dates}</title>
<meta name="description" content="{tagline}">
<link rel="icon" href="assets/emblem.png">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
<link rel="stylesheet" href="assets/styles.css">
</head>
<body>
<header class="hero">
  <img class="emblem" src="assets/emblem.png" alt="Сплавные ребята">
  <h1>{brand}</h1>
  <p class="tagline">{tagline}</p>
  <div class="facts">{facts}</div>
  <p class="hero-intro">{intro}</p>
</header>

<nav class="nav" id="nav">
  <a href="#marshrut">Маршрут</a>
  <a href="#timing">Тайминги</a>
  <a href="#snar">Снаряжение</a>
  <a href="#veshi">Личные вещи</a>
  <a href="#menu">Меню</a>
</nav>

<main>
  <section id="marshrut">
    <h2>Нитка маршрута</h2>
    <p class="muted">Заводская Слобода → Кордон 273 → Горки → Лесохим → Деулино.</p>
    <div class="grid">{plan_cards}</div>

    <h3 class="sub">Карта опорных точек</h3>
    <div id="map"></div>
    <div class="legend">{legend}</div>

    <details class="table-wrap">
      <summary>Таблица опорных точек с координатами</summary>
      <table class="points">
        <thead><tr><th>Точка</th><th>Координаты</th><th>Зачем</th></tr></thead>
        <tbody>{pts_rows}</tbody>
      </table>
    </details>

    <h3 class="sub">Лоции и источники</h3>
    <ul class="links">{links}</ul>
  </section>

  <section id="timing">
    <h2>Примерные тайминги</h2>
    <p class="muted">Черновой план по дням — ориентир, а не расписание поезда.</p>
    <div class="grid">{timing_cards}</div>
  </section>

  <section id="snar">
    <h2>Общее снаряжение</h2>
    {gear_intro}
    <p class="muted">Галочки сохраняются в этом браузере — отмечай, что уже собрано.</p>
    <div class="grid">{gear_cards}</div>
  </section>

  <section id="veshi">
    <h2>Личные вещи</h2>
    {pers_intro}
    <div class="grid">{pers_cards}</div>
  </section>

  <section id="menu">
    <h2>Меню</h2>
    {menu_intro}
    {vvod}
    <h3 class="sub">По приёмам пищи</h3>
    <div class="grid">{meal_cards}</div>
    <h3 class="sub">Закупка</h3>
    <div class="grid">{shop_cards}</div>
    <h3 class="sub">Рецепты</h3>
    <div class="recipes">{recipe_cards}</div>
  </section>
</main>

<footer>
  <p>Сплавные ребята · {dates} · собрано из заметок, не является офертой на энтузиазм.</p>
</footer>

<script>window.ROUTE_POINTS = {points_json};</script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script src="assets/route.js"></script>
<script src="assets/checklist.js"></script>
</body>
</html>
"""


def main():
    route = parse_route(read_note("01"))
    gear = parse_gear(read_note("03"))
    personal = parse_gear(read_note("04"))
    menu = parse_menu(read_note("05"))
    out = render(route, gear, personal, menu)
    (BASE / "index.html").write_text(out, encoding="utf-8")
    print(f"Готово: {BASE / 'index.html'}")
    print(f"  точек на карте: {len(route['points'])}")
    print(f"  секций снаряжения: {len(gear['sections'])}, личных вещей: {len(personal['sections'])}")
    print(f"  приёмов пищи: {len(menu['meals'])}, рецептов: {len(menu['recipes'])}")


if __name__ == "__main__":
    main()
