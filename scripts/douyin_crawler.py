#!/usr/bin/env python3
"""
表达练习素材生成器
- 每日轮换一个表达练习主题
- 从抖音热榜中选出3个最适合该主题的热点话题
- 为每个话题生成练习角度建议
"""

import json
import ssl
import urllib.request
import urllib.error
import urllib.parse
import os
from datetime import datetime, date

# ============ 配置 ============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "hot_videos.json")

DOUYIN_HOT_API = "https://www.douyin.com/aweme/v1/web/hot/search/list/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.douyin.com/hot",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

# ============ 表达练习主题库 ============
# 7个主题，按星期轮换
THEMES = [
    {
        "name": "观点输出",
        "icon": "🎯",
        "desc": "选定一个热点，明确表达你的立场",
        "prompt": "从下面3个话题中选1个，用60秒表达观点：1.亮明立场 2.给出2个理由 3.一个行动建议",
        "tips": ["开头直接亮观点，不绕弯子", "每个理由配一个具体例子", "结尾给行动建议，让观众有获得感"],
        "angle_template": "就「{title}」这个话题，先说大多数人怎么看，再说你为什么同意或不同意，给出你的理由",
    },
    {
        "name": "故事讲述",
        "icon": "📖",
        "desc": "把热点变成一个有冲突的故事",
        "prompt": "选1个话题，把它讲成一个故事：开头设悬念 → 中间制造冲突 → 结尾给反转或感悟",
        "tips": ["用第一人称更有代入感", "加入细节让故事有画面感", "结尾留一个让人回味的点"],
        "angle_template": "把「{title}」改编成一个故事：找到事件中的人，讲他面对的冲突和选择，最后给出感悟",
    },
    {
        "name": "知识科普",
        "icon": "🔬",
        "desc": "把复杂的热点用大白话讲明白",
        "prompt": "选1个话题，假设你在跟一个10岁小孩解释：是什么 → 为什么重要 → 对我们有什么影响",
        "tips": ["用一个生活化的比喻开场", "每讲一个概念配一个例子", "最后总结一句金句方便记忆"],
        "angle_template": "用大白话解释「{title}」：它到底是什么，为什么发生，对普通人有什么影响",
    },
    {
        "name": "情感共鸣",
        "icon": "💗",
        "desc": "找到热点里的情绪，说出大家想说的话",
        "prompt": "选1个话题，找到最触动你的情绪点：描述场景 → 放大情绪 → 说出现众心里的话",
        "tips": ["先描述一个具体场景再谈感受", "用'你是不是也...'引导共鸣", "情绪要真，不要过度煽情"],
        "angle_template": "围绕「{title}」，找到普通人最真实的情绪，用'我看到...我想到...你呢'的结构表达",
    },
    {
        "name": "反驳辩论",
        "icon": "⚔️",
        "desc": "站在对立面，把少数派观点讲清楚",
        "prompt": "选1个话题，故意站在多数人的反面：先复述主流观点 → 再说'但是' → 给出你的反向论证",
        "tips": ["先公平复述对方观点再反驳", "反驳要有事实依据不是抬杠", "结尾可以留一个开放问题"],
        "angle_template": "关于「{title}」，大多数人支持A观点，你来论证为什么B观点也有道理",
    },
    {
        "name": "即兴点评",
        "icon": "⚡",
        "desc": "60秒不准备，张嘴就评",
        "prompt": "选1个话题，打开计时器，60秒内完成：是什么 → 我的看法 → 一个启发",
        "tips": ["不要写稿，想到什么说什么", "语速可以慢，但不要停顿太久", "录完听一遍，标记可以改进的地方"],
        "angle_template": "看到「{title}」这个话题，你第一反应是什么？60秒内说出来，不要修改不要重来",
    },
    {
        "name": "场景演绎",
        "icon": "🎭",
        "desc": "设一个角色，从他的视角表达",
        "prompt": "选1个话题，设定一个相关角色，从他/她的视角讲1分钟：我是谁 → 我经历了什么 → 我的感受",
        "tips": ["角色要具体：职业、年龄、处境", "用角色的语气和用词说话", "可以加一点表演让画面更强"],
        "angle_template": "围绕「{title}」，设定一个当事人角色，从他的第一视角讲述这件事的经过和感受",
    },
]


def get_today_theme():
    """根据日期获取今天的主题（7天轮换）"""
    today = date.today()
    day_offset = today.toordinal()  # 从公元1年开始的天数
    theme_index = day_offset % len(THEMES)
    return THEMES[theme_index], theme_index


def fetch_douyin_hot():
    """获取抖音热榜数据"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(DOUYIN_HOT_API, headers=HEADERS)

    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        raw = resp.read()
        data = json.loads(raw)
        return data
    except Exception as e:
        print(f"[error] fetch failed: {e}")
        return None


def parse_hot_items(data):
    """解析热榜，返回简洁的话题列表"""
    if not data:
        return []

    inner = data.get("data", {})
    word_list = inner.get("word_list", [])
    trending_list = inner.get("trending_list", [])
    all_items = word_list if word_list else trending_list

    items = []
    for i, item in enumerate(all_items):
        title = item.get("word", "")
        hot_value = item.get("hot_value", 0)

        if hot_value >= 10000:
            hot_str = f"{hot_value / 10000:.1f}万"
        else:
            hot_str = str(hot_value)

        if hot_value >= 5000000:
            level = "爆"
        elif hot_value >= 1000000:
            level = "热"
        else:
            level = "新"

        cover_urls = item.get("word_cover", {}).get("url_list", [])

        items.append({
            "rank": i + 1,
            "title": title,
            "hot_value": hot_value,
            "hot_str": hot_str,
            "level": level,
            "cover_url": cover_urls[0] if cover_urls else "",
            "search_url": f"https://www.douyin.com/search/{urllib.parse.quote(title)}" if title else "",
        })

    return items


def select_topics_for_theme(hot_items, theme, theme_index):
    """从热榜中选出3个最适合当前主题的话题"""
    if not hot_items:
        return []

    # 根据主题索引选择不同排名区间的话题，确保每天有变化
    # 主题0(观点): 选排名1,4,7  - 高热度话题适合表达观点
    # 主题1(故事): 选排名2,5,8  - 中上热度适合讲故事
    # 主题2(科普): 选排名3,6,9  - 各热度段都有
    # 主题3(情感): 选排名1,5,10 - 跨度大有层次
    # 主题4(反驳): 选排名2,6,9  - 中段话题有讨论空间
    # 主题5(即兴): 选排名1,3,5  - 高热度适合即兴
    # 主题6(演绎): 选排名2,7,10 - 多样性

    rank_patterns = [
        [1, 4, 7],   # 观点输出
        [2, 5, 8],   # 故事讲述
        [3, 6, 9],   # 知识科普
        [1, 5, 10],  # 情感共鸣
        [2, 6, 9],   # 反驳辩论
        [1, 3, 5],   # 即兴点评
        [2, 7, 10],  # 场景演绎
    ]

    ranks = rank_patterns[theme_index % len(rank_patterns)]

    selected = []
    for rank in ranks:
        # 找到对应排名的话题（rank从1开始）
        if rank <= len(hot_items):
            item = hot_items[rank - 1]
            # 生成练习角度
            angle = theme["angle_template"].format(title=item["title"])
            selected.append({
                "title": item["title"],
                "hot_str": item["hot_str"],
                "level": item["level"],
                "rank": item["rank"],
                "search_url": item["search_url"],
                "practice_angle": angle,
            })

    return selected


def save_data(theme, theme_index, topics):
    """保存数据"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    output = {
        "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "date": date.today().isoformat(),
        "theme": {
            "name": theme["name"],
            "icon": theme["icon"],
            "desc": theme["desc"],
            "prompt": theme["prompt"],
            "tips": theme["tips"],
        },
        "topics": topics,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[ok] saved to {OUTPUT_FILE}")


def load_existing():
    """加载已有数据"""
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def main():
    print("=" * 50)
    print("  expression practice - zihao workbench")
    print("=" * 50)
    print(f"  time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 获取今日主题
    theme, theme_index = get_today_theme()
    print(f"[1/3] today theme: {theme['icon']} {theme['name']}")
    print(f"      desc: {theme['desc']}")
    print()

    # 2. 获取热榜
    print("[2/3] fetching douyin hot list...")
    raw_data = fetch_douyin_hot()
    hot_items = parse_hot_items(raw_data) if raw_data else []

    if hot_items:
        print(f"      got {len(hot_items)} hot items")

        # 3. 选话题
        print("[3/3] selecting topics for today's theme...")
        topics = select_topics_for_theme(hot_items, theme, theme_index)

        if topics:
            save_data(theme, theme_index, topics)

            print()
            print(f"  {theme['icon']} {theme['name']} - {theme['desc']}")
            print(f"  prompt: {theme['prompt']}")
            print()
            print("  selected topics:")
            print("  " + "-" * 46)
            for t in topics:
                print(f"  #{t['rank']} [{t['level']}] {t['title'][:25]}")
                print(f"       hot: {t['hot_str']}")
            print("  " + "-" * 46)
            print()
            print("  done!")
            return True

    # 回退
    print()
    print("[fallback] loading existing data...")
    existing = load_existing()
    if existing and existing.get("topics"):
        print(f"  loaded cache (last: {existing.get('fetch_time', 'unknown')})")
        return True
    else:
        print("[fail] no data available")
        return False


if __name__ == "__main__":
    main()
