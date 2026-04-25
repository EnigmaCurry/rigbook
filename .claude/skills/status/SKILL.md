---
name: status
description: "Show current branch, working tree status, and any open PR"
disable-model-invocation: true
allowed-tools: Bash(git *, gh *)
---

# Status

Run these commands and report the results briefly:

1. `git branch --show-current`
2. `git status --short`
3. `gh pr list --author @me --state open --repo EnigmaCurry/guidebook --json number,title,url,headRefName,baseRefName`

Report the current branch, any uncommitted changes, and any open PRs. Keep it brief.
