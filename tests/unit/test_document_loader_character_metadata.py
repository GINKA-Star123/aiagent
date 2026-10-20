from __future__ import annotations

from pathlib import Path

import pytest

from aiagent.knowledge.document_loader import DocumentLoader

KNOWLEDGE_DIR = Path("data/knowledge/public")

CASES = [
    # filename, expected_character, expected_alias, expected_search_alias
    ("乐正绫.md", "乐正绫", "阿绫", "YueZhengling"),
    ("洛天依.md", "洛天依", "天依", "LuoTianyi"),
    ("言和.md", "言和", "言和和", "YanHe"),
    ("乐正龙牙.md", "乐正龙牙", "龙牙", "YueZhenglongya"),
    ("墨清弦.md", "墨清弦", "墨姐", "MoQingxian"),
    ("徵羽摩柯.md", "徵羽摩柯", "摩柯", "ZhiYumoke"),
    ("苍穹.md", "苍穹", "蒼穹", "cangqiong"),
    ("赤羽.md", "赤羽", "", "chiyu"),
    ("海伊.md", "海伊", "", "haiyi"),
    ("诗岸.md", "诗岸", "", "shian"),
    ("星尘.md", "星尘", "星塵", "xingchen"),
    ("心华.md", "心华", "", "muxin"),
    ("永夜Minus.md", "永夜Minus", "永夜", "yongyeminus"),
    ("乐正零.md", "乐正零", "", "乐正零"),
    ("东方栀子.md", "东方栀子", "", "东方栀子"),
    ("三色零歌.md", "三色零歌", "", "三色零歌"),
    ("诗明空.md", "诗明空", "", "诗明空"),
    ("天崎默.md", "天崎默", "", "天崎默"),
    ("初音未来.md", "初音未来", "", "初音未来"),
    ("镜音铃·连.md", "镜音铃·连", "", "镜音铃·连"),
]


@pytest.mark.skipif(
    not KNOWLEDGE_DIR.exists(),
    reason="knowledge directory is missing",
)
@pytest.mark.parametrize(
    "filename,character,alias,search_alias",
    CASES,
)
def test_document_character_metadata(
    filename: str,
    character: str,
    alias: str,
    search_alias: str,
) -> None:
    docs = DocumentLoader().load_file(
        KNOWLEDGE_DIR / filename,
        root_dir=KNOWLEDGE_DIR,
    )
    metadata = docs[0].metadata

    assert metadata["character"] == character, (
        filename,
        metadata["character"],
        character,
    )

    if alias:
        assert alias in metadata["aliases"], (
            filename,
            metadata["aliases"],
            alias,
        )

    if search_alias:
        assert search_alias in metadata["search_aliases"], (
            filename,
            metadata["search_aliases"],
            search_alias,
        )


def test_text_fallback_prefers_earliest_character() -> None:
    loader = DocumentLoader()

    assert loader._match_character_by_text(
        "洛天依是Vsinger成员……相关人士：乐正绫、言和"
    ) == "洛天依"

    assert loader._match_character_by_text(
        "乐正绫是Vsinger成员……相关人士：洛天依、言和"
    ) == "乐正绫"


def test_character_from_title_handles_section_suffix() -> None:
    loader = DocumentLoader()

    assert loader._character_from_title("洛天依") == "洛天依"
    assert loader._character_from_title("洛天依 / 基本资料") == "洛天依"
    assert loader._character_from_title("赤羽") == "赤羽"