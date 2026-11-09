import os
import sys
import argparse
import random
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USERID_OUTPUT = PROJECT_ROOT / "data" / "accounts" / "userid.txt"

def generate_userid(nama_lengkap):
    """
    Fungsi untuk membuat userid maksimal 7 karakter.
    (Maksimal 4 Huruf + 3 Angka Random)
    """
    kata = nama_lengkap.strip().split()
    
    if len(kata) == 1:
        base_id = kata[0].lower()
    else:
        kata_pertama = kata[0].lower()
        akhiran_kata_terakhir = kata[-1][-2:].lower()
        base_id = kata_pertama + akhiran_kata_terakhir
        
    base_id = ''.join(e for e in base_id if e.isalnum())
    base_id = base_id[:6]
    
    angka_random = str(random.randint(100, 999))
    return base_id + angka_random

def format_nomor_hp(nomor):
    """
    Fungsi untuk memastikan nomor HP berawalan 0
    """
    nomor = nomor.strip()
    if nomor.startswith('8'):
        return '0' + nomor
    elif nomor.startswith('62'):
        return '0' + nomor[2:]
    return nomor

def proses_format_data(file_input, file_output, file_userid, password_tetap, bank_code, bank_name):
    if not os.path.exists(file_input):
        print(f"[!] ERROR: File '{file_input}' tidak ditemukan.")
        sys.exit(1)

    baris_sukses = 0
    baris_gagal = 0

    print(f"[*] Mulai memproses file : {file_input}")
    
    try:
        # Membuka 1 file input dan 2 file output sekaligus
        with open(file_input, 'r', encoding='utf-8') as f_in, \
             open(file_output, 'w', encoding='utf-8') as f_out, \
             open(file_userid, 'w', encoding='utf-8') as f_uid:
            
            for no_baris, baris in enumerate(f_in, start=1):
                baris_bersih = baris.strip()
                if not baris_bersih:
                    continue
                
                data_terpecah = baris_bersih.split(maxsplit=1)
                
                if len(data_terpecah) == 2:
                    nomor_mentah = data_terpecah[0]
                    nama_lengkap = data_terpecah[1]
                    
                    nomor_hp = format_nomor_hp(nomor_mentah)
                    userid = generate_userid(nama_lengkap)
                    
                    # Susun Format Akhir Lengkap
                    hasil_format = f"{userid}|{password_tetap}|{nama_lengkap}|{bank_code}|{bank_name}|{nomor_hp}\n"
                    
                    # Tulis ke file hasil utama
                    f_out.write(hasil_format)
                    
                    # Tulis HANYA userid ke file userid.txt
                    f_uid.write(f"{userid}\n")
                    
                    baris_sukses += 1
                else:
                    print(f"[-] PERINGATAN (Baris {no_baris}): Format salah -> '{baris_bersih}'")
                    baris_gagal += 1
                    
        print("-" * 55)
        print("[v] PROSES SELESAI!")
        print(f"    - Berhasil diformat   : {baris_sukses} data")
        print(f"    - Gagal/Dilewati      : {baris_gagal} data")
        print(f"    - File Hasil Lengkap  : {file_output}")
        print(f"    - File Khusus UserID  : {file_userid}  <-- (File baru!)")
        print("-" * 55)

    except Exception as e:
        print(f"[!] ERROR: Terjadi kesalahan. Detail: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Program Generator Data & Ekstraksi UserID",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("-i", "--input", required=True, help="File input (Contoh: data_mentah.txt)")
    parser.add_argument("-o", "--output", required=True, help="File output utama (Contoh: hasil.txt)")
    
    # Argumen baru untuk menentukan nama file userid
    parser.add_argument(
        "-ou",
        "--out_userid",
        default=DEFAULT_USERID_OUTPUT,
        help=f"File khusus UserID (Default: {DEFAULT_USERID_OUTPUT})",
    )
    
    parser.add_argument("-p", "--password", default="Waktu888", help="Password mutlak (Default: Waktu888)")
    parser.add_argument("-bc", "--bankcode", default="63", help="Kode Bank / E-Wallet (Default: 63)")
    parser.add_argument("-bn", "--bankname", default="LINKAJA", help="Nama Bank / E-Wallet (Default: LINKAJA)")

    args = parser.parse_args()

    proses_format_data(args.input, args.output, args.out_userid, args.password, args.bankcode, args.bankname)
