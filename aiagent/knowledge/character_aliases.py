"""VSinger 角色标识与检索元数据的唯一事实源（纯数据模块）。

设计约束：

- 本文件只放常量数据，不放任何函数（函数分别住在 query_normalizer 与
  document_loader 里），保证"别名只有一个来源"；
- 每条角色记录的标识包含：规范名 + 中文别名 + 英文标识 + 全拼小写，
  这样索引侧与查询侧都能命中同一组 token。
"""

from __future__ import annotations

# 角色规范名 -> 全部可检索标识（含规范名本身）
CHARACTER_ALIASES: dict[str, tuple[str, ...]] = {
    "乐正绫": (
        "乐正绫",
        "阿绫",
        "阿綾",
        "绫绫",
        "YueZhengling",
        "yuezhengling",
    ),
    "洛天依": (
        "洛天依",
        "天依",
        "天依酱",
        "LuoTianyi",
        "luotianyi",
    ),
    "乐正龙牙": (
        "乐正龙牙",
        "龙牙",
        "龍牙",
        "YueZhenglongya",
        "yuezhenglongya",
    ),
    "言和": (
        "言和",
        "言和和",
        "YanHe",
        "yanhe",
    ),
    "墨清弦": (
        "墨清弦",
        "墨姐",
        "清弦",
        "MoQingxian",
        "moqingxian",
    ),
    "徵羽摩柯": (
        "徵羽摩柯",
        "征羽摩柯",
        "摩柯",
        "ZhiYumoke",
        "zhiyumoke",
    ),
    "苍穹": (
        "苍穹",
        "蒼穹",
        "cangqiong",
    ),
    "赤羽": (
        "赤羽",
        "chiyu",
    ),
    "海伊": (
        "海伊",
        "haiyi",
    ),
    "诗岸": (
        "诗岸",
        "shian",
    ),
    "星尘": (
        "星尘",
        "星塵",
        "xingchen",
    ),
    "心华": (
        "心华",
        "muxin",
    ),
    "永夜Minus": (
        "永夜Minus",
        "永夜",
        "yongyeminus",
    ),
    "ZERO": (
        "ZERO",
        "零",
        "zero",
    ),
    "知语墨可": (
        "知语墨可",
        "ZhiYumoke",
        "zhiyumoke",
    ),
}

# 文件名/英文标识（小写）-> 角色规范名
CHARACTER_FILE_KEYS: dict[str, str] = {
    "yuezhengling": "乐正绫",
    "luotianyi": "洛天依",
    "yuezhenglongya": "乐正龙牙",
    "yanhe": "言和",
    "moqingxian": "墨清弦",
    "zhiyumoke": "知语墨可",
    "cangqiong": "苍穹",
    "chiyu": "赤羽",
    "haiyi": "海伊",
    "shian": "诗岸",
    "xingchen": "星尘",
    "muxin": "心华",
    "yongyeminus": "永夜Minus",
    "zero": "ZERO",
}

# 主题关键词（用于 metadata.topic 与评测分类对齐）
TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "song": ("歌曲", "代表曲", "专辑", "歌词", "生贺曲", "收录曲"),
    "setting": ("设定", "人设", "资料", "基本资料", "代表色", "声源", "生日"),
    "fan_chant": ("应援词", "应援口号", "口号", "slogan", "华风夏韵", "洛水天依"),
    "workflow": ("直播", "开场", "producer", "制作人", "运营"),
    "relation": ("关系", "CP", "南北组", "洛南绫北"),
}

SOURCE_TRUST_LEVELS: dict[str, str] = {
    "official": "high",
    "public": "medium",
    "user": "low",
    "unknown": "low",
}

# 文档性质 -> (chunk_size, chunk_overlap)
# profile：角色档案，信息密度高 → 小块更容易精确定位；
# long_form：超长文档（如 41KB 的角色长文）→ 大块保持段落完整；
# reference：流程/资料型 → 维持默认。
CHUNK_POLICY: dict[str, tuple[int, int]] = {
    "profile": (420, 80),
    "long_form": (720, 120),
    "reference": (520, 80),
}

LONG_FORM_MIN_CHARS = 20000