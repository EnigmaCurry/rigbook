---
name: issue
description: "Create a GitHub issue on the guidebook repo from a description or current conversation context"
allowed-tools: Bash(gh *)
---

# Create GitHub Issue

Create an issue on `EnigmaCurry/guidebook` based on what the user describes or what we're currently working on.

## Arguments

- Free-text description of the issue (optional — if omitted, infer from conversation context).

## Instructions

1. Draft a concise issue title (under 70 characters) and a body with relevant details.
2. If the user provided a description, use that. Otherwise, derive the issue from the current conversation context.
3. Create the issue:
   ```bash
   gh issue create --repo EnigmaCurry/guidebook --title "THE TITLE" --body "THE BODY"
   ```
4. Show the issue URL when done.
