import tkinter as tk
from tkinter import ttk
from bot.bot_loop import BotLoop
import json
import os


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PW AI Bot")
        self.root.geometry("500x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind_all("<F12>", self.on_f12)

        self.bot = BotLoop()
        self.config_file = "config.json"
        self.load_config()

        self.create_tabs()

    def create_tabs(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        # Bot tab
        self.bot_tab = tk.Frame(notebook)
        notebook.add(self.bot_tab, text="Bot")

        # Settings tab
        self.settings_tab = tk.Frame(notebook)
        notebook.add(self.settings_tab, text="Settings")

        # Training tab
        self.training_tab = tk.Frame(notebook)
        notebook.add(self.training_tab, text="Training")

        self.create_bot_tab()
        self.create_settings_tab()
        self.create_training_tab()

    def create_bot_tab(self):
        self.bot_tab.columnconfigure(0, weight=1)
        self.bot_tab.columnconfigure(1, weight=1)

        self.status_label = tk.Label(self.bot_tab, text="Status: Stopped")
        self.status_label.grid(row=0, column=0, columnspan=2, pady=6)

        left_frame = tk.Frame(self.bot_tab)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=10)

        right_frame = tk.Frame(self.bot_tab)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)

        info_frame = tk.Frame(left_frame)
        info_frame.pack(anchor="w", fill="x")

        self.nickname_label = tk.Label(info_frame, text="Нік: Герой", font=("Arial", 12, "bold"))
        self.nickname_label.pack(anchor="w")

        self.health_label = tk.Label(info_frame, text="Життя: 100%", font=("Arial", 11), fg="red")
        self.health_label.pack(anchor="w", pady=(4, 0))

        self.mana_label = tk.Label(info_frame, text="Мана: 100%", font=("Arial", 11), fg="blue")
        self.mana_label.pack(anchor="w", pady=(2, 0))

        button_frame = tk.Frame(left_frame)
        button_frame.pack(pady=10)

        self.toggle_button = tk.Button(button_frame, text="Start", width=12, command=self.toggle_bot)
        self.toggle_button.pack(side="left", padx=(0, 10))

        self.status_indicator = tk.Canvas(button_frame, width=20, height=20, bg="lightgray", highlightthickness=0)
        self.status_indicator.pack(side="left")
        self.indicator_circle = self.status_indicator.create_oval(2, 2, 18, 18, fill="gray", outline="gray")

        self.note_label = tk.Label(left_frame, text="Натисніть F12 для перемикання бота")
        self.note_label.pack(pady=5)

        self.auto_farm_var = tk.BooleanVar()
        self.resource_gather_var = tk.BooleanVar()

        self.auto_farm_checkbox = tk.Checkbutton(left_frame, text="Авто фарм", variable=self.auto_farm_var)
        self.auto_farm_checkbox.pack(anchor="w", pady=2)

        self.resource_gather_checkbox = tk.Checkbutton(left_frame, text="Збір ресурсів", variable=self.resource_gather_var)
        self.resource_gather_checkbox.pack(anchor="w", pady=2)

        self.pet_checkbox_var = tk.BooleanVar()
        self.pet_checkbox = tk.Checkbutton(left_frame, text="Працювати з петомцем", variable=self.pet_checkbox_var)
        self.pet_checkbox.pack(anchor="w", pady=2)

        pet_title = tk.Label(right_frame, text="Петомец", font=("Arial", 12, "bold"))
        pet_title.pack(anchor="w")

        self.pet_name_label = tk.Label(right_frame, text="Ім'я: Пухнастик", font=("Arial", 11))
        self.pet_name_label.pack(anchor="w", pady=(8, 0))

        self.pet_health_label = tk.Label(right_frame, text="Життя: 85%", font=("Arial", 11), fg="red")
        self.pet_health_label.pack(anchor="w", pady=(4, 0))

    def create_settings_tab(self):
        canvas = tk.Canvas(self.settings_tab)
        scrollbar = ttk.Scrollbar(self.settings_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        attack_title = tk.Label(scrollable_frame, text="Налаштування атаки", font=("Arial", 12, "bold"))
        attack_title.pack(anchor="w", padx=15, pady=(15, 10))

        self.attack_buttons = []

        for i in range(1, 6):
            btn_frame = tk.Frame(scrollable_frame)
            btn_frame.pack(fill="x", padx=15, pady=5)

            var = tk.BooleanVar()
            self.attack_buttons.append({
                'number': i,
                'enabled': var,
                'timer': tk.StringVar(value="1.0")
            })

            checkbox = tk.Checkbutton(btn_frame, text=f"Кнопка {i}", variable=var)
            checkbox.pack(side="left", padx=(0, 10))

            timer_label = tk.Label(btn_frame, text="Таймер (сек):")
            timer_label.pack(side="left", padx=(0, 5))

            timer_entry = tk.Entry(btn_frame, textvariable=self.attack_buttons[i-1]['timer'], width=8)
            timer_entry.pack(side="left")

        # Healing settings
        healing_frame = tk.Frame(scrollable_frame)
        healing_frame.pack(fill="x", padx=15, pady=(20, 10))

        healing_title = tk.Label(healing_frame, text="Налаштування лікування", font=("Arial", 12, "bold"))
        healing_title.pack(anchor="w")

        hp_frame = tk.Frame(healing_frame)
        hp_frame.pack(fill="x", pady=(10, 5))

        hp_label = tk.Label(hp_frame, text="HP для хіл (%):")
        hp_label.pack(side="left")

        self.heal_hp_var = tk.IntVar(value=50)
        hp_scale = tk.Scale(hp_frame, from_=0, to=100, orient="horizontal", variable=self.heal_hp_var)
        hp_scale.pack(side="right", fill="x", expand=True)

        heal_key_frame = tk.Frame(healing_frame)
        heal_key_frame.pack(fill="x", pady=(5, 0))

        heal_key_label = tk.Label(heal_key_frame, text="Клавіша хіл:")
        heal_key_label.pack(side="left")

        self.heal_key_var = tk.StringVar(value="F1")
        heal_key_menu = tk.OptionMenu(heal_key_frame, self.heal_key_var, "F1", "F2", "F3", "F4", "F5")
        heal_key_menu.pack(side="right")

        # Mana restoration settings
        mana_frame = tk.Frame(scrollable_frame)
        mana_frame.pack(fill="x", padx=15, pady=(20, 10))

        mana_title = tk.Label(mana_frame, text="Налаштування поповнення мп", font=("Arial", 12, "bold"))
        mana_title.pack(anchor="w")

        mp_frame = tk.Frame(mana_frame)
        mp_frame.pack(fill="x", pady=(10, 5))

        mp_label = tk.Label(mp_frame, text="MP для поповнення (%):")
        mp_label.pack(side="left")

        self.restore_mp_var = tk.IntVar(value=30)
        mp_scale = tk.Scale(mp_frame, from_=0, to=100, orient="horizontal", variable=self.restore_mp_var)
        mp_scale.pack(side="right", fill="x", expand=True)

        restore_key_frame = tk.Frame(mana_frame)
        restore_key_frame.pack(fill="x", pady=(5, 0))

        restore_key_label = tk.Label(restore_key_frame, text="Клавіша поповнення:")
        restore_key_label.pack(side="left")

        self.restore_key_var = tk.StringVar(value="F2")
        restore_key_menu = tk.OptionMenu(restore_key_frame, self.restore_key_var, "F1", "F2", "F3", "F4", "F5")
        restore_key_menu.pack(side="right")

        # Pet healing settings
        pet_healing_frame = tk.Frame(scrollable_frame)
        pet_healing_frame.pack(fill="x", padx=15, pady=(20, 10))

        pet_healing_title = tk.Label(pet_healing_frame, text="Налаштування лікування петомца", font=("Arial", 12, "bold"))
        pet_healing_title.pack(anchor="w")

        pet_hp_frame = tk.Frame(pet_healing_frame)
        pet_hp_frame.pack(fill="x", pady=(10, 5))

        pet_hp_label = tk.Label(pet_hp_frame, text="HP петомца для хіл (%):")
        pet_hp_label.pack(side="left")

        self.pet_heal_hp_var = tk.IntVar(value=40)
        pet_hp_scale = tk.Scale(pet_hp_frame, from_=0, to=100, orient="horizontal", variable=self.pet_heal_hp_var)
        pet_hp_scale.pack(side="right", fill="x", expand=True)

        pet_heal_key_frame = tk.Frame(pet_healing_frame)
        pet_heal_key_frame.pack(fill="x", pady=(5, 0))

        pet_heal_key_label = tk.Label(pet_heal_key_frame, text="Клавіша хіл петомца:")
        pet_heal_key_label.pack(side="left")

        self.pet_heal_key_var = tk.StringVar(value="F3")
        pet_heal_key_menu = tk.OptionMenu(pet_heal_key_frame, self.pet_heal_key_var, "F1", "F2", "F3", "F4", "F5")
        pet_heal_key_menu.pack(side="right")

        save_settings_button = tk.Button(scrollable_frame, text="Зберегти налаштування", command=self.on_save_settings, width=20)
        save_settings_button.pack(anchor="w", padx=15, pady=(15, 20))

        # Завантажити збережені налаштування
        self.load_settings_from_config()

    def create_training_tab(self):
        training_frame = tk.Frame(self.training_tab, padx=20, pady=20)
        training_frame.pack(fill="x")

        title_label = tk.Label(training_frame, text="Налаштування вікна", font=("Arial", 12, "bold"))
        title_label.pack(anchor="w", pady=(0, 15))

        instructions_label = tk.Label(training_frame, text="Введіть назву вікна клієнта для захоплення:", font=("Arial", 10))
        instructions_label.pack(anchor="w", pady=(0, 5))

        self.window_name_var = tk.StringVar()
        if self.window_name:
            self.window_name_var.set(self.window_name)
        else:
            self.window_name_var.set("Введіть назву вікна...")

        self.window_name_entry = tk.Entry(training_frame, textvariable=self.window_name_var, width=40, font=("Arial", 10))
        self.window_name_entry.pack(anchor="w", pady=(0, 10), fill="x")

        save_button = tk.Button(training_frame, text="Запам'ятати", command=self.save_window_name, width=15)
        save_button.pack(anchor="w")

    def load_config(self):
        self.window_name = None
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.window_name = config.get('window_name', None)
                    self.config = config
            except:
                self.config = {}
        else:
            self.config = {}

    def save_all_config(self):
        """Зберегти всі налаштування"""
        config = {
            'window_name': self.window_name_var.get().strip() if self.window_name_var.get().strip() and self.window_name_var.get().strip() != "Введіть назву вікна..." else self.window_name,
            'attack_buttons': [
                {
                    'number': btn['number'],
                    'enabled': btn['enabled'].get(),
                    'timer': btn['timer'].get()
                }
                for btn in self.attack_buttons
            ],
            'healing': {
                'hp_threshold': self.heal_hp_var.get(),
                'key': self.heal_key_var.get()
            },
            'mana_restoration': {
                'mp_threshold': self.restore_mp_var.get(),
                'key': self.restore_key_var.get()
            },
            'pet_healing': {
                'hp_threshold': self.pet_heal_hp_var.get(),
                'key': self.pet_heal_key_var.get()
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def load_settings_from_config(self):
        """Завантажити налаштування з конфіга"""
        if not hasattr(self, 'config'):
            return
        
        # Завантажити налаштування атаки
        if 'attack_buttons' in self.config:
            for i, btn_config in enumerate(self.config['attack_buttons']):
                if i < len(self.attack_buttons):
                    self.attack_buttons[i]['enabled'].set(btn_config.get('enabled', False))
                    self.attack_buttons[i]['timer'].set(btn_config.get('timer', '1.0'))
        
        # Завантажити налаштування хілу
        if 'healing' in self.config:
            healing = self.config['healing']
            self.heal_hp_var.set(healing.get('hp_threshold', 50))
            self.heal_key_var.set(healing.get('key', 'F1'))
        
        # Завантажити налаштування поповнення мп
        if 'mana_restoration' in self.config:
            mana = self.config['mana_restoration']
            self.restore_mp_var.set(mana.get('mp_threshold', 30))
            self.restore_key_var.set(mana.get('key', 'F2'))
        
        # Завантажити налаштування хілу петомца
        if 'pet_healing' in self.config:
            pet = self.config['pet_healing']
            self.pet_heal_hp_var.set(pet.get('hp_threshold', 40))
            self.pet_heal_key_var.set(pet.get('key', 'F3'))

    def save_window_name(self):
        new_window_name = self.window_name_var.get().strip()
        if new_window_name and new_window_name != "Введіть назву вікна...":
            self.window_name = new_window_name
            self.save_all_config()

    def on_save_settings(self):
        self.save_all_config()
        from tkinter import messagebox
        messagebox.showinfo("Збережено", "Налаштування збережено")

    def start_bot(self):
        window_name = self.window_name_var.get().strip()
        
        if not window_name or window_name == "Введіть назву вікна...":
            from tkinter import messagebox
            messagebox.showerror("Помилка", "Будь ласка, спочатку встановіть назву вікна у вкладці 'Training'")
            return
        
        self.bot.set_window_name(window_name)
        self.bot.set_attack_buttons(self.attack_buttons)
        self.bot.start()
        
        # Перевірити чи успішно захоплено вікно після завантаження
        self.root.after(500, self.update_indicator)
        
        self.status_label.config(text="Status: Running")
        self.toggle_button.config(text="Stop")

    def stop_bot(self):
        self.bot.stop()
        self.status_label.config(text="Status: Stopped")
        self.toggle_button.config(text="Start")
        self.update_indicator()

    def update_indicator(self):
        """Оновити індикатор статусу захоплення вікна"""
        if self.bot.capture_success:
            self.status_indicator.itemconfig(self.indicator_circle, fill="green", outline="darkgreen")
        else:
            if self.bot.running:
                self.status_indicator.itemconfig(self.indicator_circle, fill="red", outline="darkred")
                from tkinter import messagebox
                messagebox.showerror("Помилка", f"Не вдалось знайти вікно '{self.window_name_var.get()}'\n\nПеревірте точну назву вікна")
            else:
                self.status_indicator.itemconfig(self.indicator_circle, fill="gray", outline="gray")

    def toggle_bot(self):
        if self.bot.running:
            self.stop_bot()
        else:
            self.start_bot()

    def on_f12(self, event=None):
        self.toggle_bot()

    def run(self):
        self.root.mainloop()

    def on_close(self):
        self.bot.stop()
        self.save_all_config()
        self.root.destroy()
        self.root.destroy()