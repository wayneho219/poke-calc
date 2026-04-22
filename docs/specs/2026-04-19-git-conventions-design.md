# Git Conventions for Claude Code — Design Spec

**Date:** 2026-04-19  
**Scope:** Global (`~/.claude/CLAUDE.md`)

## Overview

Rules that Claude Code must follow when helping with git operations across all projects.

## Rules

### 1. Commit Message Format

Use Conventional Commits: `<type>(<scope>): <description>`

- **Types:** `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`
- `scope` is optional
- Always append co-author line:
  ```
  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  ```

### 2. Branch Naming

- Default branch for all development: **`Wayne-Dev`**
  - Stay on this branch unless a special case arises
  - Never delete `Wayne-Dev`
- For special cases (feature experiments, isolated testing): `<type>/<description>` (e.g. `feat/add-login`)

### 3. Commit / Push Timing

- **Never commit or push automatically**
- Only commit or push when the user explicitly says to

### 4. PR Flow

- Always open a PR — never push directly to `main`
- Default PR target: `Wayne-Dev` → `main`

### 5. .gitignore

- Before the first commit in any project, suggest an appropriate `.gitignore` and wait for user confirmation before proceeding

## Git Identity

- `user.name`: wayneho219
- `user.email`: qazwsx08120219@gmail.com
