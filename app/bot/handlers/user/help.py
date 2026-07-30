"""/help — yordam matni va komandalar ro'yxati."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="user.help")

_USER_HELP = (
    "ℹ️ <b>@nmsupportbot — yordam</b>\n\n"
    "<b>📚 Asosiy buyruqlar</b>\n"
    "  • /start — botni ishga tushirish va asosiy menyu\n"
    "  • /help — shu yordam matni\n\n"
    "<b>🕌 Bot nima qiladi?</b>\n"
    "  • Yer yuzining <i>istalgan joyi</i> uchun namoz vaqtlarini ko'rsatadi\n"
    "  • Hudud lokatsiya orqali yoki ro'yxatdan tanlanadi\n"
    "  • 5 ta hududga obuna bo'lib, har biriga DM ga kunlik post olish mumkin\n"
    "  • Farz vaqti kirganda DM ga eslatma keladi (sozlamalardan o'chirish mumkin)\n"
    "  • Tahajjud / Ishroq / Zuho / Avvobiyn vaqtlari hisoblab beriladi\n\n"
    "<b>⚙️ Sozlamalar</b>\n"
    "  Asosiy menyu → ⚙️ Sozlamalar — eslatma turlarini yoqib/o'chirish\n\n"
    "<b>📍 Yangi hudud qo'shish</b>\n"
    "  Asosiy menyu → 📍 Hudud tanlash\n\n"
    "<i>Savol va takliflar uchun adminga yozing.</i>"
)

_ADMIN_HELP = (
    "\n\n<b>👑 Admin buyruqlari</b>\n"
    "  • /admin — admin paneli (inline menyu)\n"
    "  • /stats — statistika\n"
    "  • /test_post — kunlik post pipeline'ni darhol ishga tushirish\n"
    "  • /broadcast — barcha aktiv userlarga xabar (tasdiq bilan)\n"
    "  • /cancel — joriy FSM oqimni bekor qilish"
)


@router.message(Command("help"))
async def cmd_help(message: Message, is_admin: bool = False) -> None:
    text = _USER_HELP
    if is_admin:
        text += _ADMIN_HELP
    await message.answer(text, disable_web_page_preview=True)
