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

    let statusInterval;

    // Handle form submission
    crackForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
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
        resetControls();
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
                    const viewUrl = `/unlocked/${data.filename}/${data.password}`;
                    resultArea.innerHTML = `
                        <h2>Password Found! 🎉</h2>
                        <p><strong>Password:</strong> <code>${data.password}</code></p>
                        <a href="${viewUrl}" target="_blank" class="button">View Unlocked PDF</a>
                    `;
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
    }

    function resetControls() {
        startButton.disabled = false;
        stopButton.style.display = 'none';
        if (statusInterval) clearInterval(statusInterval);
    }
});