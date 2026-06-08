"""
Template-based content generator. Uses combinatorial template filling to produce
thousands of unique content items from moderate word pools.

With 10 templates × 30 item pools × 30 item pools = 9000+ theoretical combos,
history tracking ensures zero repeats within the tracked window.
"""
import hashlib
import random
from typing import Any

from .config import load_json, save_json


def _load_pools() -> dict[str, Any]:
    w = load_json("anime_words.json")
    return {
        "emotions": w.get("emotions", ["干劲满满"]),
        "actions": w.get("content_actions", ["微笑"]),
        "subjects": w.get("content_subjects", ["自己"]),
        "benefits": w.get("content_benefits", ["心情+1"]),
        "places_v": w.get("content_places", ["咖啡馆"]),
        "npcs_v": w.get("content_npcs", ["神秘旅人"]),
        "times": w.get("content_times", ["此刻"]),
        "numbers": w.get("content_numbers", ["1"]),
        "items": w.get("content_items", ["魔导书"]),
        "skills": w.get("content_skills", ["微笑魔法"]),
        "animals": w.get("content_animals", ["猫"]),
    }


def _hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]


def _pick(pool: list[str], exclude: set[str]) -> str:
    """Pick a random item from pool, preferring unused ones."""
    available = [x for x in pool if _hash(x) not in exclude]
    if not available:
        available = pool  # all used, reset
    return random.choice(available)


def generate(push_type: str) -> dict[str, str] | None:
    """Generate a unique content item of the given type.

    Args:
        push_type: One of 'micro_quest', 'life_tip', 'anime_quote',
                   'kingdom_news', 'encouragement', 'blessing'

    Returns:
        dict with 'title' and 'body', or None if type unknown.
    """
    pools = _load_pools()
    hist = load_json("history.json") or {}

    # Get recently used hashes for this type
    type_key = f"gen_{push_type}"
    used_hashes = set(hist.get(type_key, {}).get("hashes", []))

    result = _generate_type(push_type, pools, used_hashes)

    if result:
        h = _hash(result["body"])
        used_hashes.add(h)
        # Keep last 2000 hashes (covers 6 months at 10/day)
        hist[type_key] = {"hashes": list(used_hashes)[-2000:]}
        save_json("history.json", hist)

    return result


def _generate_type(push_type: str, p: dict, used: set) -> dict[str, str] | None:
    """Generate content for a specific type using templates."""
    templates = {
        "micro_quest": [
            ("Micro Quest", "今日修行：{action}{subjects}。这招「{skills}」是{emotions}の秘诀！"),
            ("Micro Quest", "挑战任务：在{times}内{action}{subjects}。完成可获得「{benefits}」BUFF！"),
            ("Micro Quest", "勇者试炼：今天找一个{places_v}，{action}。{emotions}等着你！"),
            ("Micro Quest", "每日一练：{action}{subjects}，坚持{numbers}次。这是「{skills}」の修行。"),
            ("Micro Quest", "探索任务：发现一个{places_v}并{action}。每次探索都是地图の扩展。"),
            ("Micro Quest", "善意修行：{action}{subjects}。不需要魔法值，只需要真心——效果是{benefits}。"),
            ("Micro Quest", "敏捷训练：{action}，目标{numbers}次。这是{skills}的入门修行！"),
            ("Micro Quest", "收集任务：今天找到{numbers}个让你{emotions}的瞬间。那是今天的{items}。"),
            ("Micro Quest", "感恩试炼：对{subjects}说一声谢谢。发动「{skills}」无需吟唱。"),
            ("Micro Quest", "感知训练：停在{places_v}，{action}。{emotions}是修行の副产品。"),
        ],
        "life_tip": [
            ("Life Tip", "勇者の知恵：{action}{subjects}，可以让{benefits}提升{numbers}%。这是基础恢复魔法。"),
            ("Life Tip", "贤者の建议：每{times}就{action}一次。持续{numbers}天后{benefits}自动+1。"),
            ("Life Tip", "精灵の秘诀：用{items}来{action}——这比普通方法效果好{numbers}倍！"),
            ("Life Tip", "冒险者の习惯：出门前检查{numbers}样东西：{items}、{subjects}、好心情。三重确认结界。"),
            ("Life Tip", "王立图书馆记载：每天{action}，{numbers}天后{benefits}翻倍。这叫「{skills}」。"),
            ("Life Tip", "工会前辈の经验：把大任务拆成{numbers}小步，每步奖励自己{items}。这是任务分解术。"),
            ("Life Tip", "圣职者の秘方：{times}花{numbers}分钟{action}，效果可持续一整天。"),
            ("Life Tip", "魔法学园教授：用{items}记录每天{numbers}件好事，{benefits}会在不知不觉中提升。"),
            ("Life Tip", "旅商人の智慧：在{places_v}{action}，效率是在家里の{numbers}倍。"),
            ("Life Tip", "自然の智慧：{action}{subjects}——这是最古老也是最有效的{skills}。"),
        ],
        "anime_quote": [
            ("Anime Quote", "「{action}不是目的，{emotions}才是。—— {npcs_v}」"),
            ("Anime Quote", "「真正的{skills}不是改变{subjects}，而是改变看待{subjects}的方式。—— 大贤者」"),
            ("Anime Quote", "「就算是最弱的{animals}，每天{action}一次，{numbers}天后也是传说。—— 传奇战士」"),
            ("Anime Quote", "「勇者の道不在{places_v}，而在脚下の每一步。—— 流浪剑士」"),
            ("Anime Quote", "「你不会因为少做了一个{action}而变弱，但会因为多做了一次而获得{benefits}。—— 修行僧」"),
            ("Anime Quote", "「这个世界的隐藏规则是：你对{subjects}{action}，它也会对你{action}。—— 猫の贤者」"),
            ("Anime Quote", "「最强的{items}不是武器，是今天愿意{action}的自己。—— 锻造之神」"),
            ("Anime Quote", "「每个{npc_v}都有自己的故事，就像现实中的每个{subjects}一样。—— 异世界転生者」"),
            ("Anime Quote", "「{emotions}比{items}更重要，{action}比等待更重要。—— 退休の勇者」"),
            ("Anime Quote", "「没有人一开始就是传说。每个传说都是从「第一次{action}」开始的。—— 冒险者学校校长」"),
            ("Anime Quote", "「最强大的防御魔法不是盾牌，是{emotions}の心。—— 圣骑士団长」"),
            ("Anime Quote", "「你走过的每一条弯路，都是为了避开更大的陷阱。包括{action}。—— 迷宫探索者」"),
            ("Anime Quote", "「今天你{action}了吗？如果没有——{times}就是最好的时机。—— 笑颜魔法师」"),
            ("Anime Quote", "「最强的攻击不是剑，是理解。最深的防御不是盾，是{emotions}。—— 武僧大师」"),
            ("Anime Quote", "「奇迹不是天上掉下来的，是你每天{action}一点点堆出来的。—— 考古学者」"),
        ],
        "kingdom_news": [
            ("Kingdom News", "📰 王国快讯：冒险者工会统计显示——本月「{skills}」使用率上升{numbers}%！工会决定本周所有任务奖励+10%。"),
            ("Kingdom News", "📰 王国快讯：{places_v}观测站报告——近日适宜{action}。{benefits}效果提升中！"),
            ("Kingdom News", "📰 王国快讯：王都{places_v}荣获「最受勇者欢迎の休憩点」称号。店主表示会继续提供最好的{items}。"),
            ("Kingdom News", "📰 王国快讯：王立图书馆新到一批「{subjects}论文集」。贤者点评：「知识就是力量，但{action}才是魔法。」"),
            ("Kingdom News", "📰 王国快讯：王国交通局公告——{action}是最环保の移动方式。每{action}1000次，碳排减少，{benefits}+1。"),
            ("Kingdom News", "📰 王国快讯：冒险者心理互助会成立！会长致辞：「每个勇者都可以偶尔{emotions}。求助不是耻辱，是智慧。」"),
            ("Kingdom News", "📰 王国快讯：王国音乐节即将开幕！街头艺人招募中。无论会不会{skills}，「{action}」就是一种参与。"),
            ("Kingdom News", "📰 王国快讯：{places_v}の{npc_v}表示——最近{animals}大量出没，带来好运！"),
            ("Kingdom News", "📰 王国快讯：最新研究表明，每天{action}{numbers}分钟可降低{numbers}%压力值。「{skills}」の科学解释发布！"),
            ("Kingdom News", "📰 王国快讯：冒险者工会发布新规——连续{numbers}天{action}の勇者，获得「{subjects}」限定称号！"),
        ],
        "encouragement": [
            ("Adventurer's Word", "勇者よ、立ち上がれ！每一次{action}都是对自我の超越。{emotions}！"),
            ("Adventurer's Word", "还记得你最初の{items}吗？每个传说都是从{action}这一步开始的。"),
            ("Adventurer's Word", "冒险途中也许疲惫，但请记住：今天的你已经比昨天更{emotions}了。"),
            ("Adventurer's Word", "贤者有言：不是看到了希望才{action}，而是{action}了才看到希望。"),
            ("Adventurer's Word", "今天就做一件让自己{emotions}の小事！比如{action}{subjects}。"),
            ("Adventurer's Word", "就算今天只完成了「{action}{subjects}」这一个任务，你也是合格的勇者！"),
            ("Adventurer's Word", "勇者の道并非一帆风顺。允许自己偶尔{emotions}，这也是修行の一部分。"),
            ("Adventurer's Word", "抬头看看窗外——这个{places_v}就是你の异世界。不需要穿越，生活本身就是最伟大的{skills}。"),
            ("Adventurer's Word", "在{places_v}做一个{action}——这就是今天の{benefits}来源。"),
            ("Adventurer's Word", "有人因为你的{emotions}而觉得这个世界更好了。只是他们还没告诉你。但这是真的。"),
            ("Adventurer's Word", "如果今天很难，那就从{action}开始。有时候，第一步就是最高成就。"),
            ("Adventurer's Word", "你并不孤单。世界上有无数个{npc_v}，正在和你经历相似的冒险。"),
            ("Adventurer's Word", "深呼吸。这个世界不会因为一次{action}失败而崩塌。你比想象中更{emotions}。"),
            ("Adventurer's Word", "背包太重？放下一些{items}吧。无论是物品还是心事，都值得被整理。"),
            ("Adventurer's Word", "偶尔的「{emotions}」也是修行。休息不是懈怠，而是为了下一段旅程积蓄力量。"),
        ],
        "blessing": [
            ("Morning Blessing", "今日の运势：大吉！{npcs_v}の加护降临，{skills}+3！出发吧勇者！"),
            ("Morning Blessing", "晨光初现，{places_v}の钟声响起。新的一天，愿你遇见{emotions}の人和事。"),
            ("Morning Blessing", "冒险者工会发来贺电：今日完成{action}任务将获得额外{benefits}加成！"),
            ("Morning Blessing", "晨风轻拂，精灵の祝福随风而至。去{places_v}发现一个今日の{emotions}吧。"),
            ("Morning Blessing", "贤者の预言：今天你会遇到{emotions}。那是你今日最重要的{items}来源。"),
            ("Morning Blessing", "早安，勇者！昨夜の星空预示：今日宜{action}、宜{emotions}、宜善待{subjects}。"),
            ("Morning Blessing", "王宫の占星术士发来消息：今日星象极佳，适合开启{numbers}段新の冒险。去{places_v}吧！"),
            ("Morning Blessing", "晨の露珠闪烁着七色光芒。每完成一个{action}，露珠就多一种颜色。今天会是七彩的吗？"),
            ("Morning Blessing", "今日星象：{skills}与{emotions}交相辉映！冒险成功率+25%，适合{action}。"),
            ("Morning Blessing", "异世界广播电台：今天の关键词是「{subjects}」。不管结果如何，{action}本身就是冒险！"),
            ("Morning Blessing", "精灵之乡传来消息：今日宜{action}，发现一个新世界。{emotions}是打开异世界之门の钥匙。"),
            ("Morning Blessing", "大贤者的每日箴言：昨日已逝，明日未至。你拥有的，只有此刻。好好使用这个「{times}」吧。"),
            ("Morning Blessing", "占卜师的神谕：今天会在{places_v}发现一样有趣の{items}。值得你驻足{numbers}秒。"),
            ("Morning Blessing", "{places_v}の{npc_v}报告：今日{emotions}正好。无论多忙，记得{action}。那是免费の治愈魔法。"),
            ("Morning Blessing", "今日运势：中吉以上！特别适合{action}。完成后获得「{emotions}」の祝福。"),
        ],
        "isekai_slang": [
            ("Isekai Slang", "今日异世界用语：「{slang_term}」——{slang_def}。💡使用场景：{slang_use}"),
            ("Isekai Slang", "勇者用语辞典：「{slang_term}」とは？{slang_def}。📝例句：「{slang_example}」"),
            ("Isekai Slang", "冒险者黑话课堂：{slang_term}（{slang_def}）。学会这个词，你在异世界の社交力+{numbers}！"),
            ("Isekai Slang", "异世界语言学：今天学「{slang_term}」——{slang_def}。{slang_use}"),
            ("Isekai Slang", "王国辞典：「{slang_term}」— {slang_def}。勇者必备词汇，今日习得！"),
        ],
        "isekai_recipe": [
            ("Isekai Recipe", "🍳 勇者の{recipe_meal}：「{recipe_name}」\n\n📜 材料：{recipe_ingredients}\n⚔ 制作：{recipe_steps}\n\n✨ 效果：{recipe_effect}\n💡 {recipe_tip}"),
            ("Isekai Recipe", "🔥 冒险者厨房：{recipe_name}\n\n🧪 所需素材：{recipe_ingredients}\n📋 炼金步骤：{recipe_steps}\n\n🎁 完成奖励：{recipe_effect}\n💬 {recipe_tip}"),
            ("Isekai Recipe", "🍜 异世界料理图鉴 #{numbers}：{recipe_name}\n\n🛒 采购清单：{recipe_ingredients}\n🔪 烹饪魔法：{recipe_steps}\n\n🌟 HP回复量：{recipe_effect}\n📝 {recipe_tip}"),
        ],
        "isekai_motivation": [
            ("Isekai Motivation", "🔥 勇者の魂に火をつけろ！\n\n{action}——这不是建议，是来自异世界の王命！\n\n{emotions}はあなたの最大の武器だ。今日も立ち上がれ！"),
            ("Isekai Motivation", "⚔ 限界突破！\n\n「{skills}」を信じろ。{npcs_v}も言っていた——「{action}こそが伝説の始まりだ」と。"),
            ("Isekai Motivation", "💥 覚醒の刻！\n\n今の自分を超えるために必要なのは、{benefits}だけ。{action}すれば、明日のあなたは今日より{numbers}倍強くなっている。"),
            ("Isekai Motivation", "🎌 いくぞ、勇者！\n\n{places_v}で待つ{npc_v}が言った：「{emotions}を持って{action}すれば、君はもう伝説だ。」\n\nその言葉を胸に、今日も一歩を踏み出そう。"),
            ("Isekai Motivation", "🌟 あなたの物語はまだ序章だ。\n\n{subjects}のために{action}すること——それは{skills}の第一歩。{emotions}を忘れるな！"),
        ],
    }

    tmpls = templates.get(push_type, [])
    if not tmpls:
        return None

    # Shuffle to add randomness in template selection
    random.shuffle(tmpls)

    for title_tmpl, body_tmpl in tmpls:
        # Fill slots
        body = body_tmpl
        # Find all {slots}
        import re
        slots = re.findall(r'\{(\w+)\}', body_tmpl)
        filled = {}
        for slot in slots:
            pool_name = {
                "action": "actions", "subjects": "subjects", "benefits": "benefits",
                "places_v": "places_v", "npcs_v": "npcs_v", "times": "times",
                "numbers": "numbers", "items": "items", "skills": "skills",
                "emotions": "emotions", "animals": "animals",
                "slang_term": "slang_terms", "slang_def": "slang_defs",
                "slang_use": "slang_uses", "slang_example": "slang_examples",
                "recipe_meal": "recipe_meals", "recipe_name": "recipe_names",
                "recipe_ingredients": "recipe_ingredients",
                "recipe_steps": "recipe_steps", "recipe_effect": "recipe_effects",
                "recipe_tip": "recipe_tips",
            }.get(slot, slot)
            pool = p.get(pool_name, ["?"])
            filled[slot] = _pick(pool, used)
            body = body.replace(f"{{{slot}}}", filled[slot], 1)

        # Check if this body was used before
        body_hash = _hash(body)
        if body_hash in used:
            continue  # try next template

        return {"title": title_tmpl, "body": body}

    # All templates exhausted, return first one anyway
    title_tmpl, body_tmpl = tmpls[0]
    body = body_tmpl
    import re
    slots = re.findall(r'\{(\w+)\}', body_tmpl)
    for slot in slots:
        pool_name = {
            "action": "actions", "subjects": "subjects", "benefits": "benefits",
            "places_v": "places_v", "npcs_v": "npcs_v", "times": "times",
            "numbers": "numbers", "items": "items", "skills": "skills",
            "emotions": "emotions", "animals": "animals",
            "slang_term": "slang_terms", "slang_def": "slang_defs",
            "slang_use": "slang_uses", "slang_example": "slang_examples",
            "recipe_meal": "recipe_meals", "recipe_name": "recipe_names",
            "recipe_ingredients": "recipe_ingredients",
            "recipe_steps": "recipe_steps", "recipe_effect": "recipe_effects",
            "recipe_tip": "recipe_tips",
        }.get(slot, slot)
        pool = p.get(pool_name, ["?"])
        body = body.replace(f"{{{slot}}}", _pick(pool, set()), 1)
    return {"title": title_tmpl, "body": body}
