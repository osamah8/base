# Project: the base

This is the base itself: the shared rules, guidance, checks and sync that every project repo starts from and keeps in step with. In a project, this file is rewritten to describe that project.

## Purpose

Hold everything that should be the same in every project, so a change made here reaches all of them.

## Source of truth

The shared rules in `README.md`. The base records no facts about me.

## Own layout

None beyond the shared layout in `README.md`.

## Own rules

- This repository is public; every project built on it is private. Nothing here, in any file or commit message, may include personal information or anything about a particular project. Write examples and commit messages in general terms.
- Keep the base general. A rule that only one project needs goes in that project's `PROJECT.md`.
- Test a change to `scripts/check.py` or the sync workflow in one project before relying on it in all of them.
- Every change here is a change to every project: say in the commit message what projects need to know.

## Own wind-up checks

None beyond `scripts/check.py`.
