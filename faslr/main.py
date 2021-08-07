import schema
import sqlalchemy as sa
import sys

from constants import (
    BUILD_VERSION,
    QT_FILEPATH_OPTION
)

from sqlalchemy.orm import sessionmaker

from PyQt5.Qt import (
    QStandardItem,
    QStandardItemModel
)

from PyQt5.QtGui import (
    QColor,
    QFont,
    QKeySequence
)

from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QRadioButton,
    QStatusBar,
    QTreeView,
    QVBoxLayout
)

from schema import ProjectTable

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Flag to determine whether there is an active database connection. Most project-related functions
        # should be disabled unless a connection is established.
        self.connection_established = False
        self.db = None

        self.resize(500, 700)

        self.setWindowTitle("FASLR - Free Actuarial System for Loss Reserving")

        menu_bar = self.menuBar()

        self.connection_action = QAction("&Connection", self)
        self.connection_action.setShortcut(QKeySequence("Ctrl+Shift+c"))
        self.connection_action.setStatusTip("Edit database connection.")
        self.connection_action.triggered.connect(self.edit_connection)

        self.new_action = QAction("&New Project", self)
        self.new_action.setShortcut(QKeySequence("Ctrl+n"))
        self.new_action.setStatusTip("Create new project.")
        self.new_action.triggered.connect(self.new_project)

        self.import_action = QAction("&Import Project")
        self.import_action.setShortcut(QKeySequence("Ctrl+Shift+i"))
        self.import_action.setStatusTip("Import a project from another data source.")

        self.engine_action = QAction("&Select Engine")
        self.engine_action.setShortcut("Ctrl+shift+e")
        self.engine_action.setStatusTip("Select a reserving engine.")

        self.settings_action = QAction("&Settings")
        self.settings_action.setShortcut("Ctrl+Shift+t")
        self.settings_action.setStatusTip("Open settings dialog box.")

        self.about_action = QAction("&About", self)
        self.about_action.setStatusTip("About")
        self.about_action.triggered.connect(self.display_about)

        file_menu = QMenu("&File", self)
        menu_bar.addMenu(file_menu)
        menu_bar.addMenu("&Edit")
        tools_menu = menu_bar.addMenu("&Tools")
        help_menu = menu_bar.addMenu("&Help")

        file_menu.addAction(self.connection_action)
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.import_action)
        file_menu.addAction(self.settings_action)

        tools_menu.addAction(self.engine_action)

        help_menu.addAction(self.about_action)

        self.setStatusBar(QStatusBar(self))

        self.toggle_project_actions()

        # navigation pane for project hierarchy

        self.project_pane = QTreeView(self)
        self.project_pane.setHeaderHidden(False)

        self.project_model = QStandardItemModel()

        self.project_root = self.project_model.invisibleRootItem()
        self.project_pane.setModel(self.project_model)
        self.project_pane.expandAll()

        self.setCentralWidget(self.project_pane)

    # disable project-based menu items until connection is established
    def toggle_project_actions(self):
        if self.connection_established:
            self.new_action.setEnabled(True)
        else:
            self.new_action.setEnabled(False)

    def edit_connection(self):

        dlg = ConnectionDialog(self)
        dlg.exec_()

    def display_about(self):

        dlg = AboutDialog(self)
        dlg.exec_()

    def new_project(self):

        dlg = ProjectDialog(self)
        dlg.exec_()


class ProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.country_edit = QLineEdit()
        self.state_edit = QLineEdit()
        self.lob_edit = QLineEdit()

        self.setWindowTitle("New Project")
        self.layout = QFormLayout()
        self.layout.addRow("Country:", self.country_edit)
        self.layout.addRow("State:", self.state_edit)
        self.layout.addRow("Line of Business:", self.lob_edit)

        button_layout = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.button_box = QDialogButtonBox(button_layout)

        self.button_box = QDialogButtonBox(button_layout)
        self.button_box.accepted.connect(lambda main_window=parent: self.make_project(main_window))
        self.button_box.rejected.connect(self.reject)

        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)

    def make_project(self, main_window):

        # connect to the database
        engine = sa.create_engine(
            main_window.db,
            echo=True
        )
        session = sessionmaker(bind=engine)
        schema.Base.metadata.create_all(engine)
        session = session()
        connection = engine.connect()

        country = ProjectItem(self.country_edit.text(), 16, set_bold=True)
        lob = ProjectItem(self.state_edit.text(), 12, text_color=QColor(155, 0, 0))
        state = ProjectItem(self.lob_edit.text(), 14)

        country.appendRow(state)
        state.appendRow(lob)

        session.add_all([
            ProjectTable(
                country=self.country_edit.text(),
                state=self.state_edit.text(),
                line_of_business=self.lob_edit.text()
            )
        ])

        session.commit()

        connection.close()

        main_window.project_root.appendRow(country)
        main_window.project_pane.expandAll()
        print("new project created")

        self.close()


class ConnectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Connection")
        self.layout = QVBoxLayout()

        self.existing_connection = QRadioButton("Connect to existing database")
        self.existing_connection.setChecked(True)
        self.layout.addWidget(self.existing_connection)

        self.new_connection = QRadioButton("Create new database")
        self.layout.addWidget(self.new_connection)

        button_layout = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.button_box = QDialogButtonBox(button_layout)
        self.button_box.accepted.connect(lambda main_window=parent: self.make_connection(main_window))
        self.button_box.rejected.connect(self.reject)

        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

    def make_connection(self, main_window):

        if self.existing_connection.isChecked():
            self.open_existing_db()
            main_window.connection_established = True
            main_window.toggle_project_actions()
        elif self.new_connection.isChecked():
            main_window.db = self.create_new_db()
            main_window.connection_established = True
            main_window.toggle_project_actions()

    def create_new_db(self):

        filename = QFileDialog.getSaveFileName(
            self,
            'SaveFile',
            'untitled.db',
            "Sqlite Database (*.db)",
            options=QT_FILEPATH_OPTION
        )
        print(filename[0])

        if not filename[0] == "":
            engine = sa.create_engine(
                'sqlite:///' + filename[0],
                echo=True
            )
            session = sessionmaker(bind=engine)
            schema.Base.metadata.create_all(engine)
            session = session()
            connection = engine.connect()
            connection.close()

            self.close()

        return 'sqlite:///' + filename[0]

    def open_existing_db(self):
        filename = QFileDialog.getOpenFileName(self, 'OpenFile')
        print(filename)

        if not filename[0] == "":
            engine = sa.create_engine(
                'sqlite:///' + filename[0],
                echo=True
            )
            session = sessionmaker(bind=engine)
            connection = engine.connect()
            connection.close()

            self.close()


class AboutDialog(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("About")
        self.setText("FASLR v" + BUILD_VERSION + "\n\nGit Repository: https://github.com/genedan/FASLR")

        self.setStandardButtons(QMessageBox.Ok)
        self.setIcon(QMessageBox.Information)


class ProjectItem(QStandardItem):
    def __init__(self, text='', font_size=12, set_bold=False, text_color=QColor(0, 0, 0)):
        super().__init__()

        project_font = QFont('Open Sans', font_size)
        project_font.setBold(set_bold)

        self.setForeground(text_color)
        self.setFont(project_font)
        self.setText(text)


app = QApplication(sys.argv)

window = MainWindow()

window.show()

app.exec_()
