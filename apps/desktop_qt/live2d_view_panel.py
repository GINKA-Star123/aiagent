from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from aiagent.live2d.registry import Live2DRegistry
from integrations.live2d.qt_live2d_widget import QtLive2DWidget


class Live2DViewPanel(QWidget):
    def __init__(
        self,
        character_root: str = "data/live2d/characters",
        background_root: str = "data/live2d/backgrounds",
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.registry = Live2DRegistry(
            character_root=character_root,
            background_root=background_root,
        )

        self.live2d_widget = QtLive2DWidget(self)
        self.live2d_widget.setMinimumHeight(300)

        self.status_view = QPlainTextEdit(self)
        self.status_view.setReadOnly(True)
        self.status_view.setMaximumHeight(110)

        self.load_button = QPushButton("加载模型", self)
        self.load_button.clicked.connect(self.load_default_character)

        self.happy_button = QPushButton("开心", self)
        self.happy_button.clicked.connect(lambda: self.set_expression("happy_smile"))

        self.gentle_button = QPushButton("温柔", self)
        self.gentle_button.clicked.connect(lambda: self.set_expression("gentle"))

        self.wave_button = QPushButton("挥手", self)
        self.wave_button.clicked.connect(lambda: self.start_motion("TapBody", 0, 2))

        self.status_label = QLabel("Live2D 未加载", self)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.status_label.setStyleSheet("font-size: 13px; color: #705e50;")

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.load_button)
        top_bar.addWidget(self.happy_button)
        top_bar.addWidget(self.gentle_button)
        top_bar.addWidget(self.wave_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addLayout(top_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.live2d_widget, 1)
        layout.addWidget(self.status_view)

        self.setLayout(layout)

    def load_default_character(self) -> dict:
        return self.load_character("yzl")

    def load_character(self, character_id: str) -> dict:
        profile = self.registry.get_character(character_id)
        result = self.live2d_widget.load_model(profile.model3_json)
        self._update_status(result)
        return result

    def apply_payload(self, payload: dict) -> dict:
        if not self.live2d_widget.loaded:
            self.load_default_character()

        result = self.live2d_widget.apply_payload(payload)
        self._update_status(result)
        return result

    def set_expression(self, expression_id: str) -> dict:
        result = self.live2d_widget.set_expression(expression_id)
        self._update_status(result)
        return result

    def start_motion(self, group: str, index: int = 0, priority: int = 2) -> dict:
        result = self.live2d_widget.start_motion(group, index, priority)
        self._update_status(result)
        return result

    def _update_status(self, result: dict) -> None:
        loaded = bool(result.get("loaded", False))
        error = str(result.get("last_error", "") or "").strip()

        if loaded:
            self.status_label.setText("Live2D 已加载")
        elif error:
            self.status_label.setText(f"Live2D 加载失败：{error}")
        else:
            self.status_label.setText("Live2D 未加载")

        self.status_view.setPlainText(str(result))
