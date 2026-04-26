import os
import json
import random
from qfluentwidgets import FluentIcon
from src.tasks.MyBaseTask import MyBaseTask
from src.tasks.HumanBehavior import HumanBehavior


class FlowRunnerTask(MyBaseTask):
    """通用流程執行器：讀取 flow.json 並自動執行，不需寫 Python 程式碼。"""

    flow_file = None  # 子類別設定此值

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.flow = self._load_flow()
        self.name = self.flow.get('task_name', 'Flow Task')
        self.description = self.flow.get('description', '')
        self._should_stop = False

        # 擬人化行為引擎
        self._human = HumanBehavior(task=self)

        # 設定圖示
        icon_name = self.flow.get('icon')
        if icon_name:
            self.icon = getattr(FluentIcon, icon_name, None)

        # 從 flow.json 動態建構 GUI 設定欄位
        flow_config = self.flow.get('config', {})
        for key, cfg in flow_config.items():
            self.default_config[key] = cfg.get('default', '')
            if cfg.get('type') == 'drop_down':
                self.config_type[key] = {
                    'type': 'drop_down',
                    'options': cfg.get('options', [])
                }

    # ── 載入 ──────────────────────────────────────────────

    def _load_flow(self):
        if not self.flow_file:
            raise ValueError("flow_file not set")
        with open(self.flow_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    # ── 擬人化點擊 ──────────────────────────────────────────

    def _find_and_click(self, feature_name, label, threshold):
        """圖片比對，找到就用擬人化方式點擊。回傳是否成功。"""
        box = self.find_one(feature_name, threshold=threshold)
        if not box:
            return False

        self.log_info(
            f"\u2714 [{label}] 找到 (相似度: {box.confidence:.2f})，點擊中..."
        )

        # 【擬人化座標】：高斯分佈 + 慣用手偏移
        click_x, click_y = HumanBehavior.humanize_click_position(box)

        # 【擬人化按壓時長】：根據按鈕大小 + 疲勞度
        dt = self._human.calc_press_duration(box)

        self.click(x=click_x, y=click_y, down_time=dt)

        # 【擬人化後延遲】：含分心、疲勞、連續操作節奏
        post_delay = self._human.post_click_delay()
        self.sleep(post_delay)
        return True

    # ── 步驟執行 ──────────────────────────────────────────

    def _resolve_feature(self, step):
        """根據 config 中的 variants 決定使用哪個 feature / label。"""
        feature = step.get('feature')
        label = step.get('label', feature)

        for config_key, value_map in step.get('variants', {}).items():
            current = self.config.get(config_key)
            if current in value_map:
                override = value_map[current]
                feature = override.get('feature', feature)
                label = override.get('label', label)

        return feature, label

    def _execute_step(self, step, threshold):
        """執行單步。回傳 True 表示已匹配（不論成功或停止）。"""
        action = step.get('action', 'click')
        feature, label = self._resolve_feature(step)

        if action == 'click':
            matched = self._find_and_click(feature, label, threshold)
            if matched:
                # 步驟切換的自然停頓（模擬大腦反應）
                self.sleep(self._human.step_transition_delay())
            return matched

        if action == 'conditional':
            matched = self._execute_conditional(step, feature, label, threshold)
            if matched:
                self.sleep(self._human.step_transition_delay())
            return matched

        return False

    def _execute_conditional(self, step, feature, label, threshold):
        """處理條件分支步驟（例如體力耗盡）。"""
        if not self.find_one(feature, threshold=threshold):
            return False

        self.log_info(f"\u26a0\ufe0f [{label}] 偵測到！")

        config_key = step.get('config_key', '')
        config_value = self.config.get(config_key, '')
        branch = step.get('branches', {}).get(config_value, {})
        branch_action = branch.get('action', 'stop')

        if branch_action == 'stop':
            msg = branch.get('message', '\u274c 已停止')
            self.log_error(msg, notify=True)
            self._should_stop = True
            return True

        if branch_action == 'sequence':
            for sub in branch.get('steps', []):
                sub_feature = sub.get('feature')
                sub_label = sub.get('label', sub_feature)
                self._find_and_click(sub_feature, sub_label, threshold)
                if sub.get('message'):
                    self.log_info(sub['message'])
                # 步驟間使用完整擬人化延遲
                self.sleep(self._human.post_click_delay())
            return True

        return True

    # ── 主迴圈 ──────────────────────────────────────────

    def run(self):
        # 重置擬人化狀態
        self._human.reset()

        loop_cfg = self.flow.get('loop', {})
        count_key = loop_cfg.get('count_key', '挑戰次數')
        threshold_key = loop_cfg.get('threshold_key', '辨識門檻')

        count = 0
        max_count = self.config.get(count_key, 99)
        threshold = self.config.get(threshold_key, 0.75)

        steps = sorted(
            self.flow.get('steps', []),
            key=lambda s: -s.get('priority', 0)
        )

        self.log_info(
            f"\U0001f680 開始執行: {self.name}，目標:{max_count}次",
            notify=True
        )

        while self.running and count < max_count and not self._should_stop:
            # ── 微休息檢查 ──────────────────────────────
            should_break, break_duration = self._human.should_micro_break(count)
            if should_break:
                self.log_info(f"☕ 微休息 {break_duration:.1f} 秒...")
                self.sleep(break_duration)

            matched = False

            # ── 掃描順序微變異 (偶爾眼殘/跳躍掃視) ────────────
            current_steps = steps.copy()
            if random.random() < 0.15 and len(current_steps) >= 2:
                # 隨機交換兩個步驟的檢查順序
                i1, i2 = random.sample(range(len(current_steps)), 2)
                current_steps[i1], current_steps[i2] = current_steps[i2], current_steps[i1]

            for step in current_steps:
                if not self.running:
                    break
                if self._execute_step(step, threshold):
                    if step.get('on_success') == 'increment_count':
                        count += 1
                        self.log_info(f"\U0001f4c8 目前進度: {count}/{max_count}")
                    matched = True
                    break

            if not matched and not self._should_stop:
                idle = self.flow.get('idle', {})
                self.log_info(idle.get('message', '\u23f3 等待中..'))

                # 擬人化等待點擊
                click_cfg = idle.get('click', {})
                if click_cfg:
                    idle_clicks = self._human.idle_clicks(
                        center_x=click_cfg.get('x', 0.5),
                        center_y=click_cfg.get('y', 0.5)
                    )
                    for (rx, ry, delay, dt) in idle_clicks:
                        self.click(rx, ry, key='left', down_time=dt)
                        self.sleep(delay)

                # 迴圈間的自然停頓
                self.sleep(self._human.loop_delay())

        self.log_info(f"\u2705 任務完成！共 {count} 回合。", notify=True)
