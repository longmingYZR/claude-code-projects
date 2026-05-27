# 知乎投资博主 Agent

自动抓取知乎付费专栏 → AI分析投资信号 → 积累博主观点数据库 → 推送飞书投资建议

---

## 项目结构

```
zhihu_agent/
├── config.py          ← ⭐ 你需要修改的配置文件
├── agent.py           ← 主程序入口
├── fetcher.py         ← 知乎文章抓取
├── analyzer.py        ← DeepSeek AI 分析
├── database.py        ← SQLite 数据库操作
├── notifier.py        ← 飞书推送
├── requirements.txt   ← 依赖列表
└── logs/              ← 运行日志（自动生成）
```

---

## 快速开始

### 第一步：安装依赖

打开命令提示符（CMD），进入项目目录，运行：

```bash
pip install -r requirements.txt
```

### 第二步：配置 config.py

打开 `config.py`，填写以下内容：

**① 知乎 Cookie（最重要）**

1. 浏览器打开 [zhihu.com](https://zhihu.com) 并登录你的付费账号
2. 打开目标付费文章 → F12 → Network → 找到文章页面的 document 请求
3. 在 Request Headers 中，复制整行 `cookie:` 的值
4. 粘贴到 config.py 的 `ZHIHU_COOKIE` 中

```python
ZHIHU_COOKIE = "z_c0=xxx; _zap=xxx; d_c0=xxx; ..."
```

> ⚠️ Cookie 有效期约 30 天，过期后需重新获取。仅 `z_c0` 不够，需要完整 Cookie 字符串。

**② DeepSeek API Key**

1. 访问 [platform.deepseek.com](https://platform.deepseek.com)
2. 注册/登录 → API Keys → 创建新的 Key
3. 填入 config.py：

```python
DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxxxx"
```

**③ 文章URL列表**

把你要分析的知乎专栏文章URL添加到列表：

```python
ARTICLE_URLS = [
    "https://zhuanlan.zhihu.com/p/xxxxxxxxxxxx",
    "https://zhuanlan.zhihu.com/p/xxxxxxxxxxxx",
]
```

**④ 投资约束（可选但推荐修改）**

根据你的实际情况修改 `INVESTMENT_PROFILE`。

---

### 第三步：运行

**手动运行一次（处理所有配置的文章）：**
```bash
python agent.py
```

**处理单篇指定文章：**
```bash
python agent.py https://zhuanlan.zhihu.com/p/xxxxxxxxxxxx
```

**强制重新处理（已处理过的文章默认跳过）：**
```bash
python agent.py --force
```

**启动定时模式（每天早上8:30自动运行）：**
```bash
python agent.py --scheduler
```

---

## 常见问题

**Q: 运行报错 `403 Forbidden`**
A: Cookie 已过期或不完整。从浏览器 Network 标签重新获取完整 cookie 字符串（不是仅 z_c0），填入 config.py 的 ZHIHU_COOKIE

**Q: 运行报错 `401 Unauthorized`**
A: 付费内容未解锁，或登录账号没有购买该专栏

**Q: 飞书没有收到消息**
A: 检查 logs/agent.log，确认是否有推送错误；同时确认飞书机器人已加入群组

**Q: 文章正文抓取为空**
A: 知乎可能更新了页面结构，在 GitHub Issues 反馈，或查看 fetcher.py 自行调整 CSS 选择器

---

## 数据库查看

数据存储在 `investment_agent.db`，可用 [DB Browser for SQLite](https://sqlitebrowser.org/) 打开查看。

三张核心表：
- `articles` — 所有已处理文章
- `directional_views` — 博主方向性观点历史
- `key_price_levels` — 关键价格点位

---

## 安全提醒

- Cookie 属于账号凭证，不要提交到 Git 或分享给他人
- 建议在 config.py 同目录创建 `.gitignore`，内容填 `config.py`
- 知乎 Cookie 定期更换，无需担心长期泄露风险
