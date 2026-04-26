import os
import cv2
import json
import glob
from src.tasks.MyBaseTask import MyBaseTask

class JsonFixerTask(MyBaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "魔法修復 JSON 工具"
        self.description = "當您手動更名、新增或刪除圖片後，執行此工具即可自動完美重建 result.json"

    def run(self):
        self.log_info("🪄 魔法修復啟動：掃描資料夾內的截圖並重建 JSON 配置...", notify=True)
        images_dir = os.path.join("assets", "images")
        json_path = os.path.join("assets", "result.json")

        if not os.path.exists(images_dir):
            self.log_error("❌ 找不到 images 資料夾！")
            return

        res = {'images': [], 'categories': [], 'annotations': []}
        
        # 取得所有 png，並排序確保順序一致
        png_files = sorted(glob.glob(os.path.join(images_dir, "*.png")))
        if not png_files:
            self.log_info("ℹ 圖片資料夾為空，已清空 JSON。")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(res, f, indent=4)
            return

        for i, filepath in enumerate(png_files):
            img = cv2.imread(filepath)
            if img is None:
                self.log_error(f"❌ 讀取檔案失敗: {filepath}")
                continue

            # 使用 OpenCV 找出圖中非全白的區域 (也就是保留下來的按鈕位置)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 254, 255, cv2.THRESH_BINARY_INV)
            pts = cv2.findNonZero(thresh)

            if pts is not None:
                x, y, w, h = cv2.boundingRect(pts)
            else:
                x, y, w, h = 0, 0, 10, 10  # 預設防呆數值
            
            # 使用檔名 (不含副檔名) 當作分類名稱
            bname = os.path.basename(filepath).replace('.png', '')
            
            # 自動防呆：如果單純是 1, 2, 3，自動補零變成 01, 02, 03 以對齊腳本
            if bname.isdigit() and len(bname) == 1:
                bname = bname.zfill(2)
                
            cid = i + 1
            
            # 加入 images 陣列
            res['images'].append({
                'id': cid, 
                'file_name': f'images/{os.path.basename(filepath)}', 
                'width': 1280, 
                'height': 720
            })
            
            # 加入 categories 陣列
            res['categories'].append({
                'id': cid, 
                'name': bname
            })
            
            # 加入 annotations 陣列 (包含反推出來的 bbox)
            res['annotations'].append({
                'id': cid, 
                'image_id': cid, 
                'category_id': cid, 
                'bbox': [x, y, w, h], 
                'area': w * h
            })

            self.log_info(f"✔ 已處理 {os.path.basename(filepath)} -> 分類 [{bname}], 座標 bbox=[{x},{y},{w},{h}]")

        # 寫回 JSON 檔案
        with open(json_path, 'w', encoding='utf-8') as out:
            json.dump(res, out, indent=2, ensure_ascii=False)

        self.log_info("✅ 魔法修復完成！現在 result.json 已完全對齊您的資料夾！", notify=True)
