#!/usr/bin/env python3
import sys
import math
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QComboBox,
                               QFileDialog, QSpinBox, QVBoxLayout, QHBoxLayout,
                               QFrame, QSizePolicy, QListWidgetItem,
                               QMessageBox, QListWidget)
from PySide6.QtGui import QPixmap, QPainter, QImage, QTransform, QPageSize, QPageLayout
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrinterInfo
from PySide6.QtCore import Qt, QRect, QRectF, QSizeF

class PhotoPrintApp(QWidget):
    PHOTO_GAP_MM = 2 # Jarak antar foto dalam mm

    def __init__(self, image_files):
        super().__init__()
        self.setWindowTitle("Print Pictures")
        self.setGeometry(100, 100, 700, 600)

        self.source_images = []
        self.document_pages = [] 
        self.current_document_page_index = 0
        self.image_rotations = {} 

        self.current_layout_key = "full_page" 
        self.current_photo_print_size_key = None 

        self.no_physical_printer = False 

        self.paper_definitions = {
            "A4 (210 x 297 mm)": (210, 297, "A4_paper"),
            "F4 (210 x 330 mm)": (210, 330, "F4_paper"),
        }
        
        # Kamus ukuran foto dalam Bahasa Inggris untuk kejelasan
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

        # Initialize navigation buttons to None to avoid AttributeError
        self.prev_button = None
        self.next_button = None

        self.initUI()

       

        if image_files:
            self.load_images(image_files)
        else:
            self._regenerate_document_pages()

        if self.optionsList.count() > 0:
            self.optionsList.setCurrentRow(0)

    def initUI(self):
        mainLayout = QVBoxLayout()

        # --- Ensure pageLabel is created early ---
        self.pageLabel = QLabel('Page 0 of 0')
        self.pageLabel.setAlignment(Qt.AlignCenter)

        settingsLayout = QHBoxLayout()
        settingsLayout.addWidget(QLabel('Printer:'))
        self.printerCombo = QComboBox()
        # Always add "Save as PDF" as the first option
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

        # Set default selection to real printer if available, otherwise "Save as PDF"
        if default_printer_name:
            idx = self.printerCombo.findText(default_printer_name)
            if idx != -1:
                self.printerCombo.setCurrentIndex(idx)
            else:
                self.printerCombo.setCurrentIndex(0)
        else:
            self.printerCombo.setCurrentIndex(0)

        # Paper size combo: ambil dari printer asli jika ada
        self.paperSizeCombo = QComboBox()
        self.paper_size_display_map = {}
        allowed_paper_names = {"A4", "A5", "Letter"}  # Tambahkan yang umum saja

        # --- Tambahkan semua ukuran kertas dari printer default, urutkan berdasarkan nama ---
        default_printer_info = QPrinterInfo.defaultPrinter()
        if not self.no_physical_printer and not default_printer_info.isNull():
            supported_sizes = default_printer_info.supportedPageSizes()
            # Urutkan berdasarkan nama (a-z)
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
            # Tambahkan F4 manual jika ingin
            self.paperSizeCombo.addItem("F4 (210 x 330 mm)")
            for display_name in self.paper_definitions.keys():
                if display_name != "F4 (210 x 330 mm)":
                    self.paperSizeCombo.addItem(display_name)
        self.paperSizeCombo.currentIndexChanged.connect(self.on_settings_changed)
        settingsLayout.addWidget(QLabel('Paper size:'))
        settingsLayout.addWidget(self.paperSizeCombo)
        # Set default ke A4 jika ada
        idx_a4 = -1
        # Cari item yang mengandung "A4" (case-insensitive)
        for i in range(self.paperSizeCombo.count()):
            if "a4" in self.paperSizeCombo.itemText(i).lower():
                idx_a4 = i
                break
        if idx_a4 != -1:
            self.paperSizeCombo.setCurrentIndex(idx_a4)

        # Quality combo: tampilkan pilihan sederhana dan jelas
        self.qualityCombo = QComboBox()
        # Pilihan kualitas umum, urut dari kualitas tertinggi ke terendah
        self.qualityCombo.addItems([
            'Photo (1200 dpi)', 'High (600 dpi)', 'Standard (300 dpi)', 'Draft (150 dpi)'
        ])
        self.qualityCombo.setCurrentIndex(2)  # Default ke Standard
        settingsLayout.addWidget(QLabel('Quality:'))
        settingsLayout.addWidget(self.qualityCombo)

        # --- Tambahkan Paper Type ---
        self.paperTypeCombo = QComboBox()
        self.paperTypeCombo.addItems([
            "Plain", "Glossy", "Matte"
        ])
        self.paperTypeCombo.setCurrentText("Plain")
        settingsLayout.addWidget(QLabel('Paper type:'))
        settingsLayout.addWidget(self.paperTypeCombo)
        # --- End Paper Type ---

        # Simpan mapping tipe kertas ke QPrinter.PaperSource jika ingin digunakan
        # Gunakan QPrinter.PaperSource enum, import jika perlu
        from PySide6.QtPrintSupport import QPrinter
        self.paper_type_map = {
            "Plain": QPrinter.PaperSource.Auto,
            "Glossy": QPrinter.PaperSource.Auto,
            "Envelope": QPrinter.PaperSource.Envelope
        }

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
        self.prev_button = QPushButton("< Previous")
        self.prev_button.clicked.connect(self.navigate_previous_page)
        navLayout.addWidget(self.prev_button)

        # self.pageLabel is already created above, just add it here
        navLayout.addWidget(self.pageLabel, 1)

        self.next_button = QPushButton("Next >")
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
        
        self.optionsList.setMinimumWidth(280)  # Lebar minimum agar list lebih lebar
        self.optionsList.setMaximumWidth(500)  # Lebar maksimum agar tidak terlalu besar
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
            "Crop image to fill frame",
            "Fit picture to frame",
            "Stretch to fill frame"
        ])
        # Set default ke "Fit picture to frame"
        self.scaling_mode_combo.setCurrentText("Fit picture to frame")
        self.scaling_mode_combo.currentIndexChanged.connect(self.on_settings_changed)
        bottomLayout.addWidget(self.scaling_mode_combo)

        self.rotate_button = QPushButton("Rotate 90°")
        self.rotate_button.clicked.connect(self.rotate_current_image)
        bottomLayout.addWidget(self.rotate_button)

        bottomLayout.addStretch()
        self.print_button = QPushButton("Print")
        self.print_button.clicked.connect(self.print_images)
        bottomLayout.addWidget(self.print_button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close)
        bottomLayout.addWidget(self.cancel_button)
        mainLayout.addLayout(bottomLayout)
        self.setLayout(mainLayout)

    def center(self):
        # Center the window on the screen (both horizontally and vertically)
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())

    def on_settings_changed(self):
        self._regenerate_document_pages()

    def rotate_current_image(self):
        if not self.document_pages or not (0 <= self.current_document_page_index < len(self.document_pages)):
            return

        current_page_desc = self.document_pages[self.current_document_page_index]
        image_path = current_page_desc.get("image_path")

        if image_path:
            current_angle = self.image_rotations.get(image_path, 0)
            new_angle = (current_angle + 90) % 360
            self.image_rotations[image_path] = new_angle
            self._regenerate_document_pages()

    def on_layout_option_changed(self, current_item, previous_item):
        if not current_item: return
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
        # Jika printer asli, ambil ukuran dari PageSize object
        if not self.no_physical_printer and selected_display_name in self.paper_size_display_map:
            ps = self.paper_size_display_map[selected_display_name]
            size_mm = ps.size(QPageSize.Millimeter)  # gunakan QPageSize.Millimeter
            return (size_mm.width(), size_mm.height(), ps.key)
        # PDF/fallback
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
                failed_files_count +=1
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
        num_copies_per_original_image = self.copies_spinbox.value()

        for image_path in self.source_images:
            if self.current_layout_key == "full_page":
                for _ in range(num_copies_per_original_image):
                    page_desc = {
                        "type": "single_image_on_page",
                        "image_path": image_path,
                        "photo_rect_mm": QRectF(0, 0, bg_paper_w_mm, bg_paper_h_mm),
                        "paper_dims_mm": (bg_paper_w_mm, bg_paper_h_mm)
                    }
                    self.document_pages.append(page_desc)

            elif self.current_layout_key == "fixed_size_photo" and self.current_photo_print_size_key:
                base_target_w_mm, base_target_h_mm = 0, 0
                is_dynamic_paper_division_layout = False 

                if self.current_photo_print_size_key in self.dynamic_layout_keys:
                    is_dynamic_paper_division_layout = True
                    if self.current_photo_print_size_key == "paper_div_2_rows":
                        cols, rows = 1, 2
                    elif self.current_photo_print_size_key == "paper_div_2x2_grid":
                        cols, rows = 2, 2
                    elif self.current_photo_print_size_key == "paper_div_2x3_grid":
                        cols, rows = 2, 3
                    elif self.current_photo_print_size_key == "paper_div_3x3_grid":
                        cols, rows = 3, 3
                    base_target_w_mm = (bg_paper_w_mm - (cols - 1) * self.PHOTO_GAP_MM) / cols
                    base_target_h_mm = (bg_paper_h_mm - (rows - 1) * self.PHOTO_GAP_MM) / rows

                elif self.current_photo_print_size_key in self.photo_print_sizes_mm:
                    base_target_w_mm, base_target_h_mm = self.photo_print_sizes_mm[self.current_photo_print_size_key]
                else: 
                    print(f"Error: Unknown photo print size key: {self.current_photo_print_size_key}")
                    continue 
                
                current_w_mm, current_h_mm = base_target_w_mm, base_target_h_mm
                
                angle = self.image_rotations.get(image_path, 0)
                # --- DIUBAH: Hanya tukar dimensi placeholder untuk ukuran cetak tetap, bukan untuk layout dinamis ---
                if (angle == 90 or angle == 270) and not is_dynamic_paper_division_layout:
                    current_w_mm, current_h_mm = base_target_h_mm, base_target_w_mm 

                if current_w_mm <= 0 or current_h_mm <= 0: continue

                cols_fit, rows_fit = 0, 0
                item_w_for_calc = current_w_mm + self.PHOTO_GAP_MM
                if current_w_mm > 0 and item_w_for_calc > 0:
                    cols_fit = int((bg_paper_w_mm + self.PHOTO_GAP_MM) // item_w_for_calc)
                elif current_w_mm > 0 and current_w_mm <= bg_paper_w_mm : cols_fit = 1

                item_h_for_calc = current_h_mm + self.PHOTO_GAP_MM
                if current_h_mm > 0 and item_h_for_calc > 0:
                    rows_fit = int((bg_paper_h_mm + self.PHOTO_GAP_MM) // item_h_for_calc)
                elif current_h_mm > 0 and current_h_mm <= bg_paper_h_mm: rows_fit = 1
                
                cols_fit = max(0, cols_fit)
                rows_fit = max(0, rows_fit)
                
                if is_dynamic_paper_division_layout:
                    if self.current_photo_print_size_key == "paper_div_2_rows":
                        cols_fit, rows_fit = 1, 2
                    elif self.current_photo_print_size_key == "paper_div_2x2_grid":
                        cols_fit, rows_fit = 2, 2
                    elif self.current_photo_print_size_key == "paper_div_2x3_grid":
                        cols_fit, rows_fit = 2, 3
                    elif self.current_photo_print_size_key == "paper_div_3x3_grid":
                        cols_fit, rows_fit = 3, 3
                
                max_photos_per_sheet = cols_fit * rows_fit
                if max_photos_per_sheet <= 0: continue

                if max_photos_per_sheet > 0:
                    prints_placed_for_this_image = 0
                    while prints_placed_for_this_image < num_copies_per_original_image:
                        page_desc = {
                            "type": "n_up_on_page",
                            "image_path": image_path,
                            "photo_dims_mm": (current_w_mm, current_h_mm),
                            "paper_dims_mm": (bg_paper_w_mm, bg_paper_h_mm),
                            "photo_rects_mm_on_this_sheet": []
                        }
                        current_sheet_photo_count = 0
                        for r_idx in range(rows_fit):
                            for c_idx in range(cols_fit):
                                if prints_placed_for_this_image < num_copies_per_original_image:
                                    x_mm = c_idx * (current_w_mm + self.PHOTO_GAP_MM)
                                    y_mm = r_idx * (current_h_mm + self.PHOTO_GAP_MM)
                                    
                                    if x_mm + current_w_mm <= bg_paper_w_mm + 0.1 and \
                                       y_mm + current_h_mm <= bg_paper_h_mm + 0.1: 
                                        page_desc["photo_rects_mm_on_this_sheet"].append(
                                            QRectF(x_mm, y_mm, current_w_mm, current_h_mm)
                                        )
                                        prints_placed_for_this_image += 1
                                        current_sheet_photo_count +=1
                                else: break
                            if prints_placed_for_this_image >= num_copies_per_original_image: break

                        if current_sheet_photo_count > 0:
                            self.document_pages.append(page_desc)
                        elif prints_placed_for_this_image < num_copies_per_original_image:
                            for _i_fallback in range(num_copies_per_original_image - prints_placed_for_this_image):
                                x_offset_mm = (bg_paper_w_mm - current_w_mm) / 2.0
                                y_offset_mm = (bg_paper_h_mm - current_h_mm) / 2.0
                                fallback_page_desc = {
                                    "type": "single_image_on_page", 
                                    "image_path": image_path,
                                    "photo_rect_mm": QRectF(max(0, x_offset_mm), max(0, y_offset_mm), current_w_mm, current_h_mm),
                                    "paper_dims_mm": (bg_paper_w_mm, bg_paper_h_mm)
                                }
                                self.document_pages.append(fallback_page_desc)
                            prints_placed_for_this_image = num_copies_per_original_image
                            break 
                else: 
                    for _ in range(num_copies_per_original_image):
                        x_offset_mm = (bg_paper_w_mm - current_w_mm) / 2.0
                        y_offset_mm = (bg_paper_h_mm - current_h_mm) / 2.0
                        page_desc = {
                            "type": "single_image_on_page",
                            "image_path": image_path,
                            "photo_rect_mm": QRectF(max(0, x_offset_mm), max(0, y_offset_mm), current_w_mm, current_h_mm),
                            "paper_dims_mm": (bg_paper_w_mm, bg_paper_h_mm)
                        }
                        self.document_pages.append(page_desc)

        if not self.document_pages:
            self.current_document_page_index = 0
        else:
            self.current_document_page_index = min(self.current_document_page_index, len(self.document_pages) - 1)
            self.current_document_page_index = max(0, self.current_document_page_index)

        self.update_preview_ui()
        self.update_page_label_ui()

    def navigate_previous_page(self):
        if self.current_document_page_index > 0:
            self.current_document_page_index -= 1
            self.update_preview_ui()
            self.update_page_label_ui()

    def navigate_next_page(self):
        if self.current_document_page_index + 1 < len(self.document_pages):
            self.current_document_page_index += 1
            self.update_preview_ui()
            self.update_page_label_ui()

    def update_page_label_ui(self):
        total_doc_pages = len(self.document_pages)
        if total_doc_pages == 0:
            self.pageLabel.setText("Page 0 of 0")
            current_display_page = 0
        else:
            current_display_page = self.current_document_page_index + 1
            self.pageLabel.setText(f"Page {current_display_page} of {total_doc_pages}")

        # Only set enabled if buttons exist
        if self.prev_button is not None:
            self.prev_button.setEnabled(current_display_page > 1)
        if self.next_button is not None:
            self.next_button.setEnabled(current_display_page < total_doc_pages)
        self.print_button.setEnabled(total_doc_pages > 0)
        self.rotate_button.setEnabled(total_doc_pages > 0)

    def update_preview_ui(self):
        # Tambahkan proteksi jika self.imagePreview belum ada
        if not hasattr(self, "imagePreview") or self.imagePreview is None:
            return

        if not self.document_pages or not (0 <= self.current_document_page_index < len(self.document_pages)):
            self.imagePreview.clear()
            self.imagePreview.setText("No page to display")
            return

        page_desc = self.document_pages[self.current_document_page_index]
        bg_paper_w_mm, bg_paper_h_mm = page_desc["paper_dims_mm"]
        aspect_ratio_bg_paper = bg_paper_w_mm / bg_paper_h_mm if bg_paper_h_mm > 0 else 1.0

        preview_area_width = self.imagePreview.width() - 2
        preview_area_height = self.imagePreview.height() - 2

        if preview_area_width <=0 or preview_area_height <=0:
            self.imagePreview.clear()
            self.imagePreview.setText("Preview area too small.")
            return

        page_w_on_pixmap, page_h_on_pixmap = 1, 1
        preview_aspect_ratio = preview_area_width / preview_area_height
        if aspect_ratio_bg_paper > preview_aspect_ratio :
            page_w_on_pixmap = preview_area_width
            page_h_on_pixmap = int(page_w_on_pixmap / aspect_ratio_bg_paper) if aspect_ratio_bg_paper > 0 else preview_area_height
        else:
            page_h_on_pixmap = preview_area_height
            page_w_on_pixmap = int(page_h_on_pixmap * aspect_ratio_bg_paper)

        page_w_on_pixmap = max(1, page_w_on_pixmap)
        page_h_on_pixmap = max(1, page_h_on_pixmap)

        preview_pixmap = QPixmap(page_w_on_pixmap, page_h_on_pixmap)
        preview_pixmap.fill(Qt.white)
        painter = QPainter(preview_pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        pixels_per_mm_preview = page_w_on_pixmap / bg_paper_w_mm if bg_paper_w_mm > 0 else 1.0

        images_to_draw_on_preview = []
        rects_on_preview_pixmap = []

        if page_desc["type"] == "single_image_on_page":
            images_to_draw_on_preview.append(page_desc["image_path"])
            rect_mm = page_desc["photo_rect_mm"]
            rect_px = QRect(
                int(rect_mm.x() * pixels_per_mm_preview), 
                int(rect_mm.y() * pixels_per_mm_preview),
                int(rect_mm.width() * pixels_per_mm_preview), 
                int(rect_mm.height() * pixels_per_mm_preview)
            )
            rects_on_preview_pixmap.append(rect_px)
        elif page_desc["type"] == "n_up_on_page":
            for rect_mm in page_desc["photo_rects_mm_on_this_sheet"]:
                images_to_draw_on_preview.append(page_desc["image_path"])
                rect_px = QRect(
                    int(rect_mm.x() * pixels_per_mm_preview), 
                    int(rect_mm.y() * pixels_per_mm_preview),
                    int(rect_mm.width() * pixels_per_mm_preview), 
                    int(rect_mm.height() * pixels_per_mm_preview)
                )
                rects_on_preview_pixmap.append(rect_px)

        self.draw_image_layout(painter, images_to_draw_on_preview, rects_on_preview_pixmap)
        painter.end()
        self.imagePreview.setPixmap(preview_pixmap)

    def draw_image_layout(self, painter, img_paths, rects_in_pixels):
        for i in range(len(rects_in_pixels)):
            target_rect = rects_in_pixels[i]
            if target_rect.width() <= 0 or target_rect.height() <= 0: continue

            if i < len(img_paths):
                img_path = img_paths[i]
                if not img_path: continue
                
                source_img = QImage(img_path)
                if source_img.isNull():
                    painter.fillRect(target_rect, Qt.lightGray)
                    painter.drawText(target_rect, Qt.AlignCenter, "Error loading image")
                    continue

                angle = self.image_rotations.get(img_path, 0)
                img_to_scale = source_img
                if angle != 0:
                    transform = QTransform().rotate(angle)
                    img_to_scale = source_img.transformed(transform, Qt.SmoothTransformation)
                
                scaled_img = None
                current_scaling_mode = self.scaling_mode_combo.currentText()
                
                if current_scaling_mode == "Crop image to fill frame":
                    scaled_img = img_to_scale.scaled(target_rect.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                elif current_scaling_mode == "Fit picture to frame":
                    scaled_img = img_to_scale.scaled(target_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                elif current_scaling_mode == "Stretch to fill frame":
                    scaled_img = img_to_scale.scaled(target_rect.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                else: 
                    scaled_img = img_to_scale.scaled(target_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

                draw_x = target_rect.x() + (target_rect.width() - scaled_img.width()) / 2.0
                draw_y = target_rect.y() + (target_rect.height() - scaled_img.height()) / 2.0

                painter.save()
                painter.setClipRect(target_rect)
                painter.drawImage(QRectF(draw_x, draw_y, scaled_img.width(), scaled_img.height()), scaled_img)
                painter.restore()
            else:
                painter.fillRect(target_rect, Qt.gainsboro)
                painter.drawText(target_rect, Qt.AlignCenter, "Empty Slot")


    def print_images(self):
        if not self.document_pages:
            QMessageBox.information(self, "Print", "No pages to print.")
            return

        printer = QPrinter()
        if self.no_physical_printer and self.printerCombo.currentText() == "Save as PDF":
            printer.setOutputFormat(QPrinter.PdfFormat)
            filePath, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF files (*.pdf)")
            if not filePath: return
            if not filePath.lower().endswith(".pdf"): filePath += ".pdf"
            printer.setOutputFileName(filePath)
        else:
            printer.setPrinterName(self.printerCombo.currentText())
            printDialog = QPrintDialog(printer, self)
            if printDialog.exec() != QPrintDialog.Accepted: return

        printer.setCopyCount(1)

        # Ambil ukuran kertas dari printer asli
        rect = printer.pageRect(QPrinter.Millimeter)
        bg_paper_w_mm_print = rect.width()
        bg_paper_h_mm_print = rect.height()
        paper_info_for_print = self.get_selected_paper_info()
        _, _, bg_paper_key_print = paper_info_for_print

        # FIX: Call bg_paper_key_print if it's a method
        if callable(bg_paper_key_print):
            bg_paper_key_print = bg_paper_key_print()

        simple_key = bg_paper_key_print.replace("_paper","")
        # Ganti mapping ke QPageSize
        paper_size_map = {
            "A4": QPageSize.A4,
            "A3": QPageSize.A3,
            "A5": QPageSize.A5,
            "B5": QPageSize.B5,
            "Letter": QPageSize.Letter,
        }
        qt_paper_size = paper_size_map.get(simple_key, None)

        # Paper size dari combo box (jika printer asli)
        if not self.no_physical_printer:
            selected_paper_size = self.paperSizeCombo.currentText()
            try:
                if selected_paper_size in self.paper_size_display_map:
                    printer.setPageSize(self.paper_size_display_map[selected_paper_size])
            except Exception:
                pass
            rect = printer.pageRect(QPrinter.Millimeter)
            bg_paper_w_mm_print = rect.width()
            bg_paper_h_mm_print = rect.height()
        else:
            # ...existing code untuk PDF...
            pass

        # Ganti orientasi kertas
        printer.setPageOrientation(QPageLayout.Portrait)

        # Quality dari combo box (jika printer asli)
        quality_str = self.qualityCombo.currentText()
        try:
            printer.setResolution(int(quality_str))
        except Exception:
            # fallback
            if quality_str == 'High': printer.setResolution(QPrinter.HighResolution)
            elif quality_str == 'Standard': printer.setResolution(300)
            elif quality_str == 'Draft': printer.setResolution(150)

        # Set paper source dari combo box jika ada
        selected_paper_type = self.paperTypeCombo.currentText()
        if selected_paper_type in self.paper_type_map:
            try:
                printer.setPaperSource(self.paper_type_map[selected_paper_type])
            except Exception:
                pass

        painter = QPainter()
        if not painter.begin(printer):
            QMessageBox.critical(self, "Print Error", "Failed to start painter on printer.")
            return

        dpi = printer.resolution() 
        mm_to_inch = 1.0 / 25.4
        pixels_per_mm_printer = dpi * mm_to_inch

        for page_idx, page_desc in enumerate(self.document_pages):
            if page_idx > 0:
                if not printer.newPage():
                    QMessageBox.critical(self, "Print Error", "Failed to create new page on printer.")
                    painter.end()
                    return

            images_on_this_physical_sheet = []
            rects_for_this_physical_sheet_px = []

            if page_desc["type"] == "single_image_on_page":
                images_on_this_physical_sheet.append(page_desc["image_path"])
                rect_mm = page_desc["photo_rect_mm"]
                rect_px = QRectF( 
                    rect_mm.x() * pixels_per_mm_printer, rect_mm.y() * pixels_per_mm_printer,
                    rect_mm.width() * pixels_per_mm_printer, rect_mm.height() * pixels_per_mm_printer
                ).toRect()
                rects_for_this_physical_sheet_px.append(rect_px)
            elif page_desc["type"] == "n_up_on_page":
                for rect_mm in page_desc["photo_rects_mm_on_this_sheet"]:
                    images_on_this_physical_sheet.append(page_desc["image_path"])
                    rect_px = QRectF(
                        rect_mm.x() * pixels_per_mm_printer, rect_mm.y() * pixels_per_mm_printer,
                        rect_mm.width() * pixels_per_mm_printer, rect_mm.height() * pixels_per_mm_printer
                    ).toRect()
                    rects_for_this_physical_sheet_px.append(rect_px)

            self.draw_image_layout(painter, images_on_this_physical_sheet, rects_for_this_physical_sheet_px)

        painter.end()
        # Removed QMessageBox.information(self, "Print", "Printing finished (or saved to PDF).")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    image_files_arg = sys.argv[1:]
    initial_files_to_load = []
    if image_files_arg:
        initial_files_to_load = image_files_arg
    else:
        selected_files, _ = QFileDialog.getOpenFileNames(
            None,
            "Select Images",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff *.svg *.ico *.ppm *.pgm *.pbm *.xbm *.xpm)"
        )
        if selected_files:
            initial_files_to_load = selected_files

    window = PhotoPrintApp(initial_files_to_load)
    window.show()
    window.center()  # Tambahkan baris ini agar window berada di tengah
    sys.exit(app.exec())
