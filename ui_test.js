// Дымовой тест интерфейса: открываем собранную страницу, жмём «Демо», считаем то, что видит пользователь
const { JSDOM, VirtualConsole } = require("jsdom");
const fs = require("fs");
const html = fs.readFileSync("/mnt/user-data/outputs/registry.html", "utf8");
const errors = [];
const vc = new VirtualConsole(); vc.on("jsdomError", e => errors.push(e.message)); vc.on("error", e => errors.push(String(e)));
const dom = new JSDOM(html, { runScripts: "dangerously", virtualConsole: vc,
  beforeParse(w) { w.TextDecoder = TextDecoder; } });
const { document: doc } = dom.window;
let fails = 0;
const check = (name, ok, d = "") => { console.log(`${ok ? "PASS" : "FAIL"}  ${name}${d ? "  " + d : ""}`); if (!ok) fails++; };
const key = JSON.parse(fs.readFileSync("data/answer_key.json", "utf8"));
const lateExp = Object.values(key.orders).filter(o => o.overdue_days > 0).length;

check("пустое состояние до загрузки", /Загрузите хотя бы один файл/.test(doc.getElementById("out").textContent));
doc.getElementById("demo").click();
const summary = doc.querySelector(".summary").textContent.replace(/\s+/g, " ");
check("сводка", true, summary);
check("карточек на доске = заказов в ключе", doc.querySelectorAll(".card").length === 42, `${doc.querySelectorAll(".card").length}`);
check("красная кромка = просроченные", doc.querySelectorAll(".card.late").length === lateExp, `${doc.querySelectorAll(".card.late").length} из ${lateExp}`);
check("колонка «Не определён» показана", [...doc.querySelectorAll(".col h3")].some(h => h.textContent.startsWith("Не определён")));
check("строк на проверку", doc.querySelectorAll("h2 + .tbl tbody tr").length === 3);
const recon = [...doc.querySelectorAll("table")].pop();
check("сверка сходится по 4 файлам", [...recon.querySelectorAll("tbody tr td:last-child")].every(td => td.textContent === "да"));
const cb = doc.getElementById("onlyLate"); cb.checked = true; cb.dispatchEvent(new dom.window.Event("change"));
check("фильтр «Только просроченные»", doc.querySelectorAll(".card").length === lateExp, `${doc.querySelectorAll(".card").length}`);
cb.checked = false; cb.dispatchEvent(new dom.window.Event("change"));
const sel = doc.getElementById("channel"); sel.value = "Дилер 1"; sel.dispatchEvent(new dom.window.Event("change"));
const d1 = [...doc.querySelectorAll(".card")].every(c => c.textContent.includes("Дилер 1"));
check("фильтр по каналу", d1 && doc.querySelectorAll(".card").length > 0, `${doc.querySelectorAll(".card").length} карточек`);
const d = doc.getElementById("date"); d.value = "2026-12-31"; d.dispatchEvent(new dom.window.Event("change"));
check("смена даты пересчитывает просрочку", doc.querySelectorAll(".card.late").length > 0 && /Просрочено/.test(doc.querySelector(".summary").textContent),
  doc.querySelector(".summary").textContent.replace(/\s+/g, " ").slice(0, 90));
check("ошибок JS нет", !errors.length, errors.join(" | "));
console.log(fails ? `\nНЕ ПРОШЛО: ${fails}` : "\nВСЁ ПРОШЛО");
process.exit(fails ? 1 : 0);
