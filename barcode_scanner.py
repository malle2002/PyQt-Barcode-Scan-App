import cv2
from pyzbar.pyzbar import decode
from product_operations import fetch_product

def scan_barcode():
    """Scan barcode using webcam and return barcode data."""
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

if __name__ == "__main__":
    print("Scanning barcode...")
    barcode = scan_barcode()
    
    if barcode:
        print(f"Barcode detected: {barcode}")
        product = fetch_product(barcode)
        if product:
            print("Product details:", product)
        else:
            print("No product details found.")
    else:
        print("No barcode detected.")
