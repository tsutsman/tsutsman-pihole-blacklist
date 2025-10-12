# Project status analysis

## 1. Mission and context
- The repository centralises domain and regex lists for Pi-hole that target
  infrastructure operated by aggressor states.
- Its value lies in combining manually curated data (`domains.txt`,
  `regex.list`) with automated domain ingestion and rich metadata stored in
  `data/`.

## 2. Repository architecture
### 2.1. Data sources
- `domains.txt` and `regex.list` are the core artifacts consumed directly by
  Pi-hole.
- The `data/` directory contains JSON configuration: `catalog.json` for
  metadata, `sources.json` for source definitions, `domain_status.json` for
  historical sightings, and `false_positives.json` for manual exceptions.
- `reports/` stores execution outputs (e.g. `latest_update.json`) that keep
  changes transparent.

### 2.2. Scripts and business logic
- `scripts/check_lists.py` performs comprehensive validation: syntax, duplicates,
  cross-file overlaps, metadata presence, and optional DNS checks.
- `scripts/update_domains.py` aggregates external sources, manages weights, and
  emits reports about newly added entries.
- `scripts/generate_lists.py` builds AdGuard, uBlock, hosts, and other formats
  while supporting segmentation by category, region, and source.
- `scripts/audit_lists.py` and `scripts/validate_catalog.py` focus on metadata
  coverage and policy compliance.
- Shared utilities in `scripts/utils.py` load entries and metadata with
  consistent filtering and tagging support.

### 2.3. Test infrastructure
- Tests rely on `pytest`; the `tests/` folder mirrors the script structure.
- `tests/test_update_domains.py` mocks source configurations, while
  `tests/test_generate_lists.py` validates segmentation and
  `tests/test_check_lists.py` covers validation scenarios.

### 2.4. Documentation and standards
- `README.md` describes usage, automation tooling, and the list of upstream
  sources.
- Documentation in `docs/` covers inclusion criteria (`criteria.md`), audits
  (`audit.md`), and the catalog of key domains.
- The project roadmap (`docs/roadmap.md`) aligns with the plan presented below.

### 2.5. Automation and CI/CD
- GitHub Actions (`.github/workflows/ci.yml`) runs list checks, unit tests, and
  distribution generation on Python 3.11 for every pull request and weekly.
- `pre-commit` ensures local quality checks run before commits.

## 3. Data and process quality
- Metadata tracks categories, regions, sources, severities, and monitoring flags
  that enable precise segmentation.
- `data/false_positives.json` captures user reports, though there is no automated
  feedback loop.
- Source freshness depends on `data/sources.json`; reviewing reliability and
  weights regularly is critical.
- `reports/latest_update.json` records the latest changes but lacks long-term
  trends and effectiveness metrics.

## 4. Testing and stability
- The full test suite (35 tests) passes on Python 3.12 locally, confirming
  compatibility with the latest interpreter.
- Integration tests for DNS interactions or Pi-hole validation are not yet
  present.
- Coverage metrics are not tracked; adopting `coverage.py` with an ≥80% threshold
  is recommended to meet internal standards.

## 5. Risks and bottlenecks
- Manual metadata maintenance can desynchronise lists and catalog entries if no
  mandatory checks run before releases.
- Lacking a central incident log for false positives complicates triage.
- The current CI pipeline misses dependency security scans and does not store
  generated list artifacts for later verification.
- There is no automated release versioning or changelog generation.

## 6. Growth opportunities
- Expanding catalog tags and trust levels will improve tailored distributions.
- Integrating telemetry or user feedback from Pi-hole deployments will tighten
  false-positive detection.
- Automated correlation with external threat-intel feeds (VirusTotal, AbuseIPDB)
  can prioritise new domains more effectively.
- Containerised Pi-hole environments would enable end-to-end release validation.

## 7. Recommended roadmap (high level)
- Short term: standardise data quality checks, extend test coverage, and
  formalise the release procedure.
- Mid term: automate telemetry collection, build analytics dashboards, and
  launch source trust evaluation.
- Long term: integrate ML/heuristics for threat prediction, deploy resilient
  delivery infrastructure, and expose public APIs.

See `docs/roadmap.md` for the detailed execution plan.
