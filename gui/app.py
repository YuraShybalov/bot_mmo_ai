import json
import os
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw, ImageOps, ImageTk

from bot.bot_loop import BotLoop


PLACEHOLDER_WINDOW_NAME = "Введіть назву вікна клієнта..."
PREVIEW_MAX_SIZE = (1100, 520)
POP_OUT_PREVIEW_MAX_SIZE = (1600, 1000)
OLD_HP_ROI = "0.05,0.05,0.25,0.03"
OLD_MP_ROI = "0.05,0.09,0.25,0.03"
OLD_PET_HP_ROI = "0.70,0.05,0.20,0.03"
OLD_HP_ROI_2 = "0.105,0.030,0.165,0.022"
OLD_MP_ROI_2 = "0.105,0.052,0.165,0.022"
OLD_PET_HP_ROI_2 = "0.105,0.074,0.165,0.022"
DEFAULT_HP_ROI = "118,36,184,12"
DEFAULT_MP_ROI = "118,55,184,12"
DEFAULT_PET_HP_ROI = ""


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PW AI Бот")
        self.root.geometry("920x820")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind_all("<F12>", self.on_f12)

        self.bot = BotLoop()
        self.config_file = "config.json"
        self.config = {}
        self.window_name = None
        self.window_error_shown = False
        self.preview_image = None
        self.preview_render_box = None
        self.preview_source_size = None
        self.popout_window = None
        self.popout_canvas = None
        self.popout_preview_image = None
        self.popout_preview_render_box = None
        self.selection_target = None
        self.selection_start = None
        self.selection_current = None

        self.load_config()
        self.create_tabs()
        self.apply_bot_configuration()
        self.ensure_monitoring_started()
        self.poll_bot_status()

    def create_tabs(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        self.bot_tab = tk.Frame(notebook)
        self.settings_tab = tk.Frame(notebook)
        self.training_tab = tk.Frame(notebook)

        notebook.add(self.bot_tab, text="Бот")
        notebook.add(self.settings_tab, text="Налаштування")
        notebook.add(self.training_tab, text="Навчання")

        self.create_bot_tab()
        self.create_settings_tab()
        self.create_training_tab()

    def create_bot_tab(self):
        self.bot_tab.columnconfigure(0, weight=3)
        self.bot_tab.columnconfigure(1, weight=2)

        self.status_label = tk.Label(self.bot_tab, text="Статус: Моніторинг")
        self.status_label.grid(row=0, column=0, columnspan=2, pady=6)

        left_frame = tk.Frame(self.bot_tab)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=10)

        right_frame = tk.Frame(self.bot_tab)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)

        info_frame = tk.Frame(left_frame)
        info_frame.pack(anchor="w", fill="x")

        self.health_label = tk.Label(info_frame, text="HP персонажа: н/д", font=("Arial", 11), fg="red")
        self.health_label.pack(anchor="w", pady=(4, 0))
        self.mana_label = tk.Label(info_frame, text="MP персонажа: н/д", font=("Arial", 11), fg="blue")
        self.mana_label.pack(anchor="w", pady=(2, 0))
        self.pet_health_label = tk.Label(info_frame, text="HP петомця: н/д", font=("Arial", 11), fg="darkred")
        self.pet_health_label.pack(anchor="w", pady=(2, 0))

        button_frame = tk.Frame(left_frame)
        button_frame.pack(pady=10, anchor="w")

        self.toggle_button = tk.Button(button_frame, text="Старт режимів", width=14, command=self.toggle_bot)
        self.toggle_button.pack(side="left", padx=(0, 10))

        self.status_indicator = tk.Canvas(button_frame, width=20, height=20, bg="lightgray", highlightthickness=0)
        self.status_indicator.pack(side="left")
        self.indicator_circle = self.status_indicator.create_oval(2, 2, 18, 18, fill="gray", outline="gray")

        tk.Label(
            left_frame,
            text="Захоплення вікна та YOLO-моніторинг запускаються автоматично. F12 перемикає вибрані режими.",
            wraplength=360,
            justify="left",
        ).pack(pady=5, anchor="w")

        self.auto_farm_var = tk.BooleanVar(value=self.config.get("auto_farm", False))
        self.resource_gather_var = tk.BooleanVar(value=self.config.get("resource_gather", False))
        self.pet_checkbox_var = tk.BooleanVar(value=self.config.get("pet_mode", False))
        self.pause_on_bot_var = tk.BooleanVar(value=self.config.get("pause_on_bot", True))

        tk.Checkbutton(left_frame, text="Автофарм", variable=self.auto_farm_var).pack(anchor="w", pady=2)
        tk.Checkbutton(left_frame, text="Збір ресурсів", variable=self.resource_gather_var).pack(anchor="w", pady=2)
        tk.Checkbutton(left_frame, text="Використовувати петомця", variable=self.pet_checkbox_var).pack(anchor="w", pady=2)
        tk.Checkbutton(left_frame, text="Пауза дій, якщо виявлено іншого бота", variable=self.pause_on_bot_var).pack(anchor="w", pady=2)

        vision_frame = tk.LabelFrame(right_frame, text="Стан розпізнавання")
        vision_frame.pack(anchor="w", fill="x", pady=(0, 14))

        self.yolo_status_label = tk.Label(vision_frame, text="YOLO: очікування", justify="left", wraplength=320)
        self.yolo_status_label.pack(anchor="w", padx=10, pady=(10, 4))

        self.detection_label = tk.Label(vision_frame, text="Розпізнавання: н/д", justify="left", wraplength=320)
        self.detection_label.pack(anchor="w", padx=10, pady=(0, 10))

        target_frame = tk.LabelFrame(right_frame, text="Підсумок цілей")
        target_frame.pack(anchor="w", fill="x", pady=(0, 14))

        self.target_summary_label = tk.Label(target_frame, text="Цілі атаки: н/д", justify="left", wraplength=320)
        self.target_summary_label.pack(anchor="w", padx=10, pady=(10, 4))

        self.resource_status_label = tk.Label(target_frame, text="Ресурси: н/д", justify="left", wraplength=320)
        self.resource_status_label.pack(anchor="w", padx=10, pady=(0, 4))

        self.bot_warning_label = tk.Label(target_frame, text="Боти: н/д", justify="left", wraplength=320)
        self.bot_warning_label.pack(anchor="w", padx=10, pady=(0, 10))

        action_frame = tk.LabelFrame(right_frame, text="Стан режимів")
        action_frame.pack(anchor="w", fill="x")

        self.mode_state_label = tk.Label(action_frame, text="Дії: вимкнено", justify="left", wraplength=320)
        self.mode_state_label.pack(anchor="w", padx=10, pady=(10, 10))

        preview_frame = tk.LabelFrame(self.bot_tab, text="Прев’ю")
        preview_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=(8, 12))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        preview_toolbar = tk.Frame(preview_frame)
        preview_toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        tk.Button(preview_toolbar, text="Відкрити велике прев'ю", command=self.open_preview_popout, width=22).pack(side="left")

        self.preview_canvas = tk.Canvas(preview_frame, bg=self.root.cget("bg"), highlightthickness=0)
        self.preview_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.preview_canvas.bind("<ButtonPress-1>", self.on_preview_press)
        self.preview_canvas.bind("<B1-Motion>", self.on_preview_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self.on_preview_release)

    def create_settings_tab(self):
        canvas = tk.Canvas(self.settings_tab)
        scrollbar = ttk.Scrollbar(self.settings_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Label(scrollable_frame, text="Кнопки атаки", font=("Arial", 12, "bold")).pack(anchor="w", padx=15, pady=(15, 10))

        self.attack_buttons = []
        config_attack_buttons = self.config.get("attack_buttons", [])
        for i in range(1, 6):
            btn_frame = tk.Frame(scrollable_frame)
            btn_frame.pack(fill="x", padx=15, pady=5)

            saved = config_attack_buttons[i - 1] if i - 1 < len(config_attack_buttons) else {}
            enabled_var = tk.BooleanVar(value=saved.get("enabled", False))
            timer_var = tk.StringVar(value=str(saved.get("timer", "1.0")))
            self.attack_buttons.append({"number": i, "enabled": enabled_var, "timer": timer_var})

            tk.Checkbutton(btn_frame, text=f"Кнопка {i}", variable=enabled_var).pack(side="left", padx=(0, 10))
            tk.Label(btn_frame, text="Інтервал (сек):").pack(side="left", padx=(0, 5))
            tk.Entry(btn_frame, textvariable=timer_var, width=8).pack(side="left")

        self.create_healing_settings(scrollable_frame)
        self.create_yolo_settings(scrollable_frame)
        self.create_cv_settings(scrollable_frame)

        tk.Button(scrollable_frame, text="Зберегти налаштування", command=self.on_save_settings, width=20).pack(anchor="w", padx=15, pady=(15, 20))

    def create_healing_settings(self, parent):
        healing = self.config.get("healing", {})
        mana = self.config.get("mana_restoration", {})
        pet = self.config.get("pet_healing", {})

        healing_frame = tk.Frame(parent)
        healing_frame.pack(fill="x", padx=15, pady=(20, 10))
        tk.Label(healing_frame, text="Лікування", font=("Arial", 12, "bold")).pack(anchor="w")

        hp_frame = tk.Frame(healing_frame)
        hp_frame.pack(fill="x", pady=(10, 5))
        tk.Label(hp_frame, text="Поріг HP для лікування (%):").pack(side="left")
        self.heal_hp_var = tk.IntVar(value=healing.get("hp_threshold", 50))
        tk.Scale(hp_frame, from_=0, to=100, orient="horizontal", variable=self.heal_hp_var).pack(side="right", fill="x", expand=True)

        heal_key_frame = tk.Frame(healing_frame)
        heal_key_frame.pack(fill="x", pady=(5, 0))
        tk.Label(heal_key_frame, text="Клавіша лікування:").pack(side="left")
        self.heal_key_var = tk.StringVar(value=healing.get("key", "F1"))
        tk.OptionMenu(heal_key_frame, self.heal_key_var, "F1", "F2", "F3", "F4", "F5").pack(side="right")

        mana_frame = tk.Frame(parent)
        mana_frame.pack(fill="x", padx=15, pady=(20, 10))
        tk.Label(mana_frame, text="Мана", font=("Arial", 12, "bold")).pack(anchor="w")

        mp_frame = tk.Frame(mana_frame)
        mp_frame.pack(fill="x", pady=(10, 5))
        tk.Label(mp_frame, text="Поріг MP для відновлення (%):").pack(side="left")
        self.restore_mp_var = tk.IntVar(value=mana.get("mp_threshold", 30))
        tk.Scale(mp_frame, from_=0, to=100, orient="horizontal", variable=self.restore_mp_var).pack(side="right", fill="x", expand=True)

        restore_key_frame = tk.Frame(mana_frame)
        restore_key_frame.pack(fill="x", pady=(5, 0))
        tk.Label(restore_key_frame, text="Клавіша відновлення:").pack(side="left")
        self.restore_key_var = tk.StringVar(value=mana.get("key", "F2"))
        tk.OptionMenu(restore_key_frame, self.restore_key_var, "F1", "F2", "F3", "F4", "F5").pack(side="right")

        pet_frame = tk.Frame(parent)
        pet_frame.pack(fill="x", padx=15, pady=(20, 10))
        tk.Label(pet_frame, text="Лікування петомця", font=("Arial", 12, "bold")).pack(anchor="w")

        pet_hp_frame = tk.Frame(pet_frame)
        pet_hp_frame.pack(fill="x", pady=(10, 5))
        tk.Label(pet_hp_frame, text="Поріг HP петомця (%):").pack(side="left")
        self.pet_heal_hp_var = tk.IntVar(value=pet.get("hp_threshold", 40))
        tk.Scale(pet_hp_frame, from_=0, to=100, orient="horizontal", variable=self.pet_heal_hp_var).pack(side="right", fill="x", expand=True)

        pet_key_frame = tk.Frame(pet_frame)
        pet_key_frame.pack(fill="x", pady=(5, 0))
        tk.Label(pet_key_frame, text="Клавіша лікування петомця:").pack(side="left")
        self.pet_heal_key_var = tk.StringVar(value=pet.get("key", "F3"))
        tk.OptionMenu(pet_key_frame, self.pet_heal_key_var, "F1", "F2", "F3", "F4", "F5").pack(side="right")

    def create_yolo_settings(self, parent):
        yolo_config = self.config.get("yolo", {})

        frame = tk.Frame(parent)
        frame.pack(fill="x", padx=15, pady=(20, 10))
        tk.Label(frame, text="YOLO-розпізнавання", font=("Arial", 12, "bold")).pack(anchor="w")

        self.yolo_enabled_var = tk.BooleanVar(value=yolo_config.get("enabled", True))
        tk.Checkbutton(frame, text="Увімкнути YOLO-моніторинг при старті програми", variable=self.yolo_enabled_var).pack(anchor="w", pady=(10, 6))

        model_frame = tk.Frame(frame)
        model_frame.pack(fill="x", pady=4)
        tk.Label(model_frame, text="Шлях до моделі:").pack(side="left")
        self.yolo_model_path_var = tk.StringVar(value=yolo_config.get("model_path", "yolov8n.pt"))
        tk.Entry(model_frame, textvariable=self.yolo_model_path_var, width=40).pack(side="right", fill="x", expand=True)

        confidence_frame = tk.Frame(frame)
        confidence_frame.pack(fill="x", pady=4)
        tk.Label(confidence_frame, text="Впевненість:").pack(side="left")
        self.yolo_confidence_var = tk.StringVar(value=str(yolo_config.get("confidence", 0.5)))
        tk.Entry(confidence_frame, textvariable=self.yolo_confidence_var, width=12).pack(side="right")

        attack_frame = tk.Frame(frame)
        attack_frame.pack(fill="x", pady=4)
        tk.Label(attack_frame, text="Класи ворогів:").pack(side="left")
        self.yolo_target_classes_var = tk.StringVar(value=yolo_config.get("target_classes", "enemy,mob,monster"))
        tk.Entry(attack_frame, textvariable=self.yolo_target_classes_var, width=40).pack(side="right", fill="x", expand=True)

        resource_frame = tk.Frame(frame)
        resource_frame.pack(fill="x", pady=4)
        tk.Label(resource_frame, text="Класи ресурсів:").pack(side="left")
        self.resource_classes_var = tk.StringVar(value=yolo_config.get("resource_classes", "resource,ore,herb,tree"))
        tk.Entry(resource_frame, textvariable=self.resource_classes_var, width=40).pack(side="right", fill="x", expand=True)

        bot_frame = tk.Frame(frame)
        bot_frame.pack(fill="x", pady=4)
        tk.Label(bot_frame, text="Класи інших ботів:").pack(side="left")
        self.bot_classes_var = tk.StringVar(value=yolo_config.get("bot_classes", "player,bot"))
        tk.Entry(bot_frame, textvariable=self.bot_classes_var, width=40).pack(side="right", fill="x", expand=True)

        key_frame = tk.Frame(frame)
        key_frame.pack(fill="x", pady=4)
        tk.Label(key_frame, text="Клавіша ресурсу:").pack(side="left")
        self.resource_key_var = tk.StringVar(value=self.config.get("resource_key", "F4"))
        tk.OptionMenu(key_frame, self.resource_key_var, "F1", "F2", "F3", "F4", "F5").pack(side="right")

    def create_cv_settings(self, parent):
        cv_config = self.config.get("cv_analysis", {})

        frame = tk.Frame(parent)
        frame.pack(fill="x", padx=15, pady=(20, 10))
        tk.Label(frame, text="Візуальний аналіз HP / MP", font=("Arial", 12, "bold")).pack(anchor="w")

        self.cv_enabled_var = tk.BooleanVar(value=cv_config.get("enabled", False))
        tk.Checkbutton(frame, text="Увімкнути аналіз HP/MP/HP петомця із захопленого вікна", variable=self.cv_enabled_var).pack(anchor="w", pady=(10, 6))

        self.hp_roi_var = self._roi_entry(frame, "ROI HP персонажа:", self._resolve_default_roi(cv_config.get("hp_roi"), {OLD_HP_ROI, OLD_HP_ROI_2}, DEFAULT_HP_ROI))
        self.mp_roi_var = self._roi_entry(frame, "ROI MP персонажа:", self._resolve_default_roi(cv_config.get("mp_roi"), {OLD_MP_ROI, OLD_MP_ROI_2}, DEFAULT_MP_ROI))
        self.pet_hp_roi_var = self._roi_entry(frame, "ROI HP петомця:", self._resolve_default_roi(cv_config.get("pet_hp_roi"), {OLD_PET_HP_ROI, OLD_PET_HP_ROI_2}, DEFAULT_PET_HP_ROI))

        picker_frame = tk.Frame(frame)
        picker_frame.pack(fill="x", pady=(8, 4))
        tk.Button(picker_frame, text="Виділити HP на прев'ю", command=lambda: self.start_roi_selection("hp")).pack(side="left", padx=(0, 8))
        tk.Button(picker_frame, text="Виділити MP на прев'ю", command=lambda: self.start_roi_selection("mp")).pack(side="left", padx=(0, 8))
        tk.Button(picker_frame, text="Виділити HP петомця", command=lambda: self.start_roi_selection("pet")).pack(side="left")

        self.selection_status_label = tk.Label(frame, text="Ручне виділення вимкнене.", fg="gray40", justify="left")
        self.selection_status_label.pack(anchor="w", pady=(0, 4))

        tk.Label(
            frame,
            text="Формат ROI: x,y,width,height. Можна використовувати частки 0..1 або абсолютні пікселі. Це перший крок до стабільної логіки лікування.",
            fg="gray40",
            wraplength=720,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

    def _roi_entry(self, parent, label_text, initial_value):
        row = tk.Frame(parent)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label_text).pack(side="left")
        variable = tk.StringVar(value=initial_value)
        tk.Entry(row, textvariable=variable, width=32).pack(side="right", fill="x", expand=True)
        return variable

    @staticmethod
    def _resolve_default_roi(value, old_defaults, new_default):
        if not value or value in old_defaults:
            return new_default
        return value

    def create_training_tab(self):
        frame = tk.Frame(self.training_tab, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Прив’язка вікна", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 10))
        tk.Label(frame, text="Введіть точну назву ігрового вікна. Після збереження моніторинг перезапуститься автоматично.").pack(anchor="w", pady=(0, 5))

        self.window_name_var = tk.StringVar(value=self.window_name or PLACEHOLDER_WINDOW_NAME)
        tk.Entry(frame, textvariable=self.window_name_var, width=48, font=("Arial", 10)).pack(anchor="w", pady=(0, 10), fill="x")
        tk.Button(frame, text="Зберегти назву вікна", command=self.save_window_name, width=18).pack(anchor="w")

        tk.Label(frame, text="Сценарій навчання", font=("Arial", 12, "bold")).pack(anchor="w", pady=(24, 10))
        tk.Label(
            frame,
            text=(
                "1. Вирівняйте ROI-блоки у прев’ю так, щоб HP / MP персонажа і HP петомця зчитувались правильно.\n"
                "2. Збережіть приклади кадрів, коли видно ворогів, ресурси та інших гравців.\n"
                "3. Зберіть розмічений датасет із цих скріншотів.\n"
                "4. Натренуйте власну YOLO-модель на класах ворогів, ресурсів, гравців і петомців."
            ),
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        tk.Button(frame, text="Зберегти поточний кадр", command=self.save_current_frame, width=18).pack(anchor="w")
        self.training_status_label = tk.Label(frame, text="Папка з навчальними прикладами: training_samples", justify="left")
        self.training_status_label.pack(anchor="w", pady=(10, 0))

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as config_file:
                    self.config = json.load(config_file)
                    self.window_name = self.config.get("window_name")
            except (json.JSONDecodeError, OSError):
                self.config = {}
                self.window_name = None
        else:
            self.config = {}
            self.window_name = None

    def collect_attack_button_snapshot(self):
        snapshot = []
        for btn in self.attack_buttons:
            timer_text = btn["timer"].get().strip() or "1.0"
            try:
                timer_value = max(0.05, float(timer_text))
            except ValueError:
                timer_value = 1.0
            snapshot.append({"number": btn["number"], "enabled": bool(btn["enabled"].get()), "timer": timer_value})
        return snapshot

    def collect_yolo_settings(self):
        try:
            confidence = float(self.yolo_confidence_var.get().strip() or "0.5")
        except ValueError:
            confidence = 0.5

        confidence = min(max(confidence, 0.01), 0.99)
        return {
            "enabled": bool(self.yolo_enabled_var.get()),
            "model_path": self.yolo_model_path_var.get().strip() or "yolov8n.pt",
            "confidence": confidence,
            "target_classes": self.yolo_target_classes_var.get().strip(),
            "resource_classes": self.resource_classes_var.get().strip(),
            "bot_classes": self.bot_classes_var.get().strip(),
        }

    def collect_cv_settings(self):
        return {
            "enabled": bool(self.cv_enabled_var.get()),
            "hp_roi": self.hp_roi_var.get().strip(),
            "mp_roi": self.mp_roi_var.get().strip(),
            "pet_hp_roi": self.pet_hp_roi_var.get().strip(),
        }

    def collect_mode_settings(self):
        return {
            "auto_farm": self.auto_farm_var.get(),
            "resource_gather": self.resource_gather_var.get(),
            "pet_mode": self.pet_checkbox_var.get(),
            "pause_on_bot": self.pause_on_bot_var.get(),
            "resource_key": self.resource_key_var.get(),
        }

    def save_all_config(self):
        window_name = self.window_name_var.get().strip()
        config = {
            "window_name": window_name if window_name and window_name != PLACEHOLDER_WINDOW_NAME else self.window_name,
            "attack_buttons": [
                {"number": btn["number"], "enabled": btn["enabled"].get(), "timer": btn["timer"].get()}
                for btn in self.attack_buttons
            ],
            "healing": {"hp_threshold": self.heal_hp_var.get(), "key": self.heal_key_var.get()},
            "mana_restoration": {"mp_threshold": self.restore_mp_var.get(), "key": self.restore_key_var.get()},
            "pet_healing": {"hp_threshold": self.pet_heal_hp_var.get(), "key": self.pet_heal_key_var.get()},
            "auto_farm": self.auto_farm_var.get(),
            "resource_gather": self.resource_gather_var.get(),
            "pet_mode": self.pet_checkbox_var.get(),
            "pause_on_bot": self.pause_on_bot_var.get(),
            "resource_key": self.resource_key_var.get(),
            "yolo": self.collect_yolo_settings(),
            "cv_analysis": self.collect_cv_settings(),
        }

        with open(self.config_file, "w", encoding="utf-8") as config_file:
            json.dump(config, config_file, ensure_ascii=False, indent=2)
        self.config = config

    def apply_bot_configuration(self):
        self.bot.set_window_name(self.window_name or "")
        self.bot.set_attack_buttons(self.collect_attack_button_snapshot())
        self.bot.set_yolo_settings(self.collect_yolo_settings())
        self.bot.set_support_settings(
            healing_settings={"hp_threshold": self.heal_hp_var.get(), "key": self.heal_key_var.get()},
            mana_settings={"mp_threshold": self.restore_mp_var.get(), "key": self.restore_key_var.get()},
            pet_heal_settings={"hp_threshold": self.pet_heal_hp_var.get(), "key": self.pet_heal_key_var.get()},
            cv_settings=self.collect_cv_settings(),
        )
        self.bot.set_mode_settings(self.collect_mode_settings())

    def ensure_monitoring_started(self):
        self.apply_bot_configuration()
        self.bot.start_monitoring()

    def restart_monitoring(self):
        self.bot.stop_monitoring()
        self.ensure_monitoring_started()

    def save_window_name(self):
        new_window_name = self.window_name_var.get().strip()
        if new_window_name and new_window_name != PLACEHOLDER_WINDOW_NAME:
            self.window_name = new_window_name
            self.save_all_config()
            self.restart_monitoring()

    def on_save_settings(self):
        self.save_all_config()
        actions_were_enabled = self.bot.actions_enabled
        self.restart_monitoring()
        if actions_were_enabled:
            self.bot.enable_actions()
        messagebox.showinfo("Збережено", "Налаштування збережено, моніторинг перезапущено.")

    def start_bot(self):
        window_name = self.window_name_var.get().strip()
        if not window_name or window_name == PLACEHOLDER_WINDOW_NAME:
            messagebox.showerror("Немає вікна", "Спочатку вкажіть назву ігрового вікна у вкладці «Навчання».")
            return

        self.window_name = window_name
        self.save_all_config()
        self.apply_bot_configuration()
        self.window_error_shown = False
        self.bot.enable_actions()
        self.status_label.config(text="Статус: Моніторинг + режими активні")
        self.toggle_button.config(text="Стоп режимів")

    def stop_bot(self):
        self.bot.disable_actions()
        self.status_label.config(text="Статус: Лише моніторинг")
        self.toggle_button.config(text="Старт режимів")
        self.window_error_shown = False
        self.update_indicator()

    def update_indicator(self):
        if self.bot.capture_success:
            if self.bot.actions_enabled:
                self.status_indicator.itemconfig(self.indicator_circle, fill="green", outline="darkgreen")
            else:
                self.status_indicator.itemconfig(self.indicator_circle, fill="deepskyblue", outline="navy")
            return

        if self.bot.monitoring:
            self.status_indicator.itemconfig(self.indicator_circle, fill="red", outline="darkred")
            if not self.window_error_shown:
                self.window_error_shown = True
                messagebox.showerror("Вікно не знайдено", f"Не вдалося знайти вікно '{self.window_name_var.get()}'. Перевірте точну назву.")
        else:
            self.status_indicator.itemconfig(self.indicator_circle, fill="gray", outline="gray")

    def poll_bot_status(self):
        yolo_settings = self.collect_yolo_settings()
        attack_targets = yolo_settings["target_classes"] or "немає"

        if self.bot.yolo_enabled:
            if self.bot.last_error:
                self.yolo_status_label.config(text=f"YOLO: Помилка\n{self.bot.last_error}")
            else:
                self.yolo_status_label.config(text=f"YOLO: працює\nМодель: {yolo_settings['model_path']}")
            labels = ", ".join(self.bot.last_detection_labels[:8]) if self.bot.last_detection_labels else "немає"
            self.detection_label.config(text=f"Видимі мітки: {labels}")
        else:
            self.yolo_status_label.config(text="YOLO: вимкнено")
            self.detection_label.config(text="Видимі мітки: н/д")

        resources = self.bot.last_categories.get("resources", [])
        bots = self.bot.last_categories.get("bots", [])
        attacks = self.bot.last_categories.get("attack", [])
        resource_text = ", ".join(item["label"] for item in resources[:4]) if resources else "немає"
        bot_text = ", ".join(item["label"] for item in bots[:4]) if bots else "немає"
        attack_text = ", ".join(item["label"] for item in attacks[:4]) if attacks else "немає"

        self.target_summary_label.config(text=f"Цілі атаки: {attack_targets}\nВиявлено: {attack_text}")
        self.resource_status_label.config(text=f"Ресурси в кадрі: {resource_text}")
        self.bot_warning_label.config(text=f"Інші боти / гравці: {bot_text}")

        hp = self.bot.last_resource_state.get("hp_percent")
        mp = self.bot.last_resource_state.get("mp_percent")
        pet_hp = self.bot.last_resource_state.get("pet_hp_percent")
        hp_text = self.bot.last_resource_state.get("hp_text")
        mp_text = self.bot.last_resource_state.get("mp_text")
        pet_hp_text = self.bot.last_resource_state.get("pet_hp_text")
        hp_ok = self.bot.last_resource_state.get("hp_ok")
        mp_ok = self.bot.last_resource_state.get("mp_ok")
        pet_hp_ok = self.bot.last_resource_state.get("pet_hp_ok")
        self.health_label.config(text=f"HP персонажа: {self._format_percent(hp)}{self._format_raw(hp_text)}{self._format_ocr_state(hp_ok, hp_text)}")
        self.mana_label.config(text=f"MP персонажа: {self._format_percent(mp)}{self._format_raw(mp_text)}{self._format_ocr_state(mp_ok, mp_text)}")
        self.pet_health_label.config(text=f"HP петомця: {self._format_percent(pet_hp)}{self._format_raw(pet_hp_text)}{self._format_ocr_state(pet_hp_ok, pet_hp_text)}")

        modes = self.collect_mode_settings()
        enabled_modes = [
            name
            for name, enabled in [("автофарм", modes["auto_farm"]), ("збір ресурсів", modes["resource_gather"]), ("петомець", modes["pet_mode"])]
            if enabled
        ]
        action_state = "enabled" if self.bot.actions_enabled else "disabled"
        mode_text = ", ".join(enabled_modes) if enabled_modes else "немає"
        action_state_uk = "увімкнено" if self.bot.actions_enabled else "вимкнено"
        self.mode_state_label.config(text=f"Дії: {action_state_uk}\nВибрані режими: {mode_text}")

        self.refresh_preview()
        if self.bot.monitoring:
            self.update_indicator()
        self.root.after(500, self.poll_bot_status)

    def refresh_preview(self):
        preview_state = self.bot.get_preview_state()
        frame = preview_state["frame"]
        if frame is None:
            return

        image = Image.fromarray(frame[:, :, ::-1])
        self._decorate_preview_image(image, preview_state)

        preview_frame = self.preview_canvas.master.master
        available_width = max(320, preview_frame.winfo_width() - 20)
        max_width = min(available_width, PREVIEW_MAX_SIZE[0])
        aspect_ratio = image.height / max(1, image.width)
        target_width = max_width
        target_height = int(target_width * aspect_ratio)

        if target_height > PREVIEW_MAX_SIZE[1]:
            target_height = PREVIEW_MAX_SIZE[1]
            target_width = int(target_height / max(aspect_ratio, 0.001))

        fitted = ImageOps.contain(
            image,
            (target_width, target_height),
            method=Image.Resampling.LANCZOS,
        )

        canvas_width = max(available_width, fitted.width)
        canvas_height = max(PREVIEW_MAX_SIZE[1], fitted.height)
        offset_x = max(0, (canvas_width - fitted.width) // 2)
        offset_y = max(0, (canvas_height - fitted.height) // 2)

        self.preview_image = ImageTk.PhotoImage(fitted)
        self.preview_canvas.config(width=canvas_width, height=canvas_height)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(offset_x, offset_y, image=self.preview_image, anchor="nw")
        self.preview_render_box = (offset_x, offset_y, fitted.width, fitted.height)
        self.preview_source_size = image.size

        self.refresh_preview_popout(image)

    def refresh_preview_popout(self, image):
        if self.popout_window is None or not self.popout_window.winfo_exists() or self.popout_canvas is None:
            return

        available_width = max(640, self.popout_window.winfo_width() - 40)
        available_height = max(360, self.popout_window.winfo_height() - 80)
        target_width = min(available_width, POP_OUT_PREVIEW_MAX_SIZE[0])
        target_height = min(available_height, POP_OUT_PREVIEW_MAX_SIZE[1])

        fitted = ImageOps.contain(
            image,
            (target_width, target_height),
            method=Image.Resampling.LANCZOS,
        )

        canvas_width = max(target_width, fitted.width)
        canvas_height = max(target_height, fitted.height)
        offset_x = max(0, (canvas_width - fitted.width) // 2)
        offset_y = max(0, (canvas_height - fitted.height) // 2)

        self.popout_preview_image = ImageTk.PhotoImage(fitted)
        self.popout_canvas.config(width=canvas_width, height=canvas_height)
        self.popout_canvas.delete("all")
        self.popout_canvas.create_image(offset_x, offset_y, image=self.popout_preview_image, anchor="nw")
        self.popout_preview_render_box = (offset_x, offset_y, fitted.width, fitted.height)

    def _decorate_preview_image(self, image, preview_state):
        draw = ImageDraw.Draw(image)

        for item in preview_state["boxes"]:
            x1, y1, x2, y2 = item["xyxy"]
            label = f"{item['label']} {item['confidence']:.2f}"
            color = self._pick_box_color(item["label"])
            draw.rectangle((x1, y1, x2, y2), outline=color, width=3)
            draw.text((x1 + 4, max(0, y1 - 14)), label, fill=color)

        hud_box = preview_state.get("hud_box")
        if hud_box:
            draw.rectangle(hud_box, outline="yellow", width=2)
            draw.text((hud_box[0] + 4, max(0, hud_box[1] - 14)), "HUD", fill="yellow")

        text_rois = preview_state.get("text_rois", {})
        self.draw_box_overlay(draw, text_rois.get("hp"), "red", "OCR HP")
        self.draw_box_overlay(draw, text_rois.get("mp"), "cyan", "OCR MP")
        self.draw_box_overlay(draw, text_rois.get("pet"), "orange", "OCR PET")

        if self.selection_start and self.selection_current:
            x1, y1, x2, y2 = self._normalized_box(self.selection_start, self.selection_current)
            draw.rectangle((x1, y1, x2, y2), outline="deepskyblue", width=3)
            draw.text((x1 + 4, max(0, y1 - 14)), "SELECT", fill="deepskyblue")

    def draw_roi_overlay(self, draw, image_size, roi_text, color, label):
        roi = self.parse_roi(roi_text)
        if roi is None:
            return

        width, height = image_size
        x, y, w, h = roi
        if max(abs(x), abs(y), abs(w), abs(h)) <= 1.0:
            x = width * x
            y = height * y
            w = width * w
            h = height * h

        x1 = max(0, int(x))
        y1 = max(0, int(y))
        x2 = min(width, int(x + w))
        y2 = min(height, int(y + h))
        if x2 <= x1 or y2 <= y1:
            return

        draw.rectangle((x1, y1, x2, y2), outline=color, width=2)
        draw.text((x1 + 4, y1 + 4), label, fill=color)

    @staticmethod
    def draw_box_overlay(draw, roi, color, label):
        if roi is None:
            return

        x1, y1, x2, y2 = [int(value) for value in roi]
        if x2 <= x1 or y2 <= y1:
            return

        draw.rectangle((x1, y1, x2, y2), outline=color, width=2)
        draw.text((x1 + 4, max(0, y1 - 14)), label, fill=color)

    def start_roi_selection(self, target):
        preview_state = self.bot.get_preview_state()
        if preview_state["frame"] is None:
            messagebox.showwarning("Немає кадру", "Дочекайся живого кадру в прев'ю, а потім запускай ручне виділення.")
            return

        self.selection_target = target
        self.selection_start = None
        self.selection_current = None
        target_label = {"hp": "HP персонажа", "mp": "MP персонажа", "pet": "HP петомця"}.get(target, target)
        self.selection_status_label.config(
            text=f"Режим виділення: {target_label}. Можна тягнути рамку на звичайному або великому прев'ю.",
            fg="deepskyblue4",
        )
        self.refresh_preview()

    def on_preview_press(self, event):
        if not self.selection_target:
            return

        point = self._preview_to_frame_point(event.x, event.y)
        if point is None:
            return

        self.selection_start = point
        self.selection_current = point
        self.refresh_preview()

    def on_preview_drag(self, event):
        if not self.selection_target or self.selection_start is None:
            return

        point = self._preview_to_frame_point(event.x, event.y)
        if point is None:
            return

        self.selection_current = point
        self.refresh_preview()

    def on_preview_release(self, event):
        if not self.selection_target or self.selection_start is None:
            return

        point = self._preview_to_frame_point(event.x, event.y)
        self._finish_roi_selection(point)

    def _finish_roi_selection(self, point):
        if point is None:
            self._clear_selection_state()
            self.refresh_preview()
            return

        self.selection_current = point
        x1, y1, x2, y2 = self._normalized_box(self.selection_start, self.selection_current)
        if x2 - x1 < 4 or y2 - y1 < 4:
            self.selection_status_label.config(text="Виділення замале. Спробуй ще раз.", fg="firebrick")
            self._clear_selection_state()
            self.refresh_preview()
            return

        roi_text = f"{x1},{y1},{x2 - x1},{y2 - y1}"
        if self.selection_target == "hp":
            self.hp_roi_var.set(roi_text)
        elif self.selection_target == "mp":
            self.mp_roi_var.set(roi_text)
        else:
            self.pet_hp_roi_var.set(roi_text)

        self.cv_enabled_var.set(True)
        self.selection_status_label.config(text=f"ROI збережено: {roi_text}", fg="darkgreen")
        self._clear_selection_state()
        self.apply_bot_configuration()
        self.refresh_preview()

    def _clear_selection_state(self):
        self.selection_target = None
        self.selection_start = None
        self.selection_current = None

    @staticmethod
    def _normalized_box(start, end):
        return (
            min(start[0], end[0]),
            min(start[1], end[1]),
            max(start[0], end[0]),
            max(start[1], end[1]),
        )

    def _preview_to_frame_point(self, canvas_x, canvas_y):
        return self._render_to_frame_point(canvas_x, canvas_y, self.preview_render_box)

    def _render_to_frame_point(self, canvas_x, canvas_y, render_box):
        if not render_box or not self.preview_source_size:
            return None

        offset_x, offset_y, render_w, render_h = render_box
        source_w, source_h = self.preview_source_size
        local_x = canvas_x - offset_x
        local_y = canvas_y - offset_y

        if local_x < 0 or local_y < 0 or local_x > render_w or local_y > render_h:
            return None

        frame_x = int((local_x / max(1, render_w)) * source_w)
        frame_y = int((local_y / max(1, render_h)) * source_h)
        return (
            max(0, min(source_w - 1, frame_x)),
            max(0, min(source_h - 1, frame_y)),
        )

    def open_preview_popout(self):
        if self.popout_window is not None and self.popout_window.winfo_exists():
            self.popout_window.deiconify()
            self.popout_window.lift()
            self.refresh_preview()
            return

        self.popout_window = tk.Toplevel(self.root)
        self.popout_window.title("Велике прев'ю")
        self.popout_window.geometry("1400x900")
        self.popout_window.configure(bg=self.root.cget("bg"))
        self.popout_window.protocol("WM_DELETE_WINDOW", self.close_preview_popout)

        info_label = tk.Label(
            self.popout_window,
            text="Тут можна точніше виділяти ROI мишкою. Координати збережуться так само, як і зі звичайного прев'ю.",
            justify="left",
            bg=self.root.cget("bg"),
        )
        info_label.pack(anchor="w", padx=12, pady=(12, 6))

        self.popout_canvas = tk.Canvas(self.popout_window, bg=self.root.cget("bg"), highlightthickness=0)
        self.popout_canvas.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.popout_canvas.bind("<ButtonPress-1>", self.on_popout_preview_press)
        self.popout_canvas.bind("<B1-Motion>", self.on_popout_preview_drag)
        self.popout_canvas.bind("<ButtonRelease-1>", self.on_popout_preview_release)
        self.popout_window.bind("<Configure>", self.on_popout_window_resize)
        self.refresh_preview()

    def close_preview_popout(self):
        if self.popout_window is not None and self.popout_window.winfo_exists():
            self.popout_window.destroy()
        self.popout_window = None
        self.popout_canvas = None
        self.popout_preview_image = None
        self.popout_preview_render_box = None

    def on_popout_window_resize(self, event=None):
        if event is not None and event.widget is not self.popout_window:
            return
        self.refresh_preview()

    def on_popout_preview_press(self, event):
        if not self.selection_target:
            return

        point = self._render_to_frame_point(event.x, event.y, self.popout_preview_render_box)
        if point is None:
            return

        self.selection_start = point
        self.selection_current = point
        self.refresh_preview()

    def on_popout_preview_drag(self, event):
        if not self.selection_target or self.selection_start is None:
            return

        point = self._render_to_frame_point(event.x, event.y, self.popout_preview_render_box)
        if point is None:
            return

        self.selection_current = point
        self.refresh_preview()

    def on_popout_preview_release(self, event):
        if self.popout_canvas is None or not self.selection_target or self.selection_start is None:
            return

        point = self._render_to_frame_point(event.x, event.y, self.popout_preview_render_box)
        self._finish_roi_selection(point)

    def save_current_frame(self):
        preview_state = self.bot.get_preview_state()
        frame = preview_state["frame"]
        if frame is None:
            messagebox.showwarning("Немає кадру", "Поки що немає захопленого кадру.")
            return

        samples_dir = os.path.join(os.getcwd(), "training_samples")
        os.makedirs(samples_dir, exist_ok=True)
        filename = datetime.now().strftime("frame_%Y%m%d_%H%M%S.png")
        filepath = os.path.join(samples_dir, filename)
        Image.fromarray(frame[:, :, ::-1]).save(filepath)
        self.training_status_label.config(text=f"Збережено: {filepath}")

    @staticmethod
    def _format_percent(value):
        return "н/д" if value is None else f"{value:.1f}%"

    @staticmethod
    def _format_raw(value):
        return "" if not value else f" ({value})"

    @staticmethod
    def _format_ocr_state(ok, raw_value):
        if ok:
            return " [OCR OK]"
        if raw_value:
            return " [OCR FAIL]"
        return ""

    def _pick_box_color(self, label):
        label = label.lower()
        if label in self.bot.class_settings["attack"]:
            return "lime"
        if label in self.bot.class_settings["resources"]:
            return "gold"
        if label in self.bot.class_settings["bots"]:
            return "magenta"
        return "white"

    @staticmethod
    def parse_roi(value):
        if not isinstance(value, str) or not value.strip():
            return None
        parts = [part.strip() for part in value.split(",")]
        if len(parts) != 4:
            return None
        try:
            return tuple(float(part) for part in parts)
        except ValueError:
            return None

    def toggle_bot(self):
        if self.bot.actions_enabled:
            self.stop_bot()
        else:
            self.start_bot()

    def on_f12(self, event=None):
        self.toggle_bot()

    def run(self):
        self.root.mainloop()

    def on_close(self):
        self.bot.stop_monitoring()
        self.save_all_config()
        self.root.destroy()
