document.addEventListener('DOMContentLoaded', () => {
    const crackForm = document.getElementById('crack-form');
    const startButton = document.getElementById('start-button');
    const stopButton = document.getElementById('stop-button');

    const uploadSection = document.getElementById('upload-section');
    const progressSection = document.getElementById('progress-section');
    const resultSection = document.getElementById('result-section');

    const progressBarFill = document.getElementById('progress-bar-fill');
    const statusText = document.getElementById('status-text');
    const speedText = document.getElementById('speed-text');
    const etaText = document.getElementById('eta-text');
    const elapsedText = document.getElementById('elapsed-text');
    const currentAttemptText = document.getElementById('current-attempt-text');
    const resultArea = document.getElementById('result-area');
    const alertModal = document.getElementById('alertModal');
    const alertModalTitle = document.getElementById('alertModalTitle');
    const alertModalMessage = document.getElementById('alertModalMessage');
    const alertModalIcon = document.getElementById('alertModalIcon');
    const alertModalClose = document.getElementById('alertModalClose');
    const alertModalOverlay = alertModal ? alertModal.querySelector('[data-alert-close]') : null;

    const STORAGE_PREFIX = 'pdf-viewer:';
    let statusInterval = null;
    let unlockedBlobUrl = null;
    let currentDigitMode = '6';
    let alertDismissHandler = null;

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

    function showAlert(message, options = {}) {
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

        alertDismissHandler = typeof onClose === 'function' ? onClose : null;
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

    function safeSetLocalStorage(key, value) {
        try {
            localStorage.setItem(key, value);
            return true;
        } catch (err) {
            console.warn('Failed to persist PDF to localStorage', err);
            return false;
        }
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
            return URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
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

    function determineEtaLimit(total) {
        if (typeof total === 'number' && total >= 100_000_000) return 300;
        if (typeof total === 'number' && total > 0) return 60;
        return currentDigitMode === '8' ? 300 : 60;
    }

    function clampEtaDisplay(rawEta, total) {
        const limitSeconds = determineEtaLimit(total);
        const seconds = parseEtaToSeconds(rawEta);
        if (seconds == null) {
            return rawEta || (limitSeconds === 300 ? '≤ 5 menit' : '≤ 1 menit');
        }
        if (seconds > limitSeconds) {
            return limitSeconds === 300 ? '≤ 5 menit' : '≤ 1 menit';
        }
        return formatSecondsToClock(seconds);
    }

    function resetUI() {
        progressSection.style.display = 'none';
        resultSection.style.display = 'none';
        uploadSection.style.display = 'block';
        progressBarFill.style.width = '0%';
        progressBarFill.textContent = '0%';
        statusText.textContent = 'Ready to start.';
        speedText.textContent = '0';
        etaText.textContent = '-';
        elapsedText.textContent = '0s';
        currentAttemptText.textContent = '...';
        resultArea.innerHTML = '';
        revokeUnlockedBlob();
    }

    function resetControls() {
        startButton.disabled = false;
        stopButton.style.display = 'none';
        if (statusInterval) {
            clearInterval(statusInterval);
            statusInterval = null;
        }
    }

    crackForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const formData = new FormData(crackForm);
        const submittedMode = formData.get('digit_mode');
        if (submittedMode) {
            currentDigitMode = submittedMode;
        }

        resetUI();
        uploadSection.style.display = 'none';
        progressSection.style.display = 'block';
        progressSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        startButton.disabled = true;
        stopButton.style.display = 'inline-block';

        try {
            const response = await fetch('/crack', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();

            if (!response.ok) {
                showError(result.error || 'An unknown error occurred.');
                return;
            }

            statusInterval = setInterval(updateStatus, 500);
        } catch (error) {
            showError('Failed to connect to the server.');
        }
    });

    stopButton.addEventListener('click', async () => {
        try {
            await fetch('/stop', { method: 'POST' });
        } catch (error) {
            console.warn('Failed to send stop command', error);
        }
        statusText.textContent = 'Process stopped by user.';
        resetControls();
    });

    async function updateStatus() {
        try {
            const response = await fetch('/status');
            const data = await response.json();

            if (data.status === 'running') {
                const total = data.total || (currentDigitMode === '8' ? 100_000_000 : 1_000_000);
                const percentage = total ? ((data.progress / total) * 100) : 0;
                progressBarFill.style.width = `${percentage.toFixed(2)}%`;
                progressBarFill.textContent = `${percentage.toFixed(0)}%`;
                statusText.textContent = 'Cracking...';
                speedText.textContent = data.rate || '0';
                etaText.textContent = clampEtaDisplay(data.eta, data.total);
                elapsedText.textContent = data.elapsed || '0s';
                currentAttemptText.textContent = data.current_attempt || '...';
                return;
            }

            resetControls();
            progressSection.style.display = 'none';
            resultSection.style.display = 'block';
            etaText.textContent = '-';

            if (data.status === 'found') {
                let blobUrl = null;
                let storageMessage = '';

                if (data.unlocked_pdf_base64) {
                    const stored = storeUnlockedPdf(data.unlocked_pdf_base64, data.filename);
                    if (!stored) {
                        storageMessage = '<p class="text-warning">PDF tidak dapat disimpan di local storage (kemungkinan ruang penuh).</p>';
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
                    storageMessage += '<p class="text-warning">PDF belum tersedia di browser. Silakan coba lagi.</p>';
                } else {
                    unlockedBlobUrl = blobUrl;
                }

                resultArea.innerHTML = `
                    <h2>Password Found! 🎉</h2>
                    <p><strong>Password:</strong> <code>${data.password}</code></p>
                    <p>PDF disimpan ke local storage browser Anda. Pratinjau tersedia di bawah.</p>
                    ${blobUrl ? '<iframe id="unlockedPdfFrame" class="pdf-frame" title="PDF Preview" frameborder="0"></iframe>' : ''}
                    ${blobUrl ? '<p><button id="openPdfNewTab" class="button">Buka PDF di Tab Baru</button></p>' : ''}
                    ${storageMessage}
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

                resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else if (data.status === 'failed') {
                resultArea.innerHTML = `
                    <h2>Process Finished</h2>
                    <p>Sorry, the password was not found in the selected range.</p>
                `;
                resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else if (data.status === 'stopped') {
                 resultArea.innerHTML = `
                    <h2>Process Stopped</h2>
                    <p>The cracking process was stopped by the user.</p>
                `;
                resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        } catch (error) {
            showError('Lost connection to the server.');
        }
    }

    function showError(message) {
        showAlert(`Error: ${message}`, {
            title: 'Terjadi Kesalahan',
            variant: 'error'
        });
        resetUI();
        resetControls();
    }

    resetUI();
});