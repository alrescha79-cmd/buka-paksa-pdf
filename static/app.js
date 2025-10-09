// Frontend logic for the redesigned Indonesian UI
// Wires drag/drop upload, mode selection, start/stop, and status polling to Flask endpoints

(function() {
  // Elements
  const uploadArea = document.getElementById('uploadArea');
  const selectFileBtn = document.getElementById('selectFileBtn');
  const fileInput = document.getElementById('fileInput');
  const fileInfo = document.getElementById('fileInfo');
  const fileNameEl = document.getElementById('fileName');
  const fileSizeEl = document.getElementById('fileSize');
  const changeFileBtn = document.getElementById('changeFileBtn');

  const modeSection = document.getElementById('modeSection');
  const modeCards = document.querySelectorAll('.mode-card');
  const controlSection = document.getElementById('controlSection');
  const startBtn = document.getElementById('startBtn');
  const cancelBtn = document.getElementById('cancelBtn');

  const progressSection = document.getElementById('progressSection');
  const progressFill = document.getElementById('progressFill');
  const progressText = document.getElementById('progressText');
  const currentPasswordEl = document.getElementById('currentPassword');
  const elapsedTimeEl = document.getElementById('elapsedTime');
  const attemptCountEl = document.getElementById('attemptCount');
  const estimatedTimeEl = document.getElementById('estimatedTime');
  const statusMessageEl = document.getElementById('statusMessage');

  const resultsSection = document.getElementById('resultsSection');
  const resultsContent = document.getElementById('resultsContent');
  const resetBtn = document.getElementById('resetBtn');

  const confirmModal = document.getElementById('confirmModal');
  const cancelConfirmBtn = document.getElementById('cancelConfirm');
  const confirmStartBtn = document.getElementById('confirmStart');

  const STORAGE_PREFIX = 'pdf-viewer:';

  // State
  let selectedFile = null;
  let selectedMode = null; // '6' or '8'
  let statusInterval = null;
  let lastProgress = 0;
  let unlockedBlobUrl = null;

  // Helpers
  function bytesToSize(bytes) {
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
  }

  function safeSetLocalStorage(key, value) {
    try {
      localStorage.setItem(key, value);
      return true;
    } catch (err) {
      console.warn('Failed to persist data to localStorage', err);
      return false;
    }
  }

  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result || '';
        const [, base64 = ''] = String(result).split(',');
        resolve(base64);
      };
      reader.onerror = () => reject(reader.error || new Error('Failed to read file.'));
      reader.readAsDataURL(file);
    });
  }

  function cacheUploadedPdf(file) {
    fileToBase64(file)
      .then((base64) => {
        if (!base64) return;
        const key = `${STORAGE_PREFIX}original:${file.name}`;
        safeSetLocalStorage(key, base64);
      })
      .catch((err) => console.warn('Unable to cache uploaded PDF', err));
  }

  function storeUnlockedPdf(base64, filename) {
    if (!base64) return false;
    const key = `${STORAGE_PREFIX}unlocked:${filename}`;
    return safeSetLocalStorage(key, base64);
  }

  function getUnlockedPdfFromStorage(filename) {
    const key = `${STORAGE_PREFIX}unlocked:${filename}`;
    return localStorage.getItem(key);
  }

  function createBlobUrlFromBase64(base64) {
    try {
      const byteString = atob(base64);
      const len = byteString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i += 1) {
        bytes[i] = byteString.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: 'application/pdf' });
      return URL.createObjectURL(blob);
    } catch (err) {
      console.warn('Failed to create blob from base64', err);
      return null;
    }
  }

  function revokeUnlockedBlob() {
    if (unlockedBlobUrl) {
      URL.revokeObjectURL(unlockedBlobUrl);
      unlockedBlobUrl = null;
    }
  }

  function show(el) { el.classList.remove('hidden'); }
  function hide(el) { el.classList.add('hidden'); }

  function resetAll() {
    // Stop polling
    if (statusInterval) clearInterval(statusInterval);

    // Reset state
    selectedFile = null;
    selectedMode = null;
    lastProgress = 0;

    // Reset UI
    fileInput.value = '';
    hide(fileInfo);
    fileNameEl.textContent = '';
    fileSizeEl.textContent = '';

  revokeUnlockedBlob();

    // Sections
    show(uploadArea.closest('section'));
    hide(modeSection);
    hide(controlSection);
    hide(progressSection);
    hide(resultsSection);

    // Controls
    startBtn.disabled = true;
    hide(cancelBtn);

    // Progress
    progressFill.style.width = '0%';
    progressText.textContent = '0%';
    currentPasswordEl.textContent = '-';
    elapsedTimeEl.textContent = '00:00:00';
    attemptCountEl.textContent = '0';
    estimatedTimeEl.textContent = '-';
    statusMessageEl.textContent = 'Menunggu file diunggah...';

    // Clear selection highlight
    modeCards.forEach(c => c.classList.remove('selected'));
  }

  function openModal() { confirmModal.classList.remove('hidden'); }
  function closeModal() { confirmModal.classList.add('hidden'); }

  // Upload handlers
  selectFileBtn.addEventListener('click', () => fileInput.click());
  changeFileBtn.addEventListener('click', () => fileInput.click());

  uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
  });

  uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
  });

  // Also allow clicking anywhere on the drop area to open the file picker
  uploadArea.addEventListener('click', (e) => {
    // If the explicit select button was clicked, the button handler will run
    if (e.target.closest('button')) return;
    fileInput.click();
  });

  uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) handleSelectedFile(file);
  });

  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) handleSelectedFile(file);
  });

  function handleSelectedFile(file) {
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      alert('Hanya file PDF yang diizinkan.');
      return;
    }
    selectedFile = file;
    fileNameEl.textContent = file.name;
    fileSizeEl.textContent = bytesToSize(file.size);
    show(fileInfo);
    show(modeSection);
    cacheUploadedPdf(file);
    // Scroll into view
    modeSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Mode selection
  modeCards.forEach(card => {
    card.addEventListener('click', () => {
      modeCards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      selectedMode = card.getAttribute('data-mode');
      show(controlSection);
      startBtn.disabled = false;
      controlSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  // Start process
  startBtn.addEventListener('click', async () => {
    if (!selectedFile || !selectedMode) return;

    if (selectedMode === '8') {
      openModal();
      return;
    }

    await startCracking();
  });

  confirmStartBtn.addEventListener('click', async () => {
    closeModal();
    await startCracking();
  });
  cancelConfirmBtn.addEventListener('click', () => closeModal());

  async function startCracking() {
    try {
      // Reset visual state
      hide(resultsSection);
      show(progressSection);
      statusMessageEl.textContent = 'Mengunggah dan memulai proses...';
      startBtn.disabled = true;
      cancelBtn.classList.remove('hidden');

      const formData = new FormData();
      formData.append('pdf', selectedFile);
      formData.append('digit_mode', selectedMode);
      formData.append('thread_mode', 'multi');

      const res = await fetch('/crack', { method: 'POST', body: formData });
      const json = await res.json();
      if (!res.ok) {
        alert(json.error || 'Terjadi kesalahan saat memulai proses.');
        startBtn.disabled = false;
        cancelBtn.classList.add('hidden');
        return;
      }

      // Begin polling
      statusInterval = setInterval(updateStatus, 600);
    } catch (err) {
      alert('Gagal terhubung ke server.');
      startBtn.disabled = false;
      cancelBtn.classList.add('hidden');
    }
  }

  // Cancel/Stop
  cancelBtn.addEventListener('click', async () => {
    cancelBtn.disabled = true;
    try {
      await fetch('/stop', { method: 'POST' });
    } catch {}
    if (statusInterval) clearInterval(statusInterval);
    statusMessageEl.textContent = 'Proses dibatalkan oleh pengguna.';
    show(resultsSection);
    resultsContent.innerHTML = `
      <div class="failure-result">
        <div class="failure-icon">⛔</div>
        <h3>Proses Dihentikan</h3>
        <p>Proses brute force dihentikan oleh pengguna.</p>
      </div>
    `;
    cancelBtn.classList.add('hidden');
    startBtn.disabled = false;
  });

  // Polling status
  async function updateStatus() {
    try {
      const res = await fetch('/status');
      const data = await res.json();

      // Update common fields
      const total = data.total || (selectedMode === '6' ? 1_000_000 : 100_000_000);
      const progress = Math.min(data.progress || 0, total);
      const pct = total > 0 ? ((progress / total) * 100) : 0;
      progressFill.style.width = `${pct.toFixed(2)}%`;
      progressText.textContent = `${pct.toFixed(0)}%`;
      currentPasswordEl.textContent = data.current_attempt || '-';
      elapsedTimeEl.textContent = data.elapsed || '0s';
      attemptCountEl.textContent = String(progress);
      estimatedTimeEl.textContent = data.eta || '-';

      if (data.status === 'running') {
        statusMessageEl.textContent = `Berjalan • ${data.rate || 0} percobaan/detik`;
        lastProgress = progress;
        return;
      }

      // Terminal states
      clearInterval(statusInterval);
      cancelBtn.classList.add('hidden');
      show(resultsSection);

      if (data.status === 'found') {
        statusMessageEl.textContent = 'Password ditemukan!';
        let storageMessage = '';
        let blobUrl = null;

        if (data.unlocked_pdf_base64) {
          const stored = storeUnlockedPdf(data.unlocked_pdf_base64, data.filename);
          if (!stored) {
            storageMessage = '<p class="text-warning">Tidak dapat menyimpan PDF ke local storage (batas ruang tercapai).</p>';
          }
          revokeUnlockedBlob();
          blobUrl = createBlobUrlFromBase64(data.unlocked_pdf_base64);
        } else {
          const cached = getUnlockedPdfFromStorage(data.filename);
          if (cached) {
            revokeUnlockedBlob();
            blobUrl = createBlobUrlFromBase64(cached);
          }
        }

        if (!blobUrl) {
          storageMessage += '<p class="text-warning">PDF belum tersedia di browser. Coba muat ulang status atau periksa koneksi.</p>';
        } else {
          unlockedBlobUrl = blobUrl;
        }

        resultsContent.innerHTML = `
          <div class="success-result">
            <div class="success-icon">🎉</div>
            <h3>Berhasil Membuka PDF</h3>
            <div class="password-display">
              <div class="password-label">Password</div>
              <div class="password-value">${data.password}</div>
            </div>
            <div class="pdf-preview">
              <div class="preview-icon">📄</div>
              <p>PDF berhasil dibuka dan disimpan di local storage browser Anda.</p>
              ${blobUrl ? '<iframe id="unlockedPdfFrame" class="pdf-frame" title="Pratinjau PDF" frameborder="0"></iframe>' : ''}
              ${blobUrl ? `<div class="preview-actions"><button class="btn btn--outline" id="openPdfNewTab">Buka di Tab Baru</button></div>` : ''}
              ${storageMessage}
            </div>
          </div>
        `;

        if (blobUrl) {
          const frame = document.getElementById('unlockedPdfFrame');
          if (frame) {
            frame.src = blobUrl;
          }
          const openBtn = document.getElementById('openPdfNewTab');
          if (openBtn) {
            openBtn.addEventListener('click', () => {
              window.open(blobUrl, '_blank', 'noopener');
            });
          }
        }
      } else if (data.status === 'failed' || data.status === 'error') {
        statusMessageEl.textContent = data.status === 'error' ? (data.error_message || 'Terjadi kesalahan.') : 'Selesai tanpa menemukan password.';
        resultsContent.innerHTML = `
          <div class="failure-result">
            <div class="failure-icon">😞</div>
            <h3>${data.status === 'error' ? 'Terjadi Kesalahan' : 'Password Tidak Ditemukan'}</h3>
            <p>${data.status === 'error' ? (data.error_message || '') : 'Maaf, password tidak ditemukan dalam rentang yang dipilih.'}</p>
          </div>
        `;
      } else if (data.status === 'stopped') {
        statusMessageEl.textContent = 'Proses dihentikan.';
        resultsContent.innerHTML = `
          <div class="failure-result">
            <div class="failure-icon">⛔</div>
            <h3>Proses Dihentikan</h3>
            <p>Proses brute force dihentikan oleh pengguna.</p>
          </div>
        `;
      }
    } catch (e) {
      // Network issues – keep trying a few times or show message
      statusMessageEl.textContent = 'Koneksi ke server terputus. Mencoba lagi...';
    }
  }

  // Reset flow
  resetBtn.addEventListener('click', () => {
    resetAll();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  // Initial
  resetAll();
})();
