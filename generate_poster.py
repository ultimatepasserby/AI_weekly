#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import textwrap

def fetch_ai_news():
    """调用 DeepSeek API（强制联网搜索），返回上周 AI 新闻的 JSON 数据"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
        "Content-Type": "application/json"
    }

    # 计算上周一和上周日（完全属于过去的一周）
    today = datetime.now()
    offset_to_this_monday = today.weekday()          # 本周一偏移量（周一=0）
    this_monday = today - timedelta(days=offset_to_this_monday)
    last_monday = this_monday - timedelta(days=7)
    last_sunday = last_monday + timedelta(days=6)

    week_start_str = last_monday.strftime("%Y年%m月%d日")
    week_end_str = last_sunday.strftime("%Y年%m月%d日")
    week_range = f"{week_start_str} - {week_end_str}"

    prompt = f"""今天是{today.strftime('%Y年%m月%d日')}。请搜索并总结上周（{week_range}）人工智能领域最重要的5条新闻或技术突破。
要求：
1. 输出 JSON 格式，不要有其他任何额外文字。
2. 结构如下：
{{
    "week": "{week_range}",
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

    # 清理可能包裹的 markdown
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    news_data = json.loads(content)
    # 保证返回的键名一致
    if "week" not in news_data:
        news_data["week"] = week_range
    return news_data


def generate_background_image(summary_title):
    """生成一张不含文字的科技感背景图（16:9，4K）"""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # 背景图提示词
    prompt = f"""一张用于 AI 新闻周报海报的纯背景图，不要包含任何文字或数字。
风格：科技感、蓝紫渐变、抽象数据流线条、干净的信息图区域留白。
主题暗示：{summary_title}（仅作风格参考，不出现文字）。
尺寸：16:9，4K 分辨率，高质量。"""

    response = client.images.generate(
        model="gpt-image-2",           # 可改为 "dall-e-3" 或 ideogram
        prompt=prompt,
        size="1792x1024",              # 16:9 接近 4K
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
    """在背景图上叠加标题、新闻列表、日期等信息"""
    bg = Image.open(bg_path).convert("RGB")
    draw = ImageDraw.Draw(bg)
    width, height = bg.size

    # 中文字体处理（优先使用仓库内字体，否则下载）
    font_local = "NotoSansCJKsc-Regular.otf"
    if not os.path.exists(font_local):
        font_url = "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
        print("下载中文字体...")
        r = requests.get(font_url)
        with open(font_local, "wb") as f:
            f.write(r.content)

    title_font = ImageFont.truetype(font_local, 70)
    sub_font = ImageFont.truetype(font_local, 45)
    news_title_font = ImageFont.truetype(font_local, 35)
    news_summary_font = ImageFont.truetype(font_local, 25)

    # 主标题
    draw.text((width // 2, 70), "AI 一周热点", fill="white", anchor="mt", font=title_font)
    # 周范围
    week_text = news_data["week"]
    draw.text((width // 2, 150), week_text, fill="#CCCCCC", anchor="mt", font=sub_font)
    # 一句话总结
    summary_text = news_data["summary_title"]
    draw.text((width // 2, 220), summary_text, fill="#FFD966", anchor="mt", font=sub_font)

    # 新闻条目
    y = 320
    for i, item in enumerate(news_data["news"], 1):
        # 标题
        title_line = f"{i}. {item['title']}"
        draw.text((80, y), title_line, fill="white", font=news_title_font)
        y += 50
        # 摘要（自动换行）
        wrapped = textwrap.wrap(item["summary"], width=55)
        for line in wrapped:
            draw.text((100, y), line, fill="#E0E0E0", font=news_summary_font)
            y += 35
        y += 25

    # 底部信息
    footer = f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 数据来源：DeepSeek 联网搜索 | 个人作品集"
    footer_font = ImageFont.truetype(font_local, 20)
    draw.text((width // 2, height - 40), footer, fill="#AAAAAA", anchor="mb", font=footer_font)

    bg.save(output_path)
    print(f"海报已保存：{output_path}")
    return output_path

def generate_index_html(poster_filename):
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Weekly Poster</title>
    <style>
        body {{
            background: #0a0a2a;
            color: white;
            font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
            text-align: center;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        img {{
            max-width: 100%;
            border-radius: 24px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.4);
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 40px;
            font-size: 14px;
            color: #888;
        }}
    </style>
</head>
<body>
<div class="container">
    <h1> AI 周报作品集</h1>
    <p>每周自动生成，回顾上周AI领域重要动态</p>
    <img src="{poster_filename}" alt="AI Weekly Poster">
    <div class="footer">自动更新于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
</div>
</body>
</html>""")


# ---------- 主流程 ----------
def main():
    print(" Step 1: 联网搜索上周 AI 新闻...")
    news = fetch_ai_news()
    print(f"✅ 获取成功，周范围：{news['week']}")
    print(f"   摘要：{news['summary_title']}")

    print(" Step 2: 调用 GPT Image 2 生成背景图...")
    bg_path = generate_background_image(news["summary_title"])
    print("✅ 背景图生成完成")

    print(" Step 3: 合成最终海报...")
    poster_path = compose_poster(bg_path, news)
    print("✅ 海报合成完成")

    print(" Step 4: 生成 GitHub Pages 展示页...")
    generate_index_html(poster_path)
    print("✅ 全部完成！")


if __name__ == "__main__":
    main()