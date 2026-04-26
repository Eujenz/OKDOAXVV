import cv2
import os
import re
import json
from src.tasks.MyBaseTask import MyBaseTask


class TemplateMakerTask(MyBaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "模板製作工具"
        self.description = "截圖 + 命名 + 自動更新 JSON，一步到位"

        self.default_config.update({
            '模板名稱': '',  # 空 = 自動遞增編號 (01, 02...)
        })

    def run(self):
        images_dir = os.path.join("assets", "images")
        json_path = os.path.join("assets", "result.json")
        os.makedirs(images_dir, exist_ok=True)

        # ── 列出現有模板 ──
        existing = sorted(
            f.replace('.png', '')
            for f in os.listdir(images_dir)
            if f.endswith('.png')
        )
        if existing:
            self.log_info(f"📋 現有模板: {', '.join(existing)}")
        else:
            # 空資料夾 → 初始化 JSON
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({"images": [], "categories": [], "annotations": []}, f, indent=2)
            self.log_info("ℹ 圖片資料夾為空，已初始化 result.json。")

        # ── 決定模板名稱 ──
        raw_name = self.config.get('模板名稱', '').strip()
        if raw_name:
            # 清理名稱：保留英數中文底線連字號
            template_name = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', raw_name)
            is_overwrite = template_name in existing
            if is_overwrite:
                self.log_info(f"⚠️ 模板 [{template_name}] 已存在，將覆蓋更新。")
        else:
            # 自動遞增
            i = 1
            while f"{i:02d}" in existing:
                i += 1
            template_name = f"{i:02d}"
            is_overwrite = False

        self.log_info(f"📸 準備截取模板 [{template_name}]，框選區域後按 ENTER 確認，ESC 取消。", notify=True)

        # ── 擷取畫面 ──
        frame = self.executor.device_manager.capture_method.get_frame()
        if frame is None:
            self.log_error("❌ 無法擷取畫面！請確認遊戲視窗已開啟。")
            return

        display = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR) if frame.shape[2] == 4 else frame.copy()
        screen_h, screen_w = display.shape[:2]

        roi = cv2.selectROI("Template Maker", display, False, False)
        cv2.destroyAllWindows()

        if roi[2] <= 0 or roi[3] <= 0:
            self.log_info("已取消。")
            return

        x, y, w, h = int(roi[0]), int(roi[1]), int(roi[2]), int(roi[3])

        # ── 儲存全螢幕白底 + ROI 區域 ──
        img_basename = f"{template_name}.png"
        save_path = os.path.join(images_dir, img_basename)

        canvas = cv2.cvtColor(
            cv2.cvtColor(display, cv2.COLOR_BGR2GRAY),
            cv2.COLOR_GRAY2BGR
        )
        canvas[:] = 255
        canvas[y:y+h, x:x+w] = display[y:y+h, x:x+w]
        cv2.imwrite(save_path, canvas)

        # ── 更新 result.json ──
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                coco = json.load(f)
        except Exception:
            coco = {}
        coco.setdefault("images", [])
        coco.setdefault("categories", [])
        coco.setdefault("annotations", [])

        img_filename = f"images/{img_basename}"
        entry = next((c for c in coco["categories"] if c["name"] == template_name), None)

        if entry:
            cid = entry["id"]
            for img in coco["images"]:
                if img["id"] == cid:
                    img.update({"file_name": img_filename, "width": screen_w, "height": screen_h})
            for ann in coco["annotations"]:
                if ann["category_id"] == cid:
                    ann.update({"bbox": [x, y, w, h], "area": w * h})
            self.log_info(f"   (覆蓋更新模板 ID={cid})")
        else:
            cid = max((c["id"] for c in coco["categories"] if "id" in c), default=0) + 1
            coco["images"].append({
                "id": cid, "file_name": img_filename,
                "width": screen_w, "height": screen_h
            })
            coco["categories"].append({"id": cid, "name": template_name})
            coco["annotations"].append({
                "id": cid, "image_id": cid, "category_id": cid,
                "bbox": [x, y, w, h], "area": w * h
            })

        # ── 自動清理殘留的 JSON 項目 (防呆：使用者刪除或移動實體檔案) ──
        valid_images = []
        valid_cids = set()
        for img in coco["images"]:
            img_path = os.path.join("assets", img["file_name"])
            if os.path.exists(img_path):
                valid_images.append(img)
                valid_cids.add(img["id"])
            else:
                self.log_info(f"🗑️ 自動清理不存在的實體圖片對應 JSON: {img['file_name']}")

        coco["images"] = valid_images
        coco["categories"] = [c for c in coco["categories"] if c["id"] in valid_cids]
        coco["annotations"] = [a for a in coco["annotations"] if a["category_id"] in valid_cids]

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(coco, f, indent=2, ensure_ascii=False)

        # ── 完成 ──
        self.log_info(f"✅ 已儲存: {save_path}", notify=True)
        self.log_info(f"   名稱: {template_name}  大小: {w}x{h}  座標: ({x},{y})")
        self.log_info(f"   全螢幕: {screen_w}x{screen_h}")
        self.log_info(f"")
        self.log_info(f"   💡 在 flow.json 中使用:")
        self.log_info(f'   {{ "feature": "{template_name}", "label": "描述", "action": "click", "priority": 50 }}')
        self.log_info(f"")
        self.log_info(f"   💡 在 Python 中使用:")
        self.log_info(f"   self.find_one('{template_name}')")
