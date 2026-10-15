# CLAUDE.md — Hu?ng d?n cho AI Agent

## M?c dích repo này

Ðây là k?t qu? audit UI/UX + Technical SEO cho 14 crypto sites.
M?i site có di?m s?, danh sách l?i uu tiên, và screenshots.
**Nhi?m v? c?a b?n:** Ð?c issues, r?i vào t?ng website d? fix code.

## Cách d?c d? li?u

```
sites/<domain>/
+-- audit-YYYY-MM-DD.md   # Báo cáo d?y d? (d?c cái này tru?c)
+-- issues.json            # Danh sách l?i có priority + fix hu?ng d?n
+-- scorecard.json         # Ði?m t?ng h?ng m?c
+-- screenshots/           # ?nh ch?p desktop + mobile
```

## Priority th? t? fix

1. `critical` — fix ngay, ?nh hu?ng traffic l?n
2. `high` — fix trong sprint này
3. `medium` — backlog
4. `low` — nice-to-have

## L?i ph? bi?n nh?t (critical across all sites)

| L?i | ?nh hu?ng | Fix |
|-----|-----------|-----|
| OG Image missing | CTR social -40-60% | Add `<meta property="og:image" content="...1200x630...">` |
| NewsArticle JSON-LD missing | Không có Google News rich result | Add `<script type="application/ld+json">{"@type":"NewsArticle"...}</script>` |
| No llms.txt | AI bots không index ? m?t GEO | T?o `/llms.txt` theo format llms.txt spec |
| CSP header missing | Security risk | Add `Content-Security-Policy` header ? server/nginx |
| No author page | E-E-A-T th?p | T?o `/author/<name>` pages v?i bio + photo |

## Cách dùng repo này d? fix

### Bu?c 1 — Ch?n site c?n fix
```
Ð?c README.md ? xem leaderboard ? ch?n site di?m th?p nh?t
```

### Bu?c 2 — Ð?c issues.json c?a site dó
```json
// M?i issue có structure:
{
  "id": "XX-001",
  "priority": "critical",
  "category": "technical_seo",
  "title": "OG Image missing on homepage",
  "location": "https://example.com",
  "element": "head og:image",
  "what": "og:image tag absent",
  "why": "No social share preview — CTR -40-60%",
  "fix": "Add meta property og:image 1200x630px to homepage head",
  "effort": "30min",
  "evidence": "01_home_top.png"
}
```

### Bu?c 3 — Vào repo code c?a site dó d? fix

M?i site dùng WordPress/Next.js/static. Fix theo `fix` field trong issues.json.

### Bu?c 4 — Verify sau khi fix

Re-run audit d? confirm di?m tang:
```bash
cd C:\Users\admin\AppData\Local\Temp\audit-web-14-sites
python tools/audit_site.py https://<domain> --proxy 103.82.22.77:28718:1ke2:1ke2 --push
```

## Leaderboard tóm t?t (d? bi?t site nào c?n fix nh?t)

| Site | Score | Ði?m y?u nh?t |
|------|-------|----------------|
| kanalcoin.com | 70/100 | Security (3/10) |
| tokentopnews.com | 69/100 | E-E-A-T (8/15) |
| defiliban.io | 69/100 | Security (3/10) |
| nftenex.com | 65/100 | Tech SEO (13/25) |
| coinlineup.com | 63/100 | E-E-A-T (5/15) |
| theccpress.com | 61/100 | Tech SEO (11/25) |
| aicryptocore.com | 59/100 | UI/UX (8/20) |
| coinwy.com | 59/100 | E-E-A-T (2/15) |
| marketbit.net | 57/100 | E-E-A-T (2/15) |
| trustscrypto.com | 56/100 | UI/UX (8/20) |
| bitcoininfonews.com | 55/100 | GEO (5/10) |
| cryptodailyalert.com | 55/100 | GEO (4/10) |
| coinlive.me | 50/100 | Tech SEO (11/25), E-E-A-T (3/15) |
| coincu.com | 62/100 | Tech SEO (13/25), Security (5/15) |

## Luu ý k? thu?t

- Proxy: `103.82.22.77:28718` (user: `1ke2`, pass: `1ke2`)
- Tinyfish API: `sk-tinyfish-4XtV65QCqzoU1fs3tGF-RSIWrrX-9M84`
- Audit script: `tools/audit_site.py`
- Re-audit sau fix: `python tools/audit_site.py https://<domain> --proxy ... --push`
