import asyncio, json, re, os, argparse, subprocess
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).parent.parent

def site_slug(url):
    return re.sub(r"https?://(www\.)?", "", url).rstrip("/").split("/")[0]

def grade(score, mx):
    pct = score / mx * 100
    for t, g in [(90,"A+"),(80,"A"),(70,"B+"),(60,"B"),(50,"C+"),(40,"C")]:
        if pct >= t: return g
    return "D"

async def safe_goto(page, url, wait="load", timeout=40000):
    try: return await page.goto(url, wait_until=wait, timeout=timeout)
    except Exception as e:
        print(f"  WARN: {str(e)[:60]}")
        return None

def open_session(proxy_str=""):
    env = os.environ.copy()
    cmd = ["npx","tinyfish","browser","session","create"]
    if proxy_str:
        parts = proxy_str.split(":")
        if len(parts) == 4:
            cmd += ["--proxy-url", f"http://{parts[0]}:{parts[1]}", "--proxy-username", parts[2]]
            env["TINYFISH_PROXY_PASSWORD"] = parts[3]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return json.loads(r.stdout.strip())["cdp_url"]

async def m1_screenshots(page, target, ss_dir):
    shots = {}
    async def shoot(name, url, scroll=0):
        await safe_goto(page, url, "load", 40000)
        await asyncio.sleep(2)
        if scroll:
            expr = "window.scrollTo(0, document.body.scrollHeight * " + str(scroll) + ")"
            await page.evaluate(expr)
            await asyncio.sleep(1)
        path = str(ss_dir / (name + ".png"))
        await page.screenshot(path=path)
        shots[name] = path
        print(f"  [SS] {name}.png")
    await page.set_viewport_size({"width":1440,"height":900})
    await shoot("01_home_top", target)
    await shoot("02_home_mid", target, 0.5)
    await shoot("03_home_bottom", target, 1.0)
    news_url = await page.evaluate('() => { const a = Array.from(document.querySelectorAll("a[href]")).find(a => /news|blog|articles/i.test(a.href)); return a ? a.href : ""; }')
    if news_url:
        await shoot("04_news", news_url)
        await shoot("05_news_bottom", news_url, 1.0)
    for p in ["/about","/about-us"]:
        r = await safe_goto(page, target+p, "load", 20000)
        if r and r.status == 200:
            await asyncio.sleep(1)
            path = str(ss_dir / "06_about.png")
            await page.screenshot(path=path)
            shots["06_about"] = path
            break
    await page.set_viewport_size({"width":390,"height":844})
    await shoot("07_mobile", target)
    await page.set_viewport_size({"width":1440,"height":900})
    return shots

async def m2_tech(page, target):
    await safe_goto(page, target, "load", 40000)
    await asyncio.sleep(2)
    JS = """() => {
        const qs = s => document.querySelector(s);
        const schemas = Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
            .map(s=>{try{return JSON.parse(s.textContent)}catch(e){return null}}).filter(Boolean);
        return {
            title: document.title, title_len: document.title.length,
            meta_desc: qs('meta[name="description"]')?.content||"",
            meta_desc_len: (qs('meta[name="description"]')?.content||"").length,
            canonical: qs('link[rel="canonical"]')?.href||"",
            og_image: qs('meta[property="og:image"]')?.content||"",
            og_title: qs('meta[property="og:title"]')?.content||"",
            tw_card: qs('meta[name="twitter:card"]')?.content||"",
            lang: document.documentElement.lang||"",
            h1s: Array.from(document.querySelectorAll("h1")).map(e=>e.innerText.trim()),
            schemas_count: schemas.length,
            schema_types: schemas.map(s=>s["@type"]||(s["@graph"]?s["@graph"].map(x=>x["@type"]):"?")),
            imgs_total: document.querySelectorAll("img").length,
            imgs_no_alt: document.querySelectorAll("img:not([alt]),img[alt='']").length,
            has_footer: !!qs("footer,[class*='footer']"),
            has_search: !!qs("input[type='search'],[class*='search'] input"),
            has_nav: !!qs("nav,[role='navigation']"),
        }
    }"""
    return await page.evaluate(JS)

async def m3_perf(page, target):
    await safe_goto(page, target, "load", 40000)
    JS = """() => {
        const nav = performance.getEntriesByType("navigation")[0]||{};
        const paint = {};
        performance.getEntriesByType("paint").forEach(e=>paint[e.name]=Math.round(e.startTime));
        const res = performance.getEntriesByType("resource");
        const slow = res.filter(r=>r.duration>500).map(r=>({n:r.name.split("/").pop().substring(0,40),ms:Math.round(r.duration)}));
        return {fcp_ms: paint["first-contentful-paint"]||0, load_ms: Math.round(nav.loadEventEnd||0),
                resources_total: res.length, slow_resources: slow.slice(0,5),
                has_lazy: document.querySelectorAll("img[loading='lazy']").length>0}
    }"""
    return await page.evaluate(JS)

async def m4_crawl(page, target):
    D = {}
    r = await safe_goto(page, target+"/robots.txt", "load", 20000)
    robots = await page.inner_text("body") if (r and r.status==200) else ""
    D["robots_status"] = r.status if r else 404
    D["sitemap_url"] = ""
    for line in robots.splitlines():
        if line.lower().startswith("sitemap:"):
            D["sitemap_url"] = line.split(":",1)[1].strip(); break
    if D["sitemap_url"]:
        await safe_goto(page, D["sitemap_url"], "load", 20000)
        sm = await page.content()
        locs = re.findall(r"<loc>(.*?)</loc>", sm)
        D["sitemap_children"] = len(locs)
        if locs:
            await safe_goto(page, locs[0], "load", 20000)
            D["sitemap_first_child_urls"] = (await page.content()).count("<loc>")
    D["ai_bots"] = {"GPTBot":"GPTBot" in robots,"ClaudeBot":"ClaudeBot" in robots,
                    "PerplexityBot":"PerplexityBot" in robots,"Google-Extended":"Google-Extended" in robots}
    r2 = await safe_goto(page, target+"/llms.txt", "load", 10000)
    D["llms_txt_status"] = r2.status if r2 else 404
    r3 = await safe_goto(page, target, "load", 30000)
    h = r3.headers if r3 else {}
    D["security_headers"] = {
        "hsts": h.get("strict-transport-security","MISSING"),
        "csp": "PRESENT" if h.get("content-security-policy") else "MISSING",
        "x_frame_options": h.get("x-frame-options","MISSING"),
        "x_content_type": h.get("x-content-type-options","MISSING"),
        "referrer_policy": h.get("referrer-policy","MISSING"),
        "server": h.get("server","hidden"),
    }
    trust_map = {"about":["/about","/about-us"],"editorial":["/editorial-policy"],
                 "team":["/our-team","/team"],"contact":["/contact"],"privacy":["/privacy-policy"]}
    trust = {}
    for name, paths in trust_map.items():
        for path in paths:
            rr = await safe_goto(page, target+path, "load", 15000)
            if rr and rr.status==200:
                trust[name] = {"status":200,"url":target+path}; break
        if name not in trust: trust[name] = {"status":404}
    D["trust_pages"] = trust
    return D

async def m5_article(page, target, sitemap_url=""):
    article_url = ""
    if sitemap_url:
        await safe_goto(page, sitemap_url, "load", 20000)
        sm = await page.content()
        for loc in re.findall(r"<loc>(.*?)</loc>", sm):
            if "news" in loc.lower() or "post" in loc.lower():
                await safe_goto(page, loc, "load", 20000)
                child = await page.content()
                arts = [u for u in re.findall(r"<loc>(.*?)</loc>", child)
                        if u.count("/")>=4 and not re.search(r"tool|category|tag|author|page",u)]
                if arts: article_url = arts[0]; break
    if not article_url:
        await safe_goto(page, target, "load", 40000)
        await asyncio.sleep(2)
        article_url = await page.evaluate('() => { const links = Array.from(document.querySelectorAll("a[href]")).map(a=>a.href).filter(h=>h.includes(location.hostname)&&h.split("/").filter(Boolean).length>=4&&!h.includes("#")&&!/tool|category|tag|author/.test(h)); return links[0]||""; }')
    if not article_url: return {"error":"no article found"}
    await safe_goto(page, article_url, "load", 45000)
    await asyncio.sleep(2)
    JS = """() => {
        const schemas = Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
            .map(s=>{try{return JSON.parse(s.textContent)}catch(e){return null}}).filter(Boolean);
        let artS = null;
        schemas.forEach(s=>{
            if(["Article","NewsArticle","BlogPosting"].includes(s["@type"])) artS=s;
            if(s["@graph"]) s["@graph"].forEach(g=>{if(["Article","NewsArticle","BlogPosting"].includes(g["@type"])) artS=g;});
        });
        const bodyEl = document.querySelector("article,[class*='article-body'],[class*='post-content'],[class*='entry-content']");
        const wc = (bodyEl?bodyEl.innerText:document.body.innerText).trim().split(/\s+/).filter(w=>w.length>0).length;
        const host = location.hostname;
        return {
            url: location.href, title: document.querySelector("h1")?.innerText?.trim()||"",
            word_count: wc,
            internal_links: Array.from(document.querySelectorAll("a[href]")).filter(a=>a.href.includes(host)).length,
            external_links: Array.from(document.querySelectorAll("a[href]")).filter(a=>a.href.startsWith("http")&&!a.href.includes(host)).length,
            schema_types: schemas.map(s=>s["@type"]||(s["@graph"]?s["@graph"].map(x=>x["@type"]):"?")),
            schema_article: artS?.["@type"]||"MISSING",
            schema_author: artS?.author?.name||"MISSING",
            schema_date_pub: artS?.datePublished||"MISSING",
            schema_date_mod: artS?.dateModified||"MISSING",
            schema_image: artS?.image?"YES":"MISSING",
            author_visible: (document.querySelector("[class*='author'],[rel='author']")?.innerText||"").trim().substring(0,80),
            author_link: document.querySelector("a[href*='/author/']")?.href||"",
            breadcrumb: (document.querySelector("[class*='breadcrumb']")?.innerText||"").trim().substring(0,200),
            toc: !!document.querySelector("[class*='toc'],[id*='toc']"),
            faq: !!document.querySelector("[class*='faq'],[id*='faq']"),
            h2_count: document.querySelectorAll("h2").length,
            og_image: document.querySelector("meta[property='og:image']")?.content||"MISSING",
            related_posts: document.querySelectorAll("[class*='related'] a").length,
        }
    }"""
    return await page.evaluate(JS)

def score_all(tech, perf, crawl, article):
    S = {}
    flat = str(tech.get("schema_types",""))
    t = 0
    if tech.get("title") and 30<=tech.get("title_len",0)<=65: t+=3
    elif tech.get("title"): t+=1
    if tech.get("meta_desc") and 100<=tech.get("meta_desc_len",0)<=160: t+=3
    elif tech.get("meta_desc"): t+=1
    if tech.get("og_image"): t+=3
    if tech.get("og_title"): t+=1
    if tech.get("tw_card"): t+=1
    if tech.get("canonical"): t+=2
    if tech.get("lang"): t+=1
    if "NewsArticle" in flat or "Article" in flat: t+=3
    if "Organization" in flat or "WebSite" in flat: t+=2
    if tech.get("imgs_no_alt",99)==0: t+=2
    S["technical_seo"] = {"score":min(t,25),"max":25}
    fcp=perf.get("fcp_ms",9999); ld=perf.get("load_ms",9999)
    p = 0
    if fcp<1000: p+=7
    elif fcp<2500: p+=4
    elif fcp<4000: p+=2
    if ld<2000: p+=6
    elif ld<4000: p+=3
    if perf.get("has_lazy"): p+=2
    if perf.get("resources_total",999)<150: p+=3
    S["performance"] = {"score":min(p,20),"max":20}
    u = 0
    if tech.get("has_footer"): u+=5
    if tech.get("has_search"): u+=4
    if tech.get("has_nav"): u+=3
    wc=article.get("word_count",0)
    if wc>=1000: u+=3
    elif wc>=600: u+=2
    if article.get("toc"): u+=2
    if article.get("related_posts",0)>0: u+=2
    if article.get("breadcrumb"): u+=1
    S["ui_ux"] = {"score":min(u,20),"max":20}
    e = 0
    if article.get("author_visible"): e+=3
    if article.get("author_link"): e+=2
    if article.get("schema_author") not in ("MISSING",""): e+=2
    if article.get("schema_article") not in ("MISSING",""): e+=2
    if article.get("schema_image")=="YES": e+=1
    if article.get("faq"): e+=2
    if article.get("external_links",0)>2: e+=2
    if article.get("og_image") and article.get("og_image")!="MISSING": e+=1
    S["eeat"] = {"score":min(e,15),"max":15}
    sec=crawl.get("security_headers",{})
    s = 0
    if sec.get("hsts")!="MISSING": s+=3
    if sec.get("csp")=="PRESENT": s+=3
    if sec.get("x_frame_options")!="MISSING": s+=1
    if sec.get("x_content_type")!="MISSING": s+=1
    if sec.get("referrer_policy")!="MISSING": s+=1
    S["security"] = {"score":min(s,10),"max":10}
    g = sum(1 for v in crawl.get("ai_bots",{}).values() if v)
    if crawl.get("llms_txt_status")==200: g+=3
    if crawl.get("sitemap_url"): g+=1
    if article.get("faq"): g+=1
    S["geo"] = {"score":min(g,10),"max":10}
    S["overall"] = sum(v["score"] for v in S.values())
    S["max"] = sum(v["max"] for v in S.values())
    for v in S.values():
        if isinstance(v,dict) and "score" in v: v["grade"]=grade(v["score"],v["max"])
    return S

def build_issues(tech, perf, crawl, article, shots):
    issues=[]; counter=[0]
    slug=tech.get("_site","XX"); base=tech.get("_base","")
    code=(slug[:2].upper() if len(slug)>=2 else "XX")
    def iss(pri,cat,title,loc,el,what,why,fix,effort,ev=None):
        counter[0]+=1
        issues.append({"id":f"{code}-{counter[0]:03d}","priority":pri,"category":cat,
            "title":title,"location":loc,"element":el,"what":what,"why":why,
            "fix":fix,"effort":effort,"evidence":Path(ev).name if ev else None})
    if not tech.get("og_image"):
        iss("critical","technical_seo","OG Image missing on homepage",base,"head og:image",
            "og:image tag absent","No social share preview — CTR -40-60%",
            "Add meta property og:image 1200x630px to homepage head","30min",shots.get("01_home_top"))
    if not tech.get("has_footer"):
        iss("critical","ui_ux","Footer completely missing",base,"body",
            "No footer element","No copyright/privacy/sitemap — fails E-E-A-T",
            "Add footer: copyright, privacy policy, terms, contact, sitemap","1day",shots.get("03_home_bottom"))
    if crawl.get("llms_txt_status")!=200:
        iss("high","geo","llms.txt missing",base+"/llms.txt","site root",
            "/llms.txt 404","AI agents cannot discover site","Create /llms.txt per llmstxt.org spec","1h")
    sec=crawl.get("security_headers",{})
    if sec.get("hsts")=="MISSING":
        iss("high","security","HSTS header missing",base,"HTTP Headers",
            "HSTS not set","SSL stripping vulnerability",
            "Cloudflare SSL/TLS Edge Certs: Enable HSTS max-age=31536000","5min")
    if sec.get("csp")=="MISSING":
        iss("medium","security","CSP header missing",base,"HTTP Headers",
            "CSP not present","XSS vulnerability",
            "Add Content-Security-Policy via Cloudflare Transform Rules","2h")
    if not tech.get("has_search"):
        iss("high","ui_ux","No search bar",base,"Navigation",
            "No search input","High bounce rate","Add search to header nav","1day",shots.get("04_news"))
    if tech.get("imgs_no_alt",0)>0:
        n=tech["imgs_no_alt"]
        iss("medium","technical_seo",f"Images missing alt ({n})",base,"img",
            f"{n} imgs no alt","WCAG + Google image indexing","Add alt text to all images","2h")
    if article.get("schema_article")=="MISSING":
        iss("critical","eeat","Article schema missing",article.get("url",""),"ld+json",
            "No NewsArticle JSON-LD","No rich results, no Google News",
            "Add NewsArticle LD+JSON: headline, author, dates, image, publisher","1day")
    if not article.get("author_visible") and not article.get("author_link"):
        iss("high","eeat","No author attribution",article.get("url",""),"byline",
            "No visible author","E-E-A-T fail for YMYL crypto",
            "Add author byline: name, photo, link to /author/ bio","1day")
    if not article.get("toc"):
        iss("medium","ui_ux","No Table of Contents",article.get("url",""),"article",
            "No TOC on multi-H2 article","Low dwell time, miss SERP sitelinks",
            "Auto-generate TOC from H2/H3 after intro","1day")
    if not article.get("faq"):
        iss("medium","geo","No FAQ section",article.get("url",""),"article",
            "No FAQ or FAQPage schema","Miss PAA boxes in SERP",
            "Add 3-5 QA + FAQPage JSON-LD at end of analysis articles","2h per template")
    wc=article.get("word_count",0)
    if wc<800:
        iss("medium","eeat",f"Low word count ({wc})",article.get("url",""),"body",
            f"Only {wc} words","Thin content","Expand analysis articles to 1000-1500 words","ongoing")
    if article.get("related_posts",0)==0:
        iss("low","ui_ux","No related posts",article.get("url",""),"article bottom",
            "No related articles","High bounce rate","Add 3-4 related cards at bottom","1day")
    order={"critical":0,"high":1,"medium":2,"low":3}
    issues.sort(key=lambda x: order.get(x["priority"],9))
    return issues

def write_report(site_dir, target, date_str, tech, perf, crawl, article, scores, issues, shots):
    L=[]
    L.append(f"# {target} Unified Audit Report")
    L.append(f"**Date:** {date_str}  |  **Auditor:** Codex AI")
    L.append("")
    L.append("## Score Card")
    L.append("| Category | Score | Max | Grade | Status |")
    L.append("|---|---|---|---|---|")
    for k,v in scores.items():
        if not isinstance(v,dict): continue
        st="OK" if v["grade"] in ("A+","A","B+") else ("WARN" if v["grade"] in ("B","C+") else "FAIL")
        cat = k.replace("_"," ").title()
        L.append(f"| {cat} | {v['score']} | {v['max']} | {v['grade']} | {st} |")
    L.append(f"| **OVERALL** | **{scores['overall']}** | **{scores['max']}** | | |")
    L.append("")
    L.append("## Issues Summary")
    by_p={}
    for i in issues: by_p.setdefault(i["priority"],[]).append(i)
    for p2 in ["critical","high","medium","low"]:
        if p2 in by_p: L.append(f"- **{p2.title()}:** {len(by_p[p2])} issues")
    L.append("")
    L.append("## Issues Detail")
    for iss_item in issues:
        L.append(f"")
        L.append(f"### [{iss_item['id']}] {iss_item['title']}  {iss_item['priority'].upper()}")
        L.append(f"- **Category:** {iss_item['category']}")
        L.append(f"- **What:** {iss_item['what']}")
        L.append(f"- **Why:** {iss_item['why']}")
        L.append(f"- **Fix:** {iss_item['fix']}")
        L.append(f"- **Effort:** {iss_item['effort']}")
        if iss_item.get("evidence"): L.append(f"- **Evidence:** screenshots/{iss_item['evidence']}")
    L.append("")
    L.append("## Raw Data")
    L.append(f"- FCP:{perf.get('fcp_ms')}ms  Load:{perf.get('load_ms')}ms  Resources:{perf.get('resources_total')}")
    L.append(f"- Schema homepage: {tech.get('schema_types')}")
    L.append(f"- Footer: {'YES' if tech.get('has_footer') else 'NO'}  Search: {'YES' if tech.get('has_search') else 'NO'}")
    L.append(f"- HSTS:{crawl.get('security_headers',{}).get('hsts')}  CSP:{crawl.get('security_headers',{}).get('csp')}")
    L.append(f"- llms.txt:{crawl.get('llms_txt_status')}  AI bots:{crawl.get('ai_bots')}")
    L.append(f"- Trust pages: { {k:v.get('status') for k,v in crawl.get('trust_pages',{}).items()} }")
    L.append(f"- Article: {article.get('url','')}  words:{article.get('word_count',0)}")
    L.append(f"  Schema:{article.get('schema_article')}  Author:{article.get('author_visible') or 'MISSING'}")
    L.append(f"  TOC:{article.get('toc')}  FAQ:{article.get('faq')}  Related:{article.get('related_posts',0)}")
    L.append("")
    L.append("## Priority Action Plan")
    L.append("| # | Priority | ID | Task | Effort |")
    L.append("|---|---|---|---|---|")
    for i,iss_item in enumerate(issues[:15],1):
        L.append(f"| {i} | {iss_item['priority'].title()} | {iss_item['id']} | {iss_item['title']} | {iss_item['effort']} |")
    out = site_dir / f"audit-{date_str}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    return out

async def audit(target, proxy_str="", push=False):
    target=target.rstrip("/")
    slug=site_slug(target); date_str=datetime.now(timezone.utc).strftime("%Y-%m-%d")
    site_dir=REPO_ROOT/"sites"/slug; ss_dir=site_dir/"screenshots"
    site_dir.mkdir(parents=True,exist_ok=True); ss_dir.mkdir(parents=True,exist_ok=True)
    print(f"Auditing: {target}")
    cdp_url=open_session(proxy_str)
    print(f"Session: {cdp_url}")
    async with async_playwright() as pw:
        browser=await pw.chromium.connect_over_cdp(cdp_url)
        ctx=browser.contexts[0]
        page=ctx.pages[0] if ctx.pages else await ctx.new_page()
        print("[M1] Screenshots..."); shots=await m1_screenshots(page,target,ss_dir)
        print("[M2] Technical SEO..."); tech=await m2_tech(page,target)
        tech["_site"]=slug; tech["_base"]=target
        print("[M3] Performance..."); perf=await m3_perf(page,target)
        print(f"  FCP:{perf.get('fcp_ms')}ms  Load:{perf.get('load_ms')}ms")
        print("[M4] Crawlability+Security+GEO..."); crawl=await m4_crawl(page,target)
        print("[M5] Article audit..."); article=await m5_article(page,target,crawl.get("sitemap_url",""))
        print(f"  Words:{article.get('word_count',0)}  Schema:{article.get('schema_article')}")
    scores=score_all(tech,perf,crawl,article)
    issues=build_issues(tech,perf,crawl,article,shots)
    print(f"Score:{scores['overall']}/{scores['max']}  Issues:{len(issues)}")
    sc={"site":target,"slug":slug,"audit_date":date_str,"overall":scores["overall"],"max":scores["max"],
        "categories":{k:v for k,v in scores.items() if isinstance(v,dict)}}
    (site_dir/"scorecard.json").write_text(json.dumps(sc,indent=2),encoding="utf-8")
    io={"site":target,"slug":slug,"audit_date":date_str,"overall_score":scores["overall"],
        "summary":{p:sum(1 for i in issues if i["priority"]==p) for p in ["critical","high","medium","low"]},
        "issues":issues}
    (site_dir/"issues.json").write_text(json.dumps(io,indent=2,ensure_ascii=False),encoding="utf-8")
    report=write_report(site_dir,target,date_str,tech,perf,crawl,article,scores,issues,shots)
    print(f"Written: {report}")
    if push:
        os.chdir(REPO_ROOT)
        subprocess.run(["git","add",f"sites/{slug}/"],check=True)
        msg = f"audit({slug}): {date_str} score {scores['overall']}/{scores['max']}"
        subprocess.run(["git","commit","-m",msg],check=True)
        subprocess.run(["git","push","origin","main"],check=True)
        print("Pushed!")
    return str(report)

def main():
    parser=argparse.ArgumentParser(description="Unified website audit")
    parser.add_argument("url")
    parser.add_argument("--proxy",default="")
    parser.add_argument("--push",action="store_true")
    args=parser.parse_args()
    asyncio.run(audit(args.url,args.proxy,args.push))

if __name__=="__main__":
    main()
