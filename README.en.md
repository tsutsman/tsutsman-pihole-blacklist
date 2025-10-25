# Pi-hole Blacklist

This repository ships curated regular expressions and plain-domain blocklists
that focus on infrastructure linked to aggressor states.

## Usage
1. Copy `regex.list` and/or `domains.txt` into `/etc/pihole/` on your
   Pi-hole server.
2. Restart the Pi-hole service:
   ```bash
   pihole restartdns
   ```

## Automation
- `python scripts/check_lists.py [--catalog data/catalog.json] [--false-positives data/false_positives.json] [--check-dns] [--require-metadata {domains,regexes,all}]` — verifies syntax, duplicates, overlaps, and catalog coverage, optionally enforcing metadata presence and checking DNS resolution for entries labelled `monitor`.
- `python scripts/validate_catalog.py [--catalog data/catalog.json] [--policy data/inclusion_policy.json]` — ensures catalog metadata meets inclusion policy requirements (see [docs/criteria.md](docs/criteria.md)).
- `python scripts/audit_lists.py [--output reports/audit.json]` — produces a JSON audit of the lists, metadata coverage, and catalog entries that have no matching list entry.
- `python scripts/generate_lists.py [--dist-dir DIR] [--formats adguard ublock hosts rpz dnsmasq unbound] [--group-by category|region|source] [--categories ...] [--regions ...] [--severities ...] [--tags ...]` — builds lists in multiple formats, optionally segmented by category, region, or source, allows filtering by severity and tags, and stores grouped results under `dist/segments/`.
- `python scripts/update_domains.py [--chunk-size N] [--dest FILE] [--config data/sources.json] [--report reports/latest_update.json] [--status data/domain_status.json]` — downloads domains in parallel using both source weight and trust factors, enforces `sla_days` windows (skipping feeds with `auto_disable_on_sla`), generates update reports, and keeps an observation history.
- `python scripts/diff_reports.py PREVIOUS CURRENT [--output FILE]` — compares two update JSON reports (e.g. `reports/latest_update.json`) and builds a diff for release notes and history tracking.

## Metadata and Reporting
- `data/catalog.json` describes categories, regions, sources, statuses, and optional confidence levels for key domains and regexes. Entries missing metadata are grouped into the `no-metadata` segment.
- `data/sources.json` defines domain sources with weights, trust multipliers, SLA expectations (`sla_days`), and `auto_disable_on_sla` flags so stale feeds can be skipped automatically without code changes.
- `data/domain_status.json` stores when domains last appeared in the feeds and whether they remain `active`, became `stale`, or were `removed`.
- `reports/latest_update.json` captures domains added during the most recent update, highlights potentially outdated entries, lists source health diagnostics (`source_health`), skipped feeds (`skipped_sources`), and flags fetch errors when they occur.
- Segmented outputs created by `generate_lists.py` live under `dist/segments/`.

## Malicious Domain Categories
The metadata catalog covers a broad set of thematic groups used to segment the
lists:

- **anonymizers** — VPN and proxy services that hide malicious traffic.
- **botnet** — command-and-control infrastructure for compromised devices.
- **government** — platforms run by aggressor-state institutions and affiliates.
- **ecosystem** — large digital platforms that expose hostile infrastructure.
- **adult-content** — unwanted adult material blocked for safety reasons.
- **crypto-fraud** — phishing and scams disguised as cryptocurrency projects.
- **cryptomining** — services that push mining workloads without consent.
- **propaganda** — state-backed media amplifying hostile narratives.
- **finance** — banks and financial operators tied to aggressor interests.
- **phishing** — impersonation domains stealing credentials.
- **fraud** — non-crypto social-engineering and financial scams.
- **malware** — sites distributing malicious software and tooling.
- **espionage** — telemetry collection and surveillance endpoints.
- **infrastructure** — supporting services such as DNS, CDN, or hosting.

## Domain Sources
`update_domains.py` relies on maintained public feeds:
- [URLhaus](https://urlhaus.abuse.ch/)
- [Phishing Army](https://phishing.army/)
- [StevenBlack/hosts](https://github.com/StevenBlack/hosts)
- [AnudeepND/blacklist](https://github.com/anudeepND/blacklist) — advertising and tracking domains
- [Phishing.Database](https://github.com/mitchellkrogza/Phishing.Database) — phishing domains
- [StevenBlack/hosts (gambling-only)](https://github.com/StevenBlack/hosts/tree/master/alternates/gambling-only) — gambling domains
- [Firebog/Prigent-Malware](https://v.firebog.net/hosts/Prigent-Malware.txt) — malware-related domains
- [Firebog/Prigent-Crypto](https://v.firebog.net/hosts/Prigent-Crypto.txt) — cryptocurrency scam domains
- [PolishFiltersTeam/KADhosts](https://raw.githubusercontent.com/PolishFiltersTeam/KADhosts/master/KADhosts.txt) — phishing and scam list
- [Spam404 Project](https://raw.githubusercontent.com/Spam404/lists/master/main-blacklist.txt) — phishing infrastructure
- [malware-filter/malware-filter-hosts](https://malware-filter.gitlab.io/malware-filter/malware-filter-hosts.txt) — aggregated malware domains
- [malware-filter/phishing-filter-hosts](https://malware-filter.gitlab.io/malware-filter/phishing-filter-hosts.txt) — active phishing domains
- [Hagezi DNS Blocklists (malicious)](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/hosts/malicious.txt) — verified malicious hosts
- [BlocklistProject/malware](https://raw.githubusercontent.com/blocklistproject/Lists/master/malware.txt) — general malware activity
- [BlocklistProject/phishing](https://raw.githubusercontent.com/blocklistproject/Lists/master/phishing.txt) — emerging phishing campaigns
- [DigitalSide Threat-Intel](https://osint.digitalside.it/Threat-Intel/lists/latestdomains.txt) — active malware-campaign domains
- [ThreatView High-Confidence Domain Feed](https://threatview.io/Downloads/DOMAIN-High-Confidence-Feed.txt) — high-confidence malicious domains
- [ThreatFox Hostfile](https://threatfox.abuse.ch/downloads/hostfile/) — abuse.ch ThreatFox domains
- [CriticalPathSecurity Zeus Bad Domains](https://raw.githubusercontent.com/CriticalPathSecurity/ZeusBadDomains/master/baddomains.txt) — Zeus banking trojan domains

## CI
- The GitHub Actions workflow `.github/workflows/ci.yml` runs weekly syntax checks, pytest suites, and blocklist generation for AdGuard, uBlock, and hosts formats.
- Pull requests must pass CI to ensure updated metadata and scripts keep the pipeline stable.
- Tests collect coverage with `coverage.py` and fail the build if coverage drops below 85%.
- Static analysis includes `pip-audit --strict` for dependency vulnerabilities and `bandit -r scripts -ll` for security linting.

## Contributing
1. Fork the repository and create a feature branch.
2. Run `pre-commit run --all-files` before committing.
3. Add or update tests for any logic changes, then run `pytest`.
4. In pull requests describe the evidence or rationale for each new domain.

## Inclusion Policy and Metadata Requirements

### Mandatory Steps Before a PR
- Ensure each domain or regex has at least one reliable source listed in `data/sources.json` or a documented incident. Include references in the PR description and in the catalog `sources` field.
- Run `python scripts/check_lists.py --require-metadata all` and paste successful output (syntax, duplicates, statuses) into the PR description.
- For feeds imported from external projects, add a `notes` entry with the acquisition date and potential false-positive risk.

### Catalog Metadata Requirements
- `data/catalog.json` must capture `category`, `regions`, `sources`, and `status` for active entries. Add `confidence` and `last_seen` when useful.
- List specific regions or campaigns in the `regions` array along with a short explanation.
- For regular expressions add representative matches in `samples` to help reviewers understand the scope.

### Rejection and Quality Control
- Entries lacking strong evidence or with high false-positive risk are deferred until more proof is gathered.
- If complaints arise after adding a domain, append an object to `data/false_positives.json` documenting the scenario and recommended rollback.
- Controversial cases should include validation logs (`scripts/validate_catalog.py`, DNS lookups, screenshots) and an impact assessment in the PR.

### Updating Reports and Artifacts
- After modifying lists, run `python scripts/generate_lists.py` to refresh segments and attach checksums to the PR or CI artifacts.
- Update relevant files in `reports/` (such as `reports/latest_update.json`, `reports/audit.json`) to keep metrics current.
- Mention new domains, sources, and potential risks in the release changelog to keep users informed.

### Handling False Positives and Quick Rollbacks
- `data/false_positives.json` uses structured objects with `reason`, `reported_by`, `reported_at`, `review_status`, `action`, `notes`, and `evidence` arrays to track reports.
- Use `python scripts/rollback_false_positives.py --output-dir dist/rollback` for immediate removal of verified false positives. The script produces updated `domains.txt`, `regex.list`, and `summary.json` with details about excluded and pending entries.
- Entries with `action = "exclude"` are removed from generated files, whereas those marked `monitor` stay under observation.
