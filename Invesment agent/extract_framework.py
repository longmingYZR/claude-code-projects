"""
一次性脚本：分析所有已入库文章，提炼博主核心投资框架
聚焦四个标的：白银、上证指数、科创50、创业板指
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from database import get_conn
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from openai import OpenAI

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

# 1. 读取所有文章
conn = get_conn()
rows = conn.execute('SELECT id, title, summary, raw_signals FROM articles ORDER BY id').fetchall()
conn.close()

articles_text = ""
for r in rows:
    articles_text += f"""
=== 文章 {r['id']} ===
标题：{r['title']}
AI摘要：{r['summary']}
原始信号：{r['raw_signals']}
"""

print(f"共 {len(rows)} 篇文章，开始提取核心框架...\n")

# 2. 喂给 DeepSeek
prompt = f"""你是一个投资分析助手。请仔细阅读以下投资博主的所有文章摘要和信号，提炼出该博主**长期坚守、跨文章反复出现**的核心投资框架。

请重点聚焦以下四个标的（按优先级）：
1. 白银（最重要）
2. 上证指数
3. 科创50
4. 创业板指

对每个标的，请提取：
- **核心观点**：博主长期坚持的方向性判断（如"白银长期必涨"、"A股牛市未结束"）
- **关键点位**：博主反复提到的价格目标、支撑位、压力位（标注在哪几篇文章中出现）
- **入手策略**：博主是否给出了具体的买入区间/条件？如果有，是什么？如果没有，明确指出"博主未给出入手区间"
- **投资原则**：博主操作这个标的时坚守的纪律（如"绝不追高"、"回调到XX均线才买"、"仓位不超过XX"）

请用清晰的结构化格式输出，方便后续程序化使用。

以下是所有文章数据：
{articles_text}
"""

resp = client.chat.completions.create(
    model=DEEPSEEK_MODEL,
    messages=[
        {"role": "system", "content": "你是一个专业的投资分析助手。请仔细阅读博主的文章，提炼出长期坚守的核心投资框架。只输出分析结果，不要寒暄。"},
        {"role": "user", "content": prompt},
    ],
    temperature=0.3,
    max_tokens=4000,
)

result = resp.choices[0].message.content.strip()
print(result)

# 保存到文件
with open("framework_output.txt", "w", encoding="utf-8") as f:
    f.write(result)
print("\n\n✅ 结果已保存到 framework_output.txt")
