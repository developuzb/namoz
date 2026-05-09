"""Loyiha bo'yicha o'zgarmas qiymatlar."""
from __future__ import annotations

# ============== Namozlar ==============

#: Farz namozlari (bildirishnoma yuboriladiganlar)
FARZ_PRAYERS: tuple[str, ...] = ("Bomdod", "Peshin", "Asr", "Shom", "Xufton")

#: Vaqtlar jadvalida ko'rinadigan barcha namozlar
ALL_PRAYERS: tuple[str, ...] = ("Bomdod", "Quyosh", "Peshin", "Asr", "Shom", "Xufton")

#: Nafl namozlari
NAFL_PRAYERS: tuple[str, ...] = ("Tahajjud", "Ishroq", "Zuho", "Avvobiyn")

#: Nafl namozlari uchun ikonkalar
NAFL_ICONS: dict[str, str] = {
    "Tahajjud": "🌙",
    "Ishroq": "☀️",
    "Zuho": "🌤",
    "Avvobiyn": "🌇",
}

# ============== Sana / vaqt ==============

#: Hafta kunlari (O'zbekcha)
WEEKDAYS_UZ: tuple[str, ...] = (
    "Dushanba",
    "Seshanba",
    "Chorshanba",
    "Payshanba",
    "Juma",
    "Shanba",
    "Yakshanba",
)

#: Milodiy oylar (O'zbekcha)
MONTHS_UZ: dict[int, str] = {
    1: "yanvar",
    2: "fevral",
    3: "mart",
    4: "aprel",
    5: "may",
    6: "iyun",
    7: "iyul",
    8: "avgust",
    9: "sentyabr",
    10: "oktyabr",
    11: "noyabr",
    12: "dekabr",
}

#: Hijriy oylar (O'zbekcha)
HIJRI_MONTHS_UZ: dict[int, str] = {
    1: "muharram",
    2: "safar",
    3: "robi'ul avval",
    4: "robi'us soniy",
    5: "jumodul avval",
    6: "jumodus soniy",
    7: "rajab",
    8: "sha'bon",
    9: "ramazon",
    10: "shavvol",
    11: "zulqa'da",
    12: "zulhijja",
}

# ============== Provider mapping ==============

#: islomapi.uz va praytime.uz dan kelgan kalitlarni
#: ichki standart nomlarga aylantirish
PROVIDER_LABEL_MAP: dict[str, str] = {
    # islomapi.uz
    "tong_saharlik": "Bomdod",
    "quyosh": "Quyosh",
    "peshin": "Peshin",
    "asr": "Asr",
    "shom_iftor": "Shom",
    "hufton": "Xufton",
    "xufton": "Xufton",
    # praytime.uz / boshqalar
    "Tong": "Bomdod",
    "Bomdod": "Bomdod",
    "Quyosh": "Quyosh",
    "Peshin": "Peshin",
    "Asr": "Asr",
    "Shom": "Shom",
    "Xufton": "Xufton",
    "Hufton": "Xufton",
}

# ============== Qur'on oyati (post oxirida) ==============

VERSE_AR: str = "إِنَّ الصَّلَاةَ كَانَتْ عَلَى الْمُؤْمِنِينَ كِتَابًا مَوْقُوتًا"
VERSE_UZ: str = "Namoz mo'minlarga vaqt bilan farz qilindi."
VERSE_REF: str = "Niso 4:103"

# ============== Tashqi havolalar ==============

NAFL_GUIDE_URL: str = "https://telegra.ph/Nafl-nima---Qanday-oqiladi-08-25"

# ============== Cache / limit ==============

#: Provider javobini necha sekund cache da saqlash
PROVIDER_CACHE_TTL: int = 3600  # 1 soat

#: Bir foydalanuvchi uchun obuna chegarasi
MAX_SUBSCRIPTIONS_PER_USER: int = 5
