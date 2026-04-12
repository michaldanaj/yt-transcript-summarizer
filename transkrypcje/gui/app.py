"""Główne okno aplikacji Qt — szkielet do rozbudowy."""

import sys

from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Transkrypcje YouTube")
        self.setMinimumSize(900, 600)
        self.setCentralWidget(QLabel("TODO: GUI"))


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
