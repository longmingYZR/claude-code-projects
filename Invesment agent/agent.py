"""
agent.py — 主流程编排器
用法：
  python agent.py              # 处理config.py中所有配置的文章
  python agent.py <URL>        # 处理单篇指定文章
  python agent.py --scheduler  # 启动定时模式（每天早上8:30自动运行）
"""

import sys
import logging
import io

# 修复 Windows CMD 的 GBK 编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
import logging.handlers
from datetime import datetime

from config import ARTICLE_URLS, LOG_PATH
from database import (
    init_db, is_article_processed, save_article,
    upsert_directional_view, save_price_level,
    get_latest_views, get_active_price_levels, get_all_urls
)
from fetcher import fetch_article, discover_new_articles
from analyzer import extract_signals, generate_investment_advice
from notifier import send_feishu_message, send_error_alert
from market_data import get_market_snapshot

# ── 日志配置 ──────────────────────────────────────────────────
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台输出
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # 文件输出（按天滚动，保留7天）
    fh = logging.handlers.TimedRotatingFileHandler(
        LOG_PATH, when="midnight", backupCount=7, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

setup_logging()
logger = logging.getLogger(__name__)


def process_article(url: str, force: bool = False) -> bool:
    """
    处理单篇文章的完整流程：
    抓取 → 提取信号 → 存库 → 生成建议 → 推送飞书
    返回是否成功
    """
    logger.info(f"{'='*50}")
    logger.info(f"开始处理: {url}")

    # 1. 去重检查
    if not force and is_article_processed(url):
        logger.info("文章已处理过，跳过（使用 --force 可强制重新处理）")
        return True

    # 2. 抓取文章
    article = fetch_article(url)
    if not article:
        msg = f"文章抓取失败: {url}"
        logger.error(msg)
        send_error_alert(msg)
        return False

    # 3. AI提取信号
    signals = extract_signals(article)
    if not signals:
        msg = f"信号提取失败: {article['title']}"
        logger.error(msg)
        send_error_alert(msg)
        return False

    # 4. 存入数据库
    article_id = save_article(
        url=url,
        title=article["title"],
        publish_date=article["publish_date"],
        summary=signals.get("summary", ""),
        raw_signals=signals
    )
    logger.info(f"文章已入库，ID: {article_id}")

    # 5. 存储方向性观点
    for view in signals.get("directional_views", []):
        upsert_directional_view(
            article_id=article_id,
            asset_class=view.get("asset_class", ""),
            direction=view.get("direction", ""),
            confidence=view.get("confidence", "中"),
            core_logic=view.get("core_logic", "")
        )

    # 6. 存储关键点位
    for lvl in signals.get("key_price_levels", []):
        if lvl.get("price"):
            save_price_level(
                article_id=article_id,
                asset_code=lvl.get("asset_code", ""),
                asset_name=lvl.get("asset_name", ""),
                level_type=lvl.get("level_type", ""),
                price=float(lvl["price"]),
                note=lvl.get("note", "")
            )

    # 7. 如果文章不含可操作建议，仅入库不推送
    if not signals.get("is_actionable", True):
        logger.info("文章不含可操作建议（纯分析/科普），仅入库，不推送飞书")
        return True

    # 8. 拉取历史数据 + 实时行情，生成复合建议
    historical_views = get_latest_views()
    active_levels = get_active_price_levels()
    market_snapshot = get_market_snapshot()
    advice = generate_investment_advice(article, signals, historical_views, active_levels, market_snapshot)

    # 9. 推送飞书
    today_str = datetime.now().strftime("%Y-%m-%d")
    send_feishu_message(
        title=f"投资建议 | {today_str}",
        article_title=article["title"],
        article_url=url,
        summary=signals.get("summary", ""),
        advice=advice,
        has_signals=bool(signals.get("directional_views") or signals.get("key_price_levels"))
    )

    logger.info(f"✅ 处理完成: 《{article['title']}》")
    return True


def run_all(force: bool = False):
    """处理配置文件中所有文章 + 自动发现新文章"""
    # 合并手动配置和自动发现的文章
    all_urls = list(ARTICLE_URLS)
    known = set(ARTICLE_URLS) | get_all_urls()
    new_urls = discover_new_articles(known)
    all_urls.extend(new_urls)

    logger.info(f"批量处理模式，共 {len(all_urls)} 篇文章（手动 {len(ARTICLE_URLS)} + 新发现 {len(new_urls)}）")
    success, fail = 0, 0
    for url in all_urls:
        ok = process_article(url, force=force)
        if ok:
            success += 1
        else:
            fail += 1
    logger.info(f"批量处理完成：成功 {success}，失败 {fail}")


def run_scheduler():
    """定时模式：每天 08:30 自动运行"""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError:
        logger.error("请先安装: pip install apscheduler")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(run_all, "cron", hour=8, minute=30)
    logger.info("定时模式已启动，每天 08:30 自动运行（Ctrl+C 退出）")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("定时任务已停止")


if __name__ == "__main__":
    init_db()

    args = sys.argv[1:]

    if "--scheduler" in args:
        run_scheduler()
    elif args and not args[0].startswith("--"):
        # 命令行传入URL
        url = args[0]
        force = "--force" in args
        process_article(url, force=force)
    else:
        force = "--force" in args
        run_all(force=force)
