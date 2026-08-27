"""
QR Code Detector & Decoder Module for Job Scraper Pipeline
Primary Decoder: OpenCV (cv2.QRCodeDetector)
Fallback Decoder: pyzbar (pyzbar.pyzbar.decode)
Preprocessing: Resizing, Grayscale, Contrast Enhancement, Thresholding
"""

import os
import re
import json

def classify_qr_payload(raw_data):
    if not raw_data or not isinstance(raw_data, str):
        return {"raw_data": raw_data or "", "type": "unknown", "url": None}

    data_str = raw_data.strip()
    data_lower = data_str.lower()

    # 1. HTTP/HTTPS URL
    if data_lower.startswith("http://") or data_lower.startswith("https://") or data_lower.startswith("www."):
        url_val = data_str if not data_lower.startswith("www.") else f"https://{data_str}"
        return {"raw_data": data_str, "type": "url", "url": url_val}

    # 2. Phone / Tel
    if data_lower.startswith("tel:") or data_lower.startswith("whatsapp:") or re.match(r'^(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}$', data_str):
        return {"raw_data": data_str, "type": "phone", "url": None}

    # 3. Email / Mailto
    if data_lower.startswith("mailto:") or re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', data_str):
        return {"raw_data": data_str, "type": "email", "url": None}

    # 4. WiFi
    if data_lower.startswith("wifi:"):
        return {"raw_data": data_str, "type": "wifi", "url": None}

    # 5. Payment / UPI
    if data_lower.startswith("upi:") or "pay" in data_lower and "paa" in data_lower:
        return {"raw_data": data_str, "type": "payment", "url": None}

    # 6. Contact / vCard
    if "begin:vcard" in data_lower:
        return {"raw_data": data_str, "type": "contact", "url": None}

    # 7. Calendar
    if "begin:vevent" in data_lower or "begin:vcalendar" in data_lower:
        return {"raw_data": data_str, "type": "calendar", "url": None}

    # 8. Text / Default
    return {"raw_data": data_str, "type": "text", "url": None}


def detect_and_decode_qr(image_path):
    """
    Detects and decodes QR codes from an image using OpenCV with pyzbar fallback and preprocessing.
    Returns a dict following the required spec.
    """
    if not os.path.exists(image_path):
        return {"qr_detected": False, "qr_decoded": False, "qr_count": 0, "qr_codes": []}

    decoded_strings = set()
    qr_detected = False

    # 1. Try OpenCV
    try:
        import cv2
        img = cv2.imread(image_path)
        if img is not None:
            detector = cv2.QRCodeDetector()
            
            # Prepare image variants for robust decoding
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            variants = [
                img,
                gray,
                cv2.equalizeHist(gray),
                cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1],
                cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            ]
            
            for var in variants:
                # Multi QR check
                try:
                    retval, decoded_info, points, _ = detector.detectAndDecodeMulti(var)
                    if retval:
                        qr_detected = True
                        for info in decoded_info:
                            if info and info.strip():
                                decoded_strings.add(info.strip())
                except Exception:
                    pass

                # Single QR check
                try:
                    data, points, _ = detector.detectAndDecode(var)
                    if points is not None and len(points) > 0:
                        qr_detected = True
                    if data and data.strip():
                        decoded_strings.add(data.strip())
                except Exception:
                    pass

                if decoded_strings:
                    break
    except ImportError:
        pass
    except Exception as e:
        print(f"⚠️ OpenCV QR detection error: {e}")

    # 2. Try pyzbar fallback
    if not decoded_strings:
        try:
            from pyzbar.pyzbar import decode as pyzbar_decode
            from PIL import Image
            
            pil_img = Image.open(image_path)
            barcodes = pyzbar_decode(pil_img)
            
            for barcode in barcodes:
                if barcode.type == 'QRCODE':
                    qr_detected = True
                    payload = barcode.data.decode('utf-8', errors='ignore').strip()
                    if payload:
                        decoded_strings.add(payload)
        except ImportError:
            pass
        except Exception:
            pass

    # Construct response according to spec
    if not qr_detected and not decoded_strings:
        return {
            "qr_detected": False,
            "qr_decoded": False,
            "qr_count": 0,
            "qr_codes": []
        }

    if qr_detected and not decoded_strings:
        return {
            "qr_detected": True,
            "qr_decoded": False,
            "qr_count": 1,
            "qr_codes": []
        }

    parsed_codes = [classify_qr_payload(raw) for raw in sorted(list(decoded_strings))]

    return {
        "qr_detected": True,
        "qr_decoded": True,
        "qr_count": len(parsed_codes),
        "qr_codes": parsed_codes
    }
