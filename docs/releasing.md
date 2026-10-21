# Maintainer release procedure

Source is maintained in Git; versioned releases deliver snapshots. This uses the source-install approach of [jianying-local-mcp](https://github.com/Capricornus-joe/jianying-local-mcp), the versioned model of [pyJianYingDraft releases](https://github.com/GuanYixuan/pyJianYingDraft/releases), and [GitHub release guidance](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).

1. Work on a branch. Update pyproject version, CLI/HTML labels, CHANGELOG and `docs/releases/vVERSION.md` together.
2. Run `uv lock`, `uv sync --locked`, tests and `uv run python tools/build_docs.py`. Record optional native checks separately.
3. Run `uv run python tools/package_release.py --out dist`. Existing version artifacts are never overwritten; use a fresh output directory for a repeated build.
4. Review allowlisted public source and archives. Personal introduction copy, environments, outputs, generated media, caches and native files are excluded.
5. Commit source and check CI. Create tag `vVERSION`, use matching release notes and attach both ZIPs plus both manifests. The optional workflow creates a draft, not an automatically public release.
6. Verify the public repository, tag, release and downloads. Preserve old releases and local share packages.

Installed Skill updates are deliberate: compare source, back up changed files, synchronize, and validate. The installer refuses to overwrite an existing directory. YAML existing in the repository does not prove CI or release workflow execution.
