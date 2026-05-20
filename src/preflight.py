"""
預啟動檢查：在 ok-script 框架初始化前執行，確保 result.json 與實際圖片檔案同步。

用途：
    使用者可以隨時刪除/重命名 assets/images/ 裡的圖片，
    下次啟動時本模組會自動從 result.json 移除已不存在的條目，
    避免框架載入時因找不到圖片而報錯。
"""

import os
import json


def sanitize_result_json(json_path="assets/result.json", images_dir="assets"):
    """
    掃描 result.json，移除所有引用了不存在圖片的條目。

    - 如果 result.json 不存在，跳過（首次啟動）。
    - 如果有條目被移除，會自動寫回修正後的 JSON。
    - 回傳被移除的條目數量。
    """
    if not os.path.exists(json_path):
        return 0

    with open(json_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            # JSON 損壞，清空讓 JsonFixerTask 重建
            data = {'images': [], 'categories': [], 'annotations': []}
            with open(json_path, 'w', encoding='utf-8') as out:
                json.dump(data, out, indent=2, ensure_ascii=False)
            print("[preflight] ⚠️ result.json 格式損壞，已清空。請執行 JsonFixerTask 重建。")
            return -1

    images = data.get('images', [])
    if not images:
        return 0

    # 找出仍然存在的圖片 ID
    valid_ids = set()
    valid_images = []
    removed = []

    for img in images:
        file_path = os.path.join(images_dir, img.get('file_name', ''))
        if os.path.exists(file_path):
            valid_ids.add(img['id'])
            valid_images.append(img)
        else:
            removed.append(img.get('file_name', '?'))

    if not removed:
        return 0

    # 過濾 categories 和 annotations
    data['images'] = valid_images
    data['categories'] = [c for c in data.get('categories', []) if c['id'] in valid_ids]
    data['annotations'] = [a for a in data.get('annotations', []) if a['image_id'] in valid_ids]

    with open(json_path, 'w', encoding='utf-8') as out:
        json.dump(data, out, indent=2, ensure_ascii=False)

    for name in removed:
        print(f"[preflight] 🗑️ 已從 result.json 移除不存在的圖片: {name}")

    print(f"[preflight] ✅ 已清理 {len(removed)} 筆失效條目，剩餘 {len(valid_images)} 筆。")
    return len(removed)
