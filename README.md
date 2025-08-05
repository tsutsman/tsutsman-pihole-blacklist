# Чорний список для Pi-hole

Цей репозиторій містить список регулярних виразів для блокування доменних зон, пов'язаних з державами-агресорами.

## Використання
1. Скопіюйте файл `regex.list` у директорію `/etc/pihole/` на вашому сервері.
2. Перезапустіть службу Pi-hole:
   ```bash
   pihole restartdns
   ```

Файл `domains.txt` містить точні доменні імена, які можна імпортувати безпосередньо у Pi-hole.

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

Перелік буде поповнюватися.
