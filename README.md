# 🎧 بوت فصل الصوت (Vocal / Instrumental Separation Bot)

بوت تليجرام يفصل صوت المغني عن الموسيقى باستخدام نموذج **Demucs** (AI Audio Source Separation).

---

## ⚠️ تنبيه أمني مهم (اقرأه الأول)

توكن البوت (`BOT_TOKEN`) لازم **يفضل سري تمامًا**:

- متحطوش أبدًا داخل الكود أو داخل ملف `.env` يترفع على GitHub.
- استخدم **GitHub Secrets** (شرح تحت) أو ملف `.env` محلي فقط على جهازك/السيرفر ومُضاف في `.gitignore` (موجود بالفعل هنا).
- لو التوكن اتكشف قبل كده (مثلاً اتبعت في محادثة أو تم رفعه بالغلط)، اعمل **Revoke/Regenerate** له فورًا من [@BotFather](https://t.me/BotFather) عن طريق `/revoke`.

---

## ⚠️ تنبيه عن استضافة GitHub Actions

طلبت تشغيل البوت واستضافته على GitHub Actions مع إعادة تشغيل كل 6 ساعات، وده موجود في المشروع (`.github/workflows/bot.yml`). لكن مهم توعى للقيود دي:

- **مفيش GPU مجاني** على GitHub Actions، فالمعالجة هتبقى على CPU وأبطأ بكتير من سيرفر فيه GPU.
- كل تشغيل جديد بياخد وقت لتحميل النموذج (Demucs) من الإنترنت، رغم إننا عملنا Cache ليه لتقليل الوقت.
- الـ Runner بتاع GitHub عنده حد أقصى **6 ساعات لكل Job**، فالبوت مبرمج يشتغل 350 دقيقة (~5 ساعات و50 دقيقة) بعدها يقفل نفسه بأمان، وبعدين الـ cron بيشغّله تاني.
- في **فجوة صغيرة بين انتهاء تشغيل وبداية التاني** (بضع ثواني لدقائق حسب سرعة الـ Runner)، يعني البوت مش 24/7 بشكل مضمون 100%.
- قاعدة البيانات (SQLite) بتتحفظ بين التشغيلات عن طريق `actions/cache`، لكنها مش موثوقة زي سيرفر حقيقي (ممكن الكاش يتحذف تلقائيًا لو مستخدمش لفترة).

**التوصية:** لو عايز استقرار حقيقي و24/7 مضمون + أداء أسرع، الأفضل VPS بسيط (حتى بدون GPU) بيشغل الكود عن طريق Docker مباشرة. المشروع جاهز للطريقتين.

---

## 📁 هيكل المشروع

```
bot/
├── main.py                  # نقطة البداية
├── config.py                 # كل الإعدادات من .env
├── handlers/
│   ├── start.py              # /start, /help, القائمة الرئيسية
│   ├── audio.py               # استقبال الملفات ومعالجتها
│   └── admin.py                # لوحة تحكم الأدمن
├── keyboards/
│   ├── main.py
│   └── admin.py
├── services/
│   ├── separation.py           # تشغيل نموذج Demucs
│   ├── ffmpeg.py                 # استخراج الصوت / تحويل الصيغ
│   ├── downloader.py              # تحميل ملفات تليجرام بأمان
│   ├── cleanup.py                  # حذف الملفات المؤقتة تلقائيًا
│   └── queue_manager.py             # نظام الطابور (Queue)
├── database/
│   └── db.py                          # SQLite (async)
├── utils/
│   ├── logger.py
│   ├── validators.py
│   └── system_info.py
├── .github/workflows/bot.yml           # تشغيل على GitHub Actions كل 6 ساعات
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## 1️⃣ إعداد بوت تليجرام

1. افتح [@BotFather](https://t.me/BotFather) وابعت `/newbot` (أو استخدم بوت موجود).
2. خد الـ **Token**.
3. عشان تعرف الـ **User ID** بتاعك كـ Owner/Admin، ابعت أي رسالة لـ [@userinfobot](https://t.me/userinfobot).

---

## 2️⃣ التشغيل محليًا (Local)

### تثبيت FFmpeg

**Ubuntu / Debian:**
```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
حمّل من [ffmpeg.org](https://ffmpeg.org/download.html) وضيفه لـ PATH.

### تثبيت PyTorch

**لو عندك CPU بس (مافيش GPU):**
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

**لو عندك NVIDIA GPU (CUDA 12.1 مثلاً):**
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```
(غيّر رقم إصدار CUDA حسب كارتك — تأكد من [docs.pytorch.org](https://pytorch.org/get-started/locally/))

### باقي المكتبات

```bash
git clone <رابط-الريبو>
cd audio-separator-bot
python -m venv venv
source venv/bin/activate   # على Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### إعداد .env

```bash
cp .env.example .env
```
افتح `.env` وحط فيه التوكن الصحيح والـ Admin IDs:
```
BOT_TOKEN=توكنك_هنا
ADMIN_IDS=8355232956
```

> نموذج Demucs (`htdemucs`) بيتحمل تلقائيًا أول مرة تشغّل فيها البوت (لا يحتاج تحميل يدوي)، ويتخزن في `~/.cache/torch` ويُعاد استخدامه بعد كده.

### التشغيل

```bash
python main.py
```

---

## 3️⃣ التشغيل على VPS / Linux Server

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv ffmpeg git

git clone <رابط-الريبو>
cd audio-separator-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # وعدّل التوكن والقيم

# تشغيل دائم باستخدام systemd (موصى به) أو screen/tmux:
python main.py
```

**لتشغيله كخدمة دائمة (systemd):**

أنشئ `/etc/systemd/system/audio-bot.service`:
```ini
[Unit]
Description=Audio Separator Telegram Bot
After=network.target

[Service]
WorkingDirectory=/path/to/audio-separator-bot
ExecStart=/path/to/audio-separator-bot/venv/bin/python main.py
Restart=always
EnvironmentFile=/path/to/audio-separator-bot/.env

[Install]
WantedBy=multi-user.target
```
ثم:
```bash
sudo systemctl daemon-reload
sudo systemctl enable audio-bot
sudo systemctl start audio-bot
```

---

## 4️⃣ التشغيل بـ Docker

```bash
cp .env.example .env   # وعدّل القيم
docker compose up -d --build
```

لمتابعة السجلات:
```bash
docker compose logs -f
```

### تفعيل GPU مع Docker

1. تأكد إن عندك [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) متثبت على السيرفر.
2. افتح `docker-compose.yml` وشيل التعليق (`#`) عن قسم `deploy.resources` في آخر الملف.
3. `docker compose up -d --build` تاني.

البوت بيكتشف GPU تلقائيًا (`torch.cuda.is_available()`) ويستخدمه لو موجود، وإلا يرجع لـ CPU تلقائيًا — من غير أي تعديل إضافي في الكود.

---

## 5️⃣ التشغيل على GitHub Actions (كل 6 ساعات)

1. ادفع المشروع لريبو على GitHub (تأكد إن `.env` مش متضاف — ملف `.gitignore` بيمنعه تلقائيًا).
2. من إعدادات الريبو: **Settings → Secrets and variables → Actions → New repository secret** وضيف:
   - `BOT_TOKEN` = توكن البوت
   - `ADMIN_IDS` = `8355232956`
3. الـ Workflow (`.github/workflows/bot.yml`) هيشتغل تلقائيًا كل 6 ساعات، وتقدر كمان تشغّله يدويًا من تاب **Actions → Run workflow**.
4. لو عايز تغيّر أي حد (حجم الملف، عدد العمليات...) عدّل قيم الـ `env:` جوه ملف الـ workflow مباشرة، أو حوّلها لـ Secrets/Variables لو حابب تغيّرها من غير تعديل كود.

> ملحوظة: أول تشغيل هياخد وقت أطول لتحميل نموذج Demucs، والتشغيلات اللي بعده هتبقى أسرع بفضل الـ cache.

---

## ⚙️ الإعدادات القابلة للتعديل (كلها في `.env` / GitHub Secrets)

| المتغير | الوصف | الافتراضي |
|---|---|---|
| `MAX_FILE_SIZE_MB` | أقصى حجم ملف مسموح | 50 |
| `MAX_DURATION_SECONDS` | أقصى مدة للأغنية | 600 |
| `MAX_WORKERS` | عدد العمليات المتزامنة في نظام الطابور | 1 |
| `MAX_CONCURRENT_PER_USER` | أقصى عدد ملفات متزامنة لكل مستخدم | 1 |
| `MAX_JOBS_PER_USER_DAILY` | أقصى عدد عمليات يوميًا لكل مستخدم | 10 |
| `MODEL_NAME` | اسم نموذج Demucs المستخدم | `htdemucs` |
| `RESULT_TTL_MINUTES` | بعد قد إيه تتحذف الملفات المؤقتة | 30 |
| `RUN_DURATION_MINUTES` | مدة تشغيل البوت قبل الإغلاق الآمن (لـ GitHub Actions) | 350 |

---

## 🔒 الأمان

- التوكن بيتقرأ من Environment Variables فقط، مش مكتوب في الكود.
- أسماء الملفات بتتحول لأسماء عشوائية آمنة قبل أي معالجة (`utils/validators.py`).
- كل استدعاءات FFmpeg بتستخدم `subprocess` بقوائم Arguments (مفيش `shell=True` أو تنفيذ نصوص من المستخدم مباشرة).
- الملفات الصوتية بتتحذف فورًا بعد إرسال النتيجة للمستخدم، والملفات المهملة بتتنضف تلقائيًا كل فترة.
- الـ Logs مفيهاش أي محتوى صوتي أو بيانات حساسة، بس IDs وحالة العمليات.

---

## 🧠 استبدال نموذج AI مستقبلًا

النظام مصمم بحيث تقدر تغيّر النموذج بس عن طريق تغيير `MODEL_NAME` في `.env` (مثلاً لنموذج Demucs تاني زي `htdemucs_ft` أو `mdx_extra`)، من غير ما تعدّل أي كود في `services/separation.py`.
