from __future__ import annotations

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


def normalize_aliases(query: str) -> str:
    normalized = query
    for alias, canonical in ALIASES.items():
        if alias in normalized and canonical not in normalized:
            normalized = normalized.replace(alias, f"{alias} {canonical}")
    return normalized


def expand_domain_terms(query: str) -> str:
    expansions: list[str] = []
    for triggers, terms in DOMAIN_EXPANSION_RULES:
        if any(trigger in query for trigger in triggers):
            for term in terms:
                if term not in expansions:
                    expansions.append(term)

    if not expansions:
        return query

    merged = query
    for term in expansions:
        if term not in merged:
            merged += f" {term}"
    return merged


def normalize_rag_query(query: str) -> str:
    query = (query or "").strip()
    if not query:
        return ""
    query = normalize_aliases(query)
    query = expand_domain_terms(query)
    return query.strip()
