// Сводный реестр заказов. Чистые функции без DOM: один и тот же файл
// гоняется тестом в Node и встраивается в страницу при сборке.
(function (root) {
  "use strict";

  const STAGES = ["Договор", "Замер", "Проект", "Производство", "Готов к монтажу", "Монтаж", "Закрыт"];
  const SI = Object.fromEntries(STAGES.map((s, i) => [s, i]));
  const PLANNED = "__planned__", LEAD = "__lead__";

  const SOURCES = {
    sales: { title: "Продажи", required: ["договор", "клиент", "телефон", "канал", "менеджер", "срок_по_договору", "статус"],
      status: { "договор": "Договор", "новый договор": "Договор", "замер": "Замер", "замер назначен": "Замер",
        "проект": "Проект", "на согласовании проекта": "Проект", "в производстве": "Производство",
        "ждет монтажа": "Готов к монтажу", "монтаж": "Монтаж", "сдан": "Закрыт", "закрыт": "Закрыт",
        "рекламация": "Рекламация" } },
    production: { title: "Производство", required: ["договор", "клиент", "телефон", "статус"],
      status: { "в очереди": "Производство", "раскрой": "Производство", "в цеху": "Производство",
        "в работе": "Производство", "готово": "Готов к монтажу", "отгружено": "Готов к монтажу" } },
    montage: { title: "Монтаж", required: ["договор", "клиент", "телефон", "дата_монтажа_факт", "бригада", "статус"],
      status: { "назначен": PLANNED, "в процессе": "Монтаж", "сдан": "Закрыт", "смонтирован": "Закрыт",
        "рекламация устранена": "Закрыт", "рекламация": "Рекламация" } },
    crm: { title: "CRM", required: ["договор", "клиент", "телефон", "этап", "срок"], statusCol: "этап",
      status: { "лид": LEAD, "консультация": LEAD, "договор подписан": "Договор", "замер": "Замер",
        "дизайн-проект": "Проект", "производство": "Производство", "монтаж": "Монтаж",
        "успешно закрыта": "Закрыт" } },
  };

  // ---------- чтение файла ----------
  function decodeBytes(bytes) {
    let b = bytes;
    if (b.length >= 3 && b[0] === 0xEF && b[1] === 0xBB && b[2] === 0xBF) b = b.subarray(3);
    try { return { text: new TextDecoder("utf-8", { fatal: true }).decode(b), encoding: "UTF-8" }; }
    catch (e) { return { text: new TextDecoder("windows-1251").decode(b), encoding: "Windows-1251" }; }
  }

  function detectDelimiter(text) {
    const first = text.split(/\r?\n/, 1)[0];
    let semi = 0, comma = 0, q = false;
    for (const ch of first) { if (ch === '"') q = !q; else if (!q && ch === ";") semi++; else if (!q && ch === ",") comma++; }
    return semi > comma ? ";" : ",";
  }

  function parseCSV(text, delim) {
    const rows = []; let row = [], cell = "", q = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (q) {
        if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; }
        else cell += ch;
      } else if (ch === '"') q = true;
      else if (ch === delim) { row.push(cell); cell = ""; }
      else if (ch === "\n") { row.push(cell); rows.push(row); row = []; cell = ""; }
      else if (ch !== "\r") cell += ch;
    }
    if (cell !== "" || row.length) { row.push(cell); rows.push(row); }
    return rows;
  }

  const normHeader = h => h.toLowerCase().replace(/ё/g, "е").replace(/[^a-zа-я0-9 ]/g, " ").trim().replace(/\s+/g, "_");
  const normStatus = s => (s || "").toLowerCase().replace(/ё/g, "е").trim().replace(/\s+/g, " ");

  function readSource(name, bytes) {
    const { text, encoding } = decodeBytes(bytes);
    const delim = detectDelimiter(text);
    const table = parseCSV(text, delim);
    const header = (table[0] || []).map(normHeader);
    const missing = SOURCES[name].required.filter(c => !header.includes(c));
    if (missing.length) return { error: `Файл «${SOURCES[name].title}»: нет колонок ${missing.join(", ")}. Проверьте, что файл загружен в свой слот.` };
    const rows = table.slice(1).map((cells, i) => {
      const r = { _row: i + 1, _source: name, _raw: cells };
      header.forEach((h, j) => { r[h] = (cells[j] || "").trim(); });
      return r;
    });
    return { rows, encoding, delim };
  }

  // ---------- нормализация значений ----------
  function normContract(s) {
    const g = (s || "").match(/\d+/g);
    if (!g || g.length < 2 || !/^20\d\d$/.test(g[0])) return null;
    return `${g[0]}-${parseInt(g[1], 10)}`;
  }
  function normPhone(s) {
    const d = (s || "").replace(/\D/g, "");
    return d.length >= 10 ? d.slice(-10) : null;
  }
  function parseDate(s) {
    const t = (s || "").trim();
    if (!t) return { value: null, bad: false };
    let m, y, mo, d;
    if ((m = t.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/))) [d, mo, y] = [+m[1], +m[2], +m[3]];
    else if ((m = t.match(/^(\d{1,2})\.(\d{1,2})\.(\d{2})$/))) [d, mo, y] = [+m[1], +m[2], 2000 + +m[3]];
    else if ((m = t.match(/^(\d{4})-(\d{2})-(\d{2})$/))) [y, mo, d] = [+m[1], +m[2], +m[3]];
    else return { value: null, bad: true };
    const dt = new Date(Date.UTC(y, mo - 1, d));
    if (dt.getUTCMonth() !== mo - 1 || dt.getUTCDate() !== d) return { value: null, bad: true };
    return { value: dt, bad: false };
  }
  const dayDiff = (a, b) => Math.round((a - b) / 86400000);
  const isEmptyRow = r => r._raw.every(c => !c.trim());

  // ---------- сборка реестра ----------
  function build(loaded, reportDate) {
    const orders = new Map(), review = [], recon = {}, keyless = [];
    const bucket = new Map();
    const getOrder = k => {
      if (!orders.has(k)) orders.set(k, { key: k, rows: [] });
      return orders.get(k);
    };

    for (const [name, src] of Object.entries(loaded)) {
      recon[name] = { total: src.rows.length, attached: 0, unmatched: 0, leads: 0, empty: 0, encoding: src.encoding };
      const stCol = SOURCES[name].statusCol || "статус";
      for (const r of src.rows) {
        if (isEmptyRow(r)) { bucket.set(r, "empty"); continue; }
        r._claim = SOURCES[name].status[normStatus(r[stCol])];
        if (r._claim === LEAD) { bucket.set(r, "leads"); continue; }
        const k = normContract(r["договор"]);
        if (k) { getOrder(k).rows.push(r); bucket.set(r, "attached"); }
        else keyless.push(r);
      }
    }

    // Запасной ключ: телефон, но только если он принадлежит ровно одному заказу
    const phoneIdx = new Map();
    for (const o of orders.values()) for (const r of o.rows) {
      const p = normPhone(r["телефон"]);
      if (p) { if (!phoneIdx.has(p)) phoneIdx.set(p, new Set()); phoneIdx.get(p).add(o.key); }
    }
    for (const r of keyless) {
      const p = normPhone(r["телефон"]);
      const hit = p && phoneIdx.get(p);
      let reason = null;
      if (!p) reason = "no_key";
      else if (!hit) reason = "not_found";
      else if (hit.size > 1) reason = "phone_ambiguous";
      if (reason) { review.push({ file: r._source, row: r._row, reason, raw: r._raw }); bucket.set(r, "unmatched"); }
      else { orders.get([...hit][0]).rows.push(r); bucket.set(r, "attached"); }
    }
    for (const [r, b] of bucket) recon[r._source][b]++;

    const result = [];
    for (const o of orders.values()) result.push(evaluate(o, reportDate, loaded));
    result.sort((a, b) => (b.overdueDays || 0) - (a.overdueDays || 0) || a.key.localeCompare(b.key));
    for (const name in recon) {
      const c = recon[name];
      c.balanced = c.total === c.attached + c.unmatched + c.leads + c.empty;
    }
    return { orders: result, review, recon };
  }

  function evaluate(o, D, loaded) {
    const by = s => o.rows.filter(r => r._source === s);
    const sales = by("sales"), crm = by("crm"), mont = by("montage");
    const flags = new Set();
    // этап
    let stage = null, complaint = false;
    for (const r of o.rows) {
      if (r._claim === undefined) { flags.add("неизвестный статус"); continue; }
      if (r._claim === PLANNED) continue;
      if (r._claim === "Рекламация") { complaint = true; continue; }
      if (stage === null || SI[r._claim] > SI[stage]) stage = r._claim;
    }
    if (complaint) stage = "Рекламация";
    if (stage === null) stage = "Не определён";
    // срок
    const salesDl = [];
    for (const r of sales) { const p = parseDate(r["срок_по_договору"]); if (p.bad) flags.add("дата не распознана"); if (p.value) salesDl.push(p.value); }
    const crmDl = [];
    for (const r of crm) { const p = parseDate(r["срок"]); if (p.bad) flags.add("дата не распознана"); if (p.value) crmDl.push(p.value); }
    const uniq = a => [...new Set(a.map(d => +d))].map(t => new Date(t));
    let deadline = null;
    if (salesDl.length) {
      const u = uniq(salesDl);
      if (u.length > 1) flags.add("дубль с расхождением");
      deadline = new Date(Math.min(...u));
      if (crmDl.length && uniq(crmDl).some(d => !u.some(x => +x === +d))) flags.add("срок расходится");
    } else if (crmDl.length) deadline = new Date(Math.min(...crmDl));
    if (!deadline) flags.add("нет срока");
    // факт монтажа
    let fact = null;
    for (const r of mont) { const p = parseDate(r["дата_монтажа_факт"]); if (p.bad) flags.add("дата не распознана"); if (p.value && (!fact || p.value > fact)) fact = p.value; }
    // просрочка
    let overdueDays = deadline ? 0 : null;
    if (deadline) {
      if (stage === "Закрыт" || stage === "Рекламация") { if (fact && fact > deadline) flags.add("закрыт с опозданием"); }
      else if (D > deadline) overdueDays = dayDiff(D, deadline);
    }
    if (loaded.sales && !sales.length) flags.add("нет в таблице продаж");
    if (loaded.crm && !crm.length) flags.add("нет в CRM");
    const first = (rows, col) => (rows.find(r => r[col]) || {})[col] || "";
    const manager = first(sales, "менеджер"), brigade = first(mont, "бригада");
    let responsible = "—";
    if (["Договор", "Замер", "Проект", "Не определён"].includes(stage)) responsible = manager || "менеджер не указан";
    else if (stage === "Производство" || stage === "Готов к монтажу") responsible = "цех";
    else if (stage === "Монтаж" || stage === "Рекламация") responsible = brigade || "бригада не назначена";
    return {
      key: o.key, contract: first(sales, "договор") || first(o.rows, "договор"),
      client: first(sales, "клиент") || first(o.rows, "клиент"), channel: first(sales, "канал") || "—",
      stage, responsible, deadline, fact, overdueDays, flags: [...flags].sort(), sources: [...new Set(o.rows.map(r => r._source))],
    };
  }

  const api = { STAGES, SOURCES, readSource, build, decodeBytes, parseCSV, normContract, normPhone, parseDate };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.Registry = api;
})(typeof window !== "undefined" ? window : globalThis);
