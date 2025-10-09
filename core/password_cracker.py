"""
PDF Password Cracker Core Functions
Fungsi-fungsi utama untuk melakukan brute force password PDF
"""
import fitz
import time
import threading
import multiprocessing
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed


def _open_document(pdf_source):
    """Open a PDF document from various source types."""
    if isinstance(pdf_source, bytes):
        return fitz.open(stream=pdf_source, filetype="pdf")
    if isinstance(pdf_source, bytearray):
        return fitz.open(stream=bytes(pdf_source), filetype="pdf")
    if isinstance(pdf_source, memoryview):
        return fitz.open(stream=pdf_source.tobytes(), filetype="pdf")
    if hasattr(pdf_source, "read"):
        data = pdf_source.read()
        return fitz.open(stream=data, filetype="pdf")
    return fitz.open(pdf_source)

def test_password_range(pdf_source, start_range, end_range, digits, progress_q, stop_evt, pause_evt):
    """
    Fungsi untuk mentest range password dalam thread terpisah dengan dukungan pause
    """
    try:
        doc = _open_document(pdf_source)
        if not doc.is_encrypted:
            return None
        
        for i in range(start_range, end_range):
            # Cek jika proses dihentikan
            if stop_evt.is_set():
                doc.close()
                return None
            
            # Cek jika proses di-pause
            if pause_evt.is_set():
                progress_q.put(("paused", i))
                # Tunggu sampai pause di-clear atau stop
                while pause_evt.is_set() and not stop_evt.is_set():
                    time.sleep(0.1)
                
                if stop_evt.is_set():
                    doc.close()
                    return None
                
                progress_q.put(("resumed", i))
                
            password = f"{i:0{digits}d}"
            
            if doc.authenticate(password) > 0:
                doc.close()
                progress_q.put(("found", password, i))
                return password
            
            # Update progress setiap 100 iterasi dengan format yang sama seperti single thread
            if i % 100 == 0:
                progress_q.put(("progress", i - start_range))
                # Kirim juga informasi password saat ini untuk konsistensi dengan single thread
                progress_q.put(("single_progress", {
                    "tested": i,
                    "total": end_range - start_range,
                    "current_password": password
                }))
                
            # Update password yang sedang dicoba setiap 50 iterasi (sama seperti single thread)
            if i % 50 == 0:
                progress_q.put(("current_password", password))
        
        doc.close()
        return None
    except Exception as e:
        progress_q.put(("error", str(e)))
        return None

def format_time(seconds):
    """Format waktu dalam format yang mudah dibaca"""
    if seconds < 60:
        return f"{seconds:.1f} detik"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} menit"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} jam"

class PasswordCracker:
    """Class utama untuk cracking password PDF"""
    
    def __init__(self, progress_queue, stop_event, pause_event):
        self.progress_queue = progress_queue
        self.stop_event = stop_event
        self.pause_event = pause_event
    
    def crack_6_digit_multithread(self, pdf_source):
        """Crack 6-digit password dengan multithread"""
        def run_brute_force():
            try:
                doc = _open_document(pdf_source)
            except Exception as e:
                self.progress_queue.put(("error", f"Tidak bisa membuka file: {str(e)}"))
                return

            if not doc.is_encrypted:
                doc.close()
                self.progress_queue.put(("error", "PDF tidak memiliki password"))
                return

            doc.close()

            # Setup multiprocessing
            cpu_count = multiprocessing.cpu_count()
            chunk_size = 1000000 // cpu_count
            
            with ThreadPoolExecutor(max_workers=cpu_count) as executor:
                futures = []
                for i in range(cpu_count):
                    start_range = i * chunk_size
                    end_range = (i + 1) * chunk_size if i < cpu_count - 1 else 1000000
                    future = executor.submit(test_password_range, pdf_source, start_range, end_range, 6, 
                                           self.progress_queue, self.stop_event, self.pause_event)
                    futures.append(future)
                
                # Check hasil
                for future in as_completed(futures):
                    if self.stop_event.is_set():
                        break
                    result = future.result()
                    if result:
                        # Password ditemukan, stop semua thread
                        self.stop_event.set()
                        break
                
                # Jika tidak ditemukan
                if not self.stop_event.is_set():
                    self.progress_queue.put(("completed", "Password tidak ditemukan"))
        
        # Reset events
        self.stop_event.clear()
        self.pause_event.clear()
        
        # Start background thread
        threading.Thread(target=run_brute_force, daemon=True).start()
        return True
    
    def crack_8_digit_multithread(self, pdf_source):
        """Crack 8-digit password dengan multithread"""
        def run_brute_force():
            try:
                doc = _open_document(pdf_source)
            except Exception as e:
                self.progress_queue.put(("error", f"Tidak bisa membuka file: {str(e)}"))
                return

            if not doc.is_encrypted:
                doc.close()
                self.progress_queue.put(("error", "PDF tidak memiliki password"))
                return

            doc.close()

            # Setup multiprocessing untuk 8 digit (100,000,000 kombinasi)
            cpu_count = multiprocessing.cpu_count()
            chunk_size = 100000000 // cpu_count
            
            with ThreadPoolExecutor(max_workers=cpu_count) as executor:
                futures = []
                for i in range(cpu_count):
                    start_range = i * chunk_size
                    end_range = (i + 1) * chunk_size if i < cpu_count - 1 else 100000000
                    future = executor.submit(test_password_range, pdf_source, start_range, end_range, 8, 
                                           self.progress_queue, self.stop_event, self.pause_event)
                    futures.append(future)
                
                # Check hasil
                for future in as_completed(futures):
                    if self.stop_event.is_set():
                        break
                    result = future.result()
                    if result:
                        # Password ditemukan, stop semua thread
                        self.stop_event.set()
                        break
                
                # Jika tidak ditemukan
                if not self.stop_event.is_set():
                    self.progress_queue.put(("completed", "Password tidak ditemukan"))
        
        # Reset events
        self.stop_event.clear()
        self.pause_event.clear()
        
        # Start background thread
        threading.Thread(target=run_brute_force, daemon=True).start()
        return True
    
    def crack_6_digit_single(self, pdf_source):
        """Crack 6-digit password dengan single thread"""
        try:
            doc = _open_document(pdf_source)
        except Exception as e:
            return {"error": f"Tidak bisa membuka file PDF: {str(e)}"}

        if not doc.is_encrypted:
            doc.close()
            return {"no_password": True}

        waktu_mulai = time.time()
        password_ditemukan = None
        total_combinations = 1000000

        for i in range(total_combinations):  # 0 sampai 999999 (6 digit)
            # Check if stop event is set
            if self.stop_event.is_set():
                doc.close()
                return {"error": "Proses dihentikan oleh user"}
            
            password = f"{i:06d}"
            
            if doc.authenticate(password) > 0:
                password_ditemukan = password
                break
            
            # Update progress setiap 500 iterasi untuk lebih responsif
            if i % 500 == 0:
                self.progress_queue.put(("single_progress", {
                    "tested": i,
                    "total": total_combinations,
                    "current_password": password
                }))
                
            # Update password yang sedang dicoba setiap 50 iterasi
            if i % 50 == 0:
                self.progress_queue.put(("current_password", password))

        waktu_selesai = time.time()
        durasi = waktu_selesai - waktu_mulai
        doc.close()

        if password_ditemukan:
            return {"success": True, "password": password_ditemukan, "duration": durasi}
        else:
            return {"success": False, "duration": durasi}
    
    def crack_8_digit_single(self, pdf_source):
        """Crack 8-digit password dengan single thread"""
        try:
            doc = _open_document(pdf_source)
        except Exception as e:
            return {"error": f"Tidak bisa membuka file: {str(e)}"}

        if not doc.is_encrypted:
            doc.close()
            return {"no_password": True}

        waktu_mulai = time.time()
        password_ditemukan = None
        total_combinations = 100000000

        for i in range(total_combinations):  # 0 sampai 99999999 (8 digit)
            # Check if stop event is set
            if self.stop_event.is_set():
                doc.close()
                return {"error": "Proses dihentikan oleh user"}
            
            password = f"{i:08d}"
            
            if doc.authenticate(password) > 0:
                password_ditemukan = password
                break
            
            # Update progress setiap 5000 iterasi untuk 8-digit
            if i % 5000 == 0:
                self.progress_queue.put(("single_progress", {
                    "tested": i,
                    "total": total_combinations,
                    "current_password": password
                }))
                
            # Update password yang sedang dicoba setiap 1000 iterasi
            if i % 1000 == 0:
                self.progress_queue.put(("current_password", password))

        waktu_selesai = time.time()
        durasi = waktu_selesai - waktu_mulai
        doc.close()

        if password_ditemukan:
            return {"success": True, "password": password_ditemukan, "duration": durasi}
        else:
            return {"success": False, "duration": durasi}