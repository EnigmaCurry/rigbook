---
name: release-test
description: "Force push current branch to rigbook-build-test repo, tag it, and let the workflow create the release"
allowed-tools: Bash(git *, gh *, uv *), Read, Edit
---

# Release Test

Force push the current branch to the [rigbook-build-test](https://github.com/EnigmaCurry/rigbook-build-test) repo and create a tagged release there.

This creates a temporary branch with the version bump, pushes and tags it on the test repo, then switches back and deletes the temporary branch.

## Arguments

- `NEW_VERSION` — the version tag to release (e.g. `v0.2.6`). Strip any leading `v` for pyproject.toml (e.g. `0.2.6`).

## Instructions

1. **Ensure the build-test remote exists:**
   ```bash
   git remote get-url build-test 2>/dev/null || git remote add build-test git@deploy-github.com-EnigmaCurry-rigbook-build-test:EnigmaCurry/rigbook-build-test.git
   ```

2. **Save the current branch name:**
   ```bash
   git branch --show-current
   ```

3. **Check if the tag already exists locally** (save this for cleanup later):
   ```bash
   git tag -l {NEW_VERSION}
   ```

4. **Create a temporary branch from the current HEAD:**
   ```bash
   git checkout -b build-test-temp
   ```

5. **Bump version in pyproject.toml** to the new version (without `v` prefix) and rebuild the lockfile:
   ```bash
   uv lock
   ```
   Then commit:
   ```bash
   git add pyproject.toml uv.lock
   git commit -m "Bump version to {NEW_VERSION}"
   ```

6. **Force push to build-test master:**
   ```bash
   git push --force build-test HEAD:master
   ```

7. **Delete the remote tag if it already exists (ignore errors):**
   ```bash
   git push build-test :refs/tags/{NEW_VERSION} 2>/dev/null || true
   ```

8. **Create and push the tag:**
   ```bash
   git tag -f {NEW_VERSION}
   git push build-test {NEW_VERSION}
   ```

9. **Switch back to the original branch and delete the temporary branch:**
   ```bash
   git checkout {ORIGINAL_BRANCH}
   git branch -D build-test-temp
   ```

10. **Clean up the local tag** (only if it didn't exist before step 3):
    ```bash
    git tag -d {NEW_VERSION}
    ```

11. **Watch the GitHub Actions build in the background:**
    The workflow will create the GitHub release automatically.
    ```bash
    gh run watch $(gh run list --repo EnigmaCurry/rigbook-build-test --limit 1 --json databaseId -q '.[0].databaseId') --repo EnigmaCurry/rigbook-build-test
    ```
    Run this with `run_in_background: true` so the user isn't blocked. When notified of completion, report the build result.

12. **Report success** with the version and a link to the build-test repo's actions page.
