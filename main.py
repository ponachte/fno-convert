from PyQt6.QtWidgets import QApplication
from src.semantexe.visualize import PY2RDFWindow

import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PY2RDFWindow()
    window.show()
    sys.exit(app.exec())