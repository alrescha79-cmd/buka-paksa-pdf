import base64
import io
import queue
import threading
import time
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import fitz

from core.password_cracker import PasswordCracker

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

JOB_STATE = {}

progress_queue = queue.Queue()
stop_event = threading.Event()
pause_event = threading.Event()

password_cracker = PasswordCracker(progress_queue, stop_event, pause_event)

APP_CREATOR = "Anggun Caksono"

def reset_job_state():
    """Resets the global job state."""
    global JOB_STATE
    JOB_STATE = {
        "status": "idle",
        "filename": None,
        "password": None,
        "progress": 0,
        "total": 0,
        "rate": 0,
        "eta": "N/A",
        "elapsed": "0s",
        "current_attempt": "...",
        "pdf_bytes": None,
        "unlocked_pdf_base64": None,
        "unlocked_error": None,
        "start_time": None
    }
reset_job_state()


def prepare_unlocked_pdf(password):
    """Generate and cache a base64-encoded unlocked PDF."""
    pdf_bytes = JOB_STATE.get("pdf_bytes")
    filename = JOB_STATE.get("filename") or "uploaded.pdf"

    if not pdf_bytes:
        raise ValueError("No PDF data available to unlock.")

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Could not reopen PDF: {exc}") from exc

    try:
        if not doc.authenticate(password):
            raise ValueError("Unable to authenticate PDF with discovered password.")

        output = io.BytesIO()
        doc.save(output, encryption=fitz.PDF_ENCRYPT_NONE)
        doc.close()
        output.seek(0)
        encoded = base64.b64encode(output.read()).decode("ascii")
        JOB_STATE["unlocked_pdf_base64"] = encoded
        JOB_STATE["pdf_bytes"] = None
        return encoded
    except Exception as exc:
        doc.close()
        raise ValueError(f"Failed to prepare unlocked PDF for {filename}: {exc}") from exc


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
                try:
                    prepare_unlocked_pdf(data)
                except ValueError as exc:
                    JOB_STATE["status"] = "error"
                    JOB_STATE["error_message"] = str(exc)
                break
            elif msg_type == "completed":
                JOB_STATE["status"] = "failed"
                break
            elif msg_type == "error":
                JOB_STATE["status"] = "error"
                JOB_STATE["error_message"] = data
                break

        except queue.Empty:
            if stop_event.is_set():
                JOB_STATE["status"] = "stopped"
                break
            continue

    if not stop_event.is_set() and JOB_STATE["status"] not in ["found", "failed", "error"]:
        JOB_STATE["status"] = "failed"

    if JOB_STATE.get("status") in {"failed", "error", "stopped"}:
        JOB_STATE["pdf_bytes"] = None


@app.route('/')
def index():
    """Render the main page."""
    return render_template(
        'index.html',
        current_year=datetime.now().year,
        creator_name=APP_CREATOR
    )

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
    
    digit_mode = request.form.get('digit_mode', '6')
    thread_mode = request.form.get('thread_mode', 'multi')

    if file:
        filename = secure_filename(file.filename)
        file_bytes = file.read()

        if not file_bytes:
            return jsonify({"error": "Uploaded file is empty."}), 400

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            if not doc.is_encrypted:
                doc.close()
                return jsonify({
                    "error": "PDF tidak dienkripsi. Tidak perlu password."
                }), 400
            doc.close()
        except Exception as e:
            return jsonify({"error": f"Invalid PDF file: {e}"}), 400
            
        stop_event.clear()
        reset_job_state()
        JOB_STATE.update({
            "status": "running",
            "filename": filename,
            "total": 1_000_000 if digit_mode == '6' else 100_000_000,
            "start_time": time.time(),
            "pdf_bytes": file_bytes
        })

        target_func = None
        if digit_mode == '6' and thread_mode == 'multi':
            target_func = password_cracker.crack_6_digit_multithread
        elif digit_mode == '8' and thread_mode == 'multi':
            target_func = password_cracker.crack_8_digit_multithread
        else:
             return jsonify({"error": "This web UI only supports the multi-threaded method."}), 400

        cracker_thread = threading.Thread(target=target_func, args=(file_bytes,), daemon=True)
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

    public_state = {k: v for k, v in JOB_STATE.items() if k not in {"pdf_bytes"}}
    return jsonify(public_state)

@app.route('/stop', methods=['POST'])
def stop_cracking():
    """Stop the currently running process."""
    if JOB_STATE["status"] == "running":
        stop_event.set()
        JOB_STATE["pdf_bytes"] = None
        return jsonify({"message": "Stop signal sent."})
    return jsonify({"error": "No process is running."}), 400


@app.route('/unlocked/<filename>/<password>')
def serve_unlocked_pdf(filename, password):
    """Serve the unlocked PDF file for viewing."""
    if JOB_STATE.get("status") != "found":
        return "No unlocked PDF available.", 404

    if JOB_STATE.get("filename") != filename:
        return "Requested file does not match the active job.", 400

    if JOB_STATE.get("password") != password:
        return "Password mismatch for the requested PDF.", 403

    encoded = JOB_STATE.get("unlocked_pdf_base64")
    if not encoded:
        try:
            encoded = prepare_unlocked_pdf(password)
        except ValueError as exc:
            return str(exc), 500

    try:
        pdf_bytes = base64.b64decode(encoded)
    except Exception:
        return "Failed to decode unlocked PDF data.", 500

    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)
    download_name = f"unlocked_{filename}"
    return send_file(buffer, mimetype='application/pdf', download_name=download_name, as_attachment=False)

if __name__ == '__main__':
    app.run(debug=True)