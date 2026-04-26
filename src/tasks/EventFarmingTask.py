from qfluentwidgets import FluentIcon
from src.tasks.MyBaseTask import MyBaseTask
from src.tasks.HumanBehavior import HumanBehavior
import random

class EventFarmingTask(MyBaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "自動刷活動"
        self.description = "全流程：選單 -> 標籤 -> 關卡 -> 挑戰 -> 跳過 -> 結算"
        self.icon = FluentIcon.SYNC
        
        self.default_config.update({
            '關卡模式': '最高難度',
            '體力耗盡時': '停止腳本',
            '挑戰次數': 99,
            '辨識門檻': 0.75
        })
        
        self.config_type = {
            '關卡模式': {'type': 'drop_down', 'options': ['最高難度', '較弱關卡']},
            '體力耗盡時': {'type': 'drop_down', 'options': ['停止腳本', '喝100體力水', '喝滿體力水']}
        }
        
        # 擬人化行為引擎
        self._human = HumanBehavior(task=self)

    def _find_and_click(self, feature_name, label, threshold):
        """圖片比對優先，找到就用擬人化方式點擊。回傳是否成功。"""
        box = self.find_one(feature_name, threshold=threshold)
        if box:
            self.log_info(f"✔ [{label}] 圖片比對成功 (相似度: {box.confidence:.2f})，點擊中...")
            
            # 【擬人化座標】：高斯分佈 + 慣用手偏移
            click_x, click_y = HumanBehavior.humanize_click_position(box)
            
            # 【擬人化按壓時長】：根據按鈕大小 + 疲勞度
            dt = self._human.calc_press_duration(box)
            
            self.click(x=click_x, y=click_y, down_time=dt)
            
            # 【擬人化後延遲】：含分心、疲勞、連續操作節奏
            post_delay = self._human.post_click_delay()
            self.sleep(post_delay)
            
            return True
        return False

    def run(self):
        # 重置擬人化狀態
        self._human.reset()
        
        count = 0
        max_count = self.config.get('挑戰次數', 99)
        threshold = self.config.get('辨識門檻', 0.75)
        mode = self.config.get('關卡模式', '最高難度')
        
        self.log_info(f"🚀 開始自動刷活動，目標:{max_count}次，模式:{mode}", notify=True)

        while self.running and count < max_count:

            # ── 微休息檢查 ──────────────────────────────
            should_break, break_duration = self._human.should_micro_break(count)
            if should_break:
                self.log_info(f"☕ 微休息 {break_duration:.1f} 秒...")
                self.sleep(break_duration)

            # 執行順序從「最深層/最優先」到「最淺層」，避免卡在常駐標籤
            
            # --- 處理體力耗盡 (09) ---
            if self.find_one('09', threshold=threshold):
                stamina_action = self.config.get('體力耗盡時', '停止腳本')
                self.log_info(f"⚠️ 體力耗盡！執行設定動作：{stamina_action}")
                
                if stamina_action == '停止腳本':
                    self.log_error("❌ 體力耗盡，已自動停止腳本。", notify=True)
                    break
                    
                elif stamina_action == '喝100體力水':
                    self.sleep(self._human.step_transition_delay())
                    if self._find_and_click('10', '喝100體力水', threshold):
                        self.sleep(random.uniform(0.4, 0.7))
                    if self._find_and_click('12', '確認回復', threshold):
                        self.log_info("✔ 已回復體力！")
                        self.sleep(random.uniform(1.5, 2.5))
                    continue
                    
                elif stamina_action == '喝滿體力水':
                    self.sleep(self._human.step_transition_delay())
                    if self._find_and_click('11', '喝滿體力水', threshold):
                        self.sleep(random.uniform(0.4, 0.7))
                    if self._find_and_click('12', '確認回復', threshold):
                        self.log_info("✔ 已回復滿體！")
                        self.sleep(random.uniform(1.5, 2.5))
                    continue

            # --- 7. 獎勵畫面 ---
            if self._find_and_click('08', '獎勵畫面', threshold):
                self.sleep(self._human.step_transition_delay())
                continue

            # --- 6. RESULT 結算畫面 ---
            if self._find_and_click('07', 'RESULT畫面', threshold):
                self.sleep(self._human.step_transition_delay())
                continue

            # --- 5. 確定/結算 ---
            if self._find_and_click('06', '確定結算', threshold):
                self.sleep(self._human.step_transition_delay())
                continue

            # --- 4. ALL SKIP ---
            if self._find_and_click('05', 'ALL SKIP', threshold):
                self.sleep(self._human.step_transition_delay())
                continue

            # --- 3. 進行挑戰 ---
            if self._find_and_click('04', '進行挑戰', threshold):
                count += 1
                self.log_info(f"📈 目前進度: {count}/{max_count}")
                self.sleep(self._human.step_transition_delay())
                continue

            # --- 2. 挑戰關卡 (含難度切換) ---
            if mode == '較弱關卡':
                if self._find_and_click('03-weak', '較弱關卡', threshold):
                    self.sleep(self._human.step_transition_delay())
                    continue
            else:
                if self._find_and_click('03', '最高難度關卡', threshold):
                    self.sleep(self._human.step_transition_delay())
                    continue

            # --- 1. 推薦選單 ---
            if self._find_and_click('02', '推薦選單', threshold):
                self.sleep(self._human.step_transition_delay())
                continue

            # --- 0. 競賽選單 ---
            if self._find_and_click('01', '競賽選單', threshold):
                self.sleep(self._human.step_transition_delay())
                continue

            # ── 等待中 (無匹配) ────────────────────────
            self.log_info("⏳ 等待畫面載入中..")
            
            idle_clicks = self._human.idle_clicks(center_x=0.72, center_y=0.20)
            for (rx, ry, delay, dt) in idle_clicks:
                self.click(rx, ry, key='left', down_time=dt)
                self.sleep(delay)
            
            # 迴圈間的自然停頓
            self.sleep(self._human.loop_delay())

        self.log_info(f"✅ 任務完成！共 {count} 回合。", notify=True)
