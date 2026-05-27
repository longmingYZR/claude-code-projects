# 知乎投资博主 Agent — 项目交接文档

> 本文档用于向 Claude Code 交接项目现状、已知问题和下一步任务。
> 请 Claude Code 阅读本文档后，直接进入问题修复和功能完善，无需重新设计架构。

---

## 一、项目目标

自动抓取知乎付费专栏文章 → DeepSeek AI 分析提取投资信号 → 积累博主观点数据库 → 推送飞书投资建议卡片。

最终效果：每天早上 8:30 自动运行，飞书收到一张包含"博主历史框架 + 最新观点 + 具体操作建议"的投资分析卡片。

---

## 二、技术栈

| 组件 | 选型 |
|------|------|
| 语言 | Python 3.x（Windows 本地运行） |
| AI 分析 | DeepSeek API（兼容 OpenAI SDK，model: deepseek-chat） |
| 数据库 | SQLite（本地文件，investment_agent.db） |
| 推送 | 飞书自定义机器人 Webhook |
| 定时 | APScheduler |
| 抓取 | requests + BeautifulSoup4 |

---

## 三、项目文件结构

```
zhihu_agent/
├── config.py          ← 所有配置参数（Cookie、API Key、URL列表、投资约束）
├── agent.py           ← 主程序入口，流程编排
├── fetcher.py         ← 知乎文章抓取（⚠️ 当前有问题，见第四节）
├── analyzer.py        ← DeepSeek AI 分析，两步：提取信号 + 生成建议
├── database.py        ← SQLite 三张表的读写操作
├── notifier.py        ← 飞书富文本卡片推送
├── requirements.txt   ← 依赖：openai, requests, beautifulsoup4, apscheduler, lxml
└── logs/              ← 运行日志（TimedRotatingFileHandler，保留7天）
```

---

## 四、当前已知问题（最优先修复）

### 🔴 问题1：知乎抓取 403 Forbidden

**现象：**
```
2026-05-11 15:37:41 [ERROR] fetcher — 403 Forbidden — Cookie可能已过期，请重新获取
```

**根本原因：**
当前 `fetcher.py` 只传了 `z_c0` 单个 Cookie 字段，不够。知乎对付费内容有额外防护，需要完整的浏览器 Cookie 字符串（包含 `_zap`、`d_c0`、`__utmz` 等多个字段）。

**修复方案：**
1. 修改 `config.py` 的 `ZHIHU_COOKIE`，改为接受完整 Cookie 字符串而非字典：
   ```python
   ZHIHU_COOKIE_STR = "z_c0=xxx; _zap=xxx; d_c0=xxx; ..."  # 从浏览器 Network 标签复制完整 cookie header
   ```
2. 修改 `fetcher.py`，将 Cookie 字符串直接设置到请求头：
   ```python
   HEADERS["Cookie"] = ZHIHU_COOKIE_STR
   ```
3. 同时建议在 Headers 中补充 `x-requested-with`、`sec-fetch-mode` 等字段，更接近真实浏览器请求。

**获取完整Cookie的方法：**
浏览器访问目标付费文章 → F12 → Network → 找到文章页面的 document 请求 → Request Headers → 复制整行 `cookie:` 的值。

---

## 五、数据库设计（已实现，可直接使用）

### 表1：articles（文章表）
```sql
CREATE TABLE articles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    url          TEXT UNIQUE NOT NULL,
    title        TEXT,
    publish_date TEXT,
    fetched_at   TEXT,
    summary      TEXT,
    raw_signals  TEXT,   -- JSON，AI原始分析结果
    processed    INTEGER DEFAULT 0
)
```

### 表2：directional_views（方向性观点表）
```sql
CREATE TABLE directional_views (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id   INTEGER,
    asset_class  TEXT,   -- "A股"/"港股"/"黄金"等
    direction    TEXT,   -- 看多/看空/震荡
    confidence   TEXT,   -- 高/中/低
    core_logic   TEXT,
    valid_from   TEXT,
    valid_until  TEXT,   -- NULL=仍有效
    is_latest    INTEGER DEFAULT 1,
    FOREIGN KEY(article_id) REFERENCES articles(id)
)
```

### 表3：key_price_levels（关键点位表）
```sql
CREATE TABLE key_price_levels (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id    INTEGER,
    asset_code    TEXT,   -- "000001.SH"/"510300"等
    asset_name    TEXT,
    level_type    TEXT,   -- 支撑位/压力位/目标价/止损位
    price         REAL,
    mention_count INTEGER DEFAULT 1,  -- 被多篇文章提及则累加
    triggered     INTEGER DEFAULT 0,
    triggered_time TEXT,
    note          TEXT,
    FOREIGN KEY(article_id) REFERENCES articles(id)
)
```

---

## 六、核心业务流程（已实现）

```
agent.py::process_article(url)
    │
    ├─ 1. is_article_processed() → 去重，已处理则跳过
    ├─ 2. fetcher.fetch_article(url) → 抓取正文  ⚠️ 当前卡在这里
    ├─ 3. analyzer.extract_signals(article) → DeepSeek 提取结构化信号
    │      返回: {summary, is_actionable, directional_views[], key_price_levels[]}
    ├─ 4. database.save_article() → 文章入库
    ├─ 5. database.upsert_directional_view() → 观点入库（同资产类别自动替换旧观点）
    ├─ 6. database.save_price_level() → 点位入库（相近价格累加mention_count）
    ├─ 7. 若 is_actionable=False → 仅入库，不推送
    ├─ 8. analyzer.generate_investment_advice() → 结合历史数据库生成复合建议
    └─ 9. notifier.send_feishu_message() → 推送飞书卡片
```

---

## 七、DeepSeek Prompt 设计（已实现）

**第一步提取 Prompt 要求 AI 返回严格 JSON：**
```json
{
  "summary": "文章核心观点的2-3句话摘要",
  "is_actionable": true/false,
  "directional_views": [
    {"asset_class": "A股", "direction": "看多", "confidence": "高", "core_logic": "..."}
  ],
  "key_price_levels": [
    {"asset_name": "上证指数", "asset_code": "000001.SH", "level_type": "支撑位", "price": 3000, "note": "..."}
  ]
}
```

**第二步建议 Prompt** 会注入：博主历史框架（数据库查询）+ 最新观点 + 用户投资约束，生成带emoji分节的飞书友好文本。

---

## 八、待完善功能（优先级排序）

### P0 — 解决抓取问题（阻塞主流程）
- [ ] 修复 fetcher.py，支持完整 Cookie 字符串
- [ ] 验证付费文章可以正常获取全文

### P1 — 核心功能补全
- [ ] **自动发现新文章**：当前 ARTICLE_URLS 需手动维护。目标：自动抓取专栏首页，发现新文章后自动加入处理队列。知乎专栏首页 URL 格式：`https://zhuanlan.zhihu.com/c_xxxxx`（需用户提供专栏ID）
- [ ] **AKShare 行情集成**：在生成建议时，自动拉取关键标的的实时/最新价格，注入 Prompt，让建议更贴合当下市场

### P2 — 体验优化
- [ ] **点位触发监控**：定时检查 key_price_levels 表中未触发点位 vs 实时行情，触发时单独推送预警飞书消息
- [ ] **飞书卡片优化**：当前卡片结构完整但样式简单，可增加颜色标注（看多绿/看空红）、折叠长文本
- [ ] **Cookie 过期提醒**：抓取返回 403 时，推送飞书提醒"Cookie已过期，请更新"，而非仅写日志

### P3 — 长期迭代
- [ ] Streamlit 本地看板（博主多空方向变化曲线、点位分布图）
- [ ] 多博主支持（database 已预留结构，需在 config 和流程中扩展）
- [ ] 飞书卡片交互（按钮回复"已执行/忽略"，记录决策日志）

---

## 九、配置项说明（config.py）

```python
ZHIHU_COOKIE       # 知乎登录凭证，需定期更新（约30天）
ARTICLE_URLS       # 要监控的文章URL列表，手动维护
DEEPSEEK_API_KEY   # DeepSeek 平台 API Key
DEEPSEEK_BASE_URL  # https://api.deepseek.com
DEEPSEEK_MODEL     # deepseek-chat
FEISHU_WEBHOOK     # 飞书机器人 Webhook URL（已配置）
INVESTMENT_PROFILE # 用户投资约束文本，注入 AI Prompt
DB_PATH            # investment_agent.db
LOG_PATH           # logs/agent.log
```

---

## 十、运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 手动处理所有配置文章（测试用）
python agent.py

# 处理单篇指定文章
python agent.py https://zhuanlan.zhihu.com/p/xxxx

# 强制重新处理（跳过去重检查）
python agent.py --force

# 启动定时模式（每天 08:30 自动运行）
python agent.py --scheduler
```

---

*文档生成时间：2026-05-11*
*当前状态：基础架构完整，主流程卡在知乎抓取 403 问题，修复后可端到端跑通*
