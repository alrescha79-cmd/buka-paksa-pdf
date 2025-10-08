"""
PDF Viewer Component
Komponen untuk menampilkan dan navigasi PDF
"""
import tkinter as tk
from tkinter import simpledialog
import fitz
from PIL import Image, ImageTk
import io

class PDFViewer:
    """Class untuk menangani tampilan dan navigasi PDF"""
    
    def __init__(self, canvas, content_frame, label_gambar, status_label):
        self.canvas = canvas
        self.content_frame = content_frame
        self.label_gambar = label_gambar
        self.status_label = status_label
        
        # PDF state variables
        self.current_zoom = 1.0
        self.current_pdf_doc = None
        self.current_page = 0
        self.total_pages = 0
        
        # UI elements (will be set by main app)
        self.page_info_label = None
        self.tombol_prev = None
        self.tombol_next = None
        self.tombol_goto = None
        self.tombol_zoom_in = None
        self.tombol_zoom_out = None
        self.tombol_zoom_reset = None
    
    def set_ui_elements(self, page_info_label, tombol_prev, tombol_next, tombol_goto, 
                       tombol_zoom_in, tombol_zoom_out, tombol_zoom_reset):
        """Set referensi ke elemen UI"""
        self.page_info_label = page_info_label
        self.tombol_prev = tombol_prev
        self.tombol_next = tombol_next
        self.tombol_goto = tombol_goto
        self.tombol_zoom_in = tombol_zoom_in
        self.tombol_zoom_out = tombol_zoom_out
        self.tombol_zoom_reset = tombol_zoom_reset
    
    def display_page(self, doc, page_number, zoom_level=None):
        """Fungsi untuk merender dan menampilkan halaman PDF dengan zoom yang dapat dikontrol."""
        # Update variabel global
        self.current_pdf_doc = doc
        self.current_page = page_number
        self.total_pages = len(doc)
        
        try:
            page = doc.load_page(page_number)
            
            # Gunakan zoom level yang diberikan atau yang ada
            if zoom_level is not None:
                self.current_zoom = zoom_level
            elif self.current_zoom <= 0:  # Initialize zoom jika belum di-set
                # Auto-fit ke window pada first load
                self.canvas.update_idletasks()
                available_width = max(self.canvas.winfo_width() - 40, 300)
                available_height = max(self.canvas.winfo_height() - 40, 300)
                
                page_rect = page.rect
                scale_x = available_width / page_rect.width
                scale_y = available_height / page_rect.height
                self.current_zoom = min(scale_x, scale_y, 2.0)  # Maksimal 2x untuk initial
                self.current_zoom = max(self.current_zoom, 0.3)  # Minimal 0.3x
            
            # Render dengan skala yang sesuai
            matrix = fitz.Matrix(self.current_zoom, self.current_zoom)
            pix = page.get_pixmap(matrix=matrix)
            img_data = pix.tobytes("ppm")
            img = Image.open(io.BytesIO(img_data))
            photo = ImageTk.PhotoImage(img)

            # Update label dengan gambar PDF
            self.label_gambar.config(image=photo, text="", bg="white")
            self.label_gambar.image = photo
            
            # Update scroll region
            self.content_frame.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # Update status dengan info halaman dan zoom controls
            page_info = f"PDF: Halaman {page_number + 1} dari {self.total_pages} | Zoom: {self.current_zoom:.1f}x | Gunakan tombol navigasi dan zoom"
            self.status_label.config(text=page_info)
            
            # Update page navigation info
            if self.page_info_label:
                self.page_info_label.config(text=f"Halaman {page_number + 1} / {self.total_pages}")
            
            # Enable/disable navigation buttons
            if self.tombol_prev:
                self.tombol_prev.config(state="normal" if page_number > 0 else "disabled")
            if self.tombol_next:
                self.tombol_next.config(state="normal" if page_number < self.total_pages - 1 else "disabled")
            if self.tombol_goto:
                self.tombol_goto.config(state="normal")
            
            # Enable zoom buttons
            if self.tombol_zoom_in:
                self.tombol_zoom_in.config(state="normal")
            if self.tombol_zoom_out:
                self.tombol_zoom_out.config(state="normal")
            if self.tombol_zoom_reset:
                self.tombol_zoom_reset.config(state="normal")
                
        except Exception as e:
            from ui.custom_dialog import show_custom_dialog
            show_custom_dialog(
                self.canvas.master,
                "Error",
                f"Gagal menampilkan halaman PDF:\n\n{str(e)}\n\nPastikan file PDF tidak corrupt dan dapat dibaca.",
                [("OK", True, "#4CAF50")]
            )
    
    def zoom_in(self):
        """Perbesar zoom PDF"""
        if self.current_pdf_doc and self.current_zoom < 5.0:  # Maksimal 5x zoom
            self.current_zoom += 0.25
            self.display_page(self.current_pdf_doc, self.current_page)

    def zoom_out(self):
        """Perkecil zoom PDF"""
        if self.current_pdf_doc and self.current_zoom > 0.25:  # Minimal 0.25x zoom
            self.current_zoom -= 0.25
            self.display_page(self.current_pdf_doc, self.current_page)

    def zoom_reset(self):
        """Reset zoom ke ukuran fit-to-window"""
        if self.current_pdf_doc:
            # Hitung zoom fit-to-window
            page = self.current_pdf_doc.load_page(self.current_page)
            self.canvas.update_idletasks()
            available_width = max(self.canvas.winfo_width() - 40, 300)
            available_height = max(self.canvas.winfo_height() - 40, 300)
            
            page_rect = page.rect
            scale_x = available_width / page_rect.width
            scale_y = available_height / page_rect.height
            self.current_zoom = min(scale_x, scale_y, 2.5)  # Maksimal 2.5x zoom
            self.current_zoom = max(self.current_zoom, 0.3)  # Minimal 0.3x zoom
            
            self.display_page(self.current_pdf_doc, self.current_page)

    def prev_page(self):
        """Pindah ke halaman sebelumnya"""
        if self.current_pdf_doc and self.current_page > 0:
            self.current_page -= 1
            self.display_page(self.current_pdf_doc, self.current_page)

    def next_page(self):
        """Pindah ke halaman berikutnya"""
        if self.current_pdf_doc and self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.display_page(self.current_pdf_doc, self.current_page)

    def goto_page(self):
        """Dialog untuk langsung ke halaman tertentu"""
        if not self.current_pdf_doc:
            return
        
        page_num = simpledialog.askinteger(
            "Pergi ke Halaman", 
            f"Masukkan nomor halaman (1-{self.total_pages}):",
            minvalue=1, 
            maxvalue=self.total_pages
        )
        
        if page_num:
            self.current_page = page_num - 1  # Convert to 0-based index
            self.display_page(self.current_pdf_doc, self.current_page)
    
    def goto_first_page(self):
        """Pergi ke halaman pertama"""
        if self.current_pdf_doc:
            self.current_page = 0
            self.display_page(self.current_pdf_doc, self.current_page)
    
    def goto_last_page(self):
        """Pergi ke halaman terakhir"""
        if self.current_pdf_doc:
            self.current_page = self.total_pages - 1
            self.display_page(self.current_pdf_doc, self.current_page)
    
    def handle_keypress(self, event):
        """Handle keyboard shortcuts untuk PDF viewer"""
        if not self.current_pdf_doc:
            return
        
        key = event.keysym.lower()
        
        # Navigation shortcuts
        if key in ['left', 'up'] or (event.char == 'p'):
            self.prev_page()
        elif key in ['right', 'down'] or (event.char == 'n'):
            self.next_page()
        elif key == 'home':
            self.goto_first_page()
        elif key == 'end':
            self.goto_last_page()
        
        # Zoom shortcuts
        elif event.char == '+' or key == 'equal':
            self.zoom_in()
        elif event.char == '-':
            self.zoom_out()
        elif event.char == '0' or key == 'f':
            self.zoom_reset()
        elif event.char == 'g':
            self.goto_page()