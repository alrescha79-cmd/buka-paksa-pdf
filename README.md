# PDF Viewer - Buka Paksa PDF

Aplikasi untuk membuka file PDF yang terproteksi password dengan metode brute force menggunakan kombinasi angka 6 atau 8 digit.

> [!IMPORTANT]  
> Aplikasi ini hanya untuk tujuan edukasi. Penggunaan untuk membuka file PDF yang dilindungi tanpa izin adalah ilegal.

> [!CAUTION]
> Pastikan Anda memiliki hak untuk membuka file PDF tersebut. Aplikasi ini hanya untuk file PDF yang Anda miliki atau memiliki izin untuk membuka.

> [!NOTE]  
> Pengembang tidak bertanggung jawab atas penggunaan aplikasi ini untuk tujuan ilegal.

## Fitur

- ✅ Brute force password 6 digit (000000-999999)
- ✅ Brute force password 8 digit (00000000-99999999)
- ✅ Preview halaman PDF setelah berhasil dibuka
- ✅ Interface GUI yang user-friendly
- ✅ Real-time status update saat proses berlangsung
- ✅ Peringatan untuk proses 8 digit yang memakan waktu lama

## Requirements

### Python Version

- Python 3.7 atau lebih baru

### Dependencies

- `PyMuPDF` (fitz) - untuk membaca dan memanipulasi PDF
- `Pillow` (PIL) - untuk pemrosesan gambar
- `tkinter` - untuk GUI (sudah termasuk dalam Python)

## Instalasi

### 1. Clone repository atau download source code

```bash
git clone https://github.com/alrescha79-cmd/buka-paksa-pdf.git pdf-viewer
cd pdf-viewer
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Jalankan aplikasi

```bash
python main.py
```

## Cara Penggunaan

1. **Jalankan aplikasi**

   ```bash
   python main.py
   ```

2. **Pilih file PDF**
   - Klik tombol "Pilih PDF dan Mulai Proses"
   - Pilih file PDF yang terproteksi password

3. **Pilih mode brute force**
   - **6 digit**: Cepat, mencoba 1,000,000 kombinasi (000000-999999)
   - **8 digit**: Sangat lama, mencoba 100,000,000 kombinasi (00000000-99999999)

4. **Tunggu proses selesai**
   - Status akan ditampilkan secara real-time
   - Jika password ditemukan, halaman PDF akan ditampilkan

## Peringatan

⚠️ **Mode 8 digit** akan memakan waktu sangat lama (bisa berjam-jam hingga berhari-hari) tergantung pada:

- Kecepatan komputer
- Posisi password dalam urutan (apakah di awal atau akhir range)

⚠️ **Penggunaan Legal**: Pastikan Anda memiliki hak untuk membuka PDF tersebut. Tool ini hanya untuk file PDF yang Anda miliki atau memiliki izin untuk membuka.

## Troubleshooting

### Error: ModuleNotFoundError

```bash
pip install -r requirements.txt
```

### Error: tkinter tidak ditemukan (Linux)

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# CentOS/RHEL/Fedora
sudo yum install tkinter
# atau
sudo dnf install python3-tkinter
```

### Error: Tidak bisa membuka PDF

- Pastikan file PDF valid dan tidak corrupt
- Pastikan file tidak sedang dibuka di aplikasi lain

## Spesifikasi Teknis

- **GUI Framework**: tkinter
- **PDF Library**: PyMuPDF (fitz)
- **Image Processing**: Pillow (PIL)
- **Metode**: Brute force dengan iterasi sequential
- **Range Password**:
  - 6 digit: 000000 - 999999
  - 8 digit: 00000000 - 99999999
