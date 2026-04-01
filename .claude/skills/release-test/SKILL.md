---
name: release-test
description: "Push a tagged release to rigbook-build-test repo and let the workflow build it"
allowed-tools: Bash(git *, gh *, uv *, python *), Read, Edit
---

# Release Test

Push a tagged release to the [rigbook-build-test](https://github.com/EnigmaCurry/rigbook-build-test) repo. The release workflow triggers on tag push (no branch required).

This creates a temporary branch with the version bump, tags it, pushes the commit and tag to the test repo, then cleans up locally.

## Version Numbering

The version is determined automatically:

1. Read the base version from `pyproject.toml` (e.g. `0.2.7`).
2. Query existing releases on `EnigmaCurry/rigbook-build-test` for tags matching `v{BASE_VERSION}.dev*`.
3. Find the highest `.devN` suffix and increment it. If none exist, start at `.dev0`.
4. The resulting `NEW_VERSION` tag is e.g. `v0.2.7.dev0`, `v0.2.7.dev1`, etc.
5. The pyproject.toml version is set to the version without the `v` prefix (e.g. `0.2.7.dev1`).

## Instructions

1. **Read the base version from pyproject.toml:**
   ```bash
   python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
   ```

2. **Determine the next dev version:**
   ```bash
   gh release list --repo EnigmaCurry/rigbook-build-test --json tagName --limit 100 --jq '.[].tagName'
   ```
   Filter for tags matching `v{BASE_VERSION}.dev*`, extract the numeric suffix, find the max, and add 1. If no matches, use `dev0`. Set `NEW_VERSION=v{BASE_VERSION}.dev{N}` and `PYPROJECT_VERSION={BASE_VERSION}.dev{N}`.

3. **Tell the user** which version will be built (e.g. "Building test release v0.2.7.dev3").

4. **Ensure the build-test remote exists:**
   ```bash
   git remote get-url build-test 2>/dev/null || git remote add build-test git@deploy-github.com-EnigmaCurry-rigbook-build-test:EnigmaCurry/rigbook-build-test.git
   ```

5. **Save the current branch name:**
   ```bash
   git branch --show-current
   ```

6. **Check if the tag already exists locally** (save this for cleanup later):
   ```bash
   git tag -l {NEW_VERSION}
   ```

7. **Create a temporary branch from the current HEAD:**
   ```bash
   git checkout -b build-test-temp
   ```

8. **Bump version in pyproject.toml** to `{PYPROJECT_VERSION}` and rebuild the lockfile:
   ```bash
   uv lock
   ```
   Then commit:
   ```bash
   git add pyproject.toml uv.lock
   git commit -m "Bump version to {NEW_VERSION}"
   ```

9. **Delete the remote tag if it already exists (ignore errors):**
   ```bash
   git push build-test :refs/tags/{NEW_VERSION} 2>/dev/null || true
   ```

10. **Tag and force push the commit and tag:**
    The workflow needs the tagged commit to exist on the remote. Push the commit to a throwaway branch, then push the tag.
    ```bash
    git tag -f {NEW_VERSION}
    git push --force build-test HEAD:refs/heads/build-test-temp
    git push --force build-test {NEW_VERSION}
    ```

11. **Switch back to the original branch and delete the temporary branch:**
    ```bash
    git checkout {ORIGINAL_BRANCH}
    git branch -D build-test-temp
    ```

12. **Clean up the local tag** (only if it didn't exist before step 6):
    ```bash
    git tag -d {NEW_VERSION}
    ```

13. **Watch the GitHub Actions build in the background:**
    The workflow will create the GitHub release automatically.
    ```bash
    gh run watch $(gh run list --repo EnigmaCurry/rigbook-build-test --limit 1 --json databaseId -q '.[0].databaseId') --repo EnigmaCurry/rigbook-build-test
    ```
    Run this with `run_in_background: true` so the user isn't blocked. When notified of completion, report the build result.

14. **Report success** with the version and a link to the build-test repo's actions page.
