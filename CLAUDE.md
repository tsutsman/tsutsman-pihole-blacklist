# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

This repository maintains curated Pi-hole blocklists (domains and regexes) focused on infrastructure linked to aggressor states. It is a Python-driven automation project with metadata-driven list generation.

## Common commands

Run tasks via helper scripts (cross-platform):

- `./tasks.sh test` or `./tasks.ps1 test` — run pytest suite
- `./tasks.sh lint` or `./tasks.ps1 lint` — run ruff check + bandit
- `./tasks.sh format` or `./tasks.ps1 format` — run ruff format + black
- `./tasks.sh audit` or `./tasks.ps1 audit` — run pip-audit --strict
- `./tasks.sh generate` or `./tasks.ps1 generate` — generate AdGuard, uBlock, and hosts lists

Install dependencies: `pip install -r requirements.txt`

Run a single test: `pytest tests/test_<name>.py -q`

Pre-commit (run before committing): `pre-commit run --all-files`

## Architecture

### Core data files
- `domains.txt` — plain list of blocked domains
- `regex.list` — regex patterns for Pi-hole
- `data/catalog.json` — metadata catalog for domains and regexes (categories, regions, sources, status, severity, tags, notes)
- `data/sources.json` — source configuration with weights, trust factors, SLA windows, and `auto_disable_on_sla` flags
- `data/false_positives.json` — reported false positives with review status and actions
- `data/domain_status.json` — tracks domain lifecycle (`active`, `stale`, `removed`)

### Shared library
`scripts/utils.py` is the central utility module. It defines:
- `EntryMetadata` — dataclass representing metadata for a domain or regex
- `Catalog` — loads and queries `data/catalog.json`, supports filtering by category, region, source, status, severity, tags
- `FalsePositiveRecord` — structured representation of false-positive reports
- `load_entries()`, `load_catalog()`, `load_false_positive_records()` — standard loaders used across scripts

All scripts import from `utils.py` using a fallback pattern that appends the repo root to `sys.path` when run directly.

### Key scripts
- `check_lists.py` — validates syntax, detects duplicates/overlaps between domains and regexes, verifies catalog coverage, optionally checks DNS for `monitor` entries, and can enforce `--require-metadata`
- `validate_catalog.py` — validates catalog entries against `data/inclusion_policy.json` (required fields, allowed values, minimum source count)
- `generate_lists.py` — builds output lists in multiple formats (`adguard`, `ublock`, `hosts`, `rpz`, `dnsmasq`, `unbound`), supports segmentation by category/region/source, writes grouped results to `dist/segments/`
- `update_domains.py` — parallel download from public feeds, weighted merging with trust and SLA enforcement, generates `reports/latest_update.json` and updates `data/domain_status.json`
- `audit_lists.py` — produces `reports/audit.json` with metadata coverage stats and orphaned catalog entries
- `generate_dashboard.py` — aggregates metrics for dashboards into `reports/dashboard.json` with optional history tracking
- `diff_reports.py` — compares two update JSON reports and produces a diff for changelogs
- `rollback_false_positives.py` — generates clean lists excluding confirmed false positives

### Testing
Tests live in `tests/` and mirror script names (`test_<script>.py`). `conftest.py` adds the repo root to `sys.path`. Coverage is configured in `pyproject.toml` with an 85% minimum threshold on `scripts/`.

### CI
GitHub Actions (`.github/workflows/ci.yml`) runs weekly and on PRs:
1. pip-audit --strict
2. bandit -r scripts -ll
3. check_lists.py
4. pytest with coverage (must be >= 85%)
5. generate_lists.py --formats adguard ublock hosts
6. SHA-256 checksums of dist artifacts

## Development notes

- Python 3.11 target. Ruff and Black are both used for formatting (pre-commit runs both).
- `domains.txt` and `regex.list` are lowercase-normalized on load.
- Catalog entries without metadata fall into the `без-метаданих` (no-metadata) segment.
- When modifying scripts, update the corresponding `tests/test_<script>.py` and run `./tasks.sh test`.
- When adding domains or regexes, update `data/catalog.json` with required metadata and run `check_lists.py --require-metadata all` before committing.
- False positives with `action = "exclude"` are removed from generated outputs; those with `action = "monitor"` are kept for observation.
