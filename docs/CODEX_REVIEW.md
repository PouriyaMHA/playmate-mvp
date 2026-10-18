# بررسی مستقل PlayMate — کد، سایت زنده و محصول

تاریخ: **۱۸ اکتبر ۲۰۲۶**، منطقهٔ زمانی America/Vancouver  
نسخهٔ محلی بررسی‌شده: commit `f76de29`  
سایت: [PlayMate](https://playmate-api-aamc.onrender.com)

## نتیجهٔ اصلی

**امتیاز کلی پس از تست عملی با سه حساب: ۶٫۵ از ۱۰، به‌عنوان یک MVP در early access.** چرخهٔ اصلی ثبت‌نام → پروفایل → like → mutual → نمایش اطلاعات تماس، در سایت زنده کار کرد. طراحی بصری، وضوح مسئله و ایدهٔ مخفی‌ماندن اطلاعات تماس تا علاقهٔ متقابل، نقاط قوت واقعی‌اند. با این حال، نشت اطلاعات بین حساب‌ها و double-skip اکنون در مرورگر نیز تأیید شده‌اند؛ هم‌زمانی تعویض بازی، هویت سراسری کاربر، کشف پیشنهادهای بعدی و رسیدگی به تخلف همچنان نیاز به کار دارند. نمرهٔ کلی حفظ شد: اطمینان به کارکرد هسته بیشتر شد، ولی واقعی‌بودن چند ضعف نیز روشن‌تر شد.

برای دعوت محدود یک کامیونیتی کوچک، پس از اصلاح موارد High، مسیر قابل‌قبولی وجود دارد. برای تبلیغ عمومی و رشد بدون نظارت، هنوز آماده نیست. **هیچ آسیب‌پذیری Critical تأیید نشد؛ این به معنای تأیید امنیت کامل نیست.**

## دامنه، روش و محدودیت‌ها

ابتدا `AGENTS.md`، `docs/CODEX_REVIEW_BRIEF.md`، `CLAUDE.md` و `docs/PROJECT_HISTORY.md` خوانده شدند. مسیرهای اصلی backend، مدل بازی‌ها و مکان‌ها، سه فایل JavaScript، HTML/CSS صفحات، وابستگی‌ها و workflow موجود بررسی شدند. فایل تولید artwork فقط به‌صورت ایستا بررسی شد و اجرا نشد.

این گزارش دو دور بررسی را ترکیب می‌کند. دور اول طبق محدودیت اولیه کاملاً فقط‌خواندنی بود. در دور دوم، مالک صریحاً ساخت سه حساب، پذیرش Terms/Privacy و ذخیرهٔ پروفایل و تعاملات بین همین حساب‌ها را مجاز کرد. یک تلاش ذخیرهٔ پروفایل ابتدا توسط بررسی خودکار مجوز متوقف شد؛ پس از دریافت اجازهٔ صریح‌تر مالک، تست ادامه یافت.

- سه حساب با ایمیل‌های ساختگی روی دامنهٔ رزروشدهٔ `example.com` ساخته شد؛ دادهٔ بازی و اطلاعات تماس همگی آزمایشی بودند. رمز حساب‌ها در گزارش یا log چاپ نشد.
- پروفایل‌ها، like، mutual، Looking now، دعوت و block فقط در محدودهٔ حساب‌های آزمایشی انجام شدند. به کاربران واقعی like، block، report یا پیام ارسال نشد؛ Skip روی کارت‌های دیگر فقط وضعیت محلی UI را تغییر داد.
- `.env` خوانده یا چاپ نشد؛ برنامهٔ اصلی محلی اجرا نشد؛ SQL یا دسترسی service key برای نوشتن استفاده نشد. ping خودکار و سایر ذخیره‌ها از مسیر معمول سایت و حساب‌های مجاز انجام شدند.
- در پایان، پس از تأیید جداگانهٔ حذف دائمی، A/B از رابط سایت حذف شدند. به‌علت قفل native Confirm مرورگر، سه بازی باقی‌مانده و حساب C از **API خود اپ با ورود همان حساب C** حذف شد؛ هویت C پیش از حذف کنترل شد. فایل موقت رمز فقط برای همین پاک‌سازی استفاده و در finally حذف شد؛ هیچ رمز، access token یا service key چاپ نشد.
- هیچ کد، تنظیم، وابستگی یا asset پروژه تغییر نکرد. فقط همین گزارش به‌روز شد؛ commit، push و PR انجام نشد. تصویرهای شواهد در پوشهٔ خروجی بیرون repository ذخیره شدند.
- بررسی REST ناشناس دور اول با **کلید عمومیِ از قبل منتشرشده در frontend**، فقط GET و فقط انتخاب ستون `id` با `limit=1` بود. شناسه‌ها و کلید در گزارش ثبت نشدند.

مرورگر واقعی روی سایت زنده، در viewport دسکتاپ **1440×900** و موبایل **390×844** استفاده شد؛ پروفایل و صفحهٔ Privacy در عرض **320** نیز بررسی شدند. این شبیه‌سازی عرض مرورگر است، نه تست روی Safari/iOS، Android واقعی یا چند موتور مرورگر.

ثبت‌نام تا پایان، ورود موفق و ناموفق، onboarding، ذخیرهٔ چند بازی، like یک‌طرفه، mutual، نمایش و کپی اطلاعات تماس، reload و block در دور دوم **عملاً تست شدند**. انقضای واقعی توکن و refresh پس از آن، دریافت ایمیل بازیابی و تغییر رمز، load test، رقابت هم‌زمان روی دیتابیس و تزریق خطای حذف هنوز تست نشده‌اند. ابزار مرورگر برای `window.prompt` گزارش تخلف خطای صریح عدم پشتیبانی داد؛ ارسال Report از ابتدا تا انتها تأیید نشده است. policyهای کامل RLS، indexها، FKها، تنظیمات Render و داشبورد Supabase مستقلاً دیده نشدند. سه ثبت‌نام بدون تأیید ایمیل وارد اپ شدند، مطابق تنظیم اعلام‌شدهٔ مالک؛ خود داشبورد تنظیمات دیده نشد. برابری دقیق همهٔ فایل‌های deployشده با commit محلی نیز قابل‌اثبات نبود.

سطح شواهد در یافته‌ها مشخص است: «زنده»، «بازتولید آفلاین»، «کد» یا «نیازمند تأیید schema/config».

## تکمیل بررسی با سه حساب واقعی آزمایشی

### داده‌های آزمون و وضعیت پاک‌سازی

| حساب آزمایشی | ایمیل ساختگی | مشخصات و پروفایل‌های ساخته‌شده |
|---|---|---|
| A: `pmqa261018a` | `pmqa261018a@example.com` | Iran/Tehran، English+Persian، Voice؛ Battlefield، Minecraft Java، GTA PC، LoL EUW، FC PlayStation |
| B: `pmqa261018b` | `pmqa261018b@example.com` | Iran/Tehran، English+Persian، Voice؛ Battlefield، Minecraft Java، GTA PlayStation، LoL EUW، FC PC |
| C: `pmqa261018c` | `pmqa261018c@example.com` | Canada/Vancouver، German، No mic؛ Battlefield، Minecraft Bedrock/Mobile، LoL NA، FC Switch |

مجموعاً **۱۴ game profile** روی سه حساب ساخته شد. bio هر سه حساب با عبارت QA TEST ACCOUNT و توضیح «بازیکن واقعی نیست» مشخص شد. **پاک‌سازی نهایی تکمیل شد:** A/B از مسیر Delete account در UI حذف شدند؛ FC حساب C از UI و سه بازی باقی‌مانده و حساب C از API با ورود همان حساب حذف شدند. GET عمومی برای **هر سه نام 404** داد؛ ورود دوبارهٔ A از UI و C از Auth API رد شد. نبود C در یک تب تازهٔ مرورگر نیز تأیید و تصویر ذخیره شد. هیچ حساب آزمایشی برای ادامهٔ کار باقی گذاشته نشد. بررسی مستقیم جدول‌ها با کلید مدیر یا SQL انجام نشد؛ این نتیجه بر پیام موفقیت حذف، وضعیت endpointها و رد ورود متکی است.

### نتایج عملی

| سناریو | نتیجهٔ مشاهده‌شده |
|---|---|
| سه ثبت‌نام با ایمیل ساختگی | موفق؛ هر سه بدون تأیید ایمیل وارد اپ شدند |
| login دوباره و رمز اشتباه | ورود صحیح موفق؛ یک تلاش با رمز غلط برای حساب آزمایشی با پیام Wrong email or password رد شد |
| انتخاب اولین بازی و فرم ناقص | موفق؛ فیلدهای Region/Country/Platform/Mode/Languages مشخص و focus به فیلد ناقص منتقل شد |
| انتخاب منطقه → کشور → شهر | Iran/Tehran و Canada/Vancouver قابل‌ذخیره و پس از بازگشت قابل‌بازیابی بودند |
| جداسازی حساب‌ها پس از خروج | **ناموفق:** فرم تازهٔ B، Discord حساب A را پیش‌پر کرد؛ تصویر ذخیره شد. مقدار پیش از ذخیره به Discord آزمایشی B اصلاح شد |
| امتیاز و دلایل Battlefield برای A/B | ۱۰۰٪؛ منطقه، کشور، شهر، دو زبان، voice، platform، mode و کلاس مکمل به‌درستی توضیح داده شدند |
| اولویت Looking now | A/B پیش از سایر پیشنهادها آمدند؛ C حتی با امتیاز ۸٪ آن‌ها را در ابتدای deck دید |
| like یک‌طرفه B→A | پیام LIKE SENT؛ تماس A همچنان مخفی؛ در Pending Likes وضعیت انتظار نمایش داده شد |
| like متقابل A→B | پیام IT'S A MATCH؛ Squad ساخته شد و IGN/Discord آزمایشی B برای A آشکار شد |
| سمت مقابل match | بعد از ورود دوبارهٔ B، IGN/Discord آزمایشی A هم برای B قابل‌مشاهده بود |
| کپی Discord و reload | محتوای کپی با مقدار آزمایشی موردانتظار یکسان بود؛ Squad پس از reload باقی ماند |
| دعوت A→B | پس از ساخت پروفایل B، شمارندهٔ A عبارت 1 friend joined را نشان داد؛ این فقط یک دعوت ترتیبی بود، نه آزمون ضدتقلب یا concurrency |
| چند بازی در یک حساب | A و B هر کدام پنج بازی داشتند؛ نام حساب ثابت و فرم بازی‌ها مستقل بود؛ اطلاعات مشترک از بازی دیگر پیش‌پر شد |
| Minecraft Java در A/B | B به‌عنوان پیشنهاد A دیده شد |
| Minecraft Bedrock در C | هیچ‌یک از دو پروفایل Java به C پیشنهاد نشد |
| GTA PC در A در برابر PlayStation در B | B به A پیشنهاد نشد؛ نتیجهٔ A خالی بود |
| LoL EUW در A/B | B برای A دیده شد؛ C روی NA، این دو بازیکن را ندید |
| FC PlayStation در A و PC در B | B برای A پیشنهاد شد؛ C روی Switch هیچ‌کدام را ندید |
| Same language only در C | A/B با English+Persian کنار رفتند؛ یک پیشنهاد آلمانی‌زبان باقی ماند |
| Only looking now در C | دو حساب Looking now یعنی A/B باقی ماندند؛ ترکیب آن با German-only نتیجهٔ خالی داد |
| empty state و Show everyone | پیام و راه خروج از فیلتر نمایش داده شد و Show everyone پیشنهادها را بازگرداند |
| Skip سریع | **ناموفق:** یک double-click شمارنده را از ۴ به ۲ رساند؛ بازتولید زندهٔ M03 |
| ویرایش حساب | bio/avatar/banner ذخیره و نمایش داده شدند؛ ورود markup بی‌خطر `<b>` در bio با پیام اعتبارسنجی رد شد |
| مالک در برابر بازدیدکننده | Edit profile برای مالک موجود بود؛ هنگام مشاهدهٔ پروفایل A از C وجود نداشت |
| block C→A | بعد از reload، A در کل پنج کارت باقی‌ماندهٔ C نبود؛ برای کنترل، deck از طریق Skip محلی تا انتها دیده شد |
| block A→B | پیام Blocked آمد؛ پس از reload، Squad خالی شد و B در Minecraft هم دیگر پیشنهاد نشد، با وجود سازگاری قبلی |
| UI بلافاصله پس از block | کارت Squad و تماس B فوراً از تصویر حذف نشد؛ پس از reload حذف شد. حداکثر زمان ماندگاری اندازه‌گیری نشد؛ حذف محلی فوری و کنترل پاسخ قدیمی توصیه می‌شود |
| پروفایل عمومی فرد blocked | همچنان از حساب C باز شد؛ تأیید عملی محدودیت وعدهٔ block، نه نشت IGN/Discord |
| Report | **تأییدنشده:** `prompt() is not supported` در console همین مرورگر، پیش از ارسال فرم؛ این نتیجه به همهٔ مرورگرهای معمولی تعمیم داده نمی‌شود |
| حذف حساب A و B | موفق از UI؛ پیام حذف نمایش داده شد. ورود مجدد A رد شد و public API برای A/B پاسخ 404 داد |
| حذف یک بازی C | FC حذف شد و تعداد بازی‌ها از چهار به سه رسید؛ بقیهٔ بازی‌ها در یک تب تازه همچنان موجود بودند |
| حذف سه بازی باقی‌مانده و آخرین بازی C | از **API با توکن همان C** انجام شد؛ هر سه DELETE موفق. سپس `/api/account` هنوز 200، `username=null` و `games=[]` داشت، ولی public-profile برابر 404 شد؛ تأیید backend نگرانی M06. تکمیل این مسیر از دکمه‌های UI به‌علت native Confirm تأیید نشد |
| حذف نهایی C | از API خود حساب موفق؛ public API هر سه حساب 404، ورود دوبارهٔ C برابر 400 و در مرورگر Player not found مشاهده شد |
| دسکتاپ/موبایل داخل حساب | هر سه ستون دسکتاپ و تب‌های Profile/Match/Squad موبایل استفاده شدند؛ modalهای like/match روی موبایل کار کردند، ولی نام و IGN بلند بیش از حد شکسته/کوتاه شدند |

تغییر بازی نیز یک پنجرهٔ انتقالی نشان داد که URL بازی جدید شده بود ولی کارت و نام بازی قبلی هنوز روی صفحه و دکمهٔ like موجود بود. عمداً در این پنجره like ارسال نشد. این مشاهده، همراه با بازتولید آفلاین پاسخ‌های جابه‌جا، نگرانی H02 را تقویت می‌کند؛ مسابقهٔ پاسخ‌های شبکه با throttle مصنوعی در production ایجاد نشد.

### شواهد تصویری منتخب

تصویرها فقط اطلاعات آزمایشی دارند. مسیرها محلی‌اند و در پوشهٔ خروجی این گفت‌وگو قرار دارند، نه در repository:

- [Discord حساب A در فرم حساب تازهٔ B](<C:/Users/pouri/.codex/visualizations/2026/10/18/01a14e2b-6c89-7ef3-8d2a-a49863cf8ae6/playmate-cross-account-prefill.png>)؛ نام B در snapshot همان مرحله تأیید شد و در این قاب پایین فرم بیرون تصویر است.
- [کارت A پیش از mutual و قفل اطلاعات تماس](<C:/Users/pouri/.codex/visualizations/2026/10/18/01a14e2b-6c89-7ef3-8d2a-a49863cf8ae6/playmate-before-mutual.png>).
- [modal واقعی mutual در موبایل](<C:/Users/pouri/.codex/visualizations/2026/10/18/01a14e2b-6c89-7ef3-8d2a-a49863cf8ae6/playmate-mutual-mobile.png>).
- [Squad و اطلاعات تماس پس از mutual](<C:/Users/pouri/.codex/visualizations/2026/10/18/01a14e2b-6c89-7ef3-8d2a-a49863cf8ae6/playmate-mutual-squad.png>).
- [صفحهٔ عمومی A همچنان برای C پس از block قابل‌دیدن است](<C:/Users/pouri/.codex/visualizations/2026/10/18/01a14e2b-6c89-7ef3-8d2a-a49863cf8ae6/playmate-blocked-public-visible.png>).
- [پروفایل C پس از پاک‌سازی دیگر پیدا نمی‌شود](<C:/Users/pouri/.codex/visualizations/2026/10/18/01a14e2b-6c89-7ef3-8d2a-a49863cf8ae6/playmate-cleanup-profile-missing.png>).

موفقیت این سناریوهای UI به معنای تست تمام payloadهای API با توکن جعلی، RLS نقش authenticated، بازیابی ایمیل، انقضای session، تمام ترکیب‌های ۱۲ بازی یا ظرفیت production نیست. برای این‌ها همچنان staging و تست‌های مستقل لازم‌اند.

## نقاط قوت

1. **مسئله و پیام روشن است.** شعار اصلی، زبان، منطقه، mic و نمایش دلیل پیشنهاد، ارزش محصول را سریع منتقل می‌کنند. طراحی تاریک و رنگ‌های neon با مخاطب بازی هماهنگ‌اند.
2. **هویت عملیات از JWT گرفته می‌شود.** مسیرهای شخصی از `Depends(get_current_user_id)` استفاده می‌کنند و `from_user` ارسالی در like مبنای هویت نیست. در تست زنده، پنج GET خصوصی بدون توکن 401 دادند.
3. **خروجی عمومی whitelist دارد.** `public_view` اطلاعات تماس را برنمی‌گرداند؛ مسیر squad خصوصی بعد از بررسی mutual آن‌ها را اضافه می‌کند. در پاسخ زندهٔ پروفایل نمونه، نام کلیدهای IGN، Discord، email و user_id وجود نداشت.
4. **رندر ورودی‌ها عموماً محتاطانه است.** در templateهای بررسی‌شده، نام، bio، متن دلایل و داده‌های فرم با `esc()` یا `textContent` رندر می‌شوند؛ لینک شبکه‌های اجتماعی روی دامنهٔ ثابت ساخته می‌شود. XSS قابل‌بهره‌برداری تأیید نشد. این نتیجه جای تست مرورگر با دادهٔ staging را نمی‌گیرد.
5. **مدل بازی‌ها داده‌محور است.** `games.py` به‌خوبی گزینه‌ها، وزن‌ها و فیلترها را متمرکز کرده است. تفکیک `locations.py` نیز مفید است.
6. **محدودیت جامعهٔ کوچک در UX دیده شده است.** حذف حداقل امتیاز، empty state با دعوت دوست و Looking now، بهتر از نمایش یک صفحهٔ بی‌پاسخ است. پنهان‌کردن شمارش کم، به‌تنهایی ضعف نیست.
7. **جزئیات کاربردی وجود دارد.** copy اطلاعات تماس، انتظار برای mutual، حالت background polling، خطاهای فرم، 404 با لحن مناسب و بازیابی پروفایل از سرور، برای یک پروژهٔ فردی نکات مثبتی‌اند.
8. **پایهٔ رابط سبک است.** نبود framework و build step برای این اندازه مزیت است. مجموع سه JS محلی حدود 82KB و سه CSS حدود 71KB پیش از فشرده‌سازی است؛ در حال حاضر بازنویسی با React ضرورت ندارد.

## یافته‌های High

### H01 — اطلاعات خصوصی حساب قبلی بعد از Logout برای حساب بعدی باقی می‌ماند

**شواهد: کد + بازتولید آفلاین + تأیید در مرورگر زنده با حساب‌های A/B.** محل: [ui.js:52](<G:/Claude code/PlayMate/static/js/ui.js:52>)، [ui.js:509](<G:/Claude code/PlayMate/static/js/ui.js:509>)، [ui.js:603](<G:/Claude code/PlayMate/static/js/ui.js:603>).

`playmate_shared` شامل Discord، شهر، کشور، زبان و mic است، اما `clearAuthAndRedirect` آن را حذف نمی‌کند. این cache به user_id نیز وابسته نیست. کاربر A روی دستگاه مشترک خارج می‌شود؛ کاربر B که پروفایل دیگری ندارد وارد می‌شود؛ فرم بازی جدید B اطلاعات A را از همان cache پر می‌کند. اگر B فرم را ذخیره کند، Discord متعلق به A می‌تواند در پروفایل B ذخیره و بعد به squadmates او نمایش داده شود. آزمون آفلاین تأیید کرد کلید خصوصی پس از logout باقی می‌ماند.

**پیشنهاد:** cache مشترک را با user_id نام‌گذاری و هنگام تغییر حساب پاک کنید؛ پاک‌کردن `playmate_shared`، `pm_ref` و cacheهای مربوط به حساب را در یک مسیر واحد قرار دهید. برای پیش‌پرکردن از پروفایل صاحب فعلی در سرور استفاده کنید. logout فعلی همچنین `supabase.auth.signOut()` را فراخوانی نمی‌کند؛ حذف localStorage به‌تنهایی refresh token را در سرور باطل نمی‌کند. تست A→logout→B باید شرط انتشار باشد.

### H02 — پاسخ بازی قبلی می‌تواند وضعیت بازی جدید را خراب کند

**شواهد: کد + بازتولید آفلاین ترتیب پاسخ‌ها؛ پنجرهٔ UI قدیمی در تعویض بازی زنده نیز دیده شد.** محل: [ui.js:363](<G:/Claude code/PlayMate/static/js/ui.js:363>)، [ui.js:488](<G:/Claude code/PlayMate/static/js/ui.js:488>)، [ui.js:580](<G:/Claude code/PlayMate/static/js/ui.js:580>)، [ui.js:797](<G:/Claude code/PlayMate/static/js/ui.js:797>)، [ui.js:1036](<G:/Claude code/PlayMate/static/js/ui.js:1036>).

`selectGame` و `loadProfileForGame` بعد از `await` اطمینان نمی‌دهند که درخواست هنوز متعلق به انتخاب فعلی است. در تست حافظه‌ای، پاسخ GTA زودتر رسید و سپس پاسخ Battlefield، `state.profile` را به Battlefield برگرداند، در حالی که `state.game` هنوز GTA بود. درخواست metadata نیز همین خطر را دارد. کاربر ممکن است فرم یک بازی را زیر نام بازی دیگر ببیند و با همان ترکیب ذخیره کند.

در like نیز game برای ادامهٔ عملیات و callback تأخیری ثابت نشده است؛ پاسخ یا timer بازی قبلی می‌تواند modal یا index کارت بازی جدید را تغییر دهد. `toggleLooking` هم پاسخ قبلی را در `state.profile` فعلی می‌نویسد. وجود محافظ game در `findMatches` و `refreshPending` خوب است، اما همهٔ زنجیره‌ها را پوشش نمی‌دهد.

**پیشنهاد:** برای هر انتخاب یک generation/request id بسازید؛ game و profile مربوط به عملیات را در آغاز ثابت بگیرید و پس از هر await و پیش از هر تغییر UI تطبیق دهید. درخواست قبلی را با AbortController لغو کنید. timerهای swipe را نیز با همان generation کنترل کنید. محافظ باید در success، error و finally اعمال شود.

### H03 — یکتایی و ثبات username در سطح حساب اتمیک نیست

**شواهد: کد؛ دامنهٔ اثر وابسته به schema واقعی است.** محل: [main.py:403](<G:/Claude code/PlayMate/main.py:403>)، [main.py:416](<G:/Claude code/PlayMate/main.py:416>)، [main.py:477](<G:/Claude code/PlayMate/main.py:477>)، [main.py:217](<G:/Claude code/PlayMate/main.py:217>)، [main.py:489](<G:/Claude code/PlayMate/main.py:489>).

نام حساب از اولین ردیف `profiles` استخراج می‌شود؛ انتخاب نام، بررسی اشغال‌بودن و درج سه عمل جدا هستند. طبق history، قید نام به game وابسته بوده است. دو کاربر می‌توانند هم‌زمان برای دو بازی متفاوت، یک نام یکسان را قبل از درج دیگری بررسی کنند. یکتایی `(username, game)` جلوی این سناریو را نمی‌گیرد. سپس `user_id_for_username(...).limit(1)` می‌تواند مالک دلخواهی را برای صفحهٔ عمومی، block یا referral انتخاب کند. همچنین با حذف آخرین game profile، نام قفل‌شده از بین می‌رود و قابل‌تغییر یا تصاحب مجدد می‌شود.

**پیشنهاد:** هویت را در جدول مستقل حساب با `user_id` یکتا و `canonical_username` یکتای سراسری ثبت و رزرو کنید؛ game profile فقط FK به حساب داشته باشد. انتخاب نام در یک عملیات اتمیک انجام شود و پس از حذف بازی‌ها باقی بماند. وجود trigger یا قید اضافی در production بررسی شود؛ بدون schema آن را نبودِ قطعیِ constraint اعلام نمی‌کنم، اما کد به‌تنهایی invariant اعلام‌شده را تضمین نمی‌کند.

## یافته‌های Medium

### M01 — فیلتر سازگاری از API دور زده می‌شود و مدل GTA نسخهٔ بازی را نمی‌شناسد

**شواهد: bypass از کد/آفلاین؛ صحت فیلتر برای پلتفرم و edition معتبر در مرورگر زنده؛ منبع رسمی بازی.** محل: [main.py:440](<G:/Claude code/PlayMate/main.py:440>)، [games.py:176](<G:/Claude code/PlayMate/games.py:176>)، [games.py:250](<G:/Claude code/PlayMate/games.py:250>).

frontend پلتفرم را لازم می‌داند، اما backend مقدار خالی یا نامعتبر را به `None` تبدیل و ذخیره می‌کند. `can_play_together` وقتی یکی از پلتفرم‌ها خالی باشد، محدودیت GTA/FC را اعمال نمی‌کند. آزمون آفلاین `GTA(None, Xbox) == True` و `GTA(PC, Xbox) == False` را تأیید کرد. مقادیر قدیمیِ بدون Minecraft edition/LoL server نیز با رویکرد unknown-never-block عبور می‌کنند؛ ذخیرهٔ جدید آن دو فیلد required را کنترل می‌کند.

حتی دو GTA profile معتبر با `platform=PC` ممکن است یکی Legacy و دیگری Enhanced باشد. مدل فعلی edition ندارد؛ Rockstar جدابودن این دو جامعه را تأیید می‌کند. [توضیح رسمی Rockstar](https://www.rockstargames.com/newswire/article/7551a7k917554a/free-upgrade-for-grand-theft-auto-v-on-pc-now-available).

**پیشنهاد:** در سرور پلتفرم الزامی و نامعتبر 422 شود. برای دادهٔ قدیمی سازگاری نامعلوم، از نمایش قطعی «قابل‌بازی» پرهیز و تکمیل پروفایل درخواست شود. برای GTA، edition/build بازی را جدا از خانوادهٔ سخت‌افزار مدل کنید و matrix نسخه‌های پشتیبانی‌شده را با منابع رسمی نگه دارید.

### M02 — محدودیت ۲۰ نتیجه و فیلتر پس از ۸۰۰ ردیف، کشف بازیکنان را متوقف می‌کند

**شواهد: کد.** محل: [main.py:619](<G:/Claude code/PlayMate/main.py:619>)، [main.py:622](<G:/Claude code/PlayMate/main.py:622>)، [main.py:657](<G:/Claude code/PlayMate/main.py:657>)، [ui.js:783](<G:/Claude code/PlayMate/static/js/ui.js:783>)، [main.py:728](<G:/Claude code/PlayMate/main.py:728>).

تنها ۲۰ نتیجه بازگردانده می‌شود؛ cursor و صفحهٔ بعد وجود ندارد. Skip فقط index حافظه را جلو می‌برد. کاربری که ۲۰ پیشنهاد اول را نمی‌پسندد، با Scan again همان‌ها را می‌گیرد و نفر ۲۱ را نمی‌بیند. بعد از رشد، اگر ۵۰۰ بازیکن نزدیک و ۳۰۰ دورِ انتخاب‌شده قبلاً like/block شده یا ناسازگار باشند، نتیجه می‌تواند خالی باشد، با وجود بازیکن مناسب قدیمی‌تر خارج از این پنجره. Looking now نیز فقط داخل همین پنجره اولویت می‌گیرد.

Pending likes فقط **ارسال‌شده‌ها** را نشان می‌دهد؛ دریافت‌کننده لزوماً نمی‌فهمد چه کسی او را پسندیده، به‌خصوص اگر فرستنده خارج از ۲۰ کارت او باشد. این چرخه می‌تواند mutual را دشوار کند.

**پیشنهاد:** حذف blocked/liked و hard filterها را تا حد ممکن پیش از limit در DB انجام دهید؛ pagination پایدار و راه دیدن پیشنهادهای بعدی اضافه کنید. Skip را حداقل در سطح session نگه دارید و incoming likes را با همان whitelist عمومی نمایش دهید. شمارش `total` را به‌عنوان شمارش داخل پنجره معرفی کنید، نه تعداد همهٔ بازیکنان مناسب دیتابیس.

### M03 — دوبار Skip چند کارت را بدون مشاهده رد می‌کند

**شواهد: بازتولید آفلاین + double-click زنده با تغییر شمارندهٔ ۴ به ۲.** محل: [ui.js:783](<G:/Claude code/PlayMate/static/js/ui.js:783>).

دو کلیک یا دو ArrowLeft در ۲۸۰ میلی‌ثانیه، دو callback می‌سازند؛ هر دو index را زیاد می‌کنند. کاربر فقط کارت اول را دیده، ولی کارت دوم هم رد می‌شود. callback قدیمی هنگام تغییر بازی نیز خطر مشابه دارد.

**پیشنهاد:** قفل مستقل swipe/animation قرار دهید، کنترل‌ها را فوراً غیرفعال کنید و callback را به شناسهٔ کارت و generation بازی وابسته کنید. در آزمون آفلاین دو فراخوانی سریع، index را دو واحد جلو برد.

### M04 — عملیات like و ذخیرهٔ پروفایل در برابر تکرار و رقابت مقاوم نیست

**شواهد: کد؛ رفتار duplicate وابسته به constraint دیتابیس است.** محل: [main.py:688](<G:/Claude code/PlayMate/main.py:688>)، [ui.js:1206](<G:/Claude code/PlayMate/static/js/ui.js:1206>)، [ui.js:622](<G:/Claude code/PlayMate/static/js/ui.js:622>).

like از الگوی select-then-insert استفاده می‌کند. دو تب می‌توانند هم‌زمان «وجود ندارد» ببینند؛ با unique constraint یکی خطا می‌دهد و بدون آن duplicate درج می‌شود. reverse-like نیز پیش از insert خوانده می‌شود؛ دو like متقابل هم‌زمان ممکن است هر دو ابتدا `liked` جواب دهند، اگرچه polling بعدی mutual را کشف می‌کند.

دکمهٔ Find Matches تا پایان `saveProfile` قفل نمی‌شود؛ قفل matching دیرتر فعال می‌شود. چند کلیک می‌تواند چند upsert، lookup و referral request هم‌زمان ایجاد کند.

**پیشنهاد:** unique constraint روی `(from_user_id,to_user_id,game)` را در migration تثبیت و insert را idempotent کنید؛ نتیجهٔ mutual را پس از ثبت یا در transaction/RPC محاسبه کنید. در UI کل زنجیرهٔ save→match از نخستین کلیک قفل شود و finally آن را آزاد کند.

### M05 — merge حساب و شمارندهٔ referral در رقابت، تغییرات را از دست می‌دهند

**شواهد: کد.** محل: [main.py:243](<G:/Claude code/PlayMate/main.py:243>)، [main.py:826](<G:/Claude code/PlayMate/main.py:826>)، [main.py:886](<G:/Claude code/PlayMate/main.py:886>)، [ui.js:1085](<G:/Claude code/PlayMate/static/js/ui.js:1085>).

merge از snapshot خوانده‌شدهٔ `app_metadata.playmate` انجام می‌شود. دو تب که هم‌زمان bio و avatar را تغییر دهند ممکن است snapshot قبلی را روی تغییر تازه بنویسند. دو referral هم‌زمان نیز هر دو n را خوانده و n+1 می‌نویسند؛ یکی از دعوت‌ها گم می‌شود. برعکس، دو درخواست برای یک invitee ممکن است قبل از ثبت `referred_by` هر دو مجاز شناخته شوند. ثبت referred_by و افزایش شمارنده نیز یک transaction نیست. کلاینت `pm_ref` را حتی پس از خطای شبکه حذف می‌کند.

**پیشنهاد:** referral را رویداد یکتا با قید invitee و شمارش اتمیک/مشتق‌شده ذخیره کنید؛ برای metadata از کنترل نسخه یا جدول account با update محدود به ستون استفاده کنید. فقط بعد از پاسخ موفق، referral محلی را پاک کنید. تا قبل از ضدتقلب، referral را مبنای جایزهٔ باارزش قرار ندهید.

### M06 — حذف حساب چندمرحله‌ای است و بدون game profile مسیر مدیریت حساب از دسترس خارج می‌شود

**شواهد: کد برای حالت شکست؛ حذف عادی A/B از UI و C از API موفق بود. حذف آخرین بازی C و باقی‌ماندن Auth همراه `username=null` از API تأیید شد. مسیر کامل دکمه‌های Remove در UI به‌علت native Confirm تأیید نشد؛ خطای production عمداً تزریق نشد.** محل: [main.py:489](<G:/Claude code/PlayMate/main.py:489>)، [main.py:863](<G:/Claude code/PlayMate/main.py:863>)، [main.py:915](<G:/Claude code/PlayMate/main.py:915>)، [profile.js:256](<G:/Claude code/PlayMate/static/js/profile.js:256>)، [profile.js:383](<G:/Claude code/PlayMate/static/js/profile.js:383>).

پنج حذف دیتابیس و سپس حذف Auth جدا انجام می‌شوند. اگر مرحله‌ای وسط کار شکست بخورد، rollback وجود ندارد؛ اگر حذف Auth شکست بخورد، داده‌ها قبلاً پاک شده‌اند. پیام سرور صادقانه است، ولی به support ارجاع می‌دهد که فعلاً راه تماس ندارد.

نام و صفحهٔ مالک نیز به وجود game profile وابسته‌اند. بعد از حذف آخرین بازی و reload، public-profile کاربر 404 می‌شود؛ Edit profile و دکمهٔ حذف حساب از این مسیر در دسترس نیستند. کاربری که ثبت‌نام کرده ولی هنوز اولین پروفایلش را نساخته نیز صفحهٔ مستقل تنظیمات ندارد. این انسداد مطلق نیست، چون می‌توان دوباره game profile ساخت، اما برای حذف حساب نباید چنین کاری لازم باشد.

در تست C، پس از حذف آخرین بازی، GET خصوصی account با همان session همچنان موفق بود ولی username تهی و games خالی داشت؛ GET عمومی 404 شد. حذف نهایی Auth از API همچنان ممکن بود و برای پاک‌سازی انجام شد. این تفاوت نشان می‌دهد backend قابلیت حذف حسابِ بدون بازی را دارد، اما مسیر دسترسی کاربر در UI باید مستقل از پروفایل عمومی باشد.

**پیشنهاد:** حذف داده‌های اپ را transaction کنید و برای هماهنگی با Auth فرایند قابل‌تکرارِ deletion-pending با retry داشته باشید. صفحهٔ Settings/Account مستقل از game profile بسازید؛ نام حساب را مستقل نگه دارید. referral باقی‌مانده در metadata دیگران و تعریف «تمام داده‌ها» نیز باید روشن شود؛ شمارندهٔ تاریخی را با ادعای حذف دادهٔ شخصی یکی نگیرید.

### M07 — JWT از نظر audience/issuer/وجود exp و وضعیت حساب کافی محدود نشده است

**شواهد: کد + مستندات رسمی؛ exploit زنده یا توکن واقعی استفاده نشد.** محل: [main.py:267](<G:/Claude code/PlayMate/main.py:267>)، [main.py:225](<G:/Claude code/PlayMate/main.py:225>)، [main.py:767](<G:/Claude code/PlayMate/main.py:767>).

امضای HS256 و انقضای claim موجود با PyJWT بررسی می‌شود؛ بنابراین «توکن بدون امضا پذیرفته می‌شود» یا «exp اصلاً کنترل نمی‌شود» صحیح نیست. مشکل این است که `verify_aud=False` است، issuer محدود نشده و وجود `exp` اجباری نیست. sub نیز فقط باید nonempty باشد. این‌ها نقص محدودسازی trust هستند، نه مدرک امکان ساخت توکن معتبر توسط کاربر عادی. [مستندات PyJWT](https://pyjwt.readthedocs.io/en/latest/api.html).

علاوه بر آن، اعتبارسنجی محلی JWT وضعیت حذف/تعلیق حساب را نمی‌خواند. Supabase توضیح می‌دهد JWT صادرشده تا exp معتبر می‌ماند. برای نمونه `/api/block` برخلاف like حتی game profile فعال را هم لازم ندارد. امکان درج پس از حذف به FK/config وابسته است و آزمایش نشده؛ اما رد فوری حساب تعلیق‌شده با کد فعلی تضمین نمی‌شود. [مستندات حذف کاربر Supabase](https://supabase.com/docs/guides/auth/managing-user-data).

**پیشنهاد:** audience مورد انتظار، issuer پروژه، `require` برای claimهای ضروری و قالب UUID برای sub را بررسی کنید. وضعیت حساب را برای عملیات حساس با یک منبع معتبر/فهرست ابطال مناسب کنترل کنید. migration به signing key جدید باید با اعتبارسنجی مطابق پیکربندی واقعی برنامه‌ریزی شود؛ HS256 ثابت را ناگهان تغییر ندهید.

### M08 — fan-out عمومی و polling، هزینهٔ بزرگی برای free tier ایجاد می‌کنند

**شواهد: شمارش مسیرهای کد؛ load test انجام نشد.** محل: [main.py:353](<G:/Claude code/PlayMate/main.py:353>)، [main.py:913](<G:/Claude code/PlayMate/main.py:913>)، [main.py:705](<G:/Claude code/PlayMate/main.py:705>)، [main.py:728](<G:/Claude code/PlayMate/main.py:728>)، [ui.js:1140](<G:/Claude code/PlayMate/static/js/ui.js:1140>).

`/api/games` برای هر بار بارگذاری، ۱۲ count مستقل و ترتیبی می‌زند. پروفایل عمومی شامل lookup حساب Auth و mutualهای هر بازی است؛ با ۱۲ بازی و outgoing likes می‌تواند حدود ۲۸ فراخوانی Supabase، با احتساب Auth lookup، ایجاد کند. هر درخواست عمومی این کار را دوباره انجام می‌دهد. rate limit یا cache در خود اپ دیده نشد؛ وجود محدودیت لایهٔ میزبان تأیید نشده است.

هر tick فعال سه درخواست ping/squad/pending می‌فرستد. بسته به داده، این‌ها حدود **۶ تا ۱۳ round trip به Supabase در هر ۱۵ ثانیه** دارند. برای ۱۰۰ کاربر فعال، مدل بالایی حدود **۵۲۰۰ فراخوانی در دقیقه** است؛ این تخمین از کد است، نه اندازه‌گیری ظرفیت سرور. hidden tab آهسته‌تر است که تصمیم خوبی است، اما همچنان هزینه دارد.

**پیشنهاد:** ابتدا count گروهی با cache کوتاه، endpoint تجمیعی state و کاهش queryهای تکراری mutual/blocked؛ سپس backoff، jitter و refresh پس از تغییر. rate limit روی endpointهای پرهزینه و عملیات abuse-sensitive اضافه شود. برای مقیاس بعدی SQL/RPC matching با pagination و index مناسب؛ تغییر به async به‌تنهایی تعداد فراخوانی‌ها را کم نمی‌کند.

### M09 — درخواست بدون deadline می‌تواند UI را قفل کند؛ خطای سرویس با «پیدا نشد» مخلوط می‌شود

**شواهد: کد.** محل: [ui.js:63](<G:/Claude code/PlayMate/static/js/ui.js:63>)، [ui.js:672](<G:/Claude code/PlayMate/static/js/ui.js:672>)، [main.py:225](<G:/Claude code/PlayMate/main.py:225>)، [profile.js:383](<G:/Claude code/PlayMate/static/js/profile.js:383>)، [landing.js:137](<G:/Claude code/PlayMate/static/js/landing.js:137>).

fetchهای کلاینت AbortController/deadline ندارند؛ درخواست معلق می‌تواند match یا like را تا timeout شبکه قفل نگه دارد. timeout کلاینت Supabase در سرور جای timeout کل عملیات UI را نمی‌گیرد؛ یک endpoint می‌تواند چند درخواست ترتیبی داشته باشد.

`auth_user` همهٔ exceptionها را به `None` تبدیل می‌کند؛ قطعی Auth به 404 «Account not found» یا پروفایل عمومی با دادهٔ پیش‌فرض تبدیل می‌شود. در save profile همین fallback ممکن است avatar کش‌شده را خالی کند. `loadGames` و public profile نیز همه‌جا `res.ok` را قبل از مصرف JSON کنترل نمی‌کنند. forgotPassword در خطای transport، catch و قفل دکمه ندارد.

**پیشنهاد:** خطاهای not-found، unauthorized، timeout و upstream failure را جدا کنید؛ 503 قابل‌تلاش مجدد بدهید. برای کل عملیات deadline و لغو، و برای mutationها retry فقط با idempotency بگذارید. خطای upstream نباید به دادهٔ پیش‌فرضی تبدیل شود که بعداً ذخیره می‌شود.

### M10 — وعدهٔ block از رفتار واقعی عمومی گسترده‌تر است

**شواهد: کد، مشاهدهٔ public profile/squad بدون ورود و بازکردن A از حساب C پس از block واقعی.** محل: [main.py:175](<G:/Claude code/PlayMate/main.py:175>)، [main.py:913](<G:/Claude code/PlayMate/main.py:913>)، [main.py:950](<G:/Claude code/PlayMate/main.py:950>)، [landing.html:224](<G:/Claude code/PlayMate/landing.html:224>).

فیلتر دوطرفه در match و squad خصوصی وجود دارد و across-game است. اما public-profile، `/profile-full` و `/profile-squad` viewer احراز‌شده را نمی‌شناسند. فرد مسدودشده می‌تواند URL عمومی را باز کند و پروفایل، وضعیت فعالیت و ارتباطات عمومی را ببیند. عمومی‌بودن این داده‌ها طبق سیاست فعلی intentional است؛ این مورد، نشت IGN/Discord نیست. مسئله ادعای «دیگر همدیگر را نمی‌بینید» و «everywhere» است که انتظار حریم خصوصی قوی‌تری ایجاد می‌کند.

**پیشنهاد:** تعریف block را دقیق بنویسید؛ برای viewer واردشده محدودیت مربوطه را در public API اعمال کنید و صادقانه توضیح دهید صفحهٔ عمومی همچنان برای بازدیدکنندهٔ ناشناس قابل‌دیدن است. گزینهٔ محدودسازی public profile، city، last active و نمایش squad را بررسی کنید؛ دادهٔ عمومی را پنهانی خصوصی معرفی نکنید.

### M11 — report یک پرچم قابل‌بازنویسی است؛ رسیدگی، unmatch و unblock کامل نیستند

**شواهد: کد؛ فرایند خارج از repository بررسی نشده است.** محل: [main.py:776](<G:/Claude code/PlayMate/main.py:776>)، [main.py:871](<G:/Claude code/PlayMate/main.py:871>)، [ui.js:1055](<G:/Claude code/PlayMate/static/js/ui.js:1055>)، [ui.js:937](<G:/Claude code/PlayMate/static/js/ui.js:937>).

ارسال report همان ردیف block را upsert می‌کند. درخواست block عادی بعدی برای همان کلید می‌تواند `reported=true` و reason قبلی را با false/None جایگزین کند. حذف حسابِ هر یک از طرف‌ها نیز ردیف‌های report مرتبط را حذف می‌کند. در repository صف رسیدگی، وضعیت پرونده یا ابزار moderation وجود ندارد. ذخیرهٔ report به‌تنهایی تضمین رسیدگی نیست.

در رابط، کنار squadmate فقط Block وجود دارد؛ کاربر برای پایان یک ارتباط عادی ابزار unmatch ندارد. فهرست blockedها و unblock هم وجود ندارد؛ اشتباه کاربر قابل‌اصلاح نیست.

**پیشنهاد:** گزارش تخلف را از رابطهٔ block جدا و رویداد آن را ثبت کنید؛ block عادی نباید آن را پس بگیرد. حداقل یک فرایند مالک‌محور برای مشاهده، رسیدگی و ثبت نتیجه و راه تماس بسازید. سیاست نگهداری/حذف گزارش‌ها را روشن کنید. unmatch و مدیریت blockedها را با سرور و UI هماهنگ اضافه کنید.

### M12 — در حالت بازیابی رمز، دکمهٔ Sign up همچنان مسیر تغییر رمز را اجرا می‌کند

**شواهد: بازتولید آفلاین.** محل: [landing.js:70](<G:/Claude code/PlayMate/static/js/landing.js:70>)، [landing.js:85](<G:/Claude code/PlayMate/static/js/landing.js:85>)، [landing.js:145](<G:/Claude code/PlayMate/static/js/landing.js:145>).

پس از event بازیابی، `recovering=true` می‌ماند. کاربر می‌تواند tab ثبت‌نام را بزند و عنوان/دکمه را «Create account» ببیند، ولی handleAuth قبل از بررسی mode مستقیماً `saveNewPassword()` را اجرا می‌کند. در تست آفلاین، recovery→signup دقیقاً وارد شاخهٔ تغییر رمز شد. این hijack حساب نیست؛ ناسازگاری پرخطر میان متن دکمه و عمل حساس کاربر است. تبادل واقعی ایمیل و رمز زنده آزمایش نشد.

**پیشنهاد:** recovery را صفحه/حالت مجزا کنید؛ toggleهای auth را در آن حذف یا کنترل کنید و خروج از recovery را صریح انجام دهید. دکمهٔ ذخیره و فرایند بازیابی نیز قفل، catch و پیام نتیجه داشته باشد.

### M13 — دسترس‌پذیری ظاهری شروع خوبی دارد، ولی semantics و مدیریت focus ناقص‌اند

**شواهد: HTML/JS و مشاهدهٔ مرورگر؛ آزمون کامل screen reader انجام نشد.** محل: [ui.js:440](<G:/Claude code/PlayMate/static/js/ui.js:440>)، [ui.js:986](<G:/Claude code/PlayMate/static/js/ui.js:986>)، [profile.js:129](<G:/Claude code/PlayMate/static/js/profile.js:129>)، [profile.js:230](<G:/Claude code/PlayMate/static/js/profile.js:230>)، [profile.html:86](<G:/Claude code/PlayMate/profile.html:86>)، [landing.css:272](<G:/Claude code/PlayMate/static/css/landing.css:272>).

modalها role و aria-modal دارند، اما focus به آن‌ها منتقل/محصور و پس از بستن بازگردانده نمی‌شود. language pills وضعیت `aria-pressed` ندارند. tabهای auth/profile در کد صرفاً class می‌گیرند؛ `aria-selected`، ارتباط panel و الگوی Arrow-key کامل ندارند. textarea Bio نام متصل‌شده ندارد؛ دکمه‌های انتخاب avatar/banner با تصویر alt خالی نام قابل‌فهم ندارند. toast اپ live region ندارد. label دکمهٔ نمایش رمز بعد از تغییر حالت همچنان «Show password» است.

متن‌های hint/footer با `--faint` کوچک و کم‌رنگ‌اند؛ نسبت نمونهٔ رنگ `#5d6e7b` روی panel تیره حدود ۳ تا ۳٫۵ است، بسته به ترکیب واقعی زمینه، و باید دقیق روی حالت‌های واقعی اندازه‌گیری شود. برای متن معمولی حداقل مرجع ۴٫۵:۱ است. [WCAG 2.2، معیار کنتراست](https://www.w3.org/TR/WCAG22/#contrast-minimum).

**پیشنهاد:** مدیریت focus و inert پس‌زمینه، labelهای متصل، stateهای ARIA و live region اضافه شود؛ رنگ متن راهنما و اندازهٔ آن بازبینی شود. focus-visible و prefers-reduced-motion موجود نکات مثبت‌اند؛ audit را به ادعای نبود کامل دسترس‌پذیری تبدیل نکنید.

### M14 — انتشار قابل‌بازتولید و تضمین invariantهای دیتابیس در repository وجود ندارد

**شواهد: repository.** محل: [requirements.txt:1](<G:/Claude code/PlayMate/requirements.txt:1>)، [main.py:477](<G:/Claude code/PlayMate/main.py:477>)، [keepalive.yml:1](<G:/Claude code/PlayMate/.github/workflows/keepalive.yml:1>).

وابستگی‌های Python بدون pin/lock هستند؛ نصب یک commit ثابت الزاماً همان نسخه‌های قبلی را نمی‌سازد. migration/schema/RLS قابل‌بازبینی و مجموعه تست خودکار یافت نشد؛ تنها workflow موجود keepalive است. این نقص، آسیب‌پذیری شناخته‌شدهٔ یک نسخهٔ خاص را ثابت نمی‌کند، ولی تشخیص regression و بازسازی محیط را دشوار می‌کند. با service key، RLS جایگزین کنترل دسترسی backend هم نیست.

**پیشنهاد:** نسخه‌های تست‌شده و lock ثبت شود؛ migration شامل unique/FK/index/RLS و تست آن اضافه شود. CI ابتدا syntax و تست‌های خالص، سپس API با Supabase جعلی/دیتابیس تست مستقل اجرا کند. هرگز `.env` فعلی را برای تست integration بارگذاری نکنید. با توجه به auto-deploy روی main، شکست CI باید جلوی انتشار را بگیرد.

### M15 — چند پیش‌نیاز اعتماد و حفاظت عمومی هنوز باز است

**شواهد: مرورگر + کد + تنظیم اعلام‌شده در brief؛ سه ثبت‌نام زنده بدون مرحلهٔ تأیید ایمیل.** محل: [legal.html:63](<G:/Claude code/PlayMate/legal.html:63>)، [legal.html:84](<G:/Claude code/PlayMate/legal.html:84>)، [main.py:54](<G:/Claude code/PlayMate/main.py:54>)، [main.py:289](<G:/Claude code/PlayMate/main.py:289>)، [profile.html:130](<G:/Claude code/PlayMate/profile.html:130>).

Terms و Privacy واقعاً Draft هستند و راه تماس عملی برای support/حقوق artwork دیده نمی‌شود. سه ثبت‌نام زنده روی ایمیل‌های ساختگی بدون دریافت/تأیید ایمیل وارد حساب شدند، مطابق اعلام مالک دربارهٔ خاموش‌بودن confirmation؛ خود dashboard دیده نشد. همراه با فقدان محدودیت abuse در اپ، حساب‌سازی و دست‌کاری referral/like آسان‌تر می‌شود. سرویس Auth ممکن است محدودیت‌های مستقل داشته باشد؛ آن‌ها را نباید نبودِ کامل rate limit دانست.

در پاسخ زندهٔ `/` و APIهای نمونه، CSP، X-Frame-Options، X-Content-Type-Options، Referrer-Policy و HSTS مشاهده نشد. این نتیجه از HTTP واقعی است، نه صرفاً نبود middleware. API خصوصی نیز سیاست صریح `Cache-Control: no-store` ندارد؛ کش‌شدن واقعی اطلاعات خصوصی در این بررسی اثبات نشد. SDK از CDN نسخه‌دار بارگذاری می‌شود، ولی integrity ندارد و CSP هم از آن محافظت نمی‌کند.

**پیشنهاد:** پیش از دعوت عمومی، سیاست‌ها و تماس واقعی را تکمیل و confirm email را با مسیر تأیید/ارسال مجدد و recovery در staging تست کنید. هدرهای محافظ را با CSP ابتدا در Report-Only و سازگار با inline scriptهای موجود اضافه کنید؛ برای پاسخ خصوصی no-store تعیین کنید. SDK را self-host یا با integrity مناسب مدیریت کنید. CORS باز در کد/نمونهٔ پاسخ دیده نشد؛ برای اپ هم‌مبدأ، اضافه‌کردن wildcard CORS لازم نیست.

## یافته‌های Low

### L01 — درصد match یک احتمال یا مقیاس نرمال‌شده نیست

**شواهد: کد + تست آفلاین.** محل: [main.py:567](<G:/Claude code/PlayMate/main.py:567>)، [ui.js:731](<G:/Claude code/PlayMate/static/js/ui.js:731>).

امتیاز جمع وزن‌ها و cap است. مثلاً حداکثر CS2 با دو زبان مشترک، کشور/شهر مشترک، mic و fields یکسان **۹۷** می‌شود؛ Battlefield می‌تواند از ۱۰۰ خام عبور و cap شود. این به‌تنهایی باگ ranking نیست، ولی «۹۷٪» میان بازی‌ها یا احتمال موفقیت واقعی قابل‌مقایسه نیست. مقادیر `Any` در fieldهای `match=same` نیز wildcard محسوب نمی‌شوند؛ برای نمونه Helldivers front=Any با Terminids امتیاز آن field را نمی‌گیرد.

**پیشنهاد:** عبارت Compatibility score و توضیح روش، یا نرمال‌سازی مشخص بر وزن‌های قابل‌اعمال؛ semantics مقادیر flexible را برای هر field صریح کنید. کشور محل سکونت را نیز با server region یکی نگیرید: کاربر ایرانیِ بازی‌کننده روی EU فعلاً نمی‌تواند EU و Iran را هم‌زمان انتخاب کند، چون country تابع region است. این تصمیم مدل باید با واقعیت مخاطبان هدف ارزیابی شود.

### L02 — تب چهارم پروفایل در موبایل ۳۲۰ پیکسل از دید خارج می‌شود

**شواهد: مرورگر در عرض ۳۲۰.** محل: [profile.css:758](<G:/Claude code/PlayMate/static/css/profile.css:758>).

صفحه سرریز کلی نداشت، ولی tab strip اسکرول افقی گرفت و Squad خارج از نمای اولیه بود؛ با وجود comment کد که می‌گوید هر چهار تب بدون اسکرول جا می‌شوند. در ۳۹۰ این مشکل دیده نشد.

**پیشنهاد:** اندازه و فاصلهٔ تب‌ها را با ترجمه/نام‌های طولانی و عرض ۳۲۰ تست کنید؛ حذف Highlights فعلاً فضای مفیدی آزاد می‌کند. معیار پذیرش را با عرض‌های مشخص بنویسید.

### L03 — انتخاب بازی و نیت کاربر هنگام رفتن به ثبت‌نام گم می‌شود

**شواهد: مسیر زنده + کد.** محل: [profile.js:160](<G:/Claude code/PlayMate/static/js/profile.js:160>)، [ui.js:1280](<G:/Claude code/PlayMate/static/js/ui.js:1280>)، [landing.js:17](<G:/Claude code/PlayMate/static/js/landing.js:17>)، [landing.js:174](<G:/Claude code/PlayMate/static/js/landing.js:174>).

از public profile روی «Find a squad in this game» کلیک شد؛ `/app?game=battlefield` کاربر مهمان را به `/` بدون game یا return path برگرداند. login نیز همیشه به `/app` می‌رود. کارت بازی روی landing هم فقط signup را باز می‌کند و بازی انتخابی را حمل نمی‌کند. در نتیجه کاربر دوباره انتخاب می‌کند؛ اگر هدف او ارتباط با همان فرد بوده، آن هدف هم منتقل نمی‌شود.

**پیشنهاد:** return path محدود به مسیر امن داخلی و game منتخب را در جریان auth حفظ کنید؛ متن CTA مشخص کند «بازیکنان این بازی» را باز می‌کند یا درخواست به این شخص می‌فرستد. کاربر را به تصور ارسال درخواست شخصی نیندازید.

### L04 — اشتراک‌گذاری پروفایل و status صفحه برای crawlerها ضعیف است

**شواهد: کد + browser missing-profile.** محل: [profile.html:8](<G:/Claude code/PlayMate/profile.html:8>)، [main.py:310](<G:/Claude code/PlayMate/main.py:310>)، [profile.js:383](<G:/Claude code/PlayMate/static/js/profile.js:383>).

همهٔ public profileها HTML عمومی یکسان با title ثابت اولیه و بدون OG اختصاصی می‌گیرند؛ title بعداً با JS تغییر می‌کند. username ناموجود نیز ابتدا HTML با 200 می‌گیرد و بعد پیام client-side «Player not found». preview لینک در Discord و موتورهای بدون اجرای JS اطلاعات خاص بازیکن را نمی‌گیرد.

**پیشنهاد:** حداقل title/description/OG امن و status درست پروفایل را سمت سرور تولید کنید. ابتدا حریم خصوصی و رضایت نمایش عمومی را تعیین کنید؛ برای این کار نیازی به مهاجرت کل frontend نیست.

### L05 — بخش‌های Coming soon و متن‌های مطلق از اعتماد کم می‌کنند

**شواهد: مرورگر + کد.** محل: [profile.js:181](<G:/Claude code/PlayMate/static/js/profile.js:181>)، [main.py:252](<G:/Claude code/PlayMate/main.py:252>)، [landing.js:77](<G:/Claude code/PlayMate/static/js/landing.js:77>)، [ui.js:770](<G:/Claude code/PlayMate/static/js/ui.js:770>).

Highlights تب کاملی با شش جای خالی دارد؛ دو badge و upload نیز ناتمام‌اند. عبارت «Takes 20 seconds» فقط ایجاد حساب را توصیف می‌کند و برای رسیدن به بازی واقعی قابل‌اتکا نیست. «Add to squad» قبل از mutual، نتیجه‌ای قوی‌تر از عمل واقعی یعنی ارسال like القا می‌کند. همچنین IGN و Discord هر دو اختیاری‌اند؛ دو نفر می‌توانند match شوند و هیچ راه تماس در محصول نداشته باشند.

**پیشنهاد:** Highlights و badgeهای نمایشی ناتمام را فعلاً از مسیر اصلی بردارید؛ قبل از mutual از Like/Send request استفاده کنید. در مسیر match، نبود راه تماس را روشن و تکمیل حداقل یکی از روش‌ها را پیشنهاد کنید. وعدهٔ زمان رسیدن به squad را پس از اندازه‌گیری واقعی بازنویسی کنید.

### L06 — اسکریپت محلی تشخیصی هنوز می‌تواند service key را چاپ کند

**شواهد: تحلیل AST بدون اجرای اسکریپت یا خواندن `.env`.** محل: [test_env.py:13](<G:/Claude code/PlayMate/test_env.py:13>)، [.gitignore:12](<G:/Claude code/PlayMate/.gitignore:12>).

فایل محلی `test_env.py` وجود دارد و print روی `os.getenv("SUPABASE_KEY")` دارد. فایل ignore شده و مدرکی از انتشار فعلی کلید ندارم؛ اما اجرای دستی و کپی log می‌تواند راز production را افشا کند. فایل در این بررسی اجرا نشد و هیچ مقداری از کلید خوانده نشد.

**پیشنهاد:** در آینده فقط وجود/عدم‌وجود تنظیم را گزارش کند و credential را چاپ نکند. rotation کلیدهای واقعاً افشاشدهٔ گذشته از روی داشبورد تأیید شود؛ این گزارش افشای جدیدی را اثبات نمی‌کند.

### L07 — جزئیات modal و کنترل ایمنی در بعضی محیط‌ها ضعیف‌تر از بقیهٔ رابط‌اند

**شواهد: کد + مشاهدهٔ زنده؛ محدودیت Report مربوط به مرورگر این بررسی است.** محل: [ui.js:813](<G:/Claude code/PlayMate/static/js/ui.js:813>)، [ui.js:891](<G:/Claude code/PlayMate/static/js/ui.js:891>)، [ui.js:1058](<G:/Claude code/PlayMate/static/js/ui.js:1058>)، [ui.css:802](<G:/Claude code/PlayMate/static/css/ui.css:802>).

در LIKE SENT، حساب A روی کارت avatar انتخابی داشت، اما در modal حرف اولیه نشان داده شد؛ آبجکت `mate` در بعضی مسیرها avatar را به renderer نمی‌رساند. در موبایل، نام‌های بلند مشابه کوتاه می‌شوند و IGN بلند در چند خط باریک می‌شکند. placeholder قفل‌شدهٔ `Operator_Name_BF` هم از CSS وارد accessibility tree می‌شود، حتی برای بازی‌های غیر Battlefield؛ این نام، دادهٔ خصوصی واقعی بازیکن نیست.

Report از `window.prompt` استفاده می‌کند؛ در مرورگر داخل برنامهٔ این بررسی با خطای عدم پشتیبانی متوقف شد. این شکست را به Chrome/Safari معمولی تعمیم نمی‌دهم، ولی برای کنترل ایمنی حیاتی، یک فرم HTML در خود اپ، رفتار قابل‌اتکاتر و قابل‌دسترس‌تری دارد.

**پیشنهاد:** avatar را همراه mate عبور دهید؛ نام کامل را در جای قابل‌خواندن نگه دارید و چیدمان contact بلند را تست کنید. placeholder تزئینی را از accessibility tree حذف کنید؛ report/block را به dialog خود اپ با label، مدیریت focus و خطای inline منتقل کنید.

## نتیجهٔ تست‌های انجام‌شده

| بررسی | نتیجه و محدودیت |
|---|---|
| landing دسکتاپ 1440×900 | پیام اصلی، دو ستون، CTA و auth card قابل‌استفاده و منسجم |
| landing/signup موبایل 390×844 | CTA ثبت‌نام را باز کرد؛ فرم خوانا بود؛ سرریز افقی کلی دیده نشد |
| فرم خالی login و Forgot password | خطای محلی واضح نمایش داده شد؛ auth request ارسال نشد |
| `/u/pouriya` دسکتاپ و 390 | اطلاعات عمومی، بازی، badge و tabها بارگذاری شدند؛ خطای warn/error در نمونهٔ console دیده نشد |
| public Squad و Highlights | squad عمومی بدون اطلاعات تماس نشان داده شد؛ Highlights واقعاً placeholder است |
| public profile عرض 320 | صفحه جا شد؛ tab strip اسکرول گرفت و Squad خارج از نمای اولیه بود |
| Terms و Privacy | قابل‌دسترسی و صریحاً Draft؛ راه تماس عملی دیده نشد |
| URL ناموجود | 404 اختصاصی با راه برگشت؛ public username ناموجود پیام مناسب JS داشت |
| `/health` | 200؛ فقط سلامت سبک، نه اثبات سلامت تمام وابستگی‌ها |
| پنج GET خصوصی بدون token | my-profile، account، my-games، my-squad-details و pending-likes همگی 401 |
| public-profile نمونه | 200؛ در JSON، کلیدهای IGN/Discord/email/user_id/app_metadata نبودند |
| REST ناشناس profiles/likes/blocks | هر سه 200 با آرایهٔ خالی برای `select=id&limit=1`؛ سازگار با عدم مشاهدهٔ ردیف ناشناس، نه اثبات کل policyهای RLS یا رفتار نقش authenticated |
| هدرهای HTTP | HTML اصلی `Cache-Control: no-cache` داشت؛ هدرهای محافظ ذکرشده در پاسخ‌های نمونه مشاهده نشد |
| ۱۲ آزمون Python آفلاین | hard filterهای شناخته‌شده، bypass مقدار نامعلوم، lookup کشور، required fields، whitelist و scoring بررسی شدند؛ همگی مطابق انتظار آزمون بودند |
| ۴ سناریوی JavaScript حافظه‌ای | باقی‌ماندن cache بعد logout، double-skip، پاسخ قدیمی profile و شاخهٔ اشتباه recovery بازتولید شدند؛ هیچ مرورگر یا backend واقعی درگیر این سناریوها نبود |
| بررسی syntax | `node --check` برای سه JS و AST parse برای main/games/locations/gen_art موفق بود؛ این‌ها integration test نیستند |

برای نمونهٔ تک‌درخواست، `/api/games` حدود **۰٫۷۷ ثانیه** و public-profile حدود **۰٫۳۵ ثانیه** طول کشید؛ این نمونه‌ها از یک مسیر شبکه‌اند، benchmark، p95، cold-start یا اندازه‌گیری Core Web Vitals نیستند. تست فشار production انجام نشد.

## نقد تجربهٔ کاربر و محصول

### آیا من به‌عنوان کاربر جذب می‌شوم؟

برای گیمر فارسی‌زبان که دنبال هم‌تیمی با mic و زبان مشترک است، پیام اصلی قابل‌فهم است. ظاهر landing و public profile برای یک MVP اعتماد اولیه ایجاد می‌کند. دلیل‌های match و قفل اطلاعات تماس نسبت به یک فهرست username ارزش بیشتری دارند. انگلیسی‌بودن UI طبق تصمیم پروژه عمدی است و به‌خودی‌خود ایراد محسوب نمی‌شود.

اما دلیل بازگشت کاربر، تعداد بازی‌ها یا افکت match نیست؛ **پیداکردن فرد مناسب که واقعاً جواب بدهد و بتوان با او بازی کرد** است. در جامعهٔ بسیار کوچک، احتمال نتیجهٔ خالی یا انتظار برای like متقابل مهم‌ترین ریسک است. دعوت دوست مفید است، ولی اگر محصول برای مفیدشدن همیشه از کاربر بخواهد دوستش را از Discord بیاورد، باید ارزش اضافهٔ خودش را روشن‌تر نشان دهد.

انتشار هم‌زمان ۱۲ بازی، جامعهٔ حدود پنج‌پروفایلی را به poolهای کوچک‌تری تقسیم می‌کند. پیشنهاد محصولی من، تمرکز معرفی و onboarding روی Battlefield و یک کامیونیتی مشخص فارسی‌زبان است؛ بازی‌های دیگر می‌توانند باقی بمانند، اما نباید تمرکز جذب و پشتیبانی را بگیرند. برای شروع، رویدادهای هماهنگ «الان دنبال squad هستیم» در زمان‌های مشخصِ کامیونیتی می‌تواند به density کمک کند؛ این پیشنهاد افزودن فیلد اجباری زمان بازی به پروفایل نیست.

### چه چیزهایی بیشترین اثر را دارند؟

1. incoming likes و راه برگشت به بازیکن علاقه‌مند، برای کامل‌شدن چرخهٔ mutual.
2. راه مطمئن تماس بعد match؛ تشخیص پروفایل بدون هیچ contact و متن دقیق دربارهٔ مرحلهٔ بعد.
3. اعلان خارج از تب پس از آماده‌شدن زیرساخت و رضایت کاربر؛ polling فقط وقتی سایت باز است برای retention کافی نیست. chat کامل الزام فوری نیست.
4. Settings مستقل، unmatch، unblock و رسیدگی واقعی به report؛ این‌ها از badge جدید ضروری‌ترند.
5. شفافیت دربارهٔ Early access، اطلاعات عمومی، وضعیت آنلاین و محدودیت block. حالت Looking now به معنای حضور زندهٔ تضمینی نیست.
6. جداکردن محل سکونت از server/region بازی، متناسب با کاربران ایرانی و مهاجر.
7. اندازه‌گیری مسیر landing→signup→profile→like→mutual→بازی واقعی، با حداقل دادهٔ لازم و بدون ذخیرهٔ اطلاعات تماس در analytics. معیار موفقیت مهم، زمان تا اولین **بازی موفق با هم‌تیمی** و نرخ بازگشت هفتگی است، نه تعداد حساب خام.

### چه چیزهایی را فعلاً حذف یا عقب بیندازم؟

Highlights، upload تصویر، Verified/Legendary نمایشی، wallet/store/subscription و اپ موبایل مستقل را عقب بیندازید. moderation و هزینهٔ این امکانات با اندازهٔ فعلی جامعه تناسب ندارد. سیستم notification و کشف متقابل، اولویت بیشتری از chat کامل دارد. بازنویسی framework و microservice نیز فعلاً ارزش اصلی ایجاد نمی‌کند.

## ساختار کد و ترتیب اصلاح پیشنهادی

`main.py` و `ui.js` با وجود طول زیاد هنوز نام‌گذاری و بخش‌بندی قابل‌فهمی دارند. مشکل اصلی «تعداد خط» نیست؛ ترکیب قواعد هویت، دسترسی، فراخوانی شبکه و state رابط در مسیرهایی است که تست مستقل ندارند. shared auth/token/escaping/avatar logic بین سه JS تکرار شده و رفتار خروج/refresh در آن‌ها یکسان نیست.

ترتیب پیشنهادی:

1. **پیش از دعوت بعدی:** H01 و H02، سپس تضمین username و تست A/B؛ رفع validation پلتفرم، recovery و idempotency کلیک/like.
2. **پیش از جذب عمومی:** Settings مستقل، report/moderation، سیاست و تماس، confirm email با تست واقعی staging، هدرها و محدودیت abuse؛ incoming likes و pagination.
3. **برای رشد:** cache شمارش، endpoint تجمیعی polling، SQL matching، schema/indexهای نسخه‌دار، مانیتور نرخ 5xx و latency؛ فقط سپس بهینه‌سازی‌های بزرگ‌تر.

برای refactor، ابتدا scoring و compatibility را pure نگه دارید، سپس repository دیتابیس و سرویس account/likes را جدا کنید؛ routeها به فایل‌های auth/profiles/matches/safety تقسیم شوند. در frontend یک لایهٔ مشترک auth/API و controller برای انتخاب بازی با request generation بسازید. تغییر ساختار باید با تست رفتار همراه باشد، نه صرفاً جابه‌جایی فایل‌ها.

اولین تست‌های ارزشمند در staging یا با fake DB:

- ماتریس مالک/غریبه/mutual/blocked برای تمام خروجی‌ها؛ عدم افشای IGN/Discord/email، از جمله endpointهای legacy.
- دو حساب روی یک مرورگر، خروج در یک تب و تغییر حساب در تب دیگر؛ پاک‌سازی cache و refresh token.
- ترتیب معکوس پاسخ metadata/profile/like/looking در تعویض بازی؛ هیچ state قدیمی نباید وارد بازی جدید شود.
- رقابت انتخاب نام، درج like متقابل، تکرار درخواست و referral هم‌زمان.
- تمام hard filterها، پلتفرم خالی/نامعتبر، دادهٔ قدیمی نامعلوم، وزن نقش متفاوت و مقادیر flexible.
- بیش از ۲۰ نتیجه، بیش از ۸۰۰ candidate و حالتی که همهٔ ردیف‌های پنجره hidden هستند.
- تزریق خطا پس از هر مرحلهٔ حذف، retry، حذف آخرین بازی و دسترسی مستقل به Settings.
- auth نامعتبر/منقضی، audience/issuer اشتباه، نبود exp و حساب تعلیق‌شده؛ بدون استفاده از secret واقعی در تست.
- سفر کامل دو کاربر staging از ثبت‌نام تا mutual و تماس، در دسکتاپ و موبایل؛ سپس screen reader/keyboard.

## امتیازدهی

این امتیاز پس از دور دومِ تست واقعی با سه حساب به‌روز شده است؛ تأیید امنیت، دسترس‌پذیری یا ظرفیت production نیست. اطمینان به کارکرد چرخهٔ اصلی بیشتر شد؛ امتیاز امنیت به‌دلیل تأیید نشت بین حساب‌ها کمتر و امتیاز درستی هسته به‌دلیل موفقیت mutual و فیلترهای معتبر بیشتر شد. میانگین گرد‌شده تغییر نکرد.

| بخش | امتیاز از ۱۰ | وزن | دلیل |
|---|---:|---:|---|
| طراحی بصری و هویت | ۸ | ۱۵٪ | هماهنگ، جذاب و مناسب مخاطب؛ چند متن کم‌رنگ و بخش ناتمام |
| وضوح و تجربهٔ کاربر | ۷ | ۱۵٪ | شروع روشن و موبایل مناسب؛ نیت کاربر و چند مسیر lifecycle ناقص |
| امنیت و حریم خصوصی | ۶ | ۲۰٪ | identity/whitelist خوب؛ نشت cache بین دو حساب در سایت تأیید شد |
| درستی رفتار | ۶٫۵ | ۲۰٪ | mutual و فیلترهای معتبر عملاً کار کردند؛ race، double-skip و discovery باقی‌اند |
| نگهداشت و قابلیت انتشار | ۶ | ۱۵٪ | ساختار داده‌محور خوب؛ تست، schema نسخه‌دار و lock کم است |
| کارایی در مرحلهٔ فعلی | ۶ | ۱۰٪ | حجم frontend مناسب؛ round trip زیاد و رشد بدون pagination/cache |
| آمادگی عرضهٔ عمومی | ۴٫۵ | ۵٪ | support، policy، abuse handling و E2E staging هنوز لازم است |
| **میانگین وزنی، گرد‌شده** | **۶٫۵** | **۱۰۰٪** | **MVP امیدوارکننده با چند اصلاح ضروری پیش از رشد** |

ارزشمندترین سرمایه‌گذاری بعدی، اثبات این است که دو کاربر جدید بدون سردرگمی، نشت داده یا انتظار بی‌نتیجه، یکدیگر را پیدا می‌کنند و بازی را شروع می‌کنند. همین نتیجه، به محصول بیش از افزودن ویژگی‌های نمایشی امتیاز می‌دهد.
