# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Coding Guidelines

Always apply [Karpathy Guidelines](~/.agents/skills/karpathy-guidelines/SKILL.md):
1. **Think Before Coding** — State assumptions, surface tradeoffs, ask when unclear.
2. **Simplicity First** — Minimum code, no speculative features, no premature abstractions.
3. **Surgical Changes** — Touch only what's needed, match existing style, clean up only your own mess.
4. **Goal-Driven Execution** — Define verifiable success criteria, loop until verified.

## Repository structure

This is a multi-project workspace. Each subdirectory is an independent project with its own tech stack and git remote:

| Directory | Description | Remote |
|-----------|-------------|--------|
| `sales-assistant/` | React + Vite SPA, sales CRM with country pricing & quotation | `longmingYZR/sales-assistant` |
| `sales-map/` | Single-page geocoding + Leaflet map tool | (part of outer repo) |
| `first-cc/` | Pomodoro timer utility | `longmingYZR/pomodoro-timer` |
| `Invesment agent/` | Python investment monitoring agent | — |
| `voice-transcribe/` | Audio transcription utility | — |

## Push discipline

Each sub-project pushes to its own remote. Always `cd` into the project directory and verify with `git remote -v` before pushing.
