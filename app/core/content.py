"""Quron oyatlari va dua'lar — caption uchun har kuni boshqacha mazmun.

Sana asosida tanlanadi (`target_date.toordinal() % len(...)`) — har kuni bitta
ayat va bitta dua aylanadi.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Ayah:
    arabic: str
    uzbek: str
    ref: str  # "Niso 4:103" kabi


@dataclass(frozen=True, slots=True)
class Dua:
    arabic: str
    uzbek: str
    ref: str | None = None


# ============== Namoz haqida 15 ta oyat ==============
QURAN_AYAHS_PRAYER: tuple[Ayah, ...] = (
    Ayah(
        arabic="إِنَّ الصَّلَاةَ كَانَتْ عَلَى الْمُؤْمِنِينَ كِتَابًا مَوْقُوتًا",
        uzbek="Namoz mo'minlarga vaqt bilan farz qilindi.",
        ref="Niso 4:103",
    ),
    Ayah(
        arabic="وَاسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ",
        uzbek="Sabr va namoz bilan yordam so'rang.",
        ref="Baqara 2:45",
    ),
    Ayah(
        arabic="وَأَقِمِ الصَّلَاةَ لِذِكْرِي",
        uzbek="Meni yodga olish uchun namoz o'qi.",
        ref="Toha 20:14",
    ),
    Ayah(
        arabic="إِنَّ الصَّلَاةَ تَنْهَىٰ عَنِ الْفَحْشَاءِ وَالْمُنكَرِ",
        uzbek="Albatta, namoz fahsh va munkar ishlardan saqlaydi.",
        ref="Ankabut 29:45",
    ),
    Ayah(
        arabic="حَافِظُوا عَلَى الصَّلَوَاتِ وَالصَّلَاةِ الْوُسْطَىٰ",
        uzbek="Namozlarni va o'rta namozni saqlangiz.",
        ref="Baqara 2:238",
    ),
    Ayah(
        arabic="وَأَقِيمُوا الصَّلَاةَ وَآتُوا الزَّكَاةَ وَارْكَعُوا مَعَ الرَّاكِعِينَ",
        uzbek="Namoz o'qing, zakot bering, ruku' qiluvchilar bilan ruku' qiling.",
        ref="Baqara 2:43",
    ),
    Ayah(
        arabic="قَدْ أَفْلَحَ الْمُؤْمِنُونَ ۝ الَّذِينَ هُمْ فِي صَلَاتِهِمْ خَاشِعُونَ",
        uzbek="Mo'minlar najot topdilar — namozlarida xushu' qiluvchilar.",
        ref="Mu'minun 23:1-2",
    ),
    Ayah(
        arabic="وَالَّذِينَ هُمْ عَلَىٰ صَلَوَاتِهِمْ يُحَافِظُونَ",
        uzbek="Va ular namozlarini muhofaza qiladilar.",
        ref="Mu'minun 23:9",
    ),
    Ayah(
        arabic="فَاسْجُدْ لِلَّهِ وَاعْبُدْ",
        uzbek="Bas, Allohga sajda qil va ibodat qil.",
        ref="Najm 53:62",
    ),
    Ayah(
        arabic="وَأَقِمِ الصَّلَاةَ طَرَفَيِ النَّهَارِ وَزُلَفًا مِّنَ اللَّيْلِ",
        uzbek="Namozni kunning ikki tomonida va kechaning bir qismida o'qi.",
        ref="Hud 11:114",
    ),
    Ayah(
        arabic="فَوَيْلٌ لِّلْمُصَلِّينَ ۝ الَّذِينَ هُمْ عَن صَلَاتِهِمْ سَاهُونَ",
        uzbek="Voy, namozlaridan g'ofil bo'lgan namozxonlarning holiga.",
        ref="Mo'un 107:4-5",
    ),
    Ayah(
        arabic="إِلَّا الْمُصَلِّينَ ۝ الَّذِينَ هُمْ عَلَىٰ صَلَاتِهِمْ دَائِمُونَ",
        uzbek="Faqat namozxonlar — namozlariga doimiy bo'ladiganlar bundan mustasno.",
        ref="Ma'orij 70:22-23",
    ),
    Ayah(
        arabic="يَا أَيُّهَا الَّذِينَ آمَنُوا اسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ ۚ إِنَّ اللَّهَ مَعَ الصَّابِرِينَ",
        uzbek="Ey iymon keltirganlar! Sabr va namoz bilan yordam so'rang. Albatta, Alloh sabr qiluvchilar bilandir.",
        ref="Baqara 2:153",
    ),
    Ayah(
        arabic="إِنَّ فِي ذَٰلِكَ لَذِكْرَىٰ لِمَن كَانَ لَهُ قَلْبٌ",
        uzbek="Albatta, bunda qalbi bor odam uchun ibrat bordir.",
        ref="Qof 50:37",
    ),
    Ayah(
        arabic="وَاذْكُرُوا اللَّهَ كَثِيرًا لَّعَلَّكُمْ تُفْلِحُونَ",
        uzbek="Allohni ko'p yodga oling — najot topishingiz mumkin.",
        ref="Anfol 8:45",
    ),
)


# ============== 10 ta qisqa dua ==============
DUAS: tuple[Dua, ...] = (
    Dua(
        arabic="رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ",
        uzbek="Robbimiz! Bizga dunyoda ham yaxshilik, oxiratda ham yaxshilik ber va bizni jahannam azobidan saqla.",
        ref="Baqara 2:201",
    ),
    Dua(
        arabic="رَبِّ اجْعَلْنِي مُقِيمَ الصَّلَاةِ وَمِن ذُرِّيَّتِي",
        uzbek="Robbim! Meni va zurriyotimni namozni qoim qiluvchi qilgin.",
        ref="Ibrohim 14:40",
    ),
    Dua(
        arabic="رَبِّ زِدْنِي عِلْمًا",
        uzbek="Robbim! Mening ilmimni ko'paytirgin.",
        ref="Toha 20:114",
    ),
    Dua(
        arabic="اللَّهُمَّ أَعِنِّي عَلَى ذِكْرِكَ وَشُكْرِكَ وَحُسْنِ عِبَادَتِكَ",
        uzbek="Allohim! Seni zikr qilish, Senga shukr aytish va Senga chiroyli ibodat qilishda menga yordam ber.",
        ref=None,
    ),
    Dua(
        arabic="رَبَّنَا لَا تُؤَاخِذْنَا إِن نَّسِينَا أَوْ أَخْطَأْنَا",
        uzbek="Robbimiz! Agar unutgan yoki xato qilgan bo'lsak, bizni javobgar qilma.",
        ref="Baqara 2:286",
    ),
    Dua(
        arabic="رَبَّنَا اغْفِرْ لِي وَلِوَالِدَيَّ وَلِلْمُؤْمِنِينَ يَوْمَ يَقُومُ الْحِسَابُ",
        uzbek="Robbim! Hisob qilinadigan kunda meni, ota-onamni va mo'minlarni mag'firat qilgin.",
        ref="Ibrohim 14:41",
    ),
    Dua(
        arabic="اللَّهُمَّ إِنِّي أَسْأَلُكَ الْعَفْوَ وَالْعَافِيَةَ فِي الدُّنْيَا وَالْآخِرَةِ",
        uzbek="Allohim! Sendan dunyo va oxiratda afv va sog'liqni so'rayman.",
        ref=None,
    ),
    Dua(
        arabic="رَبَّنَا أَفْرِغْ عَلَيْنَا صَبْرًا وَثَبِّتْ أَقْدَامَنَا",
        uzbek="Robbimiz! Ustimizdan sabr to'kib ber va qadamlarimizni mustahkam qil.",
        ref="Baqara 2:250",
    ),
    Dua(
        arabic="اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْهَمِّ وَالْحَزَنِ",
        uzbek="Allohim! Senga g'am va qayg'udan panoh tilayman.",
        ref=None,
    ),
    Dua(
        arabic="حَسْبُنَا اللَّهُ وَنِعْمَ الْوَكِيلُ",
        uzbek="Bizga Alloh kifoyadir va U eng yaxshi vakildir.",
        ref="Imron 3:173",
    ),
)


@dataclass(frozen=True, slots=True)
class Hadith:
    text_uz: str
    source: str  # "Buxoriy" / "Muslim" / "Tirmiziy" / etc.


# ============== 12 ta qisqa hadis (asosan namoz haqida) ==============
HADITHS: tuple[Hadith, ...] = (
    Hadith(
        text_uz="«Mo'min va kofir o'rtasidagi farq — namozni tark qilishdir.»",
        source="Muslim",
    ),
    Hadith(
        text_uz="«Qiyomat kunida bandadan so'raladigan birinchi narsa namoz bo'ladi.»",
        source="Tirmiziy",
    ),
    Hadith(
        text_uz="«Beshta namoz — eshik oldidan oqib turgan daryo kabi: u kuniga besh marta cho'milgan kishi tanasida hech qanday kir qolmaydi.»",
        source="Buxoriy va Muslim",
    ),
    Hadith(
        text_uz="«Eng yaxshi amal — vaqtida o'qilgan namoz.»",
        source="Buxoriy",
    ),
    Hadith(
        text_uz="«Kim ikki sovuq vaqtni (Bomdod va Asrni) o'qisa, jannatga kiradi.»",
        source="Buxoriy",
    ),
    Hadith(
        text_uz="«Jamoat namozi yolg'iz o'qilgan namozdan yigirma yetti baravar afzal.»",
        source="Buxoriy va Muslim",
    ),
    Hadith(
        text_uz="«Bandaning Robbiga eng yaqin holati — sajda holatidir.»",
        source="Muslim",
    ),
    Hadith(
        text_uz="«Juma kuni — kunlarning eng yaxshisidir. O'sha kunda Odam alayhissalom yaratilgan.»",
        source="Muslim",
    ),
    Hadith(
        text_uz="«Kim chiroyli tahorat olib, namoz o'qisa, oldingi kichik gunohlari kechiriladi.»",
        source="Buxoriy va Muslim",
    ),
    Hadith(
        text_uz="«Vitr namozini saqlanglar — bu Allohning sizga sevimli sovg'asidir.»",
        source="Tirmiziy",
    ),
    Hadith(
        text_uz="«Kim Bomdoddan keyin masjidda quyosh chiqquncha o'tirib zikr qilsa, bir to'liq haj va umra savobiga ega bo'ladi.»",
        source="Tirmiziy",
    ),
    Hadith(
        text_uz="«Ey o'g'lim! Namozni qoim qil — bu eng buyuk amaldir.»",
        source="Luqmonning o'g'liga vasiyati — Luqmon 31:17",
    ),
)


def get_daily_ayah(day_ordinal: int) -> Ayah:
    """Bugungi sanaga ko'ra rotating oyat tanlaydi."""
    return QURAN_AYAHS_PRAYER[day_ordinal % len(QURAN_AYAHS_PRAYER)]


def get_daily_dua(day_ordinal: int) -> Dua:
    """Bugungi sanaga ko'ra rotating dua tanlaydi."""
    return DUAS[day_ordinal % len(DUAS)]


def get_daily_hadith(day_ordinal: int) -> Hadith:
    """Bugungi sanaga ko'ra rotating hadis tanlaydi."""
    return HADITHS[day_ordinal % len(HADITHS)]


__all__ = [
    "Ayah",
    "DUAS",
    "Dua",
    "HADITHS",
    "Hadith",
    "QURAN_AYAHS_PRAYER",
    "get_daily_ayah",
    "get_daily_dua",
    "get_daily_hadith",
]
