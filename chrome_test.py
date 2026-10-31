# Проверка в настоящем Chrome: открываем файл registry.html с диска, грузим CSV через кнопки, сверяем сводку с демо
import base64, re
from playwright.sync_api import sync_playwright
F = "node_modules/@fontsource/golos-text/files/golos-text-"
css = ""
for sub, rng in [("cyrillic", "U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116"), ("latin", "U+0000-00FF,U+2000-206F,U+20AC")]:
    for w in (400, 500, 600, 700):
        try: data = base64.b64encode(open(f"{F}{sub}-{w}-normal.woff2", "rb").read()).decode()
        except FileNotFoundError: continue
        css += f"@font-face{{font-family:'Golos Text';font-weight:{w};src:url(data:font/woff2;base64,{data}) format('woff2');unicode-range:{rng}}}"
errors, fails = [], 0
def check(name, ok, d=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + (f"  {d}" if d else "")); fails += (not ok)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/google/chrome/chrome", args=["--no-sandbox", "--lang=ru-RU"])
    ctx = b.new_context(locale="ru-RU", viewport={"width": 1440, "height": 900}, device_scale_factor=1.5); pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
    pg.route("https://fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=css))
    pg.route("https://fonts.gstatic.com/**", lambda r: r.abort())
    pg.goto("file:///mnt/user-data/outputs/registry.html")
    pg.fill("#date", "2026-10-30")
    for k in ["sales", "production", "montage", "crm"]:
        pg.set_input_files(f"#f-{k}", f"data/{k}.csv")
    upl = pg.inner_text(".summary")
    states = [pg.inner_text(f"#s-{k}") for k in ["sales", "production", "montage", "crm"]]
    check("загрузка через кнопки, все 4 файла", all("ошибка" not in s.lower() and "нет колонок" not in s for s in states), " | ".join(states))
    pg.click("#demo")
    demo = pg.inner_text(".summary")
    check("сводка после загрузки = сводке демо", upl == demo, demo)
    check("карточек 42", pg.locator(".card").count() == 42, str(pg.locator(".card").count()))
    check("шрифт Golos Text применён", pg.evaluate("document.fonts.check('16px \"Golos Text\"')"))
    check("ошибок JS нет", not errors, "; ".join(errors))
    pg.screenshot(path="shot_board.png", clip={"x": 0, "y": 0, "width": 1440, "height": 900})
    pg.locator("h2", has_text="Требует проверки").scroll_into_view_if_needed()
    y = pg.evaluate("document.querySelector('h2').getBoundingClientRect().top + scrollY - 16")
    h = pg.evaluate("document.body.scrollHeight") - y
    pg.screenshot(path="shot_review.png", full_page=True, clip={"x": 0, "y": y, "width": 1440, "height": min(h, 700)})
    pg.emulate_media(color_scheme="dark"); pg.wait_for_timeout(200)
    pg.screenshot(path="shot_dark.png", clip={"x": 0, "y": 0, "width": 1440, "height": 900})
    m = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    m.route("https://fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=css))
    m.goto("file:///mnt/user-data/outputs/registry.html"); m.click("#demo")
    over = m.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    check("телефон 390 px: страница не скроллится вбок", not over)
    m.screenshot(path="shot_mobile.png")
    b.close()
print("ВСЁ ПРОШЛО" if not fails else f"НЕ ПРОШЛО: {fails}")
