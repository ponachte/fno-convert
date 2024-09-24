from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout, QHBoxLayout, QTabWidget

from .flowview import FlowCtrlWidget
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

        code_viewer = ScrollWidget()
        rdf_viewer = ScrollWidget()
        f_picker = FunctionPicker()

        layout1.addWidget(f_picker, 0, 0, 1, 1)
        layout1.addWidget(code_viewer, 0, 1, 1, 4)
        layout1.addWidget(rdf_viewer, 0, 5, 1, 4)

        # Tab to view flow
        viewTab = QWidget()
        layout2 = QHBoxLayout()
        viewTab.setLayout(layout2)

        ctrlWidget = FlowCtrlWidget()
        layout2.addWidget(ctrlWidget)

        # Event handling
        f_picker.file_loaded.connect(code_viewer.setText)
        f_picker.function_loaded.connect(code_viewer.setSource)
        f_picker.function_loaded.connect(rdf_viewer.setGraph)
        f_picker.function_loaded.connect(ctrlWidget.setFlow)

        # Add Tabs
        tabWidget = QTabWidget()
        tabWidget.addTab(loadTab, "Load")
        tabWidget.addTab(viewTab, "View")
        self.setCentralWidget(tabWidget)