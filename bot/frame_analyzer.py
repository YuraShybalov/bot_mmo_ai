from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2

from bot.hud_text_reader import HUDTextReader, OCRResult


@dataclass
class ResourceState:
    hp_percent: float | None = None
    mp_percent: float | None = None
    pet_hp_percent: float | None = None
    hp_text: str | None = None
    mp_text: str | None = None
    pet_hp_text: str | None = None
    hp_ok: bool = False
    mp_ok: bool = False
    pet_hp_ok: bool = False
    error: str | None = None


class FrameAnalyzer:
    def __init__(self) -> None:
        self.hp_roi = None
        self.mp_roi = None
        self.pet_hp_roi = None
        self.text_reader = HUDTextReader()
        self.hud_template = self._load_hud_template()
        self.hud_box = None
        self.last_text_rois = {"hp": None, "mp": None, "pet": None}

    def configure(self, hp_roi: str = "", mp_roi: str = "", pet_hp_roi: str = "") -> None:
        self.hp_roi = self._parse_roi(hp_roi)
        self.mp_roi = self._parse_roi(mp_roi)
        self.pet_hp_roi = self._parse_roi(pet_hp_roi)

    def analyze(self, frame) -> ResourceState:
        self.hud_box = self._locate_hud(frame)
        hp_result = self._read_kind_text(frame, self.hp_roi, "hp")
        mp_result = self._read_kind_text(frame, self.mp_roi, "mp")
        pet_result = self._read_kind_text(frame, self.pet_hp_roi, "pet")

        first_error = hp_result.error or mp_result.error or pet_result.error
        return ResourceState(
            hp_percent=hp_result.percent,
            mp_percent=mp_result.percent,
            pet_hp_percent=pet_result.percent,
            hp_text=hp_result.text,
            mp_text=mp_result.text,
            pet_hp_text=pet_result.text,
            hp_ok=hp_result.ok,
            mp_ok=mp_result.ok,
            pet_hp_ok=pet_result.ok,
            error=first_error,
        )

    def _read_roi_text(self, frame, roi) -> OCRResult:
        if roi is None:
            return OCRResult()

        x1, y1, x2, y2 = roi
        if x2 <= x1 or y2 <= y1:
            return OCRResult(error="invalid OCR ROI")

        return self.text_reader.read_fraction(frame, (x1, y1, x2, y2))

    def _read_kind_text(self, frame, roi, kind: str) -> OCRResult:
        candidate_rois = self._resolve_text_roi_candidates(frame, roi, kind)
        best_result = OCRResult()
        best_roi = None

        for candidate in candidate_rois:
            result = self._read_roi_text(frame, candidate)
            if result.ok:
                self.last_text_rois[kind] = candidate
                return result

            if best_result.text is None and result.text:
                best_result = result
                best_roi = candidate

        self.last_text_rois[kind] = best_roi if best_roi is not None else (candidate_rois[0] if candidate_rois else None)
        return best_result

    @staticmethod
    def _parse_roi(value: str):
        if not isinstance(value, str) or not value.strip():
            return None

        parts = [part.strip() for part in value.split(",")]
        if len(parts) != 4:
            return None

        try:
            return tuple(float(part) for part in parts)
        except ValueError:
            return None

    @staticmethod
    def _resolve_roi(frame, roi):
        height, width = frame.shape[:2]
        x, y, w, h = roi

        if max(abs(x), abs(y), abs(w), abs(h)) <= 1.0:
            x = int(width * x)
            y = int(height * y)
            w = int(width * w)
            h = int(height * h)
        else:
            x = int(x)
            y = int(y)
            w = int(w)
            h = int(h)

        x1 = max(0, min(width, x))
        y1 = max(0, min(height, y))
        x2 = max(0, min(width, x + w))
        y2 = max(0, min(height, y + h))
        return x1, y1, x2, y2

    def _resolve_text_roi_candidates(self, frame, roi, kind: str):
        if roi is not None:
            return [self._resolve_roi(frame, roi)]

        if self.hud_box is not None:
            x1, y1, x2, y2 = self.hud_box
            hud_w = max(1, x2 - x1)
            hud_h = max(1, y2 - y1)

            relative_rois = {
                "hp": (0.36, 0.09, 0.46, 0.15),
                "mp": (0.36, 0.21, 0.46, 0.15),
            }
            rel = relative_rois.get(kind)

            if rel is not None:
                rx, ry, rw, rh = rel
                candidates = []
                for dx, dy in ((0.0, 0.0), (0.0, -0.02), (0.0, 0.02), (-0.02, 0.0), (0.02, 0.0)):
                    cx1 = x1 + int(hud_w * max(0.0, rx + dx))
                    cy1 = y1 + int(hud_h * max(0.0, ry + dy))
                    cx2 = x1 + int(hud_w * min(1.0, rx + rw + dx))
                    cy2 = y1 + int(hud_h * min(1.0, ry + rh + dy))
                    candidates.append((cx1, cy1, cx2, cy2))
                return candidates

        return []

    def get_debug_rois(self):
        return dict(self.last_text_rois)

    def _locate_hud(self, frame):
        if self.hud_template is None:
            return None

        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        search_h = max(180, frame_gray.shape[0] // 3)
        search_w = max(360, frame_gray.shape[1] // 3)
        search_region = frame_gray[:search_h, :search_w]

        template_h, template_w = self.hud_template.shape[:2]
        best_match = None

        for scale in (0.82, 0.90, 0.96, 1.0, 1.06):
            scaled_w = max(120, int(template_w * scale))
            scaled_h = max(60, int(template_h * scale))
            if scaled_h >= search_region.shape[0] or scaled_w >= search_region.shape[1]:
                continue

            scaled_template = cv2.resize(
                self.hud_template,
                (scaled_w, scaled_h),
                interpolation=cv2.INTER_AREA if scale <= 1.0 else cv2.INTER_CUBIC,
            )
            result = cv2.matchTemplate(search_region, scaled_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if best_match is None or max_val > best_match[0]:
                best_match = (max_val, max_loc, scaled_w, scaled_h)

        if best_match is None or best_match[0] < 0.68:
            return self.hud_box

        _, (x, y), w, h = best_match
        return (x, y, x + w, y + h)

    @staticmethod
    def _load_hud_template():
        base = Path(__file__).resolve().parents[1] / "datasets" / "hud_bars" / "images" / "train"
        full_hud_path = base / "hud_reference.png"
        if not full_hud_path.exists():
            return None

        full = cv2.imread(str(full_hud_path), cv2.IMREAD_GRAYSCALE)
        if full is None:
            return None

        return full[0:150, 0:345]
