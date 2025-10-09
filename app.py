import os
import queue
import threading
import time
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF

# Import your existing password cracker
from core.password_cracker import PasswordCracker

# --- Flask App Setup ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['UNLOCKED_FOLDER'] = 'unlocked'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['UNLOCKED_FOLDER'], exist_ok=True)

# --- Job State Management ---
# This dictionary will hold the state of the cracking job.
# In a real multi-user app, this would be a database or a more robust solution.
JOB_STATE = {}

# Threading and Queue for communication
progress_queue = queue.Queue()
stop_event = threading.Event()
pause_event = threading.Event() # Note: Pause/Resume is not implemented in this UI for simplicity

# Instantiate your cracker
password_cracker = PasswordCracker(progress_queue, stop_event, pause_event)

def reset_job_state():
    """Resets the global job state."""
    global JOB_STATE
    JOB_STATE = {
        "status": "idle", # idle, running, found, failed, stopped
        "filename": None,
        "password": None,
        "progress": 0,
        "total": 0,
        "rate": 0,
        "eta": "N/A",
        "elapsed": "0s",
        "current_attempt": "..."
    }
reset_job_state()


def cracking_monitor():
    """
    A monitor that runs in a background thread.
    It reads from the progress_queue and updates the global JOB_STATE.
    """
    global JOB_STATE
    
    while JOB_STATE.get("status") == "running":
        try:
            msg_type, data, *extra = progress_queue.get(timeout=1)

            if msg_type == "progress":
                JOB_STATE["progress"] += data
            elif msg_type == "current_password":
                JOB_STATE["current_attempt"] = data
            elif msg_type == "found":
                JOB_STATE["status"] = "found"
                JOB_STATE["password"] = data
                break
            elif msg_type == "completed":
                JOB_STATE["status"] = "failed"
                break
            elif msg_type == "error":
                JOB_STATE["status"] = "error"
                JOB_STATE["error_message"] = data
                break

        except queue.Empty:
            # Continue loop if queue is empty
            if stop_event.is_set():
                JOB_STATE["status"] = "stopped"
                break
            continue

    # Final cleanup
    if not stop_event.is_set() and JOB_STATE["status"] not in ["found", "failed", "error"]:
         JOB_STATE["status"] = "failed"


# --- Flask Routes ---
@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/crack', methods=['POST'])
def start_cracking():
    """Handle file upload and start the cracking process."""
    global JOB_STATE
    
    if JOB_STATE["status"] == "running":
        return jsonify({"error": "A job is already in progress."}), 400

    if 'pdf' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['pdf']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Get options from the form
    digit_mode = request.form.get('digit_mode', '6')
    thread_mode = request.form.get('thread_mode', 'multi')

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Check if PDF is encrypted
        try:
            doc = fitz.open(filepath)
            if not doc.is_encrypted:
                doc.close()
                return jsonify({
                    "error": "File is not encrypted. No password needed."
                }), 400
            doc.close()
        except Exception as e:
            return jsonify({"error": f"Invalid PDF file: {e}"}), 400
            
        # Reset events and state
        stop_event.clear()
        reset_job_state()
        JOB_STATE.update({
            "status": "running",
            "filename": filename,
            "total": 1_000_000 if digit_mode == '6' else 100_000_000,
            "start_time": time.time()
        })

        # Start the correct cracking method in a background thread
        target_func = None
        if digit_mode == '6' and thread_mode == 'multi':
            target_func = password_cracker.crack_6_digit_multithread
        elif digit_mode == '8' and thread_mode == 'multi':
            target_func = password_cracker.crack_8_digit_multithread
        # Note: Single-thread modes are not recommended for web UIs as they are blocking.
        # This implementation focuses on the superior multi-threaded approach.
        else:
             return jsonify({"error": "This web UI only supports the multi-threaded method."}), 400

        # Start cracker and monitor in background threads
        cracker_thread = threading.Thread(target=target_func, args=(filepath,), daemon=True)
        monitor_thread = threading.Thread(target=cracking_monitor, daemon=True)
        
        cracker_thread.start()
        monitor_thread.start()

        return jsonify({"message": "Cracking process started."})

    return jsonify({"error": "An unknown error occurred."}), 500

@app.route('/status')
def get_status():
    """Provide real-time status updates to the frontend."""
    if JOB_STATE["status"] == "running":
        elapsed_seconds = time.time() - JOB_STATE.get("start_time", 0)
        
        if elapsed_seconds > 0 and JOB_STATE["progress"] > 0:
            rate = JOB_STATE["progress"] / elapsed_seconds
            JOB_STATE["rate"] = f"{rate:.0f}"
            remaining = JOB_STATE["total"] - JOB_STATE["progress"]
            if rate > 0:
                eta_seconds = remaining / rate
                JOB_STATE["eta"] = time.strftime("%H:%M:%S", time.gmtime(eta_seconds))
            else:
                JOB_STATE["eta"] = "N/A"
        
        JOB_STATE["elapsed"] = f"{elapsed_seconds:.1f}s"

    return jsonify(JOB_STATE)

@app.route('/stop', methods=['POST'])
def stop_cracking():
    """Stop the currently running process."""
    if JOB_STATE["status"] == "running":
        stop_event.set()
        return jsonify({"message": "Stop signal sent."})
    return jsonify({"error": "No process is running."}), 400


@app.route('/unlocked/<filename>/<password>')
def serve_unlocked_pdf(filename, password):
    """Serve the unlocked PDF file for viewing."""
    original_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    unlocked_path = os.path.join(app.config['UNLOCKED_FOLDER'], f"unlocked_{filename}")
    
    try:
        doc = fitz.open(original_path)
        if doc.authenticate(password):
            doc.save(unlocked_path)
            return send_from_directory(app.config['UNLOCKED_FOLDER'], f"unlocked_{filename}", as_attachment=False)
        else:
            return "Invalid password provided.", 403
    except Exception as e:
        return f"Could not open or save the PDF: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)