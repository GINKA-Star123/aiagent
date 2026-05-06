from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from apps.desktop_qt.live2d_view_panel import Live2DViewPanel


class Live2DDebugWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Live2D Debug")
        self.resize(900, 700)

        self.panel = Live2DViewPanel(self)

        load_button = QPushButton("加载乐正绫")
        happy_button = QPushButton("开心")
        calm_button = QPushButton("温柔")
        wave_button = QPushButton("挥手")

        load_button.clicked.connect(self.panel.load_default_character)
        happy_button.clicked.connect(lambda: self.panel.set_expression("happy_smile"))
        calm_button.clicked.connect(lambda: self.panel.set_expression("gentle"))
        wave_button.clicked.connect(lambda: self.panel.start_motion("TapBody", 0, 2))

        buttons = QHBoxLayout()
        buttons.addWidget(load_button)
        buttons.addWidget(happy_button)
        buttons.addWidget(calm_button)
        buttons.addWidget(wave_button)

        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(self.panel, 1)

        self.setLayout(layout)


def main() -> None:
    app = QApplication(sys.argv)
    window = Live2DDebugWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
