// Приёмка по критериям ТЗ. Ключ строил генератор, модуль его не видит.
const fs = require("fs");
const R = require("./registry.js");
const key = JSON.parse(fs.readFileSync("data/answer_key.json", "utf8"));
const D = new Date(Date.UTC(2026, 9, 30));
const files = ["sales", "production", "montage", "crm"];
const bytes = Object.fromEntries(files.map(f => [f, new Uint8Array(fs.readFileSync(`data/${f}.csv`))]));

let fails = 0;
const check = (ac, ok, detail = "") => { console.log(`${ok ? "PASS" : "FAIL"}  ${ac}${detail ? "  " + detail : ""}`); if (!ok) fails++; };

// AC1
const loaded = {};
for (const f of files) { const s = R.readSource(f, bytes[f]); if (s.error) console.log(s.error); else loaded[f] = s; }
check("AC1 все 4 файла читаются", Object.keys(loaded).length === 4,
  files.map(f => `${f}:${loaded[f] ? loaded[f].encoding + " «" + loaded[f].delim + "»" : "ошибка"}`).join(", "));
const res = R.build(loaded, D);
const got = Object.fromEntries(res.orders.map(o => [o.key, o]));

// AC2
const expKeys = Object.keys(key.orders).sort(), gotKeys = Object.keys(got).sort();
check("AC2 число заказов", expKeys.length === gotKeys.length, `ожидали ${expKeys.length}, получили ${gotKeys.length}` +
  (expKeys.join() !== gotKeys.join() ? `; лишние: ${gotKeys.filter(k => !key.orders[k])}; потеряны: ${expKeys.filter(k => !got[k])}` : ""));

const diff = (field, pick) => expKeys.filter(k => got[k] && pick(got[k]) !== key.orders[k][field])
  .map(k => `${k}: ждали ${key.orders[k][field]}, есть ${pick(got[k])}`);
// AC3, AC4
let d = diff("stage", o => o.stage); check("AC3 этапы", !d.length, d.join("; "));
d = diff("overdue_days", o => o.overdueDays); check("AC4 дни просрочки", !d.length, d.join("; "));
// AC5
d = expKeys.filter(k => got[k] && got[k].flags.includes("нет в CRM") !== key.orders[k].flags.includes("нет в CRM"));
check("AC5 флаг «нет в CRM»", !d.length, d.join(", "));
// AC6
const sig = u => `${u.file}#${u.row}:${u.reason}`;
const expU = key.unmatched.map(sig).sort(), gotU = res.review.map(sig).sort();
check("AC6 строки на проверку", expU.join() === gotU.join(), `ждали [${expU}], есть [${gotU}]`);
// AC7
const rc = files.map(f => {
  const e = key.reconciliation[f], g = res.recon[f];
  const same = ["total", "attached", "unmatched", "leads", "empty"].every(x => e[x] === g[x]);
  return { f, ok: same && g.balanced, s: `${f} ${g.total}=${g.attached}+${g.unmatched}+${g.leads}+${g.leads === undefined ? "" : g.empty}` };
});
check("AC7 сверка строк", rc.every(x => x.ok), rc.map(x => (x.ok ? "" : "✗ ") + x.s).join(" | "));
// AC8
const undef = expKeys.filter(k => key.orders[k].stage === "Не определён");
check("AC8 незнакомый статус", undef.every(k => got[k] && got[k].stage === "Не определён" && got[k].flags.includes("неизвестный статус")),
  `Не определён: ${undef.map(k => k + "→" + (got[k] && got[k].stage))}`);
// AC9: файл монтажа в слоте продаж
const wrong = R.readSource("sales", bytes.montage);
check("AC9 чужой файл отклонён", !!wrong.error, wrong.error || "ошибки нет");
// AC10
check("AC10 лиды не стали заказами", res.recon.crm.leads === 4 && !res.review.some(u => u.file === "crm"),
  `лидов: ${res.recon.crm.leads}`);
// AC11
check("AC11 общий телефон не склеен", res.review.some(u => u.reason === "phone_ambiguous"));
// AC12
const bad = [];
for (const k of expKeys) {
  if (!got[k]) continue;
  for (const fl of key.checked_flags) {
    const e = key.orders[k].flags.includes(fl), g = got[k].flags.includes(fl);
    if (e !== g) bad.push(`${k} «${fl}» ждали ${e ? "есть" : "нет"}`);
  }
}
check("AC12 засеянные флаги", !bad.length, bad.join("; "));
// R10: ответственный
d = diff("responsible", o => o.responsible); check("R10 ответственный", !d.length, d.join("; "));

// AC13: без CRM флаг «нет в CRM» не ставится
const noCrm = R.build({ sales: loaded.sales, production: loaded.production, montage: loaded.montage }, D);
check("AC13 частичная загрузка", !noCrm.orders.some(o => o.flags.includes("нет в CRM")) && noCrm.orders.length === 41,
  `заказов без CRM: ${noCrm.orders.length} (41: минус заказ, который есть только в CRM)`);

// НФТ: 2 000 строк на файл
const big = {};
for (const f of files) {
  const s = loaded[f]; const rows = [];
  for (let i = 0; rows.length < 2000; i++) for (const r of s.rows) {
    if (rows.length >= 2000) break;
    const c = { ...r, _row: rows.length + 1 };
    if (c["договор"]) c["договор"] = c["договор"].replace(/\d+$/, m => String(+m + 1000 * (i + 1)));
    rows.push(c);
  }
  big[f] = { rows, encoding: s.encoding };
}
const t0 = process.hrtime.bigint(); R.build(big, D); const ms = Number(process.hrtime.bigint() - t0) / 1e6;
check("НФТ 2 000 строк × 4 файла", ms < 2000, `${ms.toFixed(0)} мс на сборку (без отрисовки, Node)`);

console.log(fails ? `\nНЕ ПРОШЛО: ${fails}` : "\nВСЁ ПРОШЛО");
process.exit(fails ? 1 : 0);
