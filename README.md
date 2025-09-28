# Чорний список для Pi-hole

Цей репозиторій містить список регулярних виразів та окремих доменів для блокування ресурсів,
пов'язаних із державами-агресорами.

## Використання
1. Скопіюйте файли `regex.list` та/або `domains.txt` у директорію `/etc/pihole/` на вашому сервері.
2. Перезапустіть службу Pi-hole:
   ```bash
   pihole restartdns
   ```

## Автоматизація
- `python scripts/check_lists.py [--catalog data/catalog.json] [--false-positives data/false_positives.json] [--check-dns]` — перевіряє синтаксис, дублікати, перетини, статуси записів у каталозі та за потреби виконує DNS-моніторинг для доменів із позначкою `monitor`.
- `python scripts/generate_lists.py [--dist-dir DIR] [--formats adguard ublock hosts rpz dnsmasq unbound] [--group-by category|region|source] [--categories ...] [--regions ...]` — формує списки у вибраних форматах, підтримує сегментацію за категорією, регіоном або джерелом та створює додаткові файли з розбивкою у `dist/segments/`.
- `python scripts/update_domains.py [--chunk-size N] [--dest FILE] [--config data/sources.json] [--report reports/latest_update.json] [--status data/domain_status.json]` — паралельно завантажує домени, враховуючи вагу джерел, генерує звіт про додані записи та оновлює історію спостережень.

## Метадані та звітність
- `data/catalog.json` описує категорії, регіони, джерела та статуси для ключових доменів і регулярних виразів. Записи без метаданих потрапляють у сегмент `без-метаданих`.
- `data/sources.json` містить конфігурацію джерел із вагами та частотою оновлення. Файл дозволяє тимчасово вимикати або додавати джерела без зміни коду.
- `data/domain_status.json` зберігає історію появи доменів у джерелах і відмічає записи як `active`, `stale` або `removed`.
- `reports/latest_update.json` показує, які домени додано під час останнього запуску, та короткий список потенційно застарілих записів.
- Згенеровані списки з розбивкою за категоріями й регіонами зберігаються у `dist/segments/` після виконання `generate_lists.py`.

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
- [CriticalPathSecurity Zeus Bad Domains](https://raw.githubusercontent.com/CriticalPathSecurity/ZeusBadDomains/master/baddomains.txt) — домени банківського трояна Zeus


## CI
- Конвеєр GitHub Actions `.github/workflows/ci.yml` щотижня виконує перевірку синтаксису, тести `pytest` та генерацію списків у форматах AdGuard, uBlock і hosts.
- Перед злиттям Pull Request CI гарантує, що оновлені метадані й скрипти не ламають збірку.


## Внесок
1. Форкніть репозиторій та створіть гілку для змін.
2. Виконуйте `pre-commit run --all-files` перед кожним комітом.
3. Для змін у коді додавайте відповідні тести й запускайте `pytest`.
4. У Pull Request опишіть джерело інформації про домен або причину додавання.

## Ліцензія
Проєкт поширюється за ліцензією MIT. Деталі — у файлі `LICENSE`.

## Поточні доменні зони у списку
- `.ru` — Росія
- `.su` — історична зона, що використовується РФ
- `.by` — Білорусь
- `.xn--p1ai` — міжнародне кодування для `.рф`

## Поточні домени у списку
- `vk.com`
- `mail.ru`
- `yandex.ru`
- `ok.ru`
- `rt.com`
- `1tv.ru`
- `smotrim.ru`
- `sputniknews.com`
- `a.tiktokmod.pro`
- `hideservers.net`
- `ams-new.bonuses.email`
- `an.yandex.ru`
- `api.mainnet.minepi.com`
- `checkip.deepstateplatypus.com`
- `dev.period-calendar.com`
- `fcm-pc.period-calendar.com`
- `fetside.com`
- `free-de-ds.hideservers.net`
- `ipinfo.suinfra.com`
- `kms.03k.org`
- `mirai.senkuro.org`
- `pcudataproxy.period-calendar.com`
- `peradjoka.t35.com`
- `shiro.senkuro.org`
- `static.okko.tv`
- `tse2.explicit.bing.net`
- `zakpos.mine.nu`
- `gosuslugi.ru`
- `sberbank.ru`
- `kremlin.ru`
- `mos.ru`
- `tass.ru`
- `ria.ru`
- `rbc.ru`
- `lenta.ru`
- `gazprombank.ru`
- `vgtrk.ru`
- `vtb.ru`

Перелік буде поповнюватися.
