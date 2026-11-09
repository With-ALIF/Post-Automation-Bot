# 🤖 Telegram to Facebook Auto Publisher Bot

একটি সম্পূর্ণ মডুলার এবং প্রোডাকশন-রেডি টেলিগ্রাম বট, যার সাহায্যে আপনি সরাসরি টেলিগ্রাম থেকেই আপনার ফেসবুক পেজে **Text Post** এবং **Image + Caption Post** অটোমেটিক প্রকাশ (Publish) করতে পারবেন।

---

## 🌟 প্রধান সুবিধাসমূহ (Key Features)

### 1. 📝 Text Post (টেক্সট পোস্ট)
- টেলিগ্রাম বটে যেকোনো সাধারণ মেসেজ পাঠালে সাথে সাথে ফেসবুক পোস্ট প্রিভিউ তৈরি হয়।
- প্রিভিউয়ের নিচে **🚀 Publish Now** এবং **❌ Cancel** বাトン প্রদর্শিত হয়।
- Publish বাটনে চাপ দিলে মেটা গ্রাফ এপিআই (`POST /{PAGE_ID}/feed`)-এর মাধ্যমে পোস্ট সরাসরি ফেসবুক পেজে চলে যায়।
- পোস্ট সফল হলে ফেসবুক পোস্ট আইডি ও ডিরেক্ট লিংকসহ কনফার্মেশন মেসেজ প্রদান করে।

### 2. 🖼 Image + Caption Post (ছবি ও ক্যাপশন পোস্ট)
- টেলিগ্রাম বটে ছবি পাঠালে স্বয়ংক্রিয়ভাবে তা গ্রহণ করে।
- ছবির সাথে ক্যাপশন পাঠানো হলে সেটিই পোস্টের ক্যাপশন হিসেবে ব্যবহার করে।
- কোনো ক্যাপশন ছাড়া ছবি পাঠালে পোস্ট করার আগে **➕ Add Caption** বাটনে চাপ দিয়ে ক্যাপশন লেখার সুবিধা রয়েছে।
- প্রয়োজনে **✏️ Edit Caption** বা **🗑 Remove Caption** করার অপশন থাকে।
- মেটা গ্রাফ এপিআই (`POST /{PAGE_ID}/photos`)-এর মাধ্যমে ছবি সরাসরি পেজে আপলোড হয়।

### 3. 🛡️ নিরাপত্তা ও অথোরাইজেশন (Security & Authorization)
- **Authorized User Protection:** `.env` ফাইলে নির্ধারিত `ALLOWED_USER_IDS` ব্যতীত কোনো অননুমোদিত ব্যক্তি বট ব্যবহার করতে পারবে না।
- **Token Sanitization:** কোনো ত্রুটি বা এক্সেপশন ঘটলেও মেসেজ বা লগে ফেসবুক বা টেলিগ্রামের কোনো অ্যাক্সেস টোকেন প্রকাশ পাবে না।
- **Git Protection:** `.gitignore` কনফিগার করা আছে যাতে `.env` ও সংবেদনশীল ক্রেডেনশিয়াল কখনো গিটহাবে পুশ না হয়।

### 4. ⚡ ডুপ্লিকেট পোস্ট প্রতিরোধ ও স্বয়ংক্রিয় রিট্রাই (Reliability)
- **Duplicate Prevention:** দ্রুত একাধিকবার পাবলিশ বাটন চাপলেও একই পোস্ট একাধিকবার পাবলিশ হবে না।
- **Network Resilience:** নেটওয়ার্ক ফেইলিওরের ক্ষেত্রে এক্সপোনেনশিয়াল ব্যাকঅফসহ স্বয়ংক্রিয় রিট্রাই মেকানিজম।
- **Telegram Channel Compatibility:** পূর্বের টেলিগ্রাম চ্যানেল অটো পাবলিশিং ওয়ার্কফ্লো অক্ষুণ্ণ রাখা হয়েছে (`AUTO_POST_TO_CHANNEL=true` থাকলে চ্যানেলেও স্বয়ংক্রিয় ক্রস-পোস্ট হবে)।

---

## 📁 প্রজেক্ট আর্কিটেকচার (Project Structure)

```text
pagebot/
├── .github/
│   └── workflows/
│       └── bot-ci.yml           # GitHub Actions CI & Verification
├── handlers/
│   ├── __init__.py
│   ├── command_handlers.py      # /start, /help, /status, /cancel, /settings
│   ├── menu_handlers.py         # Persistent Reply Keyboard বাটন হ্যান্ডলার
│   └── post_handlers.py         # Text, Photo, Caption ও Inline বাটনের লজিক
├── services/
│   ├── __init__.py
│   ├── facebook_service.py      # Meta Graph API ক্লায়েন্ট (Feed, Photos, Verification)
│   └── channel_service.py       # Telegram Channel Cross-Publisher সার্ভিস
├── utils/
│   ├── __init__.py
│   ├── auth.py                  # Authorized Telegram User ডেকোরেটর ও গার্ড
│   └── helpers.py               # টোকেন রেড্যাকশন, ডুপ্লিকেট ম্যানেজার ও কিবোর্ড
├── tests/
│   ├── __init__.py
│   └── test_bot.py              # সম্পূর্ণ ইউনিট ও ইন্টিগ্রেশন টেস্ট
├── .env.example                 # এনভায়রনমেন্ট ভ্যারিয়েবলের নমুনা
├── .gitignore                   # গিট ইগনোর রুলস
├── config.py                    # কনফিগারেশন লোডার ও ভ্যালিডেশন
├── main.py                      # বটের মূল এক্সিকিউশন ফাইল
├── requirements.txt             # ডিপেনডেন্সি লিস্ট
├── run_tests.py                 # টেস্ট রানার
└── README.md                    # নির্দেশিকা ও ডকুমেন্টেশন
```

---

## ⚙️ প্রয়োজনীয় সেটআপ (Setup Guide)

### ১. মেটা ফেসবুক পেজ ক্রেডেনশিয়াল সংগ্রহ (Facebook Credentials):
1. **Meta for Developers** ([developers.facebook.com](https://developers.facebook.com/)) এ গিয়ে একটি App তৈরি করুন (Type: `Business` অথবা `Other`).
2. **Graph API Explorer**-এ যান।
3. আপনার Facebook Page সিলেক্ট করুন এবং প্রয়োজনীয় পারমিশন যুক্ত করুন:
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `pages_show_list`
4. **Generate Access Token**-এ ক্লিক করে একটি দীর্ঘমেয়াদী (Never Expiring / Long-lived) Page Access Token সংগ্রহ করুন।
5. আপনার ফেসবুক পেজের **Page ID** সংগ্রহ করুন (About সেকশন অথবা পেজের সেটিংস থেকে)।

### ২. টেলিগ্রাম বট ও ইউজার আইডি সংগ্রহ (Telegram Credentials):
1. টেলিগ্রামে [@BotFather](https://t.me/BotFather)-এ গিয়ে `/newbot` লিখে একটি নতুন বট তৈরি করুন এবং **Bot Token** সংগ্রহ করুন।
2. আপনার নিজস্ব টেলিগ্রাম ইউজার আইডি জানতে [@userinfobot](https://t.me/userinfobot) বা [@raw_data_bot](https://t.me/raw_data_bot)-এ মেসেজ পাঠান।

### ৩. কনফিগারেশন ফাইল তৈরি (.env):
প্রজেক্ট ফোল্ডারে `.env.example` ফাইলটিকে কপি করে `.env` নামে সেভ করুন:

```bash
cp .env.example .env
```

`.env` ফাইলে আপনার সংগৃহীত মানগুলো বসান:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
ALLOWED_USER_IDS=123456789

FACEBOOK_PAGE_ID=109876543210
FACEBOOK_PAGE_ACCESS_TOKEN=EAAG...
GRAPH_API_VERSION=v21.0

# ঐচ্ছিক (টেলিগ্রাম চ্যানেলেও পোস্ট করতে চাইলে):
TELEGRAM_CHANNEL_ID=
AUTO_POST_TO_CHANNEL=false
```

---

## 🚀 বট চালু করার নিয়ম (How to Run)

### ডিপেনডেন্সি ইনস্টল করুন:
```bash
pip install -r requirements.txt
```

### টেস্ট রান করে যাচাই করুন:
```bash
python run_tests.py
```

### বট রান করুন:
```bash
python main.py
```

---

## 📱 বট কমান্ড ও ব্যবহার প্রণালী

| কমান্ড / অপশন | বিবরণ |
| :--- | :--- |
| `/start` | বট চালু করা ও প্রধান মেনু প্রদর্শন |
| `/help` | বিস্তারিত ব্যবহারের নিয়মাবলী |
| `/status` | ফেসবুক পেজ ও এপিআই কানেকশন স্ট্যাটাস চেক |
| `/settings` | বর্তমান কনফিগারেশন বিবরণী (নিরাপদভাবে মাস্ক করা) |
| `/cancel` | যেকোনো চলমান ড্রাফট বা ক্যাপশন এন্ট্রি বাতিল করা |
| 📝 Create Text Post | নতুন টেক্সট পোস্ট তৈরি করার প্রম্পট |
| 🖼 Create Image Post | ছবি পাঠিয়ে পোস্ট করার প্রম্পট |
| 📊 Publishing Status | পেজের কানেকশন যাচাই ও লাইভ লিংক ভিউ |
