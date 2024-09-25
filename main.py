#!/usr/bin/env python3

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QComboBox,
                             QFileDialog, QSpinBox, QVBoxLayout, QHBoxLayout, QWidget,
                             QCheckBox, QListWidget, QListWidgetItem, QGroupBox, QFormLayout,QFrame,QSizePolicy)
from PyQt5.QtGui import QPixmap, QPainter, QImage
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrinterInfo
from PyQt5.QtCore import Qt, QSize, QRect

class PhotoPrintApp(QWidget):
    def __init__(self, image_files):
        super().__init__()
        self.setWindowTitle("Print Pictures")
        self.setGeometry(100, 100, 800, 600)
        self.images = []
        self.current_image_index = 0
        self.current_layout = "full_page"
        self.initUI()

        # Load images passed as command-line arguments
        self.load_images_from_command_line(image_files)

    def initUI(self):
        mainLayout = QVBoxLayout()

        # Print settings
        settingsLayout = QHBoxLayout()
        settingsLayout.addWidget(QLabel('Printer:'))
        settingsLayout.addWidget(QComboBox())
        
        settingsLayout.addWidget(QLabel('Paper size:'))
        paperSizeCombo = QComboBox()
        paperSizeCombo.addItem('A4')
        settingsLayout.addWidget(paperSizeCombo)
        
        settingsLayout.addWidget(QLabel('Quality:'))
        qualityCombo = QComboBox()
        qualityCombo.addItem('Standard')
        settingsLayout.addWidget(qualityCombo)
        
        settingsLayout.addWidget(QLabel('Paper type:'))
        paperTypeCombo = QComboBox()
        paperTypeCombo.addItem('Plain paper')
        settingsLayout.addWidget(paperTypeCombo)

        mainLayout.addLayout(settingsLayout)

        # Image preview and options
        previewLayout = QHBoxLayout()

        # Left side - main image
        leftLayout = QVBoxLayout()
        self.imagePreview = QLabel()
        self.imagePreview.setFrameShape(QFrame.StyledPanel)
        self.imagePreview.setAlignment(Qt.AlignCenter)
        self.imagePreview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.imagePreview.setMinimumSize(400, 300)
        self.imagePreview.setStyleSheet("border: 1px solid gray;")
        leftLayout.addWidget(self.imagePreview)

        navigationLayout = QHBoxLayout()
        self.prev_button = QPushButton("<")
        self.prev_button.clicked.connect(self.navigate_previous)
        navigationLayout.addWidget(self.prev_button)

        self.pageLabel = QLabel('1 of 1 page')
        self.pageLabel.setAlignment(Qt.AlignRight)
        
        self.next_button = QPushButton(">")
        self.next_button.clicked.connect(self.navigate_next)
        navigationLayout.addWidget(self.next_button)

        navigationLayout.addWidget(self.pageLabel, 1)  # Give more space to center the label
        leftLayout.addLayout(navigationLayout)

        leftFrame = QFrame()
        leftFrame.setLayout(leftLayout)
        previewLayout.addWidget(leftFrame, 3)  # Increase ratio to make listbox smaller
        
        # Right side - list of print options
        self.optionsList = QListWidget()
        self.optionsList.addItem(QListWidgetItem('Full page photo'))
        self.optionsList.addItem(QListWidgetItem('13 x 18 cm, (2)'))
        self.optionsList.addItem(QListWidgetItem('20 x 25 cm, (1)'))
        self.optionsList.setMaximumWidth(200)  # Limit the width of the listbox
        self.optionsList.currentItemChanged.connect(self.update_layout)  # Connect item change
        previewLayout.addWidget(self.optionsList, 1)

        mainLayout.addLayout(previewLayout)

        # Bottom options
        bottomLayout = QHBoxLayout()
        bottomLayout.addWidget(QLabel("Copies of each picture:"))
        self.copies_spinbox = QSpinBox()
        self.copies_spinbox.setValue(1)
        self.copies_spinbox.setMinimum(1)
        bottomLayout.addWidget(self.copies_spinbox)

        self.fit_checkbox = QCheckBox("Fit picture to frame")
        self.fit_checkbox.stateChanged.connect(self.update_preview)
        bottomLayout.addWidget(self.fit_checkbox)

        bottomLayout.addStretch()

        self.options_button = QPushButton("Options...")
        bottomLayout.addWidget(self.options_button)

        self.print_button = QPushButton("Print")
        self.print_button.clicked.connect(self.print_images)
        bottomLayout.addWidget(self.print_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close)
        bottomLayout.addWidget(self.cancel_button)

        mainLayout.addLayout(bottomLayout)

        self.setLayout(mainLayout)

    def load_images_from_command_line(self, image_files):
        if image_files:
            self.images.extend(image_files)
            if self.images:  # Check if images are loaded before updating preview
                self.update_preview()

    def update_layout(self):
        current_item = self.optionsList.currentItem()
        if current_item:
            self.current_layout = current_item.text().split()[0].lower().replace('x', 'x').replace(',', '')
            self.current_image_index = 0
            self.update_preview()

    def navigate_previous(self):
        if self.current_layout == "13":
            if self.current_image_index > 1:
                self.current_image_index -= 2
            elif self.current_image_index == 1:
                self.current_image_index -= 1
        else:
            if self.current_image_index > 0:
                self.current_image_index -= 1
        self.update_preview()

    def navigate_next(self):
        if self.current_layout == "13":
            if self.current_image_index + 2 < len(self.images):
                self.current_image_index += 2
            elif self.current_image_index + 1 < len(self.images):
                self.current_image_index += 1
        else:
            if self.current_image_index < len(self.images) - 1:
                self.current_image_index += 1
        self.update_preview()

    def update_preview(self):
        if not self.images:
            return

        preview = QPixmap(500, 400)
        preview.fill(Qt.white)
        painter = QPainter(preview)

        if self.current_layout == "full":
            self.draw_full_page_layout(painter)
        elif self.current_layout == "13":
            self.draw_13x18_layout(painter)
        elif self.current_layout == "20":
            self.draw_20x25_layout(painter)

        painter.end()
        self.imagePreview.setPixmap(preview)

        # Update page count
        page_count = self.get_page_count()
        self.pageLabel.setText(f"{page_count[0]} of {page_count[1]} page")

    def get_page_count(self):
        if not self.images:
            return (0, 0)

        if self.current_layout == "full":
            return (self.current_image_index + 1, len(self.images))
        elif self.current_layout == "13":
            return ((self.current_image_index // 2) + 1, (len(self.images) + 1) // 2)
        elif self.current_layout == "20":
            return (self.current_image_index + 1, len(self.images))

        return (0, 0)  # Default return value

    def draw_full_page_layout(self, painter):
        if self.current_image_index < len(self.images):
            img = QImage(self.images[self.current_image_index])
            target_rect = QRect(0, 0, 500, 400)
            self.draw_image(painter, img, target_rect)

    def draw_13x18_layout(self, painter):
        total_images = len(self.images)
        if self.current_image_index < total_images:
            # Draw first image
            img1 = QImage(self.images[self.current_image_index])
            target_rect1 = QRect(0, 0, 250, 400)
            self.draw_image(painter, img1, target_rect1)

        if self.current_image_index + 1 < total_images:
            # Draw second image
            img2 = QImage(self.images[self.current_image_index + 1])
            target_rect2 = QRect(250, 0, 250, 400)
            self.draw_image(painter, img2, target_rect2)

    def draw_20x25_layout(self, painter):
        if self.current_image_index < len(self.images):
            img = QImage(self.images[self.current_image_index])
            target_rect = QRect(50, 0, 400, 400)
            self.draw_image(painter, img, target_rect)

    def draw_image(self, painter, img, target_rect):
        if img.isNull():
            print(f"Image failed to load: {img}")
            return

        if self.fit_checkbox.isChecked():
            scaled_img = img.scaled(target_rect.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        else:
            scaled_img = img.scaled(target_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        x_offset = (target_rect.width() - scaled_img.width()) // 2
        y_offset = (target_rect.height() - scaled_img.height()) // 2

        painter.drawImage(target_rect.adjusted(x_offset, y_offset, -x_offset, -y_offset), scaled_img)

    def print_images(self):
        if not self.images:
            return

        printer = QPrinter(QPrinterInfo.defaultPrinter())
        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QPrintDialog.Accepted:
            painter = QPainter(printer)

            for index in range(len(self.images)):
                self.current_image_index = index
                self.update_preview()  # Update preview before printing
                self.draw_full_page_layout(painter)  # Just print full page for each image
                if index < len(self.images) - 1:
                    printer.newPage()  # Add new page for each image
            painter.end()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    image_files = sys.argv[1:]  # Get image files from command-line arguments
    mainWin = PhotoPrintApp(image_files)
    mainWin.show()
    sys.exit(app.exec_())
