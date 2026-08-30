"""
Robust QR Code Scanner and Payload Classifier.
Uses OpenCV QRCodeDetector as primary and pyzbar as fallback.
Applies image preprocessing variants to maximize QR detection rate on flyer posters.
"""
import re
from typing import Optional, List, Dict, Any
import cv2
import numpy as np
from ..schema.job_schema import QRCodeResult
from ..preprocessing.preprocessor import ImagePreprocessor

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    PYZBAR_AVAILABLE = True
except Exception:
    pyzbar_decode = None
    PYZBAR_AVAILABLE = False


class QRScanner:
    @staticmethod
    def classify_payload(raw_data: str) -> Dict[str, Any]:
        """
        Classify raw QR code string into: url, phone, email, vcard, wifi, text.
        Never invents or hallucinated URLs.
        """
        raw = raw_data.strip()
        result = {
            "payload_type": "text",
            "raw_data": raw,
            "url": None,
            "phone": None,
            "email": None
        }

        # 1. WhatsApp click to chat (e.g. https://wa.me/919876543210 or wa.me/919876543210)
        wa_match = re.search(r'wa\.me/(\+?\d+)', raw, re.IGNORECASE)
        if wa_match:
            result["payload_type"] = "url"
            result["url"] = raw if raw.startswith('http') else f"https://{raw}"
            result["phone"] = wa_match.group(1).lstrip("+")
            return result

        # 2. Generic URL pattern (http/https or standard web address)
        if re.match(r'^(https?://|www\.)[^\s]+$', raw, re.IGNORECASE):
            url = raw if raw.startswith('http') else f"https://{raw}"
            result["payload_type"] = "url"
            result["url"] = url
            return result

        # 3. Email (mailto: or raw email address)
        email_match = re.match(r'^(?:mailto:)?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$', raw, re.IGNORECASE)
        if email_match:
            result["payload_type"] = "email"
            result["email"] = email_match.group(1)
            return result

        # 4. Tel URI or phone number
        tel_match = re.match(r'^(?:tel:)?(\+?[0-9\s-]{10,15})$', raw, re.IGNORECASE)
        if tel_match:
            result["payload_type"] = "phone"
            result["phone"] = tel_match.group(1).replace(" ", "").replace("-", "")
            return result

        # 5. vCard contact
        if "BEGIN:VCARD" in raw.upper():
            result["payload_type"] = "vcard"
            # Extract phone/email from vCard
            tel = re.search(r'TEL[^:]*:([^\r\n]+)', raw)
            if tel:
                result["phone"] = tel.group(1).strip()
            em = re.search(r'EMAIL[^:]*:([^\r\n]+)', raw)
            if em:
                result["email"] = em.group(1).strip()
            return result

        return result

    @classmethod
    def scan_image(cls, image_input) -> QRCodeResult:
        """
        Scan image for QR codes using OpenCV and pyzbar across multiple preprocessing passes.
        """
        if isinstance(image_input, str):
            img = ImagePreprocessor.load_image(image_input)
        else:
            img = image_input

        if img is None:
            return QRCodeResult(found=False)

        cv_detector = cv2.QRCodeDetector()
        detected_texts: List[str] = []

        # Prepare image variants for QR detection
        variants = []
        variants.append(img)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        variants.append(gray)

        # Contrast enhanced
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        variants.append(clahe.apply(gray))

        # Thresholded
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(thresh)

        # 1. Primary: OpenCV QRCodeDetector
        for v in variants:
            try:
                data, bbox, _ = cv_detector.detectAndDecode(v)
                if data and data.strip():
                    detected_texts.append(data.strip())
                    break
            except Exception:
                pass

        # 2. Fallback: pyzbar
        if not detected_texts and PYZBAR_AVAILABLE:
            for v in variants:
                try:
                    barcodes = pyzbar_decode(v)
                    for b in barcodes:
                        text = b.data.decode('utf-8', errors='ignore').strip()
                        if text:
                            detected_texts.append(text)
                    if detected_texts:
                        break
                except Exception:
                    pass

        if detected_texts:
            classified = cls.classify_payload(detected_texts[0])
            return QRCodeResult(
                found=True,
                payload_type=classified["payload_type"],
                raw_data=classified["raw_data"],
                url=classified["url"],
                phone=classified["phone"],
                email=classified["email"]
            )

        return QRCodeResult(found=False)
