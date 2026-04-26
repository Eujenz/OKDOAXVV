"""
HumanBehavior — 擬人化行為引擎 v2
===================================
將機械式的自動化操作轉化為接近真實人類的行為模式。

核心原理：
- Fitts's Law：按鈕越小/越遠，點擊花的時間越長
- Log-Normal 分佈：人類反應時間呈右偏分佈，非對稱高斯
- 時間自相關 (AR(1))：人類的節奏有「慣性」，不是每次獨立取樣
- S-curve 疲勞模型：前期穩定 → 中期急降 → 具備閒置恢復
- 學習效應：前幾輪較慢（不熟悉）→ 穩定 → 後期受疲勞退化
- Session 個性：每次啟動產生不同的行為「人格」
- 泊松微休息：無週期性的隨機休息觸發
"""

import math
import random
import time


class HumanBehavior:
    """提供擬人化的延遲、座標、節奏管理。"""

    def __init__(self, task=None):
        self.task = task
        self._start_time = time.monotonic()
        self._action_count = 0
        self._consecutive_fast = 0      # 連續快速操作計數
        self._last_click_time = 0.0
        self._fatigue_level = 0.0       # 0.0 ~ 1.0

        # ── Session 個性 (每次啟動不同) ────────────────
        self._personality = {
            'speed_factor': random.uniform(0.85, 1.15),       # 整體速度偏好
            'accuracy': random.uniform(0.88, 1.0),            # 點擊精度
            'patience': random.uniform(0.8, 1.25),            # 等待時長偏好
            'distraction_prone': random.uniform(0.03, 0.07),  # 分心傾向
        }

        # ── 時間自相關狀態 (AR(1) 節奏慣性) ─────────────
        self._tempo_state = 0.0
        self._tempo_inertia = random.uniform(0.6, 0.8)  # 慣性係數

    def _debug_log(self, msg):
        """將內部狀態以 Log 印出到 UI"""
        if self.task and hasattr(self.task, 'log_debug'):
            self.task.log_info(f"🧠 [Human] {msg}")
        else:
            print(f"🧠 [Human] {msg}")

    # ── 時間自相關噪聲 ───────────────────────────────────

    def _correlated_delay(self, base_delay):
        """
        產生具有時間自相關的延遲。
        人類的操作速度有「慣性」— 如果這一秒反應慢，下一秒也大概率偏慢。
        """
        innovation = random.gauss(0, 0.08)
        self._tempo_state = (
            self._tempo_inertia * self._tempo_state
            + (1 - self._tempo_inertia) * innovation
        )
        
        # ── Regime Shift (節奏突變) ────────────
        # 約 2% 的機率出現突發性的節奏轉變 (突然變得很慢或突然振作變快)
        if random.random() < 0.02:
            self._tempo_state += random.uniform(-0.4, 0.6)
            
        # 限制極端值避免行為異常
        self._tempo_state = max(-0.5, min(self._tempo_state, 1.2))
        
        return base_delay * (1 + self._tempo_state)

    # ── 學習曲線 ─────────────────────────────────────────

    def _learning_factor(self):
        """
        模擬肌肉記憶的學習效應：
        - 前 5 輪：較慢（還在適應介面）
        - 5~30 輪：穩定期（已經熟悉流程）
        - 30+ 輪：開始受疲勞拖慢
        """
        n = self._action_count
        if n < 3:
            return 1.25 - 0.05 * n   # 1.25 → 1.10
        elif n < 8:
            return 1.10 - 0.02 * (n - 3)  # 1.10 → 1.00
        elif n < 30:
            return 1.0                # 穩定期
        else:
            return 1.0 + self.fatigue * 0.25  # 後期受疲勞影響

    # ── 疲勞模型 (S-curve + 自然恢復) ────────────────────

    def _update_fatigue(self):
        """
        S 形疲勞曲線：
        - 前 15 分鐘幾乎不疲勞
        - 30~60 分鐘急劇上升
        - 長時間無操作會微幅恢復 (模擬「歇一下」)
        """
        elapsed_minutes = (time.monotonic() - self._start_time) / 60.0

        # S-curve: sigmoid 中心在 40 分鐘
        time_fatigue = 1.0 / (1.0 + math.exp(-0.12 * (elapsed_minutes - 40))) * 0.6

        # 連續快速操作累積的爆發疲勞
        burst_fatigue = min(self._consecutive_fast / 20.0, 1.0) * 0.35

        # 長時間無操作 → 微幅恢復 (模擬短暫休息後精神好一點)
        if self._last_click_time > 0:
            idle_seconds = time.monotonic() - self._last_click_time
            if idle_seconds > 5.0:
                recovery = min(idle_seconds / 120.0, 0.12)
                time_fatigue = max(0, time_fatigue - recovery)

        self._fatigue_level = min(time_fatigue + burst_fatigue, 1.0)

    @property
    def fatigue(self):
        self._update_fatigue()
        return self._fatigue_level

    # ── 點擊座標擬人化 ──────────────────────────────────

    @staticmethod
    def humanize_click_position(box):
        """
        在按鈕範圍內生成擬人化點擊座標。
        使用高斯分佈，讓點擊集中在中心偏移處（人類不會精準點中心）。
        """
        cx = box.x + box.width / 2
        cy = box.y + box.height / 2

        # 人類傾向偏右下方一點（慣用手偏移）
        hand_bias_x = box.width * random.uniform(0.02, 0.05)
        hand_bias_y = box.height * random.uniform(0.02, 0.06)

        # 高斯分佈：sigma = 按鈕尺寸的 15%，確保 99.7% 落在按鈕內
        sigma_x = box.width * 0.15
        sigma_y = box.height * 0.15

        # 安全邊距
        margin_x = box.width * 0.08
        margin_y = box.height * 0.08

        click_x = random.gauss(cx + hand_bias_x, sigma_x)
        click_y = random.gauss(cy + hand_bias_y, sigma_y)

        # Clamp 到安全範圍
        click_x = max(box.x + margin_x, min(click_x, box.x + box.width - margin_x))
        click_y = max(box.y + margin_y, min(click_y, box.y + box.height - margin_y))

        return int(click_x), int(click_y)

    # ── 按壓時長 (Fitts's Law 啟發) ────────────────────

    def calc_press_duration(self, box):
        """
        按壓時長基於按鈕大小：
        - 大按鈕 → 快速、自信地按
        - 小按鈕 → 稍微猶豫、按久一點
        加入疲勞因子與學習因子。
        """
        area = box.width * box.height
        # 基礎按壓時長：按鈕越小，基礎越長
        if area > 5000:
            base = random.uniform(0.04, 0.08)
        elif area > 2000:
            base = random.uniform(0.06, 0.11)
        else:
            base = random.uniform(0.08, 0.15)

        # 疲勞加成：疲勞時按壓會拖長
        fatigue_bonus = self.fatigue * random.uniform(0.02, 0.06)

        # 學習加成：熟悉之後按更快
        result = (base + fatigue_bonus) * self._learning_factor()

        return self._correlated_delay(result)

    # ── 點擊後延遲 ─────────────────────────────────────

    def post_click_delay(self):
        """
        模擬人類「按完之後的反應時間」。
        使用 Log-Normal 分佈（天然右偏，更真實）。
        偶爾會有較長的停頓（分心、看手機等）。
        """
        self._action_count += 1
        self._last_click_time = time.monotonic()

        # Log-Normal 反應時間 (中位數 ~0.15s，玩家在刷圖時通常會連點)
        base = random.lognormvariate(math.log(0.15), 0.25)
        base = max(0.05, min(base, 0.40))

        # 疲勞加成
        fatigue_add = self.fatigue * random.uniform(0.05, 0.15)

        # 學習因子
        learn = self._learning_factor()

        # 分心 — 使用 session 個性中的分心傾向
        distraction = 0
        roll = random.random()
        distraction_threshold = self._personality['distraction_prone']

        if roll < distraction_threshold * 0.4:
            # 大分心：1.5~4 秒（像是看一下手機）
            distraction = random.lognormvariate(math.log(2.5), 0.3)
            distraction = min(distraction, 6.0)
        elif roll < distraction_threshold:
            # 小分心：0.5~1.2 秒（像是猶豫了一下）
            distraction = random.uniform(0.5, 1.2)

        # 連續快速操作後偶爾強制休息
        if self._consecutive_fast > 8:
            distraction += random.uniform(0.8, 2.0)
            self._consecutive_fast = 0

        total = (base * learn + fatigue_add + distraction) * self._personality['speed_factor']

        if total < 0.35:
            self._consecutive_fast += 1
        else:
            self._consecutive_fast = max(0, self._consecutive_fast - 1)

        final_delay = self._correlated_delay(total)
        self._debug_log(f"反應時間 {final_delay:.2f}s | 學習={learn:.2f}, 疲勞={self.fatigue:.2f}, 連擊={self._consecutive_fast}, 節奏突變=({self._tempo_state:.2f})")
        return final_delay

    # ── 迴圈間延遲 ─────────────────────────────────────

    def loop_delay(self):
        """
        每輪迴圈之間的等待時間，模擬「人類觀察畫面」的節奏。
        使用 Log-Normal 分佈。
        """
        # Log-Normal（中位數 ~1.2s）
        base = random.lognormvariate(math.log(1.2), 0.25)
        base = max(0.6, min(base, 3.0))

        # 疲勞時更慢
        fatigue_add = self.fatigue * random.uniform(0.2, 0.8)

        # 約 3% 機率出現「微休息」(3~8 秒)
        if random.random() < 0.03:
            base += random.lognormvariate(math.log(5.0), 0.3)
            base = min(base, 12.0)

        total = (base + fatigue_add) * self._personality['patience']
        final_delay = self._correlated_delay(total)
        self._debug_log(f"畫面等待 {final_delay:.2f}s | 基礎={base:.2f}, 隱藏疲勞干擾={fatigue_add:.2f}")
        return final_delay

    # ── 等待中的隨機點擊 ──────────────────────────────

    def idle_clicks(self, center_x=0.72, center_y=0.20):
        """
        生成等待時的隨機點擊序列。
        每次 session 可能有不同的 idle 習慣區域。
        回傳 list of (x, y, delay_after, down_time)。
        """
        # 有時不點（人類有時只是在等）
        if random.random() < 0.25:
            return []

        clicks = []
        n = random.choices([1, 2, 3], weights=[50, 40, 10])[0]

        # 偶爾偏移到不同的區域（模擬無聊亂點）
        zone_roll = random.random()
        if zone_roll < 0.70:
            # 大多數時候在指定區域附近
            zone_cx, zone_cy = center_x, center_y
        elif zone_roll < 0.85:
            # 偶爾偏移到畫面中央偏上
            zone_cx = center_x + random.uniform(-0.10, 0.10)
            zone_cy = center_y + random.uniform(-0.05, 0.08)
        else:
            # 少數情況點擊安全的空白區域
            zone_cx = random.uniform(0.3, 0.7)
            zone_cy = random.uniform(0.15, 0.35)

        for i in range(n):
            # 每次點擊的位置有小幅飄移
            drift_x = random.gauss(0, 0.015)
            drift_y = random.gauss(0, 0.012)
            x = zone_cx + drift_x
            y = zone_cy + drift_y

            # 點擊間隔遞增（人類連點會越來越慢）— Log-Normal
            base_delay = 0.3 + i * 0.15
            delay = random.lognormvariate(math.log(base_delay), 0.2)
            delay = max(0.2, min(delay, 1.5))

            # idle click 也有按壓時長
            down_time = random.uniform(0.03, 0.08)

            clicks.append((x, y, delay, down_time))

        return clicks

    # ── 步驟間的小停頓 ─────────────────────────────────

    def step_transition_delay(self):
        """
        從一個步驟切換到下一個步驟的自然停頓。
        模擬「看到畫面變了 → 腦袋反應 → 開始動作」。
        使用 Log-Normal 分佈。
        """
        # 人類視覺反應時間 (預期接下來的畫面變化，中位數只需 ~120ms)
        reaction = random.lognormvariate(math.log(0.12), 0.25)
        reaction = max(0.05, min(reaction, 0.35))

        # 動作選擇時間（熟悉的農圖流程，幾乎不用思考）
        decision = random.uniform(0.02, 0.08)

        # 學習因子：熟悉流程後反應更快
        learn = self._learning_factor()

        total = (reaction + decision) * learn
        total += self.fatigue * random.uniform(0.03, 0.10)
        total *= self._personality['speed_factor']

        return self._correlated_delay(total)

    # ── 長時間運行的微休息 (泊松過程) ──────────────────

    def should_micro_break(self, round_number):
        """
        使用泊松過程判斷是否應該微休息。
        平均每 15 輪觸發一次，無週期性。
        """
        if round_number < 5:
            return False, 0

        # 泊松過程：λ = 1/15，每輪獨立判斷
        trigger_rate = 1.0 / 15.0
        if random.random() < trigger_rate:
            # Log-Normal 休息時長，中位數 ~8 秒
            duration = random.lognormvariate(math.log(8.0), 0.35)
            duration = max(3.0, min(duration, 25.0))
            duration *= (1 + self.fatigue * 0.5) * self._personality['patience']
            self._debug_log(f"觸發泊松微休息！機率命中，暫停 {duration:.1f}s 放空中...")
            return True, duration

        return False, 0

    # ── 重置（新任務開始時） ──────────────────────────

    def reset(self):
        """重置所有狀態，但保留 session 個性。"""
        self._start_time = time.monotonic()
        self._action_count = 0
        self._consecutive_fast = 0
        self._last_click_time = 0.0
        self._fatigue_level = 0.0
        self._tempo_state = 0.0
