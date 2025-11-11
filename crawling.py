import asyncio, json, time
from pathlib import Path
from collections import deque
from urllib.parse import urlparse, urljoin, urlunparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from playwright.async_api import Page, BrowserContext

# CONFIG
WP_URL      = "http://192.168.64.2/wordpress_instrumented"
LOGIN_URL   = f"{WP_URL}/wp-login.php"
ADMIN_URL   = f"{WP_URL}/wp-admin/"
USERNAME    = "wpuser"
PASSWORD    = "password123!"

OUT_JSONL   = Path("/home/camvm76/crawl4ai/out/crawl4ia_output.jsonl")   # expected base file
HEADLESS    = True
VERBOSE     = True

MAX_PAGES   = 200
MAX_DEPTH   = 5
DELAY_S     = 0.3

# Restrict the scope
BASE_SCOPE  = "http://192.168.64.2/wordpress_instrumented"

# UTILS
def normalize_url(u: str) -> str:
    if not u: return ""
    p = urlparse(u)
    p = p._replace(fragment="")
    return urlunparse(p)

def in_scope(u: str) -> bool:
    return u.startswith(BASE_SCOPE)

def extract_links(obj, base: str):
    links = set()
    if not obj:
        return links
    raw = getattr(obj, "links", None)
    # dict {type: [ {href:...}, ... ]} or list
    if isinstance(raw, dict):
        iters = []
        for _, items in raw.items():
            if items: iters.extend(items)
    else:
        iters = raw if isinstance(raw, list) else []
    for it in iters:
        href = None
        if isinstance(it, dict):
            href = it.get("href") or it.get("src")
        elif isinstance(it, str):
            href = it
        if not href:
            continue
        if not href.startswith("http"):
            href = urljoin(base, href)
        links.add(normalize_url(href))
    return links

def result_to_jsonl_line(result, fallback_url: str):

    if hasattr(result, "model_dump_json"):
        try:
            return result.model_dump_json()
        except Exception:
            pass
    # build a minimal payload
    payload = {
        "url": getattr(result, "url", None) or fallback_url,
        "status": getattr(result, "status", None),
        "title": getattr(result, "title", None),
        "meta": {},  # placeholder if you want to enrich
        "params": {},  # placeholder
        "has_form": False,  # placeholder
        "response_time_ms": getattr(result, "response_time_ms", None),
        "response_size": getattr(result, "response_size", None),
    }
    # if markdown is available, include a short excerpt
    md = getattr(result, "markdown", None)
    if isinstance(md, str) and md:
        payload["excerpt"] = md[:500]
    return json.dumps(payload, ensure_ascii=False)

# --------- MAIN ---------
async def main():
    print("[INIT] \u2192 Crawl4AI login + BFS \u2192 JSONL")
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    # Browser configuration
    browser_config = BrowserConfig(
        headless=HEADLESS,
        verbose=VERBOSE
    )
    # Crawl configuration
    crawler_run_config = CrawlerRunConfig(
        js_code=None,
        wait_for="body",
        cache_mode=CacheMode.BYPASS,
        verbose=VERBOSE
    )
    crawler = AsyncWebCrawler(config=browser_config)

    # Login hook
    async def on_page_context_created(page: Page, context: BrowserContext, **kwargs):
        try:
            await page.goto(LOGIN_URL, timeout=30000)
            await page.wait_for_selector("#user_login", timeout=5000)
            await page.fill("#user_login", USERNAME)
            await page.fill("#user_pass", PASSWORD)
            await page.click("#wp-submit")
            await page.wait_for_selector("#wpadminbar", timeout=10000)
            if VERBOSE: print("[HOOK] Login OK (wpadminbar detected).")
        except Exception as e:
            if VERBOSE: print(f"[HOOK] Login not performed (already logged in ?) : {e}")
        try:
            await page.set_viewport_size({"width": 1200, "height": 900})
        except: pass
        return page

    # Attach the hook
    try:
        crawler.crawler_strategy.set_hook("on_page_context_created", on_page_context_created)
    except Exception:
        try:
            crawler.set_hook("on_page_context_created", on_page_context_created)
        except Exception as e:
            print("[WARN] Unable to attach hook :", e)

    await crawler.start()
    print("[START] Crawler started. BFS on:", ADMIN_URL)

    visited = set()
    q = deque([(normalize_url(ADMIN_URL), 0)])
    pages_written = 0

    with OUT_JSONL.open("w", encoding="utf-8") as fout:
        while q and pages_written < MAX_PAGES:
            url, depth = q.popleft()
            if url in visited:
                continue
            if depth > MAX_DEPTH:
                continue
            if not in_scope(url):
                continue

            time.sleep(DELAY_S)
            if VERBOSE: print(f"[FETCH][d={depth}] {url}")

            try:
                result = await crawler.arun(url, config=crawler_run_config)
            except Exception as e:
                print(f"[ERR] arun({url}) : {e}")
                visited.add(url)
                continue

            # Write one JSON line per page
            try:
                line = result_to_jsonl_line(result, fallback_url=url)
                fout.write(line + "\n")
                pages_written += 1
            except Exception as e:
                print(f"[WARN] JSONL write failed for {url}: {e}")

            visited.add(url)

            # Enqueue new links
            try:
                for ln in extract_links(result, base=url):
                    if ln not in visited and ln.startswith(BASE_SCOPE):
                        q.append((ln, depth + 1))
            except Exception as e:
                if VERBOSE: print(f"[WARN] extract_links: {e}")

    await crawler.close()
    print(f"[END] Wrote {pages_written} lines to {OUT_JSONL}")

if __name__ == "__main__":
    asyncio.run(main())
