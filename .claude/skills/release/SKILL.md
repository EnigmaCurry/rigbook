---
name: release
description: "Release a new version: bump version, generate changelog, tag, and push"
allowed-tools: Bash(git *, uv *, cd *), Read, Edit, Write, AskUserQuestion
---

# Release New Version

## Arguments

- `NEW_VERSION` — the version to release (e.g. `v0.3.0`). Strip any leading `v` for pyproject.toml (e.g. `0.3.0`).

## Instructions

1. **Verify branch and pull latest:**
   ```bash
   git branch --show-current
   ```
   If not on `master`, abort with an error. Then pull:
   ```bash
   git pull
   ```

2. **Run tests — abort if any fail:**
   ```bash
   uv run pytest
   ```

3. **Parse current version from pyproject.toml:**
   Read `pyproject.toml` and extract the current `version` value.

4. **Bump version in pyproject.toml:**
   Edit `pyproject.toml` to set the new version (without the `v` prefix).

5. **Rebuild uv.lock:**
   ```bash
   uv lock
   ```

6. **Analyze git history since last release:**
   ```bash
   git log --oneline v{OLD_VERSION}..HEAD
   ```
   (Use the old version tag. If the tag doesn't exist, use `git log --oneline` with a reasonable range.)

7. **Write CHANGELOG.txt entry:**
   - Read `CHANGELOG.txt` if it exists.
   - Prepend a new entry at the top of the file with this format:
     ```
     ## v{NEW_VERSION} — {YYYY-MM-DD}

     - Brief, user-facing summary of changes (new features, fixes, improvements)
     - One bullet per logical change
     - Skip internal refactors, CI tweaks, and dev-only changes unless significant

     ```
   - Keep entries concise — focus on what a user would care about.

8. **Show the new CHANGELOG entry and ask the user to confirm:**
   Display the new entry text and ask: "Does this changelog look good? Ready to tag and push?"
   Wait for confirmation before proceeding. If the user wants edits, make them and re-confirm.

9. **Commit, tag, and push:**
   ```bash
   git add pyproject.toml uv.lock CHANGELOG.txt
   git commit -m "Bump version to v{NEW_VERSION} and add changelog"
   git tag v{NEW_VERSION}
   git push
   git push --tags
   ```

10. **Report success** with the new version and tag.
