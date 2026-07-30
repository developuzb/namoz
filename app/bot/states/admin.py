"""Admin va user FSM holatlari."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class MasjidTimeFSM(StatesGroup):
    """Masjid vaqtini tahrirlash oqimi."""

    choosing_region = State()
    choosing_prayer = State()
    entering_time = State()


class ChannelFSM(StatesGroup):
    """Kanal qo'shish va tahrirlash oqimi."""

    waiting_forward = State()
    choosing_region = State()
    entering_link = State()
    entering_caption_template = State()
    # Tahrirlash (mavjud kanal)
    editing_link = State()
    editing_title = State()


class BroadcastFSM(StatesGroup):
    """Broadcast yuborish oqimi."""

    composing = State()
    confirming = State()


class SearchFSM(StatesGroup):
    """Region nomini qidirish oqimi (user uchun)."""

    querying = State()
