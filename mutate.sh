#!/bin/bash
# Каждая мутация ломает одно правило ТЗ. Тест обязан упасть на каждой.
declare -A M
M["не срезать BOM"]='s/if (b.length >= 3 \&\& b\[0\] === 0xEF/if (false \&\& b[0] === 0xEF/'
M["нет запасной Windows-1251"]='s/new TextDecoder("windows-1251")/new TextDecoder("utf-8")/'
M["склеивать по общему телефону"]='s/else if (hit.size > 1) reason = "phone_ambiguous";//'
M["план монтажа двигает этап"]='s/"назначен": PLANNED/"назначен": "Монтаж"/'
M["рекламация в просрочке"]='s/if (stage === "Закрыт" || stage === "Рекламация") {/if (stage === "Закрыт") {/'
caught=0
for name in "${!M[@]}"; do
  rm -rf /tmp/mut && mkdir /tmp/mut && cp -r data test.js /tmp/mut/
  sed "${M[$name]}" registry.js > /tmp/mut/registry.js
  if cmp -s registry.js /tmp/mut/registry.js; then echo "?? мутация не применилась: $name"; continue; fi
  out=$(cd /tmp/mut && node test.js 2>&1)
  if [ $? -ne 0 ]; then caught=$((caught+1)); echo "поймана: $name → $(echo "$out" | grep FAIL | grep -oE "AC[0-9]+|R10" | paste -sd, -)"
  else echo "ПРОПУЩЕНА: $name"; fi
done
echo "поймано $caught из ${#M[@]}"
