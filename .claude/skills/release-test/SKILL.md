---
name: release-test
description: "Push a tagged release to guidebook-build-test repo and let the workflow build it"
allowed-tools: Bash(git *, gh *, uv *, just *), Read, Edit
---

# Release Test

Push a tagged release to the [guidebook-build-test](https://github.com/EnigmaCurry/guidebook-build-test) repo. The release workflow triggers on tag push (no branch required).

This creates a temporary branch with the version bump, tags it, pushes the commit and tag to the test repo, then cleans up locally.

## Version Numbering

Run `just next-dev-version` to get the next version automatically. This reads the base version from `pyproject.toml` and queries existing releases on `EnigmaCurry/guidebook-build-test` to find the next sequential `.devN` suffix.

The result is e.g. `0.2.7.dev0`. The tag uses a `v` prefix: `v0.2.7.dev0`.

## Instructions

1. **Get the next version** and tell the user which version will be built:
   ```bash
   just next-dev-version
   ```
   Set `PYPROJECT_VERSION` to the output (e.g. `0.2.7.dev0`) and `NEW_VERSION` to `v{PYPROJECT_VERSION}`.

2. **Ensure the build-test remote exists:**
   ```bash
   git remote get-url build-test 2>/dev/null || git remote add build-test git@deploy-github.com-EnigmaCurry-guidebook-build-test:EnigmaCurry/guidebook-build-test.git
   ```

3. **Save the current branch name:**
   ```bash
   git branch --show-current
   ```

4. **Check if the tag already exists locally** (save this for cleanup later):
   ```bash
   git tag -l {NEW_VERSION}
   ```

5. **Create a temporary branch from the current HEAD:**
   ```bash
   git checkout -b build-test-temp
   ```

6. **Bump version in pyproject.toml** to `{PYPROJECT_VERSION}` and rebuild the lockfile:
   ```bash
   uv lock
   ```
   Then commit:
   ```bash
   git add pyproject.toml uv.lock
   git commit -m "Bump version to {NEW_VERSION}"
   ```

7. **Delete the remote tag if it already exists (ignore errors):**
   ```bash
   git push build-test :refs/tags/{NEW_VERSION} 2>/dev/null || true
   ```

8. **Tag and force push the commit and tag:**
   The workflow needs the tagged commit to exist on the remote. Push the commit to a throwaway branch, then push the tag.
   ```bash
   git tag -f {NEW_VERSION}
   git push --force build-test HEAD:refs/heads/build-test-temp
   git push --force build-test {NEW_VERSION}
   ```

9. **Switch back to the original branch and delete the temporary branch:**
   ```bash
   git checkout {ORIGINAL_BRANCH}
   git branch -D build-test-temp
   ```

10. **Clean up the local tag** (only if it didn't exist before step 4):
    ```bash
    git tag -d {NEW_VERSION}
    ```

11. **Watch the GitHub Actions build in the background:**
    The workflow will create the GitHub release automatically.
    ```bash
    gh run watch $(gh run list --repo EnigmaCurry/guidebook-build-test --limit 1 --json databaseId -q '.[0].databaseId') --repo EnigmaCurry/guidebook-build-test
    ```
    Run this with `run_in_background: true` so the user isn't blocked. When notified of completion, report the build result.

12. **Report success** with the version and a link to the build-test repo's actions page.
