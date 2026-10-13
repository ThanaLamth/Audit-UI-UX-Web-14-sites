# CLAUDE.md — Instructions for AI Agents Reading This Repo

## Purpose
This repo contains unified website audits (Technical SEO + UI/UX + E-E-A-T + Security + GEO).
When you read this repo, your job is to understand what needs to be fixed on each site.

## How to Navigate

### Step 1 — Get the big picture
Read `README.md` to see which sites have been audited and their overall scores.

### Step 2 — Per-site audit
Each site lives at `sites/<sitename>/`. Read in this order:
1. `scorecard.json` — overall scores per category (0-100)
2. `issues.json` — structured list of all issues with priority + fix instructions
3. `audit-YYYY-MM-DD.md` — full narrative report with context
4. `screenshots/` — visual evidence (reference filenames from issues.json)

### Step 3 — Prioritize work
Issues in `issues.json` are pre-sorted by priority:
- `critical` — fix immediately, blocking SEO/UX
- `high` — fix this sprint
- `medium` — fix this month
- `low` — backlog

## issues.json Schema

```json
{
  "site": "kanalcoin.com",
  "audit_date": "2026-10-13",
  "auditor": "Codex AI",
  "issues": [
    {
      "id": "K-001",
      "priority": "critical",
      "category": "technical_seo | ui_ux | eeat | security | geo",
      "title": "Short title of the issue",
      "location": "URL or page where issue exists",
      "element": "HTML element or section",
      "what": "What is wrong",
      "why": "Why it matters (impact)",
      "fix": "Exact fix instruction",
      "effort": "15min | 1h | 1day | 1week",
      "evidence": "screenshots/filename.png or null"
    }
  ]
}
```

## scorecard.json Schema

```json
{
  "site": "kanalcoin.com",
  "audit_date": "2026-10-13",
  "overall": 70,
  "categories": {
    "technical_seo": { "score": 18, "max": 25, "grade": "B" },
    "performance":   { "score": 20, "max": 20, "grade": "A+" },
    "ui_ux":         { "score": 14, "max": 20, "grade": "C+" },
    "eeat":          { "score": 10, "max": 15, "grade": "C+" },
    "security":      { "score": 8,  "max": 15, "grade": "C" },
    "geo":           { "score": 8,  "max": 15, "grade": "C" }
  }
}
```

## How to Generate Fix Instructions

When asked "what needs to be fixed on site X":
1. Load `sites/X/issues.json`
2. Filter by `priority: critical` first
3. For each issue, output: **[ID] Title** — Fix: `fix field` — Effort: `effort field`
4. Group by category
5. Reference screenshot filename if available

## When a New Audit is Added

The audit script (`tools/audit_site.py`) auto-generates:
- `issues.json`
- `scorecard.json`
- `audit-YYYY-MM-DD.md`
- `screenshots/*.png`

Then pushes to this repo. You will see a new commit with message:
`audit(<sitename>): YYYY-MM-DD — score X/100`

## Notes for Claude
- Do NOT guess fixes — only use data from issues.json
- Screenshots are evidence, not instructions
- `effort` field is realistic estimate — do not promise faster
- If `evidence` is null, the issue was detected via code/headers, not visually
- Priority order: critical > high > medium > low
- Multiple issues can share the same fix (e.g., adding a footer fixes 3 issues at once)
