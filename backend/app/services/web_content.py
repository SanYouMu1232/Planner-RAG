"""Safe webpage fetching and article/table extraction for explicit user actions."""
from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .text_extractor import ExtractedText, LayoutBlock, PageContent, table_markdown
from ..config import REQUEST_TIMEOUT_SECONDS


class WebContentError(RuntimeError):
    pass


BOILERPLATE_RE = re.compile(
    r"(登录|注册|广告|相关阅读|相关推荐|分享|客户端|下载|版权|免责声明|返回顶部|扫码|微信|微博|字号|打印|收藏|导航|菜单)"
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？；])")


def _assert_public(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise WebContentError("只允许 http/https 公网 URL。")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise WebContentError("域名无法解析。") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast:
            raise WebContentError("禁止抓取内网、回环或保留地址。")


def _clean_text(text: str) -> str:
    text = (text or "").replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip()


def _is_noise(text: str, tag_name: str = "") -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return True
    if len(compact) <= 2 and tag_name not in {"h1", "h2", "h3", "h4"}:
        return True
    if len(compact) <= 18 and BOILERPLATE_RE.search(compact):
        return True
    return False


def _split_long_text(text: str, limit: int = 700) -> list[str]:
    """Split display/extraction blocks at sentence boundaries without losing text."""
    text = _clean_text(text)
    if len(text) <= limit:
        return [text] if text else []
    pieces: list[str] = []
    buf = ""
    for sentence in [x for x in SENTENCE_SPLIT_RE.split(text) if x]:
        if len(buf) + len(sentence) <= limit or not buf:
            buf += sentence
            continue
        pieces.append(buf.strip())
        buf = sentence
    if buf.strip():
        pieces.append(buf.strip())
    # Extremely long punctuation-free blocks: fall back to hard split, keeping all chars.
    out: list[str] = []
    for piece in pieces:
        if len(piece) <= limit:
            out.append(piece)
        else:
            for start in range(0, len(piece), limit):
                out.append(piece[start : start + limit].strip())
    return [x for x in out if x]


def _table_rows(el) -> list[list[str]]:
    return [[cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])] for tr in el.find_all("tr")]


def _best_root(soup: BeautifulSoup):
    selectors = [
        "article",
        "main",
        "[role=main]",
        ".article",
        ".article-content",
        ".content",
        ".main-content",
        ".TRS_Editor",
        "#content",
        "#article",
    ]
    for selector in selectors:
        found = soup.select_one(selector)
        if found and len(found.get_text("", strip=True)) > 120:
            return found
    return soup.body or soup


def extract_html(html: str, url: str = "") -> tuple[str, ExtractedText]:
    soup = BeautifulSoup(html, "lxml")
    for el in soup(["script", "style", "noscript", "nav", "footer", "aside", "form", "iframe", "button"]):
        el.decompose()
    title = ""
    if soup.title:
        title = _clean_text(soup.title.get_text(" ", strip=True))
    if not title:
        h1 = soup.find("h1")
        title = _clean_text(h1.get_text(" ", strip=True)) if h1 else url or "未命名网页"
    root = _best_root(soup)
    blocks: list[LayoutBlock] = []
    texts: list[str] = []
    seen: set[str] = set()
    order = 0

    def add_block(kind: str, text: str, table: list[list[str]] | None = None) -> None:
        nonlocal order
        text = _clean_text(text)
        if _is_noise(text, "table" if kind == "table" else kind):
            return
        key = re.sub(r"\s+", "", text)
        # Keep duplicate short headings out, but do not de-duplicate long policy clauses.
        if len(key) < 80 and key in seen:
            return
        seen.add(key)
        for piece in _split_long_text(text, 700 if kind != "heading" else 220):
            order += 1
            blocks.append(LayoutBlock(order, kind, piece, 1, title, None, table if kind == "table" else None))
            texts.append(piece)

    add_block("heading", title)
    candidate_nodes = root.find_all(["h1", "h2", "h3", "h4", "p", "li", "table"])
    for el in candidate_nodes:
        if el.find_parent("table") and el.name != "table":
            continue
        if el.name == "table":
            rows = _table_rows(el)
            md = table_markdown(rows)
            if md:
                add_block("table", md, rows)
            continue
        text = el.get_text(" ", strip=True)
        add_block("heading" if el.name.startswith("h") else "paragraph", text)

    # Some sites put the article in plain divs without p tags. If structured nodes
    # were too sparse, fall back to visible body lines so the ingested webpage is not
    # reduced to the search-result摘要/前半段。
    joined_compact = re.sub(r"\s+", "", "".join(texts))
    if len(joined_compact) < 300:
        fallback_text = _clean_text(root.get_text("\n", strip=True))
        for line in [x.strip() for x in fallback_text.splitlines() if x.strip()]:
            if re.sub(r"\s+", "", line) not in seen:
                add_block("paragraph", line)

    result = ExtractedText(
        "\n\n".join(texts),
        [PageContent(1, "\n".join(texts))],
        blocks,
        source_method="web_html",
        parser_name="BeautifulSoup/article-DOM-order/fulltext",
    )
    return title, result


async def fetch_webpage(url: str) -> tuple[str, ExtractedText]:
    _assert_public(url)
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=True, headers={"User-Agent": "PlannerThinkTank/1.1"}) as client:
        response = await client.get(url)
        response.raise_for_status()
    if "html" not in response.headers.get("content-type", "").lower():
        raise WebContentError("该链接未返回 HTML 网页，不能作为网页资料入库。")
    return extract_html(response.text, url)
