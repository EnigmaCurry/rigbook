---
name: release-test
description: "Push a tagged release to rigbook-build-test repo and let the workflow build it"
allowed-tools: Bash(git *, gh *, uv *), Read, Edit
---

# Release Test

Push a tagged release to the [rigbook-build-test](https://github.com/EnigmaCurry/rigbook-build-test) repo. The release workflow triggers on tag push (no branch required).

This creates a temporary branch with the version bump, tags it, pushes the commit and tag to the test repo, then cleans up locally.

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

6. **Delete the remote tag if it already exists (ignore errors):**
   ```bash
   git push build-test :refs/tags/{NEW_VERSION} 2>/dev/null || true
   ```

7. **Tag and force push the commit and tag:**
   The workflow needs the tagged commit to exist on the remote. Push the commit to a throwaway branch, then push the tag.
   ```bash
   git tag -f {NEW_VERSION}
   git push --force build-test HEAD:refs/heads/build-test-temp
   git push --force build-test {NEW_VERSION}
   ```

8. **Switch back to the original branch and delete the temporary branch:**
   ```bash
   git checkout {ORIGINAL_BRANCH}
   git branch -D build-test-temp
   ```

9. **Clean up the local tag** (only if it didn't exist before step 3):
   ```bash
   git tag -d {NEW_VERSION}
   ```

10. **Watch the GitHub Actions build in the background:**
    The workflow will create the GitHub release automatically.
    ```bash
    gh run watch $(gh run list --repo EnigmaCurry/rigbook-build-test --limit 1 --json databaseId -q '.[0].databaseId') --repo EnigmaCurry/rigbook-build-test
    ```
    Run this with `run_in_background: true` so the user isn't blocked. When notified of completion, report the build result.

11. **Report success** with the version and a link to the build-test repo's actions page.
