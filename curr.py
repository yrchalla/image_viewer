import requests
import os, sys
import zipfile
import threading
import time

if getattr(sys, 'frozen', False):
    # The application is running as a bundled executable
    current_dir = os.path.dirname(sys.executable)
else:
    # The application is running as a script
    current_dir = os.path.dirname(os.path.abspath(__file__))

if not os.path.isdir(os.path.join(current_dir, "openslide-win64-20230414")):
    url = "https://github.com/openslide/openslide-winbuild/releases/download/v20230414/openslide-win64-20230414.zip"
    filename = "openslide-win64-20230414.zip"

    # Send a GET request to the URL and stream the response
    response = requests.get(url, stream=True)

    # Check if the request was successful
    if response.status_code == 200:
        with open(os.path.join(current_dir, filename), "wb") as file:
            # Iterate over the response content in chunks and write to file
            for chunk in response.iter_content(chunk_size=4096):
                file.write(chunk)
        print(f"Download completed: {filename}")
    else:
        print("Failed to download the file.")
    with zipfile.ZipFile(os.path.join(current_dir, 'openslide-win64-20230414.zip'), 'r') as zip:
        zip.extractall(current_dir)




from PyQt6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QWidget,
    QGridLayout,
    QLabel,
    QFileDialog,
    QInputDialog,
    QSizePolicy,
    QToolBar,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
)
from PyQt6.QtGui import QPixmap, QIcon, QKeySequence, QImage
from PyQt6.QtCore import QDir, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
import sys, os
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QSize
from PyQt6.QtCore import QSettings
from verification_dump import get_np_predicts, count_predicts


class MainWindow(QMainWindow):
    def __init__(self, settings, parent=None):

        super().__init__(parent)
        self.tile_size = 512
        self.falsePositives = set()
        self.currPage = 0
        self.res = 200
        # Connect the QMainWindow's resize event to a custom function
        self.resizeEvent = self.onResize
        # Add a menu bar and a "File" menu
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu("&File")

        # Add an "Open" action to the "File" menu
        openAction = QAction("&Open", self)
        openAction.triggered.connect(self.onOpenActionTriggered)
        fileMenu.addAction(openAction)

        helpMenu = menuBar.addMenu("&Help")

        # Add an "Open" action to the "File" menu
        aboutAction = QAction("&About", self)
        aboutAction.triggered.connect(self.onAboutActionTriggered)
        helpMenu.addAction(aboutAction)

        # Add a "View" menu
        viewMenu = menuBar.addMenu("&View")

        # Add a "Hide/Show Toolbar" action to the "View" menu
        toggleToolbarAction = QAction("Show Toolbar", self)
        toggleToolbarAction.setCheckable(True)
        toggleToolbarAction.setChecked(True)
        toggleToolbarAction.triggered.connect(self.onToggleToolbarActionTriggered)
        viewMenu.addAction(toggleToolbarAction)

        # Add a "Settings" menu
        settingsMenu = menuBar.addMenu("&Settings")

        # Add a "Set Resolution" action to the "Settings" menu
        setResAction = QAction("Set &Resolution...", self)
        setResAction.triggered.connect(self.onSetResActionTriggered)
        settingsMenu.addAction(setResAction)

        # Add a "Set Rows" action to the "Settings" menu
        setRowsAction = QAction("Set &Rows...", self)
        setRowsAction.triggered.connect(self.onSetRowsActionTriggered)
        settingsMenu.addAction(setRowsAction)

        setSizeAction = QAction("Set &Tile Size...", self)
        setSizeAction.triggered.connect(self.onSetSizeActionTriggered)
        settingsMenu.addAction(setSizeAction)

        actionsMenu = menuBar.addMenu("&Actions")
        nextAction = QAction("&Next", self)
        nextAction.triggered.connect(self.onNextButtonClicked)
        actionsMenu.addAction(nextAction)
        backAction = QAction("&Back", self)
        backAction.triggered.connect(self.onBackButtonClicked)
        actionsMenu.addAction(backAction)

        # Create and set up the toolbar
        self.toolbar = QToolBar(self)
        self.addToolBar(self.toolbar)

        # Add the back button to the toolbar
        # backIcon = QIcon.fromTheme("go-previous")
        backIcon =  QIcon("app_data\\back.png")
        self.backButton = QAction(backIcon, "Back", self)
        # self.backButton.setShortcut("Left")
        self.backButton.triggered.connect(self.onBackButtonClicked)

        self.nRows = 3
        self.nCols = 6

        # Add the next button to the toolbar
        # nextIcon = QIcon.fromTheme("go-next")
        nextIcon = QIcon("app_data\\next.png")
        self.nextButton = QAction(nextIcon, "Next", self)
        # self.nextButton.setShortcut("Right")
        self.nextButton.triggered.connect(self.onNextButtonClicked)

        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)  # Removes text from buttons
        self.toolbar.addAction(self.backButton)
        self.toolbar.addAction(self.nextButton)

        # Set the central widget to a container widget
        self.containerWidget = QWidget(self)
        self.setCentralWidget(self.containerWidget)

        # Create and set up the scroll area
        self.scrollAreaWidgetContents = QWidget(self.containerWidget)

        screenGeometry = QApplication.primaryScreen().availableGeometry()
        # self.setMaximumSize(screenGeometry.width()+10, screenGeometry.height()+10)

        self.maxSize = min(screenGeometry.width(), screenGeometry.height()) // self.nRows
        self.maxSize = QSize(int(self.maxSize*0.9), int(self.maxSize*0.9))

        # Create the layout for the page number label
        pageLayout = QHBoxLayout()

        # Create a spacer item to push the label to the right
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        pageLayout.addItem(spacerItem)
        self.pageLabel = QLabel(self)
        # Add the label to the page layout
        pageLayout.addWidget(self.pageLabel)

        layout = QVBoxLayout(self.containerWidget)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.scrollAreaWidgetContents)
        layout.addLayout(pageLayout)

        # Set the layout of the scroll area widget contents
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scrollAreaWidgetContents.setLayout(self.gridLayout)
        self.scrollAreaWidgetContents.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Display the images in the specified folder
        self.folderPath = settings.value("last_value", "/")
        if not (os.path.isfile(self.folderPath) and self.folderPath.endswith(".ndpi")):
            self.folderPath = str(QFileDialog.getOpenFileName(self, "Select ndpi file", QDir.homePath())[0])
            settings.setValue("last_value", self.folderPath)
        if not os.path.isfile(self.folderPath[:-5]+"_fp.txt"):
            with open(self.folderPath[:-5]+"_fp.txt", 'w') as _:
                pass
        # read into set
        with open(self.folderPath[:-5]+"_fp.txt", 'r') as file:
            for line in file:
                self.falsePositives.add(int(line.strip()))  # Remove newline character and add line to set



        self.setWindowTitle(self.folderPath)
        # self.tile_list, self.id_list = get_np_predicts(self.folderPath[:self.folderPath.rfind('\\')], self.folderPath.split('\\')[-1].split('.')[0])
        self.tile_list = []
        thread = threading.Thread(target=get_np_predicts, args=(self.folderPath[:self.folderPath.rfind('\\')], self.folderPath.split('\\')[-1].split('.')[0], self.tile_list, self.tile_size))
        thread.start()
        # get_np_predicts(self.folderPath[:self.folderPath.rfind('\\')], self.folderPath.split('\\')[-1].split('.')[0], self.tile_list)
        self.numImages = count_predicts(self.folderPath[:self.folderPath.rfind('\\')], self.folderPath.split('\\')[-1].split('.')[0])
        self.maxPage = (self.numImages - 1) // (self.nRows * self.nCols)
        # Create the label for the page number
        self.pageLabel.setText("Page " + str(self.currPage+1) + "/" + str(self.maxPage+1))
        self.leftShortcut = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.leftShortcut.activated.connect(self.onBackButtonClicked)

        self.rightShortcut = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.rightShortcut.activated.connect(self.onNextButtonClicked)
        time.sleep(1.5)
        self.displayImages(0, self.nRows * self.nCols - 1)

        # self.showFullScreen()  # <--- add this line to show the window in fullscreen mode
        # self.toolbar.setVisible(False)

    def displayImages(self, startIndex: int, endIndex: int) -> None:
        row = 0
        column = 0
        maxColumns = self.nCols

        for i in range(startIndex, endIndex+1):
            if i < len(self.tile_list):
                imageFile = self.tile_list[i]
                height, width, channel = imageFile.shape
                bytesPerLine = channel * width
                qimage = QImage(imageFile.data, width, height, bytesPerLine, QImage.Format.Format_RGB888)


                # Create the label and pixmap for the image
                imageLabel = QLabel(self)
                imageLabel.setMaximumSize(self.maxSize)
                pixmap = QPixmap.fromImage(qimage)
                pixmap = pixmap.scaledToWidth(self.res)

                # Set the pixmap on the label and add it to the grid layout
                imageLabel.setPixmap(pixmap)
                imageLabel.setScaledContents(True)  # Ensure pixmap always fills label
                # Set the size policy of the image label
                imageLabel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

                imageLabel.mouseDoubleClickEvent = lambda event, label=imageLabel: self.onImageLabelClicked(label)

                self.gridLayout.addWidget(imageLabel, row, column)

            else:
                imageLabel = QLabel(self)
                placeholderPixmap = QPixmap(100, 100)
                placeholderPixmap.fill(QColor(200, 200, 200))
                imageLabel.setPixmap(placeholderPixmap)
                imageLabel.setScaledContents(True)
                imageLabel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                self.gridLayout.addWidget(imageLabel, row, column)

            # Increment the row and column counters
            column += 1
            if column == maxColumns:
                row += 1
                column = 0

        if self.currPage < self.maxPage:
            self.nextButton.setEnabled(True)
            self.rightShortcut.setEnabled(True)
        else:
            self.nextButton.setEnabled(False)
            self.rightShortcut.setEnabled(False)

        if self.currPage > 0:
            self.backButton.setEnabled(True)
            self.leftShortcut.setEnabled(True)
        else:
            self.backButton.setEnabled(False)
            self.leftShortcut.setEnabled(False)

        # Resize the window
        self.gridLayout.update()
        # Set grid lines to the widgets in the grid layout
        for i in range(self.gridLayout.count()):
            widget = self.gridLayout.itemAt(i).widget()
            if (i < self.nRows*self.nCols) and (i+self.currPage*self.nRows*self.nCols in self.falsePositives):
                widget.setStyleSheet("border: 4px solid red;")
            else:
                widget.setStyleSheet("border: 4px solid black;")
        # self.scrollAreaWidgetContents.adjustSize()


    def onNextButtonClicked(self):
        if (self.currPage >= self.maxPage):
            return
        width = self.width()
        height = self.height()
        child = self.gridLayout.takeAt(0)
        while child is not None:
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()
            del child
            child = self.gridLayout.takeAt(0)
        self.currPage += 1
        self.pageLabel.setText("Page " + str(self.currPage+1) + "/" + str(self.maxPage+1))
        self.displayImages(self.currPage * self.nRows * self.nCols, (self.currPage * self.nRows * self.nCols) + (self.nRows * self.nCols) - 1)
        self.resize(width, height)
        


    def onBackButtonClicked(self):
        if self.currPage == 0:
            return
        width = self.width()
        height = self.height()
        child = self.gridLayout.takeAt(0)
        while child is not None:
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()
            del child
            child = self.gridLayout.takeAt(0)
        self.currPage -= 1
        self.pageLabel.setText("Page " + str(self.currPage+1) + "/" + str(self.maxPage+1))
        self.displayImages(self.currPage * self.nRows * self.nCols, (self.currPage * self.nRows * self.nCols) + (self.nRows * self.nCols) - 1)
        self.resize(width, height)

    def onSetRowsActionTriggered(self):
        width = self.width()
        height = self.height()
        text, ok = QInputDialog.getText(self, "Input Dialog", "WARNING! The app will flip to the first page. Enter the row count:")
        text0, ok0 = QInputDialog.getText(self, "Input Dialog", "WARNING! The app will flip to the first page. Enter the column count:")
        if ok and text != '':
            self.nRows = int(text)
        if ok0 and text0 != '':
            self.nCols = int(text0)
        screenGeometry = QApplication.primaryScreen().availableGeometry()
        self.maxSize = min(screenGeometry.width(), screenGeometry.height()) // self.nRows
        self.maxSize = QSize(self.maxSize, self.maxSize)
        self.currPage = 0
        self.maxPage = (self.numImages - 1) // (self.nRows * self.nCols)
        self.pageLabel.setText("Page " + str(self.currPage+1) + "/" + str(self.maxPage+1))
        child = self.gridLayout.takeAt(0)
        while child is not None:
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()
            del child
            child = self.gridLayout.takeAt(0)    
        self.displayImages(0, self.nRows * self.nCols - 1)
        self.resize(width, height)

    def onSetSizeActionTriggered(self):
        width = self.width()
        height = self.height()
        text, ok = QInputDialog.getText(self, "Input Dialog", "WARNING! The app will flip to the first page. Enter value:")
        if ok and text != '':
            self.tile_size = int(text)
            self.currPage = 0
            self.pageLabel.setText("Page " + str(self.currPage+1) + "/" + str(self.maxPage+1))
            child = self.gridLayout.takeAt(0)
            while child is not None:
                widget = child.widget()
                if widget is not None:
                    widget.deleteLater()
                del child
                child = self.gridLayout.takeAt(0)
            self.tile_list = []
            # get_np_predicts(self.folderPath[:self.folderPath.rfind('\\')], self.folderPath.split('\\')[-1].split('.')[0], self.tile_list)
            thread = threading.Thread(target=get_np_predicts, args=(self.folderPath[:self.folderPath.rfind('\\')], self.folderPath.split('\\')[-1].split('.')[0], self.tile_list, self.tile_size))
            thread.start()
            time.sleep(1.5)
            self.displayImages(0, self.nRows * self.nCols - 1)
            self.resize(width, height)

    def onSetResActionTriggered(self):
        text, ok = QInputDialog.getText(self, "Input Dialog", "Change page afterward for effects to take place. Enter the resolution:")
        if ok and text != '':
            self.res = int(text)

    def save(self):
        open(self.folderPath[:-5]+"_fp.txt", 'w').close()
        # clear and write line by line
        with open(self.folderPath[:-5]+"_fp.txt", 'w') as file:
            for line in self.falsePositives:
                file.write(str(line) + '\n')  # Write line to file with a newline character
    
    def onOpenActionTriggered(self):
        width = self.width()
        height = self.height()
        folderPath = str(QFileDialog.getOpenFileName(self, "Select ndpi file", QDir.homePath())[0])
        if folderPath:
            self.falsePositives = set()
            if not os.path.isfile(self.folderPath[:-5]+"_fp.txt"):
                with open(self.folderPath[:-5]+"_fp.txt", 'w') as _:
                    pass
            # read into set
            with open(self.folderPath[:-5]+"_fp.txt", 'r') as file:
                for line in file:
                    self.falsePositives.add(int(line.strip()))  # Remove newline character and add line to set
            self.setWindowTitle(folderPath)
            settings.setValue("last_value", folderPath)
            self.folderPath = folderPath
            self.currPage = 0
            self.setWindowTitle(self.folderPath)
            # self.tile_list, self.id_list = get_np_predicts(self.folderPath[:self.folderPath.rfind('\\')], self.folderPath.split('\\')[-1].split('.')[0])
            self.tile_list = []
            # get_np_predicts(self.folderPath[:self.folderPath.rfind('\\')], self.folderPath.split('\\')[-1].split('.')[0], self.tile_list)
            thread = threading.Thread(target=get_np_predicts, args=(self.folderPath[:self.folderPath.rfind('\\')], self.folderPath.split('\\')[-1].split('.')[0], self.tile_list, self.tile_size))
            thread.start()
            self.numImages = count_predicts(self.folderPath[:self.folderPath.rfind('\\')], self.folderPath.split('\\')[-1].split('.')[0])
            self.maxPage = (self.numImages - 1) // (self.nRows * self.nCols)
            # Create the label for the page number
            self.pageLabel.setText("Page " + str(self.currPage+1) + "/" + str(self.maxPage+1))
            child = self.gridLayout.takeAt(0)
            while child is not None:
                widget = child.widget()
                if widget is not None:
                    widget.deleteLater()
                del child
                child = self.gridLayout.takeAt(0)    
            time.sleep(1.5)
            self.displayImages(0, self.nRows * self.nCols - 1)
            self.resize(width, height)

    def onResize(self, event):
        width = event.size().width()
        height = event.size().height()
        screenGeometry = QApplication.primaryScreen().availableGeometry()
        if width < 0.9 * screenGeometry.width():
            ratio = 0.9*self.nCols/(self.nRows)
            if width / height > ratio:  
                # Constrain height
                new_height = int(min(width / ratio, screenGeometry.height()*0.9))
                self.resize(int(new_height*ratio), new_height)
            else:
                # Constrain width
                new_width = int(height*ratio)
                self.resize(new_width, height)

        if self.height() > screenGeometry.height():
            self.resize(int(ratio*screenGeometry.height()), screenGeometry.height())

        # Update the geometry of the grid layout and its contents
        # Set the horizontal spacing of the grid layout to fill the width of the window
        layoutWidth = self.containerWidget.size().width() - self.gridLayout.spacing() * (self.nCols - 1)
        labelWidth = self.maxSize.width() * self.nCols
        spacing = max(10, (layoutWidth - labelWidth) // (self.nCols - 1))
        self.gridLayout.setHorizontalSpacing(spacing)
        self.gridLayout.setGeometry(self.scrollAreaWidgetContents.rect())

        # Call the base class's resize event
        super().resizeEvent(event)


    def onImageLabelClicked(self, label):
        # Set the border color to red
        # Get the index of the widget in the grid layout
        index = self.gridLayout.indexOf(label)

        # Calculate the row and column based on the index
        row, col = divmod(index, self.nCols)
        widget = self.gridLayout.itemAtPosition(row, col).widget()
        if index+self.currPage*self.nRows*self.nCols not in self.falsePositives:
            widget.setStyleSheet("border: 4px solid red;")
            self.falsePositives.add(index+self.currPage*self.nRows*self.nCols)
            self.save()
        else:
            widget.setStyleSheet("border: 4px solid black;")
            self.falsePositives.discard(index+self.currPage*self.nRows*self.nCols)
            self.save()
    
    def onToggleToolbarActionTriggered(self, checked):
        self.toolbar.setVisible(checked)
    
    def toggleFullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def onAboutActionTriggered(self):
        msgBox = QMessageBox()
        msgBox.setText("Version 2")
        msgBox.exec()



        


if __name__ == '__main__':
    # Create a QSettings object with the organization name and the application name
    settings = QSettings("Vyuha", "Viewer")

    # Read the value of the variable from the settings
    app = QApplication(sys.argv)
    w = MainWindow(settings)
    w.show()
    sys.exit(app.exec())
