# Чорний список для Pi-hole

[English version](README.en.md)

Цей репозиторій містить список регулярних виразів та окремих доменів для блокування ресурсів,
пов'язаних із державами-агресорами.

## Використання
1. Скопіюйте файли `regex.list` та/або `domains.txt` у директорію `/etc/pihole/` на вашому сервері.
2. Перезапустіть службу Pi-hole:
   ```bash
   pihole restartdns
   ```

## Автоматизація
- `python scripts/check_lists.py [--catalog data/catalog.json] [--false-positives data/false_positives.json] [--check-dns] [--require-metadata {domains,regexes,all}]` — перевіряє синтаксис, дублікати, перетини, статуси записів у каталозі, може вимагати наявність метаданих для вибраних списків і за потреби виконує DNS-моніторинг для доменів із позначкою `monitor`.
- `python scripts/validate_catalog.py [--catalog data/catalog.json] [--policy data/inclusion_policy.json]` — гарантує, що метадані відповідають критеріям включення (див. [docs/criteria.md](docs/criteria.md)).
- `python scripts/audit_lists.py [--output reports/audit.json]` — формує JSON-звіт з аудитом списків, охопленням метаданими та виявленням записів каталогу без відповідників.
- `python scripts/generate_lists.py [--dist-dir DIR] [--formats adguard ublock hosts rpz dnsmasq unbound] [--group-by category|region|source] [--categories ...] [--regions ...] [--severities ...] [--tags ...]` — формує списки у вибраних форматах, підтримує сегментацію за категорією, регіоном або джерелом, дозволяє фільтрувати записи за рівнем важливості та тегами й створює додаткові файли з розбивкою у `dist/segments/`.
- `python scripts/update_domains.py [--chunk-size N] [--dest FILE] [--config data/sources.json] [--report reports/latest_update.json] [--status data/domain_status.json]` — паралельно завантажує домени, враховуючи вагу та коефіцієнт довіри джерел (`trust`), контролює дотримання `sla_days` і за потреби автоматично пропускає джерела з `auto_disable_on_sla`, генерує звіт про додані записи та оновлює історію спостережень.
- `python scripts/diff_reports.py PREVIOUS CURRENT [--output FILE]` — порівнює два JSON-звіти оновлень (наприклад, `reports/latest_update.json`) і формує диф для changelog та історії релізів.

## Метадані та звітність
- `data/catalog.json` описує категорії, регіони, джерела та статуси для ключових доменів і регулярних виразів. Записи без метаданих потрапляють у сегмент `без-метаданих`.
- `data/sources.json` містить конфігурацію джерел із вагами, коефіцієнтом довіри (`trust`), очікуваним SLA (`sla_days`) і прапорцем `auto_disable_on_sla`, що дозволяє автоматично пропускати застарілі фіди. Файл дозволяє тимчасово вимикати або додавати джерела без зміни коду.
- `data/domain_status.json` зберігає історію появи доменів у джерелах і відмічає записи як `active`, `stale` або `removed`.
- `reports/latest_update.json` показує, які домени додано під час останнього запуску, короткий список потенційно застарілих записів, стан кожного джерела (`source_health`), пропущені через SLA фіди (`skipped_sources`) та ознаку наявності помилок завантаження.
- Згенеровані списки з розбивкою за категоріями й регіонами зберігаються у `dist/segments/` після виконання `generate_lists.py`.

## Категорії шкідливих доменів
Каталог метаданих охоплює повний перелік тематичних груп, які використовуються для сегментації списків:

- **анонімайзери** — VPN, проксі та інші сервіси обходу блокувань, що маскують шкідливу активність.
- **ботнет** — інфраструктура керування та зв'язку з ботнетами або мережами заражених пристроїв.
- **держсервіси** — ресурси державних установ держав-агресорів і пов'язані з ними портали.
- **екосистема** — великі цифрові платформи, що надають доступ до множини сервісів ворожої інфраструктури.
- **контент 18+** — домени з небажаними матеріалами для дорослих, які блокуються з міркувань безпеки.
- **крипто-шахрайство** — фішингові та шахрайські схеми, замасковані під криптовалютні проєкти.
- **криптомайнінг** — сервіси, що нав'язують майнінг або використовують ресурси користувачів без згоди.
- **пропаганда** — державні чи афілійовані ЗМІ та платформи розповсюдження ворожих наративів.
- **фінанси** — банки, платіжні сервіси та інші фінансові інституції, пов'язані з агресором.
- **фішинг** — домени, що імітують легітимні ресурси для викрадення облікових даних.
- **шахрайство** — схеми виманювання коштів або персональних даних, не обмежені криптосектором.
- **шкідливе ПЗ** — сайти поширення зловмисних програм та інструментів.
- **шпигунство** — ресурси збору телеметрії, стеження або витоку чутливих даних.
- **інфраструктура** — технічні сервіси підтримки ворожих ІТ-систем (DNS, CDN, хостинг тощо).

## Джерела доменів
Скрипт `update_domains.py` використовує публічні списки, що регулярно оновлюються:
- [URLhaus](https://urlhaus.abuse.ch/)
- [Phishing Army](https://phishing.army/)
- [StevenBlack/hosts](https://github.com/StevenBlack/hosts)
- [AnudeepND/blacklist](https://github.com/anudeepND/blacklist) — рекламні та трекінгові домени
- [Phishing.Database](https://github.com/mitchellkrogza/Phishing.Database) — фішингові домени
- [StevenBlack/hosts (gambling-only)](https://github.com/StevenBlack/hosts/tree/master/alternates/gambling-only) — азартні домени
- [Firebog/Prigent-Malware](https://v.firebog.net/hosts/Prigent-Malware.txt) — домени з відомими зловмисними програмами
- [Firebog/Prigent-Crypto](https://v.firebog.net/hosts/Prigent-Crypto.txt) — криптовалютні шахрайські майданчики
- [PolishFiltersTeam/KADhosts](https://raw.githubusercontent.com/PolishFiltersTeam/KADhosts/master/KADhosts.txt) — польський фішинговий та шахрайський список
- [Spam404 Project](https://raw.githubusercontent.com/Spam404/lists/master/main-blacklist.txt) — домени, що використовуються у фішингових кампаніях
- [malware-filter/malware-filter-hosts](https://malware-filter.gitlab.io/malware-filter/malware-filter-hosts.txt) — агрегований перелік шкідливих доменів
- [malware-filter/phishing-filter-hosts](https://malware-filter.gitlab.io/malware-filter/phishing-filter-hosts.txt) — активні фішингові домени
- [Hagezi DNS Blocklists (malicious)](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/hosts/malicious.txt) — ретельно перевірені шкідливі хости
- [BlocklistProject/malware](https://raw.githubusercontent.com/blocklistproject/Lists/master/malware.txt) — загальна шкідлива активність
- [BlocklistProject/phishing](https://raw.githubusercontent.com/blocklistproject/Lists/master/phishing.txt) — нові фішингові кампанії
- [DigitalSide Threat-Intel](https://osint.digitalside.it/Threat-Intel/lists/latestdomains.txt) — оперативні домени активних кампаній шкідливого ПЗ
- [ThreatView High-Confidence Domain Feed](https://threatview.io/Downloads/DOMAIN-High-Confidence-Feed.txt) — високодостовірні зловмисні домени
- [ThreatFox Hostfile](https://threatfox.abuse.ch/downloads/hostfile/) — шкідливі домени з проєкту abuse.ch ThreatFox
- [CriticalPathSecurity Zeus Bad Domains](https://raw.githubusercontent.com/CriticalPathSecurity/ZeusBadDomains/master/baddomains.txt) — домени банківського трояна Zeus


## CI
- Конвеєр GitHub Actions `.github/workflows/ci.yml` щотижня виконує перевірку синтаксису, тести `pytest` та генерацію списків у форматах AdGuard, uBlock і hosts.
- Перед злиттям Pull Request CI гарантує, що оновлені метадані й скрипти не ламають збірку.
- Тестовий етап формує звіт покриття за допомогою `coverage.py` та провалюється, якщо показник падає нижче 85%.
- Статичні перевірки включають `pip-audit --strict` для виявлення вразливих залежностей і `bandit -r scripts -ll` для пошуку потенційних проблем безпеки в скриптах.


## Внесок
1. Форкніть репозиторій та створіть гілку для змін.
2. Виконуйте `pre-commit run --all-files` перед кожним комітом.
3. Для змін у коді додавайте відповідні тести й запускайте `pytest`.
4. У Pull Request опишіть джерело інформації про домен або причину додавання.

## Політика прийому нових доменів і вимоги до метаданих

### Обов'язкові кроки перед створенням PR
- Переконайтеся, що для кожного домену чи регулярного виразу є як мінімум одне надійне джерело з `data/sources.json` або
  задокументований інцидент. Додайте посилання в опис Pull Request і в полі `sources` каталогу.
- Запустіть `python scripts/check_lists.py --require-metadata all` і додайте в PR фрагмент виводу, який підтверджує успішне
  завершення перевірок (синтаксис, дублікати, статуси).
- Для записів, імпортованих зі зовнішніх фідів, додайте коротку нотатку щодо дати отримання і ймовірності хибнопозитивів у полі
  `notes`.

### Вимоги до метаданих каталогу
- `data/catalog.json` має містити для активних записів поля `category`, `regions`, `sources`, `status`; за необхідності зазначайте
  `confidence` (рівень довіри) та `last_seen`.
- Якщо домен стосується конкретного географічного регіону або кампанії, вкажіть це у масиві `regions` разом із коротким
  поясненням.
- Для регулярних виразів додавайте приклади збігів у полі `samples`, щоб рев’юери могли швидко перевірити мету блокування.

### Критерії відхилення та контроль якості
- Домени без підтверджених джерел або з високою ймовірністю хибнопозитивів відхиляються до моменту отримання додаткових доказів.
- Якщо після додавання домену надходять скарги, додайте запис до `data/false_positives.json` та підготуйте опис сценарію
  спрацьовування й рекомендацію з відкату.
- Суперечливі кейси мають супроводжуватися журналом перевірки (`scripts/validate_catalog.py`, DNS-запити, скріншоти) та
  оцінкою впливу на користувачів у PR.

### Оновлення звітів і артефактів
- Після зміни списків виконуйте `python scripts/generate_lists.py` для відтворення сегментів і додавайте контрольні суми у
  коментар PR або в артефакти CI.
- Оновіть відповідні файли в `reports/` (наприклад, `reports/latest_update.json`, `reports/audit.json`) і впевніться, що вони
  містять актуальні метрики.
- У changelog релізу зазначайте нові домени, джерела та потенційні ризики, щоб користувачі могли прийняти усвідомлене рішення про
  оновлення.

### Облік хибнопозитивів та швидкий відкат
- Файл `data/false_positives.json` містить структуровані об'єкти з полями `reason`, `reported_by`, `reported_at`, `review_status`,
  `action`, `notes` та переліком `evidence`. Вони дозволяють відстежувати джерело звернення і статус перевірки.
- Для негайного вилучення підтверджених хибнопозитивів використовуйте `python scripts/rollback_false_positives.py --output-dir dist/rollback`.
  Скрипт створює очищені `domains.txt`, `regex.list` та `summary.json` зі списком виключених записів і тими, що очікують перевірки.
- Значення з `action = "exclude"` прибираються із згенерованих файлів, тоді як записи зі статусом `monitor` залишаються для
  додаткового спостереження.

## Ліцензія
Проєкт поширюється за ліцензією MIT. Деталі — у файлі `LICENSE`.

## Поточні доменні зони у списку
- `.ru` — Росія
- `.su` — історична зона, що використовується РФ
- `.by` — Білорусь
- `.xn--p1ai` — міжнародне кодування для `.рф`

## Ключові домени за категоріями
Ручно підтримувані домени згруповано за тематичними категоріями. Детальні списки з описами зберігаються в окремих файлах:

- [Пропагандистські та медійні ресурси](docs/key-domains/propaganda-media.md)
- [Соціальні платформи та екосистеми РФ](docs/key-domains/ecosystems.md)
- [Державні сервіси та інституції РФ](docs/key-domains/government.md)
- [Банківські та фінансові структури](docs/key-domains/finance.md)
- [Шкідливі, шпигунські та шахрайські ресурси](docs/key-domains/malware-tracking.md)

### Зведений перелік ключових доменів
Алфавітний список нижче формується як об'єднання категорій вище і може використовуватися для швидкої перевірки наявності запису:

- `1tv.ru`
- `a.tiktokmod.pro`
- `ams-new.bonuses.email`
- `an.yandex.ru`
- `anna-news.info`
- `api.mainnet.minepi.com`
- `checkip.deepstateplatypus.com`
- `dev.period-calendar.com`
- `eadaily.com`
- `fcm-pc.period-calendar.com`
- `fetside.com`
- `free-de-ds.hideservers.net`
- `gazprombank.ru`
- `gosuslugi.ru`
- `hideservers.net`
- `ipinfo.suinfra.com`
- `kms.03k.org`
- `kremlin.ru`
- `mid.ru`
- `mil.ru`
- `lenta.ru`
- `life.ru`
- `mail.ru`
- `mirai.senkuro.org`
- `mos.ru`
- `ok.ru`
- `pcudataproxy.period-calendar.com`
- `peradjoka.t35.com`
- `patriot.media`
- `rbc.ru`
- `ria.ru`
- `riafan.ru`
- `rt.com`
- `rusvesna.su`
- `rutube.ru`
- `sberbank.ru`
- `shiro.senkuro.org`
- `smotrim.ru`
- `sputnikglobe.com`
- `sputniknews.com`
- `static.okko.tv`
- `tass.ru`
- `tsargrad.tv`
- `tvzvezda.ru`
- `tse2.explicit.bing.net`
- `vgtrk.ru`
- `vk.com`
- `voennoedelo.com`
- `vtb.ru`
- `vz.ru`
- `warsonline.info`
- `yandex.ru`
- `zakpos.mine.nu`

Перелік буде поповнюватися.
