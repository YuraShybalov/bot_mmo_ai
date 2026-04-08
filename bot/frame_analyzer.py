from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ResourceState:
    hp_percent: float | None = None
    mp_percent: float | None = None
    pet_hp_percent: float | None = None


class FrameAnalyzer:
    def __init__(self) -> None:
        self.hp_roi = None
        self.mp_roi = None
        self.pet_hp_roi = None

    def configure(self, hp_roi: str = "", mp_roi: str = "", pet_hp_roi: str = "") -> None:
        self.hp_roi = self._parse_roi(hp_roi)
        self.mp_roi = self._parse_roi(mp_roi)
        self.pet_hp_roi = self._parse_roi(pet_hp_roi)

    def analyze(self, frame) -> ResourceState:
        return ResourceState(
            hp_percent=self._estimate_fill(frame, self.hp_roi, "red"),
            mp_percent=self._estimate_fill(frame, self.mp_roi, "blue"),
            pet_hp_percent=self._estimate_fill(frame, self.pet_hp_roi, "red"),
        )

    def _estimate_fill(self, frame, roi, mode: str):
        if roi is None:
            return None

        x1, y1, x2, y2 = self._resolve_roi(frame, roi)
        if x2 <= x1 or y2 <= y1:
            return None

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None

        b = crop[:, :, 0].astype(np.int16)
        g = crop[:, :, 1].astype(np.int16)
        r = crop[:, :, 2].astype(np.int16)

        if mode == "red":
            score = r - ((g + b) // 2)
            mask = (r > g + 18) & (r > b + 18) & (r > 65)
        else:
            score = b - ((g + r) // 2)
            mask = (b > g + 18) & (b > r + 18) & (b > 65)

        row_strength = score.mean(axis=1)
        active_rows = row_strength > max(8.0, float(row_strength.max()) * 0.45)
        band_rows = self._expand_active_band(active_rows, margin=1)
        if not band_rows.any():
            band_rows = np.ones(mask.shape[0], dtype=bool)

        band_mask = mask[band_rows, :]
        band_score = score[band_rows, :]
        if band_mask.size == 0:
            return None

        columns = band_mask.mean(axis=0)
        score_columns = band_score.mean(axis=0)
        threshold = max(0.20, float(columns.max()) * 0.45)
        score_threshold = max(10.0, float(score_columns.max()) * 0.30)
        filled_columns = (columns >= threshold) & (score_columns >= score_threshold)
        filled_columns = self._close_small_gaps(filled_columns, gap_limit=6)

        active_indices = np.flatnonzero(filled_columns)
        if active_indices.size == 0:
            return 0.0

        start_idx = int(active_indices[0])
        end_idx = int(active_indices[-1])
        total_width = max(1, filled_columns.size - start_idx)
        fill_ratio = (end_idx - start_idx + 1) / total_width
        return round(float(fill_ratio) * 100.0, 1)

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

    @staticmethod
    def _expand_active_band(active_rows, margin: int):
        indices = np.flatnonzero(active_rows)
        if indices.size == 0:
            return active_rows

        start = max(0, int(indices[0]) - margin)
        end = min(active_rows.size, int(indices[-1]) + margin + 1)
        expanded = np.zeros_like(active_rows, dtype=bool)
        expanded[start:end] = True
        return expanded

    @staticmethod
    def _close_small_gaps(values, gap_limit: int):
        result = values.copy()
        start = None

        for index, value in enumerate(result):
            if value:
                if start is not None and 0 < index - start <= gap_limit:
                    result[start:index] = True
                start = None
            elif start is None:
                start = index

        return result
