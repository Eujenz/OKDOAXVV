import re

from ok import BaseTask

import time
import random
import math

class MyBaseTask(BaseTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_mouse_x = 0
        self._last_mouse_y = 0

    def operate(self, func):
        self.executor.interaction.operate(func, block=True)

    def do_mouse_down(self, key):
        self.executor.interaction.do_mouse_down(key=key)

    def do_mouse_up(self, key):
        self.executor.interaction.do_mouse_up(key=key)

    def do_send_key_down(self, key):
        self.executor.interaction.do_send_key_down(key)

    def do_send_key_up(self, key):
        self.executor.interaction.do_send_key_up(key)

    def _simulate_mouse_move(self, target_x, target_y):
        """產生一連串向目標靠近的 MOUSEMOVE 軌跡（簡單的非線性差值）"""
        try:
            import win32api
            import win32con
            import win32gui
            # 透過 win32gui 直接取得遊戲視窗控制代碼
            hwnd = win32gui.FindWindow(None, "DOAX VenusVacation")
            if not hwnd:
                self.log_debug("找不到視窗 'DOAX VenusVacation'")
                return
            
            # 若傳入的目標點是相對座標 (0 ~ 1)，則轉換為絕對視窗像素座標
            if 0 < target_x <= 1.0 and 0 < target_y <= 1.0:
                rect = win32gui.GetClientRect(hwnd)
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]
                target_x = target_x * width
                target_y = target_y * height
            
            # 從上一次的位置移動到新位置，如果沒有上一次位置則從附近角落開始
            start_x = self._last_mouse_x if self._last_mouse_x > 0 else target_x - random.randint(200, 400)
            start_y = self._last_mouse_y if self._last_mouse_y > 0 else target_y - random.randint(100, 200)
            
            # --- Bezier 曲線模擬 ---
            # 隨機產生一個控制點 P1，讓軌跡形成一個弧形 (Arc) 而非直線
            # 控制點偏移量取決於起點到終點的距離
            distance = math.hypot(target_x - start_x, target_y - start_y)
            bow_factor = random.uniform(0.1, 0.3)  # 弧度參數
            # 隨機向左偏或向右偏
            direction = 1 if random.random() > 0.5 else -1
            
            # 中間點
            mid_x = (start_x + target_x) / 2
            mid_y = (start_y + target_y) / 2
            
            # 垂直於直線的向量
            dx = target_x - start_x
            dy = target_y - start_y
            perp_x = -dy * bow_factor * direction
            perp_y =  dx * bow_factor * direction
            
            ctrl_x = mid_x + perp_x
            ctrl_y = mid_y + perp_y
            
            # 增加軌跡密度與總時間，讓軌跡有肉眼可見的「滑動」
            steps = random.randint(15, 30)
            for i in range(1, steps + 1):
                raw_t = i / steps
                # ease-in-out (smoothstep) 讓起步慢、中段快、末端慢
                t = raw_t * raw_t * (3 - 2 * raw_t)
                
                # 計算二次 Bezier 曲線座標
                # B(t) = (1-t)^2 * P0 + 2(1-t)t * P1 + t^2 * P2
                omt = 1 - t
                curr_x = int(omt**2 * start_x + 2 * omt * t * ctrl_x + t**2 * target_x)
                curr_y = int(omt**2 * start_y + 2 * omt * t * ctrl_y + t**2 * target_y)
                
                # 末端微小手抖，人類在精確對準按鈕時會有微小校正
                jitter_factor = 2.0 * (1 - t) * t  # 僅在移動中段產生最大抖動，末端收斂
                curr_x += int(random.gauss(0, jitter_factor))
                curr_y += int(random.gauss(0, jitter_factor))
                
                lparam = win32api.MAKELONG(max(0, curr_x), max(0, curr_y))
                win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
                
                # 每次移動的微小停頓 (8~15ms)
                time.sleep(random.uniform(0.008, 0.015))
                
            self._last_mouse_x = target_x
            self._last_mouse_y = target_y
        except Exception as e:
            self.log_debug(f"WM_MOUSEMOVE 模擬失敗: {e}")

    def click(self, *args, **kwargs):
        """覆寫 click，在點擊前先注入擬人的 MOUSEMOVE 軌跡"""
        x = kwargs.get('x', -1)
        y = kwargs.get('y', -1)
        move = kwargs.get('move', True)
        
        # 嘗試從 args 取出 x, y (或者 Box)
        if len(args) >= 1:
            arg0 = args[0]
            if isinstance(arg0, (int, float)):
                x = arg0
            elif hasattr(arg0, 'x') and hasattr(arg0, 'y'): # 如果是 ok-script 的 Box
                # 取 Box 的中心點
                x = arg0.x + getattr(arg0, 'width', 0) / 2
                y = arg0.y + getattr(arg0, 'height', 0) / 2

        if len(args) >= 2 and isinstance(args[1], (int, float)):
            y = args[1]
            
        if move and x != -1 and y != -1:
            # 加上 Log 確認真的有觸發
            self.log_debug(f"🔍 模擬滑鼠軌跡至 ({int(x)}, {int(y)})")
            self._simulate_mouse_move(x, y)
            
        return super().click(*args, **kwargs)



