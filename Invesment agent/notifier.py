"""
notifier.py — 飞书消息推送
"""

import requests
import logging
from datetime import datetime
from config import FEISHU_WEBHOOK

logger = logging.getLogger(__name__)


def send_feishu_message(title: str, article_title: str, article_url: str,
                         summary: str, advice: str, has_signals: bool):
    """
    发送富文本飞书消息
    """
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 构建消息体（飞书卡片格式）
    card = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📈 {title}"
                },
                "template": "blue" if has_signals else "grey"
            },
            "elements": [
                # 文章信息
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📄 来源文章**\n[{article_title}]({article_url})\n\n**🕐 分析时间**\n{today}"
                    }
                },
                {"tag": "hr"},
                # 文章摘要
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📝 文章摘要**\n{summary}"
                    }
                },
                {"tag": "hr"},
                # 投资建议
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**🧠 投资分析与建议**\n{advice}"
                    }
                },
                {"tag": "hr"},
                # 免责声明
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "⚠️ 以上内容由AI自动生成，仅供参考，不构成投资建议。请结合自身判断做最终决策。"
                        }
                    ]
                }
            ]
        }
    }

    try:
        resp = requests.post(FEISHU_WEBHOOK, json=card, timeout=10)
        result = resp.json()
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            logger.info("飞书消息发送成功")
            return True
        else:
            logger.error(f"飞书发送失败: {result}")
            # 降级为纯文本发送
            return send_feishu_text(f"【投资Agent】{title}\n\n{summary}\n\n{advice}")
    except Exception as e:
        logger.exception(f"飞书请求异常: {e}")
        return False


def send_feishu_text(text: str) -> bool:
    """降级方案：发送纯文本消息"""
    payload = {
        "msg_type": "text",
        "content": {"text": text}
    }
    try:
        resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.exception(f"飞书纯文本发送也失败了: {e}")
        return False


def send_error_alert(error_msg: str):
    """发送错误通知"""
    send_feishu_text(f"⚠️ 投资Agent运行出错\n\n{error_msg}\n\n请检查日志：logs/agent.log")
