# ============================================================
#  配置文件 — 所有需要你修改的参数都在这里
# ============================================================

# ── 知乎 Cookie ─────────────────────────────────────────────
# 从浏览器 F12 → Network → 文章页请求 → Request Headers → 复制整行 cookie:
# z_c0=xxx; _zap=xxx; d_c0=xxx; __utmz=xxx; ...
ZHIHU_COOKIE = (
    "__snaker_id=rplf4QqDMfyUipey; "
    "SESSIONID=2PGwngFRohHifWzeA8QeE2kY1naTIY0GYXO8UMY5mm; "
    "JOID=WI4QC0hd-a3k96XQFJ099NHII_ZtB4Djl5jvxxcxemoxZ2kTd9g1o7yqN56FpJymuBlv95YOucfrzGpVl_pUU=; "
    "osd=W1sQAklc_K3t9qTVfjQ89dTlnvdSaoDqlpnqvx4vxoOyzlylSTg8q4_3qNd7ff-Jw2qAk_9wYeqZFhRXHP_c_rEQ=; "
    "_xsrf=LekZzvWylVOKZHcs7WdKkeSQ25e4T3hlZ; "
    "_zap=17a2de4a-c883-464a-9610-843314f7c593; "
    "d_c0=3nMUovMKKBuPTqlko5Y0zt44COC4LV3hO7c=|1766303015; "
    "Hm_lvt_98beee57fd2ef70ccdd5ca52b9740c49=1776178273,1778500155; "
    "HMACCOUNT=571C731579E51FBF; "
    "captcha_session_v2=2|1:0|10:1778500154|18:captcha_session_v2|88:OUg1akMxRTZsL1RzbXN4My91aitYMldlc3N4dWtuY1dEnhuSoI0ai9keldvWDdzBXdxcnZWZU0oCvF2WXZKWA==|b6bd25647a3a6919fd04a55473aa642f0fb3962e4b58b0903aca37c436cc542; "
    "_zse_ck=005_VC8gUOjudwGkjwnKeqRxskiqeHNIV/jvqTDEYoJOSQXrVrd03Mzlo1imL9dMzGITgKWIOUteNj5VeDiueRF6/NmuQQf=XPhTH3Tl/cF64=XACL067LKYxsUcangzo6iXJ-8m/PPUu1hUA8eleL4hpw11ufhDVx5t8NnnRUHAkhkcpB4qb2YaNcS60rsMJJCazJ85CSRRdgQ6ngSP0Xm3GOdshhsAF00elRs0jBIP6vD58XgAy1yW0b89PJtdsnZFZ; "
    "BEC=fct13dc7850b2e749d88c66e883fdd0e4; "
    "z_c0=2|1:0|10:1778500199|4:z_c0|92:MiaXOVEFUbJUQBUFQURIY3hTaTh3cVFHEvIBQUFCZOFsVk5UQkR2YWdBtKfpWeMtMc0dwcoINUDd2djB2QVFEsu1uaXJB|5472361df0792a4663db01bc217ea9c694275c537ce5eaa5acab37cbc78148e0; "
    "Hm_lpvt_98beee57fd2ef70ccdd5ca52b9740c49=1778500201"
)


# ── 知乎专栏配置 ─────────────────────────────────────────────
# 专栏ID（从文章页提取，或从专栏URL中获取）
COLUMN_ID = "c_1962592595592081509"
COLUMN_URL = f"https://www.zhihu.com/column/{COLUMN_ID}"

# 手动指定的文章URL（自动发现会在此基础上补充新文章）
ARTICLE_URLS = [
    "https://zhuanlan.zhihu.com/p/2037049895828321582",
]

# ── DeepSeek API ─────────────────────────────────────────────
DEEPSEEK_API_KEY = "DEEPSEEK_API_KEY_REDACTED_PLEASE_ROTATE"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# ── 飞书 Webhook ─────────────────────────────────────────────
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/62263665-859f-4e37-8457-3a969c1e8bc8"

# ── 你的投资约束（用于生成建议时注入给AI）──────────────────────
INVESTMENT_PROFILE = """
- 总本金：10万元人民币（AI建议中请用"总资金"表示，不要写具体金额）
- 单只标的最大仓位：不超过总资金的20%
- 风险偏好：中等，可接受短期波动但不做高杠杆
- 关注标的（按优先级）：
  1. 白银（最重要，主要操作标的）
  2. 上证指数（000001.SH）
  3. 科创50（000688）
  4. 沪深300（000300）
  5. 创业板指（399006）
- 禁止标的：ST/*ST股票、场外配资产品
"""

# ── 博主核心投资框架（从所有历史文章中提炼，随新文章持续更新）─────
# 这是博主跨文章长期坚守的原则，不同于每篇文章的短期观点
BLOGGER_FRAMEWORK = """
【博主长期核心框架】

★ 白银（最重要标的）
  长期方向：看多。逻辑 — 全球资金泛滥+经济疲弱，白银盘子小适合炒作，金银比显示脉冲机会。
  关键点位：
    · 中期目标 $115/盎司（2026年目标，博主反复提及8次以上）
    · 长期目标 $150-200/盎司
    · 极端支撑 $10/盎司（泡沫破裂后才可能触及）
  操作原则：绝不重仓、绝不追高、容忍极端波动、中长期持有
  博主未给出具体入手区间（由用户自行设定）

★ 上证指数
  长期方向：看多。逻辑 — A股牛市未结束，流动性风险暂时解除。
  关键点位：长期目标 8100 点（未来一年多）
  操作原则：选对板块、关注博主每周"规划图"更新
  博主未给出具体入手区间（由用户自行设定）

★ 科创50 / 创业板指
  博主在专栏中较少针对这两个指数做具体分析，无长期点位判断。
  操作以用户自行设定的规则为准。
"""

# ── 用户自定义投资规则（你设定的入手区间，博主没给的你自己定）─────
# 系统会把当前市价与这些区间对比，给出"距离入手区还有多远"的建议
USER_ENTRY_ZONES = {
    "白银": {"low": 65, "high": 70, "unit": "美元/盎司", "note": "用户设定入手区间"},
    "上证指数": None,   # 待设定，如 {"low": 3000, "high": 3200, "unit": "点", "note": "..."}
    "科创50": None,
    "创业板指": None,
}

# ── 数据库路径 ────────────────────────────────────────────────
DB_PATH = "investment_agent.db"

# ── 日志路径 ─────────────────────────────────────────────────
LOG_PATH = "logs/agent.log"
