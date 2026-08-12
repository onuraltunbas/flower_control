import cv2
import mediapipe as mp
import math
import os
import time

# --- AYARLAR ---
KLASOR_YOLU = "video/kare_bg"
TOPLAM_KARE = 150

# Geliştirici modunu açıp kapatmak için bu değeri True veya False yapman yeterli!
GELISTIRICI_MODU = True 

# Sadece genişliği belirliyoruz, yüksekliği kod orijinal orana göre kendi bulacak
CICEK_GENISLIGI = 400 
CICEK_BOYUTU = (400, 400) # Varsayılan, ilk resim yüklenirken güncellenecek

def overlay_image_alpha(img, img_overlay, x, y):
    h, w, _ = img_overlay.shape
    if y + h > img.shape[0] or x + w > img.shape[1]:
        return img
    overlay_image = img_overlay[..., :3]
    mask = img_overlay[..., 3:] / 255.0
    img[y:y+h, x:x+w] = (1.0 - mask) * img[y:y+h, x:x+w] + mask * overlay_image
    return img

def el_kutuda_mi(hand_lms, kutu_x1, kutu_y1, kutu_x2, kutu_y2, w, h):
    if not hand_lms: 
        return False
    x9, y9 = int(hand_lms.landmark[9].x * w), int(hand_lms.landmark[9].y * h)
    if (kutu_x1 < x9 < kutu_x2 and kutu_y1 < y9 < kutu_y2):
        return True
    return False

def ciz_gelistirici_bilgileri(frame, sol_el_lms, w, h, ref_boyut, min_oran, max_oran):
    """Geliştirici modu açıksa parmak uçlarını, çizgiyi ve detaylı matematiksel verileri ekrana basar."""
    if sol_el_lms:
        # 4 (Baş Parmak) ve 8 (İşaret Parmağı) koordinatları
        x4, y4 = int(sol_el_lms.landmark[4].x * w), int(sol_el_lms.landmark[4].y * h)
        x8, y8 = int(sol_el_lms.landmark[8].x * w), int(sol_el_lms.landmark[8].y * h)
        
        # Noktaları ve aradaki çizgiyi çiz
        cv2.circle(frame, (x4, y4), 8, (0, 255, 255), cv2.FILLED)
        cv2.circle(frame, (x8, y8), 8, (0, 255, 255), cv2.FILLED)
        cv2.line(frame, (x4, y4), (x8, y8), (0, 255, 255), 3)
        
        # Mesafeleri hesapla ve ekrana yazdır
        mesafe_px = math.hypot(x8 - x4, y8 - y4)
        
        # Yazıları ekranın sol üst köşesine, kutularla çakışmayacak bir yere yazalım
        bilgi_y_baslangic = h - 120
        cv2.putText(frame, "--- GELISTIRICI MODU ---", (10, bilgi_y_baslangic), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 100), 2)
        cv2.putText(frame, f"Anlik Mesafe (Piksel): {mesafe_px:.1f}", (10, bilgi_y_baslangic + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        if ref_boyut > 0:
            anlik_oran = mesafe_px / ref_boyut
            cv2.putText(frame, f"Anlik Oran: {anlik_oran:.3f}", (10, bilgi_y_baslangic + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, f"Kalibre Edilen Min: {min_oran:.3f} | Max: {max_oran:.3f}", (10, bilgi_y_baslangic + 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

# 1. Papatya karelerini hafızaya yükle ve En-Boy oranını düzelt
print("Görseller yükleniyor, lütfen bekleyin...")
papatya_kareleri = []
oran_hesaplandi = False

for i in range(1, TOPLAM_KARE + 1):
    dosya_adi = f"kare_{i:03d}.png"
    dosya_yolu = os.path.join(KLASOR_YOLU, dosya_adi)
    img = cv2.imread(dosya_yolu, cv2.IMREAD_UNCHANGED)
    
    if img is not None:
        # İlk resim yüklendiğinde orijinal en-boy oranını bul ve yüksekliği hesapla
        if not oran_hesaplandi:
            h_orig, w_orig = img.shape[:2]
            cicek_yuksekligi = int(h_orig * (CICEK_GENISLIGI / w_orig))
            CICEK_BOYUTU = (CICEK_GENISLIGI, cicek_yuksekligi)
            oran_hesaplandi = True
            print(f"Orijinal Oran Korundu. Yeni Çiçek Boyutu: {CICEK_BOYUTU}")

        img = cv2.resize(img, CICEK_BOYUTU)
        papatya_kareleri.append(img)

# 2. MediaPipe Kurulumu
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)

# --- DURUM VE KALİBRASYON DEĞİŞKENLERİ ---
durum = "BEKLEME" 
hizalama_zamanlayici = 0
zamanlayici_baslangic = 0

referans_el_boyutu = 0 
el_boyutlari = [] 
min_mesafe_orani = float('inf')
max_mesafe_orani = 0

cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    if not success: break

    frame = cv2.flip(frame, 1) # Ayna görüntüsü
    h, w, c = frame.shape
    
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    sol_el_lms = None
    sag_el_lms = None
    
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            x9 = hand_landmarks.landmark[9].x
            if x9 < 0.5: 
                sol_el_lms = hand_landmarks
            else:        
                sag_el_lms = hand_landmarks

    # --- DURUM MAKİNESİ (STATE MACHINE) ---
    
    if durum == "BEKLEME":
        sol_kutu = (int(w*0.1), int(h*0.2), int(w*0.4), int(h*0.8))
        sag_kutu = (int(w*0.6), int(h*0.2), int(w*0.9), int(h*0.8))
        
        sol_ok = el_kutuda_mi(sol_el_lms, *sol_kutu, w, h)
        sag_ok = el_kutuda_mi(sag_el_lms, *sag_kutu, w, h)
        
        cv2.rectangle(frame, (sol_kutu[0], sol_kutu[1]), (sol_kutu[2], sol_kutu[3]), (0, 255, 0) if sol_ok else (0, 0, 255), 2)
        cv2.putText(frame, "Sol El", (sol_kutu[0]+10, sol_kutu[1]+30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if sol_ok else (0, 0, 255), 2)
        
        cv2.rectangle(frame, (sag_kutu[0], sag_kutu[1]), (sag_kutu[2], sag_kutu[3]), (0, 255, 0) if sag_ok else (0, 0, 255), 2)
        cv2.putText(frame, "Sag El", (sag_kutu[0]+10, sag_kutu[1]+30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if sag_ok else (0, 0, 255), 2)

        cv2.putText(frame, "Baslamak icin ellerinizi kutulara hizalayin", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        if sol_ok and sag_ok:
            if hizalama_zamanlayici == 0:
                hizalama_zamanlayici = time.time()
            else:
                gecen_hizalama = time.time() - hizalama_zamanlayici
                kalan_hizalama = 3 - int(gecen_hizalama)
                
                cv2.putText(frame, f"SABIT TUTUN: {kalan_hizalama}", (int(w/2)-120, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
                
                if gecen_hizalama > 3:
                    durum = "KALIB_1"
                    zamanlayici_baslangic = time.time()
        else:
            hizalama_zamanlayici = 0 

    elif durum == "KALIB_1":
        gecen_sure = time.time() - zamanlayici_baslangic
        kalan_sure = 5 - int(gecen_sure)
        
        if gecen_sure > 5:
            referans_el_boyutu = sum(el_boyutlari) / len(el_boyutlari) if el_boyutlari else 100.0
            durum = "KALIB_2"
            zamanlayici_baslangic = time.time()
        else:
            cv2.putText(frame, f"Adim 1: Ellerinizi sabit tutun. {kalan_sure}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            if sol_el_lms:
                x0, y0 = int(sol_el_lms.landmark[0].x * w), int(sol_el_lms.landmark[0].y * h)
                x9, y9 = int(sol_el_lms.landmark[9].x * w), int(sol_el_lms.landmark[9].y * h)
                el_boyutlari.append(math.hypot(x9 - x0, y9 - y0))

    elif durum == "KALIB_2":
        gecen_sure = time.time() - zamanlayici_baslangic
        kalan_sure = 5 - int(gecen_sure)
        
        if gecen_sure > 5:
            durum = "OYUN"
        else:
            cv2.putText(frame, f"Adim 2: Sol isaret ve bas parmaginizi acip kapatin. {kalan_sure}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            if sol_el_lms:
                x4, y4 = int(sol_el_lms.landmark[4].x * w), int(sol_el_lms.landmark[4].y * h)
                x8, y8 = int(sol_el_lms.landmark[8].x * w), int(sol_el_lms.landmark[8].y * h)
                mesafe = math.hypot(x8 - x4, y8 - y4) / referans_el_boyutu
                if mesafe < min_mesafe_orani: min_mesafe_orani = mesafe
                if mesafe > max_mesafe_orani: max_mesafe_orani = mesafe

    elif durum == "OYUN":
        cv2.putText(frame, "Proje Aktif! Sol elinizle cicegi buyutun.", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        kare_indeksi = 0
        
        if sol_el_lms:
            x4, y4 = int(sol_el_lms.landmark[4].x * w), int(sol_el_lms.landmark[4].y * h)
            x8, y8 = int(sol_el_lms.landmark[8].x * w), int(sol_el_lms.landmark[8].y * h)
            
            anlik_mesafe_orani = math.hypot(x8 - x4, y8 - y4) / referans_el_boyutu
            
            # Eğer max_mesafe_orani ve min_mesafe_orani aynıysa 0'a bölünme hatasını engellemek için güvenlik önlemi
            fark = max_mesafe_orani - min_mesafe_orani
            if fark < 0.01: fark = 0.01 
            
            oran = max(0, min(anlik_mesafe_orani - min_mesafe_orani, max_mesafe_orani - min_mesafe_orani)) / fark
            kare_indeksi = int(oran * (TOPLAM_KARE - 1))

        if len(papatya_kareleri) > 0:
            cicek_resmi = papatya_kareleri[kare_indeksi]
            frame = overlay_image_alpha(frame, cicek_resmi, 0, h - CICEK_BOYUTU[1])

    # --- GELİŞTİRİCİ MODU ÇİZİMİ ---
    if GELISTIRICI_MODU:
        ciz_gelistirici_bilgileri(frame, sol_el_lms, w, h, referans_el_boyutu, min_oran=min_mesafe_orani if min_mesafe_orani != float('inf') else 0, max_oran=max_mesafe_orani)

    cv2.imshow("Papatya Kontrol", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()