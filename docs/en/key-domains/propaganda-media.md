# Propaganda and media outlets

> **Note.** The up-to-date set of domains for this category lives in the Ukrainian master list at [README.md#зведений-перелік-ключових-доменів](../../README.md#зведений-перелік-ключових-доменів).
> We intentionally keep a single source of truth to avoid mismatched edits between language versions.

## Scope
- State-controlled or affiliated media amplifying Kremlin narratives.
- Franchise portals or mirrors operated by major propaganda holdings (RT, VGTRK, Komsomolskaya Pravda, Izvestia, etc.).
- News aggregators and opinion hubs that rebroadcast official messaging without disclosure.
- Multimedia and streaming platforms created to promote propaganda content.

## How to contribute
1. Verify that the domain meets the criteria above and collect at least one trustworthy reference (investigation, official statement, OSINT report).
2. Insert the record into the "Зведений перелік ключових доменів" section of `README.md`, keeping alphabetical order.
3. Add a short comment (one or two sentences) that summarises why the domain is blocked and cite the reference in your PR description.
4. Ensure the domain exists in `domains.txt` (automatically generated or manual) and that no conflicting pattern is already present in `regex.list`.
5. Run `python scripts/check_lists.py --require-metadata domains` to validate the catalog before committing.

## Removal or updates
- If a domain no longer fits the criteria (ownership change, shutdown), document it in the PR and delete the entry from the master list.
- For disputed cases, create or update a note in `data/false_positives.json` and tag the domain with `monitor` to preserve context.
- When new localized mirrors appear, add them as separate entries in the alphabetical list with a comment about their origin.
