# منظومة إصدار شهادات الرفع المساحي والتقاطعات الجغرافية (SPV Online)
### معمارية سحابية كاملة: Modal Serverless Backend + Vercel Frontend + GitHub Actions CI/CD

---

## 🌟 نظرة عامة على المشروع

تم تصميم وتطوير هذه النسخة السحابية لتعمل دون الحاجة إلى تثبيت أي برمجيات معقدة على أجهزة المستخدمين:
1. **Frontend على Vercel:**
   - واجهة ويب عصرية تفاعلية بتقنية Drag & Drop لرفع ملفات الأركان والأحواض (`Land_*.csv` و `Areas_*.csv`).
   - معاينة فورية لكروكي الأبعاد (CAD) وصور الأقمار الصناعية عالية الدقة.
   - تنزيل مباشر لحزمة الشهادة الرسمية بصيغة ZIP تضم ملف Word معتمد (.docx) والصور الأصلية.
2. **Backend على Modal (modal.com):**
   - خادم سحابي عديم الخوادم (Serverless Container) بتقنية FastAPI.
   - معالجة جغرافية دقيقة بنظام WGS84 Geodesic، وتوليد صور الأقمار الصناعية وكروكي الـ CAD مع دعم كامل للخطوط وتشكيل النصوص العربية في بيئة Linux.
3. **أتمتة النشر عبر GitHub Actions:**
   - بمجرد عمل `git push`:
     - يتم تحديث واجهة Vercel تلقائياً وفورياً بنسبة 100%.
     - يقوم GitHub Action بنشر الكود الجديد على خوادم Modal سحابياً آلياً.

---

## 📁 هيكل المجلدات (`SPV_online`)

```text
SPV_online/
├── backend/
│   ├── modal_app.py               # الخادم السحابي Modal + FastAPI
│   ├── cad_engine.py              # محرك رسم كروكي الـ CAD ودعم الخطوط العربية
│   ├── sat_engine.py              # محرك جلب ودمج صور الأقمار الصناعية
│   ├── docx_engine.py             # محرك تعبئة وطباعة الشهادة الرسمية
│   ├── قالب_شهادة_الرفع_المساحي_الرسمية.docx # القالب الرسمي المعتمد
│   ├── requirements.txt           # مكتبات بايثون المطلوبة
│   └── test_local_backend.py      # سكريبت الفحص الشامل محلياً
├── frontend/
│   ├── index.html                 # واجهة الويب السحابية (Drag & Drop + Direct Download)
│   ├── vercel.json                # تهيئة الاستضافة على Vercel
│   └── assets/                    # الشعار والأيقونات الرسمية
├── .github/
│   └── workflows/
│       └── deploy-modal.yml       # خط الأتمتة والنشر التلقائي عبر GitHub Actions
└── sample_data/                   # ملفات اختبارية جاهزة للتجربة الفورية
    ├── Land_101_محمد_احمد.csv
    └── Areas_101_محمد_احمد.csv
```

---

## 🚀 دليل النشر والتشغيل خطوة بخطوة

### 1. ربط ونشر الباك إند على Modal (أول مرة):
1. افتح التيرمينال وسجل الدخول في حساب Modal الخاص بك:
   ```bash
   modal token new
   ```
   (سيفتح المتصفح ليمنح جهازك مفتاح الربط آلياً).
2. اختبر النشر من جهازك:
   ```bash
   cd SPV_online/backend
   modal deploy modal_app.py
   ```
3. سيعطيك Modal رابطاً عاماً لخادمك السحابي مثل:
   `https://<your-username>--spv-cert-suite-modal-asgi.modal.run`
   *(انسخ هذا الرابط)*.

---

### 2. استضافة الواجهة على Vercel:
1. توجه إلى [vercel.com](https://vercel.com) واضغط **Add New > Project**.
2. اختر مستودع الـ GitHub الخاص بك.
3. في خانة **Root Directory**: اختر مجلد `frontend` (وليس `SPV_online/frontend`).
4. اضغط **Deploy**!
5. بعد انتهاء النشر (أقل من دقيقة):
   - افتح رابط موقعك على Vercel.
   - اضغط على زر **⚙ إعدادات الـ API** في أعلى الشاشة.
   - ضع رابط Modal الذي حصلت عليه في الخطوة السابقة واضغط "حفظ واعتماد".

---

### 3. تفعيل النشر التلقائي عند التعديل على GitHub (CI/CD):
لكي يقوم GitHub بنشر أي تعديل في الباك إند على Modal تلقائياً دون الحاجة لتشغيل أي أمر يدوي:
1. اذهب إلى إعدادات حسابك في Modal: [modal.com/settings](https://modal.com/settings) وانشئ **API Token**.
2. انسخ `Token ID` و `Token Secret`.
3. اذهب إلى مستودع المشروع على GitHub:
   - ادخل على **Settings > Secrets and variables > Actions**.
   - اضغط **New repository secret** وأضف:
     * `MODAL_TOKEN_ID` = (قيمة الـ Token ID)
     * `MODAL_TOKEN_SECRET` = (قيمة الـ Token Secret)
4. انتهى! الآن عند عمل أي `git push`:
   - Vercel سيبني الواجهة الجديدة فوراً.
   - GitHub Actions سينشر الباك إند على Modal تلقائياً.

---

## 💻 التشغيل المحلي أثناء التطوير (Local Development)

إذا أردت تجربة النظام محلياً بالكامل على جهازك:
1. تشغيل خادم FastAPI المحلي:
   ```bash
   cd SPV_online/backend
   python modal_app.py
   ```
   سيعمل السيرفر على: `http://localhost:8000`.
2. فتح الواجهة:
   افتح ببساطة ملف `SPV_online/frontend/index.html` في أي متصفح، وسيتصل تلقائياً بالسيرفر المحلي.
