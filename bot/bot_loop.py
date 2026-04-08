import threading
import time

import numpy as np
import pyautogui
import win32con
import win32gui
import win32ui

from bot.frame_analyzer import FrameAnalyzer
from bot.yolo_detector import YOLODetector


class BotLoop:
    def __init__(self):
        self.monitoring = False
        self.actions_enabled = False
        self.thread = None
        self.window_name = None
        self.hwnd = None
        self.capture_success = False
        self.attack_buttons = []
        self.button_timers = {}
        self.detector = YOLODetector()
        self.frame_analyzer = FrameAnalyzer()
        self.yolo_enabled = False
        self.last_detection_found = False
        self.last_detection_labels = []
        self.last_detection_boxes = []
        self.last_categories = {"attack": [], "resources": [], "bots": []}
        self.last_resource_state = {"hp_percent": None, "mp_percent": None, "pet_hp_percent": None}
        self.last_error = None
        self.last_frame = None
        self.preview_lock = threading.Lock()
        self.heal_settings = {"hp_threshold": 50, "key": "F1"}
        self.mana_settings = {"mp_threshold": 30, "key": "F2"}
        self.pet_heal_settings = {"hp_threshold": 40, "key": "F3"}
        self.cv_settings = {"enabled": False, "hp_roi": "", "mp_roi": "", "pet_hp_roi": ""}
        self.mode_settings = {"auto_farm": False, "resource_gather": False, "pet_mode": False, "pause_on_bot": True}
        self.class_settings = {"attack": set(), "resources": set(), "bots": set()}
        self.resource_action_key = "F4"
        self.last_support_action = {"heal": 0.0, "mana": 0.0, "pet_heal": 0.0, "gather": 0.0}

    def set_window_name(self, window_name):
        self.window_name = window_name

    def set_attack_buttons(self, attack_buttons):
        self.attack_buttons = attack_buttons
        self.button_timers = {}
        for btn in attack_buttons:
            self.button_timers[btn["number"]] = time.time()

    def set_yolo_settings(self, yolo_settings):
        attack_targets = self._normalize_classes(yolo_settings.get("target_classes", ""))
        resource_targets = self._normalize_classes(yolo_settings.get("resource_classes", ""))
        bot_targets = self._normalize_classes(yolo_settings.get("bot_classes", ""))

        self.yolo_enabled = bool(yolo_settings.get("enabled", False))
        self.detector.configure(
            enabled=self.yolo_enabled,
            model_path=yolo_settings.get("model_path", "yolov8n.pt"),
            confidence=float(yolo_settings.get("confidence", 0.5)),
            target_classes=attack_targets | resource_targets | bot_targets,
        )
        self.class_settings = {
            "attack": attack_targets,
            "resources": resource_targets,
            "bots": bot_targets,
        }
        self.last_detection_found = False
        self.last_detection_labels = []
        self.last_detection_boxes = []
        self.last_categories = {"attack": [], "resources": [], "bots": []}
        self.last_error = None

    def set_support_settings(self, healing_settings, mana_settings, pet_heal_settings, cv_settings):
        self.heal_settings = {
            "hp_threshold": int(healing_settings.get("hp_threshold", 50)),
            "key": healing_settings.get("key", "F1"),
        }
        self.mana_settings = {
            "mp_threshold": int(mana_settings.get("mp_threshold", 30)),
            "key": mana_settings.get("key", "F2"),
        }
        self.pet_heal_settings = {
            "hp_threshold": int(pet_heal_settings.get("hp_threshold", 40)),
            "key": pet_heal_settings.get("key", "F3"),
        }
        self.cv_settings = {
            "enabled": bool(cv_settings.get("enabled", False)),
            "hp_roi": cv_settings.get("hp_roi", ""),
            "mp_roi": cv_settings.get("mp_roi", ""),
            "pet_hp_roi": cv_settings.get("pet_hp_roi", ""),
        }
        self.frame_analyzer.configure(
            hp_roi=self.cv_settings["hp_roi"],
            mp_roi=self.cv_settings["mp_roi"],
            pet_hp_roi=self.cv_settings["pet_hp_roi"],
        )

    def set_mode_settings(self, mode_settings):
        self.mode_settings = {
            "auto_farm": bool(mode_settings.get("auto_farm", False)),
            "resource_gather": bool(mode_settings.get("resource_gather", False)),
            "pet_mode": bool(mode_settings.get("pet_mode", False)),
            "pause_on_bot": bool(mode_settings.get("pause_on_bot", True)),
        }
        self.resource_action_key = mode_settings.get("resource_key", "F4") or "F4"

    def start_monitoring(self):
        if self.monitoring:
            return

        self.monitoring = True
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def stop_monitoring(self):
        self.monitoring = False
        self.actions_enabled = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)
        self.thread = None
        self.hwnd = None
        self.capture_success = False
        self.last_detection_found = False
        self.last_detection_labels = []
        self.last_detection_boxes = []
        self.last_categories = {"attack": [], "resources": [], "bots": []}
        self.last_resource_state = {"hp_percent": None, "mp_percent": None, "pet_hp_percent": None}
        with self.preview_lock:
            self.last_frame = None

    def enable_actions(self):
        self.actions_enabled = True

    def disable_actions(self):
        self.actions_enabled = False

    def find_window(self):
        try:
            self.hwnd = win32gui.FindWindow(None, self.window_name)
            if self.hwnd == 0:
                self.hwnd = None
                return False
            return True
        except Exception as exc:
            self.last_error = str(exc)
            print(f"Window lookup failed: {exc}")
            return False

    def capture_screenshot(self):
        if not self.hwnd:
            return None

        hwnd_dc = None
        mfc_dc = None
        save_dc = None
        bitmap = None

        try:
            hwnd_dc = win32gui.GetWindowDC(self.hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()

            client_left, client_top = win32gui.ClientToScreen(self.hwnd, (0, 0))
            window_left, window_top, _, _ = win32gui.GetWindowRect(self.hwnd)
            client_rect = win32gui.GetClientRect(self.hwnd)
            width = client_rect[2] - client_rect[0]
            height = client_rect[3] - client_rect[1]
            source_x = client_left - window_left
            source_y = client_top - window_top

            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)
            save_dc.BitBlt((0, 0), (width, height), mfc_dc, (source_x, source_y), win32con.SRCCOPY)

            bitmap_info = bitmap.GetInfo()
            bitmap_bytes = bitmap.GetBitmapBits(True)
            frame = np.frombuffer(bitmap_bytes, dtype=np.uint8)
            frame = frame.reshape((bitmap_info["bmHeight"], bitmap_info["bmWidth"], 4))
            frame = np.ascontiguousarray(frame[:, :, :3])

            self.last_error = None
            return frame
        except Exception as exc:
            self.last_error = str(exc)
            print(f"Screen capture failed: {exc}")
            return None
        finally:
            if bitmap is not None:
                win32gui.DeleteObject(bitmap.GetHandle())
            if save_dc is not None:
                save_dc.DeleteDC()
            if mfc_dc is not None:
                mfc_dc.DeleteDC()
            if hwnd_dc is not None and self.hwnd:
                win32gui.ReleaseDC(self.hwnd, hwnd_dc)

    def press_button(self, button_number):
        try:
            if self.hwnd:
                try:
                    win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(self.hwnd)
                    win32gui.SetFocus(self.hwnd)
                except Exception:
                    pass
                time.sleep(0.08)

            pyautogui.press(str(button_number))
            print(f"Pressed key {button_number}")
        except Exception as exc:
            self.last_error = str(exc)
            print(f"Key press failed for {button_number}: {exc}")

    def press_key(self, key_name):
        try:
            pyautogui.press(key_name)
            print(f"Pressed support key {key_name}")
        except Exception as exc:
            self.last_error = str(exc)
            print(f"Support key press failed for {key_name}: {exc}")

    def loop(self):
        print("Vision monitoring started")

        while self.monitoring:
            if not self.window_name:
                self.capture_success = False
                time.sleep(0.2)
                continue

            if not self.hwnd and not self.find_window():
                self.capture_success = False
                time.sleep(0.5)
                continue

            self.capture_success = True
            frame = self.capture_screenshot()
            if frame is None:
                self.capture_success = False
                self.hwnd = None
                time.sleep(0.2)
                continue

            self.process_frame(frame)
            time.sleep(0.05)

        print("Vision monitoring stopped")

    def process_frame(self, frame):
        if self.cv_settings["enabled"]:
            self.handle_support_actions(frame, allow_actions=self.actions_enabled)
        else:
            self.last_resource_state = {"hp_percent": None, "mp_percent": None, "pet_hp_percent": None}

        detections = self.detect_targets(frame)
        self.update_preview_state(frame)

        if not self.actions_enabled:
            return

        bot_detected = bool(self.last_categories["bots"])
        if bot_detected and self.mode_settings["pause_on_bot"]:
            return

        if self.mode_settings["resource_gather"]:
            self.handle_resource_gather()

        if self.mode_settings["auto_farm"]:
            self.handle_attack_cycle(detections_present=bool(self.last_categories["attack"]))

    def detect_targets(self, frame):
        if not self.yolo_enabled:
            self.last_detection_found = False
            self.last_detection_labels = []
            self.last_detection_boxes = []
            self.last_categories = {"attack": [], "resources": [], "bots": []}
            return []

        detection = self.detector.detect(frame)
        self.last_error = detection.error
        self.last_detection_boxes = []
        categories = {"attack": [], "resources": [], "bots": []}

        for box in detection.boxes:
            item = {"label": box.label, "confidence": box.confidence, "xyxy": box.xyxy}
            self.last_detection_boxes.append(item)

            if box.label in self.class_settings["attack"]:
                categories["attack"].append(item)
            if box.label in self.class_settings["resources"]:
                categories["resources"].append(item)
            if box.label in self.class_settings["bots"]:
                categories["bots"].append(item)

        self.last_categories = categories
        self.last_detection_labels = [item["label"] for item in self.last_detection_boxes]
        self.last_detection_found = any(categories.values()) if any(self.class_settings.values()) else detection.found
        return self.last_detection_boxes

    def handle_attack_cycle(self, detections_present):
        if not detections_present:
            return

        current_time = time.time()
        for btn in self.attack_buttons:
            if not btn["enabled"]:
                continue

            timer_value = float(btn["timer"])
            btn_number = btn["number"]
            previous_press = self.button_timers.get(btn_number, current_time)
            if current_time - previous_press >= timer_value:
                self.press_button(btn_number)
                self.button_timers[btn_number] = current_time

    def handle_resource_gather(self):
        if not self.last_categories["resources"]:
            return

        now = time.time()
        if now - self.last_support_action["gather"] >= 1.0:
            self.press_key(self.resource_action_key)
            self.last_support_action["gather"] = now

    def handle_support_actions(self, frame, allow_actions):
        resource_state = self.frame_analyzer.analyze(frame)
        self.last_resource_state = {
            "hp_percent": resource_state.hp_percent,
            "mp_percent": resource_state.mp_percent,
            "pet_hp_percent": resource_state.pet_hp_percent,
        }

        if not allow_actions:
            return

        now = time.time()

        if resource_state.hp_percent is not None and resource_state.hp_percent <= self.heal_settings["hp_threshold"]:
            if now - self.last_support_action["heal"] >= 1.0:
                self.press_key(self.heal_settings["key"])
                self.last_support_action["heal"] = now

        if resource_state.mp_percent is not None and resource_state.mp_percent <= self.mana_settings["mp_threshold"]:
            if now - self.last_support_action["mana"] >= 1.0:
                self.press_key(self.mana_settings["key"])
                self.last_support_action["mana"] = now

        if self.mode_settings["pet_mode"]:
            pet_hp = resource_state.pet_hp_percent
            if pet_hp is not None and pet_hp <= self.pet_heal_settings["hp_threshold"]:
                if now - self.last_support_action["pet_heal"] >= 1.0:
                    self.press_key(self.pet_heal_settings["key"])
                    self.last_support_action["pet_heal"] = now

    def update_preview_state(self, frame):
        with self.preview_lock:
            self.last_frame = frame.copy()

    def get_preview_state(self):
        with self.preview_lock:
            frame = None if self.last_frame is None else self.last_frame.copy()

        return {
            "frame": frame,
            "boxes": list(self.last_detection_boxes),
            "categories": {key: list(value) for key, value in self.last_categories.items()},
            "resources": dict(self.last_resource_state),
            "cv_settings": dict(self.cv_settings),
            "actions_enabled": self.actions_enabled,
        }

    @staticmethod
    def _normalize_classes(text):
        if not isinstance(text, str):
            return set()
        return {item.strip().lower() for item in text.split(",") if item.strip()}
