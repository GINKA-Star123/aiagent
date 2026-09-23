# 角色参考图库（本地私有资产，不入仓）

本目录是视觉角色检索（CLIP + FAISS）的**参考图库**，
被 `.gitignore` 整体忽略，只有本文件通过 `!data/characters/README.md` 反选入仓。

## 为什么不入仓

- 体积大：当前约 132 个文件 / 414MB。
- 版权：参考图多为第三方作品，不适合随代码分发。

## 目录约定

```
data/characters/
├── luotianyi/          # 目录名 = 角色 ID（character_id），与 profiles 中的 id 一致
├── yanhe/
├── yuezhengling/
└── <character_id>/
```

- 一个角色一个子目录，**目录名必须是 `character_id`**（小写字母数字），
  `CharacterRegistry` 依据它建立角色与图片的关联。
- 每个目录至少放 5 张能体现该角色视觉特征的图片（发色、瞳色、服饰、配饰）。
- 图片格式：`.jpg` / `.jpeg` / `.png` / `.webp`。
- 建议单张控制在 2MB 以内：检索时会缩放到 CLIP 输入尺寸，过大只会拖慢索引构建。

## 新增角色后如何生效

```powershell
# 重建角色图库索引（写入 data/cache/vision/character_index）
POST /vision/characters/rebuild  {"force_rebuild": true}

# 查看索引统计
GET /vision/characters/stats
```

重建后 `reference_image_count` / `character_count` 应随之增加。
索引缓存（`data/cache/`）与图库本身都不入仓，换机器需要重新放置图片并重建。

## 低置信度策略

角色命中需要**模型确认**才算身份确认（`character_candidates[].source != "retrieval_only"`）。
只靠图库相似度命中的候选会被标为 `retrieval_only`，进入 `channels.character.status = partial`，
回复侧使用保守表达，且**不会被写入长期记忆**。因此图库质量直接影响"能不能确认"，
但不会因为图库里有相似图就误判身份。
