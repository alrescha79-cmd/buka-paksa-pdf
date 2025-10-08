"""
Progress Monitor
Komponen untuk memantau dan menampilkan progress cracking dengan animasi
"""
import time
import queue
from core.password_cracker import format_time

class ProgressMonitor:
    """Class untuk menangani monitoring progress cracking dengan animasi dan info real-time"""
    
    def __init__(self, progress_queue, status_label, root):
        self.progress_queue = progress_queue
        self.status_label = status_label
        self.root = root
        self.current_progress = {"tested": 0, "start_time": None, "total": 0, "paused_time": 0}
        self.password_found_result = None
        self.tombol_buka = None
        self.tombol_pause = None
        self.tombol_stop = None
        self.is_monitoring = False
        
        # Animation properties
        self.animation_frame = 0
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.current_password_attempt = ""
        self.last_update = time.time()
        self.update_counter = 0
    
    def set_ui_elements(self, tombol_buka, tombol_pause, tombol_stop):
        """Set referensi ke tombol UI"""
        self.tombol_buka = tombol_buka
        self.tombol_pause = tombol_pause  
        self.tombol_stop = tombol_stop
    
    def update_progress_display(self):
        """Update tampilan progress dengan animasi dan info real-time dalam Bahasa Indonesia"""
        # Update animation frame
        self.animation_frame = (self.animation_frame + 1) % len(self.spinner_chars)
        spinner = self.spinner_chars[self.animation_frame]
        
        try:
            # Process all messages in queue
            processed_messages = False
            while not self.progress_queue.empty():
                msg_type, data, *extra = self.progress_queue.get_nowait()
                processed_messages = True
                
                if msg_type == "progress":
                    # Handle both integer progress (single thread) and total progress update
                    if isinstance(data, int):
                        self.current_progress["tested"] += data
                    else:
                        # For direct progress updates
                        self.current_progress["tested"] = data
                        
                elif msg_type == "single_progress":
                    # Handle detailed progress (both single thread and multithread)
                    if isinstance(data, dict):
                        # For multithread, we get partial progress, so we accumulate
                        # For single thread, we get absolute progress
                        if "tested" in data:
                            # Update current password attempt
                            if "current_password" in data:
                                self.current_password_attempt = data["current_password"]
                        
                elif msg_type == "current_password":
                    # Update current password being tested
                    self.current_password_attempt = data
                    
                elif msg_type == "paused":
                    self.current_progress["pause_start"] = time.time()
                    self.status_label.config(text="⏸ Proses dijeda - Klik Lanjutkan untuk melanjutkan")
                    if self.tombol_pause:
                        self.tombol_pause.config(text="Lanjutkan", bg="#4CAF50")
                    
                elif msg_type == "resumed":
                    if "pause_start" in self.current_progress:
                        self.current_progress["paused_time"] += time.time() - self.current_progress["pause_start"]
                    self.status_label.config(text="▶️ Proses dilanjutkan...")
                    if self.tombol_pause:
                        self.tombol_pause.config(text="Jeda", bg="#ff9800")
                    
                elif msg_type == "found":
                    password = data
                    position = extra[0] if extra else 0
                    elapsed = time.time() - self.current_progress["start_time"] - self.current_progress["paused_time"]
                    self.status_label.config(text=f"🎉 Berhasil! Password ditemukan: {password}\nDitemukan dalam {format_time(elapsed)} pada percobaan ke-{position:,}")
                    # Simpan hasil untuk diproses di main thread
                    self.password_found_result = {
                        "password": password, 
                        "elapsed": elapsed, 
                        "path": self.current_progress.get("pdf_path")
                    }
                    return password
                    
                elif msg_type == "error":
                    self.status_label.config(text=f"❌ Terjadi kesalahan: {data}")
                    
                elif msg_type == "finished":
                    # Handle completion for single thread modes
                    elapsed = time.time() - self.current_progress["start_time"] - self.current_progress["paused_time"]
                    self.status_label.config(text=f"✅ Proses selesai! Password tidak ditemukan dalam waktu {format_time(elapsed)}")
                
                elif msg_type == "completed":
                    # Proses selesai tanpa menemukan password
                    elapsed = time.time() - self.current_progress["start_time"] - self.current_progress["paused_time"]
                    self.status_label.config(text=f"⚠️ Gagal! Semua kemungkinan sudah dicoba ({format_time(elapsed)})")
                    # Reset tombol
                    if self.tombol_buka:
                        self.tombol_buka.config(state="normal")
                    if self.tombol_pause:
                        self.tombol_pause.config(state="disabled", text="Jeda", bg="#ff9800")
                    if self.tombol_stop:
                        self.tombol_stop.config(state="disabled")
            
            # Selalu update tampilan animasi dan info progress (jika monitoring aktif)
            if self.is_monitoring and self.current_progress.get("start_time"):
                elapsed = time.time() - self.current_progress["start_time"] - self.current_progress["paused_time"]
                
                if self.current_progress["tested"] > 0:
                    rate = self.current_progress["tested"] / elapsed if elapsed > 0 else 0
                    remaining = self.current_progress["total"] - self.current_progress["tested"]
                    eta_seconds = remaining / rate if rate > 0 else 0
                    percentage = (self.current_progress["tested"] / self.current_progress["total"]) * 100
                    
                    # Progress bar
                    bar_width = 30
                    filled = int((percentage / 100) * bar_width)
                    bar = "█" * filled + "░" * (bar_width - filled)
                    
                    # Emoji status
                    if percentage < 25:
                        progress_emoji = "🔍"
                    elif percentage < 50:
                        progress_emoji = "⚡"
                    elif percentage < 75:
                        progress_emoji = "🚀"
                    else:
                        progress_emoji = "🎯"
                    
                    # Password yang sedang dicoba
                    current_pwd_display = self.current_password_attempt if self.current_password_attempt else "..."
                    
                    status_text = (
                        f"{spinner} {progress_emoji} Proses Membuka Password PDF {progress_emoji} {spinner}\n"
                        f"Progress: [{bar}] {percentage:.2f}%\n"
                        f"🔢 Jumlah percobaan: {self.current_progress['tested']:,} dari {self.current_progress['total']:,}\n"
                        f"⚡ Kecepatan: {rate:.0f} percobaan/detik\n"
                        f"⏱️ Waktu berjalan: {format_time(elapsed)}\n"
                        f"⏳ Estimasi sisa: {format_time(eta_seconds)}\n"
                        f"🔑 Password yang sedang dicoba: {current_pwd_display}"
                    )
                else:
                    # Awal proses atau progress sangat awal
                    status_text = (
                        f"{spinner} 🚀 Memulai proses brute force... 🚀 {spinner}\n"
                        f"⏱️ Waktu berjalan: {format_time(elapsed)}\n"
                        f"⚙️ Menyiapkan proses pencarian password...\n"
                        f"🔑 Password yang sedang dicoba: {self.current_password_attempt if self.current_password_attempt else 'Belum mulai'}"
                    )
                
                self.status_label.config(text=status_text)
            
            # Schedule next update only if still monitoring
            if self.is_monitoring:
                self.root.after(250, self.update_progress_display)  # Faster updates for better animation
            
        except queue.Empty:
            # Even if no queue messages, still update animation
            if self.is_monitoring:
                self.root.after(250, self.update_progress_display)
        
        return None
    
    def start_monitoring(self, current_progress):
        """Mulai monitoring progress"""
        self.current_progress = current_progress
        self.password_found_result = None
        self.is_monitoring = True
        self.root.after(500, self.update_progress_display)
    
    def check_result(self, pdf_viewer, success_callback):
        """Check untuk hasil password cracking"""
        if self.password_found_result:
            # Reset tombol
            if self.tombol_buka:
                self.tombol_buka.config(state="normal")
            if self.tombol_pause:
                self.tombol_pause.config(state="disabled", text="Pause", bg="#ff9800")
            if self.tombol_stop:
                self.tombol_stop.config(state="disabled")
            
            # Panggil callback dengan hasil
            success_callback(self.password_found_result, pdf_viewer)
            self.password_found_result = None
        else:
            # Check lagi setelah 1000ms
            self.root.after(1000, lambda: self.check_result(pdf_viewer, success_callback))
    
    def stop_monitoring(self):
        """Stop monitoring progress dan reset UI"""
        self.is_monitoring = False
        
        # Reset tombol
        if self.tombol_buka:
            self.tombol_buka.config(state="normal")
        if self.tombol_pause:
            self.tombol_pause.config(state="disabled", text="Pause", bg="#ff9800")
        if self.tombol_stop:
            self.tombol_stop.config(state="disabled")
        
        # Reset progress
        self.password_found_result = None