"""
Main Application
Aplikasi utama PDF Password Cracker & Viewer
"""
import tkinter as tk
from tkinter import filedialog, ttk
import fitz
import threading
import multiprocessing
import queue
import time

# Import custom modules
from ui.custom_dialog import show_custom_dialog
from ui.pdf_viewer import PDFViewer
from ui.progress_monitor import ProgressMonitor
from core.password_cracker import PasswordCracker

class PDFCrackerApp:
    """Main application class"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.setup_variables()
        self.setup_ui()
        self.setup_components()
        self.setup_bindings()
    
    def setup_window(self):
        """Setup main window properties"""
        self.root.title("PDF Password Cracker & Viewer (Multithreaded + Navigation)")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)
    
    def setup_variables(self):
        """Setup global variables"""
        # Threading variables
        self.progress_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
    
    def setup_ui(self):
        """Setup user interface"""
        # Header frame
        header_frame = tk.Frame(self.root, bg="#2196F3", height=80)
        header_frame.pack(fill='x', pady=(0, 10))
        header_frame.pack_propagate(False)

        title_label = tk.Label(header_frame, text="PDF Password Cracker & Viewer", 
                              font=("Arial", 18, "bold"), bg="#2196F3", fg="white")
        title_label.pack(pady=15)

        # Control frame
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10)

        # Frame untuk tombol utama
        button_frame = tk.Frame(control_frame)
        button_frame.pack(pady=5)

        self.tombol_buka = tk.Button(button_frame, text="Pilih PDF dan Mulai", 
                                    command=self.buka_file_dialog, 
                                    bg="#4CAF50", fg="white", 
                                    font=("Arial", 12, "bold"), width=20, height=2)
        self.tombol_buka.pack(side=tk.LEFT, padx=5)

        self.tombol_pause = tk.Button(button_frame, text="Pause", 
                                     command=self.toggle_pause, 
                                     bg="#ff9800", fg="white", 
                                     font=("Arial", 12, "bold"), width=12, height=2, 
                                     state="disabled")
        self.tombol_pause.pack(side=tk.LEFT, padx=5)

        self.tombol_stop = tk.Button(button_frame, text="Stop", 
                                    command=self.stop_process, 
                                    bg="#f44336", fg="white", 
                                    font=("Arial", 12, "bold"), width=12, height=2, 
                                    state="disabled")
        self.tombol_stop.pack(side=tk.LEFT, padx=5)

        # Info frame
        info_frame = tk.Frame(control_frame)
        info_frame.pack(pady=5)

        # Frame untuk tombol zoom
        zoom_frame = tk.Frame(control_frame)
        zoom_frame.pack(pady=5)

        zoom_label = tk.Label(zoom_frame, text="Zoom PDF:", font=("Arial", 11, "bold"))
        zoom_label.pack(side=tk.LEFT, padx=5)

        self.tombol_zoom_out = tk.Button(zoom_frame, text="Zoom Out (-)", 
                                        command=self.zoom_out, 
                                        bg="#9E9E9E", fg="white", 
                                        font=("Arial", 10, "bold"), width=12, 
                                        state="disabled")
        self.tombol_zoom_out.pack(side=tk.LEFT, padx=2)

        self.tombol_zoom_reset = tk.Button(zoom_frame, text="Fit Window", 
                                          command=self.zoom_reset, 
                                          bg="#2196F3", fg="white", 
                                          font=("Arial", 10, "bold"), width=12, 
                                          state="disabled")
        self.tombol_zoom_reset.pack(side=tk.LEFT, padx=2)

        self.tombol_zoom_in = tk.Button(zoom_frame, text="Zoom In (+)", 
                                       command=self.zoom_in, 
                                       bg="#9E9E9E", fg="white", 
                                       font=("Arial", 10, "bold"), width=12, 
                                       state="disabled")
        self.tombol_zoom_in.pack(side=tk.LEFT, padx=2)

        # Frame untuk navigasi halaman
        nav_frame = tk.Frame(control_frame)
        nav_frame.pack(pady=5)

        nav_label = tk.Label(nav_frame, text="Navigasi Halaman:", font=("Arial", 11, "bold"))
        nav_label.pack(side=tk.LEFT, padx=5)

        self.tombol_prev = tk.Button(nav_frame, text="◀ Sebelumnya", 
                                    command=self.prev_page, 
                                    bg="#607D8B", fg="white", 
                                    font=("Arial", 10, "bold"), width=12, 
                                    state="disabled")
        self.tombol_prev.pack(side=tk.LEFT, padx=2)

        self.page_info_label = tk.Label(nav_frame, text="Halaman - / -", 
                                       font=("Arial", 10, "bold"), fg="#333")
        self.page_info_label.pack(side=tk.LEFT, padx=10)

        self.tombol_goto = tk.Button(nav_frame, text="Pergi ke...", 
                                    command=self.goto_page, 
                                    bg="#795548", fg="white", 
                                    font=("Arial", 10, "bold"), width=10, 
                                    state="disabled")
        self.tombol_goto.pack(side=tk.LEFT, padx=2)

        self.tombol_next = tk.Button(nav_frame, text="Berikutnya ▶", 
                                    command=self.next_page, 
                                    bg="#607D8B", fg="white", 
                                    font=("Arial", 10, "bold"), width=12, 
                                    state="disabled")
        self.tombol_next.pack(side=tk.LEFT, padx=2)

        cpu_info = tk.Label(info_frame, text=f"CPU Cores: {multiprocessing.cpu_count()}", 
                           font=("Arial", 11), fg="gray")
        cpu_info.pack()

        self.status_label = tk.Label(info_frame, text="Status: Menunggu file PDF...", 
                                    font=("Arial", 12), wraplength=800, fg="#333")
        self.status_label.pack(pady=5)

        # PDF display frame dengan scrollbar
        pdf_frame = tk.Frame(self.root, relief='sunken', borderwidth=1)
        pdf_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # Canvas untuk scrolling
        self.canvas = tk.Canvas(pdf_frame, bg='white')
        scrollbar_y = ttk.Scrollbar(pdf_frame, orient="vertical", command=self.canvas.yview)
        scrollbar_x = ttk.Scrollbar(pdf_frame, orient="horizontal", command=self.canvas.xview)

        self.canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Frame dalam canvas untuk content
        self.content_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        self.label_gambar = tk.Label(self.content_frame, 
                                    text="PDF akan ditampilkan di sini setelah password ditemukan", 
                                    font=("Arial", 14), fg="gray", bg="white", pady=50)
        self.label_gambar.pack(expand=True, fill='both')

        # Tambahkan info keyboard shortcuts
        shortcut_info = tk.Label(info_frame, 
                                text="Shortcuts: ←→ atau P/N (navigasi) | +/- (zoom) | 0/F (fit) | G (goto) | Home/End", 
                                font=("Arial", 9), fg="blue")
        shortcut_info.pack(pady=2)
    
    def setup_components(self):
        """Setup komponen aplikasi"""
        # PDF Viewer
        self.pdf_viewer = PDFViewer(self.canvas, self.content_frame, 
                                   self.label_gambar, self.status_label)
        self.pdf_viewer.set_ui_elements(
            self.page_info_label, self.tombol_prev, self.tombol_next, 
            self.tombol_goto, self.tombol_zoom_in, self.tombol_zoom_out, 
            self.tombol_zoom_reset
        )
        
        # Progress Monitor
        self.progress_monitor = ProgressMonitor(self.progress_queue, 
                                               self.status_label, self.root)
        self.progress_monitor.set_ui_elements(self.tombol_buka, self.tombol_pause, 
                                             self.tombol_stop)
        
        # Password Cracker
        self.password_cracker = PasswordCracker(self.progress_queue, 
                                               self.stop_event, self.pause_event)
    
    def setup_bindings(self):
        """Setup event bindings"""
        self.content_frame.bind("<Configure>", self.update_scroll_region)
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.focus_set()
    
    def update_scroll_region(self, event=None):
        """Update scroll region untuk canvas"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_key_press(self, event):
        """Handle keyboard shortcuts"""
        self.pdf_viewer.handle_keypress(event)
    
    # Delegated methods untuk PDF viewer
    def zoom_in(self):
        self.pdf_viewer.zoom_in()
    
    def zoom_out(self):
        self.pdf_viewer.zoom_out()
    
    def zoom_reset(self):
        self.pdf_viewer.zoom_reset()
    
    def prev_page(self):
        self.pdf_viewer.prev_page()
    
    def next_page(self):
        self.pdf_viewer.next_page()
    
    def goto_page(self):
        self.pdf_viewer.goto_page()
    
    def buka_file_dialog(self):
        """Membuka dialog untuk memilih file PDF."""
        filepath = filedialog.askopenfilename(
            title="Pilih File PDF",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if filepath:
            self.pilih_mode_dan_buka(filepath)
    
    def pilih_mode_dan_buka(self, path_pdf):
        """Meminta user memilih mode: 6 digit atau 8 digit password."""
        # Dialog pertama: pilih digit
        pilihan_digit = show_custom_dialog(
            self.root,
            "Pilih Mode Password",
            "Pilih mode password yang ingin dicoba:\n\n"
            "6 Digit: 000000 - 999999 (Relatif cepat)\n"
            "8 Digit: 00000000 - 99999999 (Lebih lama)\n\n"
            "Pilih mode yang sesuai dengan password PDF Anda:",
            [
                ("6 Digit", True, "#4CAF50"),
                ("8 Digit", False, "#FF9800"), 
                ("Batalkan", None, "#f44336")
            ]
        )
        
        if pilihan_digit is None:  # Cancel
            self.status_label.config(text="Proses dibatalkan oleh user.")
            return
        
        # Dialog kedua: pilih metode (single thread vs multithread)
        cpu_count = multiprocessing.cpu_count()
        metode = show_custom_dialog(
            self.root,
            "Pilih Metode Pemrosesan",
            f"Pilih metode pemrosesan untuk mencari password:\n\n"
            f"Multithreading: Menggunakan {cpu_count} CPU cores - CEPAT\n"
            f"Single Thread: Menggunakan 1 core - Lambat tapi stabil\n\n"
            f"Rekomendasi: Gunakan Multithreading untuk performa terbaik",
            [
                ("Multithreading", True, "#4CAF50"),
                ("Single Thread", False, "#FF9800"),
                ("Kembali", None, "#9E9E9E")
            ]
        )
        
        if metode is None:  # Cancel - kembali ke pilihan digit
            self.pilih_mode_dan_buka(path_pdf)
            return
        
        # Eksekusi berdasarkan pilihan
        if pilihan_digit is True:  # 6 digit
            if metode is True:  # Multithread
                self.start_6_digit_multithread(path_pdf)
            else:  # Single thread
                self.start_6_digit_single(path_pdf)
        else:  # 8 digit
            if metode is True:  # Multithread
                self.start_8_digit_multithread(path_pdf)
            else:  # Single thread
                self.start_8_digit_single(path_pdf)
    
    def start_6_digit_multithread(self, path_pdf):
        """Start 6-digit multithread cracking"""
        # Check if PDF is encrypted
        try:
            doc = fitz.open(path_pdf)
        except Exception as e:
            show_custom_dialog(
                self.root,
                "Error",
                f"Tidak bisa membuka file PDF: {str(e)}",
                [("OK", True, "#4CAF50")]
            )
            return
        
        if not doc.is_encrypted:
            show_custom_dialog(
                self.root,
                "Info",
                "PDF ini tidak memiliki password!\n\n"
                "File PDF dapat dibuka langsung tanpa memerlukan password.\n"
                "Anda dapat melihat isinya sekarang.",
                [("Lihat PDF", True, "#4CAF50")]
            )
            doc.close()
            self.pdf_viewer.display_page(fitz.open(path_pdf), 0)
            return
        
        doc.close()
        
        # Setup UI
        self.tombol_buka.config(state="disabled")
        self.tombol_pause.config(state="normal")
        self.tombol_stop.config(state="normal")
        
        # Start cracking
        current_progress = {
            "tested": 0,
            "start_time": time.time(),
            "total": 1000000,
            "paused_time": 0,
            "pdf_path": path_pdf,
            "error_msg": "Password tidak ditemukan. Mungkin bukan 6 digit angka."
        }
        
        self.progress_monitor.start_monitoring(current_progress)
        self.password_cracker.crack_6_digit_multithread(path_pdf)
        
        # Start checking for results
        self.progress_monitor.check_result(self.pdf_viewer, self.on_password_found)
    
    def start_6_digit_single(self, path_pdf):
        """Start 6-digit single thread cracking"""
        # Check if PDF is encrypted
        try:
            doc = fitz.open(path_pdf)
        except Exception as e:
            show_custom_dialog(
                self.root,
                "Error",
                f"Tidak bisa membuka file PDF: {str(e)}",
                [("OK", True, "#4CAF50")]
            )
            return
        
        if not doc.is_encrypted:
            show_custom_dialog(
                self.root,
                "Info",
                "PDF ini tidak memiliki password!\n\n"
                "File PDF dapat dibuka langsung tanpa memerlukan password.\n"
                "Anda dapat melihat isinya sekarang.",
                [("Lihat PDF", True, "#4CAF50")]
            )
            doc.close()
            self.pdf_viewer.display_page(fitz.open(path_pdf), 0)
            return
        
        doc.close()
        
        # Setup UI
        self.tombol_buka.config(state="disabled")
        self.tombol_pause.config(state="disabled")  # Single thread tidak support pause
        self.tombol_stop.config(state="normal")
        
        # Start progress monitoring for single thread
        current_progress = {
            "tested": 0,
            "start_time": time.time(),
            "total": 1000000,
            "paused_time": 0,
            "pdf_path": path_pdf,
            "error_msg": "Password tidak ditemukan. Mungkin bukan 6 digit angka."
        }
        
        self.progress_monitor.start_monitoring(current_progress)
        
        # Run single thread in background
        def run_single_crack():
            result = self.password_cracker.crack_6_digit_single(path_pdf)
            
            # Schedule UI update in main thread
            self.root.after(200, lambda: self.handle_single_result(result, path_pdf))
        
        threading.Thread(target=run_single_crack, daemon=True).start()
    
    def start_8_digit_multithread(self, path_pdf):
        """Start 8-digit multithread cracking"""
        # Check if PDF is encrypted
        try:
            doc = fitz.open(path_pdf)
        except Exception as e:
            show_custom_dialog(
                self.root,
                "Error",
                f"Tidak bisa membuka file PDF: {str(e)}",
                [("OK", True, "#4CAF50")]
            )
            return
        
        if not doc.is_encrypted:
            show_custom_dialog(
                self.root,
                "Info",
                "PDF ini tidak memiliki password!\n\n"
                "File PDF dapat dibuka langsung tanpa memerlukan password.\n"
                "Anda dapat melihat isinya sekarang.",
                [("Lihat PDF", True, "#4CAF50")]
            )
            doc.close()
            self.pdf_viewer.display_page(fitz.open(path_pdf), 0)
            return
        
        doc.close()
        
        # Peringatan untuk 8-digit
        konfirmasi = show_custom_dialog(
            self.root,
            "Peringatan - Mode 8 Digit",
            "Mode 8 digit akan membubutuhkan waktu yang lebih lama!\n\n"
            "100,000,000 kombinasi password akan dicoba\n"
            "Akan menggunakan multithreading untuk performa maksimal\n\n"
            "Apakah Anda yakin ingin melanjutkan?",
            [
                ("Lanjutkan", True, "#4CAF50"),
                ("Batalkan", False, "#f44336")
            ]
        )
        
        if not konfirmasi:
            self.status_label.config(text="Proses dibatalkan oleh user.")
            return
        
        # Setup UI
        self.tombol_buka.config(state="disabled")
        self.tombol_pause.config(state="normal")
        self.tombol_stop.config(state="normal")
        
        # Start cracking
        current_progress = {
            "tested": 0,
            "start_time": time.time(),
            "total": 100000000,
            "paused_time": 0,
            "pdf_path": path_pdf,
            "error_msg": "Password tidak ditemukan. Mungkin bukan 8 digit angka."
        }
        
        self.progress_monitor.start_monitoring(current_progress)
        self.password_cracker.crack_8_digit_multithread(path_pdf)
        
        # Start checking for results
        self.progress_monitor.check_result(self.pdf_viewer, self.on_password_found)
    
    def start_8_digit_single(self, path_pdf):
        """Start 8-digit single thread cracking"""
        # Check if PDF is encrypted
        try:
            doc = fitz.open(path_pdf)
        except Exception as e:
            show_custom_dialog(
                self.root,
                "Error",
                f"Tidak bisa membuka file PDF: {str(e)}",
                [("OK", True, "#4CAF50")]
            )
            return
        
        if not doc.is_encrypted:
            show_custom_dialog(
                self.root,
                "Info",
                "PDF ini tidak memiliki password!\n\n"
                "File PDF dapat dibuka langsung tanpa memerlukan password.\n"
                "Anda dapat melihat isinya sekarang.",
                [("Lihat PDF", True, "#4CAF50")]
            )
            doc.close()
            self.pdf_viewer.display_page(fitz.open(path_pdf), 0)
            return
        
        doc.close()
        
        # Peringatan untuk 8-digit single thread
        konfirmasi = show_custom_dialog(
            self.root,
            "PERINGATAN KERAS - 8 Digit Single Thread",
            "Mode 8 digit single-thread akan memakan waktu yang lebih lama!\n\n"
            "100,000,000 kombinasi password akan dicoba secara berurutan\n"
            "Tidak ada pause/resume support untuk mode ini\n\n"
            "Apakah Anda BENAR-BENAR yakin?",
            [
                ("Tetap Lanjutkan", True, "#f44336"),
                ("Batalkan", False, "#4CAF50")
            ]
        )
        
        if not konfirmasi:
            self.status_label.config(text="Proses dibatalkan oleh user (recommended choice).")
            return
        
        # Setup UI
        self.tombol_buka.config(state="disabled")
        self.tombol_pause.config(state="disabled")  # Single thread tidak support pause
        self.tombol_stop.config(state="normal")
        
        # Start progress monitoring for single thread
        current_progress = {
            "tested": 0,
            "start_time": time.time(),
            "total": 100000000,
            "paused_time": 0,
            "pdf_path": path_pdf,
            "error_msg": "Password tidak ditemukan. Mungkin bukan 8 digit angka."
        }
        
        self.progress_monitor.start_monitoring(current_progress)
        
        # Run single thread in background
        def run_single_crack():
            result = self.password_cracker.crack_8_digit_single(path_pdf)
            
            # Schedule UI update in main thread
            self.root.after(200, lambda: self.handle_single_result(result, path_pdf))
        
        threading.Thread(target=run_single_crack, daemon=True).start()
    
    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()  # Keep the clipboard content
    
    def handle_single_result(self, result, pdf_path):
        """Handle result dari single thread cracking"""
        # Stop progress monitoring
        self.progress_monitor.stop_monitoring()
        
        # Reset UI
        self.tombol_buka.config(state="normal")
        self.tombol_stop.config(state="disabled")
        self.tombol_pause.config(state="disabled")
        
        if "error" in result:
            show_custom_dialog(
                self.root,
                "Error",
                result["error"],
                [("OK", True, "#4CAF50")]
            )
        elif "no_password" in result:
            show_custom_dialog(
                self.root,
                "Info",
                "PDF ini tidak memiliki password!\n\n"
                "File PDF dapat dibuka langsung tanpa memerlukan password.\n"
                "Anda dapat melihat isinya sekarang.",
                [("Lihat PDF", True, "#4CAF50")]
            )
            self.pdf_viewer.display_page(fitz.open(pdf_path), 0)
        elif result.get("success"):
            password = result["password"]
            elapsed = result["duration"]
            
            choice = show_custom_dialog(
                self.root,
                "Password Ditemukan!",
                f"Password berhasil ditemukan!\n\n"
                f"Password: {password}\n"
                f"Waktu: {elapsed:.2f} detik\n\n"
                f"Pilih tindakan yang ingin dilakukan:",
                [
                    ("Lihat PDF", True, "#4CAF50"),
                    ("Salin Password", False, "#2196F3"),
                    ("Keduanya", None, "#9C27B0")
                ]
            )
            
            if choice is True:  # Lihat PDF
                self.open_pdf_with_password(pdf_path, password)
            elif choice is False:  # Salin Password
                self.copy_to_clipboard(password)
                show_custom_dialog(
                    self.root,
                    "Password Disalin!",
                    f"Password '{password}' telah disalin ke clipboard.\n\n"
                    f"Anda dapat paste di aplikasi lain dengan Ctrl+V",
                    [("OK", True, "#4CAF50")]
                )
            else:  # Keduanya
                self.copy_to_clipboard(password)
                self.open_pdf_with_password(pdf_path, password)
                show_custom_dialog(
                    self.root,
                    "Selesai!",
                    f"Password '{password}' telah disalin ke clipboard dan PDF dibuka.",
                    [("OK", True, "#4CAF50")]
                )
        else:
            # Tidak ditemukan
            elapsed = result.get("duration", 0)
            show_custom_dialog(
                self.root,
                "Password Tidak Ditemukan",
                f"Maaf, password tidak ditemukan setelah {elapsed:.2f} detik.\n\n"
                f"Kemungkinan:\n"
                f"• Password bukan numeric\n"
                f"• Password lebih dari range yang dicoba\n"
                f"• Password mengandung huruf atau karakter khusus",
                [("OK", True, "#FF9800")]
            )
    
    def open_pdf_with_password(self, pdf_path, password):
        """Buka PDF dengan password yang ditemukan"""
        try:
            doc = fitz.open(pdf_path)
            doc.authenticate(password)
            self.pdf_viewer.display_page(doc, 0)
        except Exception as e:
            show_custom_dialog(
                self.root,
                "Error",
                f"Gagal menampilkan PDF: {str(e)}",
                [("OK", True, "#4CAF50")]
            )
    
    def on_password_found(self, result, pdf_viewer):
        """Callback ketika password ditemukan dari multithread"""
        password = result["password"]
        elapsed = result["elapsed"]
        pdf_path = result["path"]
        
        choice = show_custom_dialog(
            self.root,
            "Password Ditemukan!",
            f"Password berhasil ditemukan!\n\n"
            f"Password: {password}\n"
            f"Waktu: {elapsed:.2f} detik\n\n"
            f"Pilih tindakan yang ingin dilakukan:",
            [
                ("Lihat PDF", True, "#4CAF50"),
                ("Salin Password", False, "#2196F3"),
                ("Keduanya", None, "#9C27B0")
            ]
        )
        
        if choice is True:  # Lihat PDF
            self.open_pdf_with_password(pdf_path, password)
        elif choice is False:  # Salin Password
            self.copy_to_clipboard(password)
            show_custom_dialog(
                self.root,
                "Password Disalin!",
                f"Password '{password}' telah disalin ke clipboard.\n\n"
                f"Anda dapat paste di aplikasi lain dengan Ctrl+V",
                [("OK", True, "#4CAF50")]
            )
        else:  # Keduanya
            self.copy_to_clipboard(password)
            self.open_pdf_with_password(pdf_path, password)
            show_custom_dialog(
                self.root,
                "Selesai!",
                f"Password '{password}' telah disalin ke clipboard dan PDF dibuka.",
                [("OK", True, "#4CAF50")]
            )
    
    def stop_process(self):
        """Menghentikan proses brute force yang sedang berjalan"""
        self.stop_event.set()
        self.pause_event.clear()
        self.progress_monitor.password_found_result = None
        self.status_label.config(text="Proses dihentikan oleh user.")
        self.tombol_stop.config(state="disabled")
        self.tombol_pause.config(state="disabled", text="Pause", bg="#ff9800")
        self.tombol_buka.config(state="normal")
    
    def toggle_pause(self):
        """Toggle pause/resume proses brute force"""
        if self.pause_event.is_set():
            # Resume
            self.pause_event.clear()
            self.tombol_pause.config(text="Pause", bg="#ff9800")
        else:
            # Pause dengan konfirmasi
            konfirmasi = show_custom_dialog(
                self.root,
                "Continue to iterate?",
                "Proses brute force sedang berjalan...\n\n"
                "Apakah Anda ingin melanjutkan iterasi?\n\n"
                "Lanjutkan: Proses tetap berjalan\n"
                "Jeda: Hentikan sementara untuk istirahat",
                [
                    ("Lanjutkan", True, "#4CAF50"),
                    ("Jeda Proses", False, "#FF9800")
                ]
            )
            
            if konfirmasi is False:  # Pause
                self.pause_event.set()
                self.tombol_pause.config(text="Resume", bg="#4CAF50")
    
    def run(self):
        """Run the application"""
        self.root.mainloop()

def main():
    """Main function"""
    app = PDFCrackerApp()
    app.run()

if __name__ == "__main__":
    main()