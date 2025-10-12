# Inclusion criteria for domains and regular expressions

This document defines the common rules that govern which domains and regex
entries appear in the metadata catalog and production lists. Compliance is
validated by `python scripts/validate_catalog.py`.

## Baseline requirements

1. **Threat justification.** Each catalog entry must include a category, threat
   level, and at least one source that confirms why the domain or regex should
   be blocked.
2. **Origin transparency.** The `added` field stores the ISO 8601 date when the
   entry was introduced into the catalog.
3. **Geographic relevance.** All listed regions must belong to the allowed
   values (`global`, `ru`, `cis` for domains and `ru`, `by` for regexes).
4. **Status and notes.** When the `status` differs from `active`, the `notes`
   field must include an explanation.

## Inclusion policy

`data/inclusion_policy.json` describes:

- the required fields for domains and regexes;
- allowed values for categories, regions, statuses, and severity levels;
- the minimum number of evidence sources for each entry;
- additional conditions (for example, requiring notes for inactive entries).

The policy can be extended by introducing new categories or additional checks.
Modify `inclusion_policy.json` and update the README if the rules change
significantly.

## Automatic validation

Running `validate_catalog.py` verifies catalog compliance and returns a non-zero
exit code when the policy is violated. Examples:

```bash
python scripts/validate_catalog.py
python scripts/validate_catalog.py --catalog alternate_catalog.json \
    --policy custom_policy.json
```

Integrate the results into CI to prevent catalog updates without the required
metadata or with invalid values.
