import os
import json
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap
from datetime import datetime, timedelta

def fetch_ai_news():
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
        "Content-Type": "application/json"
    }
    now = datetime.now()

    days_to_last_monday = (now.weekday() + 7) % 7 + 1  
    last_monday = now - timedelta(days=days_to_last_monday)
    last_sunday = last_monday + timedelta(days=6)
    week_range_str = f"{last_monday.strftime('%Y年%m月%d日')} - {last_sunday.strftime('%m月%d日')}"
    
    prompt = f"""今天是{now.strftime('%Y年%m月%d日')}。请搜索并总结上周（{week_range_str}）人工智能领域最重要的5条新闻或技术突破。
要求：
1. 输出JSON格式，不要有其他额外文字。
2. 结构如下：
{{
    "week": "{week_range_str}",
    "summary_title": "一句话总结本周AI热点（20字以内）",
    "news": [
        {{"title": "新闻标题（15字以内）", "summary": "一句话摘要（50字以内）"}},
        ...
    ]
}}
注意：必须使用联网搜索获取实时信息。"""
    
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "extra_body": {"enable_search": True}
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    # 清理可能包裹的markdown
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    return json.loads(content)


def generate_background(summary_title, month_str):
    # 注意：需要 openai>=1.0.0 库，且 API key 支持图像生成
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    
    prompt = f"""一张用于月度AI新闻海报的纯背景图，不要包含任何文字或数字。
风格：科技感、蓝紫渐变、抽象数据流线条、干净的信息图区域留白。
主题暗示：{summary_title}（仅作风格参考，不出现文字）。
尺寸：16:9，4K分辨率。
"""
    response = client.images.generate(
        model="gpt-image-2",  # 请确认模型名称
        prompt=prompt,
        size="1792x1024",     # 16:9近似尺寸
        quality="hd",
        n=1,
    )
    image_url = response.data[0].url
    img_data = requests.get(image_url).content
    bg_path = "background.png"
    with open(bg_path, "wb") as f:
        f.write(img_data)
    return bg_path

def compose_poster(bg_path, news_data, output_path="final_poster.png"):
    bg = Image.open(bg_path).convert("RGB")
    draw = ImageDraw.Draw(bg)
    width, height = bg.size
    
    font_url = "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
    font_file = "NotoSansCJKsc-Regular.otf"
    if not os.path.exists(font_file):
        r = requests.get(font_url)
        with open(font_file, "wb") as f:
            f.write(r.content)
    
    title_font = ImageFont.truetype(font_file, 70)
    sub_font = ImageFont.truetype(font_file, 45)
    news_title_font = ImageFont.truetype(font_file, 35)
    news_summary_font = ImageFont.truetype(font_file, 25)
    
    draw.text((width//2, 70), "🤖 AI 月度热点", fill="white", anchor="mt", font=title_font)
    draw.text((width//2, 150), news_data["month"], fill="#CCCCCC", anchor="mt", font=sub_font)
    draw.text((width//2, 220), news_data["summary_title"], fill="#FFD966", anchor="mt", font=sub_font)
    
    y = 320
    for i, item in enumerate(news_data["news"], 1):
        draw.text((80, y), f"{i}. {item['title']}", fill="white", font=news_title_font)
        y += 50
        wrapped = textwrap.wrap(item["summary"], width=55)
        for line in wrapped:
            draw.text((100, y), line, fill="#E0E0E0", font=news_summary_font)
            y += 35
        y += 25
    
    footer = f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 数据来源：DeepSeek | 个人作品集"
    draw.text((width//2, height-40), footer, fill="#AAAAAA", anchor="mb", font=ImageFont.truetype(font_file, 20))
    
    bg.save(output_path)
    return output_path

# ---------- 主函数 ----------
def main():
    print("联网搜索本月AI新闻...")
    news = fetch_ai_news()
    print("新闻提取完成")
    
    print("生成背景图...")
    bg = generate_background(news["summary_title"], news["month"])
    print("背景图生成完成")
    
    print("合成最终海报...")
    poster = compose_poster(bg, news)
    print(f"海报已保存: {poster}")
    
    # 同时生成一个简单的 HTML 展示页
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>AI Monthly Poster</title><style>body{{text-align:center;background:#0a0a2a;color:white;}} img{{max-width:90%;border-radius:16px;margin:20px;}}</style></head>
<body><h1>AI 月度作品集</h1><img src="{poster}" alt="AI Monthly Poster"><p>自动更新于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p></body>
</html>""")
    print("index.html已生成")

if __name__ == "__main__":
    main()
