const imageInput = document.getElementById('imageInput');
const processBtn = document.getElementById('processBtn');
const statusText = document.getElementById('statusText');
const inputPreview = document.getElementById('inputPreview');
const outputPreview = document.getElementById('outputPreview');
const outputPreviewWrap = document.getElementById('outputPreviewWrap');
const transparentHint = document.getElementById('transparentHint');
const downloadBtn = document.getElementById('downloadBtn');

let selectedFile = null;
let outputObjectUrl = null;

function setStatus(message) {
  statusText.textContent = message;
}

function resetOutput() {
  if (outputObjectUrl) {
    URL.revokeObjectURL(outputObjectUrl);
    outputObjectUrl = null;
  }
  outputPreview.removeAttribute('src');
  outputPreviewWrap.classList.add('hidden');
  transparentHint.classList.add('hidden');
  downloadBtn.classList.add('hidden');
  downloadBtn.removeAttribute('href');
}

imageInput.addEventListener('change', () => {
  const [file] = imageInput.files;
  selectedFile = file || null;
  resetOutput();

  if (!selectedFile) {
    inputPreview.classList.add('hidden');
    inputPreview.removeAttribute('src');
    processBtn.disabled = true;
    setStatus('');
    return;
  }

  const previewUrl = URL.createObjectURL(selectedFile);
  inputPreview.src = previewUrl;
  inputPreview.classList.remove('hidden');
  processBtn.disabled = false;
  setStatus('Ready');
});

processBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  processBtn.disabled = true;
  setStatus('Processing...');

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const response = await fetch('/api/remove-bg', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || 'Request failed');
    }

    const blob = await response.blob();
    outputObjectUrl = URL.createObjectURL(blob);

    outputPreview.src = outputObjectUrl;
    outputPreviewWrap.classList.remove('hidden');
    transparentHint.classList.remove('hidden');
    downloadBtn.href = outputObjectUrl;
    downloadBtn.classList.remove('hidden');
    setStatus('Done');
  } catch (error) {
    setStatus(error.message || 'Error while processing image');
  } finally {
    processBtn.disabled = false;
  }
});
