from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(".")
INVENTORY_OUT = Path("docs/project-file-inventory.md")
OVERVIEW_OUT = Path("docs/project-overview-next-stage.md")

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    ".next",
    "dist",
    "build",
}

BINARY_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".wav",
    ".mp3",
    ".zip",
    ".faiss",
    ".pkl",
    ".bin",
    ".safetensors",
    ".pt",
    ".onnx",
    ".moc3",
}

LARGE_TEXT_LIMIT = 900_000

MODULE_HINTS = [
    ("aiagent/brain", "智能体核心与对话控制"),
    ("aiagent/cognition", "认知分析与回复规划"),
    ("aiagent/common", "公共工具"),
    ("aiagent/expression", "输出表达、TTS、音频与 Live2D 调度"),
    ("aiagent/graphs", "图流程与工作流状态"),
    ("aiagent/knowledge", "RAG 知识库管线"),
    ("aiagent/live2d", "Live2D 领域模型与 Payload"),
    ("aiagent/memory", "长期记忆适配"),
    ("aiagent/orchestrator", "事件编排、调度与会话管理"),
    ("aiagent/perception", "输入感知与语音回合管理"),
    ("aiagent/persona", "人格加载、提示词与人格保护"),
    ("aiagent/schemas", "输入、输出、事件 Schema"),
    ("aiagent/services", "LLM、视觉、状态、规划、记忆策略服务"),
    ("aiagent/state", "运行时状态模型"),
    ("aiagent/vision", "识图、图片存储与角色图库检索"),
    ("apps/api", "FastAPI 应用与路由"),
    ("apps/core", "运行时装配与核心门面"),
    ("apps/desktop_qt", "Qt 桌面调试前端"),
    ("apps/web", "Next.js Web 前端骨架"),
    ("config", "配置、默认值与环境变量"),
    ("domain", "早期轻量领域模型"),
    ("integrations", "第三方服务与外部库适配"),
    ("scripts", "本地脚本与验收工具"),
    ("tests", "测试套件"),
    ("docs", "项目设计与说明文档"),
    ("data/persona", "人格配置与参考音频"),
    ("data/live2d", "Live2D 角色、背景配置与资源"),
    ("data/vision", "视觉角色图库资源"),
    ("data/datasets", "训练与微调数据集"),
    ("data/cache", "运行时生成缓存"),
    ("data/uploads", "用户上传文件"),
]

PURPOSE_PATTERNS = [
    (r"class .*Runtime|build_runtime|CoreRuntime", "运行时装配或生命周期模块"),
    (r"APIRouter|FastAPI|@router", "HTTP API 路由或 FastAPI 应用模块"),
    (r"QWidget|QMainWindow|PySide6|QOpenGLWidget", "Qt 桌面 UI 或控件模块"),
    (r"BaseSettings|Field\(", "应用配置定义模块"),
    (r"BaseModel|dataclass", "数据模型或 Schema 模块"),
    (r"StateGraph|Graph|Runner|invoke", "工作流图或图执行器模块"),
    (r"OpenAI|httpx|Client|requests|post\(", "外部服务客户端或 API 调用适配模块"),
    (r"yaml.safe_load|profile.yaml|persona", "人格或 YAML 配置加载模块"),
    (r"Live2D|live2d|model3|motion3|exp3", "Live2D 相关模块"),
    (r"Vision|image|character|CLIP|faiss", "视觉、图片或角色识别模块"),
    (r"RAG|retriev|BM25|vector|embedding", "RAG、Embedding 或检索模块"),
    (r"Memory|mem0|memory", "记忆系统模块"),
    (r"TTS|audio|wav|playback|voice", "音频、TTS 或语音模块"),
    (r"ASR|whisper|microphone|vad", "ASR、麦克风或 VAD 模块"),
]


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if set(path.parts) & EXCLUDE_DIRS:
            continue
        if path == Path("scripts/generate_project_docs_zh.py"):
            # 文档生成器本身也会被列入下一轮盘点；当前轮保留它。
            pass
        files.append(path)
    return sorted(files, key=lambda item: item.as_posix().lower())


def path_posix(path: Path) -> str:
    return path.as_posix()


def layer_for(path: Path) -> str:
    value = path_posix(path)
    for prefix, name in MODULE_HINTS:
        if value.startswith(prefix):
            return name
    if path.name.startswith("."):
        return "根目录隐藏配置"
    return "根目录文件与其他资源"


def is_binary(path: Path) -> bool:
    if path.suffix.lower() in BINARY_EXTS:
        return True
    try:
        data = path.read_bytes()[:2048]
    except Exception:
        return True
    return b"\0" in data


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="gbk")
        except Exception:
            return None
    except Exception:
        return None


def py_summary(text: str) -> dict:
    try:
        tree = ast.parse(text)
    except Exception as exc:
        return {"parse_error": str(exc), "classes": [], "functions": [], "imports": []}

    classes: list[dict] = []
    functions: list[str] = []
    imports: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = [
                item.name
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            classes.append({"name": node.name, "methods": methods[:30]})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")

    return {
        "classes": classes,
        "functions": functions,
        "imports": sorted(set(imports))[:50],
    }


def purpose_for(path: Path, text: str, pyinfo: dict | None, binary: bool) -> str:
    value = path_posix(path)
    ext = path.suffix.lower()
    name = path.name

    if binary:
        if ext in {".wav", ".mp3"}:
            return "音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。"
        if ext in {".png", ".jpg", ".jpeg", ".webp"}:
            return "图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。"
        if ext == ".zip":
            return "压缩归档，通常用于数据集打包或外部资源备份。"
        return "二进制、模型、索引或缓存文件，不是源码，主要由运行时或工具读取。"

    if ext == ".py" and pyinfo is not None:
        matched = [desc for pattern, desc in PURPOSE_PATTERNS if re.search(pattern, text, re.I)]
        base = matched[0] if matched else "Python 模块，提供项目业务逻辑或集成胶水代码。"
        details: list[str] = []
        if pyinfo.get("classes"):
            details.append("类：" + "、".join(item["name"] for item in pyinfo["classes"][:10]))
        if pyinfo.get("functions"):
            details.append("函数：" + "、".join(pyinfo["functions"][:12]))
        return base + ("；" + "；".join(details) if details else "")

    if ext == ".ps1":
        return "PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。"
    if ext == ".md":
        title = ""
        for line in text.splitlines():
            if line.strip().startswith("#"):
                title = line.strip("# ").strip()
                break
        return "Markdown 文档。" + (title or "记录项目说明、设计或阶段计划。")
    if ext in {".yaml", ".yml"}:
        return "YAML 配置文件，用于 persona、Live2D、数据集、背景或服务配置。"
    if ext == ".json":
        if value.startswith("data/cache"):
            return "运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。"
        if value.startswith("data/datasets"):
            return "数据集元信息或微调训练数据。"
        return "JSON 配置、结构化数据或生成结果。"
    if ext in {".tsx", ".ts", ".css"}:
        return "Next.js Web 前端源码、配置或样式文件。"
    if ext in {".toml", ".lock", ".txt"} or name == "requirements.txt":
        return "依赖、锁文件、构建或打包配置。"
    if name.startswith(".env"):
        return "环境变量配置文件，包含模型供应商、API Key、端口、路径等运行参数。"

    return "文本资源或其他配置文件。"


def risk_tags(path: Path, text: str) -> list[str]:
    value = path_posix(path).lower()
    tags: list[str] = []
    if "mock_live2d" in value or "MockLive2D" in text:
        tags.append("注意区分 mock Live2D 与真实 Live2D 路径")
    if "live2d" in value and ("payload" in value or "dispatcher" in value):
        tags.append("属于 Live2D 调度链路，避免重复新增 dispatcher")
    if "vision" in value and ("character" in value or "retriever" in text):
        tags.append("属于视觉角色识别链路，避免重复新增检索器")
    if "memory" in value or "mem0" in text:
        tags.append("属于记忆链路，可能依赖外部向量数据库")
    if "rag" in value or "retriever" in value or "vector_store" in value:
        tags.append("属于 RAG 链路，避免重复新增索引入口")
    if "persona_guard" in value:
        tags.append("人格保护核心逻辑，修改后需要回归测试")
    return tags


def detail_for(path: Path) -> dict:
    size = path.stat().st_size
    binary = is_binary(path)
    text = None if binary or size > LARGE_TEXT_LIMIT else read_text(path)
    pyinfo = py_summary(text) if text is not None and path.suffix.lower() == ".py" else None
    return {
        "path": path_posix(path),
        "layer": layer_for(path),
        "size": size,
        "binary": binary,
        "purpose": purpose_for(path, text or "", pyinfo, binary),
        "pyinfo": pyinfo,
        "risks": risk_tags(path, text or ""),
    }


def generate_inventory() -> None:
    files = iter_files()
    items = [detail_for(path) for path in files]

    by_layer: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        by_layer[item["layer"]].append(item)

    lines: list[str] = []
    lines.append("# 项目全量文件盘点")
    lines.append("")
    lines.append(
        "说明：本文档基于当前工作区自动生成。源码、配置、脚本、Markdown、JSON、YAML 会按文本读取并摘要；"
        "图片、音频、压缩包、索引、模型和运行缓存只按路径、扩展名和用途说明，不展开二进制内容。"
    )
    lines.append("")
    lines.append(f"- 已盘点文件总数：{len(items)}")
    lines.append(f"- 二进制、资源或生成物：{sum(1 for item in items if item['binary'])}")
    lines.append(f"- 文本、源码或配置：{sum(1 for item in items if not item['binary'])}")
    lines.append("")
    lines.append("## 高风险重复功能地图")
    lines.append("")
    lines.append(
        "- Live2D 目前分三层：`aiagent/live2d` 负责领域模型和 payload，"
        "`aiagent/expression/live2d_payload_dispatcher.py` 负责输出调度，"
        "`integrations/live2d/*` 负责文件、Python runtime、Qt 控件等集成。后续应扩展这些文件，不要再新增平行 dispatcher。"
    )
    lines.append(
        "- 视觉识图链路已经存在：`aiagent/vision/*`、`aiagent/services/vision_service.py`、"
        "`aiagent/graphs/vision_graph.py`、`apps/api/routes/vision.py` 和 `/chat/multimodal`。"
        "新增识图能力应挂在 VisionService 或 VisionGraph。"
    )
    lines.append(
        "- RAG 链路已经存在：`aiagent/knowledge/*`、`aiagent/graphs/rag_graph.py`、"
        "`apps/api/routes/knowledge.py`。不要新增第二套索引或检索实现。"
    )
    lines.append(
        "- 记忆链路已经存在：`aiagent/memory/mem0_memory.py`、`aiagent/graphs/memory_graph.py`、"
        "`apps/api/routes/memory.py`。新增记忆策略应优先改 MemoryRunner 或 MemoryPolicyLLMService。"
    )
    lines.append(
        "- Qt 主调试界面是 `apps/desktop_qt/chat_window.py`。后续 UI 应以 panel/widget 接入，"
        "除调试窗口外，不要新增互相割裂的主窗口。"
    )
    lines.append("")

    for layer in sorted(by_layer):
        lines.append(f"## {layer}")
        lines.append("")
        for item in sorted(by_layer[layer], key=lambda value: value["path"].lower()):
            lines.append(f"### `{item['path']}`")
            lines.append(f"- 大小：{item['size']} bytes")
            lines.append(f"- 类型：{'二进制/资源/生成物' if item['binary'] else '文本/源码/配置'}")
            lines.append(f"- 作用：{item['purpose']}")

            pyinfo = item.get("pyinfo")
            if pyinfo:
                if pyinfo.get("imports"):
                    lines.append("- 主要依赖：" + "、".join(pyinfo["imports"][:25]))
                if pyinfo.get("classes"):
                    for cls in pyinfo["classes"][:10]:
                        methods = "、".join(cls["methods"][:15]) or "无显式方法"
                        lines.append(f"- 类 `{cls['name']}`：方法 {methods}")
                if pyinfo.get("functions"):
                    lines.append("- 顶层函数：" + "、".join(pyinfo["functions"][:20]))
                if pyinfo.get("parse_error"):
                    lines.append("- 解析警告：" + pyinfo["parse_error"])

            if item["risks"]:
                lines.append("- 注意：" + "；".join(item["risks"]))
            lines.append("")

    INVENTORY_OUT.write_text("\n".join(lines), encoding="utf-8")


def generate_overview() -> None:
    content = """# 项目总览与下一阶段计划

## 当前架构总览

项目当前已经形成一个多模态 AI Agent Runtime，主要分为以下层级。

### 1. 运行时与 API 层

- `apps/core/bootstrap.py`：完整运行时装配入口，负责把 LLM、RAG、记忆、视觉、TTS、ASR、Live2D、输出广播等组件组装起来。
- `apps/core/runtime.py`：API 层调用的核心门面，提供 chat、voice、vision、memory、knowledge、multimodal 等入口。
- `apps/api/http_server.py`：FastAPI 应用注册入口。
- `apps/api/routes/*`：HTTP 边界层。这里应保持轻量，只做请求解析、错误包装和调用 runtime 或集成服务。

### 2. 主 Agent 图流程

- `aiagent/graphs/main_graph.py`：主流程图，负责串联上下文准备、视觉图、记忆检索、状态分析、规划、RAG、LLM、记忆写入和最终 `ResponsePacket` 构建。
- `aiagent/graphs/state_graph.py`、`planner_graph.py`、`rag_graph.py`、`llm_graph.py`、`memory_graph.py`、`vision_graph.py`：各自负责独立子流程。
- `aiagent/graphs/graph_model.py`：图流程共享状态和结果模型。

### 3. Persona 人格系统

- `aiagent/persona/persona_loader.py`：读取 persona YAML。
- `aiagent/persona/persona_manager.py`：管理当前人格。
- `aiagent/persona/persona_runtime.py`：构建运行时人格上下文。
- `aiagent/persona/persona_prompts.py`：人格提示词生成。
- `aiagent/persona/persona_guard.py`：回复归一化和人格防漂移。
- `data/persona/yzl/persona.yaml`：乐正绫人格配置。
- `scripts/generate_yzl_persona_dataset.py`：LoRA 数据集生成脚本。注意它应和 runtime persona 逻辑保持分离。

### 4. 视觉与识图系统

- `aiagent/vision/image_store.py`：保存上传图片。
- `aiagent/vision/character_registry.py`：加载角色图库配置。
- `aiagent/vision/character_retriever.py`：基于本地角色图库进行候选召回。
- `aiagent/services/vision_service.py`：整合本地角色召回和模型视觉分析。
- `aiagent/graphs/vision_graph.py`：把识图结果转换成聊天上下文、记忆提示和 Live2D 建议。
- `apps/api/routes/vision.py`、`apps/api/routes/multimodal_chat.py`：提供直接识图和多模态聊天入口。

### 5. RAG 知识库系统

- `aiagent/knowledge/document_loader.py`：加载知识文档。
- `aiagent/knowledge/retriever.py`：BM25 与向量召回。
- `aiagent/knowledge/vector_store.py`：向量库与 embedding 适配。
- `aiagent/knowledge/reranker.py`：简单重排。
- `aiagent/knowledge/rag_pipeline.py`：索引构建、检索、上下文格式化和 rebuild 状态。
- `aiagent/graphs/rag_graph.py`：决定何时注入知识上下文。
- `apps/api/routes/knowledge.py`：知识库 stats、rebuild、search API。

### 6. 长期记忆系统

- `aiagent/memory/mem0_memory.py`：Mem0、Qdrant、图记忆适配。
- `aiagent/graphs/memory_graph.py`：记忆检索和写入流程。
- `aiagent/services/memory_policy_llm_service.py`：判断一轮对话是否值得写入长期记忆。
- `apps/api/routes/memory.py`：记忆 stats、search、clear API。

### 7. 语音与音频系统

- `integrations/asr/*`：麦克风、VAD、mock ASR、Faster Whisper ASR。
- `aiagent/perception/*`：输入源归一化和语音回合管理。
- `integrations/tts/*`：GPT-SoVITS、IndexTTS2、VoxCPM、mock TTS 和文本清理。
- `aiagent/expression/tts_dispatcher.py`：TTS 调度。
- `aiagent/expression/audio_playback_dispatcher.py`：音频播放调度。
- `apps/api/routes/voice.py`、`audio.py`：语音识别、语音状态和音频访问 API。

### 8. Live2D 系统

- `aiagent/live2d/*`：Live2D 领域层，负责角色 profile、动作映射、表情映射、场景映射和 payload 构建。
- `aiagent/expression/live2d_payload_dispatcher.py`：从 `ResponsePacket` 生成 Live2D 命令文件。
- `integrations/live2d/*`：集成层，负责文件客户端、Python Live2D runtime 检查、模型扫描、profile 生成、模型会话、headless renderer 和 Qt OpenGL 控件。
- `apps/api/routes/live2d.py`：Live2D stats、preview、runtime inspect、model scan、profile generate API。
- `apps/desktop_qt/live2d_view_panel.py`、`integrations/live2d/qt_live2d_widget.py`：Qt 前端 Live2D 面板。

### 9. Qt 前端

- `apps/desktop_qt/chat_window.py`：当前主调试前端。已经包含聊天、图片上传、语音录制、记忆显示、知识库控制、API Detail、Live2D 面板。
- 新增 Qt 功能应优先做成 panel/widget 并插入该窗口。

### 10. Web 前端

- `apps/web`：Next.js 前端骨架，目前主要是 README 和基础页面。
- 当前主力前端仍是 Qt。

## 当前阶段状态

- 第一阶段：核心聊天、RAG、记忆、Persona 基础能力已经基本成型。
- 第二阶段：识图、多模态聊天、角色图库召回、VisionGraph 接入已经完成。
- 第三阶段：Live2D payload、Python runtime 检查、Qt 面板、模型资源工具已经完成。真实 Cubism 模型资源尚未放入。

## 当前关键缺口

1. 真实 Live2D 模型资源缺失。
   - 预期路径：`data/live2d/characters/yzl/model/yzl.model3.json`
   - 当前 `scripts/test_phase3_live2d.ps1` 返回 `model3_json_missing` 是正确状态，不是代码错误。

2. 工作区存在未提交改动。
   - 当前 `git status` 显示 persona、config、bootstrap、Live2D 相关文件仍有改动。
   - 大改前建议先确认这些改动是否预期，并做一次提交或快照。

3. 运行缓存较多。
   - `data/cache/mock_live2d/*.json`、录音、上传图片、知识库缓存等是运行产物。
   - 后续不要把缓存文件当成源码依赖。

4. `domain/*` 多数是早期占位。
   - 当前有效业务主要在 `aiagent/*`、`apps/*`、`integrations/*`。
   - 不建议把新功能写进 `domain/*`，除非明确要做领域层重构。

## 下一阶段建议

建议第四阶段先做稳定化和工程收敛，不建议立即继续开大功能。

### 优先级 1：运行时稳定性

- 做统一启动诊断，检查 Qdrant、RAG embedding、memory provider、vision provider、TTS、ASR、Live2D 模型资源。
- 可选子系统不可用时应明确降级，而不是直接 500。
- 在 `config/settings.py` 中补 provider 组合校验。

### 优先级 2：测试收敛

应补以下测试：

- `/chat`
- `/chat/multimodal`
- `/vision/analyze`
- `/live2d/preview`
- `/knowledge/rebuild/status`
- `PersonaGuard`
- `Live2DPayloadBuilder`
- `VisionService` mock 与本地召回路径
- `RAGPipeline` rebuild/status

### 优先级 3：真实 Live2D 模型接入

接入顺序：

1. 把真实 Cubism 资源放入 `data/live2d/characters/yzl/model`。
2. 运行 `scripts/scan_live2d_models.ps1`。
3. 使用 `scripts/generate_live2d_profile.ps1` 生成或更新 `profile.yaml`。
4. 运行 `scripts/test_phase3_live2d.ps1`。
5. 打开 Qt 前端验证模型渲染和 payload 驱动。

### 优先级 4：Qt 前端整理

- 把 API Detail、Memory Status、Live2D Payload、Runtime Snapshot 改成 tabs。
- 把图片上传和 Live2D 显示保持在同一调试工作流里。
- 右侧面板不要继续无限纵向堆叠。

### 优先级 5：训练数据工具规范

- 保持 `scripts/generate_yzl_persona_dataset.py` 作为唯一数据集生成入口。
- 增加 dataset lint：
  - 重复 prompt 检查
  - 禁词检查
  - 核心/日常/功能比例检查
  - 过长样本检查
  - 功能问答是否先给正确答案

## 后续开发入口规则

- 新 HTTP 接口：写在 `apps/api/routes/*`，保持薄封装。
- 新 runtime 能力：写在 `apps/core/runtime.py`，必要时在 `apps/core/bootstrap.py` 装配。
- 新图流程行为：写在 `aiagent/graphs/*`。
- 新 LLM prompt 或归一化：写在 `aiagent/cognition/*` 或 `aiagent/persona/*`。
- 新识图能力：写在 `aiagent/services/vision_service.py`、`aiagent/vision/*` 或 `aiagent/graphs/vision_graph.py`。
- 新记忆策略：写在 `aiagent/graphs/memory_graph.py` 或 `aiagent/services/memory_policy_llm_service.py`。
- 新 Live2D 能力：
  - 领域映射：`aiagent/live2d/*`
  - 输出调度：`aiagent/expression/live2d_payload_dispatcher.py`
  - Python/Qt/文件集成：`integrations/live2d/*`
  - Qt UI：`apps/desktop_qt/*`
- 新 Qt UI：优先做 panel/widget 并接入 `apps/desktop_qt/chat_window.py`。

如果一个新文件无法落到上述入口之一，通常说明它在重复已有功能。
"""
    OVERVIEW_OUT.write_text(content, encoding="utf-8")


def main() -> None:
    generate_inventory()
    generate_overview()
    print(f"wrote {INVENTORY_OUT}")
    print(f"wrote {OVERVIEW_OUT}")


if __name__ == "__main__":
    main()
