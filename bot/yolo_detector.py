from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover - import availability depends on host setup
    YOLO = None


@dataclass
class DetectionBox:
    label: str
    confidence: float
    xyxy: tuple[int, int, int, int]


@dataclass
class DetectionResult:
    found: bool = False
    labels: list[str] = field(default_factory=list)
    confidences: list[float] = field(default_factory=list)
    boxes: list[DetectionBox] = field(default_factory=list)
    error: str | None = None


class YOLODetector:
    def __init__(
        self,
        enabled: bool = False,
        model_path: str = "yolov8n.pt",
        confidence: float = 0.5,
        target_classes: Iterable[str] | None = None,
    ) -> None:
        self.enabled = enabled
        self.model_path = model_path
        self.confidence = confidence
        self.target_classes = self._normalize_targets(target_classes)
        self.model = None
        self.loaded_model_path = None
        self.last_error = None

    def configure(
        self,
        *,
        enabled: bool,
        model_path: str,
        confidence: float,
        target_classes: Iterable[str] | None,
    ) -> None:
        self.enabled = enabled
        self.model_path = model_path or "yolov8n.pt"
        self.confidence = confidence
        self.target_classes = self._normalize_targets(target_classes)

        if self.loaded_model_path != self.model_path:
            self.model = None
            self.loaded_model_path = None

        self.last_error = None

    def detect(self, frame) -> DetectionResult:
        if not self.enabled:
            return DetectionResult(found=True)

        model = self._ensure_model()
        if model is None:
            return DetectionResult(found=False, error=self.last_error)

        try:
            results = model.predict(frame, conf=self.confidence, verbose=False)
        except Exception as exc:  # pragma: no cover - runtime depends on model/device
            self.last_error = str(exc)
            return DetectionResult(found=False, error=self.last_error)

        all_boxes: list[DetectionBox] = []
        matched_boxes: list[DetectionBox] = []

        for result in results:
            names = result.names
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                label = str(names.get(class_id, class_id)).lower()
                confidence = float(box.conf[0].item())
                coords = tuple(int(round(value)) for value in box.xyxy[0].tolist())
                detection_box = DetectionBox(label=label, confidence=confidence, xyxy=coords)
                all_boxes.append(detection_box)

                if not self.target_classes or label in self.target_classes:
                    matched_boxes.append(detection_box)

        if not all_boxes:
            return DetectionResult(found=False)

        source_boxes = matched_boxes if self.target_classes else all_boxes
        return DetectionResult(
            found=bool(source_boxes),
            labels=[item.label for item in source_boxes],
            confidences=[item.confidence for item in source_boxes],
            boxes=source_boxes,
        )

    def _ensure_model(self):
        if self.model is not None:
            return self.model

        if YOLO is None:
            self.last_error = "ultralytics is not installed"
            return None

        try:
            self.model = YOLO(self.model_path)
            self.loaded_model_path = self.model_path
            self.last_error = None
            return self.model
        except Exception as exc:  # pragma: no cover - depends on filesystem/network
            self.last_error = str(exc)
            return None

    @staticmethod
    def _normalize_targets(target_classes: Iterable[str] | None) -> set[str]:
        if not target_classes:
            return set()

        normalized = set()
        for item in target_classes:
            value = str(item).strip().lower()
            if value:
                normalized.add(value)
        return normalized
