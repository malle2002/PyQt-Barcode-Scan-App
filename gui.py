import sys
import json
import cv2
import requests
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, 
    QLineEdit, QFormLayout, QDialog, QMessageBox, QFileDialog
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from pyzbar.pyzbar import decode
from product_operations import fetch_product, add_product_to_db
import pandas as pd
from product_operations import fetch_all_products_from_neo4j

class HyperlinkLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__()
        self.setStyleSheet('font-size: 35px')
        self.setOpenExternalLinks(True)
        self.setParent(parent)

class ProductForm(QDialog):
    """Dialog form to manually enter product details if not found."""
    
    def __init__(self, barcode, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual Product Entry")
        self.setGeometry(300, 300, 400, 500)
        
        self.layout = QVBoxLayout()
        self.fields = {}
        self.barcode = barcode

        form_layout = QFormLayout()
        
        # List of fields to add (all optional)
        field_names = [
            "title", "category", "manufacturer", "brand", "mpn", "model", 
            "asin", "ingredients", "nutrition_facts", "description", "image"
        ]
        
        for field in field_names:
            self.fields[field] = QLineEdit()
            form_layout.addRow(field.capitalize() + ":", self.fields[field])

        self.submit_button = QPushButton("Add Product")
        self.submit_button.clicked.connect(self.submit_product)
        
        self.layout.addLayout(form_layout)
        self.layout.addWidget(self.submit_button)
        self.setLayout(self.layout)

    def submit_product(self):
        """Collects form data and adds product to the database."""
        product_data = {"barcode_number": self.barcode}
        for field, widget in self.fields.items():
            value = widget.text().strip()
            if value:
                product_data[field] = value
        
        add_product_to_db(product_data)
        self.accept()

class BarcodeScannerApp(QWidget):
    def __init__(self):
        super().__init__()

        self.last_scanned_barcode = None

        self.setWindowTitle("Barcode Scanner")
        self.setGeometry(200, 200, 400, 300)

        layout = QVBoxLayout()

        self.label = QLabel("Click 'Scan Barcode' to start")
        layout.addWidget(self.label)

        self.scan_button = QPushButton("Scan Barcode")
        self.scan_button.clicked.connect(self.scan_barcode)
        layout.addWidget(self.scan_button)

        self.download_button = QPushButton("Download Neo4J data as a CSV file")
        self.download_button.clicked.connect(self.download_neo4j_data)
        layout.addWidget(self.download_button)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        layout.addWidget(self.result_area)

        self.open_product_form_button = QPushButton("Add the Product")
        self.open_product_form_button.clicked.connect(self.handle_add_product)
        layout.addWidget(self.open_product_form_button)
        self.open_product_form_button.setHidden(True)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setHidden(True)
        layout.addWidget(self.image_label)

        self.setLayout(layout)

    def scan_barcode(self):
        """Opens camera to scan barcode and fetches product details."""
        barcode = self.scan_with_opencv()
        self.last_scanned_barcode = barcode
        
        if barcode:
            self.label.setText(f"Barcode: {barcode}")
            product = fetch_product(barcode)
            
            if product:
                product_details = json.dumps(product, indent=4)
                self.result_area.setText(product_details)

                image_url = product.get("image", [None])
                if image_url:
                    product_details = self.add_image_to_html(product_details, image_url)
                
                self.result_area.setHtml(product_details)
            else:
                self.result_area.setText("Product not found. Please enter details manually.")
                self.image_label.setHidden(True)
                self.open_product_form(barcode)
            self.open_product_form_button.setHidden(False)
        else:
            self.label.setText("No barcode detected.")
            self.image_label.setHidden(True)

    def scan_with_opencv(self):
        """Opens webcam to scan barcode."""
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            barcodes = decode(frame)
            for barcode in barcodes:
                barcode_data = barcode.data.decode("utf-8")
                cap.release()
                cv2.destroyAllWindows()
                return barcode_data

            cv2.imshow("Scan Barcode - Press 'Q' to Quit", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()
        return None

    def display_image(self, url):
        """Fetch and display product image from URL."""
        response = requests.get(url)
        if response.status_code == 200:
            with open("temp_image.jpg", "wb") as f:
                f.write(response.content)
            pixmap = QPixmap("temp_image.jpg")
            self.image_label.setPixmap(pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio))
            self.image_label.setHidden(False)

    def handle_add_product(self, link):
        """Opens the manual product entry form when 'Add Product' is clicked."""
        if hasattr(self, 'last_scanned_barcode') and self.last_scanned_barcode:
            self.open_product_form(self.last_scanned_barcode)
    
    def download_neo4j_data(self):
        """Fetch data from Neo4j and save as a CSV file."""
        data = fetch_all_products_from_neo4j()

        if not data:
            QMessageBox.warning(self, "No Data", "No products found in Neo4j database.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")

        if file_path:
            df = pd.DataFrame(data)
            df.to_csv(file_path, index=False)
            QMessageBox.information(self, "Success", "CSV file saved successfully.")

    def open_product_form(self, barcode):
        """Opens a form for manual product entry."""
        form = ProductForm(barcode, self)
        form.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BarcodeScannerApp()
    window.show()
    sys.exit(app.exec())

def add_image_to_html(self, product_details, image_url):
    """Formats product details as HTML and embeds the image."""
    image_html = f'<br><img src="{image_url}" width="200"/>'
    product_html = f"<pre>{product_details}</pre>" + image_html
    return product_html