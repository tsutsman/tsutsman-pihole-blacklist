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
- `python scripts/check_lists.py` — перевіряє списки, виявляє дублікати й помилки.
- `python scripts/generate_lists.py` — створює формати для AdGuard та uBlock у каталозі `dist/`.
- `python scripts/update_domains.py` — завантажує домени зі сторонніх перевірених списків і додає їх у `domains.txt` порціями по 500.

## Джерела доменів
Скрипт `update_domains.py` використовує публічні списки, що регулярно оновлюються:
- [URLhaus](https://urlhaus.abuse.ch/)
- [Phishing Army](https://phishing.army/)
- [StevenBlack/hosts](https://github.com/StevenBlack/hosts)
- [AnudeepND/blacklist](https://github.com/anudeepND/blacklist) — рекламні та трекінгові домени
- [Phishing.Database](https://github.com/mitchellkrogza/Phishing.Database) — фішингові домени
- [StevenBlack/hosts (gambling-only)](https://github.com/StevenBlack/hosts/tree/master/alternates/gambling-only) — азартні домени


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
- `vtb.ru`

Перелік буде поповнюватися.
