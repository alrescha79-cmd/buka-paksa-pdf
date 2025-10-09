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

  // State
  let selectedFile = null;
  let selectedMode = null; // '6' or '8'
  let statusInterval = null;
  let lastProgress = 0;

  // Helpers
  function bytesToSize(bytes) {
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
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
        const viewUrl = `/unlocked/${encodeURIComponent(data.filename)}/${encodeURIComponent(data.password)}`;
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
              <p>PDF berhasil dibuka. Klik tombol di bawah untuk melihat.</p>
              <a class="btn btn--primary" href="${viewUrl}" target="_blank">Lihat PDF Terbuka</a>
            </div>
          </div>
        `;
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
