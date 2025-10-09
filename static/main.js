document.addEventListener('DOMContentLoaded', function() {
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

    const STORAGE_PREFIX = 'pdf-viewer:';
    let statusInterval;
    let unlockedBlobUrl = null;

    // Handle form submission
    crackForm.addEventListener('submit', async function(e) {
    function safeSetLocalStorage(key, value) {
        try {
            localStorage.setItem(key, value);
            return true;
        } catch (err) {
            console.warn('Failed to persist PDF to localStorage', err);
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

        
        const formData = new FormData(this);
        
        // Reset UI
        resetUI();
        uploadSection.style.display = 'none';
        progressSection.style.display = 'block';
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

            // Start polling for status updates
            statusInterval = setInterval(updateStatus, 500);

        } catch (error) {
            showError('Failed to connect to the server.');
        }
    });

    // Handle stop button click
    stopButton.addEventListener('click', async function() {
        clearInterval(statusInterval);
        await fetch('/stop', { method: 'POST' });
        statusText.textContent = 'Process stopped by user.';
    });

    // Function to poll the /status endpoint
    async function updateStatus() {
        try {
            const response = await fetch('/status');
            const data = await response.json();

            if (data.status === 'running') {
                const percentage = (data.progress / data.total * 100).toFixed(2);
                progressBarFill.style.width = percentage + '%';
                progressBarFill.textContent = percentage + '%';
                statusText.textContent = 'Cracking...';
                speedText.textContent = data.rate || '0';
                etaText.textContent = data.eta || 'N/A';
                elapsedText.textContent = data.elapsed || '0s';
                currentAttemptText.textContent = data.current_attempt || '...';
            } else {
                clearInterval(statusInterval);
                progressSection.style.display = 'none';
                resultSection.style.display = 'block';

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
                        ${blobUrl ? '<p><button id="openPdfNewTab" class="button">Buka di Tab Baru</button></p>' : ''}
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
                } else if (data.status === 'failed') {
                    resultArea.innerHTML = `
                        <h2>Process Finished</h2>
                        <p>Sorry, the password was not found in the selected range.</p>
                    `;
                } else if (data.status === 'stopped') {
                     resultArea.innerHTML = `
                        <h2>Process Stopped</h2>
                        <p>The cracking process was stopped by the user.</p>
                    `;
                }
                 resetControls();
            }
        } catch (error) {
            showError('Lost connection to the server.');
        }
    }

    function showError(message) {
        alert(`Error: ${message}`);
        resetUI();
        resetControls();
    }
    
    function resetUI() {
        progressSection.style.display = 'none';
        resultSection.style.display = 'none';
        uploadSection.style.display = 'block';
        progressBarFill.style.width = '0%';
        progressBarFill.textContent = '0%';
        resultArea.innerHTML = '';
        revokeUnlockedBlob();
    }

    function resetControls() {
        startButton.disabled = false;
        stopButton.style.display = 'none';
        if (statusInterval) clearInterval(statusInterval);
    }
});