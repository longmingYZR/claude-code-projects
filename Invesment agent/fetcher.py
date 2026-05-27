"""
fetcher.py — 知乎文章抓取器（Playwright 浏览器驱动）
"""

import logging
import time
import random
from contextlib import contextmanager
from bs4 import BeautifulSoup
from config import ZHIHU_COOKIE, COLUMN_URL

logger = logging.getLogger(__name__)


def _parse_cookies(cookie_str: str) -> list[dict]:
    """将 Cookie 字符串解析为 Playwright 格式"""
    cookies = []
    for item in cookie_str.split("; "):
        if "=" in item:
            key, _, val = item.partition("=")
            cookies.append({
                "name": key.strip(),
                "value": val.strip(),
                "domain": ".zhihu.com",
                "path": "/",
            })
    return cookies


@contextmanager
def _browser_page():
    """共享的 Playwright 浏览器启动器"""
    from playwright.sync_api import sync_playwright

    cookies = _parse_cookies(ZHIHU_COOKIE)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            channel="msedge",
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        context.add_cookies(cookies)
        page = context.new_page()

        # 先访问知乎首页建立会话
        page.goto("https://www.zhihu.com/", wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(2000)

        yield page

        browser.close()


def _navigate(page, url: str) -> str:
    """导航到目标页面，返回 HTML"""
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    return page.content()


def discover_new_articles(known_urls: set) -> list[str]:
    """
    从专栏首页发现新文章（不在 known_urls 中的）
    返回新文章URL列表
    """
    try:
        with _browser_page() as page:
            html = _navigate(page, COLUMN_URL)

        soup = BeautifulSoup(html, "html.parser")
        found = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/p/" in href:
                # 统一转为完整 https URL
                if href.startswith("//"):
                    url = "https:" + href
                elif href.startswith("/"):
                    url = "https://zhuanlan.zhihu.com" + href
                else:
                    url = href
                found.add(url)

        new_urls = [u for u in found if u not in known_urls]
        logger.info(f"专栏发现：共 {len(found)} 篇文章，{len(new_urls)} 篇新文章")
        return new_urls

    except Exception as e:
        logger.exception(f"文章发现失败: {e}")
        return []


def fetch_article(url: str) -> dict | None:
    """
    使用 Playwright 浏览器抓取知乎专栏文章正文
    返回: {"title": ..., "content": ..., "publish_date": ...} 或 None
    """
    try:
        time.sleep(random.uniform(2, 5))

        with _browser_page() as page:
            html = _navigate(page, url)

        if '<meta id="zh-zse-ck"' in html or len(html) < 2000:
            logger.error("页面被反爬拦截（zse_ck 挑战或内容过短）")
            return None

        soup = BeautifulSoup(html, "html.parser")

        title = ""
        title_tag = soup.find("h1", class_=lambda c: c and "Post-Title" in c)
        if not title_tag:
            title_tag = soup.find("h1")
        if title_tag:
            title = title_tag.get_text(strip=True)

        publish_date = ""
        time_tag = soup.find("time")
        if time_tag:
            publish_date = time_tag.get("datetime", time_tag.get_text(strip=True))

        content = ""
        content_div = soup.find("div", class_=lambda c: c and "Post-RichTextContainer" in c)
        if not content_div:
            content_div = soup.find("div", class_=lambda c: c and "RichText" in c)
        if not content_div:
            content_div = soup.find("article")

        if content_div:
            for noise in content_div.find_all(["script", "style", "aside"]):
                noise.decompose()
            content = content_div.get_text(separator="\n", strip=True)
        else:
            logger.warning(f"未找到正文容器，尝试全页提取: {url}")
            body = soup.find("body")
            content = body.get_text(separator="\n", strip=True) if body else ""

        if not content or len(content) < 100:
            logger.error(f"正文内容过短（{len(content)}字），可能是付费墙未突破: {url}")
            return None

        content_trimmed = content[:8000]

        logger.info(f"成功抓取文章: 《{title}》({len(content)}字)")
        return {
            "title": title,
            "content": content_trimmed,
            "publish_date": publish_date,
            "url": url,
        }

    except Exception as e:
        logger.exception(f"抓取异常: {url} — {e}")
        return None
