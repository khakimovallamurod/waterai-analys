# WaterAI Analysis 💧 — Suv Sifatini Sun'iy Intellekt Bilan Tahlil Qilish Platformasi

Ushbu platforma O‘zbekiston davlat standartlari (**SanPiN 0211-06**) hamda **JSST (WHO)** xalqaro me'yorlari asosida ichimlik, artezian, quduq va tabiiy daryo suvlari sifatini neyron tarmoq va ekspert qoidalar orqali kompleks tahlil qilish imkonini beradi.

---

## 🌟 Asosiy Imkoniyatlar

1. **AI Suv Sifati Indeksi (WQI) va Klassifikatsiya**:
   - 10+ ta fizik-kimyoviy parametrlar (pH, TDS, Turbidlik, Qattiqlik, Sulfatlar, Xloraminlar, Organik moddalar, Trihalometanlar, Harorat, EC).
   - Suvning 3 ta toifaga bo'linishi: 🟢 **Yaroqli**, 🟡 **Shartli yaroqli**, 🔴 **Yaroqsiz**.
   - Har bir toifa bo'yicha sun'iy intellektning ishonchlilik ehtimolligi (`confidence %`).

2. **Interaktiv Laboratoriya (Parametrlar kiritish)**:
   - Real vaqtda me'yorni tekshiruvchi slayderlar.
   - 4 xil tayyor namuna (`presets`): Vodoprovod, Tog' bulog'i, Quduq suvi, Daryo suvi.

3. **Chuqur Analitika va Tavsiyalar**:
   - 6 xil soha bo'yicha ko'rsatmalar (Ichish, Ovqat tayyorlash, Kir yuvish, Maishiy foydalanish, Sug'orish, Bolalar uchun).
   - Parametrlarning ruxsat etilgan chegaraga nisbati diagrammasi.
   - AI qaroriga eng ko'p ta'sir qiluvchi xususiyatlar (`Feature Importance`).

4. **Eksport va Hisobotlar**:
   - Bitta tahlil natijasini **CSV** ga yuklab olish.
   - Butun tahlillar tarixini CSV ga eksport qilish.
   - PDF ko'rinishida chop etish (`Print to PDF` optimallashtirilgan).

5. **Xavfsiz Autentifikatsiya va Rollar**:
   - O'zbekiston telefon raqami formati bilan ro'yxatdan o'tish (`+998 XX XXX-XX-XX`).
   - JWT va HttpOnly cookie asosidagi xavfsiz sessiyalar.
   - **Oddiy foydalanuvchi** va **Administrator** rollari.

6. **Admin Paneli va Umumiy Statistika**:
   - Barcha foydalanuvchilar va tahlillarni boshqarish.
   - Tahlillarni o'chirish va rollarni o'zgartirish.
   - Chart.js orqali interaktiv aylana va ustunli grafiklar.

7. **Moslashuvchan (Responsive) Dizayn**:
   - Desktop va planshetlar uchun to'liq boshqaruv.
   - Smartfonlar uchun qulay pastki menyu (**Bottom Navigation Bar**).

---

## 🚀 Ishga Tushirish

### 1. Virtual muhitni faollashtirish
```bash
source .venv/bin/activate
```

### 2. Bog'liqliklarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. Serverni ishga tushirish
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
yoki:
```bash
python main.py
```

Brauzerda oching: **http://localhost:8000**

---

## 🔐 Foydalanuvchilar va Xavfsizlik (SQLite & CLI)

Xavfsizlik talablariga ko'ra, **parollar va hisob ma'lumotlari manba kodida (source code) saqlanmaydi**. Barcha foydalanuvchilar SQLite3 (`waterai.db`) ma'lumotlar bazasida **bcrypt** yordamida shifrlangan holda saqlanadi.

### 1. Yangi foydalanuvchi yaratish yoki ro'yxatdan o'tish:
- Sayt orqali: `/register` sahifasida to'g'ridan-to'g'ri ro'yxatdan o'tish mumkin.
- CLI orqali administrator yaratish:
  ```bash
  python manage_users.py create-admin --phone "+998901234567" --name "Bosh Administrator"
  ```
- Foydalanuvchilar ro'yxatini ko'rish:
  ```bash
  python manage_users.py list
  ```
- Parolni xavfsiz tiklash:
  ```bash
  python manage_users.py reset-password --phone "+998901234567"
  ```

---

## 📁 Loyiha Strukturasi

```
waterai-analys/
├── main.py              # FastAPI serveri, barcha marshrutlar va biznes mantiqi
├── ai_engine.py         # WQI hisoblash, SanPiN me'yorlari va AI tavsiyalar dvigateli
├── auth.py              # JWT tokenlar, parol xeshlash, telefon maskasi
├── database.py          # SQLite va SQLAlchemy konfiguratsiyasi
├── models.py            # User, WaterAnalysis, ParameterNorm jadvallari
├── requirements.txt     # Python kutubxonalari
├── static/
│   ├── css/custom.css   # Glassmorphism, animatsiyalar va zamonaviy UI stillari
│   ├── js/analyze.js    # Slayderlar, presets va real-vaqt me'yor tekshiruvi
│   ├── js/main.js       # Telefon maskasi va bildirishnomalar
│   └── images/logo.png  # Loyiha logotipi
└── templates/
    ├── base.html        # Asosiy tartib (Tailwind, FontAwesome, Chart.js)
    ├── components/      # Navbar, footer, alert, bottom_menu
    ├── auth/            # login.html, register.html
    ├── user/            # dashboard, analyze, result, history, stats, profile
    └── admin/           # dashboard.html (Admin boshqaruvi)
```