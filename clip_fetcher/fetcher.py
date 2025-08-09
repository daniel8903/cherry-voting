import asyncio
import aiohttp
import random
import html
import re
import json
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from typing import Dict, List, Optional

from clips import CLIP_CATEGORIES

# ============================================
# Keep your original CLIP_CATEGORIES as-is
# (paste your big dict here)
# ============================================
# CLIP_CATEGORIES = { ... }  # <- unchanged

# ---------- Tuning knobs ----------
MAX_CONCURRENCY = 20
PER_HOST_LIMIT   = 8
HTTP_TIMEOUT     = 15
RETRIES          = 3
BACKOFF          = 1.35
RETRYABLE        = {429, 500, 502, 503, 504}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

def pick_ua() -> str:
    return random.choice(USER_AGENTS)

def clean_html_entities(text: Optional[str]) -> Optional[str]:
    if not text:
        return text
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&#\d+;', '', text)
    text = re.sub(r'&[a-zA-Z]+;', '', text)
    text = re.sub(r'["\'/><]', '', text)
    return text.strip()

def get_clip_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith("clips.twitch.tv"):
        slug = parsed.path.strip("/").split("/")[0]
        return slug or ""
    if parsed.netloc.endswith("twitch.tv"):
        parts = [p for p in parsed.path.split("/") if p]
        for i, p in enumerate(parts):
            if p.lower() == "clip" and i + 1 < len(parts):
                return parts[i + 1]
        qs = parse_qs(parsed.query)
        for k in ("clip", "slug", "id"):
            if k in qs and qs[k]:
                return qs[k][0]
    m = re.search(r"(?:clip/|clips\.twitch\.tv/)([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    return ""

def parse_clip_page(html_content: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html_content, 'html.parser')
    title = None
    creator = None

    og = soup.find('meta', property='og:title')
    if og and og.get('content'):
        t = og['content']
        if " - Clip Created by @" in t:
            parts = t.split(' - Clip Created by @')
            if len(parts) == 2:
                title_part = parts[0].strip()
                creator = clean_html_entities(parts[1].strip())
                if creator and creator.startswith('@'):
                    creator = creator[1:]
                if ' - ' in title_part:
                    title = ' - '.join(title_part.split(' - ')[1:])
                else:
                    title = title_part
        else:
            title = t

    if not (title and creator):
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if not title and 'name' in data:
                        title = data['name']
                    if not creator and 'creator' in data:
                        c = data['creator']
                        if isinstance(c, dict) and 'name' in c:
                            creator = c['name']
            except Exception:
                continue
            if title and creator:
                break

    if not creator:
        for script in soup.find_all('script'):
            s = script.string or ""
            if not s:
                continue
            patterns = [
                r'"curator":\s*{\s*"displayName":\s*"([^"]+)"',
                r'"curator":\s*{\s*"login":\s*"([^"]+)"',
                r'"createdBy":\s*"([^"]+)"',
                r'"clipCreator":\s*"([^"]+)"',
                r'Created by @([A-Za-z0-9_]+)',
                r'Clipped by @([A-Za-z0-9_]+)',
            ]
            for pat in patterns:
                m = re.search(pat, s)
                if m:
                    creator = clean_html_entities(m.group(1))
                    if creator and creator.startswith('@'):
                        creator = creator[1:]
                    break
            if creator:
                break

    if title:
        title = clean_html_entities(title)
        title = re.sub(r'\s*-\s*Twitch\s*Clips?\s*$', '', title, flags=re.IGNORECASE)
        if title.strip() == "Twitch":
            title = None
    if creator:
        creator = clean_html_entities(creator)
        if creator and creator.startswith('@'):
            creator = creator[1:]

    return {"title": title, "creator": creator}

async def fetch_with_retries(session: aiohttp.ClientSession, method: str, url: str, *,
                             headers: Optional[dict] = None,
                             json_body: Optional[dict] = None,
                             timeout: int = HTTP_TIMEOUT,
                             retries: int = RETRIES,
                             backoff: float = BACKOFF):
    for attempt in range(1, retries + 1):
        try:
            if method == "GET":
                async with session.get(url, headers=headers, timeout=timeout) as resp:
                    if resp.status in RETRYABLE:
                        await asyncio.sleep((backoff ** attempt) + random.uniform(0, 0.4))
                        continue
                    if 200 <= resp.status < 300:
                        return await resp.text()
                    await asyncio.sleep((backoff ** attempt) / 2 + random.uniform(0, 0.2))
            else:  # POST
                async with session.post(url, json=json_body, headers=headers, timeout=timeout) as resp:
                    if resp.status in RETRYABLE:
                        await asyncio.sleep((backoff ** attempt) + random.uniform(0, 0.4))
                        continue
                    if 200 <= resp.status < 300:
                        try:
                            return await resp.json(content_type=None)
                        except Exception:
                            return None
                    await asyncio.sleep((backoff ** attempt) / 2 + random.uniform(0, 0.2))
        except (aiohttp.ClientError, asyncio.TimeoutError):
            await asyncio.sleep((backoff ** attempt) / 2 + random.uniform(0, 0.2))
    return None

async def try_twitch_gql_api(session: aiohttp.ClientSession, clip_id: str) -> Dict[str, Optional[str]]:
    if not clip_id:
        return {"title": None, "creator": None}

    gql_url = "https://gql.twitch.tv/gql"
    query = {
        "query": f"""
        query {{
            clip(slug: "{clip_id}") {{
                title
                curator {{ displayName login }}
                broadcaster {{ displayName login }}
            }}
        }}
        """
    }

    async def one(ua: str):
        headers = {
            "Client-ID": "kimne78kx3ncx6brgo4mv6wki5h1ko",
            "Content-Type": "application/json",
            "User-Agent": ua,
            "Accept": "*/*",
            "Origin": "https://www.twitch.tv",
            "Referer": "https://www.twitch.tv/",
        }
        return await fetch_with_retries(session=session, method="POST", url=gql_url,
                                        headers=headers, json_body=query)

    tasks = [one(ua) for ua in USER_AGENTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    best = {"title": None, "creator": None}
    for res in results:
        if not isinstance(res, dict):
            continue
        clip = res.get("data", {}).get("clip") if isinstance(res, dict) else None
        if not clip:
            continue
        title = clip.get("title")
        creator = None
        curator = clip.get("curator") or {}
        if curator.get("displayName"):
            creator = curator["displayName"]
        elif curator.get("login"):
            creator = curator["login"]
        if title and not best["title"]:
            best["title"] = title
        if creator and not best["creator"]:
            best["creator"] = creator
        if best["title"] and best["creator"]:
            break

    return best

def merge_info(base: Dict[str, Optional[str]], new: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    out = dict(base)
    if not out.get("title") and new.get("title"):
        out["title"] = new["title"]
    if not out.get("creator") and new.get("creator"):
        out["creator"] = new["creator"]
    return out

async def scrape_clip(session: aiohttp.ClientSession, url: str, debug: bool = False) -> Dict[str, Optional[str]]:
    clip_id = get_clip_id(url)
    best = {"title": None, "creator": None}

    # 1) GraphQL first
    if clip_id:
        best = merge_info(best, await try_twitch_gql_api(session, clip_id))
        if best["title"] and best["creator"]:
            return best

    # 2) HTML scraping (only if needed)
    urls_to_try: List[str] = []
    if clip_id:
        urls_to_try.extend([
            f"https://clips.twitch.tv/{clip_id}",
            f"https://www.twitch.tv/{clip_id}",
            f"https://www.twitch.tv/videos/{clip_id}",
        ])
    urls_to_try.append(url)

    # Dedup while preserving order
    seen = set()
    deduped = []
    for u in urls_to_try:
        if u not in seen:
            deduped.append(u)
            seen.add(u)

    async def fetch_and_parse(u: str) -> Dict[str, Optional[str]]:
        headers = {
            "User-Agent": pick_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "no-cache",
        }
        text = await fetch_with_retries(session, "GET", u, headers=headers)
        if not text:
            return {"title": None, "creator": None}
        return parse_clip_page(text)

    tasks = [asyncio.create_task(fetch_and_parse(u)) for u in deduped]
    for coro in asyncio.as_completed(tasks):
        parsed = await coro
        best = merge_info(best, parsed)
        if best["title"] and best["creator"]:
            for t in tasks:
                if not t.done():
                    t.cancel()
            break

    return best

async def process_category(session: aiohttp.ClientSession, category_name: str, urls: List[str], debug: bool = False) -> List[Dict[str, Optional[str]]]:
    print(f"\n{'='*60}\nProcessing category: {category_name}\n{'='*60}")
    results: List[Dict[str, Optional[str]]] = []
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def one(u: str, idx: int, total: int):
        async with sem:
            if debug:
                print(f"[{category_name}] {idx+1}/{total}: {u}")
            info = await scrape_clip(session, u, debug=debug)
            if debug:
                print(f"  Final -> title={info.get('title')!r} | creator={info.get('creator')!r}")
            return {"url": u, "title": info.get("title"), "clip_creator": info.get("creator")}

    tasks = [asyncio.create_task(one(u, i, len(urls))) for i, u in enumerate(urls)]
    done = []
    for t in asyncio.as_completed(tasks):
        done.append(await t)

    # keep original order
    url_to_result = {r["url"]: r for r in done}
    ordered = [url_to_result[u] for u in urls]
    return ordered

async def run_all():
    conn = aiohttp.TCPConnector(limit=MAX_CONCURRENCY, limit_per_host=PER_HOST_LIMIT, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=None, connect=HTTP_TIMEOUT, sock_connect=HTTP_TIMEOUT, sock_read=HTTP_TIMEOUT)

    async with aiohttp.ClientSession(
        connector=conn,
        timeout=timeout,
        headers={"User-Agent": pick_ua(), "Accept": "*/*"},
        raise_for_status=False,
        trust_env=True,
    ) as session:
        all_results: Dict[str, List[Dict[str, Optional[str]]]] = {}

        cat_tasks = {
            category_name: asyncio.create_task(process_category(session, category_name, urls, debug=True))
            for category_name, urls in CLIP_CATEGORIES.items()
        }

        for category_name, task in cat_tasks.items():
            category_results = await task
            all_results[category_name] = category_results

            filename = f"clips_{category_name.lower()}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(category_results, f, ensure_ascii=False, indent=2)
            print(f"\nSaved {len(category_results)} clips to {filename}")

        print(f"\n{'='*60}\nFINAL SUMMARY\n{'='*60}")
        for category, clips in all_results.items():
            successful = sum(1 for c in clips if c.get('title') or c.get('clip_creator'))
            print(f"{category}: {successful}/{len(clips)} successful")

def main():
    asyncio.run(run_all())

if __name__ == "__main__":
    main()
