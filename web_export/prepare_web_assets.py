# -*- coding: utf-8 -*-
"""
PNG → WebP Dönüştürücü

Flower Control projesi için 150 adet 1280x720 RGBA PNG karesini
web'e uygun 640x360 WebP formatına dönüştürür.

Kullanım:
    python3 prepare_web_assets.py

Çıktı:
    web_export/frames/kare_001.webp ... kare_150.webp
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow kütüphanesi gerekli. Kurmak için: pip install Pillow")
    sys.exit(1)

# --- AYARLAR ---
KAYNAK_KLASOR = Path(__file__).parent.parent / "video" / "kare_bg"
CIKTI_KLASOR = Path(__file__).parent / "frames"
TOPLAM_KARE = 150
HEDEF_GENISLIK = 640
WEBP_KALITE = 85  # 0-100, 85 kalite/boyut dengesi iyi


def main():
    # Çıktı klasörünü oluştur
    CIKTI_KLASOR.mkdir(parents=True, exist_ok=True)

    if not KAYNAK_KLASOR.exists():
        print(f"HATA: Kaynak klasör bulunamadı: {KAYNAK_KLASOR}")
        sys.exit(1)

    print(f"Kaynak: {KAYNAK_KLASOR}")
    print(f"Çıktı:  {CIKTI_KLASOR}")
    print(f"Hedef:  {HEDEF_GENISLIK}px genişlik, WebP kalite {WEBP_KALITE}")
    print(f"Toplam: {TOPLAM_KARE} kare")
    print("-" * 50)

    basarili = 0
    toplam_boyut = 0

    for i in range(1, TOPLAM_KARE + 1):
        kaynak_adi = f"kare_{i:03d}.png"
        kaynak_yolu = KAYNAK_KLASOR / kaynak_adi
        cikti_adi = f"kare_{i:03d}.webp"
        cikti_yolu = CIKTI_KLASOR / cikti_adi

        if not kaynak_yolu.exists():
            print(f"  UYARI: {kaynak_adi} bulunamadı, atlanıyor.")
            continue

        try:
            img = Image.open(kaynak_yolu)

            # Orijinal en-boy oranını koru
            w_orig, h_orig = img.size
            hedef_yukseklik = int(h_orig * (HEDEF_GENISLIK / w_orig))

            # Yeniden boyutlandır (LANCZOS = en kaliteli)
            img_resized = img.resize(
                (HEDEF_GENISLIK, hedef_yukseklik),
                Image.LANCZOS
            )

            # WebP olarak kaydet (alpha kanalı korunur)
            img_resized.save(
                cikti_yolu,
                format="WEBP",
                quality=WEBP_KALITE,
                method=6,  # En iyi sıkıştırma (daha yavaş ama daha küçük)
                lossless=False,
            )

            dosya_boyutu = cikti_yolu.stat().st_size
            toplam_boyut += dosya_boyutu
            basarili += 1

            if i % 25 == 0 or i == 1:
                print(f"  [{i:3d}/{TOPLAM_KARE}] {cikti_adi} — {dosya_boyutu / 1024:.1f} KB")

        except Exception as e:
            print(f"  HATA: {kaynak_adi} işlenirken hata: {e}")

    print("-" * 50)
    print(f"Tamamlandı! {basarili}/{TOPLAM_KARE} kare dönüştürüldü.")
    print(f"Toplam boyut: {toplam_boyut / (1024 * 1024):.1f} MB")

    # İlk kareyi düşük çözünürlüklü placeholder olarak da kaydet
    placeholder_yolu = CIKTI_KLASOR / "placeholder.webp"
    try:
        img = Image.open(KAYNAK_KLASOR / "kare_001.png")
        img_placeholder = img.resize((160, 90), Image.LANCZOS)
        img_placeholder.save(placeholder_yolu, format="WEBP", quality=50)
        print(f"Placeholder oluşturuldu: {placeholder_yolu.stat().st_size / 1024:.1f} KB")
    except Exception as e:
        print(f"Placeholder oluşturulamadı: {e}")


if __name__ == "__main__":
    main()
