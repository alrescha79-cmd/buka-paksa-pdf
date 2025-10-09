(function() {
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
  const alertModal = document.getElementById('alertModal');
  const alertModalTitle = document.getElementById('alertModalTitle');
  const alertModalMessage = document.getElementById('alertModalMessage');
  const alertModalIcon = document.getElementById('alertModalIcon');
  const alertModalClose = document.getElementById('alertModalClose');
  const alertModalOverlay = alertModal ? alertModal.querySelector('[data-alert-close]') : null;

  const STORAGE_PREFIX = 'pdf-viewer:';

  let selectedFile = null;
  let selectedMode = null;
  let statusInterval = null;
  let lastProgress = 0;
  let unlockedBlobUrl = null;
  let alertDismissHandler = null;

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

  function parseEtaToSeconds(rawEta) {
    if (!rawEta || typeof rawEta !== 'string') return null;
    const parts = rawEta.split(':').map(Number);
    if (parts.some((part) => Number.isNaN(part))) return null;
    while (parts.length < 3) parts.unshift(0);
    const [hours, minutes, seconds] = parts.slice(-3);
    return (hours * 3600) + (minutes * 60) + seconds;
  }

  function formatSecondsToClock(totalSeconds) {
    const seconds = Math.max(0, Math.round(totalSeconds));
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return [hours, minutes, secs].map((unit) => unit.toString().padStart(2, '0')).join(':');
  }

  function clampEtaDisplay(rawEta, total) {
    let limitSeconds;
    if (typeof total === 'number' && total >= 100_000_000) {
      limitSeconds = 300;
    } else if (typeof total === 'number' && total > 0) {
      limitSeconds = 60;
    } else {
      limitSeconds = selectedMode === '8' ? 300 : 60;
    }

    const seconds = parseEtaToSeconds(rawEta);
    if (seconds == null) {
      return rawEta || (limitSeconds === 300 ? '≤ 5 menit' : '≤ 1 menit');
    }
    if (seconds > limitSeconds) {
      return limitSeconds === 300 ? '≤ 5 menit' : '≤ 1 menit';
    }
    return formatSecondsToClock(seconds);
  }

  const ALERT_ICONS = {
    info: 'ℹ️',
    success: '✅',
    warning: '⚠️',
    error: '⛔'
  };

  function setAlertVariant(variant) {
    if (!alertModal) return;
    const activeVariant = ALERT_ICONS[variant] ? variant : 'info';
    alertModal.setAttribute('data-variant', activeVariant);
    if (alertModalIcon) {
      alertModalIcon.textContent = ALERT_ICONS[activeVariant];
    }
  }

  function closeAlertModal(reason) {
    if (!alertModal) return;
    alertModal.classList.add('hidden');
    if (alertDismissHandler) {
      const handler = alertDismissHandler;
      alertDismissHandler = null;
      handler(reason || null);
    }
  }

  function showAlertModal(message, options = {}) {
    if (!alertModal) {
      window.alert(message);
      if (typeof options.onClose === 'function') {
        options.onClose();
      }
      return;
    }

    const {
      title = 'Informasi',
      variant = 'info',
      dismissText = 'Tutup',
      onClose = null
    } = options;

    setAlertVariant(variant);

    alertDismissHandler = typeof onClose === 'function' ? onClose : null;
    alertModal.classList.remove('hidden');

    if (alertModalTitle) {
      alertModalTitle.textContent = title;
    }
    if (alertModalMessage) {
      alertModalMessage.textContent = message;
    }
    if (alertModalClose) {
      alertModalClose.textContent = dismissText;
      try {
        alertModalClose.focus({ preventScroll: true });
      } catch (err) {
        alertModalClose.focus();
      }
    }
  }

  if (alertModalClose) {
    alertModalClose.addEventListener('click', () => closeAlertModal('button'));
  }

  if (alertModalOverlay) {
    alertModalOverlay.addEventListener('click', () => closeAlertModal('overlay'));
  }

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && alertModal && !alertModal.classList.contains('hidden')) {
      event.preventDefault();
      closeAlertModal('escape');
    }
  });

  function resetControls() {
    startBtn.disabled = false;
    cancelBtn.classList.add('hidden');
    cancelBtn.disabled = false;
    if (statusInterval) {
      clearInterval(statusInterval);
      statusInterval = null;
    }
  }

  function show(el) { el.classList.remove('hidden'); }
  function hide(el) { el.classList.add('hidden'); }

  function resetAll() {
    if (statusInterval) {
      clearInterval(statusInterval);
      statusInterval = null;
    }

    selectedFile = null;
    selectedMode = null;
    lastProgress = 0;

    fileInput.value = '';
    hide(fileInfo);
    fileNameEl.textContent = '';
    fileSizeEl.textContent = '';

    revokeUnlockedBlob();

    show(uploadArea.closest('section'));
    hide(modeSection);
    hide(controlSection);
    hide(progressSection);
    hide(resultsSection);

    startBtn.disabled = true;
    hide(cancelBtn);

    progressFill.style.width = '0%';
    progressText.textContent = '0%';
    currentPasswordEl.textContent = '-';
    elapsedTimeEl.textContent = '00:00:00';
    attemptCountEl.textContent = '0';
    estimatedTimeEl.textContent = '-';
    statusMessageEl.textContent = 'Menunggu file diunggah...';

    modeCards.forEach(c => c.classList.remove('selected'));
  }

  function openModal() { confirmModal.classList.remove('hidden'); }
  function closeModal() { confirmModal.classList.add('hidden'); }

  selectFileBtn.addEventListener('click', () => fileInput.click());
  changeFileBtn.addEventListener('click', () => fileInput.click());

  uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
  });

  uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
  });

  uploadArea.addEventListener('click', (e) => {
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
      showAlertModal('Hanya file PDF yang diizinkan.', {
        title: 'File tidak valid',
        variant: 'error'
      });
      return;
    }
    selectedFile = file;
    fileNameEl.textContent = file.name;
    fileSizeEl.textContent = bytesToSize(file.size);
    show(fileInfo);
    show(modeSection);
    cacheUploadedPdf(file);
    modeSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

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
      hide(resultsSection);
      show(progressSection);
      statusMessageEl.textContent = 'Mengunggah dan memulai proses...';
      startBtn.disabled = true;
      cancelBtn.classList.remove('hidden');
      progressSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

      const formData = new FormData();
      formData.append('pdf', selectedFile);
      formData.append('digit_mode', selectedMode);
      formData.append('thread_mode', 'multi');

      const res = await fetch('/crack', { method: 'POST', body: formData });
      const json = await res.json();
      if (!res.ok) {
        showAlertModal(json.error || 'Terjadi kesalahan saat memulai proses.', {
          title: 'Gagal memulai proses',
          variant: 'error'
        });
        startBtn.disabled = false;
        cancelBtn.classList.add('hidden');
        return;
      }

      statusInterval = setInterval(updateStatus, 600);
    } catch (err) {
      showAlertModal('Gagal terhubung ke server.', {
        title: 'Koneksi bermasalah',
        variant: 'error'
      });
      startBtn.disabled = false;
      cancelBtn.classList.add('hidden');
    }
  }

  cancelBtn.addEventListener('click', async () => {
    cancelBtn.disabled = true;
    try {
      await fetch('/stop', { method: 'POST' });
    } catch {}
    statusMessageEl.textContent = 'Proses dibatalkan oleh pengguna.';
      resetControls();
      show(resultsSection);
    resultsContent.innerHTML = `
      <div class="failure-result">
        <div class="failure-icon">⛔</div>
        <h3>Proses Dihentikan</h3>
        <p>Proses brute force dihentikan oleh pengguna.</p>
      </div>
    `;
  });

  async function updateStatus() {
    try {
      const res = await fetch('/status');
      const data = await res.json();

      const total = data.total || (selectedMode === '6' ? 1_000_000 : 100_000_000);
      const progress = Math.min(data.progress || 0, total);
      const pct = total > 0 ? ((progress / total) * 100) : 0;
      progressFill.style.width = `${pct.toFixed(2)}%`;
      progressText.textContent = `${pct.toFixed(0)}%`;
      currentPasswordEl.textContent = data.current_attempt || '-';
      elapsedTimeEl.textContent = data.elapsed || '0s';
      attemptCountEl.textContent = String(progress);
      estimatedTimeEl.textContent = clampEtaDisplay(data.eta, data.total);

      if (data.status === 'running') {
        statusMessageEl.textContent = `Berjalan • ${data.rate || 0} percobaan/detik`;
        lastProgress = progress;
        return;
      }

      resetControls();
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
              ${blobUrl ? `<div class="preview-actions"><button class="btn btn--outline" id="openPdfNewTab">Buka PDF di Tab Baru</button></div>` : ''}
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
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } else if (data.status === 'failed' || data.status === 'error') {
        statusMessageEl.textContent = data.status === 'error' ? (data.error_message || 'Terjadi kesalahan.') : 'Selesai tanpa menemukan password.';
        resultsContent.innerHTML = `
          <div class="failure-result">
            <div class="failure-icon">😞</div>
            <h3>${data.status === 'error' ? 'Terjadi Kesalahan' : 'Password Tidak Ditemukan'}</h3>
            <p>${data.status === 'error' ? (data.error_message || '') : 'Maaf, password tidak ditemukan dalam rentang yang dipilih.'}</p>
          </div>
        `;
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } else if (data.status === 'stopped') {
        statusMessageEl.textContent = 'Proses dihentikan.';
        resultsContent.innerHTML = `
          <div class="failure-result">
            <div class="failure-icon">⛔</div>
            <h3>Proses Dihentikan</h3>
            <p>Proses brute force dihentikan oleh pengguna.</p>
          </div>
        `;
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    } catch (e) {
      statusMessageEl.textContent = 'Koneksi ke server terputus. Mencoba lagi...';
    }
  }

  resetBtn.addEventListener('click', () => {
    resetAll();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  resetAll();
})();
