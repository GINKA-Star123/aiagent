from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from apps.desktop_qt.api_client import APIClient
from apps.desktop_qt.recorder import AudioRecorder
from apps.desktop_qt.user_identity import DesktopIdentityStore
from apps.desktop_qt.live2d_view_panel import Live2DViewPanel

class Worker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, fn) -> None:
        super().__init__()
        self.fn = fn

    @Slot()
    def run(self) -> None:
        try:
            self.finished.emit(self.fn())
        except Exception as exc:
            self.error.emit(f"{exc}\n\n{traceback.format_exc()}")


class ChatBubble(QFrame):
    def __init__(self, speaker: str, text: str, align: str, bubble_color: str, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        name_label = QLabel(speaker)
        name_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #5b5347;")
        layout.addWidget(name_label)

        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text_label.setStyleSheet("font-size: 14px; color: #1f1f1f;")
        layout.addWidget(text_label)

        self.setMaximumWidth(430 if align == "right" else 580)
        self.setStyleSheet(
            f"""
            QFrame {{
                background: {bubble_color};
                border: 1px solid rgba(60, 60, 60, 0.10);
                border-radius: 12px;
            }}
            """
        )


class ChatWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("AIAgent Desktop Debug Panel")
        self.resize(1480, 920)

        self.identity_store = DesktopIdentityStore()
        self.user_id, self.username = self._load_or_create_identity()
        self.api_base_url = "http://127.0.0.1:8000"

        self.api_client = APIClient(self.api_base_url)
        self.recorder = AudioRecorder()

        self.current_thread: QThread | None = None
        self.current_worker: Worker | None = None
        self.current_task_name = ""
        self.selected_image_path = ""

        self._build_ui()
        self._append_system_message(f"桌面调试台已启动。当前用户：{self.username}。")
        self._set_status("就绪")
        self.run_startup_check()

    def closeEvent(self, event) -> None:
        try:
            if self.current_thread is not None and self.current_thread.isRunning():
                self.current_thread.quit()
                self.current_thread.wait(3000)
        except Exception:
            pass

        try:
            self.api_client.close()
        except Exception:
            pass

        super().closeEvent(event)

    def _load_or_create_identity(self) -> tuple[str, str]:
        identity = self.identity_store.load_identity()
        if identity is not None:
            return identity.user_id, identity.username

        username, ok = QInputDialog.getText(self, "输入昵称", "请输入你的名字：")
        if not ok or not username.strip():
            username = "Guest"

        identity = self.identity_store.create_identity(username.strip())
        return identity.user_id, identity.username

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        outer_layout = QVBoxLayout(root)
        outer_layout.setContentsMargins(18, 18, 18, 18)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([900, 700])

        outer_layout.addWidget(splitter)

        root.setStyleSheet(
            """
            QWidget {
                background: #efe6d8;
                font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
            }
            QFrame#leftPanel, QFrame#rightPanel {
                background: rgba(255, 252, 247, 0.94);
                border: 1px solid #d8ccbf;
                border-radius: 12px;
            }
            QPushButton {
                min-height: 34px;
                border-radius: 8px;
                border: 1px solid #b8aa9b;
                background: #fffaf2;
                color: #2f241f;
                font-weight: 700;
            }
            QPushButton:disabled {
                color: #9a9188;
                background: #e6ded5;
            }
            QTextEdit {
                border: 1px solid #d3c5b6;
                border-radius: 8px;
                background: #fffdf9;
                color: #1f1f1f;
                padding: 8px;
            }
            """
        )

    def _build_left_panel(self) -> QWidget:
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")

        layout = QVBoxLayout(left_panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_label = QLabel("Yzl 对话窗口")
        title_label.setStyleSheet("font-size: 26px; font-weight: 800; color: #2f241f;")
        layout.addWidget(title_label)

        self.identity_label = QLabel(
            f"当前用户：{self.username}\n用户ID：{self.user_id}\n服务端：{self.api_base_url}"
        )
        self.identity_label.setStyleSheet("font-size: 13px; color: #6f6258;")
        layout.addWidget(self.identity_label)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(8, 8, 8, 8)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch()
        self.chat_scroll.setWidget(self.chat_container)
        layout.addWidget(self.chat_scroll, 1)

        self.status_label = QLabel("状态：就绪")
        self.status_label.setStyleSheet("font-size: 13px; color: #705e50;")
        layout.addWidget(self.status_label)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("输入你想说的话……")
        self.input_edit.setMinimumHeight(120)
        self.input_edit.setMaximumHeight(190)
        layout.addWidget(self.input_edit)

        image_row = QHBoxLayout()
        self.image_label = QLabel("未选择图片")
        self.image_label.setStyleSheet("font-size: 13px; color: #705e50;")
        image_row.addWidget(self.image_label, 1)

        self.select_image_button = QPushButton("选择图片")
        self.select_image_button.clicked.connect(self.select_image_file)
        image_row.addWidget(self.select_image_button)

        self.clear_image_button = QPushButton("清除图片")
        self.clear_image_button.clicked.connect(self.clear_selected_image)
        self.clear_image_button.setDisabled(True)
        image_row.addWidget(self.clear_image_button)

        layout.addLayout(image_row)

        button_row = QHBoxLayout()
        self.send_button = QPushButton("发送消息")
        self.send_button.clicked.connect(self.send_text_message)
        button_row.addWidget(self.send_button)

        self.start_record_button = QPushButton("开始录音")
        self.start_record_button.clicked.connect(self.start_voice_recording)
        button_row.addWidget(self.start_record_button)

        self.stop_record_button = QPushButton("结束录音")
        self.stop_record_button.clicked.connect(self.stop_voice_recording)
        self.stop_record_button.setDisabled(True)
        button_row.addWidget(self.stop_record_button)

        layout.addLayout(button_row)
        return left_panel

    def _build_right_panel(self) -> QWidget:
        right_panel = QFrame()
        right_panel.setObjectName("rightPanel")

        layout = QVBoxLayout(right_panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        tools_scroll = QScrollArea()
        tools_scroll.setWidgetResizable(True)
        tools_scroll.setFrameShape(QFrame.NoFrame)

        tools_content = QWidget()
        tools_layout = QVBoxLayout(tools_content)
        tools_layout.setSpacing(12)

        control_card = self._build_section_card("快捷控制")
        control_grid = QGridLayout()
        control_grid.setHorizontalSpacing(10)
        control_grid.setVerticalSpacing(10)

        self.startup_check_button = QPushButton("启动自检")
        self.startup_check_button.clicked.connect(self.run_startup_check)
        control_grid.addWidget(self.startup_check_button, 0, 0)

        self.refresh_button = QPushButton("刷新状态")
        self.refresh_button.clicked.connect(self.refresh_state)
        control_grid.addWidget(self.refresh_button, 0, 1)

        self.pause_button = QPushButton("暂停对话")
        self.pause_button.clicked.connect(self.pause_dialogue)
        control_grid.addWidget(self.pause_button, 1, 0)

        self.resume_button = QPushButton("恢复对话")
        self.resume_button.clicked.connect(self.resume_dialogue)
        control_grid.addWidget(self.resume_button, 1, 1)

        self.interrupt_button = QPushButton("打断播放")
        self.interrupt_button.clicked.connect(self.interrupt_speaking)
        control_grid.addWidget(self.interrupt_button, 2, 0)

        self.reset_context_button = QPushButton("重置上下文")
        self.reset_context_button.clicked.connect(self.reset_context)
        control_grid.addWidget(self.reset_context_button, 2, 1)

        self.clear_memory_button = QPushButton("清空记忆")
        self.clear_memory_button.clicked.connect(self.clear_memory)
        control_grid.addWidget(self.clear_memory_button, 3, 0)

        self.clear_chat_button = QPushButton("清空聊天")
        self.clear_chat_button.clicked.connect(self.clear_chat)
        control_grid.addWidget(self.clear_chat_button, 3, 1)

        control_card.layout().addLayout(control_grid)
        tools_layout.addWidget(control_card)

        knowledge_card = self._build_section_card("知识库调试")
        self.knowledge_query_edit = QTextEdit()
        self.knowledge_query_edit.setPlaceholderText("输入问题，测试知识库召回……")
        self.knowledge_query_edit.setMaximumHeight(100)
        knowledge_card.layout().addWidget(self.knowledge_query_edit)

        knowledge_buttons = QHBoxLayout()
        self.search_knowledge_button = QPushButton("检索知识")
        self.search_knowledge_button.clicked.connect(self.search_knowledge)
        knowledge_buttons.addWidget(self.search_knowledge_button)

        self.rebuild_knowledge_button = QPushButton("重建索引")
        self.rebuild_knowledge_button.clicked.connect(self.rebuild_knowledge)
        knowledge_buttons.addWidget(self.rebuild_knowledge_button)

        self.knowledge_stats_button = QPushButton("索引状态")
        self.knowledge_stats_button.clicked.connect(self.load_knowledge_stats)
        knowledge_buttons.addWidget(self.knowledge_stats_button)

        knowledge_card.layout().addLayout(knowledge_buttons)
        tools_layout.addWidget(knowledge_card)

        memory_card = self._build_section_card("记忆调试")
        self.memory_query_edit = QTextEdit()
        self.memory_query_edit.setPlaceholderText("输入关键词，搜索当前用户的长期记忆……")
        self.memory_query_edit.setMaximumHeight(100)
        memory_card.layout().addWidget(self.memory_query_edit)

        memory_buttons = QHBoxLayout()
        self.search_memory_button = QPushButton("搜索记忆")
        self.search_memory_button.clicked.connect(self.search_memory)
        memory_buttons.addWidget(self.search_memory_button)

        self.memory_stats_button = QPushButton("记忆统计")
        self.memory_stats_button.clicked.connect(self.load_memory_stats)
        memory_buttons.addWidget(self.memory_stats_button)

        memory_card.layout().addLayout(memory_buttons)
        tools_layout.addWidget(memory_card)

        live2d_card = self._build_section_card("Live2D Model")
        self.live2d_panel = Live2DViewPanel(parent=self)
        live2d_card.layout().addWidget(self.live2d_panel)
        tools_layout.addWidget(live2d_card)

        self.live2d_view = self._build_text_panel(tools_layout, "Live2D Payload", 170)
        self.memory_view = self._build_text_panel(tools_layout, "Memory Status", 170)
        self.detail_view = self._build_text_panel(tools_layout, "API Detail", 260)
        self.state_view = self._build_text_panel(tools_layout, "Runtime Snapshot", 260)

        tools_layout.addStretch()
        tools_scroll.setWidget(tools_content)
        layout.addWidget(tools_scroll, 1)

        return right_panel

    def _build_section_card(self, title: str) -> QFrame:
        card = QFrame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 17px; font-weight: 800; color: #2f241f;")
        layout.addWidget(title_label)
        return card

    def _build_text_panel(self, parent_layout: QVBoxLayout, title: str, height: int) -> QTextEdit:
        card = self._build_section_card(title)
        view = QTextEdit()
        view.setReadOnly(True)
        view.setMinimumHeight(height)
        card.layout().addWidget(view)
        parent_layout.addWidget(card)
        return view

    def _set_status(self, text: str) -> None:
        self.status_label.setText(f"状态：{text}")

    def _append_system_message(self, text: str) -> None:
        self._append_bubble("系统", text, "left", "#ece7df")

    def _append_user_message(self, username: str, text: str) -> None:
        self._append_bubble(username, text, "right", "#dcefff")

    def _append_agent_message(self, text: str) -> None:
        self._append_bubble("Yzl", text, "left", "#f8dcc8")

    def _append_bubble(self, speaker: str, text: str, align: str, color: str) -> None:
        wrapper = QWidget()
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        bubble = ChatBubble(speaker=speaker, text=text, align=align, bubble_color=color)

        if align == "right":
            wrapper_layout.addStretch()
            wrapper_layout.addWidget(bubble)
        else:
            wrapper_layout.addWidget(bubble)
            wrapper_layout.addStretch()

        stretch_item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
        self.chat_layout.addWidget(wrapper)
        if stretch_item is not None:
            self.chat_layout.addItem(stretch_item)

        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

    def _set_busy(self, busy: bool) -> None:
        buttons = [
            self.send_button,
            self.refresh_button,
            self.pause_button,
            self.resume_button,
            self.interrupt_button,
            self.reset_context_button,
            self.clear_memory_button,
            self.search_knowledge_button,
            self.rebuild_knowledge_button,
            self.knowledge_stats_button,
            self.search_memory_button,
            self.memory_stats_button,
            self.startup_check_button,
            self.select_image_button,
        ]
        for button in buttons:
            button.setDisabled(busy)

        self.clear_image_button.setDisabled(busy or not bool(self.selected_image_path))
        self.input_edit.setDisabled(busy)

        if self.recorder.is_recording:
            self.start_record_button.setDisabled(True)
            self.stop_record_button.setDisabled(False)
        else:
            self.start_record_button.setDisabled(busy)
            self.stop_record_button.setDisabled(True)

    def select_image_file(self) -> None:
        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.webp);;所有文件 (*)",
        )
        if not image_path:
            return

        self.selected_image_path = image_path
        self._update_selected_image_label()
        self._set_status(f"已选择图片：{Path(image_path).name}")

    def clear_selected_image(self) -> None:
        self.selected_image_path = ""
        self._update_selected_image_label()
        self._set_status("已清除待发送图片")

    def _update_selected_image_label(self) -> None:
        if not self.selected_image_path:
            self.image_label.setText("未选择图片")
            self.clear_image_button.setDisabled(True)
            return

        path = Path(self.selected_image_path)
        self.image_label.setText(f"待发送图片：{path.name}")
        self.clear_image_button.setDisabled(False)

    def _start_worker(self, task_name: str, fn) -> None:
        if self.current_thread is not None and self.current_thread.isRunning():
            QMessageBox.warning(self, "提示", "当前已有任务在执行，请稍后。")
            return

        self.current_task_name = task_name
        thread = QThread(self)
        worker = Worker(fn)

        self.current_thread = thread
        self.current_worker = worker

        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_worker_success)
        worker.error.connect(self._worker_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(self._thread_finished)
        thread.start()

    @Slot(object)
    def _handle_worker_success(self, result: object) -> None:
        task_name = self.current_task_name

        if task_name == "chat":
            self._on_chat_finished(dict(result))
        elif task_name == "voice":
            self._on_voice_finished(dict(result))
        elif task_name == "refresh":
            self._on_json_result("状态已刷新。", dict(result), self.state_view)
        elif task_name == "startup_check":
            self._on_json_result("启动自检完成。", dict(result), self.state_view)
        elif task_name == "pause":
            self._on_json_result("已暂停对话。", dict(result), self.state_view)
        elif task_name == "resume":
            self._on_json_result("已恢复对话。", dict(result), self.state_view)
        elif task_name == "interrupt":
            self._on_json_result("已发送打断指令。", dict(result), self.state_view)
        elif task_name == "reset_context":
            self._on_json_result("上下文已重置。", dict(result), self.state_view)
        elif task_name == "clear_memory":
            self._on_json_result("用户记忆已清空。", dict(result), self.memory_view)
        elif task_name == "search_knowledge":
            self._on_json_result("知识检索完成。", dict(result), self.detail_view)
        elif task_name == "rebuild_knowledge":
            self._on_json_result("知识索引重建任务已提交。", dict(result), self.detail_view)
        elif task_name == "knowledge_stats":
            self._on_json_result("知识库状态已加载。", dict(result), self.detail_view)
        elif task_name == "search_memory":
            self._on_json_result("记忆搜索完成。", dict(result), self.memory_view)
        elif task_name == "memory_stats":
            self._on_json_result("记忆统计已加载。", dict(result), self.memory_view)

        self.current_task_name = ""
        self._set_busy(False)
        self._set_status("就绪")

    @Slot(str)
    def _worker_error(self, error_text: str) -> None:
        if self.current_worker is not None:
            self.current_worker.deleteLater()
            self.current_worker = None

        self.current_task_name = ""
        self._set_busy(False)
        self._set_status("发生错误")
        QMessageBox.critical(self, "错误", error_text)

    @Slot()
    def _thread_finished(self) -> None:
        if self.current_worker is not None:
            self.current_worker.deleteLater()
            self.current_worker = None
        if self.current_thread is not None:
            self.current_thread.deleteLater()
            self.current_thread = None

    def send_text_message(self) -> None:
        text = self.input_edit.toPlainText().strip()
        image_path = self.selected_image_path
        if not text and not image_path:
            return

        request_text = text or "请你看看这张图，然后和我聊聊。"
        display_text = request_text
        if image_path:
            display_text = f"{request_text}\n[图片] {Path(image_path).name}"

        self._append_user_message(self.username, display_text)
        self.input_edit.clear()
        if image_path:
            self.selected_image_path = ""
            self._update_selected_image_label()

        self._set_busy(True)
        self._set_status("正在请求回复...")

        self._start_worker(
            "chat",
            lambda: self.api_client.send_multimodal_chat(
                user_id=self.user_id,
                username=self.username,
                text=request_text,
                image_path=image_path or None,
            ),
        )

    def start_voice_recording(self) -> None:
        try:
            self.recorder.start_recording()
        except Exception as exc:
            QMessageBox.critical(self, "录音错误", str(exc))
            return

        self.start_record_button.setDisabled(True)
        self.stop_record_button.setDisabled(False)
        self._append_system_message("开始录音，请说话。")
        self._set_status("录音中...")

    def stop_voice_recording(self) -> None:
        try:
            audio_path = self.recorder.stop_recording()
        except Exception as exc:
            self.start_record_button.setDisabled(False)
            self.stop_record_button.setDisabled(True)
            QMessageBox.critical(self, "录音错误", str(exc))
            return

        self._set_busy(True)
        self._set_status("正在识别语音并生成回复...")
        self._start_worker("voice", lambda: self._run_voice_pipeline(audio_path))

    def _run_voice_pipeline(self, audio_path: str) -> dict:
        asr_result = self.api_client.transcribe_audio(audio_path)
        transcript = str(asr_result.get("transcript", "")).strip()
        if not transcript:
            raise RuntimeError("ASR 没有返回文本。")

        chat_result = self.api_client.send_chat(
            user_id=self.user_id,
            username=self.username,
            text=transcript,
        )

        return {
            "audio_path": audio_path,
            "transcript": transcript,
            "asr_result": asr_result,
            "chat_result": chat_result,
        }

    def run_startup_check(self) -> None:
        self._set_status("正在执行启动自检...")
        self._set_busy(True)
        self._start_worker("startup_check", lambda: self.api_client.run_startup_check(self.user_id))

    def refresh_state(self) -> None:
        self._set_status("正在刷新状态...")
        self._set_busy(True)
        self._start_worker("refresh", lambda: self.api_client.get_runtime_snapshot(self.user_id))

    def pause_dialogue(self) -> None:
        self._set_busy(True)
        self._start_worker("pause", self.api_client.pause_dialogue)

    def resume_dialogue(self) -> None:
        self._set_busy(True)
        self._start_worker("resume", self.api_client.resume_dialogue)

    def interrupt_speaking(self) -> None:
        self._set_busy(True)
        self._start_worker("interrupt", lambda: self.api_client.interrupt_voice(reason="desktop_qt_interrupt"))

    def reset_context(self) -> None:
        self._set_busy(True)
        self._start_worker("reset_context", self.api_client.reset_context)

    def clear_memory(self) -> None:
        confirm = QMessageBox.question(self, "确认清空记忆", f"确定要清空用户 {self.user_id} 的记忆吗？")
        if confirm != QMessageBox.Yes:
            return

        self._set_busy(True)
        self._start_worker("clear_memory", lambda: self.api_client.clear_user_memory(self.user_id))

    def clear_chat(self) -> None:
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.detail_view.clear()
        self.state_view.clear()
        self.memory_view.clear()
        self.live2d_view.clear()
        self._append_system_message("聊天窗口已清空。")

    def search_knowledge(self) -> None:
        query = self.knowledge_query_edit.toPlainText().strip()
        if not query:
            QMessageBox.information(self, "提示", "请先输入知识检索问题。")
            return

        self._set_busy(True)
        self._start_worker("search_knowledge", lambda: self.api_client.search_knowledge(query=query, top_k=4))

    def rebuild_knowledge(self) -> None:
        self._set_busy(True)
        self._start_worker("rebuild_knowledge", lambda: self.api_client.rebuild_knowledge(force_rebuild=True))

    def load_knowledge_stats(self) -> None:
        self._set_busy(True)
        self._start_worker("knowledge_stats", self.api_client.get_knowledge_stats)

    def search_memory(self) -> None:
        query = self.memory_query_edit.toPlainText().strip()
        if not query:
            QMessageBox.information(self, "提示", "请先输入记忆搜索关键词。")
            return

        self._set_busy(True)
        self._start_worker(
            "search_memory",
            lambda: self.api_client.search_user_memory(user_id=self.user_id, query=query, limit=10),
        )

    def load_memory_stats(self) -> None:
        self._set_busy(True)
        self._start_worker("memory_stats", lambda: self.api_client.get_memory_stats(self.user_id))

    def _on_chat_finished(self, data: dict) -> None:
        reply = str(data.get("reply", "")).strip()
        self._append_agent_message(reply or "后端没有返回回复。")
        self._append_memory_status(data)
        self._update_live2d_view(data)
        self._update_detail_view(data)

    def _on_voice_finished(self, data: dict) -> None:
        transcript = data["transcript"]
        chat_result = data["chat_result"]

        self._append_user_message(self.username, f"[语音识别] {transcript}")
        reply = str(chat_result.get("reply", "")).strip()
        self._append_agent_message(reply or "后端没有返回回复。")
        self._append_memory_status(chat_result)
        self._update_live2d_view(chat_result)
        self._update_detail_view(data)

        self.start_record_button.setDisabled(False)
        self.stop_record_button.setDisabled(True)

    def _on_json_result(self, message: str, data: dict, target: QTextEdit) -> None:
        target.setPlainText(self.api_client.pretty_json(data))
        self._append_system_message(message)

    def _update_detail_view(self, data: dict) -> None:
        self.detail_view.setPlainText(self.api_client.pretty_json(data))

    def _update_live2d_view(self, data: dict) -> None:
        live2d = data.get("live2d", {})
        if isinstance(live2d, dict):
            self.live2d_view.setPlainText(self.api_client.pretty_json(live2d))
            if hasattr(self, "live2d_panel") and live2d:
                result = self.live2d_panel.apply_payload(live2d)
                if result.get("last_error"):
                    self._append_system_message(f"Live2D：{result.get('last_error')}")
        else:
            self.live2d_view.setPlainText(str(live2d))

    def _append_memory_status(self, data: dict) -> None:
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            return

        raw_should_store = metadata.get("memory_write_should_store")
        if raw_should_store is None:
            return

        should_store = str(raw_should_store).lower() == "true"
        store_status = str(metadata.get("memory_store_status", "")).strip()
        category = str(metadata.get("memory_write_category", "") or metadata.get("category", "")).strip()
        importance = str(metadata.get("memory_write_importance", "") or metadata.get("importance", "")).strip()
        reason = str(metadata.get("memory_write_reason", "") or metadata.get("policy_reason", "")).strip()
        hint = str(metadata.get("memory_hint", "")).strip()

        lines = []
        if should_store and store_status == "stored":
            lines.append("长期记忆：已写入")
        elif should_store:
            lines.append("长期记忆：已判断应写入，但未看到 stored 状态")
        else:
            lines.append("长期记忆：未写入")

        if category:
            lines.append(f"类型：{category}")
        if importance:
            lines.append(f"重要性：{importance}")
        if reason:
            lines.append(f"原因：{reason}")
        if hint:
            lines.append(f"内容：{hint}")

        text = "\n".join(lines)
        self.memory_view.setPlainText(text)
        self._append_system_message(text)
