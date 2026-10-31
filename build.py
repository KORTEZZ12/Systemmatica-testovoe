# Сборка: встраивает в страницу тот же registry.js, что проходил тест, и сами демо-файлы
import base64, hashlib, json, re
js = open("registry.js", encoding="utf-8").read()
demo = {k: base64.b64encode(open(f"data/{k}.csv", "rb").read()).decode() for k in ["sales", "production", "montage", "crm"]}
html = open("template.html", encoding="utf-8").read()
html = html.replace("/*__REGISTRY_JS__*/", js).replace("/*__DEMO_DATA__*/", json.dumps(demo))
open("/mnt/user-data/outputs/registry.html", "w", encoding="utf-8").write(html)
inlined = re.search(r"<script>\n(.*?)\n</script>", html, re.S).group(1)
h = lambda s: hashlib.sha256(s.encode()).hexdigest()[:12]
print("модуль:", h(js), "| в странице:", h(inlined), "| совпадает:", inlined == js, "| размер:", len(html.encode()) // 1024, "КБ")
