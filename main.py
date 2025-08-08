#!/usr/bin/env python3
import sys
import math
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox,
    QFileDialog, QSpinBox, QVBoxLayout, QHBoxLayout,
    QFrame, QSizePolicy, QListWidgetItem,
    QMessageBox, QListWidget
)
from PySide6.QtGui import QPixmap, QPainter, QImage, QTransform, QPageSize, QPageLayout, QIcon
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrinterInfo
from PySide6.QtCore import Qt, QRect, QRectF, QSizeF, QSettings

class PrintImage(QWidget):
    PHOTO_GAP_MM = 2

    def __init__(self, image_files):
        super().__init__()
        # Set window icon (KDE icon, or use a local file path)
        self.setWindowIcon(QIcon.fromTheme("document-print"))
        self.setWindowTitle("Print Images")
        self.setGeometry(100, 100, 700, 600)

        self.source_images = []
        self.document_pages = []
        self.current_document_page_index = 0
        self.image_rotations = {}

        self.current_layout_key = "full_page"
        self.current_photo_print_size_key = None

        self.no_physical_printer = False

        self.paper_definitions = {
            "A4 (210 x 297 mm)": (210, 297, "A4"),
            "F4 (210 x 330 mm)": (210, 330, "F4"),
            "Letter (216 x 279 mm)": (216, 279, "Letter"),
            "Legal (216 x 356 mm)": (216, 356, "Legal"),
            "A5 (148 x 210 mm)": (148, 210, "A5"),
            "B5 (176 x 250 mm)": (176, 250, "B5"),
            "Executive (184 x 267 mm)": (184, 267, "Executive"),
            "Tabloid (279 x 432 mm)": (279, 432, "Tabloid"),
            "Statement (140 x 216 mm)": (140, 216, "Statement"),
            "A3 (297 x 420 mm)": (297, 420, "A3"),
            "B4 (250 x 353 mm)": (250, 353, "B4"),
            "C5 Envelope (162 x 229 mm)": (162, 229, "C5"),
            "DL Envelope (110 x 220 mm)": (110, 220, "DL"),
            "Monarch Envelope (98 x 191 mm)": (98, 191, "Monarch"),
        }

        self.photo_print_sizes_mm = {
            "2R (6.4x8.9cm) Portrait": (64, 89), "2R (8.9x6.4cm) Landscape": (89, 64),
            "3R (8.9x12.7cm) Portrait": (89, 127), "3R (12.7x8.9cm) Landscape": (127, 89),
            "4R (10.2x15.2cm) Portrait": (102, 152), "4R (15.2x10.2cm) Landscape": (152, 102),
            "5R (12.7x17.8cm) Portrait": (127, 178), "5R (17.8x12.7cm) Landscape": (178, 127),
            "6R (15.2x20.3cm) Portrait": (152, 203), "6R (20.3x15.2cm) Landscape": (203, 152),
            "8R (20.3x25.4cm) Portrait": (203, 254), "8R (25.4x20.3cm) Landscape": (254, 203),
            "10R (25.4x30.5cm) Portrait": (254, 305), "10R (30.5x25.4cm) Landscape": (305, 254),
            "ID Photo (2x3cm) Portrait": (20, 30), "ID Photo (3x2cm) Landscape": (30, 20),
            "ID Photo (3x4cm) Portrait": (30, 40), "ID Photo (4x3cm) Landscape": (40, 30),
            "ID Photo (4x6cm) Portrait": (40, 60), "ID Photo (6x4cm) Landscape": (60, 40),
            "Passport (EU) 3.5x4.5cm": (35, 45),
            "Passport (US) 5.1x5.1cm": (51, 51),
            "Square (10.2x10.2cm)": (102, 102),
            "Square (12.7x12.7cm)": (127, 127),
        }

        self.dynamic_layout_keys = {
            "paper_div_2_rows": "Layout: 2 photos per page",
            "paper_div_2x2_grid": "Layout: 4 photos per page (2x2)",
            "paper_div_2x3_grid": "Layout: 6 photos per page (2x3)",
            "paper_div_3x3_grid": "Layout: 9 photos per page (3x3)"
        }

        self.prev_button = None
        self.next_button = None

        self.settings = QSettings("printimg", "PrintImageApp")

        self.initUI()

        if image_files:
            self.load_images(image_files)
            if len(self.source_images) > 1:
                target_text = self.dynamic_layout_keys["paper_div_2x2_grid"]
                items = self.optionsList.findItems(target_text, Qt.MatchExactly)
                if items:
                    self.optionsList.setCurrentItem(items[0])
        else:
            self._regenerate_document_pages()

        if self.optionsList.count() > 0 and self.optionsList.currentRow() == -1:
            self.optionsList.setCurrentRow(0)

    def initUI(self):
        mainLayout = QVBoxLayout()

        self.pageLabel = QLabel('Page 0 of 0')
        self.pageLabel.setAlignment(Qt.AlignCenter)

        settingsLayout = QHBoxLayout()
        settingsLayout.addWidget(QLabel('Printer:'))
        self.printerCombo = QComboBox()
        self.printerCombo.addItem("Save as PDF")
        printers = QPrinterInfo.availablePrinters()
        default_printer_name = None
        if not printers:
            self.no_physical_printer = True
        else:
            default_printer_info = QPrinterInfo.defaultPrinter()
            if not default_printer_info.isNull():
                default_printer_name = default_printer_info.printerName()
            for printer in printers:
                self.printerCombo.addItem(printer.printerName())
        settingsLayout.addWidget(self.printerCombo)

        # Load last used printer from settings
        last_printer = self.settings.value("last_printer", None)
        idx = -1
        if last_printer:
            idx = self.printerCombo.findText(last_printer)
        if idx != -1:
            self.printerCombo.setCurrentIndex(idx)
        elif default_printer_name:
            idx = self.printerCombo.findText(default_printer_name)
            if idx != -1:
                self.printerCombo.setCurrentIndex(idx)
            else:
                self.printerCombo.setCurrentIndex(0)
        else:
            self.printerCombo.setCurrentIndex(0)

        self.printerCombo.currentIndexChanged.connect(self.on_printer_changed)

        self.paperSizeCombo = QComboBox()
        self.paper_size_display_map = {}
        allowed_paper_names = {"A4", "A5", "Letter"}

        default_printer_info = QPrinterInfo.defaultPrinter()
        if not self.no_physical_printer and not default_printer_info.isNull():
            supported_sizes = default_printer_info.supportedPageSizes()
            supported_sizes = sorted(
                supported_sizes,
                key=lambda ps: QPageSize.name(ps.id()).lower()
            )
            for page_size in supported_sizes:
                size_name = QPageSize.name(page_size.id())
                dimensions = page_size.size(QPageSize.Unit.Millimeter)
                width = dimensions.width()
                height = dimensions.height()
                display_name = f"{size_name} ({width:.2f} x {height:.2f} mm)"
                self.paperSizeCombo.addItem(display_name)
                self.paper_size_display_map[display_name] = page_size
        else:
            self.paperSizeCombo.addItem("F4 (210 x 330 mm)")
            for display_name in self.paper_definitions.keys():
                if display_name != "F4 (210 x 330 mm)":
                    self.paperSizeCombo.addItem(display_name)
        self.paperSizeCombo.currentIndexChanged.connect(self.on_paper_size_changed)  # changed handler
        settingsLayout.addWidget(QLabel('Paper size:'))
        settingsLayout.addWidget(self.paperSizeCombo)
        idx_a4 = -1
        for i in range(self.paperSizeCombo.count()):
            if "a4" in self.paperSizeCombo.itemText(i).lower():
                idx_a4 = i
                break

        # Load last used paper size from settings
        last_paper_size = self.settings.value("last_paper_size", None)
        idx_paper = -1
        if last_paper_size:
            idx_paper = self.paperSizeCombo.findText(last_paper_size)
        if idx_paper != -1:
            self.paperSizeCombo.setCurrentIndex(idx_paper)
        elif idx_a4 != -1:
            self.paperSizeCombo.setCurrentIndex(idx_a4)

        mainLayout.addLayout(settingsLayout)

        previewLayout = QHBoxLayout()
        leftLayout = QVBoxLayout()
        self.imagePreview = QLabel()
        self.imagePreview.setFrameShape(QFrame.StyledPanel)
        self.imagePreview.setAlignment(Qt.AlignCenter)
        self.imagePreview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.imagePreview.setMinimumSize(400, 500)
        self.imagePreview.setStyleSheet("border: 1px solid gray;")
        leftLayout.addWidget(self.imagePreview)

        navLayout = QHBoxLayout()
        self.prev_button = QPushButton("Previous")
        self.prev_button.setIcon(QIcon.fromTheme("go-previous"))
        self.prev_button.clicked.connect(self.navigate_previous_page)
        navLayout.addWidget(self.prev_button)
        navLayout.addWidget(self.pageLabel, 1)
        self.next_button = QPushButton("Next")
        self.next_button.setIcon(QIcon.fromTheme("go-next"))
        self.next_button.setLayoutDirection(Qt.RightToLeft)  # Tambahkan baris ini agar ikon di kanan
        self.next_button.clicked.connect(self.navigate_next_page)
        navLayout.addWidget(self.next_button)
        leftLayout.addLayout(navLayout)
        previewLayout.addLayout(leftLayout, 3)

        self.optionsList = QListWidget()
        self.optionsList.addItem('Full page photo')
        for key_display_text in self.dynamic_layout_keys.values():
            self.optionsList.addItem(key_display_text)
        separator = QListWidgetItem("--- Fixed Print Sizes ---")
        separator.setTextAlignment(Qt.AlignCenter)
        separator.setFlags(Qt.NoItemFlags)
        self.optionsList.addItem(separator)
        for size_key in self.photo_print_sizes_mm.keys():
            self.optionsList.addItem(f"Print size: {size_key}")
        self.optionsList.setMinimumWidth(280)
        self.optionsList.setMaximumWidth(500)
        self.optionsList.currentItemChanged.connect(self.on_layout_option_changed)
        previewLayout.addWidget(self.optionsList, 1)
        mainLayout.addLayout(previewLayout)

        bottomLayout = QHBoxLayout()
        bottomLayout.addWidget(QLabel("Copies of each picture:"))
        self.copies_spinbox = QSpinBox()
        self.copies_spinbox.setRange(1, 99)
        self.copies_spinbox.setValue(1)
        self.copies_spinbox.valueChanged.connect(self.on_settings_changed)
        bottomLayout.addWidget(self.copies_spinbox)
        bottomLayout.addWidget(QLabel("Image Scaling:"))
        self.scaling_mode_combo = QComboBox()
        self.scaling_mode_combo.addItems([
            "Crop",
            "Fit",
            "Stretch"
        ])
        self.scaling_mode_combo.setCurrentText("Fit")
        self.scaling_mode_combo.currentIndexChanged.connect(self.on_settings_changed)
        # Tambahkan ikon KDE pada setiap item combobox
        self.scaling_mode_combo.setItemIcon(0, QIcon.fromTheme("transform-crop"))      # Crop
        self.scaling_mode_combo.setItemIcon(1, QIcon.fromTheme("zoom-fit-best"))       # Fit
        self.scaling_mode_combo.setItemIcon(2, QIcon.fromTheme("transform-scale"))     # Stretch
        bottomLayout.addWidget(self.scaling_mode_combo)
        self.rotate_button = QPushButton("Rotate 90°")
        self.rotate_button.setIcon(QIcon.fromTheme("object-rotate-right"))
        self.rotate_button.clicked.connect(self.rotate_current_image)
        bottomLayout.addWidget(self.rotate_button)
        bottomLayout.addStretch()
        self.print_button = QPushButton("Print")
        self.print_button.setIcon(QIcon.fromTheme("document-print"))
        self.print_button.clicked.connect(self.print_images)
        bottomLayout.addWidget(self.print_button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setIcon(QIcon.fromTheme("dialog-cancel"))
        self.cancel_button.clicked.connect(self.close)
        bottomLayout.addWidget(self.cancel_button)
        mainLayout.addLayout(bottomLayout)
        self.setLayout(mainLayout)

    def center(self):
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())

    def update_page_label_ui(self):
        total_pages = len(self.document_pages)
        current_page = self.current_document_page_index + 1 if total_pages > 0 else 0
        self.pageLabel.setText(f'Page {current_page} of {total_pages}')
        if self.prev_button and self.next_button:
            self.prev_button.setEnabled(self.current_document_page_index > 0)
            self.next_button.setEnabled(self.current_document_page_index < total_pages - 1)

    def on_settings_changed(self):
        self._regenerate_document_pages()

    def rotate_current_image(self):
        if not self.document_pages or not (0 <= self.current_document_page_index < len(self.document_pages)):
            return

        current_page_desc = self.document_pages[self.current_document_page_index]

        # Kumpulkan semua gambar pada halaman ini (baik grid maupun n-up)
        image_paths_on_page = []
        if "image_paths" in current_page_desc:
            image_paths_on_page.extend(current_page_desc["image_paths"])
        elif "image_path" in current_page_desc:
            image_paths_on_page.append(current_page_desc["image_path"])

        # Update rotasi di kamus utama untuk setiap gambar unik di halaman ini
        for path in set(image_paths_on_page):
            current_angle = self.image_rotations.get(path, 0)
            self.image_rotations[path] = (current_angle + 90) % 360

        # Regenerasi seluruh dokumen dengan status rotasi yang baru
        self._regenerate_document_pages()

    def on_layout_option_changed(self, current_item, previous_item):
        if not current_item:
            return
        text = current_item.text()
        new_layout_key = "full_page"
        new_photo_print_size_key = None
        if text == 'Full page photo':
            new_layout_key = "full_page"
        elif text in self.dynamic_layout_keys.values():
            new_layout_key = "fixed_size_photo"
            for internal_key, display_text in self.dynamic_layout_keys.items():
                if display_text == text:
                    new_photo_print_size_key = internal_key
                    break
        elif text.startswith("Print size: "):
            new_layout_key = "fixed_size_photo"
            key_part = text.replace("Print size: ", "")
            if key_part in self.photo_print_sizes_mm:
                new_photo_print_size_key = key_part
            else:
                new_layout_key = "full_page"
                new_photo_print_size_key = None
        if self.current_layout_key != new_layout_key or \
           self.current_photo_print_size_key != new_photo_print_size_key:
            self.current_layout_key = new_layout_key
            self.current_photo_print_size_key = new_photo_print_size_key
            self._regenerate_document_pages()

    def get_selected_paper_info(self):
        selected_display_name = self.paperSizeCombo.currentText()
        if not self.no_physical_printer and selected_display_name in self.paper_size_display_map:
            ps = self.paper_size_display_map[selected_display_name]
            size_mm = ps.size(QPageSize.Millimeter)
            return (size_mm.width(), size_mm.height(), ps.key)
        if selected_display_name in self.paper_definitions:
            return self.paper_definitions[selected_display_name]
        if self.paper_definitions:
            return self.paper_definitions.get(list(self.paper_definitions.keys())[0], (210, 297, "A4_paper"))
        return (210, 297, "A4_paper")

    def load_images(self, files):
        self.source_images = []
        failed_files_count = 0
        failed_file_names = []
        for file_path in files:
            img = QImage(file_path)
            if not img.isNull():
                self.source_images.append(file_path)
            else:
                failed_files_count += 1
                failed_file_names.append(file_path)
        current_image_paths_set = set(self.source_images)
        self.image_rotations = {path: angle for path, angle in self.image_rotations.items() if path in current_image_paths_set}
        if failed_files_count > 0:
            QMessageBox.warning(self, "Image Loading Error",
                                f"Failed to load {failed_files_count} image(s):\n{', '.join(failed_file_names)}")
        self._regenerate_document_pages()

    def _regenerate_document_pages(self):
        self.document_pages = []
        if not self.source_images:
            self.update_preview_ui()
            self.update_page_label_ui()
            return

        bg_paper_w_mm, bg_paper_h_mm, _ = self.get_selected_paper_info()
        num_copies = self.copies_spinbox.value()

        # Buat daftar gambar yang perlu ditempatkan
        images_to_place = self.source_images * num_copies

        # Cek apakah layoutnya adalah salah satu dari layout multi-gambar dinamis (2x2, 2x3, dst.)
        is_dynamic_multi_image_layout = (
            self.current_layout_key == "fixed_size_photo"
            and self.current_photo_print_size_key in self.dynamic_layout_keys
        )

        if is_dynamic_multi_image_layout:
            key = self.current_photo_print_size_key
            if key == "paper_div_2_rows":
                cols, rows = 1, 2
            elif key == "paper_div_2x2_grid":
                cols, rows = 2, 2
            elif key == "paper_div_2x3_grid":
                cols, rows = 2, 3
            elif key == "paper_div_3x3_grid":
                cols, rows = 3, 3
            else:
                cols, rows = 1, 1
            max_photos_per_sheet = cols * rows
            photo_w_mm = (bg_paper_w_mm - (cols - 1) * self.PHOTO_GAP_MM) / cols
            photo_h_mm = (bg_paper_h_mm - (rows - 1) * self.PHOTO_GAP_MM) / rows
            
            while images_to_place:
                page_desc = {
                    "type": "multi_image_grid",
                    "image_paths": [],
                    "photo_rects_mm_on_this_sheet": [],
                    "paper_dims_mm": (bg_paper_w_mm, bg_paper_h_mm),
                    "page_image_rotations": []
                }
                images_for_this_page = images_to_place[:max_photos_per_sheet]
                images_to_place = images_to_place[max_photos_per_sheet:]
                page_desc["image_paths"] = images_for_this_page
                
                for r_idx in range(rows):
                    for c_idx in range(cols):
                        img_idx = r_idx * cols + c_idx
                        if img_idx < len(images_for_this_page):
                            x_mm = c_idx * (photo_w_mm + self.PHOTO_GAP_MM)
                            y_mm = r_idx * (photo_h_mm + self.PHOTO_GAP_MM)
                            page_desc["photo_rects_mm_on_this_sheet"].append(QRectF(x_mm, y_mm, photo_w_mm, photo_h_mm))
                            img_path = images_for_this_page[img_idx]
                            page_desc["page_image_rotations"].append(self.image_rotations.get(img_path, 0))
                
                if page_desc["image_paths"]:
                    self.document_pages.append(page_desc)
        
        # Logika baru untuk layout "fixed size photo" (misal 3R, 4R)
        elif self.current_layout_key == "fixed_size_photo" and self.current_photo_print_size_key:
            MAX_COLS = 10
            MAX_ROWS = 10
            MAX_PHOTOS_PER_PAGE = 50
            while images_to_place:
                page_desc = {
                    "type": "n_up_on_page",
                    "image_path": None,
                    "photo_dims_mm": None,
                    "paper_dims_mm": (bg_paper_w_mm, bg_paper_h_mm),
                    "photo_rects_mm_on_this_sheet": [],
                    "image_paths": [],
                    "page_image_rotations": []
                }

                current_image_index = 0
                # Hitung ukuran foto
                base_w, base_h = self.photo_print_sizes_mm.get(self.current_photo_print_size_key, (0, 0))
                # Gunakan rotasi gambar pertama (atau 0)
                angle = 0
                if images_to_place:
                    angle = self.image_rotations.get(images_to_place[0], 0)
                photo_w, photo_h = (base_h, base_w) if angle in [90, 270] else (base_w, base_h)
                if photo_w <= 0 or photo_h <= 0:
                    break

                # Batasi jumlah kolom/baris agar tidak terlalu besar
                cols = min(int((bg_paper_w_mm + self.PHOTO_GAP_MM) / (photo_w + self.PHOTO_GAP_MM)), MAX_COLS)
                rows = min(int((bg_paper_h_mm + self.PHOTO_GAP_MM) / (photo_h + self.PHOTO_GAP_MM)), MAX_ROWS)
                if cols * rows == 0:
                    break

                max_photos_on_page = min(cols * rows, MAX_PHOTOS_PER_PAGE)
                for placed_count_on_page in range(max_photos_on_page):
                    if current_image_index >= len(images_to_place):
                        break
                    c = placed_count_on_page % cols
                    r = placed_count_on_page // cols
                    if r >= rows:
                        break
                    x = c * (photo_w + self.PHOTO_GAP_MM)
                    y = r * (photo_h + self.PHOTO_GAP_MM)
                    img_path = images_to_place[current_image_index]
                    angle = self.image_rotations.get(img_path, 0)
                    page_desc["photo_rects_mm_on_this_sheet"].append(QRectF(x, y, photo_w, photo_h))
                    page_desc["image_paths"].append(img_path)
                    page_desc["page_image_rotations"].append(angle)
                    current_image_index += 1

                if page_desc["image_paths"]:
                    self.document_pages.append(page_desc)
                images_to_place = images_to_place[current_image_index:]

        # Logika untuk layout "full page"
        else: # self.current_layout_key == "full_page"
            for image_path in self.source_images:
                for _ in range(num_copies):
                    self.document_pages.append({
                        "type": "single_image_on_page",
                        "image_path": image_path,
                        "photo_rect_mm": QRectF(0, 0, bg_paper_w_mm, bg_paper_h_mm),
                        "paper_dims_mm": (bg_paper_w_mm, bg_paper_h_mm),
                        "page_image_rotations": [self.image_rotations.get(image_path, 0)]
                    })
        
        self.current_document_page_index = min(max(0, self.current_document_page_index), len(self.document_pages) - 1)
        self.update_preview_ui()
        self.update_page_label_ui()

    def update_preview_ui(self):
        if not hasattr(self, "imagePreview") or self.imagePreview is None:
            return
        if not self.document_pages or not (0 <= self.current_document_page_index < len(self.document_pages)):
            self.imagePreview.clear()
            self.imagePreview.setText("No page to display")
            return
        page_desc = self.document_pages[self.current_document_page_index]
        bg_w, bg_h = page_desc["paper_dims_mm"]
        if bg_h <= 0:
            return
        preview_w, preview_h = self.imagePreview.width() - 2, self.imagePreview.height() - 2
        if preview_w <= 0 or preview_h <= 0:
            return
        page_w, page_h = (preview_w, int(preview_w * bg_h / bg_w))
        if page_h > preview_h:
            page_w, page_h = (int(preview_h * bg_w / bg_h), preview_h)
        pixmap = QPixmap(max(1, page_w), max(1, page_h))
        pixmap.fill(Qt.white)
        painter = QPainter(pixmap)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        px_per_mm = page_w / bg_w if bg_w > 0 else 1.0
        rects_px, img_paths = [], []
        rotations = []
        if page_desc["type"] == "single_image_on_page":
            r_mm = page_desc["photo_rect_mm"]
            rects_px.append(QRect(int(r_mm.x() * px_per_mm), int(r_mm.y() * px_per_mm), int(r_mm.width() * px_per_mm), int(r_mm.height() * px_per_mm)))
            img_paths.append(page_desc["image_path"])
            rotations = page_desc.get("page_image_rotations", [0])
        elif page_desc["type"] == "n_up_on_page":
            for r_mm in page_desc["photo_rects_mm_on_this_sheet"]:
                rects_px.append(QRect(int(r_mm.x() * px_per_mm), int(r_mm.y() * px_per_mm), int(r_mm.width() * px_per_mm), int(r_mm.height() * px_per_mm)))
            # Use image_paths and page_image_rotations for n_up_on_page
            img_paths = page_desc.get("image_paths", [page_desc.get("image_path")] * len(rects_px))
            rotations = page_desc.get("page_image_rotations", [0] * len(rects_px))
        elif page_desc["type"] == "multi_image_grid":
            for r_mm in page_desc["photo_rects_mm_on_this_sheet"]:
                rects_px.append(QRect(int(r_mm.x() * px_per_mm), int(r_mm.y() * px_per_mm), int(r_mm.width() * px_per_mm), int(r_mm.height() * px_per_mm)))
            img_paths = page_desc["image_paths"]
            rotations = page_desc.get("page_image_rotations", [0] * len(img_paths))
        self.draw_image_layout(painter, img_paths, rects_px, rotations)
        painter.end()
        self.imagePreview.setPixmap(pixmap)

    def draw_image_layout(self, painter, img_paths, rects_in_pixels, rotations=None):
        if rotations is None:
            rotations = [0] * len(img_paths)
        for i, target_rect in enumerate(rects_in_pixels):
            if target_rect.width() <= 0 or target_rect.height() <= 0:
                continue
            img_path = img_paths[i] if i < len(img_paths) else None
            if not img_path:
                continue
            source_img = QImage(img_path)
            if source_img.isNull():
                painter.fillRect(target_rect, Qt.lightGray)
                painter.drawText(target_rect, Qt.AlignCenter, "Error")
                continue
            angle = rotations[i] if i < len(rotations) else 0
            # Konversi ke QPixmap agar transformasi rotasi dan scaling konsisten
            pixmap = QPixmap.fromImage(source_img)
            if angle != 0:
                transform = QTransform().rotate(angle)
                pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
            mode_text = self.scaling_mode_combo.currentText()
            aspect_mode = Qt.KeepAspectRatioByExpanding if mode_text == "Crop" else \
                          Qt.IgnoreAspectRatio if mode_text == "Stretch" else Qt.KeepAspectRatio
            scaled_pixmap = pixmap.scaled(target_rect.size(), aspect_mode, Qt.SmoothTransformation)
            draw_x = target_rect.x() + (target_rect.width() - scaled_pixmap.width()) / 2
            draw_y = target_rect.y() + (target_rect.height() - scaled_pixmap.height()) / 2
            painter.save()
            painter.setClipRect(target_rect)
            painter.drawPixmap(int(draw_x), int(draw_y), scaled_pixmap)
            painter.restore()

    def on_printer_changed(self):
        # Save selected printer to settings
        self.settings.setValue("last_printer", self.printerCombo.currentText())

    def on_paper_size_changed(self):
        # Save selected paper size to settings
        self.settings.setValue("last_paper_size", self.paperSizeCombo.currentText())
        self.on_settings_changed()

    def print_images(self):
        if not self.document_pages:
            QMessageBox.information(self, "Print", "No pages to print.")
            return

        # Cek apakah ukuran foto lebih besar dari ukuran kertas
        bg_paper_w_mm, bg_paper_h_mm, _ = self.get_selected_paper_info()
        if self.current_layout_key == "fixed_size_photo" and self.current_photo_print_size_key:
            base_w, base_h = self.photo_print_sizes_mm.get(self.current_photo_print_size_key, (0, 0))
            # Periksa rotasi
            angle = 0
            if self.source_images:
                angle = self.image_rotations.get(self.source_images[0], 0)
            photo_w, photo_h = (base_h, base_w) if angle in [90, 270] else (base_w, base_h)
            if photo_w > bg_paper_w_mm or photo_h > bg_paper_h_mm:
                QMessageBox.warning(self, "Paper Size Warning",
                    f"Selected photo size ({photo_w} x {photo_h} mm) is larger than paper size ({bg_paper_w_mm} x {bg_paper_h_mm} mm).\n"
                    "Please select a larger paper or a smaller photo size.")
                return

        # Save selected printer before printing
        self.settings.setValue("last_printer", self.printerCombo.currentText())

        printer = QPrinter()
        if self.printerCombo.currentText() == "Save as PDF":
            printer.setOutputFormat(QPrinter.PdfFormat)
            filePath, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF files (*.pdf)")
            if not filePath:
                return
            if not filePath.lower().endswith(".pdf"):
                filePath += ".pdf"
            printer.setOutputFileName(filePath)
        else:
            printer.setPrinterName(self.printerCombo.currentText())
            dialog = QPrintDialog(printer, self)
            if dialog.exec() != QPrintDialog.Accepted:
                return

        selected_paper_display = self.paperSizeCombo.currentText()
        if selected_paper_display in self.paper_size_display_map:
            printer.setPageSize(self.paper_size_display_map[selected_paper_display])
        
        printer.setPageOrientation(QPageLayout.Portrait)
        
        painter = QPainter()
        if not painter.begin(printer):
            QMessageBox.critical(self, "Print Error", "Failed to start painter on printer.")
            return

        dpi = printer.resolution()
        px_per_mm = dpi / 25.4
        
        for page_idx, page_desc in enumerate(self.document_pages):
            if page_idx > 0 and not printer.newPage():
                QMessageBox.critical(self, "Print Error", "Failed to create new page.")
                painter.end()
                return

            rects_px, img_paths = [], []
            rotations = []

            if page_desc["type"] == "single_image_on_page":
                r_mm = page_desc["photo_rect_mm"]
                rects_px.append(QRectF(r_mm.x() * px_per_mm, r_mm.y() * px_per_mm, r_mm.width() * px_per_mm, r_mm.height() * px_per_mm).toRect())
                img_paths.append(page_desc["image_path"])
                rotations = page_desc.get("page_image_rotations", [0])
            elif page_desc["type"] in ["n_up_on_page", "multi_image_grid"]:
                for r_mm in page_desc["photo_rects_mm_on_this_sheet"]:
                    rect_px = QRectF(r_mm.x() * px_per_mm, r_mm.y() * px_per_mm, r_mm.width() * px_per_mm, r_mm.height() * px_per_mm).toRect()
                    rects_px.append(rect_px)
                if page_desc["type"] == "n_up_on_page":
                    img_paths = page_desc.get("image_paths", [page_desc.get("image_path")] * len(rects_px))
                    rotations = page_desc.get("page_image_rotations", [0]*len(rects_px))
                else: # multi_image_grid
                    img_paths = page_desc["image_paths"]
                    rotations = page_desc.get("page_image_rotations", [0]*len(img_paths))
            
            self.draw_image_layout(painter, img_paths, rects_px, rotations)
        painter.end()

    def closeEvent(self, event):
        # Save selected printer when closing
        self.settings.setValue("last_printer", self.printerCombo.currentText())
        # Save selected paper size when closing
        self.settings.setValue("last_paper_size", self.paperSizeCombo.currentText())
        super().closeEvent(event)

    def navigate_previous_page(self):
        if self.current_document_page_index > 0:
            self.current_document_page_index -= 1
            self.update_preview_ui()
            self.update_page_label_ui()

    def navigate_next_page(self):
        if self.current_document_page_index < len(self.document_pages) - 1:
            self.current_document_page_index += 1
            self.update_preview_ui()
            self.update_page_label_ui()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    image_files = sys.argv[1:]
    if not image_files:
        image_files, _ = QFileDialog.getOpenFileNames(
            None,
            "Select Images",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff *.svg *.ico *.ppm *.pgm *.pbm *.xbm *.xpm)"
        )
    window = PrintImage(image_files)
    window.show()
    window.center()
    sys.exit(app.exec())
