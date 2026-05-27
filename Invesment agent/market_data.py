"""
market_data.py — 实时行情查询（AKShare + yfinance）
"""

import logging

logger = logging.getLogger(__name__)

INDEX_CODES = {
    "000001": "上证指数",
    "000688": "科创50",
    "000300": "沪深300",
    "399006": "创业板指",
}

OZ_PER_KG = 32.1507  # 1千克 = 32.1507 盎司


def _get_usdcny() -> float:
    """获取美元兑人民币汇率（Sina 数据不稳定，用固定汇率 + 提示）"""
    # AKShare 汇率接口常返回过期数据，使用近期合理估算值
    # 如需精确汇率，请手动修改此值
    return 7.25


def get_market_snapshot() -> str:
    """
    拉取用户关注标的的实时行情快照
    返回格式化文本，可直接注入 AI Prompt
    """
    lines = ["【当前市场行情（实时数据）】"]
    usdcny = _get_usdcny() or 7.25

    # ── 1. A股指数（新浪） ──
    try:
        import akshare as ak
        df = ak.stock_zh_index_spot_sina()
        for code, name in INDEX_CODES.items():
            sina_code = f"sh{code}" if code != "399006" else f"sz{code}"
            row = df[df["代码"] == sina_code]
            if not row.empty:
                r = row.iloc[0]
                lines.append(
                    f"• {name}({sina_code}) "
                    f"最新 {r['最新价']}  涨跌幅 {r['涨跌幅']}%  昨收 {r['昨收']}"
                )
            else:
                lines.append(f"• {name}({code}) — 未查询到数据")
    except Exception as e:
        logger.warning(f"A股指数行情查询失败: {e}")
        for code, name in INDEX_CODES.items():
            lines.append(f"• {name}({code}) — 查询失败")

    # ── 2. 白银 — 沪银期货 CNY/kg，换算 USD/oz ──
    try:
        import akshare as ak
        df = ak.futures_zh_daily_sina(symbol="AG0")
        if not df.empty:
            latest = df.iloc[-1]
            price_cny_kg = float(latest["close"])
            price_usd_oz = price_cny_kg / OZ_PER_KG / usdcny
            lines.append(
                f"• 白银 ¥{price_cny_kg:.0f} 元/千克 "
                f"(≈ ${price_usd_oz:.1f} 美元/盎司，汇率 {usdcny:.2f})"
            )
        else:
            lines.append("• 白银 — 未查询到数据")
    except Exception as e:
        logger.warning(f"白银期货行情查询失败: {e}")
        lines.append("• 白银 — 查询失败")

    lines.append("")
    return "\n".join(lines)
