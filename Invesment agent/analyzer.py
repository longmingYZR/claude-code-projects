"""
analyzer.py — 调用 DeepSeek API 分析文章，提取结构化投资信号
"""

import json
import logging
import re
from openai import OpenAI
from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    INVESTMENT_PROFILE, BLOGGER_FRAMEWORK, USER_ENTRY_ZONES,
)

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

# ── Prompt：第一步，结构化提取 ────────────────────────────────
EXTRACTION_SYSTEM = """你是一个专业的投资分析助手。
你的任务是从博主的投资文章中提取结构化信息，输出严格的JSON格式，不要有任何多余文字。

输出格式：
{
  "summary": "文章核心观点的2-3句话摘要",
  "is_actionable": true/false,  // 文章是否包含可操作的投资建议（非科普/纯分析文）
  "directional_views": [
    {
      "asset_class": "资产类别，如'A股'/'港股'/'黄金'/'美元'/'债券'",
      "direction": "看多/看空/震荡",
      "confidence": "高/中/低",
      "core_logic": "一句话说明判断依据"
    }
  ],
  "key_price_levels": [
    {
      "asset_name": "标的名称，如'上证指数'/'沪深300ETF'/'黄金'",
      "asset_code": "代码，如'000001.SH'/'510300'，不确定则留空''",
      "level_type": "支撑位/压力位/目标价/止损位",
      "price": 数字（只填数字，不含单位）,
      "note": "简短说明这个点位的意义"
    }
  ]
}

注意：
- directional_views 如果文章没有明确方向性判断，返回空数组[]
- key_price_levels 如果没有明确提到具体价格/点位数字，返回空数组[]
- 不要从"举例""假设""如果"中提取观点，只提取博主明确表达的判断
"""

# ── Prompt：第二步，生成投资建议 ──────────────────────────────
ADVICE_SYSTEM = """你是一个严谨的个人投资助手，为一个关注白银、上证指数、科创50、创业板指的投资者服务。

你的建议需要整合三层信息：
1. 博主长期核心框架（跨文章坚守的原则和关键点位）
2. 用户自行设定的入手区间（博主没给具体买入价，用户自己设的）
3. 当前实时行情 + 新文章观点

生成结构化建议，格式如下：
📌 博主框架回顾 — 一句话概括博主对该标的的长期判断
💰 市价 vs 入手区间 — **这是最重要的部分**。明确计算当前价格与用户入手区间的距离，判断是否在区间内
📄 本文新观点 — 新文章是否强化/弱化了框架
🎯 操作建议 — 结合以上信息给出具体行动（等待/分批建仓/加仓/减仓）
⚠️ 风险提示 — 必须包含

语言简洁，用具体数字说话，不要模糊表述。"""


def extract_signals(article: dict) -> dict | None:
    """
    第一步：从文章中提取结构化信号
    返回包含 summary, is_actionable, directional_views, key_price_levels 的字典
    """
    prompt = f"""请分析以下投资文章，严格按照JSON格式输出：

标题：{article['title']}
发布时间：{article['publish_date']}

正文：
{article['content']}
"""
    try:
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content.strip()

        # 清理可能的markdown代码块包裹
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        signals = json.loads(raw)
        logger.info(f"信号提取成功：{len(signals.get('directional_views', []))}个方向观点，"
                    f"{len(signals.get('key_price_levels', []))}个关键点位")
        return signals

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}\n原始输出: {raw}")
        return None
    except Exception as e:
        logger.exception(f"DeepSeek API调用失败: {e}")
        return None


def generate_investment_advice(article: dict, signals: dict,
                                historical_views: list, active_levels: list,
                                market_snapshot: str = "") -> str:
    """
    第二步：结合博主长期框架 + 用户入手区间 + 历史数据库 + 实时行情 → 复合建议
    """
    # ── 博主长期框架 ──
    framework_text = BLOGGER_FRAMEWORK

    # ── 用户入手区间 + 距离计算 ──
    entry_text = "【你设定的入手区间】\n"
    for asset, zone in USER_ENTRY_ZONES.items():
        if zone:
            entry_text += f"• {asset}：{zone['low']} - {zone['high']} {zone['unit']}（{zone['note']}）\n"
        else:
            entry_text += f"• {asset}：未设定（待用户补充）\n"

    # ── 历史观点摘要 ──
    history_text = ""
    if historical_views:
        history_text = "【博主历史框架（数据库中最新有效观点）】\n"
        for v in historical_views[:8]:
            history_text += f"• {v['asset_class']} → {v['direction']}（{v['confidence']}置信度）：{v['core_logic']}\n"
    else:
        history_text = "【博主历史框架】暂无历史数据\n"

    # ── 关键点位摘要 ──
    levels_text = ""
    if active_levels:
        levels_text = "【数据库中未触发的关键点位】\n"
        for lvl in active_levels[:8]:
            mention = f"（被提及{lvl['mention_count']}次）" if lvl['mention_count'] > 1 else ""
            levels_text += f"• {lvl['asset_name']} {lvl['level_type']} {lvl['price']}{mention}：{lvl['note']}\n"
    else:
        levels_text = "【关键点位】暂无历史点位数据\n"

    # ── 本文新观点 ──
    new_views_text = "【本文新观点】\n"
    for v in signals.get("directional_views", []):
        new_views_text += f"• {v['asset_class']} → {v['direction']}（{v['confidence']}）：{v['core_logic']}\n"

    new_levels_text = "【本文新点位】\n"
    for lvl in signals.get("key_price_levels", []):
        new_levels_text += f"• {lvl['asset_name']} {lvl['level_type']} {lvl['price']}：{lvl['note']}\n"

    # ── 实时行情 ──
    market_text = market_snapshot if market_snapshot else "【当前市场行情】暂未获取到实时行情\n"

    prompt = f"""请根据以下信息，为用户的四个关注标的（白银 > 上证指数 > 科创50 > 创业板指）生成投资建议：

{framework_text}

{entry_text}

{market_text}

{history_text}

{levels_text}

{new_views_text}

{new_levels_text}

【本文摘要】
{signals.get('summary', '')}

【用户投资约束】
{INVESTMENT_PROFILE}

请按标的逐一分析，重点是白银。每个标的按以下结构：
📌 博主框架回顾
💰 市价 vs 入手区间（计算具体距离，判断是否在区间内）
📄 本文新观点
🎯 操作建议
⚠️ 风险提示
"""
    try:
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": ADVICE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        advice = resp.choices[0].message.content.strip()
        logger.info("投资建议生成成功")
        return advice

    except Exception as e:
        logger.exception(f"生成建议失败: {e}")
        return "⚠️ 投资建议生成失败，请检查DeepSeek API配置。"
