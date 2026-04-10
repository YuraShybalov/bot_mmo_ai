from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

try:
    import pytesseract
except Exception:  # pragma: no cover
    pytesseract = None


FRACTION_RE = re.compile(r"(\d+)\s*/\s*(\d+)")


@dataclass
class OCRResult:
    current: int | None = None
    maximum: int | None = None
    percent: float | None = None
    text: str | None = None
    error: str | None = None
    ok: bool = False


class HUDTextReader:
    def __init__(self) -> None:
        self.tesseract_cmd = self._find_tesseract()
        if pytesseract is not None and self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def read_fraction(self, frame, roi) -> OCRResult:
        if pytesseract is None:
            return OCRResult(error="pytesseract is not installed")

        if not self.tesseract_cmd:
            return OCRResult(error="tesseract executable was not found")

        x1, y1, x2, y2 = roi
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return OCRResult(error="empty OCR crop")

        prepared_images = self._prepare_variants(crop)
        best_text = ""

        for prepared in prepared_images:
            try:
                text = pytesseract.image_to_string(
                    prepared,
                    config="--psm 7 -c tessedit_char_whitelist=0123456789/",
                ).strip()
            except Exception as exc:  # pragma: no cover
                return OCRResult(error=str(exc))

            cleaned = text.replace(" ", "")
            if len(cleaned) > len(best_text):
                best_text = cleaned

            match = FRACTION_RE.search(cleaned)
            if match:
                current = int(match.group(1))
                maximum = int(match.group(2))
                percent = round((current / maximum) * 100.0, 1) if maximum else None
                return OCRResult(current=current, maximum=maximum, percent=percent, text=cleaned, ok=True)

        return OCRResult(text=best_text or None, error="fraction text was not recognized")

    def _prepare_variants(self, crop):
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        enlarged = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        enlarged = cv2.GaussianBlur(enlarged, (3, 3), 0)

        blue_emphasis = cv2.resize(crop[:, :, 0], None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        red_emphasis = cv2.resize(crop[:, :, 2], None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        blue_emphasis = cv2.GaussianBlur(blue_emphasis, (3, 3), 0)
        red_emphasis = cv2.GaussianBlur(red_emphasis, (3, 3), 0)

        _, binary_light = cv2.threshold(enlarged, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, binary_dark = cv2.threshold(enlarged, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        _, blue_binary = cv2.threshold(blue_emphasis, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, red_binary = cv2.threshold(red_emphasis, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return [enlarged, binary_light, binary_dark, blue_emphasis, red_emphasis, blue_binary, red_binary]

    @staticmethod
    def _find_tesseract() -> str | None:
        candidates = [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return None
