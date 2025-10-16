#!/usr/bin/env python3
"""Формує додаткову вибірку шкідливих доменів для файлу domains.txt.

Скрипт збирає домени з відкритих джерел і ручних добірок, гарантує
унікальність відносно наявного списку та розподіл за всіма підтримуваними
категоріями. Результат використовується для оновлення `domains.txt` та
формування метаданих партії.
"""

from __future__ import annotations

import json
import textwrap
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parent.parent
DOMAINS_PATH = REPO_ROOT / "domains.txt"
OUTPUT_JSON = (
    REPO_ROOT / "data" / "batches" / "2024-10-malicious-expansion.json"
)


class BatchBuilder:
    """Накопичує домени та метадані з контролем дублювання."""

    def __init__(self, existing: Iterable[str]) -> None:
        self._existing = {
            d.strip().lower()
            for d in existing
            if d.strip()
        }
        self._new_domains: Dict[str, Dict[str, object]] = {}
        self._category_counts: Dict[str, int] = defaultdict(int)

    def add(
        self,
        domain: str,
        category: str,
        source: str,
        note: Optional[str] = None,
    ) -> bool:
        domain = domain.strip().lower()
        if not domain or domain.startswith("#"):
            return False
        if domain.startswith("0.0.0.0 "):
            domain = domain.split(maxsplit=1)[1]
        if any(c in domain for c in " /\t"):
            return False
        if domain.endswith(".local") or domain.endswith(".localhost"):
            return False
        if domain in self._existing:
            return False
        if domain in self._new_domains:
            entry = self._new_domains[domain]
            if entry["category"] != category:
                notes = set(
                    entry.get("notes", [])  # type: ignore[arg-type]
                )
                note_text = (
                    f"Категорія '{category}' отримана зі джерела {source}, "
                    "залишено первісну"
                )
                notes.add(note_text)
                entry["notes"] = sorted(notes)
                sources = set(
                    entry["sources"]  # type: ignore[assignment]
                )
                if source not in sources:
                    sources.add(source)
                    entry["sources"] = sorted(sources)
                return False
            sources = set(
                entry["sources"]  # type: ignore[assignment]
            )
            sources.add(source)
            entry["sources"] = sorted(sources)
            if note:
                notes = set(
                    entry.get("notes", [])  # type: ignore[arg-type]
                )
                notes.add(note)
                entry["notes"] = sorted(notes)
            return False
        data: Dict[str, object] = {
            "domain": domain,
            "category": category,
            "sources": [source],
        }
        if note:
            data["notes"] = [note]
        self._new_domains[domain] = data
        self._category_counts[category] += 1
        return True

    @property
    def category_counts(self) -> Dict[str, int]:
        return dict(self._category_counts)

    @property
    def domains(self) -> List[str]:
        return sorted(self._new_domains)

    @property
    def records(self) -> List[Dict[str, object]]:
        return sorted(
            self._new_domains.values(), key=lambda item: item["domain"]
        )


def fetch_lines(url: str) -> Iterable[str]:
    try:
        with urlopen(url) as response:  # nosec B310
            payload = response.read().decode("utf-8", errors="ignore")
    except HTTPError as exc:  # pragma: no cover - мережеві збої
        raise RuntimeError(
            f"HTTP {exc.code} під час завантаження {url}"
        ) from exc
    except URLError as exc:  # pragma: no cover - мережеві збої
        raise RuntimeError(
            f"Помилка мережі під час завантаження {url}: {exc}"
        ) from exc
    for raw_line in payload.splitlines():
        yield raw_line.strip()


def collect_from_url(
    builder: BatchBuilder,
    url: str,
    category: str,
    source: str,
    limit: Optional[int] = None,
    keyword_filter: Optional[Iterable[str]] = None,
) -> None:
    added = 0
    keywords = (
        None if keyword_filter is None else [k.lower() for k in keyword_filter]
    )
    for line in fetch_lines(url):
        if limit is not None and added >= limit:
            break
        domain = line
        if not domain:
            continue
        if domain.startswith("0.0.0.0 "):
            domain = domain.split(maxsplit=1)[1]
        if keywords is not None and not any(
            token in domain.lower() for token in keywords
        ):
            continue
        if builder.add(domain, category, source):
            added += 1


def add_manual(
    builder: BatchBuilder, category: str, source: str, domains: Iterable[str]
) -> None:
    for domain in domains:
        builder.add(domain, category, source)


def main() -> None:
    existing = DOMAINS_PATH.read_text(encoding="utf-8").splitlines()
    builder = BatchBuilder(existing)

    manual_categories = {
        "анонімайзери": [
            "12vpn.net",
            "1clickvpn.net",
            "1cfreevpn.com",
            "4everproxy.com",
            "acevpn.com",
            "airvpn.org",
            "anonymize.com",
            "anonymizing.com",
            "avira-vpn.com",
            "belo-vpn.ru",
            "betternet.co",
            "blackvpn.com",
            "browsec.com",
            "bulletvpn.com",
            "buy.finevpn.org",
            "cf-vpn.com",
            "citadelvpn.com",
            "fastvpn.com",
            "flashvpn.com",
            "free-hidemyass.com",
            "freevpn.me",
            "freevpn.org",
            "freevpnadd.com",
            "frootvpn.com",
            "ghostpath.com",
            "hidemy.name",
            "hidemyass.com",
            "hide.me",
            "hideipvpn.com",
            "hotspotshield.com",
            "imonstervpn.com",
            "ipvanish.com",
            "kasperskyvpn.ru",
            "kproxy.com",
            "lantern.io",
            "libertyshield.com",
            "myfastvpn.com",
            "nordvpn.com",
            "openvpn.net",
            "orangetunnel.com",
            "privadovpn.com",
            "privacyvpn.org",
            "privatevpn.com",
            "protonvpn.com",
            "psiphon.ca",
            "purevpn.com",
            "ra4wvpn.com",
            "seed4.me",
            "smartdnsproxy.com",
            "strongvpn.com",
            "surfshark.com",
            "tigervpn.com",
            "torguard.net",
            "touchvpn.net",
            "tunnelbear.com",
            "urban-vpn.com",
            "vpnbook.com",
            "vpnjantit.com",
            "vpnmaster.com",
            "vpnmentor.com",
            "vpnsecure.me",
            "vyprvpn.com",
            "windscribe.com",
            "worldvpn.net",
            "zoogvpn.com",
        ],
        "держсервіси": [
            "17.mvd.ru",
            "admportal.rosmintrud.ru",
            "aic.gov.ru",
            "arbitr.ru",
            "auth.gosuslugi.ru",
            "bezopasnost.edu.ru",
            "cis.mos.ru",
            "cloud.mil.ru",
            "data.gov.ru",
            "digital.gov.ru",
            "edu.ru",
            "egisso.ru",
            "esia.gosuslugi.ru",
            "fapmc.ru",
            "fcs.gov.ru",
            "fias.nalog.ru",
            "fivc.ru",
            "fms.gov.ru",
            "fpkgr.ru",
            "fstec.ru",
            "gosexpert.ru",
            "gossluzhba.gov.ru",
            "gost.ru",
            "gz-spb.ru",
            "iacpm.ru",
            "ipap.ru",
            "lk.budget.gov.ru",
            "mchs.media",
            "mid.ru",
            "minec.gov.ru",
            "minfin.gov.ru",
            "minstroy.ru",
            "mintrud.gov.ru",
            "nalog.gov.ru",
            "nsi.rosmintrud.ru",
            "oiv.gov.ru",
            "pravo.gov.ru",
            "priemnaya.mid.ru",
            "reestr-zalogov.ru",
            "roskazna.ru",
            "rosminzdrav.ru",
            "rosobrnadzor.gov.ru",
            "rospotrebnadzor.ru",
            "rosreestr.gov.ru",
            "rostransnadzor.gov.ru",
            "sfo.minfin.ru",
            "smi.gov.ru",
            "stat.gibdd.ru",
            "structura.gks.ru",
            "szv.minjust.gov.ru",
            "torgi.gov.ru",
            "udprf.ru",
            "zakupki.gov.ru",
        ],
        "екосистема": [
            "adsmy.top.mail.ru",
            "aura.sber.ru",
            "autorambler.ru",
            "b2b.center",
            "beru.ru",
            "biz.mail.ru",
            "bizon365.ru",
            "boostaero.ru",
            "bt.sberbank.ru",
            "business.dvhab.ru",
            "citydrive.ru",
            "cloud.sber.ru",
            "connect.yandex.ru",
            "corp.mail.ru",
            "delivery-club.ru",
            "dfir-ru.ru",
            "dostavista.ru",
            "edadeal.ru",
            "edugame.ru",
            "eda.yandex",
            "market.yandex.ru",
            "mcs.mail.ru",
            "megafon.tv",
            "mm.coinsbank.com",
            "my.games",
            "mytarget.ru",
            "okko.tv",
            "partnerkin.com",
            "partners.vk.com",
            "platformaofd.ru",
            "platforma.rosatom.ru",
            "plus.yandex.ru",
            "promo.vkplay.ru",
            "qplatform.ru",
            "sbercloud.ru",
            "school.mosreg.ru",
            "shop.1c.ru",
            "sima-land.ru",
            "smartway.sber.ru",
            "solutions.1c.ru",
            "sputnik.ru",
            "staff.sber.ru",
            "store.my.games",
            "tinkoffjournal.ru",
            "vk.app",
            "vkplay.ru",
            "yappy.media",
            "youla.ru",
            "zen.yandex.ru",
        ],
        "пропаганда": [
            "24tv.ua",
            "anna-news.info",
            "antimaidan.ru",
            "avia.pro",
            "bloknot.ru",
            "eurasia.expert",
            "evrazia.org",
            "freerussia.info",
            "gazeta.ru",
            "glav.su",
            "glavny.tv",
            "gosnovosti.com",
            "iz.ru",
            "k-eta.ru",
            "kafanews.com",
            "katehon.com",
            "kolokolrussia.ru",
            "lifenews.ru",
            "militaryreview.ru",
            "nao24.ru",
            "newinform.com",
            "novorosinform.org",
            "politikus.ru",
            "pnp.ru",
            "pravda.ru",
            "ria.ru",
            "rusnext.ru",
            "smi2.ru",
            "smotrim.ru",
            "solenka.info",
            "sputniknews.com",
            "starpolit.ru",
            "stoletie.ru",
            "svpressa.ru",
            "topcor.ru",
            "tvzvezda.ru",
            "ukraina.ru",
            "varlamov.ru",
            "vesma.today",
            "vpk-news.ru",
            "vz.ru",
            "warfiles.ru",
            "yugopolis.ru",
            "zavtra.ru",
        ],
        "фінанси": [
            "absolutbank.ru",
            "akbars.ru",
            "alfadirect.ru",
            "alfa-investor.ru",
            "alorbroker.ru",
            "atb.su",
            "avangard.ru",
            "bank-hlynov.ru",
            "bank-uralsib.ru",
            "bankiro.ru",
            "belapb.by",
            "bspb.ru",
            "capitalbank.by",
            "finam.ru",
            "forabank.ru",
            "gazfond.ru",
            "gazprombank.ru",
            "homebank.kz",
            "homecredit.ru",
            "ingbank.ru",
            "investfunds.ru",
            "lockobank.ru",
            "metallinvestbank.ru",
            "minbank.ru",
            "mn.ru",
            "mosoblbank.ru",
            "otkritie.ru",
            "promsvyazbank.ru",
            "rencredit.ru",
            "rncb.ru",
            "rosbank.ru",
            "rsb.ru",
            "sberasset.ru",
            "sberbank.ru",
            "sovcombank.ru",
            "trust.ru",
            "unicreditbank.ru",
            "uralfd.ru",
            "vtbcapital.ru",
            "zenit.ru",
        ],
        "шпигунство": [
            "agentura.ru",
            "appmetrica.yandex.ru",
            "audit.mil.ru",
            "azimuth.aero",
            "census.mil.ru",
            "cloud.fsb.ru",
            "dataleak.ru",
            "digitaltarget.ru",
            "drweb.com",
            "e-queo.com",
            "falconsat.ru",
            "ferret.rosgvard.ru",
            "finder.vk.com",
            "fobos-izmerenia.ru",
            "geo.gosuslugi.ru",
            "hitech.rosgvard.ru",
            "intellexa.com",
            "kaspersky.ru",
            "kribrum.ru",
            "leak.su",
            "mashtab.rosatom.ru",
            "monitoring.mos.ru",
            "monline.mvd.ru",
            "nortex-spy.ru",
            "perimeter-center.ru",
            "rts-telecom.ru",
            "ru.likelydata.com",
            "sorm.ru",
            "spylog.ru",
            "suricat.ru",
            "webanalytics.yandex.ru",
            "zecurion.ru",
        ],
        "інфраструктура": [
            "1c.ru",
            "cloud.mts.ru",
            "corp.beeline.ru",
            "data-line.ru",
            "datapro.ru",
            "ddos-guard.net",
            "dns-shop.ru",
            "dsm.ru",
            "dtln.ru",
            "energia.ru",
            "eqvanta.ru",
            "ertelecom.ru",
            "fregat.ru",
            "gcorelabs.com",
            "infotecs.ru",
            "it-grad.ru",
            "itpark-kazan.ru",
            "justhost.ru",
            "korusconsulting.ru",
            "lanit.ru",
            "legion-telecom.ru",
            "lesta.ru",
            "mtscloud.ru",
            "niihm.ru",
            "obit.ru",
            "red-soft.ru",
            "rosatomtech.com",
            "rosstelecom.ru",
            "rtcloud.ru",
            "scloud.ru",
            "selectel.ru",
            "softline.ru",
            "softhard.ru",
            "sovzond.ru",
            "t1.ru",
            "tele2.ru",
            "ttk.ru",
            "vscale.io",
            "webzilla.com",
            "yandex.cloud",
            "zelenaya.net",
        ],
    }

    for category, domains in manual_categories.items():
        add_manual(builder, category, "osint-manual", domains)

    print("Завантаження фіду phishing-army...")
    collect_from_url(
        builder,
        "https://phishing.army/download/phishing_army_blocklist_extended.txt",
        "фішинг",
        "phishing-army",
        limit=220,
    )
    print("Завантаження фіду Spam404...")
    collect_from_url(
        builder,
        (
            "https://raw.githubusercontent.com/"
            "Spam404/lists/master/main-blacklist.txt"
        ),
        "шахрайство",
        "spam404",
        limit=80,
    )
    print("Завантаження фіду Prigent Malware...")
    collect_from_url(
        builder,
        "https://v.firebog.net/hosts/Prigent-Malware.txt",
        "шкідливе ПЗ",
        "firebog-prigent-malware",
        limit=140,
    )
    print("Завантаження фіду Prigent Crypto...")
    collect_from_url(
        builder,
        "https://v.firebog.net/hosts/Prigent-Crypto.txt",
        "крипто-шахрайство",
        "firebog-prigent-crypto",
        limit=90,
    )
    print("Завантаження списку adblock-nocoin...")
    collect_from_url(
        builder,
        (
            "https://raw.githubusercontent.com/"
            "hoshsadiq/adblock-nocoin-list/master/hosts.txt"
        ),
        "криптомайнінг",
        "adblock-nocoin",
        limit=80,
    )
    print("Завантаження ботнет-фідів Maltrail...")
    botnet_feeds = {
        "maltrail-cutwail": (
            (
                "https://raw.githubusercontent.com/stamparm/maltrail/"
                "master/trails/static/malware/cutwail.txt"
            ),
            40,
        ),
        "maltrail-dcrat": (
            (
                "https://raw.githubusercontent.com/stamparm/maltrail/"
                "master/trails/static/malware/dcrat.txt"
            ),
            30,
        ),
        "maltrail-darkgate": (
            (
                "https://raw.githubusercontent.com/stamparm/maltrail/"
                "master/trails/static/malware/darkgate.txt"
            ),
            30,
        ),
        "maltrail-darkrat": (
            (
                "https://raw.githubusercontent.com/stamparm/maltrail/"
                "master/trails/static/malware/darkrat.txt"
            ),
            30,
        ),
    }
    for source_id, (url, limit) in botnet_feeds.items():
        collect_from_url(builder, url, "ботнет", source_id, limit=limit)
    print("Завантаження BlocklistProject porn...")
    collect_from_url(
        builder,
        (
            "https://raw.githubusercontent.com/blocklistproject/"
            "Lists/master/porn.txt"
        ),
        "контент 18+",
        "blocklistproject-porn",
        limit=80,
    )

    # Деякі фішингові домени додатково маркуємо як шахрайство
    # для банківських схем.
    print("Завантаження Scamblocklist...")
    collect_from_url(
        builder,
        (
            "https://raw.githubusercontent.com/durablenapkin/"
            "scamblocklist/master/hosts.txt"
        ),
        "шахрайство",
        "durablenapkin-scam",
        limit=60,
    )

    summary = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "total_new_domains": len(builder.domains),
        "category_counts": builder.category_counts,
        "sources": {
            "osint-manual": (
                "Ручна добірка з відкритих російських ресурсів "
                "та сервісів"
            ),
            "phishing-army": "https://phishing.army/",
            "spam404": "https://github.com/Spam404/lists",
            "firebog-prigent-malware": (
                "https://v.firebog.net/hosts/Prigent-Malware.txt"
            ),
            "firebog-prigent-crypto": (
                "https://v.firebog.net/hosts/Prigent-Crypto.txt"
            ),
            "adblock-nocoin": (
                "https://github.com/hoshsadiq/adblock-nocoin-list"
            ),
            "maltrail-cutwail": (
                "https://github.com/stamparm/maltrail/blob/master/trails/"
                "static/malware/cutwail.txt"
            ),
            "maltrail-dcrat": (
                "https://github.com/stamparm/maltrail/blob/master/trails/"
                "static/malware/dcrat.txt"
            ),
            "maltrail-darkgate": (
                "https://github.com/stamparm/maltrail/blob/master/trails/"
                "static/malware/darkgate.txt"
            ),
            "maltrail-darkrat": (
                "https://github.com/stamparm/maltrail/blob/master/trails/"
                "static/malware/darkrat.txt"
            ),
            "blocklistproject-porn": (
                "https://github.com/blocklistproject/Lists"
            ),
            "durablenapkin-scam": (
                "https://github.com/durablenapkin/scamblocklist"
            ),
        },
        "domains": builder.records,
        "notes": textwrap.dedent(
            """
            Партія сформована для покриття всіх шкідливих категорій, включаючи
            фішинг, шкідливе ПЗ, ботнети, шахрайство, пропагандистські ресурси,
            державні сервіси агресора, фінансові установи та допоміжну
            інфраструктуру. Частина записів отримана з відкритих фідів, інші
            зібрані вручну для розширення сегментів, що рідко оновлюються у
            автоматичних джерелах.
            """
        ).strip(),
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    new_domains = builder.domains
    print(f"Зібрано {len(new_domains)} нових доменів")
    # Оновлення основного списку доменів.
    full_list = sorted(set(existing) | set(new_domains))
    DOMAINS_PATH.write_text("\n".join(full_list) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
