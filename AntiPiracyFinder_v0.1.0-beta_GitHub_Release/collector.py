import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.common.by import By

from utils import clean_text, host, unwrap_url, in_domains
from config import SEARCH_DOMAINS
from scoring import score


def detect_engine(url):
    h = host(url)
    if h == "bing.com" or h.endswith(".bing.com"):
        return "Bing"
    if h == "baidu.com" or h.endswith(".baidu.com"):
        return "Baidu"
    if h == "quark.cn" or h.endswith(".quark.cn") or h.endswith(".sm.cn"):
        return "Quark"
    if h.startswith("google.") or ".google." in h:
        return "Google"
    return "Unknown"


def current_query(url, driver):
    try:
        qs = parse_qs(urlparse(url).query)
        for key in ("q", "wd", "word", "query", "keyword"):
            if qs.get(key):
                return qs[key][0]
    except Exception:
        pass

    for css in (
        'input[name="q"]',
        'textarea[name="q"]',
        'input[name="wd"]',
        'input[type="search"]',
    ):
        try:
            e = driver.find_element(By.CSS_SELECTOR, css)
            value = e.get_attribute("value")
            if value:
                return value
        except Exception:
            pass
    return ""


def _add(hits, seen, title, href, snippet="", displayed=""):
    title = clean_text(title)
    href = (href or "").strip()

    if not title or not href.startswith(("http://", "https://")):
        return
    if href in seen:
        return

    seen.add(href)
    hits.append({
        "title": title,
        "url": href,
        "snippet": clean_text(snippet)[:800],
        "displayed_domain": clean_text(displayed)[:150],
    })


def parse_google(soup):
    hits, seen = [], set()
    for h3 in soup.select("h3"):
        a = h3.find_parent("a")
        if not a:
            continue
        href = unwrap_url(a.get("href", ""))
        block = h3.find_parent("div")
        _add(
            hits, seen,
            h3.get_text(" ", strip=True),
            href,
            block.get_text(" ", strip=True) if block else "",
            host(href),
        )
    return hits


def parse_bing(soup):
    hits, seen = [], set()
    for li in soup.select("li.b_algo"):
        a = li.select_one("h2 a")
        if not a:
            continue
        p = li.select_one(".b_caption p")
        href = unwrap_url(a.get("href", ""))
        _add(
            hits, seen,
            a.get_text(" ", strip=True),
            href,
            p.get_text(" ", strip=True) if p else "",
            host(href),
        )
    return hits


def parse_baidu(soup):
    hits, seen = [], set()

    # 只以 h3 标题结果为入口，避免把底部“相关搜索”按钮当结果。
    for h3 in soup.find_all("h3"):
        a = h3.find("a")
        if not a:
            continue

        href = a.get("href", "")
        if href.startswith("/"):
            href = "https://www.baidu.com" + href

        parent = h3.find_parent("div")
        snippet = parent.get_text(" ", strip=True) if parent else ""
        displayed = ""

        if parent:
            for node in parent.select("span, cite"):
                t = clean_text(node.get_text(" ", strip=True))
                if "." in t and len(t) < 150:
                    displayed = t
                    break

        _add(
            hits, seen,
            a.get_text(" ", strip=True),
            href,
            snippet,
            displayed,
        )
    return hits


def parse_quark(soup):
    hits, seen = [], set()
    nodes = []

    for sel in (
        "h3 a[href]",
        "h2 a[href]",
        ".result a[href]",
        ".c-container a[href]",
        "article a[href]",
        "main a[href]",
    ):
        nodes.extend(soup.select(sel))

    for a in nodes:
        parent = a.find_parent(["article", "section", "div", "li"])
        _add(
            hits, seen,
            a.get_text(" ", strip=True),
            a.get("href", ""),
            parent.get_text(" ", strip=True) if parent else "",
            host(a.get("href", "")),
        )

    return hits


PARSERS = {
    "Google": parse_google,
    "Bing": parse_bing,
    "Baidu": parse_baidu,
    "Quark": parse_quark,
}


def collect_current_page(driver, book, author):
    engine = detect_engine(driver.current_url)

    if engine not in PARSERS:
        raise RuntimeError(
            "当前页面不是支持的搜索结果页。"
            "请在专用 Edge 中打开 Google、Bing、百度或 Quark 搜索结果。"
        )

    soup = BeautifulSoup(driver.page_source, "html.parser")
    query = current_query(driver.current_url, driver)
    hits = PARSERS[engine](soup)

    rows = []
    for hit in hits:
        raw = hit["url"]
        h = host(raw)

        normalized_domain = (
            hit["displayed_domain"]
            if in_domains(h, SEARCH_DOMAINS)
            else h
        )

        status, suspect = score(
            book, author,
            hit["title"],
            hit["snippet"],
            normalized_domain,
        )

        rows.append({
            **hit,
            "engine": engine,
            "query": query,
            "domain": normalized_domain,
            "status": status,
            "score": suspect,
        })

    return engine, query, rows


# ============================================================
# 导航检测
# ============================================================

def _visible_enabled(element):
    try:
        return element.is_displayed() and element.is_enabled()
    except Exception:
        return False


def _element_text(element):
    try:
        return clean_text(" ".join([
            element.text or "",
            element.get_attribute("aria-label") or "",
            element.get_attribute("title") or "",
        ]))
    except Exception:
        return ""


def current_page_number(driver, engine):
    """
    尝试读取分页器当前激活页码。
    不依赖单一 class，兼容不同搜索引擎/不同页面版本。
    """
    selectors = {
        "Baidu": [
            '[class*="page"] [class*="current"]',
            '[class*="page"] [class*="active"]',
            '[class*="pagination"] [class*="current"]',
            '[class*="pagination"] [class*="active"]',
            'span.pc',
            'strong',
        ],
        "Google": [
            '[aria-current="page"]',
            'td.YyVfkd',
        ],
        "Bing": [
            '.sb_pagS',
            '[aria-current="page"]',
        ],
        "Quark": [
            '[aria-current="page"]',
            '[class*="pagination"] [class*="active"]',
            '[class*="page"] [class*="active"]',
        ],
    }.get(engine, [])

    for css in selectors:
        try:
            for e in driver.find_elements(By.CSS_SELECTOR, css):
                if not e.is_displayed():
                    continue
                text = clean_text(e.text)
                if re.fullmatch(r"\d{1,4}", text):
                    return int(text)
        except Exception:
            pass

    # URL 参数作为备用判断。
    try:
        qs = parse_qs(urlparse(driver.current_url).query)

        if engine == "Baidu" and qs.get("pn"):
            # 百度 pn 常见为 0,10,20...
            pn = int(qs["pn"][0])
            return pn // 10 + 1

        if engine == "Bing" and qs.get("first"):
            first = int(qs["first"][0])
            return max(1, ((first - 1) // 10) + 1)

        for key in ("page", "p"):
            if qs.get(key):
                value = int(qs[key][0])
                if value >= 1:
                    return value
    except Exception:
        pass

    return None


def find_numeric_next(driver, engine):
    """
    第一策略：寻找“当前页 + 1”的数字页码。
    不假设百度永远使用数字分页；找不到就返回 None，
    上层会继续尝试 > / Next，再尝试滚动。
    """
    current = current_page_number(driver, engine)
    if current is None:
        return None, None

    target = current + 1

    # 先限制在常见分页区域。
    container_selectors = [
        '[class*="pagination"]',
        '[class*="pager"]',
        '[class*="page"]',
        '#page',
        'nav',
    ]

    candidates = []

    for container_css in container_selectors:
        try:
            containers = driver.find_elements(By.CSS_SELECTOR, container_css)
            for container in containers:
                if not container.is_displayed():
                    continue
                candidates.extend(
                    container.find_elements(By.CSS_SELECTOR, "a, button")
                )
        except Exception:
            pass

    # 页面结构特殊时再做全局 fallback。
    if not candidates:
        try:
            candidates = driver.find_elements(
                By.CSS_SELECTOR,
                "a, button"
            )
        except Exception:
            candidates = []

    for e in candidates:
        if not _visible_enabled(e):
            continue
        text = clean_text(e.text)
        if text == str(target):
            return e, target

    return None, target


def find_arrow_next(driver, engine):
    """
    第二策略：寻找 > / → / 下一页 / Next。
    兼容只有箭头图标、没有“下一页”文字的分页器。
    """
    selectors = {
        "Baidu": [
            'a.n',
            'a.new-nextpage',
            'a[class*="next"]',
            'button[class*="next"]',
            'a[aria-label*="下一"]',
            'button[aria-label*="下一"]',
            'a[aria-label*="Next"]',
            'button[aria-label*="Next"]',
        ],
        "Google": [
            'a#pnnext',
            'a[aria-label*="Next"]',
            'a[aria-label*="下一"]',
        ],
        "Bing": [
            'a.sb_pagN',
            'a[title*="Next"]',
            'a[title*="下一"]',
            'a[aria-label*="Next"]',
        ],
        "Quark": [
            'a[class*="next"]',
            'button[class*="next"]',
            'a[aria-label*="下一"]',
            'button[aria-label*="下一"]',
            'a[aria-label*="Next"]',
            'button[aria-label*="Next"]',
        ],
    }.get(engine, [])

    checked = set()

    for css in selectors:
        try:
            for e in driver.find_elements(By.CSS_SELECTOR, css):
                if not _visible_enabled(e):
                    continue
                checked.add(e.id)
                return e
        except Exception:
            pass

    # 第三方/新版分页器可能只是一个裸箭头。
    # 只在页面底部区域寻找，降低误点风险。
    try:
        page_height = driver.execute_script(
            "return Math.max(document.body.scrollHeight,"
            "document.documentElement.scrollHeight);"
        )
        elements = driver.find_elements(By.CSS_SELECTOR, "a, button")
        for e in elements:
            if not _visible_enabled(e):
                continue
            try:
                y = e.rect.get("y", 0)
            except Exception:
                y = 0

            if page_height and y < page_height * 0.60:
                continue

            text = _element_text(e).strip().lower()

            if text in (
                ">", "›", "»", "→",
                "下一页", "下一页 >", "下页",
                "next", "next page",
            ):
                return e
    except Exception:
        pass

    return None


def result_signature(driver, book, author):
    """
    用搜索结果 URL + 当前页码 + URL 建立页面指纹。
    点击后只有指纹发生变化才认为翻页真正成功。
    """
    try:
        engine, _, rows = collect_current_page(driver, book, author)
        urls = tuple(r["url"] for r in rows[:8])
    except Exception:
        engine, urls = detect_engine(driver.current_url), tuple()

    return {
        "url": driver.current_url,
        "page": current_page_number(driver, engine),
        "urls": urls,
    }


def signature_changed(before, after):
    if before["url"] != after["url"]:
        return True
    if before["page"] is not None and after["page"] is not None:
        if before["page"] != after["page"]:
            return True
    if before["urls"] and after["urls"] and before["urls"] != after["urls"]:
        return True
    return False
