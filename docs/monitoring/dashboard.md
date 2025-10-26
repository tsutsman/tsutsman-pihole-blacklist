# Аналітика та дашборди

Цей документ описує, як будувати оглядові дашборди на основі
структурованих звітів репозиторію.

## Основні джерела даних

- `reports/dashboard.json` — знімок агрегованих метрик (покриття
  метаданих, кількість доменів та регулярних виразів, розподіл
  категорій, тегів і регіонів, статистика хибнопозитивів).
- `reports/dashboard_history.json` — історія знімків для побудови
  часових рядів.
- `reports/latest_update.json` — деталі останнього оновлення, які
  відображаються у блоці `latest_update` дашборду.
- `reports/diff_history.json` — журнал різниць між релізними
  оновленнями, який поповнюється через `scripts/diff_reports.py`.

## Генерація знімка

```bash
python scripts/generate_dashboard.py \
  --dashboard reports/dashboard.json \
  --history reports/dashboard_history.json \
  --history-limit 120
```

Скрипт виведе JSON у STDOUT, запише повний знімок до файлу
`reports/dashboard.json` та додасть скорочений запис у
`reports/dashboard_history.json` (якщо не передано `--skip-history`).

## Журнал різниць між релізами

Щоб зберегти диф між двома звітами в історії:

```bash
python scripts/diff_reports.py reports/prev.json reports/latest.json \
  --output reports/diff.json \
  --history reports/diff_history.json \
  --history-limit 200
```

Файл `reports/diff_history.json` міститиме впорядковані за часом
записи з ключами `recorded_at`, `delta_total`, списками нових і
видалених доменів, змінами кандидатів на застарівання та джерел.

## Інтеграція з BI

1. Завантажуйте `dashboard.json` і `dashboard_history.json` у
   вибраний BI-інструмент (Metabase, Grafana, Superset) як JSON-джерело.
2. Побудуйте діаграми:
   - к-сть доменів та покриття метаданими у часі (з історії);
   - розподіл категорій/регіонів у поточному зрізі;
   - статуси хибнопозитивів (stacked bar).
3. Для оцінки змін між релізами використовуйте `diff_history.json` і
   відстежуйте різницю в `delta_total` та списки нових доменів.

## Автоматизація

- У CI запускайте `scripts/generate_dashboard.py --skip-history` для
  перевірки, що агрегатор не падає на свіжих даних.
- Для релізів зберігайте артефакти `dashboard.json`, `diff.json` та
  контрольні суми згенерованих списків.

## Контроль якості

- Переконуйтеся, що каталогу достатньо метаданих: низьке покриття в
  полі `metadata.domains.coverage_pct` вимагає пріоритизації.
- Використовуйте статистику хибнопозитивів для планування рев'ю та
  відкатів (`exclude` vs `monitor`).
- При значних стрибках у розділі `categories` перевіряйте джерела з
  низьким `trust` у `data/sources.json`.
