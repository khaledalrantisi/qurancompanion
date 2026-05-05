import os, random, requests, logging, re, json
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
TOKEN = os.environ.get("BOT_TOKEN")
AUTHOR = "Khaled M.M. Alrantisi"
VERSION = "1.0.0"
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# Only languages with verified API translation support
LANGUAGES = {
    "English":    {"flag": "🇬🇧", "ids": [131, 20]},
    "Arabic":     {"flag": "🇸🇦", "ids": []},
    "French":     {"flag": "🇫🇷", "ids": [136, 31]},
    "Russian":    {"flag": "🇷🇺", "ids": [79, 45]},
    "German":     {"flag": "🇩🇪", "ids": [27]},
    "Spanish":    {"flag": "🇪🇸", "ids": [83]},
    "Italian":    {"flag": "🇮🇹", "ids": [153]},
    "Turkish":    {"flag": "🇹🇷", "ids": [77, 24]},
    "Urdu":       {"flag": "🇵🇰", "ids": [97, 158]},
    "Hindi":      {"flag": "🇮🇳", "ids": [122]},
    "Bengali":    {"flag": "🇧🇩", "ids": [120]},
    "Indonesian": {"flag": "🇮🇩", "ids": [134, 33]},
    "Malay":      {"flag": "🇲🇾", "ids": [39]},
    "Persian":    {"flag": "🇮🇷", "ids": [135, 29]},
    "Bosnian":    {"flag": "🇧🇦", "ids": [25]},
    "Dutch":      {"flag": "🇳🇱", "ids": [144]},
    "Swedish":    {"flag": "🇸🇪", "ids": [71]},
}

LANG_FILE = "user_languages.json"

def _load():
    try:
        with open(LANG_FILE, "r") as f:
            return {int(k): v for k, v in json.load(f).items()}
    except:
        return {}

def _save():
    try:
        with open(LANG_FILE, "w") as f:
            json.dump({str(k): v for k, v in user_languages.items()}, f)
    except:
        pass

user_languages = _load()

def get_lang(uid): return user_languages.get(uid, "English")
def set_lang(uid, lang):
    user_languages[uid] = lang
    _save()
def clean(t): return re.sub(r'<[^>]+>', '', t).strip()

# ── API ────────────────────────────────────────────────────────────────────────
def fetch_verse(s, a, lang):
    ids = LANGUAGES.get(lang, {}).get("ids", [131])
    if not ids:  # Arabic — no translation needed
        try:
            r = requests.get(f"https://api.quran.com/api/v4/verses/by_key/{s}:{a}?fields=text_uthmani", timeout=10)
            if r.status_code == 200:
                arabic = r.json().get('verse', {}).get('text_uthmani', '')
                sname = fetch_surah_name(s)
                return {'arabic': arabic, 'translation': '', 'surah': sname, 'surah_num': s, 'ayah': a}
        except: pass
        return None

    for tid in ids:
        try:
            url = f"https://api.quran.com/api/v4/verses/by_key/{s}:{a}?translations={tid}&fields=text_uthmani"
            r = requests.get(url, timeout=10)
            if r.status_code != 200: continue
            v = r.json().get('verse', {})
            arabic = v.get('text_uthmani', '')
            tlist = v.get('translations', [])
            trans = clean(tlist[0].get('text', '')) if tlist else ''
            if not trans: continue
            sname = fetch_surah_name(s)
            return {'arabic': arabic, 'translation': trans, 'surah': sname, 'surah_num': s, 'ayah': a}
        except Exception as e:
            logging.error(f"fetch_verse tid={tid}: {e}")
    return None

def fetch_surah_name(s):
    try:
        r = requests.get(f"https://api.quran.com/api/v4/chapters/{s}", timeout=10)
        if r.status_code == 200:
            return r.json().get('chapter', {}).get('name_simple', f"Surah {s}")
    except: pass
    return f"Surah {s}"

def fetch_random(lang):
    s = random.randint(1, 114)
    try:
        r = requests.get(f"https://api.quran.com/api/v4/chapters/{s}", timeout=10)
        count = r.json().get('chapter', {}).get('verses_count', 7) if r.status_code == 200 else 7
        a = random.randint(1, count)
    except:
        s, a = 2, 255
    return fetch_verse(s, a, lang)

def fetch_tafseer(s, a):
    try:
        r = requests.get(f"https://api.quran.com/api/v4/verses/by_key/{s}:{a}?tafsirs=169&fields=text_uthmani", timeout=10)
        if r.status_code != 200: return None
        v = r.json().get('verse', {})
        arabic = v.get('text_uthmani', '')
        tafsirs = v.get('tafsirs', [])
        text = clean(tafsirs[0].get('text', '')) if tafsirs else ''
        if len(text) > 900: text = text[:900] + '...'
        return {'arabic': arabic, 'tafseer': text, 'surah': s, 'ayah': a}
    except Exception as e:
        logging.error(f"fetch_tafseer: {e}")
        return None

def fetch_surah_info(n):
    try:
        r = requests.get(f"https://api.quran.com/api/v4/chapters/{n}", timeout=10)
        if r.status_code != 200: return None
        d = r.json().get('chapter', {})
        return {
            'name': d.get('name_simple', ''),
            'arabic_name': d.get('name_arabic', ''),
            'meaning': d.get('translated_name', {}).get('name', ''),
            'verses': d.get('verses_count', 0),
            'revelation': d.get('revelation_place', '').capitalize(),
            'num': n,
        }
    except: return None

# ── DUAS ───────────────────────────────────────────────────────────────────────
DUAS = [
    {
        "title": "Dua for Anxiety and Worry",
        "arabic": "اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْهَمِّ وَالْحَزَنِ وَالْعَجْزِ وَالْكَسَلِ وَالْجُبْنِ وَالْبُخْلِ وَضَلَعِ الدَّيْنِ وَغَلَبَةِ الرِّجَالِ",
        "source": "Sahih al-Bukhari",
        "translations": {
            "English":    "O Allah, I seek refuge in You from grief, sadness, weakness, laziness, cowardice, miserliness, the burden of debt and the oppression of men.",
            "French":     "Ô Allah, je cherche refuge en Toi contre le chagrin, la tristesse, la faiblesse, la paresse, la lâcheté, l'avarice, le poids des dettes et la domination des hommes.",
            "Russian":    "О Аллах, я прибегаю к Тебе от горя, печали, слабости, лени, трусости, скупости, бремени долгов и власти людей.",
            "German":     "O Allah, ich suche Zuflucht bei Dir vor Kummer, Trauer, Schwäche, Faulheit, Feigheit, Geiz, Schuldenlast und Unterdrückung durch Menschen.",
            "Spanish":    "Oh Allah, busco refugio en Ti del dolor, tristeza, debilidad, pereza, cobardía, tacañería, carga de deudas y opresión.",
            "Italian":    "O Allah, cerco rifugio in Te dalla tristezza, debolezza, pigrizia, vigliaccheria, avarizia, peso dei debiti e oppressione degli uomini.",
            "Turkish":    "Allahım, keder, üzüntü, acizlik, tembellik, korkaklık, cimrilik, borç yükü ve insanların zulmünden Sana sığınırım.",
            "Urdu":       "اے اللہ، میں آپ سے غم، دکھ، کمزوری، سستی، بزدلی، بخل، قرض کے بوجھ اور لوگوں کے ظلم سے پناہ مانگتا ہوں۔",
            "Hindi":      "हे अल्लाह, मैं तुझसे दुःख, उदासी, कमजोरी, आलस्य, कायरता, कंजूसी, कर्ज के बोझ और लोगों के अत्याचार से शरण मांगता हूं।",
            "Bengali":    "হে আল্লাহ, আমি তোমার কাছে দুঃখ, কষ্ট, দুর্বলতা, অলসতা, কাপুরুষতা, কৃপণতা, ঋণের বোঝা ও মানুষের অত্যাচার থেকে আশ্রয় চাই।",
            "Indonesian": "Ya Allah, aku berlindung kepada-Mu dari kesedihan, duka, kelemahan, kemalasan, pengecut, kikir, beban hutang dan penindasan manusia.",
            "Malay":      "Ya Allah, aku berlindung kepada-Mu daripada kesedihan, kelemahan, kemalasan, pengecut, kebakhilan, beban hutang dan penindasan manusia.",
            "Persian":    "خداوندا، از غم، اندوه، ضعف، تنبلی، ترس، بخل، سنگینی بدهی و ستم مردم به تو پناه می‌برم.",
            "Bosnian":    "Allahu, utječem Ti se od brige, tuge, slabosti, lijenosti, kukavičluka, škrtosti, tereta duga i nasilja ljudi.",
            "Dutch":      "O Allah, ik zoek toevlucht bij U voor verdriet, zwakheid, luiheid, lafheid, gierigheid, schuldenlast en onderdrukking door mensen.",
            "Swedish":    "O Allah, jag söker skydd hos Dig mot sorg, svaghet, lättja, feghet, snålhet, skuldebörda och förtryck av människor.",
        }
    },
    {
        "title": "Dua of Prophet Yunus — in Distress",
        "arabic": "لَا إِلَهَ إِلَّا أَنتَ سُبْحَانَكَ إِنِّي كُنتُ مِنَ الظَّالِمِينَ",
        "source": "Quran 21:87",
        "translations": {
            "English":    "There is no deity except You; exalted are You. Indeed, I have been of the wrongdoers.",
            "French":     "Il n'y a de divinité que Toi, gloire à Toi! En vérité, je suis du nombre des injustes.",
            "Russian":    "Нет никого достойного поклонения, кроме Тебя! Пречист Ты! Воистину, я был одним из несправедливых.",
            "German":     "Es gibt keine Gottheit außer Dir; gepriesen bist Du. Wahrlich, ich war von den Ungerechten.",
            "Spanish":    "No hay deidad excepto Tú; glorificado seas Tú. He sido de los que cometen injusticia.",
            "Italian":    "Non c'è divinità all'infuori di Te; sii glorificato. In verità, sono stato tra gli ingiusti.",
            "Turkish":    "Senden başka ilah yoktur. Sen münezzehsin. Gerçekten ben zalimlerden oldum.",
            "Urdu":       "تیرے سوا کوئی معبود نہیں، تو پاک ہے، بیشک میں ظالموں میں سے ہوں۔",
            "Hindi":      "तेरे सिवा कोई उपास्य नहीं, तू पवित्र है, मैं अत्याचारियों में से था।",
            "Bengali":    "তুমি ছাড়া কোনো ইলাহ নেই, তুমি পবিত্র। আমি জালেমদের অন্তর্ভুক্ত ছিলাম।",
            "Indonesian": "Tidak ada Tuhan selain Engkau, Maha Suci Engkau, aku termasuk orang-orang yang zalim.",
            "Malay":      "Tiada tuhan melainkan Engkau. Maha Suci Engkau. Aku adalah dari golongan yang zalim.",
            "Persian":    "هیچ معبودی جز تو نیست، منزهی تو، من از ستمکاران بودم.",
            "Bosnian":    "Nema boga osim Tebe, hvaljen neka si. Ja sam bio od onih koji su sami sebi nepravdu nanijeli.",
            "Dutch":      "Er is geen godheid behalve U; geprezen bent U. Ik behoorde tot de onrechtplegers.",
            "Swedish":    "Det finns ingen gudom utom Du; upphöjd är Du. Jag har tillhört de orättvisa.",
        }
    },
    {
        "title": "Dua for Guidance",
        "arabic": "اللَّهُمَّ اهْدِنِي وَسَدِّدْنِي",
        "source": "Sahih Muslim",
        "translations": {
            "English":    "O Allah, guide me and make me steadfast.",
            "French":     "Ô Allah, guide-moi et affermis-moi.",
            "Russian":    "О Аллах, направь меня на прямой путь и укрепи меня.",
            "German":     "O Allah, führe mich und mache mich standhaft.",
            "Spanish":    "Oh Allah, guíame y hazme firme.",
            "Italian":    "O Allah, guidami e rendimi fermo.",
            "Turkish":    "Allahım, beni hidayete erdir ve doğruya yönlendir.",
            "Urdu":       "اے اللہ، مجھے ہدایت دے اور مجھے ثابت قدم رکھ۔",
            "Hindi":      "हे अल्लाह, मुझे मार्गदर्शन दे और मुझे दृढ़ बना।",
            "Bengali":    "হে আল্লাহ, আমাকে হেদায়েত দাও এবং অবিচল রাখো।",
            "Indonesian": "Ya Allah, tunjukilah aku dan luruskanlah aku.",
            "Malay":      "Ya Allah, tunjukilah aku jalan yang lurus dan luruskanlah aku.",
            "Persian":    "خداوندا، مرا هدایت کن و استوار نگه دار.",
            "Bosnian":    "Allahu, uputi me na Pravi put i učvrsti me.",
            "Dutch":      "O Allah, leid mij en maak mij standvastig.",
            "Swedish":    "O Allah, vägled mig och gör mig ståndaktig.",
        }
    },
    {
        "title": "Dua for Knowledge",
        "arabic": "رَبِّ زِدْنِي عِلْمًا",
        "source": "Quran 20:114",
        "translations": {
            "English":    "My Lord, increase me in knowledge.",
            "French":     "Mon Seigneur, accrois ma science.",
            "Russian":    "Господи, прибавь мне знания.",
            "German":     "Mein Herr, vermehre mein Wissen.",
            "Spanish":    "Señor mío, auméntame en conocimiento.",
            "Italian":    "Signore mio, aumentami in conoscenza.",
            "Turkish":    "Rabbim, ilmimi artır.",
            "Urdu":       "میرے رب، میرے علم میں اضافہ فرما۔",
            "Hindi":      "हे मेरे प्रभु, मेरे ज्ञान में वृद्धि कर।",
            "Bengali":    "হে আমার প্রতিপালক, আমার জ্ঞান বৃদ্ধি করুন।",
            "Indonesian": "Ya Tuhanku, tambahkanlah ilmu kepadaku.",
            "Malay":      "Ya Tuhanku, tambahkanlah ilmuku.",
            "Persian":    "پروردگارم، بر دانشم بیفزا.",
            "Bosnian":    "Gospodaru moj, povećaj mi znanje!",
            "Dutch":      "Mijn Heer, vermeerder mijn kennis.",
            "Swedish":    "Min Herre, öka mig i kunskap.",
        }
    },
    {
        "title": "Dua for Parents",
        "arabic": "رَّبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا",
        "source": "Quran 17:24",
        "translations": {
            "English":    "My Lord, have mercy on them both as they raised me when I was small.",
            "French":     "Mon Seigneur, fais-leur miséricorde comme ils m'ont élevé tout petit.",
            "Russian":    "Господи, помилуй их обоих, как они воспитывали меня в детстве.",
            "German":     "Mein Herr, erbarme Dich ihrer, wie sie mich aufgezogen haben, als ich klein war.",
            "Spanish":    "Señor mío, ten misericordia de ellos como me criaron cuando era pequeño.",
            "Italian":    "Signore mio, abbi misericordia di loro come mi hanno allevato quando ero piccolo.",
            "Turkish":    "Rabbim, beni küçükken yetiştirdikleri gibi onlara merhamet et.",
            "Urdu":       "میرے رب، ان پر رحم فرما جیسا انہوں نے مجھے بچپن میں پالا۔",
            "Hindi":      "हे मेरे प्रभु, उन पर दया कर जैसे उन्होंने मुझे बचपन में पाला।",
            "Bengali":    "হে আমার প্রতিপালক, তাদের প্রতি দয়া করুন যেভাবে তারা আমাকে ছোটবেলায় লালন করেছিলেন।",
            "Indonesian": "Ya Tuhanku, sayangilah keduanya sebagaimana mereka mendidikku waktu kecil.",
            "Malay":      "Ya Tuhanku, kasihanilah keduanya sebagaimana mereka membesarkanku semasa kecilku.",
            "Persian":    "پروردگارم، به آن دو رحم کن همان‌طور که مرا در کودکی پرورش دادند.",
            "Bosnian":    "Gospodaru moj, smiluj im se, kao što su oni meni bili milostivi kada sam bio dijete.",
            "Dutch":      "Mijn Heer, heb medelijden met hen, zoals zij mij hebben grootgebracht.",
            "Swedish":    "Min Herre, förbarma Dig över dem, liksom de fostrade mig när jag var liten.",
        }
    },
    {
        "title": "Allah is Sufficient for Us",
        "arabic": "حَسْبُنَا اللَّهُ وَنِعْمَ الْوَكِيلُ",
        "source": "Quran 3:173",
        "translations": {
            "English":    "Allah is sufficient for us, and He is the best Disposer of affairs.",
            "French":     "Allah nous suffit, et Il est le meilleur garant.",
            "Russian":    "Нам достаточно Аллаха, и Он — лучший Покровитель.",
            "German":     "Allah genügt uns, und Er ist der beste Verfüger.",
            "Spanish":    "Allah nos es suficiente, y Él es el mejor Dispensador.",
            "Italian":    "Allah ci è sufficiente ed Egli è il migliore dei Dispossitori.",
            "Turkish":    "Allah bize yeter ve O ne güzel vekildir.",
            "Urdu":       "اللہ ہمارے لیے کافی ہے اور وہ بہترین کارساز ہے۔",
            "Hindi":      "अल्लाह हमारे लिए पर्याप्त है और वह सर्वोत्तम कार्यप्रबंधक है।",
            "Bengali":    "আমাদের জন্য আল্লাহই যথেষ্ট এবং তিনি উত্তম কর্মবিধায়ক।",
            "Indonesian": "Cukuplah Allah bagi kami, dan Dia adalah sebaik-baik pelindung.",
            "Malay":      "Cukuplah Allah bagi kami dan Dia adalah sebaik-baik Penjaga.",
            "Persian":    "خداوند برای ما کافی است و بهترین وکیل است.",
            "Bosnian":    "Allah nam je dovoljan i divan je On Zaštitnik!",
            "Dutch":      "Allah is voldoende voor ons, en Hij is de beste Beschikker.",
            "Swedish":    "Allah räcker oss, och Han är den bäste Förvaltaren.",
        }
    },
    {
        "title": "Dua for Good in This World and Hereafter",
        "arabic": "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ",
        "source": "Quran 2:201",
        "translations": {
            "English":    "Our Lord, give us good in this world and good in the Hereafter, and protect us from the torment of the Fire.",
            "French":     "Notre Seigneur, accorde-nous le bien ici-bas et le bien dans l'au-delà et préserve-nous du supplice du Feu.",
            "Russian":    "Господи наш, дай нам в этом мире благо и в Последней жизни благо и защити нас от мучений Огня.",
            "German":     "Unser Herr, gib uns im Diesseits und Jenseits das Gute und bewahre uns vor der Strafe des Feuers.",
            "Spanish":    "Señor nuestro, concédenos el bien en esta vida y en la otra vida y protégenos del tormento del Fuego.",
            "Italian":    "Signore nostro, concedici il bene in questa vita e nell'aldilà e proteggici dal tormento del Fuoco.",
            "Turkish":    "Rabbimiz, bize dünyada ve ahirette iyilik ver ve bizi cehennem azabından koru.",
            "Urdu":       "اے ہمارے رب! دنیا میں بھلائی دے، آخرت میں بھی بھلائی دے اور آگ کے عذاب سے بچا۔",
            "Hindi":      "हे हमारे प्रभु, दुनिया और आखिरत में अच्छाई दे और आग के अज़ाब से बचा।",
            "Bengali":    "হে আমাদের প্রতিপালক, দুনিয়া ও আখিরাতে কল্যাণ দাও এবং জাহান্নামের আজাব থেকে রক্ষা করো।",
            "Indonesian": "Ya Tuhan kami, berilah kami kebaikan di dunia dan di akhirat dan peliharalah kami dari siksa neraka.",
            "Malay":      "Ya Tuhan kami, berilah kami kebaikan di dunia dan di akhirat, dan peliharalah kami dari azab neraka.",
            "Persian":    "پروردگارا، در دنیا و آخرت به ما نیکی عطا کن و ما را از عذاب آتش نگهدار.",
            "Bosnian":    "Gospodaru naš, daj nam dobro i na ovom i na onom svijetu i sačuvaj nas patnje u Vatri!",
            "Dutch":      "Onze Heer, geef ons het goede in deze wereld en het Hiernamaals en bescherm ons tegen de bestraffing van het Vuur.",
            "Swedish":    "Vår Herre, ge oss det goda i denna värld och i nästa värld, och skydda oss från eldens plågor.",
        }
    },
    {
        "title": "Dua for Forgiveness",
        "arabic": "رَبَّنَا ظَلَمْنَا أَنفُسَنَا وَإِن لَّمْ تَغْفِرْ لَنَا وَتَرْحَمْنَا لَنَكُونَنَّ مِنَ الْخَاسِرِينَ",
        "source": "Quran 7:23",
        "translations": {
            "English":    "Our Lord, we have wronged ourselves, and if You do not forgive us and have mercy upon us, we will surely be among the losers.",
            "French":     "Notre Seigneur, nous avons lésé nos propres âmes. Si Tu ne nous pardonnes pas, nous serons du nombre des perdants.",
            "Russian":    "Господи наш, мы поступили несправедливо по отношению к себе, и если Ты не простишь нас, мы окажемся в числе потерпевших убыток.",
            "German":     "Unser Herr, wir haben uns selbst Unrecht getan. Wenn Du uns nicht vergibst, werden wir zu den Verlierern gehören.",
            "Spanish":    "Señor nuestro, hemos sido injustos con nosotros mismos. Si no nos perdonas seremos de los perdedores.",
            "Italian":    "Signore nostro, abbiamo commesso ingiustizia verso noi stessi. Se non ci perdoni saremo certamente tra i perdenti.",
            "Turkish":    "Rabbimiz, biz kendimize zulmettik. Eğer bizi bağışlamaz ve merhamet etmezsen, ziyan edenlerden oluruz.",
            "Urdu":       "اے ہمارے رب! ہم نے اپنی جانوں پر ظلم کیا، اگر تو نہ بخشے تو ہم نقصان اٹھانے والوں میں ہوں گے۔",
            "Hindi":      "हे हमारे प्रभु, हमने अपने आप पर अत्याचार किया। यदि तू माफ नहीं करता तो हम घाटे में रहेंगे।",
            "Bengali":    "হে আমাদের প্রতিপালক, আমরা নিজেদের উপর অত্যাচার করেছি। যদি তুমি ক্ষমা না করো তবে আমরা ক্ষতিগ্রস্তদের মধ্যে হব।",
            "Indonesian": "Ya Tuhan kami, kami telah menzalimi diri kami. Jika Engkau tidak mengampuni kami, niscaya kami termasuk orang-orang yang rugi.",
            "Malay":      "Wahai Tuhan kami, kami telah menganiaya diri sendiri. Jika Engkau tidak mengampuni kami nescaya kami termasuk orang yang rugi.",
            "Persian":    "پروردگارا، ما به خود ستم کردیم و اگر ما را نبخشی، از زیانکاران خواهیم بود.",
            "Bosnian":    "Gospodaru naš, sami smo sebi nepravdu učinili. Ako nam ne oprostiš, sigurno ćemo biti izgubljeni.",
            "Dutch":      "Onze Heer, wij hebben onszelf onrecht aangedaan. Als U ons niet vergeeft, zullen wij tot de verliezers behoren.",
            "Swedish":    "Vår Herre, vi har orätt mot oss själva. Om Du inte förlåter oss, kommer vi att tillhöra förlorarna.",
        }
    },
    {
        "title": "Dua for Ease in Hardship",
        "arabic": "اللَّهُمَّ لَا سَهْلَ إِلَّا مَا جَعَلْتَهُ سَهْلًا وَأَنْتَ تَجْعَلُ الْحَزْنَ إِذَا شِئْتَ سَهْلًا",
        "source": "Ibn Hibban",
        "translations": {
            "English":    "O Allah, there is no ease except what You make easy, and You make difficulty easy when You will.",
            "French":     "Ô Allah, il n'y a pas de facilité sauf ce que Tu rends facile, et Tu rends la difficulté facile quand Tu le veux.",
            "Russian":    "О Аллах, нет лёгкости, кроме той, которую Ты сделал лёгкой, и Ты делаешь трудное лёгким, когда пожелаешь.",
            "German":     "O Allah, es gibt keine Leichtigkeit außer dem, was Du leicht machst, und Du machst die Schwierigkeit leicht, wenn Du willst.",
            "Spanish":    "Oh Allah, no hay facilidad excepto lo que Tú haces fácil, y Tú haces fácil la dificultad cuando quieres.",
            "Italian":    "O Allah, non c'è facilità se non in ciò che Tu rendi facile, e Tu rendi la difficoltà facile quando vuoi.",
            "Turkish":    "Allahım, Senin kolaylaştırdığın şey dışında kolaylık yoktur. Sen dilediğinde zorluğu da kolaylaştırırsın.",
            "Urdu":       "اے اللہ، آسانی صرف وہی ہے جو تو آسان کرے، اور تو مشکل کو بھی آسان کر سکتا ہے جب چاہے۔",
            "Hindi":      "हे अल्लाह, आसानी केवल वही है जो तू आसान करे, और तू कठिनाई को भी आसान कर सकता है।",
            "Bengali":    "হে আল্লাহ, তুমি যা সহজ করো তা ছাড়া কোনো সহজ নেই, এবং তুমি যখন চাও তখন কঠিনকেও সহজ করো।",
            "Indonesian": "Ya Allah, tidak ada kemudahan kecuali yang Engkau mudahkan, dan Engkau menjadikan kesulitan mudah jika Engkau menghendakinya.",
            "Malay":      "Ya Allah, tiada kemudahan kecuali apa yang Engkau permudahkan, dan Engkau menjadikan kesukaran itu mudah apabila Engkau kehendaki.",
            "Persian":    "خداوندا، آسانی‌ای نیست مگر آنچه تو آسان کنی، و تو سختی را هر وقت بخواهی آسان می‌کنی.",
            "Bosnian":    "Allahu, nema lakoće osim u onom što Ti učiniš lakim, a Ti činiš teškoću lakom kada hoćeš.",
            "Dutch":      "O Allah, er is geen gemak behalve wat U gemakkelijk maakt, en U maakt moeilijkheid gemakkelijk wanneer U wilt.",
            "Swedish":    "O Allah, det finns inget lätthet utom vad Du gör lätt, och Du gör svårighet lätt när Du vill.",
        }
    },
    {
        "title": "Dua for Patience",
        "arabic": "رَبَّنَا أَفْرِغْ عَلَيْنَا صَبْرًا وَثَبِّتْ أَقْدَامَنَا",
        "source": "Quran 2:250",
        "translations": {
            "English":    "Our Lord, pour upon us patience and plant firmly our feet.",
            "French":     "Notre Seigneur, déverse sur nous la patience et affermis nos pas.",
            "Russian":    "Господи наш, ниспошли на нас терпение и укрепи наши стопы.",
            "German":     "Unser Herr, schenke uns Geduld und festige unsere Füße.",
            "Spanish":    "Señor nuestro, derrama sobre nosotros paciencia y afianza nuestros pies.",
            "Italian":    "Signore nostro, riversaci sopra la pazienza e consolida i nostri passi.",
            "Turkish":    "Rabbimiz, üzerimize sabır yağdır ve ayaklarımızı sabit kıl.",
            "Urdu":       "اے ہمارے رب! ہم پر صبر نازل فرما اور ہمارے قدموں کو جمائے رکھ۔",
            "Hindi":      "हे हमारे प्रभु, हम पर धैर्य डाल और हमारे कदम जमा दे।",
            "Bengali":    "হে আমাদের প্রতিপালক, আমাদের উপর ধৈর্য ঢেলে দাও এবং আমাদের পদক্ষেপ দৃঢ় করো।",
            "Indonesian": "Ya Tuhan kami, tuangkanlah kesabaran kepada kami dan kokohkanlah langkah kami.",
            "Malay":      "Ya Tuhan kami, limpahkanlah kesabaran kepada kami dan tetapkanlah pendirian kami.",
            "Persian":    "پروردگارا، صبر را بر ما فرو ریز و قدم‌هایمان را استوار کن.",
            "Bosnian":    "Gospodaru naš, daj nam strpljenje i učvrsti naše korake!",
            "Dutch":      "Onze Heer, schenk ons geduld en maak onze voeten vast.",
            "Swedish":    "Vår Herre, ge oss tålamod och stärk våra fötter.",
        }
    },
    {
        "title": "Dua for Trust in Allah",
        "arabic": "تَوَكَّلْتُ عَلَى اللَّهِ وَلَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ",
        "source": "Abu Dawud",
        "translations": {
            "English":    "I put my trust in Allah and there is no power nor strength except with Allah.",
            "French":     "Je me confie à Allah et il n'y a de force ni de puissance qu'en Allah.",
            "Russian":    "Я уповаю на Аллаха, и нет силы и мощи, кроме как у Аллаха.",
            "German":     "Ich vertraue auf Allah und es gibt keine Kraft und keine Macht außer bei Allah.",
            "Spanish":    "Me encomiendo a Allah y no hay poder ni fuerza excepto con Allah.",
            "Italian":    "Mi affido ad Allah e non c'è potere né forza se non con Allah.",
            "Turkish":    "Allah'a tevekkül ettim, güç ve kuvvet yalnızca Allah'a aittir.",
            "Urdu":       "میں نے اللہ پر توکل کیا اور اللہ کے سوا نہ کوئی طاقت ہے نہ قوت۔",
            "Hindi":      "मैंने अल्लाह पर भरोसा किया और अल्लाह के सिवा न कोई शक्ति है न बल।",
            "Bengali":    "আমি আল্লাহর উপর ভরসা করলাম এবং আল্লাহ ছাড়া কোনো শক্তি বা সামর্থ্য নেই।",
            "Indonesian": "Aku bertawakal kepada Allah, dan tidak ada daya dan kekuatan kecuali dengan Allah.",
            "Malay":      "Aku bertawakkal kepada Allah dan tiada daya dan kekuatan melainkan dengan Allah.",
            "Persian":    "بر الله توکل کردم و نیرو و قدرتی جز از الله نیست.",
            "Bosnian":    "Pouzdao sam se u Allaha, i nema snage ni moći osim uz Allaha.",
            "Dutch":      "Ik vertrouw op Allah en er is geen kracht of macht behalve bij Allah.",
            "Swedish":    "Jag förtröstar på Allah och det finns ingen kraft eller styrka utom hos Allah.",
        }
    },
    {
        "title": "Dua When Waking Up",
        "arabic": "الْحَمْدُ لِلَّهِ الَّذِي أَحْيَانَا بَعْدَ مَا أَمَاتَنَا وَإِلَيْهِ النُّشُورُ",
        "source": "Sahih al-Bukhari",
        "translations": {
            "English":    "All praise is for Allah who gave us life after causing us to die, and to Him is the resurrection.",
            "French":     "Louange à Allah qui nous a redonné la vie après nous avoir fait mourir, et c'est vers Lui que sera la résurrection.",
            "Russian":    "Хвала Аллаху, который оживил нас после того, как умертвил нас, и к Нему возвращение.",
            "German":     "Alles Lob sei Allah, der uns lebendig gemacht hat, nachdem Er uns hatte sterben lassen, und zu Ihm ist die Auferstehung.",
            "Spanish":    "Toda alabanza es para Allah que nos dio vida después de hacernos morir, y hacia Él es la resurrección.",
            "Italian":    "Tutta la lode è per Allah che ci ha dato vita dopo averci fatto morire, e a Lui è la resurrezione.",
            "Turkish":    "Bizi öldürdükten sonra tekrar dirilten Allah'a hamdolsun. Dönüş O'nadır.",
            "Urdu":       "تمام تعریف اللہ کے لیے ہے جس نے ہمیں موت کے بعد زندگی دی۔",
            "Hindi":      "सभी प्रशंसा अल्लाह के लिए है जिसने हमें मृत्यु के बाद जीवन दिया।",
            "Bengali":    "সকল প্রশংসা আল্লাহর জন্য যিনি আমাদের মৃত্যুর পর জীবন দিয়েছেন।",
            "Indonesian": "Segala puji bagi Allah yang telah menghidupkan kami setelah mematikan kami.",
            "Malay":      "Segala puji bagi Allah yang menghidupkan kami setelah mematikan kami dan kepada-Nyalah kebangkitan.",
            "Persian":    "ستایش از آن الله است که ما را پس از میراندن زنده کرد.",
            "Bosnian":    "Hvala Allahu koji nas je oživio nakon što nas je usmrtio, i Njemu ćemo biti vraćeni.",
            "Dutch":      "Alle lof is voor Allah die ons leven gaf nadat Hij ons had laten sterven, en tot Hem is de opstanding.",
            "Swedish":    "All lovprisning tillhör Allah som gav oss liv sedan Han lät oss dö, och till Honom är uppståndelsen.",
        }
    },
]

# ── MOTIVATIONAL MESSAGES ──────────────────────────────────────────────────────
# ── MOTIVATIONAL MESSAGES ──────────────────────────────────────────────────────
# Each message: Arabic original + exact translation in every language
MESSAGES = [
    {
        "arabic": "اللهُ يعلمُ ما في قلبكَ. كلُّ دمعةٍ تذرفها، كلُّ ليلةٍ لم تنم فيها — هو يرى كلَّ ذلك. لا شيء تمرُّ به يضيعُ هباءً.",
        "English":    "Allah knows what is in your heart. Every tear you cry, every sleepless night — He sees it all. Nothing you go through is wasted.",
        "French":     "Allah connaît ce qui est dans ton cœur. Chaque larme, chaque nuit sans sommeil — Il voit tout. Rien de ce que tu traverses n'est perdu.",
        "Russian":    "Аллах знает, что у тебя в сердце. Каждая слеза, каждая бессонная ночь — Он видит всё. Ничто из того, через что ты проходишь, не пропадёт зря.",
        "German":     "Allah weiß, was in deinem Herzen ist. Jede Träne, jede schlaflose Nacht — Er sieht alles. Nichts, was du durchmachst, ist umsonst.",
        "Spanish":    "Allah sabe lo que hay en tu corazón. Cada lágrima, cada noche sin dormir — Él lo ve todo. Nada de lo que atraviesas se desperdicia.",
        "Italian":    "Allah sa cosa c'è nel tuo cuore. Ogni lacrima, ogni notte insonne — Lui vede tutto. Nulla di ciò che attraversi è sprecato.",
        "Turkish":    "Allah kalbindekini bilir. Döktüğün her gözyaşı, geçirdiğin her uykusuz gece — O hepsini görür. Yaşadıklarının hiçbiri boşa gitmez.",
        "Urdu":       "اللہ جانتا ہے تمہارے دل میں کیا ہے۔ ہر آنسو، ہر رات جو نیند نہیں آتی — وہ سب کچھ دیکھتا ہے۔ جو کچھ بھی تم سے گزرتا ہے وہ ضائع نہیں ہوتا۔",
        "Hindi":      "अल्लाह जानता है तुम्हारे दिल में क्या है। हर आंसू, हर रात जो नींद नहीं आती — वो सब देखता है। जो कुछ भी तुमसे गुजरता है वो बेकार नहीं जाता।",
        "Bengali":    "আল্লাহ জানেন তোমার হৃদয়ে কী আছে। প্রতিটি অশ্রু, প্রতিটি ঘুমহীন রাত — তিনি সবকিছু দেখেন। তুমি যা কিছু পার কর তার কিছুই নষ্ট হয় না।",
        "Indonesian": "Allah mengetahui apa yang ada di hatimu. Setiap air mata, setiap malam tanpa tidur — Dia melihat semuanya. Tidak ada yang kamu lalui yang sia-sia.",
        "Malay":      "Allah mengetahui apa yang ada dalam hatimu. Setiap air mata, setiap malam tanpa tidur — Dia melihat semuanya. Tiada yang kamu lalui yang sia-sia.",
        "Persian":    "خداوند می‌داند در دلت چیست. هر اشکی که می‌ریزی، هر شب بی‌خوابی — او همه را می‌بیند. هیچ چیزی که از سرت می‌گذرد بی‌فایده نیست.",
        "Bosnian":    "Allah zna šta je u tvom srcu. Svaka suza, svaka noć bez sna — On sve vidi. Ništa što prolaziš nije uzalud.",
        "Dutch":      "Allah weet wat er in je hart is. Elke traan, elke slapeloze nacht — Hij ziet alles. Niets wat je doormaakt is voor niets.",
        "Swedish":    "Allah vet vad som finns i ditt hjärta. Varje tår, varje sömnlös natt — Han ser allt. Inget du går igenom är förgäves.",
    },
    {
        "arabic": "لا تيأس. ربَّما بينكَ وبين الفرج دعاءٌ واحد فقط. لا يردُّ اللهُ قلباً يدعوه بصدق.",
        "English":    "Do not lose hope. Between you and relief, there may only be one more dua. Allah never turns away a heart that calls upon Him sincerely.",
        "French":     "Ne perds pas espoir. Il n'y a peut-être qu'une seule invocation entre toi et le soulagement. Allah ne repousse jamais un cœur sincère.",
        "Russian":    "Не теряй надежды. Между тобой и облегчением, возможно, осталась одна молитва. Аллах не отвергает искреннее сердце.",
        "German":     "Verliere nicht die Hoffnung. Vielleicht liegt nur noch ein Gebet zwischen dir und der Erleichterung. Allah weist kein aufrichtiges Herz ab.",
        "Spanish":    "No pierdas la esperanza. Quizás solo haya una súplica entre tú y el alivio. Allah nunca rechaza un corazón sincero.",
        "Italian":    "Non perdere la speranza. Forse c'è solo una dua tra te e il sollievo. Allah non rifiuta mai un cuore sincero.",
        "Turkish":    "Umudunu kaybetme. Seninle rahatlık arasında belki sadece bir dua kalmıştır. Allah samimi bir kalbi geri çevirmez.",
        "Urdu":       "امید مت ہارو۔ شاید صرف ایک دعا کی دوری ہے۔ اللہ سچے دل کو کبھی نہیں لوٹاتا۔",
        "Hindi":      "उम्मीद मत छोड़ो। शायद सिर्फ एक दुआ की दूरी है। अल्लाह सच्चे दिल को कभी नहीं लौटाता।",
        "Bengali":    "আশা হারিও না। তোমার এবং স্বস্তির মধ্যে হয়তো মাত্র একটি দুআ বাকি। আল্লাহ কখনো সৎ হৃদয়কে ফেরান না।",
        "Indonesian": "Jangan kehilangan harapan. Mungkin hanya satu doa antara kamu dan kelapangan. Allah tidak pernah menolak hati yang bersungguh-sungguh.",
        "Malay":      "Jangan putus harapan. Mungkin hanya satu doa yang memisahkan kamu dengan ketenangan. Allah tidak pernah menolak hati yang ikhlas.",
        "Persian":    "امید را از دست نده. شاید بین تو و آسایش فقط یک دعا فاصله است. الله هرگز دلی را که صادقانه او را می‌خواند رد نمی‌کند.",
        "Bosnian":    "Ne gubi nadu. Možda je samo jedna dova između tebe i olakšanja. Allah nikada ne odbija iskreno srce.",
        "Dutch":      "Verlies de hoop niet. Misschien is er maar één gebed tussen jou en verlichting. Allah wijst nooit een oprecht hart af.",
        "Swedish":    "Förlora inte hoppet. Det kanske bara är en bön mellan dig och lättnad. Allah avvisar aldrig ett uppriktigt hjärta.",
    },
    {
        "arabic": "بعد كلِّ عسرٍ يسر — يقيناً من الله. سورةُ الشَّرح قالتها مرَّتين: مع العسر يسر. تمسَّك.",
        "English":    "After every hardship comes ease — as a certainty from Allah. Surah Al-Inshirah says it twice: with hardship comes ease. Hold on.",
        "French":     "Après chaque difficulté vient la facilité — certitude d'Allah. La sourate Al-Inshirah le dit deux fois : avec la difficulté vient la facilité. Tiens bon.",
        "Russian":    "После каждой трудности приходит лёгкость — как уверенность от Аллаха. Сура Аш-Шарх говорит это дважды: вместе с трудностью приходит лёгкость. Держись.",
        "German":     "Nach jeder Schwierigkeit kommt Erleichterung — als Gewissheit von Allah. Sure Al-Inshirah sagt es zweimal: mit der Schwierigkeit kommt die Erleichterung. Halte durch.",
        "Spanish":    "Después de cada dificultad viene la facilidad — certeza de Allah. La Sura Al-Inshirah lo dice dos veces: con la dificultad viene la facilidad. Aguanta.",
        "Italian":    "Dopo ogni difficoltà viene la facilità — come certezza da Allah. La Sura Al-Inshirah lo dice due volte: con la difficoltà viene la facilità. Resisti.",
        "Turkish":    "Her zorluğun ardından kolaylık gelir — Allah'tan kesinlik olarak. İnşirah Suresi bunu iki kez söyler: zorlukla birlikte kolaylık vardır. Tutun.",
        "Urdu":       "ہر تکلیف کے بعد آسانی آتی ہے — اللہ کی طرف سے یقین کے ساتھ۔ سورۃ الانشراح نے دو بار کہا: تنگی کے ساتھ آسانی ہے۔ ڈٹے رہو۔",
        "Hindi":      "हर तकलीफ के बाद आसानी आती है — यकीन के साथ। सूरह इनशिराह ने दो बार कहा: तंगी के साथ आसानी है। डटे रहो।",
        "Bengali":    "প্রতিটি কষ্টের পরে সহজ আসে — আল্লাহর পক্ষ থেকে নিশ্চিতভাবে। সূরা ইনশিরাহ দুইবার বলেছে: কষ্টের সাথে সহজ আছে। ধরে থাকো।",
        "Indonesian": "Setelah setiap kesulitan datang kemudahan — kepastian dari Allah. Surah Al-Inshirah mengatakannya dua kali: bersama kesulitan ada kemudahan. Bertahanlah.",
        "Malay":      "Selepas setiap kesukaran datang kemudahan — kepastian dari Allah. Surah Al-Inshirah menyebutnya dua kali: bersama kesukaran ada kemudahan. Bertahanlah.",
        "Persian":    "بعد از هر سختی آسانی می‌آید — یقینی از الله. سوره الانشراح دو بار می‌گوید: با سختی آسانی است. مقاومت کن.",
        "Bosnian":    "Nakon svake teškoće dolazi olakšanje — kao sigurnost od Allaha. Sura Al-Inshirah to kaže dvaput: uz teškoću dolazi olakšanje. Izdrži.",
        "Dutch":      "Na elke moeilijkheid komt verlichting — als zekerheid van Allah. Sure Al-Inshirah zegt het tweemaal: met de moeilijkheid komt verlichting. Houd vol.",
        "Swedish":    "Efter varje svårighet kommer lättnad — som en visshet från Allah. Sure Al-Inshirah säger det två gånger: med svårigheten kommer lättnad. Håll ut.",
    },
    {
        "arabic": "رزقُكَ مكتوب. فرجُكَ آتٍ — كُتِبَ قبل أن تُولَد. اطمئنَّ. افعلْ ما بوسعِك وتوكَّل على الله.",
        "English":    "Your rizq is written. Your relief is coming — it was written before you were even born. Relax. Do your best and leave the rest to Allah.",
        "French":     "Ton rizq est écrit. Ton soulagement arrive — il était écrit avant même ta naissance. Détends-toi. Fais de ton mieux et laisse le reste à Allah.",
        "Russian":    "Твой ризк написан. Твоё облегчение придёт — оно было записано ещё до твоего рождения. Расслабься. Делай что можешь и остальное оставь Аллаху.",
        "German":     "Dein Rizq ist geschrieben. Deine Erleichterung kommt — sie wurde geschrieben, bevor du geboren wurdest. Entspann dich. Tu dein Bestes und überlasse den Rest Allah.",
        "Spanish":    "Tu rizq está escrito. Tu alivio viene — estaba escrito antes de que nacieras. Relájate. Haz lo mejor que puedas y deja el resto a Allah.",
        "Italian":    "Il tuo rizq è scritto. Il tuo sollievo sta arrivando — era scritto prima ancora che tu nascessi. Rilassati. Fai del tuo meglio e lascia il resto ad Allah.",
        "Turkish":    "Rızkın yazılmış. Rahatlaman geliyor — sen doğmadan önce yazılmıştı. Rahat ol. Elinden geleni yap, gerisini Allah'a bırak.",
        "Urdu":       "تمہارا رزق لکھا ہوا ہے۔ تمہاری راحت آنے والی ہے — پیدائش سے پہلے لکھی گئی تھی۔ سکون رکھو۔ بہترین کوشش کرو اور باقی اللہ پر چھوڑ دو۔",
        "Hindi":      "तुम्हारा रिज्क लिखा हुआ है। राहत आने वाली है — तुम्हारे पैदा होने से पहले लिखी गई थी। सकून रखो। बेहतरीन कोशिश करो और बाकी अल्लाह पर छोड़ दो।",
        "Bengali":    "তোমার রিজক লেখা আছে। তোমার স্বস্তি আসছে — তুমি জন্মানোর আগেই লেখা হয়েছিল। শান্ত থাকো। সর্বোত্তম চেষ্টা করো এবং বাকিটা আল্লাহর উপর ছেড়ে দাও।",
        "Indonesian": "Rezekimu sudah tertulis. Kelapanganmu akan datang — sudah ditulis sebelum kamu lahir. Tenang. Lakukan yang terbaik dan serahkan sisanya kepada Allah.",
        "Malay":      "Rezkimu sudah ditulis. Kelegaanmu akan datang — ditulis sebelum kamu dilahirkan. Tenang. Lakukan yang terbaik dan serahkan selebihnya kepada Allah.",
        "Persian":    "رزقت نوشته شده. آسایشت در راه است — قبل از تولدت نوشته شده بود. آرام باش. بهترین تلاشت را بکن و بقیه را به الله بسپار.",
        "Bosnian":    "Tvoj rizk je zapisan. Olakšanje dolazi — zapisano je prije nego što si se rodio. Opusti se. Uradi što možeš i ostalo prepusti Allahu.",
        "Dutch":      "Jouw rizq is opgeschreven. Jouw verlichting komt — het was opgeschreven voordat je zelfs maar geboren was. Ontspan. Doe je best en laat de rest aan Allah over.",
        "Swedish":    "Din rizq är skriven. Din lättnad kommer — den skrevs innan du ens var född. Slappna av. Gör ditt bästa och lämna resten till Allah.",
    },
    {
        "arabic": "إذا كان لديكَ اللهُ فلديكَ كلُّ شيء. الدُّنيا وما فيها زائل. لكنَّ رحمتَه أبدية ووعدَه حقّ.",
        "English":    "If Allah is all you have, you have everything. The world and all it contains is temporary. But His mercy is eternal and His promise is true.",
        "French":     "Si Allah est tout ce que tu as, tu as tout. Le monde et tout ce qu'il contient est temporaire. Mais Sa miséricorde est éternelle et Sa promesse est vraie.",
        "Russian":    "Если у тебя есть только Аллах, у тебя есть всё. Мир и всё в нём временно. Но Его милость вечна и Его обещание истинно.",
        "German":     "Wenn Allah alles ist, was du hast, hast du alles. Die Welt und alles, was sie enthält, ist vorübergehend. Aber Seine Barmherzigkeit ist ewig und Sein Versprechen ist wahr.",
        "Spanish":    "Si Allah es todo lo que tienes, lo tienes todo. El mundo y todo lo que contiene es temporal. Pero Su misericordia es eterna y Su promesa es verdadera.",
        "Italian":    "Se Allah è tutto ciò che hai, hai tutto. Il mondo e tutto ciò che contiene è temporaneo. Ma la Sua misericordia è eterna e la Sua promessa è vera.",
        "Turkish":    "Allah'tan başka hiçbir şeyin olmasa bile her şeyin var. Dünya ve içindeki her şey geçicidir. Ama O'nun rahmeti sonsuzdur ve vaadi gerçektir.",
        "Urdu":       "اگر اللہ تمہارے پاس سب کچھ ہے تو تمہارے پاس سب کچھ ہے۔ دنیا اور اس کی ہر چیز عارضی ہے۔ لیکن اس کی رحمت ابدی اور وعدہ سچا ہے۔",
        "Hindi":      "अगर अल्लाह तुम्हारे पास सब कुछ है तो सब कुछ है। दुनिया और इसकी हर चीज अस्थायी है। लेकिन उसकी रहमत अबदी और वादा सच्चा है।",
        "Bengali":    "যদি আল্লাহই তোমার সব হন, তাহলে তোমার কাছে সব আছে। দুনিয়া এবং এর সব কিছু সাময়িক। কিন্তু তাঁর রহমত চিরন্তন এবং তাঁর প্রতিশ্রুতি সত্য।",
        "Indonesian": "Jika Allah adalah satu-satunya yang kamu miliki, kamu memiliki segalanya. Dunia dan semua yang ada di dalamnya bersifat sementara. Tetapi rahmat-Nya abadi dan janji-Nya benar.",
        "Malay":      "Jika Allah adalah satu-satunya yang kamu miliki, kamu memiliki segalanya. Dunia dan semua yang ada di dalamnya adalah sementara. Tetapi rahmat-Nya kekal abadi dan janji-Nya benar.",
        "Persian":    "اگر الله تنها چیزی است که داری، همه چیز داری. دنیا و هر چه در آن است موقت است. اما رحمتش ابدی و وعده‌اش حق است.",
        "Bosnian":    "Ako imaš samo Allaha, imaš sve. Ovaj svijet i sve što sadrži je prolazno. Ali Njegova milost je vječna i Njegovo obećanje je istinito.",
        "Dutch":      "Als Allah alles is wat je hebt, heb je alles. De wereld en alles wat ze bevat is tijdelijk. Maar Zijn barmhartigheid is eeuwig en Zijn belofte is waar.",
        "Swedish":    "Om Allah är allt du har, har du allt. Världen och allt den innehåller är tillfälligt. Men Hans barmhärtighet är evig och Hans löfte är sant.",
    },
    {
        "arabic": "الشِّدَّةُ ليستْ عقاباً، بل هي إعداد. أكثرُ المؤمنين إيماناً كانوا أشدَّهم ابتلاءً. كُنْ صبوراً على نفسِك.",
        "English":    "Hardship is not punishment. It is preparation. The strongest believers were tested the most. Be patient with yourself.",
        "French":     "L'épreuve n'est pas une punition. C'est une préparation. Les croyants les plus forts ont été les plus testés. Sois patient avec toi-même.",
        "Russian":    "Трудности — это не наказание. Это подготовка. Самые сильные верующие были испытаны больше всего. Будь терпелив к себе.",
        "German":     "Schwierigkeiten sind keine Strafe. Sie sind Vorbereitung. Die stärksten Gläubigen wurden am meisten geprüft. Sei geduldig mit dir selbst.",
        "Spanish":    "Las dificultades no son un castigo. Son una preparación. Los creyentes más fuertes fueron los más probados. Sé paciente contigo mismo.",
        "Italian":    "Le difficoltà non sono una punizione. Sono una preparazione. I credenti più forti sono stati testati di più. Sii paziente con te stesso.",
        "Turkish":    "Zorluklar ceza değil, hazırlıktır. En güçlü müminler en çok sınandı. Kendine karşı sabırlı ol.",
        "Urdu":       "مشکل سزا نہیں تیاری ہے۔ سب سے مضبوط ایمان والوں کو سب سے زیادہ آزمایا گیا۔ اپنے آپ سے صبر کرو۔",
        "Hindi":      "मुश्किल सजा नहीं तैयारी है। सबसे मजबूत ईमान वालों को सबसे ज्यादा आजमाया गया। अपने आप से सब्र करो।",
        "Bengali":    "কষ্ট শাস্তি নয়, এটা প্রস্তুতি। সবচেয়ে শক্তিশালী মুমিনরা সবচেয়ে বেশি পরীক্ষিত হয়েছিল। নিজের প্রতি ধৈর্যশীল হও।",
        "Indonesian": "Kesulitan bukan hukuman. Ini adalah persiapan. Yang paling kuat imannya paling banyak diuji. Bersabarlah dengan dirimu sendiri.",
        "Malay":      "Kesukaran bukan hukuman. Ia adalah persediaan. Yang paling kuat imannya paling banyak diuji. Bersabarlah dengan dirimu sendiri.",
        "Persian":    "سختی‌ها مجازات نیستند، آماده‌سازی هستند. قوی‌ترین مؤمنان بیشترین آزمایش داشتند. با خودت صبور باش.",
        "Bosnian":    "Teškoće nisu kazna. One su priprema. Najjači vjernici su bili najviše iskušani. Budi strpljiv prema sebi.",
        "Dutch":      "Moeilijkheden zijn geen straf. Het is voorbereiding. De sterkste gelovigen werden het meest getest. Wees geduldig met jezelf.",
        "Swedish":    "Svårigheter är inte straff. Det är förberedelse. De starkaste troende prövades mest. Var tålmodig med dig själv.",
    },
    {
        "arabic": "أحياناً يؤخِّرُ اللهُ إجابتَك لا رفضاً لك، بل حمايةً لكَ ممَّا لا تراه. خطَّتُه أفضلُ من خطَّتك دائماً.",
        "English":    "Sometimes Allah delays His answer not to reject you, but to protect you from something you cannot see. His plan is always better than yours.",
        "French":     "Parfois Allah retarde Sa réponse non pour te rejeter, mais pour te protéger de quelque chose que tu ne vois pas. Son plan est toujours meilleur que le tien.",
        "Russian":    "Иногда Аллах задерживает Свой ответ не чтобы отвергнуть тебя, а чтобы защитить от того, чего ты не видишь. Его план всегда лучше твоего.",
        "German":     "Manchmal verzögert Allah Seine Antwort nicht, um dich abzuweisen, sondern um dich vor etwas zu schützen, das du nicht sehen kannst. Sein Plan ist immer besser als deiner.",
        "Spanish":    "A veces Allah retrasa Su respuesta no para rechazarte, sino para protegerte de algo que no puedes ver. Su plan siempre es mejor que el tuyo.",
        "Italian":    "A volte Allah ritarda la Sua risposta non per rifiutarti, ma per proteggerti da qualcosa che non puoi vedere. Il Suo piano è sempre migliore del tuo.",
        "Turkish":    "Bazen Allah cevabını geciktiriyor — seni reddetmek için değil, göremediğin bir şeyden korumak için. O'nun planı her zaman seninkinden daha iyidir.",
        "Urdu":       "کبھی کبھی اللہ جواب میں دیر کرتا ہے — تمہیں رد کرنے کے لیے نہیں، بلکہ تمہاری حفاظت کے لیے ان چیزوں سے جو تم نہیں دیکھ سکتے۔ اس کی منصوبہ بندی ہمیشہ بہتر ہے۔",
        "Hindi":      "कभी-कभी अल्लाह जवाब में देर करता है — तुम्हें रद्द करने के लिए नहीं, बल्कि तुम्हारी हिफाजत के लिए उन चीजों से जो तुम नहीं देख सकते। उसकी योजना हमेशा बेहतर है।",
        "Bengali":    "কখনো কখনো আল্লাহ তাঁর উত্তর দেরি করান — তোমাকে প্রত্যাখ্যান করতে নয়, বরং তোমাকে এমন কিছু থেকে রক্ষা করতে যা তুমি দেখতে পাচ্ছ না। তাঁর পরিকল্পনা সবসময় তোমার চেয়ে ভালো।",
        "Indonesian": "Terkadang Allah menunda jawaban-Nya bukan untuk menolakmu, tetapi untuk melindungimu dari sesuatu yang tidak bisa kamu lihat. Rencana-Nya selalu lebih baik dari rencanamu.",
        "Malay":      "Kadang-kadang Allah menangguhkan jawapan-Nya bukan untuk menolakmu, tetapi untuk melindungimu dari sesuatu yang tidak dapat kamu lihat. Rancangan-Nya sentiasa lebih baik dari rancanganmu.",
        "Persian":    "گاهی الله پاسخ را به تاخیر می‌اندازد نه برای رد کردنت، بلکه برای محافظت از چیزی که نمی‌بینی. برنامه‌اش همیشه از برنامه تو بهتر است.",
        "Bosnian":    "Ponekad Allah odgađa Svoj odgovor ne da bi te odbio, već da bi te zaštitio od nečega što ne možeš vidjeti. Njegov plan je uvijek bolji od tvog.",
        "Dutch":      "Soms vertraagt Allah Zijn antwoord niet om je af te wijzen, maar om je te beschermen tegen iets wat je niet kunt zien. Zijn plan is altijd beter dan het jouwe.",
        "Swedish":    "Ibland fördröjer Allah Sitt svar inte för att avvisa dig, utan för att skydda dig från något du inte kan se. Hans plan är alltid bättre än din.",
    },
    {
        "arabic": "كُنْ صبوراً على نفسِك. الشِّفاءُ ليس خطّاً مستقيماً. النُّموُّ ليس دائماً مرئياً. لكنَّ اللهَ يرى كلَّ جهدٍ تبذله مهما كان صغيراً.",
        "English":    "Be patient with yourself. Healing is not a straight line. Growth is not always visible. But Allah sees every effort you make, no matter how small.",
        "French":     "Sois patient avec toi-même. La guérison n'est pas une ligne droite. La croissance n'est pas toujours visible. Mais Allah voit chaque effort que tu fais, aussi petit soit-il.",
        "Russian":    "Будь терпелив к себе. Исцеление — это не прямая линия. Рост не всегда виден. Но Аллах видит каждое твоё усилие, каким бы малым оно ни было.",
        "German":     "Sei geduldig mit dir selbst. Heilung ist keine gerade Linie. Wachstum ist nicht immer sichtbar. Aber Allah sieht jede Anstrengung, die du unternimmst, egal wie klein sie ist.",
        "Spanish":    "Sé paciente contigo mismo. La sanación no es una línea recta. El crecimiento no siempre es visible. Pero Allah ve cada esfuerzo que haces, sin importar cuán pequeño sea.",
        "Italian":    "Sii paziente con te stesso. La guarigione non è una linea retta. La crescita non è sempre visibile. Ma Allah vede ogni sforzo che fai, non importa quanto piccolo.",
        "Turkish":    "Kendine karşı sabırlı ol. İyileşme düz bir çizgi değildir. Büyüme her zaman görünür değildir. Ama Allah, ne kadar küçük olursa olsun yaptığın her çabayı görür.",
        "Urdu":       "اپنے آپ سے صبر کرو۔ شفا سیدھی لکیر میں نہیں ہوتی۔ ترقی ہمیشہ نظر نہیں آتی۔ لیکن اللہ تمہاری ہر کوشش دیکھتا ہے، چاہے کتنی ہی چھوٹی کیوں نہ ہو۔",
        "Hindi":      "अपने आप से सब्र करो। शिफा सीधी लकीर में नहीं होती। तरक्की हमेशा नजर नहीं आती। लेकिन अल्लाह तुम्हारी हर कोशिश देखता है, चाहे कितनी ही छोटी क्यों न हो।",
        "Bengali":    "নিজের প্রতি ধৈর্যশীল হও। নিরাময় সরল রেখা নয়। বৃদ্ধি সবসময় দৃশ্যমান নয়। কিন্তু আল্লাহ তোমার প্রতিটি প্রচেষ্টা দেখেন, যত ছোটই হোক।",
        "Indonesian": "Bersabarlah dengan dirimu sendiri. Penyembuhan bukan garis lurus. Pertumbuhan tidak selalu terlihat. Tetapi Allah melihat setiap usaha yang kamu lakukan, sekecil apapun.",
        "Malay":      "Bersabarlah dengan dirimu sendiri. Penyembuhan bukan garis lurus. Pertumbuhan tidak selalu kelihatan. Tetapi Allah melihat setiap usaha yang kamu lakukan, walau sekecil manapun.",
        "Persian":    "با خودت صبور باش. بهبودی یک خط مستقیم نیست. رشد همیشه قابل مشاهده نیست. اما الله هر تلاشی را که می‌کنی می‌بیند، هر چقدر هم کوچک باشد.",
        "Bosnian":    "Budi strpljiv prema sebi. Ozdravljenje nije ravna linija. Rast nije uvijek vidljiv. Ali Allah vidi svaki napor koji uložiš, bez obzira koliko mali bio.",
        "Dutch":      "Wees geduldig met jezelf. Genezing is geen rechte lijn. Groei is niet altijd zichtbaar. Maar Allah ziet elke inspanning die je levert, hoe klein ook.",
        "Swedish":    "Var tålmodig med dig själv. Läkning är inte en rak linje. Tillväxt är inte alltid synlig. Men Allah ser varje ansträngning du gör, oavsett hur liten den är.",
    },
]

def fmt_msg(lang):
    msg = random.choice(MESSAGES)
    t = f"*A Reminder for You*\n\n{msg['arabic']}\n\n"
    if lang != "Arabic":
        translation = msg.get(lang, msg.get("English", ""))
        t += f"_{translation}_\n\n"
    t += f"{SEP}\n{FOOTER}"
    return t


def fmt_taf(d):
    if not d: return "Could not fetch tafseer. Please try again."
    return f"*{d['surah']}:{d['ayah']}*\n\n{d['arabic']}\n\n*التفسير — المختصر في التفسير:*\n{d['tafseer']}\n\n{SEP}\n{FOOTER}"

def lang_kb():
    kb, row = [], []
    for lang, info in LANGUAGES.items():
        row.append(InlineKeyboardButton(f"{info['flag']} {lang}", callback_data=f"sl_{lang}"))
        if len(row) == 2: kb.append(row); row = []
    if row: kb.append(row)
    return InlineKeyboardMarkup(kb)

# ── COMMAND HANDLERS ───────────────────────────────────────────────────────────
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(u.effective_user.id)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Choose Your Language", callback_data="choose_lang")],
        [InlineKeyboardButton("Random Verse", callback_data="cb_rand"),
         InlineKeyboardButton("Random Dua",   callback_data="cb_dua")],
        [InlineKeyboardButton("Motivational Reminder", callback_data="cb_msg")],
    ])
    await u.message.reply_text(
        f"*Welcome to QuranCompanion*\n\nYour daily companion for the Quran.\n\n"
        f"Current language: *{lang}*\n\n*Commands:*\n"
        f"/random — Random verse\n/verse 2:255 — Specific verse\n"
        f"/surah 36 — Surah info\n/tafseer 2:255 — Tafseer\n"
        f"/randomtafseer — Random tafseer\n/dua — Random dua\n"
        f"/message — Motivational reminder\n/change — Change language\n"
        f"/daily — Daily verse\n/clear — Clear chat\n"
        f"/restart — Restart\n/about — About\n\n_Type / to see all commands_",
        parse_mode='Markdown', reply_markup=kb)

async def cmd_random(u: Update, c: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(u.effective_user.id)
    m = await u.message.reply_text("Fetching a verse...")
    await m.edit_text(fmt_verse(fetch_random(lang), lang), parse_mode='Markdown')

async def cmd_verse(u: Update, c: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(u.effective_user.id)
    if not c.args: await u.message.reply_text("Example: /verse 2:255"); return
    try:
        s, a = c.args[0].split(':'); s, a = int(s), int(a)
        if not 1 <= s <= 114: raise ValueError
    except: await u.message.reply_text("Invalid format. Use: /verse 2:255"); return
    m = await u.message.reply_text("Fetching verse...")
    await m.edit_text(fmt_verse(fetch_verse(s, a, lang), lang), parse_mode='Markdown')

async def cmd_surah(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not c.args: await u.message.reply_text("Example: /surah 36"); return
    try:
        n = int(c.args[0])
        if not 1 <= n <= 114: raise ValueError
    except: await u.message.reply_text("Invalid number. Must be between 1 and 114."); return
    m = await u.message.reply_text("Fetching surah info...")
    info = fetch_surah_info(n)
    if not info: await m.edit_text("Could not fetch surah info. Please try again."); return
    await m.edit_text(
        f"*{info['name']} — {info['arabic_name']}*\n\nMeaning: _{info['meaning']}_\n"
        f"Number: {info['num']}\nVerses: {info['verses']}\nRevealed: {info['revelation']}\n\n{SEP}\n{FOOTER}",
        parse_mode='Markdown')

async def cmd_tafseer(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not c.args: await u.message.reply_text("Example: /tafseer 2:255"); return
    try: s, a = c.args[0].split(':'); s, a = int(s), int(a)
    except: await u.message.reply_text("Invalid format. Use: /tafseer 2:255"); return
    m = await u.message.reply_text("Fetching tafseer...")
    await m.edit_text(fmt_taf(fetch_tafseer(s, a)), parse_mode='Markdown')

async def cmd_randomtafseer(u: Update, c: ContextTypes.DEFAULT_TYPE):
    m = await u.message.reply_text("Fetching a random tafseer...")
    s = random.randint(1, 114)
    try:
        r = requests.get(f"https://api.quran.com/api/v4/chapters/{s}", timeout=10)
        count = r.json().get('chapter', {}).get('verses_count', 7) if r.status_code == 200 else 7
        a = random.randint(1, count)
    except: s, a = 2, 255
    await m.edit_text(fmt_taf(fetch_tafseer(s, a)), parse_mode='Markdown')

async def cmd_dua(u: Update, c: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(u.effective_user.id)
    await u.message.reply_text(fmt_dua(random.choice(DUAS), lang), parse_mode='Markdown')

async def cmd_message(u: Update, c: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(u.effective_user.id)
    await u.message.reply_text(fmt_msg(lang), parse_mode='Markdown')

async def cmd_change(u: Update, c: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(u.effective_user.id)
    await u.message.reply_text(
        f"*Choose Your Language*\n\nCurrent: *{lang}*\n\nSelect from the list below:",
        parse_mode='Markdown', reply_markup=lang_kb())

async def cmd_daily(u: Update, c: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(u.effective_user.id)
    await u.message.reply_text(
        f"*Daily Verse*\n\nSubscribed to daily verse in *{lang}*.\n\n{FOOTER}",
        parse_mode='Markdown')

async def cmd_clear(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(
        f"*Clear Chat*\n\nPress and hold the chat name at the top, then select *Clear History*.\n\n{FOOTER}",
        parse_mode='Markdown')

async def cmd_restart(u: Update, c: ContextTypes.DEFAULT_TYPE):
    user_languages.pop(u.effective_user.id, None)
    await u.message.reply_text(
        f"*Bot restarted*\n\nLanguage reset to English. Use /change to choose your language again.\n\n{FOOTER}",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Choose Language", callback_data="choose_lang")
        ]]))

async def cmd_about(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(
        f"*About QuranCompanion*\n\n"
        f"QuranCompanion helps you connect with the Quran daily — "
        f"verses, tafseer, duas and motivational reminders in your language.\n\n"
        f"{SEP}\nDeveloped by: {AUTHOR}\nTelegram: @rocks\n\n"
        f"May Allah accept this work and make it beneficial for all Muslims.\n{SEP}",
        parse_mode='Markdown')

async def btn(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query
    await q.answer()
    uid = q.from_user.id
    d = q.data
    lang = get_lang(uid)
    if d == "choose_lang":
        await q.edit_message_text(
            f"*Choose Your Language*\n\nCurrent: *{lang}*\n\nSelect from the list below:",
            parse_mode='Markdown', reply_markup=lang_kb())
    elif d == "cb_rand":
        await q.edit_message_text("Fetching a verse...")
        await q.edit_message_text(fmt_verse(fetch_random(lang), lang), parse_mode='Markdown')
    elif d == "cb_dua":
        await q.edit_message_text(fmt_dua(random.choice(DUAS), lang), parse_mode='Markdown')
    elif d == "cb_msg":
        await q.edit_message_text(fmt_msg(lang), parse_mode='Markdown')
    elif d.startswith("sl_"):
        new_lang = d[3:]
        if new_lang in LANGUAGES:
            set_lang(uid, new_lang)
            flag = LANGUAGES[new_lang]['flag']
            await q.edit_message_text(
                f"*Language set to {flag} {new_lang}*\n\n"
                f"All verses, duas and reminders will now appear in *{new_lang}*.\n\nWhat would you like to do?",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Random Verse", callback_data="cb_rand"),
                     InlineKeyboardButton("Random Dua",   callback_data="cb_dua")],
                    [InlineKeyboardButton("Motivational Reminder", callback_data="cb_msg")],
                ]))

async def on_error(u, c): logging.error(f"Error: {c.error}")

async def on_start(app):
    cmds = [
        BotCommand("start",         "Welcome and quick access"),
        BotCommand("random",        "Get a random Quran verse"),
        BotCommand("verse",         "Specific verse — /verse 2:255"),
        BotCommand("surah",         "Surah info — /surah 36"),
        BotCommand("tafseer",       "Tafseer — /tafseer 2:255"),
        BotCommand("randomtafseer", "Random verse with tafseer"),
        BotCommand("dua",           "Random authentic dua"),
        BotCommand("message",       "Motivational Islamic reminder"),
        BotCommand("change",        "Change your language"),
        BotCommand("daily",         "Subscribe to daily verse"),
        BotCommand("clear",         "How to clear chat"),
        BotCommand("restart",       "Restart and reset language"),
        BotCommand("about",         "About QuranCompanion"),
    ]
    await app.bot.set_my_commands(cmds)
    print("  Commands registered.")

def main():
    print("=" * 55)
    print(f"  QuranCompanion v{VERSION} — by {AUTHOR}")
    print(f"  Languages: {', '.join(LANGUAGES.keys())}")
    print("  Starting...")
    print("=" * 55)
    app = Application.builder().token(TOKEN).post_init(on_start).build()
    app.add_handler(CommandHandler("start",         start))
    app.add_handler(CommandHandler("random",        cmd_random))
    app.add_handler(CommandHandler("verse",         cmd_verse))
    app.add_handler(CommandHandler("surah",         cmd_surah))
    app.add_handler(CommandHandler("tafseer",       cmd_tafseer))
    app.add_handler(CommandHandler("randomtafseer", cmd_randomtafseer))
    app.add_handler(CommandHandler("dua",           cmd_dua))
    app.add_handler(CommandHandler("message",       cmd_message))
    app.add_handler(CommandHandler("change",        cmd_change))
    app.add_handler(CommandHandler("daily",         cmd_daily))
    app.add_handler(CommandHandler("clear",         cmd_clear))
    app.add_handler(CommandHandler("restart",       cmd_restart))
    app.add_handler(CommandHandler("about",         cmd_about))
    app.add_handler(CallbackQueryHandler(btn))
    app.add_error_handler(on_error)
    print(f"  Bot running! Search @quran_companion_bot on Telegram")
    print("=" * 55)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()