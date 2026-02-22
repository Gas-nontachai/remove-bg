const imageInput = document.getElementById('imageInput');
const featherInput = document.getElementById('featherInput');
const featherValue = document.getElementById('featherValue');
const alphaBoostInput = document.getElementById('alphaBoostInput');
const alphaBoostValue = document.getElementById('alphaBoostValue');
const processBtn = document.getElementById('processBtn');
const reprocessBtn = document.getElementById('reprocessBtn');
const undoBtn = document.getElementById('undoBtn');
const redoBtn = document.getElementById('redoBtn');
const resetEditsBtn = document.getElementById('resetEditsBtn');
const statusText = document.getElementById('statusText');
const singleProgressBar = document.getElementById('singleProgressBar');
const closePolygonBtn = document.getElementById('closePolygonBtn');
const clearPolygonBtn = document.getElementById('clearPolygonBtn');

const brushSizeInput = document.getElementById('brushSizeInput');
const brushSizeValue = document.getElementById('brushSizeValue');
const wandToleranceInput = document.getElementById('wandToleranceInput');
const wandToleranceValue = document.getElementById('wandToleranceValue');

const toolButtons = Array.from(document.querySelectorAll('.tool-btn'));
const editCanvas = document.getElementById('editCanvas');
const overlayCanvas = document.getElementById('overlayCanvas');
const canvasViewport = document.getElementById('canvasViewport');
const canvasTransform = document.getElementById('canvasTransform');
const zoomInBtn = document.getElementById('zoomInBtn');
const zoomOutBtn = document.getElementById('zoomOutBtn');
const resetViewBtn = document.getElementById('resetViewBtn');
const zoomLabel = document.getElementById('zoomLabel');

const bgMode = document.getElementById('bgMode');
const colorControls = document.getElementById('colorControls');
const gradientControls = document.getElementById('gradientControls');
const imageControls = document.getElementById('imageControls');
const bgColor = document.getElementById('bgColor');
const gradientA = document.getElementById('gradientA');
const gradientB = document.getElementById('gradientB');
const bgImageInput = document.getElementById('bgImageInput');
const downloadPngBtn = document.getElementById('downloadPngBtn');
const downloadJpgBtn = document.getElementById('downloadJpgBtn');

const batchInput = document.getElementById('batchInput');
const batchBtn = document.getElementById('batchBtn');
const batchStatus = document.getElementById('batchStatus');
const batchProgressBar = document.getElementById('batchProgressBar');

const compareCanvas = document.getElementById('compareCanvas');
const editCtx = editCanvas.getContext('2d');
const overlayCtx = overlayCanvas.getContext('2d');
const compareCtx = compareCanvas.getContext('2d');

const originalCanvas = document.createElement('canvas');
const originalCtx = originalCanvas.getContext('2d');
const composeCanvas = document.createElement('canvas');
const composeCtx = composeCanvas.getContext('2d');
const compareSlider = document.getElementById('compareSlider');

const state = {
  selectedFile: null,
  bgImage: null,
  tool: 'brush-erase',
  brushSize: 28,
  wandTolerance: 30,
  isDrawing: false,
  isPanning: false,
  panStartClientX: 0,
  panStartClientY: 0,
  startPanX: 0,
  startPanY: 0,
  lastPoint: null,
  pointerPoint: null,
  polygonPoints: [],
  undoStack: [],
  redoStack: [],
  maxUndo: 25,
  scale: 1,
  panX: 0,
  panY: 0,
  hasOutput: false,
  comparePercent: 100,
  spacePanActive: false,
  previousToolBeforeSpace: 'brush-erase',
};

const AUTOSAVE_KEY = 'rmbg_studio_settings_v1';

editCanvas.style.touchAction = 'none';

function setStatus(message) {
  statusText.textContent = message;
}

function setBatchStatus(message) {
  batchStatus.textContent = message;
}

function setSingleProgress(progress) {
  singleProgressBar.style.width = `${Math.max(0, Math.min(100, Number(progress) || 0))}%`;
}

function setBatchProgress(progress) {
  batchProgressBar.style.width = `${Math.max(0, Math.min(100, Number(progress) || 0))}%`;
}

function updateSliderLabels() {
  featherValue.textContent = Number(featherInput.value).toFixed(1);
  alphaBoostValue.textContent = Number(alphaBoostInput.value).toFixed(1);
  brushSizeValue.textContent = `${state.brushSize} px`;
  wandToleranceValue.textContent = String(state.wandTolerance);
}

function saveUiSettings() {
  const payload = {
    feather: featherInput.value,
    alphaBoost: alphaBoostInput.value,
    brushSize: brushSizeInput.value,
    wandTolerance: wandToleranceInput.value,
    bgMode: bgMode.value,
    bgColor: bgColor.value,
    gradientA: gradientA.value,
    gradientB: gradientB.value,
    comparePercent: String(state.comparePercent),
  };
  localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(payload));
}

function loadUiSettings() {
  const raw = localStorage.getItem(AUTOSAVE_KEY);
  if (!raw) return;
  try {
    const payload = JSON.parse(raw);
    if (payload.feather) featherInput.value = payload.feather;
    if (payload.alphaBoost) alphaBoostInput.value = payload.alphaBoost;
    if (payload.brushSize) brushSizeInput.value = payload.brushSize;
    if (payload.wandTolerance) wandToleranceInput.value = payload.wandTolerance;
    if (payload.bgMode) bgMode.value = payload.bgMode;
    if (payload.bgColor) bgColor.value = payload.bgColor;
    if (payload.gradientA) gradientA.value = payload.gradientA;
    if (payload.gradientB) gradientB.value = payload.gradientB;
    if (payload.comparePercent) state.comparePercent = Number(payload.comparePercent) || 100;
  } catch (_) {
    localStorage.removeItem(AUTOSAVE_KEY);
  }
}

function updateTransform() {
  canvasTransform.style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${state.scale})`;
  zoomLabel.textContent = `${Math.round(state.scale * 100)}%`;
}

function clampScale(nextScale) {
  return Math.max(0.2, Math.min(5, nextScale));
}

function zoomBy(factor) {
  state.scale = clampScale(state.scale * factor);
  updateTransform();
}

function resetView() {
  state.scale = 1;
  state.panX = 0;
  state.panY = 0;
  updateTransform();
}

function setTool(tool) {
  state.tool = tool;
  toolButtons.forEach((button) => {
    button.dataset.active = button.dataset.tool === tool ? 'true' : 'false';
  });
  drawOverlay();
}

function clearPolygon() {
  state.polygonPoints = [];
  drawOverlay();
}

function updateActionButtons() {
  const editable = state.hasOutput;
  processBtn.disabled = !state.selectedFile;
  reprocessBtn.disabled = !state.selectedFile;
  undoBtn.disabled = !editable || state.undoStack.length === 0;
  redoBtn.disabled = !editable || state.redoStack.length === 0;
  resetEditsBtn.disabled = !editable;
  closePolygonBtn.disabled = !editable || state.polygonPoints.length < 3;
  clearPolygonBtn.disabled = !editable || state.polygonPoints.length === 0;
  downloadPngBtn.disabled = !editable;
  downloadJpgBtn.disabled = !editable;
}

function renderCompareView() {
  if (!state.hasOutput) return;
  const width = compareCanvas.width;
  const height = compareCanvas.height;
  const split = Math.round((state.comparePercent / 100) * width);

  compareCtx.clearRect(0, 0, width, height);
  if (split > 0) {
    compareCtx.drawImage(originalCanvas, 0, 0, split, height, 0, 0, split, height);
  }
}

function canvasPointFromEvent(event) {
  const rect = editCanvas.getBoundingClientRect();
  if (!rect.width || !rect.height) {
    return { x: 0, y: 0 };
  }
  return {
    x: ((event.clientX - rect.left) / rect.width) * editCanvas.width,
    y: ((event.clientY - rect.top) / rect.height) * editCanvas.height,
  };
}

function loadImageFromBlob(blob) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Unable to load image'));
    };
    image.src = url;
  });
}

function captureState() {
  return editCtx.getImageData(0, 0, editCanvas.width, editCanvas.height);
}

function applyState(imageData) {
  editCtx.putImageData(imageData, 0, 0);
  renderCompareView();
  drawOverlay();
}

function pushUndoState() {
  if (!state.hasOutput) return;
  state.undoStack.push(captureState());
  if (state.undoStack.length > state.maxUndo) {
    state.undoStack.shift();
  }
  state.redoStack = [];
  updateActionButtons();
}

function undo() {
  if (!state.undoStack.length) return;
  const previous = state.undoStack.pop();
  state.redoStack.push(captureState());
  applyState(previous);
  updateActionButtons();
}

function redo() {
  if (!state.redoStack.length) return;
  const next = state.redoStack.pop();
  state.undoStack.push(captureState());
  applyState(next);
  updateActionButtons();
}

function resetEdits() {
  if (!state.hasOutput) return;
  pushUndoState();
  editCtx.clearRect(0, 0, editCanvas.width, editCanvas.height);
  editCtx.drawImage(originalCanvas, 0, 0);
  renderCompareView();
  clearPolygon();
  drawOverlay();
}

function prepareCanvasSize(width, height) {
  [compareCanvas, editCanvas, overlayCanvas, originalCanvas, composeCanvas].forEach((canvas) => {
    canvas.width = width;
    canvas.height = height;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
  });
  canvasTransform.style.width = `${width}px`;
  canvasTransform.style.height = `${height}px`;
}

function interpolatePoints(from, to, spacing) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const distance = Math.hypot(dx, dy);
  if (distance < 0.1) {
    return [to];
  }

  const steps = Math.max(1, Math.floor(distance / spacing));
  const points = [];
  for (let i = 1; i <= steps; i += 1) {
    const t = i / steps;
    points.push({ x: from.x + dx * t, y: from.y + dy * t });
  }
  return points;
}

function drawBrushPoint(point) {
  if (state.tool === 'brush-erase') {
    editCtx.save();
    editCtx.globalCompositeOperation = 'destination-out';
    editCtx.beginPath();
    editCtx.arc(point.x, point.y, state.brushSize / 2, 0, Math.PI * 2);
    editCtx.fill();
    editCtx.restore();
    return;
  }

  if (state.tool === 'brush-restore') {
    editCtx.save();
    editCtx.beginPath();
    editCtx.arc(point.x, point.y, state.brushSize / 2, 0, Math.PI * 2);
    editCtx.clip();
    editCtx.drawImage(originalCanvas, 0, 0);
    editCtx.restore();
  }
}

function colorDistanceSq(data, idxA, idxB) {
  const dr = data[idxA] - data[idxB];
  const dg = data[idxA + 1] - data[idxB + 1];
  const db = data[idxA + 2] - data[idxB + 2];
  const da = data[idxA + 3] - data[idxB + 3];
  return dr * dr + dg * dg + db * db + da * da;
}

function applyMagicWand(point, mode) {
  const width = editCanvas.width;
  const height = editCanvas.height;
  const x = Math.floor(point.x);
  const y = Math.floor(point.y);
  if (x < 0 || y < 0 || x >= width || y >= height) return;

  const editData = editCtx.getImageData(0, 0, width, height);
  const originalData = originalCtx.getImageData(0, 0, width, height);
  const data = editData.data;
  const source = originalData.data;
  const toleranceSq = state.wandTolerance * state.wandTolerance * 4;
  const targetIndex = (y * width + x) * 4;

  const visited = new Uint8Array(width * height);
  const queue = [y * width + x];

  while (queue.length) {
    const current = queue.pop();
    if (visited[current]) continue;
    visited[current] = 1;

    const cx = current % width;
    const cy = Math.floor(current / width);
    const idx = (cy * width + cx) * 4;
    if (colorDistanceSq(data, idx, targetIndex) > toleranceSq) continue;

    if (mode === 'erase') {
      data[idx + 3] = 0;
    } else {
      data[idx] = source[idx];
      data[idx + 1] = source[idx + 1];
      data[idx + 2] = source[idx + 2];
      data[idx + 3] = source[idx + 3];
    }

    if (cx > 0) queue.push(current - 1);
    if (cx < width - 1) queue.push(current + 1);
    if (cy > 0) queue.push(current - width);
    if (cy < height - 1) queue.push(current + width);
  }

  editCtx.putImageData(editData, 0, 0);
}

function applyPolygon(mode) {
  if (state.polygonPoints.length < 3) return;
  pushUndoState();

  editCtx.save();
  editCtx.beginPath();
  state.polygonPoints.forEach((point, index) => {
    if (index === 0) {
      editCtx.moveTo(point.x, point.y);
    } else {
      editCtx.lineTo(point.x, point.y);
    }
  });
  editCtx.closePath();

  if (mode === 'erase') {
    editCtx.globalCompositeOperation = 'destination-out';
    editCtx.fill();
  } else {
    editCtx.clip();
    editCtx.drawImage(originalCanvas, 0, 0);
  }

  editCtx.restore();
  clearPolygon();
}

function drawOverlay() {
  overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

  if (state.pointerPoint && (state.tool === 'brush-erase' || state.tool === 'brush-restore')) {
    overlayCtx.strokeStyle = 'rgba(15, 23, 42, 0.8)';
    overlayCtx.lineWidth = 1;
    overlayCtx.beginPath();
    overlayCtx.arc(state.pointerPoint.x, state.pointerPoint.y, state.brushSize / 2, 0, Math.PI * 2);
    overlayCtx.stroke();
  }

  if (state.polygonPoints.length) {
    overlayCtx.lineWidth = 1.5;
    overlayCtx.strokeStyle = 'rgba(14, 116, 144, 0.95)';
    overlayCtx.fillStyle = 'rgba(14, 116, 144, 0.15)';

    overlayCtx.beginPath();
    state.polygonPoints.forEach((point, index) => {
      if (index === 0) overlayCtx.moveTo(point.x, point.y);
      else overlayCtx.lineTo(point.x, point.y);
    });

    if (state.pointerPoint && state.tool.startsWith('polygon-')) {
      overlayCtx.lineTo(state.pointerPoint.x, state.pointerPoint.y);
    }

    overlayCtx.stroke();

    state.polygonPoints.forEach((point) => {
      overlayCtx.beginPath();
      overlayCtx.arc(point.x, point.y, 3, 0, Math.PI * 2);
      overlayCtx.fillStyle = 'rgba(2, 132, 199, 1)';
      overlayCtx.fill();
    });
  }
}

async function submitSingleJob(file) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('feather_radius', featherInput.value);
  formData.append('alpha_boost', alphaBoostInput.value);

  const response = await fetch('/api/jobs/remove-bg', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Failed to submit job');
  }

  return response.json();
}

async function submitBatchJob(files) {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  formData.append('feather_radius', featherInput.value);
  formData.append('alpha_boost', alphaBoostInput.value);

  const response = await fetch('/api/jobs/remove-bg-batch', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Failed to submit batch job');
  }

  return response.json();
}

async function getJobStatus(jobId) {
  const response = await fetch(`/api/jobs/${jobId}`);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Failed to get job status');
  }
  return response.json();
}

async function pollJob(jobId, onUpdate) {
  while (true) {
    const status = await getJobStatus(jobId);
    if (onUpdate) onUpdate(status);
    if (status.status === 'finished') {
      return status;
    }
    if (status.status === 'failed') {
      throw new Error(status.error || 'Job failed');
    }
    await new Promise((resolve) => {
      setTimeout(resolve, 1100);
    });
  }
}

async function downloadJobBlob(jobId) {
  const response = await fetch(`/api/jobs/${jobId}/download`);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Failed to download result');
  }
  return response.blob();
}

async function loadProcessedImage(blob) {
  const image = await loadImageFromBlob(blob);
  prepareCanvasSize(image.width, image.height);

  originalCtx.clearRect(0, 0, image.width, image.height);
  originalCtx.drawImage(image, 0, 0);

  editCtx.clearRect(0, 0, image.width, image.height);
  editCtx.drawImage(image, 0, 0);

  state.hasOutput = true;
  state.undoStack = [];
  state.redoStack = [];
  state.polygonPoints = [];
  state.pointerPoint = null;
  renderCompareView();
  drawOverlay();
  updateActionButtons();
}

function updateBackgroundControlVisibility() {
  const mode = bgMode.value;
  colorControls.classList.toggle('hidden', mode !== 'color');
  gradientControls.classList.toggle('hidden', mode !== 'gradient');
  imageControls.classList.toggle('hidden', mode !== 'image');
}

function drawCoverImage(image, targetCtx, width, height) {
  const scale = Math.max(width / image.width, height / image.height);
  const drawWidth = image.width * scale;
  const drawHeight = image.height * scale;
  const offsetX = (width - drawWidth) / 2;
  const offsetY = (height - drawHeight) / 2;
  targetCtx.drawImage(image, offsetX, offsetY, drawWidth, drawHeight);
}

function buildComposedCanvas(format) {
  if (!state.hasOutput) return null;

  const width = editCanvas.width;
  const height = editCanvas.height;
  composeCanvas.width = width;
  composeCanvas.height = height;

  composeCtx.clearRect(0, 0, width, height);
  const mode = bgMode.value;

  if (mode === 'color') {
    composeCtx.fillStyle = bgColor.value;
    composeCtx.fillRect(0, 0, width, height);
  } else if (mode === 'gradient') {
    const grad = composeCtx.createLinearGradient(0, 0, width, height);
    grad.addColorStop(0, gradientA.value);
    grad.addColorStop(1, gradientB.value);
    composeCtx.fillStyle = grad;
    composeCtx.fillRect(0, 0, width, height);
  } else if (mode === 'image' && state.bgImage) {
    drawCoverImage(state.bgImage, composeCtx, width, height);
  } else if (format === 'jpeg') {
    composeCtx.fillStyle = '#ffffff';
    composeCtx.fillRect(0, 0, width, height);
  }

  composeCtx.drawImage(editCanvas, 0, 0);
  return composeCanvas;
}

function downloadCanvas(canvas, mimeType, filename, quality = 0.92) {
  canvas.toBlob(
    (blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
    },
    mimeType,
    quality,
  );
}

async function processSingleImage() {
  if (!state.selectedFile) return;

  processBtn.disabled = true;
  reprocessBtn.disabled = true;
  setStatus('Submitting job...');
  setSingleProgress(0);

  try {
    const { job_id: jobId } = await submitSingleJob(state.selectedFile);
    const status = await pollJob(jobId, (jobState) => {
      setStatus(`Job: ${jobState.status} (${jobState.stage || 'running'})`);
      setSingleProgress(jobState.progress || 0);
    });
    if (!status.download_path) {
      throw new Error('Result is missing download path');
    }
    const blob = await downloadJobBlob(jobId);
    await loadProcessedImage(blob);
    setSingleProgress(100);
    setStatus('Done');
  } catch (error) {
    setStatus(error.message || 'Processing failed');
  } finally {
    processBtn.disabled = false;
    reprocessBtn.disabled = false;
    updateActionButtons();
  }
}

async function processBatch() {
  const files = Array.from(batchInput.files || []);
  if (!files.length) return;

  batchBtn.disabled = true;
  setBatchStatus('Submitting batch job...');
  setBatchProgress(0);

  try {
    const { job_id: jobId } = await submitBatchJob(files);
    const status = await pollJob(jobId, (jobState) => {
      setBatchStatus(`Batch: ${jobState.status} (${jobState.stage || 'running'})`);
      setBatchProgress(jobState.progress || 0);
    });
    if (!status.download_path) {
      throw new Error('Batch result is missing download path');
    }
    const zipBlob = await downloadJobBlob(jobId);
    const url = URL.createObjectURL(zipBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = status.filename || 'removed-backgrounds.zip';
    link.click();
    URL.revokeObjectURL(url);

    setBatchStatus('Batch complete');
    setBatchProgress(100);
  } catch (error) {
    setBatchStatus(error.message || 'Batch failed');
  } finally {
    batchBtn.disabled = false;
  }
}

imageInput.addEventListener('change', () => {
  const [file] = imageInput.files;
  state.selectedFile = file || null;
  updateActionButtons();
  setSingleProgress(0);
  setStatus(state.selectedFile ? 'Ready' : '');
});

processBtn.addEventListener('click', processSingleImage);
reprocessBtn.addEventListener('click', processSingleImage);

featherInput.addEventListener('input', updateSliderLabels);
featherInput.addEventListener('input', saveUiSettings);
alphaBoostInput.addEventListener('input', updateSliderLabels);
alphaBoostInput.addEventListener('input', saveUiSettings);
brushSizeInput.addEventListener('input', () => {
  state.brushSize = Number(brushSizeInput.value);
  updateSliderLabels();
  drawOverlay();
  saveUiSettings();
});
wandToleranceInput.addEventListener('input', () => {
  state.wandTolerance = Number(wandToleranceInput.value);
  updateSliderLabels();
  saveUiSettings();
});

undoBtn.addEventListener('click', undo);
redoBtn.addEventListener('click', redo);
resetEditsBtn.addEventListener('click', resetEdits);

closePolygonBtn.addEventListener('click', () => {
  if (state.tool === 'polygon-erase') applyPolygon('erase');
  if (state.tool === 'polygon-restore') applyPolygon('restore');
  updateActionButtons();
});

clearPolygonBtn.addEventListener('click', () => {
  clearPolygon();
  updateActionButtons();
});

toolButtons.forEach((button) => {
  button.addEventListener('click', () => setTool(button.dataset.tool));
});

zoomInBtn.addEventListener('click', () => zoomBy(1.2));
zoomOutBtn.addEventListener('click', () => zoomBy(1 / 1.2));
resetViewBtn.addEventListener('click', resetView);

canvasViewport.addEventListener('wheel', (event) => {
  if (!state.hasOutput) return;
  event.preventDefault();
  zoomBy(event.deltaY < 0 ? 1.1 : 1 / 1.1);
});

editCanvas.addEventListener('pointerdown', (event) => {
  if (!state.hasOutput) return;

  const point = canvasPointFromEvent(event);
  state.pointerPoint = point;

  if (state.tool === 'pan') {
    state.isPanning = true;
    state.panStartClientX = event.clientX;
    state.panStartClientY = event.clientY;
    state.startPanX = state.panX;
    state.startPanY = state.panY;
    return;
  }

  if (state.tool === 'brush-erase' || state.tool === 'brush-restore') {
    pushUndoState();
    state.isDrawing = true;
    state.lastPoint = point;
    drawBrushPoint(point);
    drawOverlay();
    return;
  }

  if (state.tool === 'wand-erase' || state.tool === 'wand-restore') {
    pushUndoState();
    applyMagicWand(point, state.tool === 'wand-erase' ? 'erase' : 'restore');
    updateActionButtons();
    return;
  }

  if (state.tool === 'polygon-erase' || state.tool === 'polygon-restore') {
    state.polygonPoints.push(point);
    updateActionButtons();
    drawOverlay();
  }
});

editCanvas.addEventListener('pointermove', (event) => {
  if (!state.hasOutput) return;
  const point = canvasPointFromEvent(event);
  state.pointerPoint = point;

  if (state.isPanning) {
    state.panX = state.startPanX + (event.clientX - state.panStartClientX);
    state.panY = state.startPanY + (event.clientY - state.panStartClientY);
    updateTransform();
    return;
  }

  if (state.isDrawing && state.lastPoint) {
    const points = interpolatePoints(state.lastPoint, point, Math.max(2, state.brushSize / 4));
    points.forEach(drawBrushPoint);
    state.lastPoint = point;
  }

  drawOverlay();
});

editCanvas.addEventListener('pointerup', () => {
  state.isDrawing = false;
  state.isPanning = false;
  state.lastPoint = null;
  updateActionButtons();
});

editCanvas.addEventListener('pointerleave', () => {
  if (!state.isDrawing) {
    state.pointerPoint = null;
    drawOverlay();
  }
});

editCanvas.addEventListener('dblclick', () => {
  if (state.tool === 'polygon-erase') applyPolygon('erase');
  if (state.tool === 'polygon-restore') applyPolygon('restore');
  updateActionButtons();
});

bgMode.addEventListener('change', updateBackgroundControlVisibility);
bgMode.addEventListener('change', saveUiSettings);
bgColor.addEventListener('input', saveUiSettings);
gradientA.addEventListener('input', saveUiSettings);
gradientB.addEventListener('input', saveUiSettings);
compareSlider.addEventListener('input', () => {
  state.comparePercent = Number(compareSlider.value);
  renderCompareView();
  saveUiSettings();
});

bgImageInput.addEventListener('change', () => {
  const [file] = bgImageInput.files || [];
  if (!file) {
    state.bgImage = null;
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    const image = new Image();
    image.onload = () => {
      state.bgImage = image;
    };
    image.src = reader.result;
  };
  reader.readAsDataURL(file);
});

downloadPngBtn.addEventListener('click', () => {
  const canvas = buildComposedCanvas('png');
  if (!canvas) return;
  downloadCanvas(canvas, 'image/png', 'result.png');
});

downloadJpgBtn.addEventListener('click', () => {
  const canvas = buildComposedCanvas('jpeg');
  if (!canvas) return;
  downloadCanvas(canvas, 'image/jpeg', 'result.jpg');
});

batchInput.addEventListener('change', () => {
  const files = Array.from(batchInput.files || []);
  batchBtn.disabled = files.length === 0;
  setBatchProgress(0);
  setBatchStatus(files.length ? `${files.length} file(s) selected` : '');
});

batchBtn.addEventListener('click', processBatch);

window.addEventListener('keydown', (event) => {
  if (event.target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) return;
  const key = event.key.toLowerCase();
  if (key === 'b') setTool('brush-erase');
  if (key === 'e') setTool('brush-restore');
  if (key === 'w') setTool('wand-erase');
  if (key === 'p') setTool('polygon-erase');
  if (key === 'z') undo();
  if (key === 'y') redo();
  if (key === ' ') {
    event.preventDefault();
    if (!state.spacePanActive) {
      state.spacePanActive = true;
      state.previousToolBeforeSpace = state.tool;
      setTool('pan');
    }
  }
});

window.addEventListener('keyup', (event) => {
  if (event.key === ' ') {
    state.spacePanActive = false;
    setTool(state.previousToolBeforeSpace || 'brush-erase');
  }
});

loadUiSettings();
state.brushSize = Number(brushSizeInput.value);
state.wandTolerance = Number(wandToleranceInput.value);
updateSliderLabels();
updateBackgroundControlVisibility();
setTool('brush-erase');
compareSlider.value = String(state.comparePercent);
updateActionButtons();
resetView();
