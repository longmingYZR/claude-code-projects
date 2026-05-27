"""
database.py — SQLite 数据库初始化与操作
"""

import sqlite3
import json
import logging
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger(__name__)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库，创建三张核心表"""
    conn = get_conn()
    c = conn.cursor()

    # 文章表
    c.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            url             TEXT UNIQUE NOT NULL,
            title           TEXT,
            publish_date    TEXT,
            fetched_at      TEXT,
            summary         TEXT,
            raw_signals     TEXT,   -- JSON字符串，存储AI原始分析
            processed       INTEGER DEFAULT 0
        )
    """)

    # 方向性观点表
    c.execute("""
        CREATE TABLE IF NOT EXISTS directional_views (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id      INTEGER,
            asset_class     TEXT,   -- 如"A股"/"港股"/"黄金"
            direction       TEXT,   -- 看多/看空/震荡
            confidence      TEXT,   -- 高/中/低
            core_logic      TEXT,
            valid_from      TEXT,
            valid_until     TEXT,   -- NULL表示仍有效
            is_latest       INTEGER DEFAULT 1,  -- 1=当前最新观点
            FOREIGN KEY(article_id) REFERENCES articles(id)
        )
    """)

    # 关键点位表
    c.execute("""
        CREATE TABLE IF NOT EXISTS key_price_levels (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id      INTEGER,
            asset_code      TEXT,   -- 如"000001.SH"
            asset_name      TEXT,   -- 如"上证指数"
            level_type      TEXT,   -- 支撑位/压力位/目标价/止损位
            price           REAL,
            mention_count   INTEGER DEFAULT 1,
            triggered       INTEGER DEFAULT 0,
            triggered_time  TEXT,
            note            TEXT,
            FOREIGN KEY(article_id) REFERENCES articles(id)
        )
    """)

    conn.commit()
    conn.close()
    logger.info("数据库初始化完成")


def is_article_processed(url: str) -> bool:
    """检查文章是否已处理过"""
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM articles WHERE url=? AND processed=1", (url,)
    ).fetchone()
    conn.close()
    return row is not None


def save_article(url: str, title: str, publish_date: str, summary: str, raw_signals: dict) -> int:
    """保存文章基本信息，返回article_id"""
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    try:
        c.execute("""
            INSERT INTO articles (url, title, publish_date, fetched_at, summary, raw_signals, processed)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title,
                fetched_at=excluded.fetched_at,
                summary=excluded.summary,
                raw_signals=excluded.raw_signals,
                processed=1
        """, (url, title, publish_date, now, summary, json.dumps(raw_signals, ensure_ascii=False)))
        conn.commit()
        article_id = c.execute("SELECT id FROM articles WHERE url=?", (url,)).fetchone()["id"]
        return article_id
    finally:
        conn.close()


def upsert_directional_view(article_id: int, asset_class: str, direction: str,
                             confidence: str, core_logic: str):
    """插入或更新方向性观点（同一资产类别，新观点替换旧观点）"""
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    try:
        # 把同一资产类别的旧观点标记为失效
        c.execute("""
            UPDATE directional_views
            SET is_latest=0, valid_until=?
            WHERE asset_class=? AND is_latest=1
        """, (now, asset_class))

        # 插入新观点
        c.execute("""
            INSERT INTO directional_views
                (article_id, asset_class, direction, confidence, core_logic, valid_from, is_latest)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (article_id, asset_class, direction, confidence, core_logic, now))
        conn.commit()
    finally:
        conn.close()


def save_price_level(article_id: int, asset_code: str, asset_name: str,
                     level_type: str, price: float, note: str):
    """保存关键点位（相同标的+相同价格+相同类型则累计mention_count）"""
    conn = get_conn()
    c = conn.cursor()
    try:
        existing = c.execute("""
            SELECT id, mention_count FROM key_price_levels
            WHERE asset_code=? AND level_type=? AND ABS(price-?)<?
        """, (asset_code, level_type, price, price * 0.005)).fetchone()  # 0.5%容差

        if existing:
            c.execute("""
                UPDATE key_price_levels SET mention_count=mention_count+1, article_id=?
                WHERE id=?
            """, (article_id, existing["id"]))
        else:
            c.execute("""
                INSERT INTO key_price_levels
                    (article_id, asset_code, asset_name, level_type, price, note)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (article_id, asset_code, asset_name, level_type, price, note))
        conn.commit()
    finally:
        conn.close()


def get_latest_views() -> list:
    """获取博主当前所有有效的方向性观点"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT dv.*, a.title as article_title, a.url as article_url
        FROM directional_views dv
        JOIN articles a ON dv.article_id = a.id
        WHERE dv.is_latest=1
        ORDER BY dv.valid_from DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_active_price_levels() -> list:
    """获取所有未触发的关键点位"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT kpl.*, a.title as article_title
        FROM key_price_levels kpl
        JOIN articles a ON kpl.article_id = a.id
        WHERE kpl.triggered=0
        ORDER BY kpl.mention_count DESC, kpl.price DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_urls() -> set:
    """获取数据库中所有文章的URL"""
    conn = get_conn()
    rows = conn.execute("SELECT url FROM articles").fetchall()
    conn.close()
    return {r["url"] for r in rows}
