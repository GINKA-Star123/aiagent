from __future__ import annotations

import os
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from aiagent.diagnostics.models import DiagnosticCheck, DiagnosticReport
from config.settings import settings


class RuntimeDiagnostics:
    def run(self) -> DiagnosticReport:
        checks = [
            self._check_api_config(),
            self._check_llm_provider("llm", settings.llm_provider, settings.llm_model, settings.enable_mock_llm),
            self._check_llm_provider("state", settings.state_provider, settings.state_model, settings.enable_mock_state),
            self._check_llm_provider("planner", settings.planner_provider, settings.planner_model, settings.enable_mock_planner),
            self._check_rag_embedding(),
            self._check_rag_files(),
            self._check_memory_config(),
            self._check_qdrant(),
            self._check_neo4j(),
            self._check_vision_config(),
            self._check_vision_character_assets(),
            self._check_tts_config(),
            self._check_asr_config(),
            self._check_live2d_config(),
            self._check_live2d_assets(),
        ]
        return DiagnosticReport.from_checks(checks)

    def _check_api_config(self) -> DiagnosticCheck:
        valid_port = 1 <= int(settings.api_port) <= 65535
        if not valid_port:
            return DiagnosticCheck(
                name="api_config",
                status="failed",
                summary="API port is invalid.",
                details={"api_host": settings.api_host, "api_port": settings.api_port},
                action="检查 API_PORT，端口必须在 1 到 65535 之间。",
            )

        return DiagnosticCheck(
            name="api_config",
            status="ok",
            summary="API basic config is valid.",
            details={
                "app_name": settings.app_name,
                "app_env": settings.app_env,
                "api_host": settings.api_host,
                "api_port": settings.api_port,
            },
        )

    def _check_llm_provider(
        self,
        name: str,
        provider: str,
        model: str,
        enable_mock: bool,
    ) -> DiagnosticCheck:
        provider_name = provider.strip().lower()

        if enable_mock or provider_name == "mock":
            return DiagnosticCheck(
                name=f"{name}_provider",
                status="ok",
                summary=f"{name} uses mock provider.",
                details={"provider": provider, "model": model, "mock": True},
            )

        if not model.strip():
            return DiagnosticCheck(
                name=f"{name}_provider",
                status="failed",
                summary=f"{name} model is empty.",
                details={"provider": provider, "model": model},
                action=f"配置 {name.upper()}_MODEL。",
            )

        if provider_name == "openai":
            return self._check_api_key_provider(
                check_name=f"{name}_provider",
                provider=provider,
                model=model,
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                env_name="OPENAI_API_KEY",
            )

        if provider_name == "siliconflow":
            return self._check_api_key_provider(
                check_name=f"{name}_provider",
                provider=provider,
                model=model,
                api_key=settings.siliconflow_api_key,
                base_url=settings.siliconflow_base_url,
                env_name="SILICONFLOW_API",
            )

        if provider_name == "lmstudio":
            tcp = self._check_url_tcp(settings.lmstudio_base_url, timeout=0.4)
            status = "ok" if tcp["reachable"] else "degraded"
            return DiagnosticCheck(
                name=f"{name}_provider",
                status=status,
                summary="LM Studio provider configured." if tcp["reachable"] else "LM Studio provider configured but endpoint is not reachable.",
                details={
                    "provider": provider,
                    "model": model,
                    "base_url": settings.lmstudio_base_url,
                    "tcp": tcp,
                },
                action="" if tcp["reachable"] else "确认 LM Studio 服务已启动，且 LMSTUDIO_BASE_URL 正确。",
            )

        return DiagnosticCheck(
            name=f"{name}_provider",
            status="degraded",
            summary=f"Unknown {name} provider.",
            details={"provider": provider, "model": model},
            action="确认 provider 名称是否被 LLMService 支持。",
        )

    def _check_api_key_provider(
        self,
        *,
        check_name: str,
        provider: str,
        model: str,
        api_key: str | None,
        base_url: str,
        env_name: str,
    ) -> DiagnosticCheck:
        if not self._has_secret(api_key):
            return DiagnosticCheck(
                name=check_name,
                status="failed",
                summary=f"{provider} API key is missing.",
                details={
                    "provider": provider,
                    "model": model,
                    "base_url": base_url,
                    "required_env": env_name,
                },
                action=f"配置 {env_name}。",
            )

        return DiagnosticCheck(
            name=check_name,
            status="ok",
            summary=f"{provider} provider config is present.",
            details={
                "provider": provider,
                "model": model,
                "base_url": base_url,
                "required_env": env_name,
            },
        )

    def _check_rag_embedding(self) -> DiagnosticCheck:
        provider = settings.rag_embedding_provider.strip().lower()
        model_path = settings.rag_embedding_model_path.strip()

        if provider == "huggingface":
            details = {
                "provider": settings.rag_embedding_provider,
                "model_name": settings.rag_embedding_model_name,
                "model_path": model_path,
                "device": settings.rag_embedding_device,
                "local_files_only": settings.rag_embedding_local_files_only,
            }

            if model_path and not Path(model_path).exists():
                return DiagnosticCheck(
                    name="rag_embedding",
                    status="failed",
                    summary="RAG embedding model path does not exist.",
                    details=details,
                    action="检查 RAG_EMBEDDING_MODEL_PATH，或改用可用的本地模型目录。",
                )

            if settings.rag_embedding_local_files_only and not model_path:
                return DiagnosticCheck(
                    name="rag_embedding",
                    status="degraded",
                    summary="RAG embedding uses local files only but no explicit model path is configured.",
                    details=details,
                    action="建议配置 RAG_EMBEDDING_MODEL_PATH，避免运行时访问 HuggingFace。",
                )

            return DiagnosticCheck(
                name="rag_embedding",
                status="ok",
                summary="RAG embedding config is present.",
                details=details,
            )

        if provider == "siliconflow":
            api_key = self._resolve_env_secret(settings.rag_embedding_api_key_env) or settings.siliconflow_api_key
            if not self._has_secret(api_key):
                return DiagnosticCheck(
                    name="rag_embedding",
                    status="failed",
                    summary="SiliconFlow RAG embedding API key is missing.",
                    details={
                        "provider": settings.rag_embedding_provider,
                        "model_name": settings.rag_embedding_model_name,
                        "api_key_env": settings.rag_embedding_api_key_env,
                        "base_url": settings.rag_embedding_base_url or settings.siliconflow_base_url,
                    },
                    action="配置 RAG_EMBEDDING_API_KEY_ENV 指向的环境变量，或配置 SILICONFLOW_API。",
                )

            return DiagnosticCheck(
                name="rag_embedding",
                status="ok",
                summary="SiliconFlow RAG embedding config is present.",
                details={
                    "provider": settings.rag_embedding_provider,
                    "model_name": settings.rag_embedding_model_name,
                    "base_url": settings.rag_embedding_base_url or settings.siliconflow_base_url,
                },
            )

        return DiagnosticCheck(
            name="rag_embedding",
            status="degraded",
            summary="Unknown RAG embedding provider.",
            details={"provider": settings.rag_embedding_provider},
            action="确认 LangChainVectorStore 是否支持该 embedding provider。",
        )

    def _check_rag_files(self) -> DiagnosticCheck:
        candidates = [
            Path("data/knowledge"),
            Path("data/cache/knowledge"),
            Path("data/cache/rag"),
        ]
        existing = [str(path) for path in candidates if path.exists()]

        status = "ok" if existing else "degraded"
        return DiagnosticCheck(
            name="rag_files",
            status=status,
            summary="RAG related directories found." if existing else "No common RAG data/cache directory found.",
            details={
                "checked": [str(path) for path in candidates],
                "existing": existing,
            },
            action="" if existing else "如果知识库功能需要启用，请确认文档目录和索引缓存目录是否已建立。",
        )

    def _check_memory_config(self) -> DiagnosticCheck:
        vector_provider = settings.memory_vector_provider.strip().lower()

        if vector_provider != "qdrant":
            return DiagnosticCheck(
                name="memory_config",
                status="degraded",
                summary="Memory vector provider is not qdrant.",
                details={
                    "vector_provider": settings.memory_vector_provider,
                    "collection": settings.memory_vector_collection,
                },
                action="确认 Mem0LongTermMemory 是否支持该 vector provider。",
            )

        return DiagnosticCheck(
            name="memory_config",
            status="ok",
            summary="Memory config is present.",
            details={
                "llm_provider": settings.memory_llm_provider,
                "llm_model": settings.memory_llm_model,
                "embedder_provider": settings.memory_embedder_provider,
                "embedder_model": settings.memory_embedder_model,
                "vector_provider": settings.memory_vector_provider,
                "collection": settings.memory_vector_collection,
                "embedding_dims": settings.memory_embedding_dims,
                "graph_enabled": settings.memory_enable_graph,
                "graph_provider": settings.memory_graph_provider,
                "neo4j_url": settings.neo4j_url,
                "neo4j_database": settings.neo4j_database,
            },
        )

    def _check_qdrant(self) -> DiagnosticCheck:
        if settings.memory_vector_provider.strip().lower() != "qdrant":
            return DiagnosticCheck(
                name="qdrant",
                status="skipped",
                summary="Qdrant check skipped because memory vector provider is not qdrant.",
                details={"memory_vector_provider": settings.memory_vector_provider},
            )

        reachable = self._check_tcp(settings.qdrant_host, int(settings.qdrant_port), timeout=0.4)
        status = "ok" if reachable else "degraded"

        return DiagnosticCheck(
            name="qdrant",
            status=status,
            summary="Qdrant is reachable." if reachable else "Qdrant is not reachable.",
            details={
                "host": settings.qdrant_host,
                "port": settings.qdrant_port,
                "reachable": reachable,
            },
            action="" if reachable else "启动 Qdrant，或确认 QDRANT_HOST / QDRANT_PORT。",
        )

    def _check_neo4j(self) -> DiagnosticCheck:
        if not settings.memory_enable_graph:
            return DiagnosticCheck(
                name="neo4j",
                status="skipped",
                summary="Neo4j check skipped because graph memory is disabled.",
                details={"memory_enable_graph": settings.memory_enable_graph},
            )

        if settings.memory_graph_provider.strip().lower() != "neo4j":
            return DiagnosticCheck(
                name="neo4j",
                status="skipped",
                summary="Neo4j check skipped because graph provider is not neo4j.",
                details={"memory_graph_provider": settings.memory_graph_provider},
            )

        parsed = urlparse(settings.neo4j_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 7687
        reachable = self._check_tcp(host, int(port), timeout=0.4)

        if not self._has_secret(settings.neo4j_password):
            return DiagnosticCheck(
                name="neo4j",
                status="failed",
                summary="Neo4j password is missing while graph memory is enabled.",
                details={
                    "url": settings.neo4j_url,
                    "username": settings.neo4j_username,
                    "database": settings.neo4j_database,
                    "reachable": reachable,
                },
                action="Configure NEO4J_PASSWORD, or disable MEMORY_ENABLE_GRAPH.",
            )

        return DiagnosticCheck(
            name="neo4j",
            status="ok" if reachable else "degraded",
            summary="Neo4j is reachable." if reachable else "Neo4j is not reachable.",
            details={
                "url": settings.neo4j_url,
                "username": settings.neo4j_username,
                "database": settings.neo4j_database,
                "reachable": reachable,
            },
            action="" if reachable else "Start Neo4j, or check NEO4J_URL / Docker service networking.",
        )

    def _check_vision_config(self) -> DiagnosticCheck:
        provider = settings.vision_provider.strip().lower()

        if provider in {"mock", "disabled", "none"}:
            return DiagnosticCheck(
                name="vision_config",
                status="ok",
                summary="Vision uses mock or disabled provider.",
                details={"provider": settings.vision_provider},
            )

        if not settings.vision_model.strip():
            return DiagnosticCheck(
                name="vision_config",
                status="failed",
                summary="Vision model is empty.",
                details={"provider": settings.vision_provider, "model": settings.vision_model},
                action="配置 VISION_MODEL。",
            )

        if provider == "lmstudio":
            tcp = self._check_url_tcp(settings.lmstudio_base_url, timeout=0.4)
            return DiagnosticCheck(
                name="vision_config",
                status="ok" if tcp["reachable"] else "degraded",
                summary="Vision LM Studio provider configured." if tcp["reachable"] else "Vision LM Studio provider configured but endpoint is not reachable.",
                details={
                    "provider": settings.vision_provider,
                    "model": settings.vision_model,
                    "base_url": settings.lmstudio_base_url,
                    "timeout_seconds": settings.vision_timeout_seconds,
                    "tcp": tcp,
                },
                action="" if tcp["reachable"] else "确认 LM Studio 服务已启动，并确认 LMSTUDIO_BASE_URL 正确。",
            )

        api_key = self._resolve_env_secret(settings.vision_api_key_env)
        if provider in {"openai", "siliconflow"} and not self._has_secret(api_key):
            return DiagnosticCheck(
                name="vision_config",
                status="failed",
                summary="Vision API key is missing.",
                details={
                    "provider": settings.vision_provider,
                    "model": settings.vision_model,
                    "api_key_env": settings.vision_api_key_env,
                    "base_url": settings.vision_base_url,
                },
                action="配置 VISION_API_KEY_ENV 指向的环境变量。",
            )

        return DiagnosticCheck(
            name="vision_config",
            status="ok",
            summary="Vision config is present.",
            details={
                "provider": settings.vision_provider,
                "model": settings.vision_model,
                "base_url": settings.vision_base_url,
                "timeout_seconds": settings.vision_timeout_seconds,
            },
        )

    def _check_vision_character_assets(self) -> DiagnosticCheck:
        root = Path(settings.vision_character_root_dir)
        index_dir = Path(settings.vision_character_index_dir)
        records_path = index_dir / "records.json"
        index_path = index_dir / "faiss.index"

        image_count = 0
        character_dirs = []

        if root.exists():
            for child in root.iterdir():
                if child.is_dir():
                    character_dirs.append(child.name)
                    image_dir = child / "images"
                    if image_dir.exists():
                        image_count += len(
                            [
                                path
                                for path in image_dir.iterdir()
                                if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
                            ]
                        )

        if not root.exists():
            status = "degraded"
            summary = "Vision character root directory does not exist."
            action = "确认 VISION_CHARACTER_ROOT_DIR，或创建角色图库目录。"
        elif image_count == 0:
            status = "degraded"
            summary = "Vision character directory exists but no reference images were found."
            action = "给每个角色补充 images 目录和参考图。"
        elif not records_path.exists() or not index_path.exists():
            status = "degraded"
            summary = "Vision character images exist but index files are missing."
            action = "调用 POST /vision/characters/rebuild?force_rebuild=true 重建索引。"
        else:
            status = "ok"
            summary = "Vision character assets and index files are present."
            action = ""

        return DiagnosticCheck(
            name="vision_character_assets",
            status=status,
            summary=summary,
            details={
                "root": str(root),
                "index_dir": str(index_dir),
                "records_path": str(records_path),
                "index_path": str(index_path),
                "character_dirs": character_dirs,
                "reference_image_count": image_count,
                "records_exists": records_path.exists(),
                "index_exists": index_path.exists(),
            },
            action=action,
        )

    def _check_tts_config(self) -> DiagnosticCheck:
        provider = settings.tts_provider.strip().lower()

        if settings.enable_mock_tts or provider == "mock":
            return DiagnosticCheck(
                name="tts_config",
                status="ok",
                summary="TTS uses mock provider.",
                details={"provider": settings.tts_provider, "mock": True},
            )

        if provider == "gpt_sovits":
            tcp = self._check_url_tcp(settings.gpt_sovits_base_url, timeout=0.4)
            return DiagnosticCheck(
                name="tts_config",
                status="ok" if tcp["reachable"] else "degraded",
                summary="GPT-SoVITS endpoint is reachable." if tcp["reachable"] else "GPT-SoVITS endpoint is not reachable.",
                details={
                    "provider": settings.tts_provider,
                    "base_url": settings.gpt_sovits_base_url,
                    "ref_audio_path": settings.gpt_sovits_ref_audio_path,
                    "tcp": tcp,
                },
                action="" if tcp["reachable"] else "确认 GPT-SoVITS 服务已启动。",
            )

        if provider == "indextts2":
            tcp = self._check_url_tcp(settings.indextts2_base_url, timeout=0.4)
            return DiagnosticCheck(
                name="tts_config",
                status="ok" if tcp["reachable"] else "degraded",
                summary="IndexTTS2 endpoint is reachable." if tcp["reachable"] else "IndexTTS2 endpoint is not reachable.",
                details={
                    "provider": settings.tts_provider,
                    "base_url": settings.indextts2_base_url,
                    "ref_audio_path": settings.indextts2_ref_audio_path,
                    "tcp": tcp,
                },
                action="" if tcp["reachable"] else "确认 IndexTTS2 服务已启动。",
            )

        if provider == "voxcpm":
            return DiagnosticCheck(
                name="tts_config",
                status="ok",
                summary="VoxCPM TTS config is present.",
                details={
                    "provider": settings.tts_provider,
                    "base_url": settings.voxcpm_base_url,
                    "timeout_seconds": settings.tts_timeout_seconds,
                },
            )

        return DiagnosticCheck(
            name="tts_config",
            status="degraded",
            summary="Unknown TTS provider.",
            details={"provider": settings.tts_provider},
            action="确认 TTSDispatcher 是否支持该 provider。",
        )

    def _check_asr_config(self) -> DiagnosticCheck:
        provider = settings.asr_provider.strip().lower()

        if settings.enable_mock_asr or provider == "mock":
            return DiagnosticCheck(
                name="asr_config",
                status="ok",
                summary="ASR uses mock provider.",
                details={"provider": settings.asr_provider, "mock": True},
            )

        if provider in {"faster_whisper", "faster-whisper", "whisper"}:
            model_path = settings.asr_model_path.strip()
            if model_path and not Path(model_path).exists():
                return DiagnosticCheck(
                    name="asr_config",
                    status="failed",
                    summary="ASR model path does not exist.",
                    details={
                        "provider": settings.asr_provider,
                        "model_size": settings.asr_model_size,
                        "model_path": model_path,
                        "device": settings.asr_device,
                        "compute_type": settings.asr_compute_type,
                    },
                    action="检查 ASR_MODEL_PATH，或清空后使用 ASR_MODEL_SIZE 下载/缓存模型。",
                )

            return DiagnosticCheck(
                name="asr_config",
                status="ok",
                summary="ASR config is present.",
                details={
                    "provider": settings.asr_provider,
                    "model_size": settings.asr_model_size,
                    "model_path": model_path,
                    "device": settings.asr_device,
                    "compute_type": settings.asr_compute_type,
                    "language": settings.asr_language,
                },
            )

        return DiagnosticCheck(
            name="asr_config",
            status="degraded",
            summary="Unknown ASR provider.",
            details={"provider": settings.asr_provider},
            action="确认 ASRListener 是否支持该 provider。",
        )

    def _check_live2d_config(self) -> DiagnosticCheck:
        provider = settings.live2d_provider.strip().lower()

        if provider in {"mock", "noop", "disabled"}:
            return DiagnosticCheck(
                name="live2d_config",
                status="ok",
                summary="Live2D uses mock/noop provider.",
                details={
                    "provider": settings.live2d_provider,
                    "enable_live2d_runtime": settings.enable_live2d_runtime,
                },
            )

        return DiagnosticCheck(
            name="live2d_config",
            status="ok",
            summary="Live2D provider config is present.",
            details={
                "provider": settings.live2d_provider,
                "enable_live2d_runtime": settings.enable_live2d_runtime,
            },
        )

    def _check_live2d_assets(self) -> DiagnosticCheck:
        root = Path("data/live2d/characters")
        profile_paths = list(root.glob("*/profile.yaml")) if root.exists() else []
        expected_yzl_model = Path("data/live2d/characters/yzl/model/yzl.model3.json")

        if not root.exists():
            return DiagnosticCheck(
                name="live2d_assets",
                status="degraded",
                summary="Live2D character root does not exist.",
                details={"root": str(root)},
                action="创建 data/live2d/characters，并放入角色模型资源。",
            )

        if not profile_paths:
            return DiagnosticCheck(
                name="live2d_assets",
                status="degraded",
                summary="No Live2D character profile found.",
                details={"root": str(root), "profile_count": 0},
                action="创建角色 profile.yaml，或使用 /live2d/profile/generate 生成。",
            )

        status = "ok" if expected_yzl_model.exists() else "degraded"
        return DiagnosticCheck(
            name="live2d_assets",
            status=status,
            summary="Live2D profiles found." if status == "ok" else "Live2D profile exists but default yzl model3 json is missing.",
            details={
                "root": str(root),
                "profile_count": len(profile_paths),
                "profiles": [str(path) for path in profile_paths],
                "expected_yzl_model": str(expected_yzl_model),
                "expected_yzl_model_exists": expected_yzl_model.exists(),
            },
            action="" if status == "ok" else "补充 data/live2d/characters/yzl/model/yzl.model3.json，或修改 profile.yaml 指向真实模型。",
        )

    def _resolve_env_secret(self, value: str | None) -> str | None:
        if value is None:
            return None

        candidate = value.strip()
        if not candidate:
            return None

        env_value = os.getenv(candidate)
        if env_value:
            return env_value.strip()

        if candidate.lower().startswith(("sk-", "sk_", "api-", "pk-")):
            return candidate

        return None

    def _has_secret(self, value: str | None) -> bool:
        if value is None:
            return False
        stripped = value.strip()
        if not stripped:
            return False
        if stripped.lower() in {"none", "null", "changeme", "your_api_key"}:
            return False
        return True

    def _check_url_tcp(self, url: str, timeout: float) -> dict[str, Any]:
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port

        if not host:
            return {
                "reachable": False,
                "host": "",
                "port": None,
                "error": "invalid_url",
            }

        if port is None:
            port = 443 if parsed.scheme == "https" else 80

        reachable = self._check_tcp(host, port, timeout=timeout)
        return {
            "reachable": reachable,
            "host": host,
            "port": port,
            "scheme": parsed.scheme,
        }

    def _check_tcp(self, host: str, port: int, timeout: float) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False
