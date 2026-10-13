# CLAUDE.md — Hướng dẫn cho AI Agent

## Mục đích repo này

Đây là kết quả audit UI/UX + Technical SEO cho 13 crypto sites.
Mỗi site có điểm số, danh sách lỗi ưu tiên, và screenshots.
**Nhiệm vụ của bạn:** Đọc issues, rồi vào từng website để fix code.

## Cách đọc dữ liệu

```
sites/<domain>/
├── audit-YYYY-MM-DD.md   # Báo cáo đầy đủ (đọc cái này trước)
├── issues.json            # Danh sách lỗi có priority + fix hướng dẫn
├── scorecard.json         # Điểm từng hạng mục
└── screenshots/           # Ảnh chụp desktop + mobile
```

## Priority thứ tự fix

1. `critical` — fix ngay, ảnh hưởng traffic lớn
2. `high` — fix trong sprint này
3. `medium` — backlog
4. `low` — nice-to-have

## Lỗi phổ biến nhất (critical across all sites)

| Lỗi | Ảnh hưởng | Fix |
|-----|-----------|-----|
| OG Image missing | CTR social -40-60% | Add `<meta property="og:image" content="...1200x630...">` |
| NewsArticle JSON-LD missing | Không có Google News rich result | Add `<script type="application/ld+json">{"@type":"NewsArticle"...}</script>` |
| No llms.txt | AI bots không index → mất GEO | Tạo `/llms.txt` theo format llms.txt spec |
| CSP header missing | Security risk | Add `Content-Security-Policy` header ở server/nginx |
| No author page | E-E-A-T thấp | Tạo `/author/<name>` pages với bio + photo |

## Cách dùng repo này để fix

### Bước 1 — Chọn site cần fix
```
Đọc README.md → xem leaderboard → chọn site điểm thấp nhất
```

### Bước 2 — Đọc issues.json của site đó
```json
// Mỗi issue có structure:
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

### Bước 3 — Vào repo code của site đó để fix

Mỗi site dùng WordPress/Next.js/static. Fix theo `fix` field trong issues.json.

### Bước 4 — Verify sau khi fix

Re-run audit để confirm điểm tăng:
```bash
cd C:\Users\admin\AppData\Local\Temp\audit-web-14-sites
python tools/audit_site.py https://<domain> --proxy 103.82.22.77:28718:1ke2:1ke2 --push
```

## Leaderboard tóm tắt (để biết site nào cần fix nhất)

| Site | Score | Điểm yếu nhất |
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

## Lưu ý kỹ thuật

- Proxy: `103.82.22.77:28718` (user: `1ke2`, pass: `1ke2`)
- Tinyfish API: `sk-tinyfish-4XtV65QCqzoU1fs3tGF-RSIWrrX-9M84`
- Audit script: `tools/audit_site.py`
- Re-audit sau fix: `python tools/audit_site.py https://<domain> --proxy ... --push`
