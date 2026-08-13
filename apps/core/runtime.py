"""核心应用的 runtime 生命周期管理。

CoreRuntime 是 API 路由和本地工具共用的门面。它把 HTTP 友好的方法调用
转换成 InputEvent，再交给 dispatcher 和图流程执行推理。
"""
from typing import Any
from apps.core.capabilities import CapabilityRegistry

from aiagent.brain.agent_core import AgentCore
from aiagent.brain.dialogue_manager import DialogueManager
from aiagent.graphs.memory_graph import MemoryRunner
from aiagent.graphs.metadata_utils import mark_stage_done, now_perf
from aiagent.graphs.vision_graph import VisionRunner
from aiagent.knowledge.query_normalizer import normalize_rag_query
from aiagent.knowledge.rag_pipeline import RAGPipeline
from aiagent.graphs.graph_model import VisionAnalyzeResult
from aiagent.memory.mem0_memory import Mem0LongTermMemory
from aiagent.memory.memory_layers import infer_memory_layer
from aiagent.orchestrator.dispatcher import EventDispatcher
from aiagent.orchestrator.interrupt_manager import InterruptManager
from aiagent.perception.asr_listener import ASRListener
from aiagent.perception.source_router import SourceRouter
from aiagent.perception.voice_session_controller import VoiceSessionController
from aiagent.perception.voice_turn_manager import VoiceTurnManager
from aiagent.schemas.inputs import InputEvent, InputSource, InputAttachment
from aiagent.schemas.outputs import OutputEvent
from aiagent.schemas.memory import (
    MemoryCategory,
    MemoryEditRequest,
    MemoryImportance,
    MemoryLayer,
    MemoryMergeRequest,
)
from aiagent.services.llm_service import LLMService
from aiagent.services.vision_service import VisionService
from aiagent.state.conversation_state import ConversationState
from aiagent.state.speaking_state import SpeakingState
from aiagent.state.stream_state import StreamingState
from aiagent.live2d.payload_contract import normalize_live2d_payload


class CoreRuntime:
    """API 路由共享的长生命周期 runtime 容器。"""

    def __init__(
        self,
        dispatcher: EventDispatcher,
        agent_core: AgentCore,
        speaking_state: SpeakingState,
        asr_listener: ASRListener,
        stream_state: StreamingState,
        long_term_memory: Mem0LongTermMemory,
        memory_runner: MemoryRunner,
        source_router: SourceRouter,
        llm_service: LLMService,
        conversation_state: ConversationState,
        dialogue_manager: DialogueManager,
        interrupt_manager: InterruptManager,
        rag_pipeline: RAGPipeline,
        voice_turn_manager: VoiceTurnManager | None = None,
        voice_session_controller: VoiceSessionController | None = None,
        vision_service: VisionService | None = None,
        vision_runner: VisionRunner | None = None,
        capabilities: CapabilityRegistry | None = None,
    ) -> None:
        self.dispatcher = dispatcher
        self.agent_core = agent_core
        self.speaking_state = speaking_state
        self.asr_listener = asr_listener
        self.stream_state = stream_state
        self.long_term_memory = long_term_memory
        self.memory_runner = memory_runner
        self.source_router = source_router
        self.llm_service = llm_service
        self.conversation_state = conversation_state
        self.dialogue_manager = dialogue_manager
        self.interrupt_manager = interrupt_manager
        self.rag_pipeline = rag_pipeline
        self.voice_turn_manager = voice_turn_manager
        self.voice_session_controller = voice_session_controller
        self.vision_service = vision_service
        self.vision_runner = vision_runner
        self.capabilities = capabilities or CapabilityRegistry()

    def handle_input_event(self, event: InputEvent) -> OutputEvent:
        """把标准化后的输入事件交给编排器处理。"""
        return self.dispatcher.handle_input(event)

    def handle_source_payload(self, source: str, payload: dict) -> OutputEvent:
        event = self.source_router.route(source=source, payload=payload)
        return self.handle_input_event(event)

    def handle_chat(self, text: str, user_id: str = "guest", username: str = "guest") -> str:
        event = InputEvent(source=InputSource.CHAT, text=text, user_id=user_id, user_name=username)
        return self.handle_input_event(event).packet.reply_text

    def handle_chat_full(self, text: str, user_id: str = "guest", username: str = "guest") -> OutputEvent:
        event = InputEvent(source=InputSource.CHAT, user_id=user_id, user_name=username, text=text)
        return self.handle_input_event(event)

    def handle_asr_text(self, audio_text: str, user_id: str = "mic", username: str = "麦克风输入") -> OutputEvent:
        event = InputEvent(
            source=InputSource.ASR,
            text=audio_text,
            user_id=user_id,
            user_name=username,
            metadata={"asr_mode": "text"},
        )
        return self.handle_input_event(event)

    def handle_voice_once(self, user_id: str = "mic", username: str = "麦克风输入", record_seconds: int = 5) -> OutputEvent:
        transcript = self.asr_listener.listen_once(record_seconds=record_seconds)
        event = InputEvent(
            source=InputSource.ASR,
            text=transcript,
            user_id=user_id,
            user_name=username,
            metadata={"asr_mode": "microphone_fixed"},
        )
        return self.handle_input_event(event)

    def handle_voice_turn(
        self,
        user_id: str = "mic",
        username: str = "麦克风输入",
        max_seconds: float = 8.0,
        silence_seconds: float = 1.2,
        interrupt_playback: bool = True,
    ) -> OutputEvent:
        if self.voice_turn_manager is None:
            raise RuntimeError("Voice turn manager is not configured.")

        transcript = self.voice_turn_manager.capture_turn(
            max_seconds=max_seconds,
            silence_seconds=silence_seconds,
            interrupt_playback=interrupt_playback,
        )

        event = InputEvent(
            source=InputSource.ASR,
            text=transcript,
            user_id=user_id,
            user_name=username,
            metadata={"asr_mode": "voice_turn"},
        )
        return self.handle_input_event(event)

    def handle_multimodal_chat_upload(
        self,
        file_obj,
        filename: str,
        text: str,
        user_id: str = "guest",
        username: str = "guest",
    ) -> OutputEvent:
        """保存上传图片、挂载元数据，然后进入主图流程。"""
        attachments: list[InputAttachment] = []

        if file_obj is not None and filename:
            if self.vision_service is None:
                raise RuntimeError("Vision service is not configured.")

            stored = self.vision_service.image_store.save_upload(
                file_obj=file_obj,
                filename=filename,
            )

            attachments.append(
                InputAttachment(
                    type="image",
                    path=str(stored.path),
                    filename=filename,
                    mime_type=f"image/{stored.format.lower()}",
                    image_id=stored.image_id,
                    metadata={
                        "sha256": stored.sha256,
                        "width": stored.width,
                        "height": stored.height,
                        "format": stored.format,
                    },
                )
            )

        modality = "mixed" if text.strip() and attachments else "image" if attachments else "text"

        event = InputEvent(
            source=InputSource.MULTIMODAL,
            text=text,
            user_id=user_id,
            user_name=username,
            modality=modality,
            attachments=attachments,
            metadata={
                "input_source": "chat_multimodal",
            },
        )

        return self.handle_input_event(event)

    def interrupt_speaking(self, reason: str = "runtime_interrupt") -> dict[str, str]:
        self.interrupt_manager.request_interrupt(reason=reason)

        if self.voice_session_controller is None:
            raise RuntimeError("Voice session controller is not configured.")
        
        self.voice_session_controller.interrupt_listening(reason=reason)
        return {"status": "interrupted", "reason": reason}

    def transcribe_audio_file(self, audio_path: str) -> str:
        return self.asr_listener.transcribe_file(audio_path)

    def get_knowledge_stats(self) -> dict:
        return self.rag_pipeline.stats()

    def rebuild_knowledge_index(self, force_rebuild: bool = True) -> dict:
        return self.rag_pipeline.build_index(force_rebuild=force_rebuild)
    
    def rebuild_knowledge_index_async(self,force_rebuild:bool=True) ->dict:
        return self.rag_pipeline.rebuild_async(force_rebuild=force_rebuild)
    
    def get_knowledge_rebuild_status(self) ->dict:
        return self.rag_pipeline.build_status()

    def search_knowledge(self, query: str, top_k: int = 4) -> list[dict]:
        normalized_query = normalize_rag_query(query)
        return self.rag_pipeline.debug_retrieve(query=normalized_query, top_k=top_k)

    def get_knowledge_prompt_context(self, query: str, top_k: int = 4) -> str:
        normalized_query = normalize_rag_query(query)
        return self.rag_pipeline.format_for_prompt(query=normalized_query, top_k=top_k)

    def inspect_knowledge(self,query:str,top_k: int =4) -> dict:
        normalized_query = normalize_rag_query(query)

        if hasattr(self.rag_pipeline,"inspect"):
            return self.rag_pipeline.inspect(query=normalized_query, top_k=top_k)
        
        chunks = self.rag_pipeline.debug_retrieve(
        query=normalized_query,
        top_k=top_k,
    )
        return {
            "ok": True,
            "query": normalized_query,
            "top_k": top_k,
            "should_inject": bool(chunks),
            "confidence": {},
            "citations": [],
            "chunks": chunks,
            "prompt_context": self.rag_pipeline.format_for_prompt(
                query=normalized_query,
                top_k=top_k,
            ),
        }

    def get_speaking_state(self) -> SpeakingState:
        if self.voice_session_controller is not None:
            self.voice_session_controller.audio_playback_dispatcher.refresh_state()
        return self.speaking_state

    def get_stream_state(self) -> StreamingState:
        if self.voice_session_controller is not None:
            self.voice_session_controller.audio_playback_dispatcher.refresh_state()
        return self.stream_state

    def get_user_profile_memories(self, user_id: str, limit: int = 20) -> list[dict]:
        records = self.long_term_memory.list_profile_memories(
            user_id=user_id,
            limit=limit,
        )
        return [ # type: ignore
            record.model_dump(mode="json") if hasattr(record, "model_dump") else record
            for record in records
        ]

    def get_long_term_memories(self, user_id: str, limit: int = 20) -> list[dict]:
        records = self.long_term_memory.list_records(user_id=user_id, limit=limit)
        return [ # type: ignore
            record.model_dump(mode="json") if hasattr(record, "model_dump") else record
            for record in records
        ]
    def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        layer: str | None = None,
    ) -> dict:
        hits = self.long_term_memory.search(user_id=user_id, query=query, limit=limit)
        target_layer = MemoryLayer(str(layer)) if layer else None
        filtered_hits = []

        for hit in hits:
            hit_layer = infer_memory_layer(hit.metadata.get("category"), hit.metadata)
            if target_layer is not None and hit_layer != target_layer:
                continue
            filtered_hits.append((hit, hit_layer))

        return {
            "query": query,
            "memory_layer": target_layer.value if target_layer else "",
            "profile_memories": [],
            "long_term_memories": [
                {
                    "id": hit.id,
                    "memory": hit.memory,
                    "score": hit.score,
                    "layer": hit_layer.value,
                    "memory_layer": hit_layer.value,
                    "metadata": hit.metadata,
                    "relations": hit.relations,
                    "created_at": hit.created_at,
                    "updated_at": hit.updated_at,
                }
                for hit, hit_layer in filtered_hits
            ],
        }

    def get_memory_stats(self, user_id: str) -> dict:
        memories = self.long_term_memory.get_all(user_id=user_id, limit=1000)
        return {
            "user_id": user_id,
            "profile": {"count": 0},
            "long_term": {"count": len(memories)},
            "graph": self.get_memory_graph_status(),
        }

    def get_memory_graph_status(self) -> dict:
        return self.long_term_memory.graph_status()

    def clear_user_memories(self, user_id: str) -> dict[str, str]:
        self.long_term_memory.delete_all(user_id=user_id)
        self.agent_core.main_runner.clear_thread(user_id)
        return {"status": "cleared", "user_id": user_id}

    def get_memory_snapshot(self, user_id: str, limit: int = 200) -> dict:
        snapshot = self.long_term_memory.get_snapshot(
            user_id=user_id,
            limit=limit,
        )
        return snapshot.model_dump(mode="json") if hasattr(snapshot, "model_dump") else snapshot # type: ignore


    def get_user_memory_layer(
        self,
        user_id: str,
        layer: str,
        limit: int = 100,
    ) -> dict:
        target_layer = MemoryLayer(str(layer))
        records = self.long_term_memory.list_layer_records(
            user_id=user_id,
            layer=target_layer,
            limit=limit,
        )

        memories = [
            record.model_dump(mode="json") if hasattr(record, "model_dump") else record
            for record in records
        ]

        return {
            "user_id": user_id,
            "layer": target_layer.value,
            "count": len(memories),
            "memories": memories,
        }


    def delete_user_memory_item(self, user_id: str, memory_id: str) -> dict:
        records = self.long_term_memory.list_records(
            user_id=user_id,
            limit=1000,
        )

        owned = any(
            getattr(record, "id", "") == memory_id
            for record in records
        )

        if not owned:
            return {
                "ok": False,
                "status": "not_found",
                "user_id": user_id,
                "memory_id": memory_id,
                "reason": "memory_not_found_or_not_owned_by_user",
            }

        result = self.long_term_memory.delete_memory(memory_id)
        return {
            "ok": True,
            "status": "deleted",
            "user_id": user_id,
            "memory_id": memory_id,
            "result": result,
        }


    def delete_user_memory_layer(self, user_id: str, layer: str) -> dict:
        return self.long_term_memory.delete_layer(
            user_id=user_id,
            layer=MemoryLayer(str(layer)),
        )
    def reset_dialogue_context(self) -> dict[str, str]:
        self.agent_core.clear_runtime_context()
        self.conversation_state.clear()
        return {"status": "reset"}

    def pause_dialogue(self) -> dict[str, str]:
        self.dialogue_manager.pause_global()
        return {"status": "paused"}

    def resume_dialogue(self) -> dict[str, str]:
        self.dialogue_manager.resume_global()
        return {"status": "resumed"}

    def get_control_snapshot(self) -> dict:
        return {
            "dialogue_manager": self.dialogue_manager.snapshot(),
            "interrupt_manager": self.interrupt_manager.snapshot(),
            "speaking_state": self.speaking_state.model_dump(),
            "stream_state": self.stream_state.model_dump(),
        }
    
    def analyze_image_upload(
        self,
        file_obj,
        filename: str,
        user_prompt: str = "",
        user_id: str = "guest",
    ) -> VisionAnalyzeResult:
        if self.vision_service is None:
            raise RuntimeError("Vision service is not configured.")

        started_at = now_perf()
        result = self.vision_service.analyze_upload(
            file_obj=file_obj,
            filename=filename,
            user_prompt=user_prompt,
            user_id=user_id,
        )
        result.metadata = mark_stage_done(
            dict(result.metadata),
            "vision_graph",
            started_at,
        )
        return result

    def analyze_image_path(
        self,
        image_path: str,
        user_prompt: str = "",
        user_id: str = "guest",
    ) -> VisionAnalyzeResult:
        if self.vision_service is None:
            raise RuntimeError("Vision service is not configured.")

        started_at = now_perf()
        result = self.vision_service.analyze_local_path(
            image_path=image_path,
            user_prompt=user_prompt,
            user_id=user_id,
        )
        result.metadata = mark_stage_done(
            dict(result.metadata),
            "vision_graph",
            started_at,
        )
        return result

    def handle_vision_chat_upload(
        self,
        file_obj,
        filename: str,
        user_prompt: str,
        user_id: str = "guest",
        username: str = "guest",
    ) -> dict:
        """先执行视觉分析，再把结果转换成聊天输入。"""
        if self.vision_runner is None:
            raise RuntimeError("Vision runner is not configured.")

        vision_state = self.vision_runner.analyze_upload(
            file_obj=file_obj,
            filename=filename,
            user_prompt=user_prompt,
            user_id=user_id,
        )

        chat_text = self._build_vision_chat_text(
            user_prompt=user_prompt,
            vision_chat_context=vision_state.get("chat_context", ""),
            memory_hint=vision_state.get("memory_hint", ""),
        )

        chat_output = self.handle_chat_full(
            text=chat_text,
            user_id=user_id,
            username=username,
        )

        packet = chat_output.packet

        vision_metadata = vision_state.get("metadata", {})
        merged_metadata = dict(packet.metadata)
        for key, value in vision_metadata.items():
            merged_metadata[str(key)] = str(value)

        packet.metadata = merged_metadata

        live2d_suggestion = vision_state.get("live2d_suggestion", {})
        if isinstance(live2d_suggestion, dict) and live2d_suggestion:
            packet.live2d = self._merge_vision_live2d(
                original=packet.live2d,
                suggestion=live2d_suggestion,
            )

        return {
            "vision_state": vision_state,
            "chat_output": chat_output,
        }

    def rebuild_vision_character_index(self, force_rebuild: bool = True) -> dict:
        if self.vision_service is None:
            raise RuntimeError("Vision service is not configured.")

        return self.vision_service.rebuild_character_index(
            force_rebuild=force_rebuild,
        )

    def get_vision_character_index_stats(self) -> dict:
        if self.vision_service is None:
            raise RuntimeError("Vision service is not configured.")

        return self.vision_service.character_index_stats()

    def _build_vision_chat_text(
        self,
        user_prompt: str,
        vision_chat_context: str,
        memory_hint: str = "",
    ) -> str:
        parts = [
            user_prompt.strip() or "请看这张图片。",
            "",
            vision_chat_context.strip(),
        ]

        if memory_hint.strip():
            parts.extend(
                [
                    "",
                    "[视觉记忆候选]",
                    memory_hint.strip(),
                    "是否写入长期记忆仍然需要由 memory_graph 根据用户表达和长期价值判断。",
                ]
            )

        return "\n".join(part for part in parts if part is not None)

    def _merge_vision_live2d(self, original: dict, suggestion: dict) -> dict:
        live2d = dict(original or {})

        character = dict(live2d.get("character") or {})
        scene = dict(live2d.get("scene") or {})

        if suggestion.get("suggested_emotion"):
            character["emotion"] = suggestion["suggested_emotion"]
        if suggestion.get("suggested_expression"):
            character["expression"] = suggestion["suggested_expression"]
        if suggestion.get("suggested_motion"):
            character["motion"] = suggestion["suggested_motion"]
        if suggestion.get("suggested_background"):
            scene["background_id"] = suggestion["suggested_background"]

        live2d["character"] = character
        live2d["scene"] = scene

        return normalize_live2d_payload(
                live2d,
                metadata={
                    "source": "runtime_vision_merge",
                },
            )

    def get_capability_snapshot(self) ->dict[str,Any]:
        return self.capabilities.snapshot()

    def get_user_memory_preference(self, user_id: str) -> dict:
        pref = self.memory_runner.get_user_preference(user_id=user_id)
        return pref.model_dump(mode="json")

    def set_user_memory_preference(
        self,
        user_id: str,
        long_term_enabled: bool,
        reason: str = "",
    ) -> dict:
        pref = self.memory_runner.set_user_preference(
            user_id=user_id,
            long_term_enabled=long_term_enabled,
            reason=reason,
        )
        return pref.model_dump(mode="json")

    def edit_user_memory_item(
        self,
        *,
        user_id: str,
        memory_id: str,
        request: MemoryEditRequest,
    ) -> dict:
        return self.long_term_memory.update_memory(
            user_id=user_id,
            memory_id=memory_id,
            memory_text=request.memory,
            category=request.category,
            importance=request.importance,
            layer=request.layer,
            pinned=request.pinned,
            reason=request.reason,
            metadata=request.metadata,
        )

    def set_user_memory_pinned(
        self,
        *,
        user_id: str,
        memory_id: str,
        pinned: bool,
        reason: str = "",
    ) -> dict:
        return self.long_term_memory.set_memory_pinned(
            user_id=user_id,
            memory_id=memory_id,
            pinned=pinned,
            reason=reason,
        )

    def merge_user_memories(
        self,
        *,
        user_id: str,
        request: MemoryMergeRequest,
    ) -> dict:
        return self.long_term_memory.merge_memories(
            user_id=user_id,
            memory_ids=request.memory_ids,
            merged_memory=request.merged_memory,
            category=request.category,
            importance=request.importance,
            layer=request.layer,
            pinned=request.pinned,
            reason=request.reason,
            metadata=request.metadata,
        )
