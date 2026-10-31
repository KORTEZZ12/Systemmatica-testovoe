"""Синтетические таблицы фабрики кухонь с заранее известными дефектами.

Сначала создаются «истинные» заказы, из них считается ключ ответов,
и только потом заказы превращаются в грязные выгрузки. Код инструмента
этот файл не импортирует и ключ не видит.
"""
import csv, io, json, random
from datetime import date, timedelta

random.seed(42)
D = date(2026, 10, 30)  # дата отчёта
OUT = "data"

STAGES = ["Договор", "Замер", "Проект", "Производство", "Готов к монтажу", "Монтаж", "Закрыт"]
SI = {s: i for i, s in enumerate(STAGES)}

SURN = ["Иванов", "Смирнова", "Кузнецов", "Попова", "Васильев", "Петрова", "Соколов", "Михайлова",
        "Новиков", "Фёдорова", "Морозов", "Волкова", "Алексеев", "Лебедева", "Семёнов", "Егорова",
        "Павлов", "Козлова", "Степанов", "Николаева", "Орлов", "Андреева", "Макаров", "Захарова",
        "Зайцев", "Соловьёва", "Борисов", "Яковлева", "Григорьев", "Романова", "Воробьёв", "Сергеева",
        "Кузьмин", "Фролова", "Александров", "Дмитриева", "Королёв", "Гусева", "Киселёв", "Ильина",
        "Тарасов", "Белова"]
STREETS = ["ул. Садовая", "ул. Лесная", "пр. Победы", "ул. Школьная", "ул. Мира", "ул. Заречная", "ул. Полевая"]
CHANNELS = ["Шоурум 1", "Шоурум 2", "Шоурум 3", "Дилер 1", "Дилер 2", "Дилер 3", "Дилер 4", "Дилер 5"]
MANAGERS = ["Анна К.", "Олег Р.", "Дина С.", "Марат Г.", "Ирина Л."]
BRIGADES = ["Бригада 1", "Бригада 2", "Бригада 3"]

# Сколько заказов на каком истинном этапе (номера 101..140)
plan = (["Договор"] * 3 + ["Замер"] * 4 + ["Проект"] * 5 + ["Производство"] * 9 +
        ["Готов к монтажу"] * 5 + ["Монтаж"] * 3 + ["Закрыт"] * 9 + ["Рекламация"] * 2)
assert len(plan) == 40
random.shuffle(plan)

used_phones = set()
def phone10():
    while True:
        p = "9" + "".join(random.choice("0123456789") for _ in range(9))
        if p not in used_phones:
            used_phones.add(p); return p

orders = []
for i, st in enumerate(plan):
    n = 101 + i
    depth = 6 if st == "Рекламация" else SI[st]
    cdate = D - timedelta(days=8 + depth * 11 + random.randint(0, 12))
    deadline = cdate + timedelta(days=random.randint(45, 60))
    o = dict(n=n, stage=st, client=f"{SURN[i]} {random.choice('АВГДЕИКМНОС')}.",
             phone=phone10(), address=f"{random.choice(STREETS)}, {random.randint(1, 90)}-{random.randint(1, 200)}",
             channel=random.choice(CHANNELS), manager=random.choice(MANAGERS),
             cdate=cdate, deadline=deadline, brigade=None, fact=None, in_crm=random.random() < 0.55,
             seeds=set())
    if st in ("Монтаж", "Закрыт", "Рекламация"):
        o["brigade"] = random.choice(BRIGADES)
    if st in ("Закрыт", "Рекламация"):
        o["fact"] = min(deadline + timedelta(days=random.randint(-10, 12)), D - timedelta(days=2))
    orders.append(o)
by_n = {o["n"]: o for o in orders}

def pick(stage_names, exclude=()):
    for o in orders:
        if o["stage"] in stage_names and o["n"] not in exclude and not o["seeds"]:
            return o
    raise RuntimeError(stage_names)

# ---------- засеянные дефекты ----------
repeat_a = pick(["Проект"]); repeat_a["seeds"].add("repeat_client")
repeat_b = pick(["Производство"]); repeat_b["seeds"].add("repeat_client")
repeat_b["phone"] = repeat_a["phone"]; repeat_b["client"] = repeat_a["client"]  # один клиент, две кухни

undefined_o = pick(["Замер"]); undefined_o["seeds"].add("only_unknown"); undefined_o["in_crm"] = False
pause_o = pick(["Производство"]); pause_o["seeds"].add("unknown_in_production")
crm_mismatch = pick(["Проект"]); crm_mismatch["seeds"].add("srok_mismatch"); crm_mismatch["in_crm"] = True
dup_o = pick(["Замер"]); dup_o["seeds"].add("dup_conflict")
bad_date = pick(["Договор"]); bad_date["seeds"].add("date_unparsed"); bad_date["in_crm"] = False
noyear_1 = pick(["Производство"]); noyear_1["seeds"].add("prod_noyear")
noyear_2 = pick(["Готов к монтажу"]); noyear_2["seeds"].add("prod_noyear")
nocontract_prod = pick(["Производство"]); nocontract_prod["seeds"].add("prod_nocontract")
planned_early = [pick(["Производство"]), None]; planned_early[0]["seeds"].add("montage_planned_early")
planned_early[1] = pick(["Производство"]); planned_early[1]["seeds"].add("montage_planned_early")
crm_nocontract = pick(["Монтаж"]); crm_nocontract["seeds"].add("crm_nocontract"); crm_nocontract["in_crm"] = True
for o in (repeat_a, repeat_b):
    o["in_crm"] = False   # чтобы телефон повторного клиента нигде не служил запасным ключом случайно

# Заказ только в CRM и заказ только в производстве (нет в sales)
crm_only = dict(n=141, stage="Проект", client="Тарасов П.", phone=phone10(), address="ул. Лесная, 3-14",
                channel=None, manager=None, cdate=D - timedelta(days=30), deadline=D + timedelta(days=20),
                brigade=None, fact=None, in_crm=True, seeds={"no_sales", "crm_only"})
prod_only = dict(n=142, stage="Производство", client="Белова Н.", phone=phone10(), address="ул. Мира, 8-2",
                 channel=None, manager=None, cdate=None, deadline=None, brigade=None, fact=None,
                 in_crm=False, seeds={"no_sales", "prod_only"})
orders += [crm_only, prod_only]; by_n[141] = crm_only; by_n[142] = prod_only

# ---------- статусы источников ----------
SALES_ST = {"Договор": "договор", "Замер": "замер назначен", "Проект": "на согласовании проекта",
            "Производство": "в производстве", "Готов к монтажу": "ждёт монтажа", "Монтаж": "монтаж",
            "Закрыт": "сдан", "Рекламация": "рекламация"}
CRM_ST = {"Договор": "Договор подписан", "Замер": "Замер", "Проект": "Дизайн-проект",
          "Производство": "Производство", "Готов к монтажу": "Производство", "Монтаж": "Монтаж",
          "Закрыт": "Успешно закрыта", "Рекламация": "Монтаж"}

def lag(stage, k):
    """Этап на k шагов раньше: таблицы продаж и CRM обновляют с опозданием."""
    idx = SI["Монтаж"] if stage == "Рекламация" else SI[stage]
    return STAGES[max(0, idx - k)]

def fmt_contract_canon(n): return f"К-2026-{n:04d}"
def ph_sales(p): return f"+7 ({p[:3]}) {p[3:6]}-{p[6:8]}-{p[8:]}"
def ph_prod(p): return "8" + p
def ph_mont(p): return f"{p[:3]} {p[3:6]} {p[6:8]} {p[8:]}"
def ph_crm(p): return "+7" + p
def d_sales(d): return d.strftime("%d.%m.%Y") if d else ""
def d_prod(d): return d.strftime("%d.%m.%y") if d else ""
def d_mont(d): return d.isoformat() if d else ""

rows = {"sales": [], "production": [], "montage": [], "crm": []}
expect_unmatched = []

for o in orders:
    st, n = o["stage"], o["n"]
    s = o["seeds"]
    # sales
    if "no_sales" not in s:
        if "only_unknown" in s:
            sst = "ждём клиента"            # незнакомый статус, других источников нет
        elif st in ("Договор", "Замер", "Проект") or "unknown_in_production" in s:
            sst = SALES_ST[st]               # для ранних этапов sales и есть владелец этапа
        else:
            sst = SALES_ST[lag(st, random.randint(1, 3))]
        dl = "конец ноября" if "date_unparsed" in s else d_sales(o["deadline"])
        base = [fmt_contract_canon(n), o["client"], ph_sales(o["phone"]), o["address"], o["channel"],
                o["manager"], d_sales(o["cdate"]), dl, sst]
        rows["sales"].append((n, base))
        if "dup_conflict" in s:
            o["dup_deadline"] = o["deadline"] - timedelta(days=7)
            dup = list(base); dup[7] = d_sales(o["dup_deadline"]); dup[8] = SALES_ST[lag(st, 1)]
            rows["sales"].append((n, dup))
    # production
    idx = 99 if st == "Рекламация" else SI[st]
    if idx >= SI["Производство"]:
        if "unknown_in_production" in s:
            pst = "пауза"
        elif idx >= SI["Готов к монтажу"]:
            pst = random.choice(["готово", "отгружено"])
        else:
            pst = random.choice(["раскрой", "в цеху", "в работе"])
        if "prod_noyear" in s:
            c = str(n)
        elif "prod_nocontract" in s:
            c = ""
        else:
            c = random.choice([f"2026/{n}", f"к2026-{n}", fmt_contract_canon(n), f"2026-{n:04d}"])
        launch = (o["cdate"] + timedelta(days=25)) if o["cdate"] else D - timedelta(days=12)
        ready = (launch + timedelta(days=14)) if idx >= SI["Готов к монтажу"] else None
        rows["production"].append((n, [f"Ц-{3000 + n}", c, o["client"].split()[0], ph_prod(o["phone"]),
                                       d_prod(launch), d_prod(ready), pst]))
    # montage
    mst = None
    if st == "Готов к монтажу": mst = "назначен"
    elif st == "Монтаж": mst = "в процессе"
    elif st == "Закрыт": mst = random.choice(["сдан", "смонтирован"])
    elif st == "Рекламация": mst = "рекламация"
    elif "montage_planned_early" in s: mst = "назначен"
    if mst:
        plan_d = o["fact"] or (D + timedelta(days=random.randint(2, 20)))
        rows["montage"].append((n, [random.choice([fmt_contract_canon(n), f"2026-{n}"]), o["client"],
                                    ph_mont(o["phone"]), o["address"], d_mont(plan_d), d_mont(o["fact"]),
                                    o["brigade"] or "", mst]))
    # crm
    if o["in_crm"]:
        if "crm_only" in s: cst = CRM_ST[st]
        else: cst = CRM_ST[lag(st, random.randint(0, 2))] if st not in ("Договор",) else CRM_ST[st]
        cdl = o["deadline"]
        if "srok_mismatch" in s:
            cdl = o["deadline"] + timedelta(days=14)
        c = "" if "crm_nocontract" in s else fmt_contract_canon(n)
        rows["crm"].append((n, [f"D-{9000 + n}", c, o["client"], ph_crm(o["phone"]), cst, d_sales(cdl)]))

# Строки, которые нельзя сопоставить
rows["montage"].append(("UNMATCHED:no_key", ["", "Григорьева Т.", "", "ул. Полевая, 17-3", "2026-11-05", "",
                                             "Бригада 2", "назначен"]))
rows["montage"].append(("UNMATCHED:phone_ambiguous", ["", repeat_a["client"], ph_mont(repeat_a["phone"]),
                                                       repeat_a["address"], "2026-11-12", "", "", "назначен"]))
rows["production"].append(("UNMATCHED:not_found", ["Ц-3999", "", "Сидоров", ph_prod(phone10()),
                                                   d_prod(D - timedelta(days=3)), "", "в цеху"]))
# Лиды CRM: не заказы. Один лид от уже существующего клиента: не должен ни к чему приклеиться
for k, (nm, ph, st) in enumerate([("Осипов Р.", phone10(), "Лид"), ("Лаптева Е.", phone10(), "Консультация"),
                                  ("Гаврилов Д.", phone10(), "Лид"), (by_n[110]["client"], by_n[110]["phone"], "Консультация")]):
    rows["crm"].append(("LEAD", [f"D-{9900 + k}", "", nm, ph_crm(ph), st, ""]))
# Пустая строка посреди файла производства (так выгружает Excel)
rows["production"].insert(7, ("EMPTY", [""] * 7))

for name in rows:
    if name != "production":
        random.shuffle(rows[name])

# ---------- запись файлов: у каждого свой «характер» ----------
HDR = {"sales": ["Договор", "Клиент", "Телефон", "Адрес", "Канал", "Менеджер", "Дата договора", "Срок по договору", "Статус"],
       "production": ["Номер цеха", "Договор", "Клиент", "Телефон", "Запуск", "Готовность", "Статус"],
       "montage": ["Договор №", "Клиент", "Телефон", "Адрес", "Дата монтажа план", "Дата монтажа факт", "Бригада", "Статус"],
       "crm": ["ID сделки", "Договор", "Клиент", "Телефон", "Этап", "Срок"]}
STYLE = {  # (разделитель, кодировка, перевод строки)
    "sales": (",", "utf-8-sig", "\r\n"),      # Excel «CSV UTF-8»: BOM + CRLF
    "production": (";", "cp1251", "\r\n"),    # русский Excel по умолчанию
    "montage": (",", "utf-8", "\n"),          # Google Sheets, адреса с запятыми в кавычках
    "crm": (",", "utf-8", "\n"),
}
row_map = {}
for name, rs in rows.items():
    delim, enc, eol = STYLE[name]
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=delim, lineterminator=eol)
    w.writerow(HDR[name])
    for _, r in rs: w.writerow(r)
    with open(f"{OUT}/{name}.csv", "wb") as f:
        f.write(buf.getvalue().encode(enc))
    row_map[name] = [tag for tag, _ in rs]

# ---------- ключ ответов из истинных данных ----------
def responsible(o, stage):
    if stage in ("Договор", "Замер", "Проект", "Не определён"):
        return o["manager"] or "менеджер не указан"
    if stage in ("Производство", "Готов к монтажу"): return "цех"
    if stage in ("Монтаж", "Рекламация"): return o["brigade"] or "бригада не назначена"
    return "—"

key_orders = {}
for o in orders:
    s = o["seeds"]
    stage = "Не определён" if "only_unknown" in s else o["stage"]
    if "date_unparsed" in s: dl = None
    elif "dup_conflict" in s: dl = o["dup_deadline"]
    else: dl = o["deadline"]
    overdue = None if dl is None else 0
    closed_late = False
    if dl is not None:
        if stage in ("Закрыт", "Рекламация"):
            closed_late = o["fact"] > dl
        elif D > dl:
            overdue = (D - dl).days
    flags = set()
    if not o["in_crm"]: flags.add("нет в CRM")
    if "no_sales" in s: flags.add("нет в таблице продаж")
    if "srok_mismatch" in s: flags.add("срок расходится")
    if "dup_conflict" in s: flags.add("дубль с расхождением")
    if "date_unparsed" in s: flags.add("дата не распознана")
    if dl is None: flags.add("нет срока")
    if "only_unknown" in s or "unknown_in_production" in s: flags.add("неизвестный статус")
    if closed_late: flags.add("закрыт с опозданием")
    key_orders[f"2026-{o['n']}"] = dict(stage=stage, overdue_days=overdue, flags=sorted(flags),
                                       responsible=responsible(o, stage))

unmatched = []
recon = {}
for name, tags in row_map.items():
    r = dict(total=len(tags), attached=0, unmatched=0, leads=0, empty=0)
    for i, t in enumerate(tags, start=1):
        if isinstance(t, int): r["attached"] += 1
        elif t == "LEAD": r["leads"] += 1
        elif t == "EMPTY": r["empty"] += 1
        else:
            r["unmatched"] += 1
            unmatched.append(dict(file=name, row=i, reason=t.split(":")[1]))
    recon[name] = r

key = dict(report_date=D.isoformat(), orders=key_orders, unmatched=unmatched, reconciliation=recon,
           checked_flags=["нет в таблице продаж", "срок расходится", "дубль с расхождением", "дата не распознана",
                          "нет срока", "неизвестный статус", "закрыт с опозданием", "нет в CRM"])
json.dump(key, open(f"{OUT}/answer_key.json", "w"), ensure_ascii=False, indent=1)
in_work = [k for k, v in key_orders.items() if v["stage"] != "Закрыт"]
od = [k for k in in_work if key_orders[k]["overdue_days"]]
print(f"заказов: {len(key_orders)}, в работе: {len(in_work)}, просрочено: {len(od)}, "
      f"на проверку: {len(unmatched)}, сверка: {recon}")
