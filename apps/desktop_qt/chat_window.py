import traceback

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
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


class Worker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, fn) -> None:
        super().__init__()
        self.fn = fn

    @Slot()
    def run(self) -> None:
        try:
            result = self.fn()
            self.finished.emit(result)
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
        text_label.setStyleSheet("font-size: 14px; line-height: 1.5; color: #1f1f1f;")
        layout.addWidget(text_label)

        self.setStyleSheet(
            f"""
            QFrame {{
                background: {bubble_color};
                border: 1px solid rgba(60, 60, 60, 0.08);
                border-radius: 16px;
            }}
            """
        )

        self.setMaximumWidth(420 if align == "right" else 560)


class ChatWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("AIAgent Desktop Panel")
        self.resize(1480, 920)

        self.identity_store = DesktopIdentityStore()
        self.user_id, self.username = self._load_or_create_identity()
        self.api_base_url = "http://127.0.0.1:8000"

        self.api_client = APIClient(self.api_base_url)
        self.recorder = AudioRecorder()

        self.current_thread: QThread | None = None
        self.current_worker: Worker | None = None
        self.current_task_name: str = ""
        self.current_task_payload: dict = {}

        self._build_ui()
        self._append_system_message(
            f"桌面端已启动，当前身份为 {self.username}。现在可以聊天、语音录音、检索知识、搜索记忆。"
        )
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
        outer_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([980, 620])

        outer_layout.addWidget(splitter)

        root.setStyleSheet(
            """
            QWidget {
                background: #efe6d8;
                font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
            }
            QFrame#leftPanel, QFrame#rightPanel {
                background: rgba(255, 252, 247, 0.92);
                border: 1px solid #d8ccbf;
                border-radius: 22px;
            }
            """
        )

    def _build_left_panel(self) -> QWidget:
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")

        layout = QVBoxLayout(left_panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title_label = QLabel("Yzl 对话窗口")
        title_label.setStyleSheet("font-size: 28px; font-weight: 800; color: #2f241f;")
        layout.addWidget(title_label)

        identity_card = self._build_section_card("身份信息")
        identity_layout = identity_card.layout()

        self.identity_label = QLabel(
            f"当前用户：{self.username}\n用户ID：{self.user_id}\n服务端：{self.api_base_url}"
        )
        self.identity_label.setStyleSheet("font-size: 13px; color: #6f6258; line-height: 1.6;")
        identity_layout.addWidget(self.identity_label)

        identity_row = QHBoxLayout()
        identity_row.setSpacing(10)

        self.rename_identity_button = QPushButton("修改昵称")
        self.rename_identity_button.clicked.connect(self.rename_identity)
        self.rename_identity_button.setStyleSheet(self._button_style("#475569"))
        identity_row.addWidget(self.rename_identity_button)

        self.rebuild_identity_button = QPushButton("重建身份")
        self.rebuild_identity_button.clicked.connect(self.rebuild_identity)
        self.rebuild_identity_button.setStyleSheet(self._button_style("#b45309"))
        identity_row.addWidget(self.rebuild_identity_button)

        identity_layout.addLayout(identity_row)
        layout.addWidget(identity_card, 0)

        chat_card = self._build_section_card("聊天记录")
        chat_layout_host = chat_card.layout()

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
        chat_layout_host.addWidget(self.chat_scroll)
        layout.addWidget(chat_card, 1)

        compose_card = self._build_section_card("输入区")
        compose_layout = compose_card.layout()

        self.status_label = QLabel("状态：就绪")
        self.status_label.setStyleSheet("font-size: 13px; color: #705e50;")
        compose_layout.addWidget(self.status_label)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("输入你想说的话……")
        self.input_edit.setMinimumHeight(130)
        self.input_edit.setMaximumHeight(220)
        self.input_edit.setStyleSheet(
            """
            QTextEdit {
                background: white;
                border: 1px solid #d3c8bc;
                border-radius: 14px;
                padding: 10px 12px;
                font-size: 15px;
            }
            """
        )
        compose_layout.addWidget(self.input_edit)

        input_button_row = QHBoxLayout()
        input_button_row.setSpacing(10)

        self.send_button = QPushButton("发送消息")
        self.send_button.clicked.connect(self.send_text_message)
        self.send_button.setStyleSheet(self._button_style("#cf5f32"))
        input_button_row.addWidget(self.send_button)

        self.start_record_button = QPushButton("开始录音")
        self.start_record_button.clicked.connect(self.start_voice_recording)
        self.start_record_button.setStyleSheet(self._button_style("#2f7d67"))
        input_button_row.addWidget(self.start_record_button)

        self.stop_record_button = QPushButton("结束录音")
        self.stop_record_button.clicked.connect(self.stop_voice_recording)
        self.stop_record_button.setStyleSheet(self._button_style("#2563eb"))
        self.stop_record_button.setDisabled(True)
        input_button_row.addWidget(self.stop_record_button)

        compose_layout.addLayout(input_button_row)
        layout.addWidget(compose_card, 0)
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
        tools_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        tools_content = QWidget()
        tools_layout = QVBoxLayout(tools_content)
        tools_layout.setContentsMargins(0, 0, 4, 0)
        tools_layout.setSpacing(12)

        live2d_card = self._build_section_card("角色区域")
        live2d_layout_host = live2d_card.layout()

        self.live2d_placeholder = QFrame()
        self.live2d_placeholder.setMinimumHeight(180)
        self.live2d_placeholder.setMaximumHeight(220)
        self.live2d_placeholder.setStyleSheet(
            """
            QFrame {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f7efe3,
                    stop:1 #ead9c5
                );
                border: 1px solid #d3c4b0;
                border-radius: 20px;
            }
            """
        )

        live2d_layout = QVBoxLayout(self.live2d_placeholder)
        live2d_layout.setContentsMargins(20, 20, 20, 20)

        live2d_name = QLabel("Yzl Live2D Preview")
        live2d_name.setAlignment(Qt.AlignCenter)
        live2d_name.setStyleSheet("font-size: 24px; font-weight: 800; color: #5c4634;")
        live2d_layout.addStretch()
        live2d_layout.addWidget(live2d_name)

        live2d_desc = QLabel("这里先保留角色显示位。\n第 22 周重点先把桌面端产品化和调试能力补完整。")
        live2d_desc.setAlignment(Qt.AlignCenter)
        live2d_desc.setStyleSheet("font-size: 14px; color: #7c6859;")
        live2d_layout.addWidget(live2d_desc)
        live2d_layout.addStretch()

        live2d_layout_host.addWidget(self.live2d_placeholder)
        tools_layout.addWidget(live2d_card)

        control_card = self._build_section_card("快捷控制")
        control_card_layout = control_card.layout()

        control_grid = QGridLayout()
        control_grid.setHorizontalSpacing(10)
        control_grid.setVerticalSpacing(10)

        self.startup_check_button = QPushButton("启动自检")
        self.startup_check_button.clicked.connect(self.run_startup_check)
        self.startup_check_button.setStyleSheet(self._button_style("#0f766e"))
        control_grid.addWidget(self.startup_check_button, 0, 0)

        self.refresh_button = QPushButton("刷新状态")
        self.refresh_button.clicked.connect(self.refresh_state)
        self.refresh_button.setStyleSheet(self._button_style("#3b82f6"))
        control_grid.addWidget(self.refresh_button, 0, 1)

        self.pause_button = QPushButton("暂停对话")
        self.pause_button.clicked.connect(self.pause_dialogue)
        self.pause_button.setStyleSheet(self._button_style("#d97706"))
        control_grid.addWidget(self.pause_button, 1, 0)

        self.resume_button = QPushButton("恢复对话")
        self.resume_button.clicked.connect(self.resume_dialogue)
        self.resume_button.setStyleSheet(self._button_style("#059669"))
        control_grid.addWidget(self.resume_button, 1, 1)

        self.interrupt_button = QPushButton("打断播放")
        self.interrupt_button.clicked.connect(self.interrupt_speaking)
        self.interrupt_button.setStyleSheet(self._button_style("#dc2626"))
        control_grid.addWidget(self.interrupt_button, 2, 0)

        self.reset_context_button = QPushButton("重置上下文")
        self.reset_context_button.clicked.connect(self.reset_context)
        self.reset_context_button.setStyleSheet(self._button_style("#7c3aed"))
        control_grid.addWidget(self.reset_context_button, 2, 1)

        self.clear_memory_button = QPushButton("清空记忆")
        self.clear_memory_button.clicked.connect(self.clear_memory)
        self.clear_memory_button.setStyleSheet(self._button_style("#475569"))
        control_grid.addWidget(self.clear_memory_button, 3, 0)

        self.clear_chat_button = QPushButton("清空聊天窗口")
        self.clear_chat_button.clicked.connect(self.clear_chat)
        self.clear_chat_button.setStyleSheet(self._button_style("#8b5cf6"))
        control_grid.addWidget(self.clear_chat_button, 3, 1)

        control_card_layout.addLayout(control_grid)
        tools_layout.addWidget(control_card)

        knowledge_card = self._build_section_card("知识库调试")
        knowledge_layout = knowledge_card.layout()

        self.knowledge_query_edit = QTextEdit()
        self.knowledge_query_edit.setPlaceholderText("输入一个问题，测试知识库命中效果……")
        self.knowledge_query_edit.setMinimumHeight(76)
        self.knowledge_query_edit.setMaximumHeight(110)
        self.knowledge_query_edit.setStyleSheet(self._panel_text_style())
        knowledge_layout.addWidget(self.knowledge_query_edit)

        knowledge_button_row = QHBoxLayout()
        knowledge_button_row.setSpacing(10)

        self.search_knowledge_button = QPushButton("检索知识")
        self.search_knowledge_button.clicked.connect(self.search_knowledge)
        self.search_knowledge_button.setStyleSheet(self._button_style("#0f766e"))
        knowledge_button_row.addWidget(self.search_knowledge_button)

        self.rebuild_knowledge_button = QPushButton("重建索引")
        self.rebuild_knowledge_button.clicked.connect(self.rebuild_knowledge)
        self.rebuild_knowledge_button.setStyleSheet(self._button_style("#9333ea"))
        knowledge_button_row.addWidget(self.rebuild_knowledge_button)

        knowledge_layout.addLayout(knowledge_button_row)
        tools_layout.addWidget(knowledge_card)

        memory_card = self._build_section_card("记忆检索")
        memory_layout = memory_card.layout()

        self.memory_query_edit = QTextEdit()
        self.memory_query_edit.setPlaceholderText("输入关键词，搜索当前用户的记忆……")
        self.memory_query_edit.setMinimumHeight(76)
        self.memory_query_edit.setMaximumHeight(110)
        self.memory_query_edit.setStyleSheet(self._panel_text_style())
        memory_layout.addWidget(self.memory_query_edit)

        memory_button_row = QHBoxLayout()
        memory_button_row.setSpacing(10)

        self.search_memory_button = QPushButton("搜索记忆")
        self.search_memory_button.clicked.connect(self.search_memory)
        self.search_memory_button.setStyleSheet(self._button_style("#2563eb"))
        memory_button_row.addWidget(self.search_memory_button)

        self.memory_stats_button = QPushButton("记忆统计")
        self.memory_stats_button.clicked.connect(self.load_memory_stats)
        self.memory_stats_button.setStyleSheet(self._button_style("#be185d"))
        memory_button_row.addWidget(self.memory_stats_button)

        memory_layout.addLayout(memory_button_row)
        tools_layout.addWidget(memory_card)

        detail_card = self._build_section_card("详细结果")
        detail_layout = detail_card.layout()

        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setMinimumHeight(180)
        self.detail_view.setStyleSheet(self._panel_text_style())
        detail_layout.addWidget(self.detail_view)
        tools_layout.addWidget(detail_card)

        state_card = self._build_section_card("状态面板")
        state_layout = state_card.layout()

        self.state_view = QTextEdit()
        self.state_view.setReadOnly(True)
        self.state_view.setMinimumHeight(220)
        self.state_view.setStyleSheet(self._panel_text_style())
        state_layout.addWidget(self.state_view)
        tools_layout.addWidget(state_card)

        tools_layout.addStretch()
        tools_scroll.setWidget(tools_content)
        layout.addWidget(tools_scroll, 1)

        return right_panel

    def _build_section_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background: rgba(255, 250, 243, 0.95);
                border: 1px solid #ddcfbf;
                border-radius: 18px;
            }
            """
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 18px; font-weight: 800; color: #2f241f;")
        layout.addWidget(title_label)
        return card

    def _panel_text_style(self) -> str:
        return """
        QTextEdit {
            background: #fffdfa;
            border: 1px solid #ddd4c8;
            border-radius: 14px;
            padding: 10px;
            font-size: 13px;
            color: #2c241e;
        }
        """

    def _button_style(self, color: str) -> str:
        return f"""
        QPushButton {{
            min-height: 40px;
            padding: 0 18px;
            border: none;
            border-radius: 14px;
            background: {color};
            color: white;
            font-size: 14px;
            font-weight: 700;
        }}
        QPushButton:disabled {{
            background: #9ea6ad;
            color: #eef0f2;
        }}
        """

    def _update_identity_label(self) -> None:
        self.identity_label.setText(
            f"当前用户：{self.username}\n用户ID：{self.user_id}\n服务端：{self.api_base_url}"
        )

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
        for button in [
            self.send_button,
            self.refresh_button,
            self.pause_button,
            self.resume_button,
            self.interrupt_button,
            self.reset_context_button,
            self.clear_memory_button,
            self.search_knowledge_button,
            self.rebuild_knowledge_button,
            self.search_memory_button,
            self.memory_stats_button,
            self.startup_check_button,
            self.rename_identity_button,
            self.rebuild_identity_button,
        ]:
            button.setDisabled(busy)

        self.input_edit.setDisabled(busy)

        if self.recorder.is_recording:
            self.start_record_button.setDisabled(True)
            self.stop_record_button.setDisabled(False)
        else:
            self.start_record_button.setDisabled(busy)
            self.stop_record_button.setDisabled(True)

    def _start_worker(self, task_name: str, fn, payload: dict | None = None) -> None:
        if self.current_thread is not None and self.current_thread.isRunning():
            QMessageBox.warning(self, "提示", "当前已有任务在执行，请稍后。")
            return

        self.current_task_name = task_name
        self.current_task_payload = payload or {}

        thread = QThread(self)
        worker = Worker(fn)

        self.current_thread = thread
        self.current_worker = worker

        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        worker.finished.connect(self._handle_worker_success)
        worker.finished.connect(self._worker_finished)
        worker.error.connect(self._worker_error)

        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(self._thread_finished)

        thread.start()

    @Slot(object)
    def _handle_worker_success(self, result: object) -> None:
        task_name = self.current_task_name

        if task_name == "chat":
            self._on_chat_finished(result)
        elif task_name == "voice":
            self._on_voice_finished(result)
        elif task_name == "refresh":
            self._on_refresh_finished(result)
        elif task_name == "startup_check":
            self._on_startup_check_finished(result)
        elif task_name == "pause":
            self._on_action_finished("已暂停对话。", result)
        elif task_name == "resume":
            self._on_action_finished("已恢复对话。", result)
        elif task_name == "interrupt":
            self._on_action_finished("已发送打断指令。", result)
        elif task_name == "reset_context":
            self._on_action_finished("上下文已重置。", result)
        elif task_name == "clear_memory":
            self._on_action_finished("用户记忆已清空。", result)
        elif task_name == "search_knowledge":
            self._on_knowledge_search_finished(result)
        elif task_name == "rebuild_knowledge":
            self._on_knowledge_rebuild_finished(result)
        elif task_name == "search_memory":
            self._on_memory_search_finished(result)
        elif task_name == "memory_stats":
            self._on_memory_stats_finished(result)

        self.current_task_name = ""
        self.current_task_payload = {}

    @Slot(object)
    def _worker_finished(self, _result: object) -> None:
        if self.current_worker is not None:
            self.current_worker.deleteLater()
            self.current_worker = None

    @Slot(str)
    def _worker_error(self, error_text: str) -> None:
        if self.current_worker is not None:
            self.current_worker.deleteLater()
            self.current_worker = None

        self.current_task_name = ""
        self.current_task_payload = {}

        self._set_busy(False)
        self.start_record_button.setDisabled(self.recorder.is_recording)
        self.stop_record_button.setDisabled(not self.recorder.is_recording)
        self._set_status("发生错误")
        QMessageBox.critical(self, "错误", error_text)

    @Slot()
    def _thread_finished(self) -> None:
        if self.current_thread is not None:
            self.current_thread.deleteLater()
            self.current_thread = None

    def rename_identity(self) -> None:
        new_name, ok = QInputDialog.getText(self, "修改昵称", "请输入新的昵称：", text=self.username)
        if not ok or not new_name.strip():
            return

        identity = self.identity_store.update_username(new_name.strip())
        self.username = identity.username
        self._update_identity_label()
        self._append_system_message(f"昵称已更新为 {self.username}。")

    def rebuild_identity(self) -> None:
        confirm = QMessageBox.question(
            self,
            "重建身份",
            "这会生成一个新的 user_id，旧记忆不会自动继承。确定继续吗？",
        )
        if confirm != QMessageBox.Yes:
            return

        new_name, ok = QInputDialog.getText(self, "新身份昵称", "请输入新身份的昵称：", text=self.username)
        if not ok or not new_name.strip():
            return

        identity = self.identity_store.rebuild_identity(new_name.strip())
        self.user_id = identity.user_id
        self.username = identity.username
        self._update_identity_label()
        self._append_system_message(f"已重建身份。新的用户ID是 {self.user_id}。")
        self._set_status("身份已重建")

    def send_text_message(self) -> None:
        text = self.input_edit.toPlainText().strip()
        if not text:
            return

        self._append_user_message(self.username, text)
        self.input_edit.clear()
        self._set_busy(True)
        self._set_status("正在请求回复...")

        self._start_worker(
            "chat",
            lambda: self.api_client.send_chat(
                user_id=self.user_id,
                username=self.username,
                text=text,
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
        self._append_system_message("开始录音，请说话。说完后点击“结束录音”。")
        self._set_status("录音中...")

    def stop_voice_recording(self) -> None:
        try:
            audio_path = self.recorder.stop_recording()
        except Exception as exc:
            self.start_record_button.setDisabled(False)
            self.stop_record_button.setDisabled(True)
            QMessageBox.critical(self, "录音错误", str(exc))
            self._set_status("录音失败")
            return

        self.start_record_button.setDisabled(True)
        self.stop_record_button.setDisabled(True)
        self._set_busy(True)
        self._set_status("正在识别语音并生成回复...")

        self._start_worker("voice", lambda: self._run_voice_pipeline(audio_path))

    def _run_voice_pipeline(self, audio_path: str) -> dict:
        asr_result = self.api_client.transcribe_audio(audio_path)
        transcript = str(asr_result.get("transcript", "")).strip()

        if not transcript:
            raise RuntimeError("ASR 没有返回文本，请检查麦克风或语音模型。")

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
        self._start_worker(
            "startup_check",
            lambda: self.api_client.run_startup_check(self.user_id),
        )

    def refresh_state(self) -> None:
        self._set_status("正在刷新状态...")
        self._set_busy(True)
        self._start_worker(
            "refresh",
            lambda: self.api_client.get_runtime_snapshot(self.user_id),
        )

    def pause_dialogue(self) -> None:
        self._set_status("正在暂停对话...")
        self._set_busy(True)
        self._start_worker("pause", self.api_client.pause_dialogue)

    def resume_dialogue(self) -> None:
        self._set_status("正在恢复对话...")
        self._set_busy(True)
        self._start_worker("resume", self.api_client.resume_dialogue)

    def interrupt_speaking(self) -> None:
        self._set_status("正在打断播放...")
        self._set_busy(True)
        self._start_worker(
            "interrupt",
            lambda: self.api_client.interrupt_voice(reason="desktop_qt_interrupt"),
        )

    def reset_context(self) -> None:
        self._set_status("正在重置上下文...")
        self._set_busy(True)
        self._start_worker("reset_context", self.api_client.reset_context)

    def clear_memory(self) -> None:
        confirm = QMessageBox.question(
            self,
            "确认清空记忆",
            f"确定要清空用户 {self.user_id} 的记忆吗？",
        )
        if confirm != QMessageBox.Yes:
            return

        self._set_status("正在清空记忆...")
        self._set_busy(True)
        self._start_worker(
            "clear_memory",
            lambda: self.api_client.clear_user_memory(self.user_id),
        )

    def clear_chat(self) -> None:
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.detail_view.clear()
        self.state_view.clear()
        self._append_system_message("聊天窗口已清空。")
        self._set_status("就绪")

    def search_knowledge(self) -> None:
        query = self.knowledge_query_edit.toPlainText().strip()
        if not query:
            QMessageBox.information(self, "提示", "请先输入知识检索问题。")
            return

        self._set_status("正在检索知识...")
        self._set_busy(True)
        self._start_worker(
            "search_knowledge",
            lambda: self.api_client.search_knowledge(query=query, top_k=4),
        )

    def rebuild_knowledge(self) -> None:
        confirm = QMessageBox.question(
            self,
            "确认重建索引",
            "确定要重建知识库索引吗？这可能需要一点时间。",
        )
        if confirm != QMessageBox.Yes:
            return

        self._set_status("正在重建知识索引...")
        self._set_busy(True)
        self._start_worker(
            "rebuild_knowledge",
            lambda: self.api_client.rebuild_knowledge(force_rebuild=True),
        )

    def search_memory(self) -> None:
        query = self.memory_query_edit.toPlainText().strip()
        if not query:
            QMessageBox.information(self, "提示", "请先输入记忆搜索关键词。")
            return

        self._set_status("正在搜索记忆...")
        self._set_busy(True)
        self._start_worker(
            "search_memory",
            lambda: self.api_client.search_user_memory(user_id=self.user_id, query=query, limit=10),
        )

    def load_memory_stats(self) -> None:
        self._set_status("正在加载记忆统计...")
        self._set_busy(True)
        self._start_worker(
            "memory_stats",
            lambda: self.api_client.get_memory_stats(self.user_id),
        )

    def _on_chat_finished(self, result: object) -> None:
        data = dict(result)
        reply = str(data.get("reply", "")).strip()
        self._append_agent_message(reply or "后端没有返回回复。")
        self._update_detail_view(data)
        self._set_busy(False)
        self._set_status("就绪")

    def _on_voice_finished(self, result: object) -> None:
        data = dict(result)
        transcript = data["transcript"]
        chat_result = data["chat_result"]

        self._append_user_message(self.username, f"[语音识别] {transcript}")
        reply = str(chat_result.get("reply", "")).strip()
        self._append_agent_message(reply or "后端没有返回回复。")

        self._update_detail_view(
            {
                "voice_audio_path": data["audio_path"],
                "transcript": transcript,
                "asr_result": data["asr_result"],
                "chat_result": chat_result,
            }
        )

        self._set_busy(False)
        self.start_record_button.setDisabled(False)
        self.stop_record_button.setDisabled(True)
        self._set_status("就绪")

    def _on_startup_check_finished(self, result: object) -> None:
        data = dict(result)
        self.detail_view.setPlainText(self.api_client.pretty_json(data))
        self.detail_view.moveCursor(QTextCursor.Start)
        self.state_view.setPlainText(self.api_client.pretty_json(data))
        self.state_view.moveCursor(QTextCursor.Start)

        if data.get("ok"):
            self._append_system_message("启动自检通过。")
            self._set_status("启动自检完成")
        else:
            self._append_system_message("启动自检完成，但存在异常项。")
            self._set_status("自检发现异常")

        self._set_busy(False)

    def _on_refresh_finished(self, result: object) -> None:
        data = dict(result)
        self.state_view.setPlainText(self.api_client.pretty_json(data))
        self.state_view.moveCursor(QTextCursor.Start)
        self._set_busy(False)
        self._set_status("状态已刷新")

    def _on_action_finished(self, message: str, result: object) -> None:
        data = dict(result)
        self._append_system_message(message)
        self.state_view.setPlainText(self.api_client.pretty_json(data))
        self.state_view.moveCursor(QTextCursor.Start)
        self._set_busy(False)
        self._set_status("操作完成")

    def _on_knowledge_search_finished(self, result: object) -> None:
        data = dict(result)
        self.detail_view.setPlainText(self.api_client.pretty_json(data))
        self.detail_view.moveCursor(QTextCursor.Start)

        summary = {
            "query": data.get("query", ""),
            "top_k": data.get("top_k", 4),
            "hit_count": len(data.get("chunks", [])),
            "chunks": data.get("chunks", []),
            "prompt_context": data.get("prompt_context", ""),
        }

        self.state_view.setPlainText(self.api_client.pretty_json(summary))
        self.state_view.moveCursor(QTextCursor.Start)

        self._append_system_message("知识检索完成，可以查看右侧结果。")
        self._set_busy(False)
        self._set_status("知识检索完成")

    def _on_knowledge_rebuild_finished(self, result: object) -> None:
        data = dict(result)
        self.detail_view.setPlainText(self.api_client.pretty_json(data))
        self.detail_view.moveCursor(QTextCursor.Start)
        self.state_view.setPlainText(self.api_client.pretty_json(data))
        self.state_view.moveCursor(QTextCursor.Start)
        self._append_system_message("知识索引重建完成。")
        self._set_busy(False)
        self._set_status("索引重建完成")

    def _on_memory_search_finished(self, result: object) -> None:
        data = dict(result)
        self.detail_view.setPlainText(self.api_client.pretty_json(data))
        self.detail_view.moveCursor(QTextCursor.Start)
        self.state_view.setPlainText(self.api_client.pretty_json(data))
        self.state_view.moveCursor(QTextCursor.Start)
        self._append_system_message("记忆搜索完成。")
        self._set_busy(False)
        self._set_status("记忆搜索完成")

    def _on_memory_stats_finished(self, result: object) -> None:
        data = dict(result)
        self.detail_view.setPlainText(self.api_client.pretty_json(data))
        self.detail_view.moveCursor(QTextCursor.Start)
        self.state_view.setPlainText(self.api_client.pretty_json(data))
        self.state_view.moveCursor(QTextCursor.Start)
        self._append_system_message("记忆统计已加载。")
        self._set_busy(False)
        self._set_status("记忆统计完成")

    def _update_detail_view(self, data: dict) -> None:
        self.detail_view.setPlainText(self.api_client.pretty_json(data))
        self.detail_view.moveCursor(QTextCursor.Start)
