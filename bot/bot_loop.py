import threading
import time
import win32gui
import win32ui
import win32con
import pyautogui


class BotLoop:
    def __init__(self):
        self.running = False
        self.thread = None
        self.window_name = None
        self.hwnd = None
        self.capture_success = False
        self.attack_buttons = None
        self.button_timers = {}

    def set_window_name(self, window_name):
        self.window_name = window_name

    def set_attack_buttons(self, attack_buttons):
        """Встановити налаштування кнопок атаки"""
        self.attack_buttons = attack_buttons
        # Ініціалізувати таймери для кнопок
        for btn in attack_buttons:
            self.button_timers[btn['number']] = time.time()

    def find_window(self):
        """Знайти вікно за назвою"""
        try:
            self.hwnd = win32gui.FindWindow(None, self.window_name)
            if self.hwnd == 0:
                self.hwnd = None
                return False
            return True
        except Exception as e:
            print(f"Помилка при пошуку вікна: {e}")
            return False

    def capture_screenshot(self):
        """Захопити скріншот вікна"""
        if not self.hwnd:
            return False
        
        try:
            hwndDC = win32gui.GetWindowDC(self.hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            width = right - left
            height = bottom - top

            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)

            saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(self.hwnd, hwndDC)

            return True
        except Exception as e:
            print(f"Помилка при захопленні екрану: {e}")
            return False

    def press_button(self, button_number):
        """Натиснути клавішу для кнопки атаки (1-5)"""
        try:
            if self.hwnd:
                try:
                    win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(self.hwnd)
                    win32gui.SetFocus(self.hwnd)
                except Exception:
                    pass
                time.sleep(0.15)

            pyautogui.press(str(button_number))
            print(f"Натиснута клавіша {button_number}")
        except Exception as e:
            print(f"Помилка при натисканні клавіші {button_number}: {e}")

    def start(self):
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.hwnd = None
        self.capture_success = False
        self.button_timers = {}

    def loop(self):
        print("Bot started")

        if self.window_name:
            if self.find_window():
                self.capture_success = True
                print(f"Вікно '{self.window_name}' успішно захоплене")
            else:
                self.capture_success = False
                print(f"Помилка: не вдалось знайти вікно '{self.window_name}'")

        while self.running:
            if self.capture_success and self.hwnd and self.attack_buttons:
                current_time = time.time()
                
                # Перевірити кожну кнопку атаки
                for btn in self.attack_buttons:
                    if btn['enabled'].get():  # Якщо чекбокс увімкнений
                        timer_value = float(btn['timer'].get())
                        btn_number = btn['number']
                        
                        # Перевірити чи вийшов час для цієї кнопки
                        if current_time - self.button_timers[btn_number] >= timer_value:
                            self.press_button(btn_number)
                            self.button_timers[btn_number] = current_time
            
            self.capture_screenshot()
            time.sleep(0.05)  # Перевіряти кожні 50мс

        print("Bot stopped")
