# Blocklist Audit

The `scripts/audit_lists.py` helper captures the current state of the domain and
regex blocklists. The generated report includes:

- statistics covering entry counts, duplicates, and metadata coverage;
- a breakdown of statuses present in the catalog;
- catalog entries that are documented but missing from production lists.

## Running the audit

```bash
poetry run python -m scripts.audit_lists --output reports/audit.json
```

Options:

- `--domains` and `--regex` provide alternate input files;
- `--catalog` selects the metadata catalog path;
- `--output` specifies the JSON output file in addition to STDOUT.

The JSON report exposes `domains`, `regexes`, and `catalog` keys with summary
counters, duplicate lists, and entries lacking metadata.
