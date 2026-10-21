# Contributing

Use Python 3.11+ and uv. Run `uv sync --locked`; Windows draft-adapter checks additionally require `uv sync --locked --extra draft`.

Read the relevant Skill reference and tests. Keep scene decisions separate from execution. Add a failing behavior test, implement the change, then run `uv run python -m unittest discover -s tests -v`.

Use synthetic reproductions. Do not submit customer footage, cached music, tokens, native caches, personal paths or unredacted logs. State OS, Python/toolkit/Jianying versions and actual tested scope. A preview is not a native export.

Backends must declare supported fields and reject unsupported behavior. Do not silently drop transitions, crop, speed or audio. Preserve existing drafts and released assets. Skill changes should include cross-scenario checks.

See [release procedure](docs/releasing.md). The repository is the source of truth; installed Skills and released ZIPs are snapshots.
