"""
OKDOAXVV Flow Editor — Backend Server
用法：python editor/server.py
"""
import os, sys, json, glob, shutil, io, base64, re, traceback
import cv2
import numpy as np
from flask import Flask, jsonify, request, send_from_directory, send_file

# ── Paths ────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
FLOWS_DIR  = os.path.join(BASE_DIR, 'flows')
IMAGES_DIR = os.path.join(ASSETS_DIR, 'images')
JSON_PATH  = os.path.join(ASSETS_DIR, 'result.json')

app = Flask(__name__, static_folder='static')

# ═══════════════════════ Static ═══════════════════════

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# ═══════════════════════ Flow API ═══════════════════════

@app.route('/api/flows')
def list_flows():
    os.makedirs(FLOWS_DIR, exist_ok=True)
    names = sorted(f[:-5] for f in os.listdir(FLOWS_DIR) if f.endswith('.json'))
    return jsonify(names)

@app.route('/api/flow/<name>')
def get_flow(name):
    path = os.path.join(FLOWS_DIR, f'{name}.json')
    if not os.path.exists(path):
        return jsonify({'error': 'Flow not found'}), 404
    with open(path, 'r', encoding='utf-8') as f:
        return jsonify(json.load(f))

@app.route('/api/flow/<name>', methods=['POST'])
def save_flow(name):
    data = request.json
    errors = _validate_flow(data)
    if errors:
        return jsonify({'errors': errors}), 400
    path = os.path.join(FLOWS_DIR, f'{name}.json')
    if os.path.exists(path):
        shutil.copy2(path, path + '.bak')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return jsonify({'success': True})

def _validate_flow(data):
    errs = []
    if not data.get('task_name'):
        errs.append('task_name 為必填')
    steps = data.get('steps', [])
    if not isinstance(steps, list):
        errs.append('steps 必須是陣列')
        return errs
    tpl_names = _get_template_names()
    for i, s in enumerate(steps):
        feat = s.get('feature', '')
        if not feat:
            errs.append(f'步驟 {i+1}: feature 為必填')
        elif tpl_names and feat not in tpl_names:
            errs.append(f'步驟 {i+1}: 模板 "{feat}" 不存在')
        if not isinstance(s.get('priority', 0), (int, float)):
            errs.append(f'步驟 {i+1}: priority 必須是數字')
    return errs

def _get_template_names():
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            coco = json.load(f)
        return {c['name'] for c in coco.get('categories', [])}
    except Exception:
        return set()

# ═══════════════════════ Template API ═══════════════════════

@app.route('/api/templates')
def list_templates():
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            coco = json.load(f)
    except Exception:
        return jsonify([])
    result = []
    for cat in coco.get('categories', []):
        ann = next((a for a in coco['annotations'] if a['category_id'] == cat['id']), None)
        result.append({
            'name': cat['name'],
            'id': cat['id'],
            'bbox': ann['bbox'] if ann else [0,0,0,0],
        })
    return jsonify(result)

@app.route('/api/images/<path:filename>')
def get_image(filename):
    safe = os.path.basename(filename)
    return send_from_directory(IMAGES_DIR, safe)

@app.route('/api/thumbnail/<name>')
def get_thumbnail(name):
    img_path = os.path.join(IMAGES_DIR, f'{name}.png')
    if not os.path.exists(img_path):
        return '', 404
    img = cv2.imread(img_path)
    if img is None:
        return '', 404
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 254, 255, cv2.THRESH_BINARY_INV)
    pts = cv2.findNonZero(thresh)
    if pts is not None:
        x, y, w, h = cv2.boundingRect(pts)
        pad = 8
        x, y = max(0, x-pad), max(0, y-pad)
        w = min(img.shape[1]-x, w+2*pad)
        h = min(img.shape[0]-y, h+2*pad)
        crop = img[y:y+h, x:x+w]
    else:
        crop = img
    _, buf = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return send_file(io.BytesIO(buf.tobytes()), mimetype='image/jpeg')

@app.route('/api/template', methods=['POST'])
def save_template():
    data = request.json
    name = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', (data.get('name') or '').strip())
    bbox = data.get('bbox')
    image_b64 = data.get('image')
    if not name or not bbox or not image_b64:
        return jsonify({'error': '缺少必要欄位'}), 400
    img_bytes = base64.b64decode(image_b64)
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return jsonify({'error': '圖片解碼失敗'}), 400
    x, y, w, h = [int(v) for v in bbox]
    sh, sw = img.shape[:2]
    canvas = np.full_like(img, 255)
    canvas[y:y+h, x:x+w] = img[y:y+h, x:x+w]
    cv2.imwrite(os.path.join(IMAGES_DIR, f'{name}.png'), canvas)
    _update_result_json(name, x, y, w, h, sw, sh)
    return jsonify({'success': True, 'name': name})

@app.route('/api/template/<name>', methods=['DELETE'])
def delete_template(name):
    img_path = os.path.join(IMAGES_DIR, f'{name}.png')
    if os.path.exists(img_path):
        os.remove(img_path)
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            coco = json.load(f)
        cat = next((c for c in coco['categories'] if c['name'] == name), None)
        if cat:
            cid = cat['id']
            coco['categories'] = [c for c in coco['categories'] if c['id'] != cid]
            coco['images']     = [i for i in coco['images']     if i['id'] != cid]
            coco['annotations']= [a for a in coco['annotations'] if a['category_id'] != cid]
            with open(JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(coco, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return jsonify({'success': True})

def _update_result_json(name, x, y, w, h, sw, sh):
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            coco = json.load(f)
    except Exception:
        coco = {}
    for k in ('images','categories','annotations'):
        coco.setdefault(k, [])
    entry = next((c for c in coco['categories'] if c['name'] == name), None)
    if entry:
        cid = entry['id']
        for im in coco['images']:
            if im['id'] == cid:
                im.update(file_name=f'images/{name}.png', width=sw, height=sh)
        for an in coco['annotations']:
            if an['category_id'] == cid:
                an.update(bbox=[x,y,w,h], area=w*h)
    else:
        cid = max((c['id'] for c in coco['categories']), default=0) + 1
        coco['images'].append(dict(id=cid, file_name=f'images/{name}.png', width=sw, height=sh))
        coco['categories'].append(dict(id=cid, name=name))
        coco['annotations'].append(dict(id=cid, image_id=cid, category_id=cid, bbox=[x,y,w,h], area=w*h))
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(coco, f, indent=2, ensure_ascii=False)

# ═══════════════════════ Capture API ═══════════════════════

@app.route('/api/capture')
def capture():
    try:
        img = _capture_game_window()
        if img is None:
            return jsonify({'error': '無法擷取遊戲視窗，請確認遊戲已開啟。'}), 400
        _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        h, w = img.shape[:2]
        return jsonify({'image': base64.b64encode(buf.tobytes()).decode(), 'width': w, 'height': h})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _capture_game_window():
    try:
        import win32gui, win32ui, win32con
        from ctypes import windll
        import time
    except ImportError:
        return None

    hwnd = None
    def _find(h, _):
        nonlocal hwnd
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if 'DOAX' in t or 'Venus' in t:
                hwnd = h
    win32gui.EnumWindows(_find, None)
    if not hwnd:
        return None

    # Bring game to foreground so screen capture works
    try:
        windll.user32.SetForegroundWindow(hwnd)
        time.sleep(0.35)
    except Exception:
        pass

    # Get client area dimensions
    cr = win32gui.GetClientRect(hwnd)
    w, h = cr[2], cr[3]
    if w <= 0 or h <= 0:
        return None

    # Map client (0,0) to screen coordinates
    left, top = win32gui.ClientToScreen(hwnd, (0, 0))

    # Capture from the SCREEN DC (most reliable for DirectX)
    scrDC = win32gui.GetDC(0)
    srcDC = win32ui.CreateDCFromHandle(scrDC)
    memDC = srcDC.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(srcDC, w, h)
    memDC.SelectObject(bmp)
    memDC.BitBlt((0, 0), (w, h), srcDC, (left, top), win32con.SRCCOPY)

    raw = bmp.GetBitmapBits(True)
    img = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 4)

    win32gui.DeleteObject(bmp.GetHandle())
    memDC.DeleteDC(); srcDC.DeleteDC()
    win32gui.ReleaseDC(0, scrDC)

    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

# ═══════════════════════ Main ═══════════════════════

if __name__ == '__main__':
    os.makedirs(FLOWS_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    print('='*50)
    print('  OKDOAXVV Flow Editor')
    print('  http://localhost:5000')
    print('='*50)
    app.run(debug=True, port=5000)
