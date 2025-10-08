import tkinter as tk
from tkinter import filedialog, messagebox
import fitz
from PIL import Image, ImageTk
import io
import time


def coba_buka(path_pdf):
    """
    Mencoba semua kombinasi password 6 digit angka untuk membuka PDF.
    """
    label_gambar.config(image='')
    root.update()

    try:
        doc = fitz.open(path_pdf)
    except Exception as e:
        messagebox.showerror("Error", f"Tidak bisa membuka file: {e}")
        return

    if not doc.is_encrypted:
        messagebox.showinfo("Info", "PDF ini tidak terenkripsi.")
        doc.close()
        tampilkan_halaman(doc, 0)
        return

    waktu_mulai = time.time()
    password_ditemukan = None

    for i in range(1000000):
        password = f"{i:06d}"
        
        status_label.config(text=f"Mencoba password: {password}")
        if i % 100 == 0:
             root.update_idletasks()

        if doc.authenticate(password) > 0:
            password_ditemukan = password
            break

    waktu_selesai = time.time()
    durasi = waktu_selesai - waktu_mulai

    if password_ditemukan:
        status_label.config(text=f"Sukses! Password: {password_ditemukan} (Ditemukan dalam {durasi:.2f} detik)")
        messagebox.showinfo("Sukses", f"Password ditemukan: {password_ditemukan}")
        tampilkan_halaman(doc, 0)
    else:
        status_label.config(text=f"Gagal setelah mencoba semua kemungkinan ({durasi:.2f} detik).")
        messagebox.showwarning("Gagal", "Password tidak ditemukan. Mungkin bukan 6 digit angka.")

    doc.close()

def tampilkan_halaman(doc, nomor_halaman):
    """Fungsi terpisah untuk merender dan menampilkan halaman PDF."""
    try:
        page = doc.load_page(nomor_halaman)
        pix = page.get_pixmap()
        img_data = pix.tobytes("ppm")
        img = Image.open(io.BytesIO(img_data))
        photo = ImageTk.PhotoImage(img)

        label_gambar.config(image=photo)
        label_gambar.image = photo
    except Exception as e:
        messagebox.showerror("Error", f"Gagal menampilkan halaman: {e}")

def buka_file_dialog():
    """Membuka dialog untuk memilih file PDF."""
    filepath = filedialog.askopenfilename(
        title="Pilih File PDF",
        filetypes=[("PDF Files", "*.pdf")]
    )
    if filepath:
        coba_buka(filepath)

root = tk.Tk()
root.title("Buka Paksa PDF (6-Digit Angka)")
root.geometry("400x350")

tombol_buka = tk.Button(root, text="Pilih PDF dan Mulai Proses", command=buka_file_dialog)
tombol_buka.pack(pady=10)

status_label = tk.Label(root, text="Status: Menunggu file PDF...", font=("Arial", 10))
status_label.pack(pady=5)

label_gambar = tk.Label(root)
label_gambar.pack(padx=10, pady=10)

root.mainloop()