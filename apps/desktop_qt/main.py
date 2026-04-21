import sys

from PySide6.QtWidgets import QApplication

from apps.desktop_qt.chat_window import ChatWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
