/* ═══════════════════════════════════════════════════
   OKDOAXVV Flow Editor — Application Logic
   ═══════════════════════════════════════════════════ */

// ── State ──────────────────────────────────────────
const S = {
    flows: [],
    currentFlowName: '',
    flow: null,            // current flow JSON
    templates: [],         // from result.json
    selectedStep: -1,      // index in flow.steps
    captureData: null,     // { image (b64), width, height }
    roi: null,             // { x, y, w, h } in actual coords
};

// ── DOM refs ───────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

const els = {
    flowSelect: $('#flow-select'),
    stepList: $('#step-list'),
    templateList: $('#template-list'),
    templateCount: $('#template-count'),
    stepDetail: $('#step-detail'),
    tplPreview: $('#template-preview'),
    flowTaskName: $('#flow-task-name'),
    captureModal: $('#capture-modal'),
    captureCanvas: $('#capture-canvas'),
    captureCoords: $('#capture-coords'),
    captureName: $('#capture-name'),
    roiInfo: $('#roi-info'),
    toasts: $('#toast-container'),
};

// ── API helpers ────────────────────────────────────
async function api(url, opts = {}) {
    try {
        const res = await fetch(url, {
            headers: { 'Content-Type': 'application/json' },
            ...opts,
            body: opts.body ? JSON.stringify(opts.body) : undefined,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || data.errors?.join(', ') || 'Unknown error');
        return data;
    } catch (e) {
        toast(e.message, 'error');
        throw e;
    }
}

// ── Toast ──────────────────────────────────────────
function toast(msg, type = 'info') {
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = `${icons[type] || ''} ${msg}`;
    els.toasts.appendChild(el);
    setTimeout(() => { el.classList.add('exit'); setTimeout(() => el.remove(), 300); }, 3000);
}

// ═══════════════════════ INIT ═══════════════════════

async function init() {
    await Promise.all([loadFlows(), loadTemplates()]);
    bindEvents();
}

async function loadFlows() {
    S.flows = await api('/api/flows');
    els.flowSelect.innerHTML = '<option value="">— 選擇 Flow —</option>' +
        S.flows.map(f => `<option value="${f}">${f}</option>`).join('');
    if (S.flows.length > 0) {
        els.flowSelect.value = S.flows[0];
        await loadFlow(S.flows[0]);
    }
}

async function loadFlow(name) {
    if (!name) return;
    S.currentFlowName = name;
    S.flow = await api(`/api/flow/${name}`);
    S.selectedStep = -1;
    els.flowTaskName.value = S.flow.task_name || '';
    renderSteps();
    renderDetail();
}

async function loadTemplates() {
    S.templates = await api('/api/templates');
    renderTemplates();
}

// ═══════════════════ RENDER ═══════════════════════

function renderTemplates() {
    els.templateCount.textContent = S.templates.length;
    els.templateList.innerHTML = S.templates.map(t => `
    <div class="tpl-card" data-name="${t.name}">
      <div class="tpl-thumb"><img src="/api/thumbnail/${t.name}" loading="lazy" alt="${t.name}"></div>
      <div class="tpl-info">
        <div class="tpl-name">${t.name}</div>
        <div class="tpl-bbox">${t.bbox[2]}×${t.bbox[3]} @ ${t.bbox[0]},${t.bbox[1]}</div>
      </div>
      <div class="tpl-actions">
        <button class="btn-icon btn-add-from-tpl" title="加入流程" data-name="${t.name}">+</button>
      </div>
    </div>
  `).join('');
}

function renderSteps() {
    if (!S.flow) { els.stepList.innerHTML = ''; return; }
    const tplSet = new Set(S.templates.map(t => t.name));
    els.stepList.innerHTML = S.flow.steps.map((s, i) => {
        const valid = tplSet.has(s.feature);
        return `
    <div class="step-card ${i === S.selectedStep ? 'selected' : ''} ${valid ? '' : 'invalid'}"
         data-index="${i}">
      <div class="step-drag" title="拖曳排序">⠿</div>
      <div class="step-priority">${s.priority ?? 0}</div>
      <div class="step-thumb-mini">
        ${valid ? `<img src="/api/thumbnail/${s.feature}" alt="">` : '⚠️'}
      </div>
      <div class="step-body">
        <div class="step-label">${s.label || s.id || '—'}</div>
        <div class="step-feature">feature: ${s.feature}</div>
      </div>
      <span class="step-badge ${s.action || 'click'}">${s.action || 'click'}</span>
    </div>`;
    }).join('');
    initSortable();
}

let sortableInstance = null;
function initSortable() {
    if (sortableInstance) sortableInstance.destroy();
    sortableInstance = new Sortable(els.stepList, {
        handle: '.step-drag',
        ghostClass: 'sortable-ghost',
        chosenClass: 'sortable-chosen',
        animation: 200,
        onEnd(evt) {
            const steps = S.flow.steps;
            const [moved] = steps.splice(evt.oldIndex, 1);
            steps.splice(evt.newIndex, 0, moved);
            // Auto-recalculate priorities (highest first = first in list)
            steps.forEach((s, i) => { s.priority = (steps.length - i) * 10; });
            if (S.selectedStep === evt.oldIndex) S.selectedStep = evt.newIndex;
            renderSteps();
            renderDetail();
        }
    });
}

function renderDetail() {
    if (S.selectedStep < 0 || !S.flow || S.selectedStep >= S.flow.steps.length) {
        els.stepDetail.innerHTML = `<div class="empty-state"><div class="empty-icon">🎯</div><p>選擇一個步驟<br>以編輯詳細設定</p></div>`;
        els.tplPreview.innerHTML = '';
        return;
    }
    const s = S.flow.steps[S.selectedStep];
    const tplOptions = S.templates.map(t =>
        `<option value="${t.name}" ${t.name === s.feature ? 'selected' : ''}>${t.name}</option>`
    ).join('');
    const actionOptions = ['click', 'conditional'].map(a =>
        `<option value="${a}" ${a === s.action ? 'selected' : ''}>${a}</option>`
    ).join('');
    const successOptions = ['', 'increment_count'].map(v =>
        `<option value="${v}" ${v === (s.on_success || '') ? 'selected' : ''}>${v || '— 無 —'}</option>`
    ).join('');

    let html = `
    <div class="detail-group">
      <label class="field-label">模板 (Feature)</label>
      <select class="input" data-field="feature">${tplOptions}</select>
    </div>
    <div class="detail-group">
      <label class="field-label">標籤</label>
      <input class="input" data-field="label" value="${s.label || ''}">
    </div>
    <div class="detail-row">
      <div class="detail-group">
        <label class="field-label">優先序</label>
        <input class="input" type="number" data-field="priority" value="${s.priority ?? 0}">
      </div>
      <div class="detail-group">
        <label class="field-label">動作</label>
        <select class="input" data-field="action">${actionOptions}</select>
      </div>
    </div>
    <div class="detail-group">
      <label class="field-label">ID</label>
      <input class="input" data-field="id" value="${s.id || ''}">
    </div>
    <div class="detail-group">
      <label class="field-label">成功後動作</label>
      <select class="input" data-field="on_success">${successOptions}</select>
    </div>`;

    if (s.action === 'conditional') {
        html += `
    <div class="detail-section-title">條件分支 (JSON)</div>
    <div class="detail-group">
      <label class="field-label">Config Key</label>
      <input class="input" data-field="config_key" value="${s.config_key || ''}">
    </div>
    <div class="detail-group">
      <label class="field-label">Branches</label>
      <textarea class="input" data-field="branches">${JSON.stringify(s.branches || {}, null, 2)}</textarea>
    </div>`;
    }

    if (s.variants && Object.keys(s.variants).length > 0) {
        html += `
    <div class="detail-section-title">Variants (JSON)</div>
    <div class="detail-group">
      <textarea class="input" data-field="variants">${JSON.stringify(s.variants, null, 2)}</textarea>
    </div>`;
    }

    html += `<button class="btn btn-danger btn-sm" id="btn-delete-step" style="margin-top:8px">刪除此步驟</button>`;
    els.stepDetail.innerHTML = html;

    // Preview
    const tpl = S.templates.find(t => t.name === s.feature);
    if (tpl) {
        els.tplPreview.innerHTML = `
      <div class="preview-label">模板預覽 — ${tpl.name} (${tpl.bbox[2]}×${tpl.bbox[3]})</div>
      <img src="/api/thumbnail/${tpl.name}" alt="${tpl.name}">`;
    } else {
        els.tplPreview.innerHTML = `<div class="preview-label" style="color:var(--error)">⚠️ 模板不存在: ${s.feature}</div>`;
    }

    // Bind detail events
    els.stepDetail.querySelectorAll('[data-field]').forEach(el => {
        el.addEventListener('change', onDetailChange);
        el.addEventListener('input', (e) => {
            if (e.target.tagName === 'INPUT' && e.target.type !== 'number') onDetailChange(e);
        });
    });
    const delBtn = $('#btn-delete-step');
    if (delBtn) delBtn.addEventListener('click', onDeleteStep);
}

// ═══════════════════ EVENTS ═══════════════════════

function bindEvents() {
    els.flowSelect.addEventListener('change', (e) => loadFlow(e.target.value));
    $('#btn-save').addEventListener('click', onSave);
    $('#btn-capture').addEventListener('click', onCapture);
    $('#btn-add-step').addEventListener('click', onAddStep);
    $('#btn-new-flow').addEventListener('click', onNewFlow);
    els.flowTaskName.addEventListener('input', (e) => { if (S.flow) S.flow.task_name = e.target.value; });

    // Step selection (delegated)
    els.stepList.addEventListener('click', (e) => {
        const card = e.target.closest('.step-card');
        if (!card || e.target.closest('.step-drag')) return;
        S.selectedStep = parseInt(card.dataset.index);
        renderSteps();
        renderDetail();
    });

    // Template "+" button (delegated)
    els.templateList.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-add-from-tpl');
        if (!btn || !S.flow) return;
        const name = btn.dataset.name;
        addStepFromTemplate(name);
    });

    // Capture modal
    $('.modal-close').addEventListener('click', closeCapture);
    els.captureModal.addEventListener('click', (e) => { if (e.target === els.captureModal) closeCapture(); });
    $('#btn-save-template').addEventListener('click', onSaveTemplate);
    $('#btn-recapture').addEventListener('click', onCapture);
    initCanvasROI();
}

function onDetailChange(e) {
    if (S.selectedStep < 0 || !S.flow) return;
    const field = e.target.dataset.field;
    let val = e.target.value;
    const step = S.flow.steps[S.selectedStep];

    if (field === 'priority') val = parseInt(val) || 0;
    if (field === 'branches' || field === 'variants') {
        try { val = JSON.parse(val); } catch { toast('JSON 格式錯誤', 'error'); return; }
    }
    if (field === 'on_success') {
        if (val) step.on_success = val; else delete step.on_success;
    } else {
        step[field] = val;
    }

    // Re-render step list to reflect label/priority changes
    renderSteps();

    // Update preview if feature changed
    if (field === 'feature') renderDetail();
}

function onDeleteStep() {
    if (S.selectedStep < 0 || !S.flow) return;
    S.flow.steps.splice(S.selectedStep, 1);
    S.selectedStep = -1;
    renderSteps();
    renderDetail();
    toast('步驟已刪除', 'info');
}

function onAddStep() {
    if (!S.flow) { toast('請先選擇 Flow', 'error'); return; }
    const minP = Math.min(...S.flow.steps.map(s => s.priority ?? 0), 10);
    S.flow.steps.push({
        id: `step_${Date.now()}`,
        label: '新步驟',
        feature: S.templates[0]?.name || '',
        action: 'click',
        priority: Math.max(minP - 10, 0),
    });
    S.selectedStep = S.flow.steps.length - 1;
    renderSteps();
    renderDetail();
}

function addStepFromTemplate(name) {
    if (!S.flow) { toast('請先選擇 Flow', 'error'); return; }
    const minP = Math.min(...S.flow.steps.map(s => s.priority ?? 0), 10);
    S.flow.steps.push({
        id: name,
        label: name,
        feature: name,
        action: 'click',
        priority: Math.max(minP - 10, 0),
    });
    S.selectedStep = S.flow.steps.length - 1;
    renderSteps();
    renderDetail();
    toast(`已新增步驟: ${name}`, 'success');
}

async function onSave() {
    if (!S.flow || !S.currentFlowName) { toast('無 Flow 可儲存', 'error'); return; }
    await api(`/api/flow/${S.currentFlowName}`, { method: 'POST', body: S.flow });
    toast('Flow 已儲存！', 'success');
}

async function onNewFlow() {
    const name = prompt('新 Flow 檔名（英文，不含 .json）：');
    if (!name) return;
    const clean = name.replace(/[^\w\-]/g, '_');
    const newFlow = {
        task_name: clean,
        description: '',
        icon: 'PLAY',
        config: {},
        loop: { count_key: '挑戰次數', threshold_key: '辨識門檻' },
        steps: [],
        idle: { message: '⏳ 等待中..', click: { x: 0.5, y: 0.5, variance: 0.01 }, sleep: 1.0 }
    };
    await api(`/api/flow/${clean}`, { method: 'POST', body: newFlow });
    await loadFlows();
    els.flowSelect.value = clean;
    await loadFlow(clean);
    toast(`已建立 Flow: ${clean}`, 'success');
}

// ═══════════════ CAPTURE & ROI ═══════════════════

async function onCapture() {
    toast('正在擷取遊戲畫面…', 'info');
    try {
        const data = await api('/api/capture');
        S.captureData = data;
        S.roi = null;
        showCaptureModal();
    } catch (e) {
        console.error('Capture failed:', e);
    }
}

function showCaptureModal() {
    els.captureModal.classList.remove('hidden');
    els.captureName.value = '';
    $('#btn-save-template').disabled = true;
    els.roiInfo.classList.add('hidden');
    // Wait for layout to compute container size before drawing
    requestAnimationFrame(() => requestAnimationFrame(() => drawCaptureImage()));
}

function closeCapture() {
    els.captureModal.classList.add('hidden');
}

function drawCaptureImage() {
    if (!S.captureData) return;
    const canvas = els.captureCanvas;
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.onload = () => {
        const wrap = canvas.parentElement;
        const maxW = wrap.clientWidth || 900;
        const maxH = wrap.clientHeight || 600;
        const imgRatio = img.width / img.height;

        // Fit to container keeping exact game aspect ratio
        let dispW, dispH;
        if (maxW / maxH > imgRatio) {
            dispH = maxH;
            dispW = Math.round(dispH * imgRatio);
        } else {
            dispW = maxW;
            dispH = Math.round(dispW / imgRatio);
        }

        // Canvas attribute = CSS display (1:1 so mouse coords align perfectly)
        canvas.width = dispW;
        canvas.height = dispH;
        canvas.style.width = dispW + 'px';
        canvas.style.height = dispH + 'px';

        // Scale factor: actual game pixels per canvas pixel
        canvas._pxScale = img.width / dispW;
        canvas._imgW = img.width;
        canvas._imgH = img.height;
        canvas._img = img;
        ctx.drawImage(img, 0, 0, dispW, dispH);
    };
    img.src = `data:image/jpeg;base64,${S.captureData.image}`;
}

function initCanvasROI() {
    const canvas = els.captureCanvas;
    let drawing = false, sx = 0, sy = 0;

    canvas.addEventListener('mousedown', (e) => {
        drawing = true;
        const r = canvas.getBoundingClientRect();
        sx = e.clientX - r.left;
        sy = e.clientY - r.top;
    });

    canvas.addEventListener('mousemove', (e) => {
        const r = canvas.getBoundingClientRect();
        const cx = e.clientX - r.left;
        const cy = e.clientY - r.top;

        // Show crosshair coords (in actual game pixels)
        if (canvas._pxScale) {
            const ax = Math.round(cx * canvas._pxScale);
            const ay = Math.round(cy * canvas._pxScale);
            els.captureCoords.textContent = `${ax}, ${ay}`;
            els.captureCoords.classList.remove('hidden');
        }

        if (!drawing) return;
        // Redraw
        const ctx = canvas.getContext('2d');
        ctx.drawImage(canvas._img, 0, 0, canvas.width, canvas.height);

        const x = Math.min(sx, cx), y = Math.min(sy, cy);
        const w = Math.abs(cx - sx), h = Math.abs(cy - sy);

        // Semi-transparent overlay outside selection
        ctx.fillStyle = 'rgba(0,0,0,0.45)';
        ctx.fillRect(0, 0, canvas.width, y);
        ctx.fillRect(0, y + h, canvas.width, canvas.height - y - h);
        ctx.fillRect(0, y, x, h);
        ctx.fillRect(x + w, y, canvas.width - x - w, h);

        // Selection border
        ctx.strokeStyle = '#8b5cf6';
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 3]);
        ctx.strokeRect(x, y, w, h);
        ctx.setLineDash([]);
    });

    canvas.addEventListener('mouseup', (e) => {
        if (!drawing) return;
        drawing = false;
        const r = canvas.getBoundingClientRect();
        const ex = e.clientX - r.left;
        const ey = e.clientY - r.top;

        const pxScale = canvas._pxScale || 1;
        const x = Math.round(Math.min(sx, ex) * pxScale);
        const y = Math.round(Math.min(sy, ey) * pxScale);
        const w = Math.round(Math.abs(ex - sx) * pxScale);
        const h = Math.round(Math.abs(ey - sy) * pxScale);

        if (w < 5 || h < 5) { S.roi = null; return; }

        S.roi = { x, y, w, h };
        $('#roi-x').textContent = x;
        $('#roi-y').textContent = y;
        $('#roi-w').textContent = w;
        $('#roi-h').textContent = h;
        els.roiInfo.classList.remove('hidden');
        els.captureCoords.textContent = `${x}, ${y} — ${w}×${h}`;

        const nameInput = els.captureName;
        $('#btn-save-template').disabled = !nameInput.value.trim();
        nameInput.addEventListener('input', () => {
            $('#btn-save-template').disabled = !nameInput.value.trim() || !S.roi;
        });
    });
}

async function onSaveTemplate() {
    const name = els.captureName.value.trim();
    if (!name || !S.roi || !S.captureData) return;
    await api('/api/template', {
        method: 'POST',
        body: { name, bbox: [S.roi.x, S.roi.y, S.roi.w, S.roi.h], image: S.captureData.image }
    });
    toast(`模板 "${name}" 已儲存！`, 'success');
    closeCapture();
    await loadTemplates();
}

// ═══════════════════ BOOT ═══════════════════════

document.addEventListener('DOMContentLoaded', init);
