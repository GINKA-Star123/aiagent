# 仓库治理与目录约定

本文档定义"什么进版本库、什么只是本机运行资产、什么永远不进仓"。
`.gitignore` 是规则的实现，本文档是规则的**解释**；两者不一致时以本文档为准并修正 `.gitignore`。

## 一、目录分类

| 分类 | 路径 | 是否入仓 | 说明 |
| --- | --- | --- | --- |
| 后端源码 | `aiagent/`、`cloud/`、`config/`、`integrations/` | 是 | 运行时全部代码 |
| 应用层 | `apps/core/`、`apps/api/`、`apps/worker/` | 是 | bootstrap、路由、任务 worker |
| 运维脚本 | `scripts/` | 是 | 含 `scripts/v1_preflight.py`，被 `tests/unit/test_v1_preflight.py` 直接导入；`scripts/scratch/` 例外（个人草稿，不入仓） |
| 部署 | `deploy/` | 是 | Dockerfile、compose、nginx |
| 测试 | `tests/` | 是 | `tests/fixtures/` 下的评测集必须入仓 |
| 示例配置 | `.env.example`、`cloud.tencent.example.env` | 是 | 模板，不得写入真实密钥 |
| 本地配置 | `.env`、`cloud.tencent.env` | 否 | 含密钥；由模板复制生成 |
| 知识库文档 | `data/knowledge/` | **否** | 仓库策略：知识文档不入仓，按本地内容资产管理（16 个文件 / 约 0.1MB） |
| 角色参考图库 | `data/characters/` | 否 | 132 个文件 / 约 414MB，体量大且涉及第三方版权 |
| 模型权重 | `data/models/` | 否 | CLIP / bge / faster-whisper，体积 GB 级 |
| Live2D 资产 | `data/live2d/` | 否 | profile 与模型资源（源码在 `aiagent/live2d/`，必须入仓） |
| 运行时缓存 | `data/cache/`、`data/logs/` | 否 | TTS 音频、realtime 录音、RAG 索引与评测报告 |
| 运行时状态 | `data/runtime/`、`data/memory/` | 否 | 记忆偏好、写入审计（`memory_write_audit.jsonl`）、向量库数据 |
| 用户数据 | `data/uploads/` | 否 | 用户上传图片，属隐私数据 |
| 本地对象存储 | `data/cloud_storage/` | 否 | `STORAGE_PROVIDER=local` 时的落盘根 |
| 临时工作区 | `_tmp/` | 否 | 排查与验证产物，可随时删除 |
| 客户端（Flutter） | `apps/flutter_client/` | **否** | 整个目录不入仓，以独立仓库维护 |
| 调试端（Qt） | `apps/desktop_qt/` | **否** | 整个目录不入仓，仅作本地调试工具 |

> **被忽略但仍是运行资产**：`data/cache/`、`data/logs/`、`data/runtime/`、`data/uploads/`、`data/cloud_storage/`、`data/live2d/`。
> 全新环境 clone 后这些目录不存在是**正常**的，程序首次运行会自动创建。
>
> **知识库文档被有意排除**：`data/knowledge/` 不入仓，因此 clone 后知识目录为空。
> 此时 `tests/rag/test_rag_quality_baseline.py` 会通过 `skipif` 自动跳过（而不是失败），
> 文本聊天、Memory、Vision 链路不受影响；需要跑检索评测时，把知识文档放回 `data/knowledge/public/` 即可。

## 二、`.gitignore` 的两条硬规则

### 1. 无前缀斜杠的通配符会命中任意层级

```gitignore
live2d/          # ✗ 错误：会同时命中 aiagent/live2d/ 与 integrations/live2d/ 两个源码包
data/live2d/     # ✓ 正确：只命中 data 下的资产目录
```

已跟踪文件不受新增规则影响，但**新加的文件会被静默忽略**（`git status` 里不出现，很容易漏提交）。
本仓库因此提供实测手段：

```powershell
# 必须加 --no-index，否则已跟踪文件永远返回"未忽略"
git check-ignore --no-index -v aiagent/live2d/models.py
```

`scripts/check_repo_hygiene.py` 会对 `aiagent/`、`apps/core`、`cloud/`、`config/`、`integrations/`、`scripts/`、`tests/` 逐文件执行该检查。

### 2. 不能反选"父目录已被排除"的文件

```gitignore
data/                 # ✗ 一旦这样写，!data/knowledge/xxx 全部失效
data/knowledge/       # ✓ 逐目录排除，才有反选空间
!data/characters/README.md
```

### 3. 含中文的 PowerShell 脚本必须带 UTF-8 BOM

Windows PowerShell 5.1 对**没有 BOM** 的 `.ps1` 按系统 ANSI 代码页读取，
中文被曲解后会吞掉引号，报出"字符串缺少终止符"这类与真实原因无关的语法错误
（`scripts/clean_workspace.ps1` 就踩过一次）。

```powershell
# 检查：前三个字节应为 ef bb bf
[System.IO.File]::ReadAllBytes('scripts\clean_workspace.ps1')[0..2] | ForEach-Object { $_.ToString('x2') }

# 修复：以 UTF-8 BOM 重新保存（VS Code 右下角编码 → Save with Encoding → UTF-8 with BOM）
```

`scripts/check_repo_hygiene.py` 会自动检查 `scripts/` 与 `deploy/` 下的 `.ps1`。
纯 ASCII 的脚本不受影响，可以不带 BOM。

## 三、历史状态处置结论

| 历史项 | 结论 |
| --- | --- |
| `stage.md` | 磁盘已不存在，`git ls-files stage.md` 为空且工作区无 `D` 状态 → **删除已提交完成，无需额外处理** |
| `pyproject.toml` 的 `domain*` | 该目录不存在，已从 `include` 移除 |
| `pyproject.toml` 缺 `cloud*` | 已补上 |
| `scripts/` 被忽略 | 已解除；`tests/unit/test_v1_preflight.py` 依赖 `scripts/v1_preflight.py`，脚本必须入仓 |
| `aiagent/knowledge/character_aliases.py` 被忽略 | 已解除；该文件是 RAG 源码，被忽略会导致 clone 后 `document_loader` 导入失败 |
| `live2d/` 通配符 | 已收窄为 `data/live2d/`，避免误伤两个源码包 |
| `data/characters/` 未忽略 | 已忽略（414MB 本地资产） |
| `.pytest_cache` 权限 | 只读挂载下可能删不掉；用 `scripts/clean_workspace.ps1` 先 `attrib -r` 再删 |
| `clean_workspace.ps1` 解析失败 | 根因是无 BOM + 中文；已改为 UTF-8 BOM 保存，并加入自动化检查 |

## 四、lint 与格式化约定

- 工具：**ruff**（lint + format 合一），行宽 120，目标 `py311`，配置见 `pyproject.toml`。
- 提交前：

  ```powershell
  .venv\Scripts\python.exe -m ruff check aiagent cloud config apps
  .venv\Scripts\python.exe -m ruff format --check aiagent cloud config apps
  ```

- 暂不强制 `mypy`：Graph state 大量使用动态字典，第三方 SDK 类型缺失，类型检查收益低于噪音。
- 标签约定：`pytest` 分层标记（`unit` / `api` / `smoke` / `rag` / `integration`）已在 `pyproject.toml` 登记，可直接 `-m unit` 筛选。

## 五、检查入口

```powershell
# 仓库卫生：源码是否被误忽略、必需文件缺失、该忽略的没忽略、大文件、疑似密钥
.venv\Scripts\python.exe scripts\check_repo_hygiene.py

# 配置三方一致性：settings.py / cloud/config.py ↔ .env.example ↔ docs/config-reference.md
.venv\Scripts\python.exe scripts\check_config_sync.py

# 清理本机运行产物（不动入仓文件）
powershell -File scripts\clean_workspace.ps1
```
