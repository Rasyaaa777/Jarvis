import urllib.parse
import requests
from bs4 import BeautifulSoup

def _search_bing(query: str, max_results: int = 3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "id,en-US;q=0.9,en;q=0.8"
    }
    url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(query)}"
    r = requests.get(url, headers=headers, timeout=6)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for el in soup.select("li.b_algo"):
            h2 = el.select_one("h2")
            p = el.select_one("div.b_caption p, p")
            if h2 and p:
                title = h2.get_text(strip=True)
                snippet = p.get_text(strip=True)
                if title and snippet:
                    results.append(f"- {title}: {snippet}")
                    if len(results) >= max_results:
                        break
        return results
    return []

def _search_wikipedia(query: str, max_results: int = 3):
    headers = {"User-Agent": "JarvisAI/1.0 (https://github.com/jarvis; jarvis@local.assistant)"}
    # Try Indonesian first, then English
    for lang in ["id", "en"]:
        try:
            wiki_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote_plus(query)}&format=json&utf8=1"
            wr = requests.get(wiki_url, headers=headers, timeout=5)
            if wr.status_code == 200:
                data = wr.json()
                search_items = data.get("query", {}).get("search", [])[:max_results]
                if search_items:
                    results = []
                    for item in search_items:
                        snippet = BeautifulSoup(item.get("snippet", ""), "html.parser").get_text()
                        results.append(f"- {item['title']} (Wikipedia): {snippet}")
                    return results
        except Exception:
            continue
    return []

def _search_google(query: str, max_results: int = 3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}&hl=id"
    r = requests.get(url, headers=headers, timeout=6)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for el in soup.select("div.MjjYud, div.g, div.tF2Cxc"):
            title_el = el.select_one("h3")
            snippet_el = el.select_one("div.VwiC3b, span.aCOpRe")
            if title_el and snippet_el:
                title = title_el.get_text(strip=True)
                snippet = snippet_el.get_text(strip=True)
                if title and snippet:
                    results.append(f"- {title}: {snippet}")
                    if len(results) >= max_results:
                        break
        return results
    return []

def search_web(query: str, max_results: int = 3) -> str:
    """
    Performs a resilient web search using Bing as primary, with Wikipedia and Google fallbacks.
    """
    # 1. Primary: Bing Search
    try:
        results = _search_bing(query, max_results=max_results)
        if results:
            return "\n".join(results)
    except Exception:
        pass

    # 2. Secondary: Wikipedia API
    try:
        results = _search_wikipedia(query, max_results=max_results)
        if results:
            return "\n".join(results)
    except Exception:
        pass

    # 3. Tertiary: Google Search
    try:
        results = _search_google(query, max_results=max_results)
        if results:
            return "\n".join(results)
    except Exception:
        pass

    return f"Tidak ditemukan informasi yang relevan di web untuk '{query}'."
