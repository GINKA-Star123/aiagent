from __future__ import annotations

from aiagent.knowledge.character_aliases import CHARACTER_ALIASES

ALIASES = {
    "天依": "洛天依",
    "阿绫": "乐正绫",
    "阿綾": "乐正绫",
    "龙牙": "乐正龙牙",
    "龍牙": "乐正龙牙",
    "摩柯": "徵羽摩柯",
    "墨姐": "墨清弦",
    "清弦": "墨清弦",
    "言和和": "言和",
}

DOMAIN_EXPANSION_RULES = [
    (
        ["应援词", "应援口号", "口号", "slogan"],
        ["口号", "应援词", "应援口号", "华风夏韵", "洛水天依"],
    ),
    (
        ["歌曲", "有什么歌", "有哪些歌", "代表曲", "曲子"],
        ["相关歌曲", "代表曲", "官方专辑", "歌词"],
    ),
    (
        ["专辑", "EP", "唱片"],
        ["官方专辑", "发行", "收录曲"],
    ),
    (
        ["生日", "诞生日", "生贺"],
        ["生日", "诞生祭", "生贺曲"],
    ),
    (
        ["设定", "人设", "资料", "介绍"],
        ["设定", "角色资料", "代表色", "声源", "生日"],
    ),
    (
        ["代表色", "应援色", "颜色"],
        ["基本资料", "设定", "阿绫红"],
    ),
    (
        ["关系", "相关cp", "cp", "朋友"],
        ["相关CP", "南北组", "洛南绫北"],
    ),
]


def _mask_expansion_terms(text: str) -> str:
    """把"领域扩展词"从文本里遮蔽掉，仅用于**角色命中判定**。

    为什么需要（roadmap 6.2 要求 normalize_rag_query 可重复调用）：

    - 应援词规则会追加 "洛水天依"，它内部包含角色别名 "天依"；
    - 若不遮蔽，第二次调用会把 "洛水天依" 里的 "天依" 当成一次**新的**角色命中，
      继续追加 洛天依 / LuoTianyi，结果在多次调用之间不断增长。

    遮蔽只影响"谁被命中"的判断，不影响最终写进 query 的词，
    也不影响领域词本身的扩展行为（那是 expand_domain_terms 的职责）。
    """

    masked = text

    for _, terms in DOMAIN_EXPANSION_RULES:
        for term in terms:
            if term:
                masked = masked.replace(term, " ")

    return masked


def normalize_aliases(query: str) -> str:
    """别名/标识扩展（查询侧）。

    幂等约定：命中判定统一读遮蔽后的 ``probe``，写入统一写 ``normalized``。
    只要遵守这条，第二次调用就不会因为"我们自己追加的词"再次触发扩展。
    """

    normalized = query
    probe = _mask_expansion_terms(query)

    # 1) 兼容旧表：别名 -> 规范名（保持历史行为与词序）
    for alias, canonical in ALIASES.items():
        if alias in probe and canonical not in normalized:
            normalized = normalized.replace(alias, f"{alias} {canonical}")

    # 2) 完整别名表：命中任一角色标识时，补齐该角色的全部标识（含英文名/全拼）。
    #    英文标识配合 retriever 侧的"标识头"才能命中英文文档名。
    for canonical, variants in CHARACTER_ALIASES.items():
        if not any(variant and variant in probe for variant in (canonical, *variants)):
            continue

        for variant in (canonical, *variants):
            if variant and variant not in normalized:
                normalized = f"{normalized} {variant}"

    return normalized


def expand_domain_terms(query: str) -> str:
    """领域词扩展：迭代到**不动点**，而不是只跑一趟。

    为什么必须迭代：规则之间存在 term/trigger 交叉——
    例如 "设定" 规则的 term 含 "代表色"，而 "代表色" 又是另一条规则的 trigger。
    只跑一趟时，第二次调用会继续追加（基本资料 / 阿绫红），造成非幂等。

    轮数上限用规则条数 + 1 兜底，规则表变化时也不会死循环。
    """

    merged = query

    for _ in range(len(DOMAIN_EXPANSION_RULES) + 1):
        added = False

        for triggers, terms in DOMAIN_EXPANSION_RULES:
            if not any(trigger in merged for trigger in triggers):
                continue

            for term in terms:
                if term and term not in merged:
                    merged += f" {term}"
                    added = True

        if not added:
            break

    return merged


def normalize_rag_query(query: str) -> str:
    query = (query or "").strip()
    if not query:
        return ""
    query = normalize_aliases(query)
    query = expand_domain_terms(query)
    return query.strip()