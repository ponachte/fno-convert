from PyQt6.QtWidgets import QMainWindow, QWidget, QGridLayout, QHBoxLayout, QTabWidget

from .flowctrl import FlowCtrlWidget
from .load import ScrollWidget, FunctionPicker

class PY2RDFWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Flow Visualizer")
        self.setGeometry(100, 100, 600, 400)

        # Tab to describe a flow
        loadTab = QWidget()
        layout1 = QGridLayout()
        loadTab.setLayout(layout1)

        codeViewer = ScrollWidget()
        rdfViewer = ScrollWidget()
        funPicker = FunctionPicker()

        layout1.addWidget(funPicker, 0, 0, 1, 1)
        layout1.addWidget(codeViewer, 0, 1, 1, 4)
        layout1.addWidget(rdfViewer, 0, 5, 1, 4)

        # Tab to view flow
        viewTab = FlowCtrlWidget()

        # Event handling
        funPicker.file_loaded.connect(codeViewer.setText)
        funPicker.function_loaded.connect(codeViewer.setSource)
        funPicker.function_loaded.connect(rdfViewer.setGraph)
        funPicker.function_loaded.connect(viewTab.setFlow)

        # Add Tabs
        tabWidget = QTabWidget()
        tabWidget.addTab(loadTab, "Load")
        tabWidget.addTab(viewTab, "View")
        self.setCentralWidget(tabWidget)