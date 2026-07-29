"""Google Sheets sync — Sheets'dan doimiy xotira (persistent storage) sifatida.

Uch vazifa:
  1. **Export** (DB → Sheets): har SHEETS_SYNC_INTERVAL_MIN daqiqada barcha
     jadvallar alohida varaqlarga yoziladi. Sheets — doimiy nusxa.
  2. **Pull** (Sheets → DB, faqat MasjidTimes): jadvaldagi qo'lda
     o'zgartirilgan masjid vaqtlarini bot avtomatik o'qib DB ga oladi.
  3. **Restore** (Sheets → DB, to'liq): DB bo'sh bo'lsa (yangi server,
     dyno restart, disk yo'qolgan) — Users/Subscriptions/Regions/Channels/
     GroupChats/MasjidTimes varaqlaridan to'liq tiklanadi.

Sozlash:
  1. Google Cloud'da Service Account yaratib, JSON kalitni
     `data/google_sa.json` ga qo'ying (GOOGLE_SA_JSON bilan o'zgartirsa bo'ladi).
  2. Sheet yaratib, uni service account emailiga "Editor" qilib ulashing.
  3. .env ga GOOGLE_SHEET_ID=<sheet id> yozing.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logger import logger
from app.db.session import get_session

#: PostLog uchun oxirgi nechta yozuv sync qilinadi
_POST_LOG_LIMIT = 1000


def _cell(v: object) -> object:
    """SQLAlchemy qiymatini Sheets katakka mos ko'rinishga keltiradi."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, datetime):
        return v.isoformat(sep=" ", timespec="seconds")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, (int, float)):
        return v
    return str(v)


def _restore_plans() -> list[tuple[str, type]]:
    """Tiklanadigan jadvallar — FK bog'liqlik tartibida."""
    from app.db.models.channel import Channel
    from app.db.models.masjid_time import MasjidTime
    from app.db.models.region import Region
    from app.db.models.subscribed_chat import SubscribedChat
    from app.db.models.subscription import Subscription
    from app.db.models.user import User

    return [
        ("Regions", Region),
        ("Users", User),
        ("Channels", Channel),
        ("GroupChats", SubscribedChat),
        ("Subscriptions", Subscription),
        ("MasjidTimes", MasjidTime),
    ]


async def _collect() -> dict[str, list[list[object]]]:
    """Barcha jadvallarni {varaq_nomi: [[header], [row], ...]} ko'rinishda yig'adi."""
    from app.db.models.post_log import PostLog

    plans: list[tuple[str, type, int | None]] = [
        *[(name, model, None) for name, model in _restore_plans()],
        ("PostLogs", PostLog, _POST_LOG_LIMIT),
    ]

    out: dict[str, list[list[object]]] = {}
    async with get_session() as session:
        for name, model, limit in plans:
            cols = [c.name for c in model.__table__.columns]
            stmt = select(model)
            if limit:
                pk = next(iter(model.__table__.primary_key.columns))
                stmt = stmt.order_by(pk.desc()).limit(limit)
            objs = (await session.execute(stmt)).scalars().all()
            out[name] = [list(cols)] + [
                [_cell(getattr(o, c)) for c in cols] for o in objs
            ]
    return out


def _push(sheet_id: str, sa_path: str, data: dict[str, list[list[object]]]) -> None:
    """Sinxron gspread bilan yozish — asyncio.to_thread ichida chaqiriladi."""
    import gspread

    gc = gspread.service_account(filename=sa_path)
    sh = gc.open_by_key(sheet_id)

    def _get_ws(title: str, rows: int, cols: int):
        try:
            return sh.worksheet(title)
        except gspread.WorksheetNotFound:
            return sh.add_worksheet(title=title, rows=rows, cols=cols)

    for name, rows in data.items():
        ws = _get_ws(name, rows=max(len(rows) + 10, 50), cols=max(len(rows[0]) + 2, 10))
        ws.clear()
        ws.update(values=rows, range_name="A1")

    meta = _get_ws("_sync", rows=4, cols=4)
    meta.update(
        values=[[
            "Oxirgi sync",
            datetime.now().isoformat(sep=" ", timespec="seconds"),
        ]],
        range_name="A1",
    )


def _create_spreadsheet(sa_path: str, owner_email: str) -> str:
    """Yangi spreadsheet yaratadi (service account nomidan) va egasiga ulashadi.

    Sinxron — asyncio.to_thread ichida chaqiriladi. Drive API yoqilgan
    bo'lishi kerak.
    """
    import gspread

    gc = gspread.service_account(filename=sa_path)
    sh = gc.create("TAQVIMbot — ma'lumotlar bazasi")
    if owner_email:
        sh.share(owner_email, perm_type="user", role="writer", notify=True)
    return sh.id


async def _ensure_sheet_id() -> str | None:
    """Sheet ID ni topadi: .env → data/sheet_id.txt → yangi yaratish."""
    settings = get_settings()

    sid = settings.GOOGLE_SHEET_ID.strip()
    if sid:
        return sid

    f = settings.sheet_id_file
    if f.exists():
        sid = f.read_text(encoding="utf-8").strip()
        if sid:
            return sid

    if not settings.google_sa_path.exists():
        return None

    sid = await asyncio.to_thread(
        _create_spreadsheet,
        str(settings.google_sa_path),
        settings.GOOGLE_SHEET_OWNER_EMAIL.strip(),
    )
    f.write_text(sid, encoding="utf-8")
    logger.info(
        "🆕 Google Sheet yaratildi va {} ga ulashildi: "
        "https://docs.google.com/spreadsheets/d/{}",
        settings.GOOGLE_SHEET_OWNER_EMAIL or "(email berilmagan)", sid,
    )
    return sid


def _read_ws(sheet_id: str, sa_path: str, title: str) -> list[list[str]]:
    """Bitta varaqni o'qish — asyncio.to_thread ichida chaqiriladi."""
    import gspread

    gc = gspread.service_account(filename=sa_path)
    sh = gc.open_by_key(sheet_id)
    try:
        return sh.worksheet(title).get_all_values()
    except gspread.WorksheetNotFound:
        return []


def _from_cell(col, raw: str):  # noqa: ANN001
    """Sheets katagini SQLAlchemy ustun tipiga qaytaradi."""
    if raw == "":
        if col.nullable:
            return None
        try:
            return "" if col.type.python_type is str else None
        except NotImplementedError:
            return None
    try:
        t = col.type.python_type
    except NotImplementedError:
        return raw
    if t is bool:
        return raw.strip().upper() in {"TRUE", "1"}
    if t is int:
        return int(raw)
    if t is float:
        return float(raw)
    if t is datetime:
        return datetime.fromisoformat(raw)
    if t is date:
        return date.fromisoformat(raw)
    return raw


def _rows_to_kwargs(model: type, values: list[list[str]]) -> list[dict]:
    """Varaq qatorlarini model kwargs ro'yxatiga aylantiradi."""
    if len(values) < 2:
        return []
    cols = {c.name: c for c in model.__table__.columns}
    header = values[0]
    out: list[dict] = []
    for raw_row in values[1:]:
        if not any(cell.strip() for cell in raw_row):
            continue
        kwargs: dict = {}
        try:
            for name, raw in zip(header, raw_row, strict=False):
                if name in cols:
                    kwargs[name] = _from_cell(cols[name], raw)
            out.append(kwargs)
        except (ValueError, TypeError) as e:
            logger.debug("Restore: qator o'tkazildi ({}): {}", model.__name__, e)
    return out


async def _db_users_count() -> int:
    from sqlalchemy import func

    from app.db.models.user import User

    async with get_session() as session:
        result = await session.execute(select(func.count()).select_from(User))
        return int(result.scalar() or 0)


async def restore_from_sheets() -> bool:
    """DB bo'sh bo'lsa (yangi server/dyno restart) Sheets nusxasidan tiklaydi.

    Returns: tiklash bajarildimi.
    """
    settings = get_settings()
    sa_path = settings.google_sa_path
    if not sa_path.exists():
        return False
    sheet_id = await _ensure_sheet_id()
    if not sheet_id:
        return False

    if await _db_users_count() > 0:
        return False  # DB da ma'lumot bor — tiklash kerak emas

    restored = 0
    for title, model in _restore_plans():
        try:
            values = await asyncio.to_thread(_read_ws, sheet_id, str(sa_path), title)
        except Exception as e:  # noqa: BLE001
            logger.warning("Restore: '{}' varaqi o'qilmadi: {}", title, e)
            continue
        rows = _rows_to_kwargs(model, values)
        if not rows:
            continue
        async with get_session() as session:
            for kwargs in rows:
                try:
                    await session.merge(model(**kwargs))
                except Exception as e:  # noqa: BLE001
                    logger.debug("Restore merge o'tkazildi ({}): {}", title, e)
        restored += len(rows)
        logger.info("♻️ Sheets'dan tiklandi: {} — {} qator", title, len(rows))

    if restored:
        logger.info("♻️ To'liq tiklash yakunlandi: jami {} qator", restored)
    return restored > 0


async def _pull_masjid_times(values: list[list[str]]) -> int:
    """MasjidTimes varaqidagi qo'lda o'zgartirishlarni DB ga oladi.

    Faqat to'g'ri HH:MM formatdagi va DB dan farq qiladigan kataklar olinadi.
    Returns: yangilangan yozuvlar soni.
    """
    from app.core.constants import FARZ_PRAYERS
    from app.db.repositories.masjid_time_repo import MasjidTimeRepository
    from app.utils.time_utils import clean_hhmm

    if len(values) < 2:
        return 0
    header = values[0]
    try:
        i_region = header.index("region_id")
        i_prayer = header.index("prayer")
        i_time = header.index("time")
    except ValueError:
        return 0

    changed = 0
    async with get_session() as session:
        repo = MasjidTimeRepository(session)
        current: dict[int, dict[str, str]] = {}
        for row in values[1:]:
            if len(row) <= max(i_region, i_prayer, i_time):
                continue
            try:
                region_id = int(row[i_region])
            except ValueError:
                continue
            prayer = row[i_prayer].strip()
            t = clean_hhmm(row[i_time])
            if prayer not in FARZ_PRAYERS or not t:
                continue
            if region_id not in current:
                current[region_id] = await repo.get_for_region(region_id)
            if current[region_id].get(prayer) != t:
                await repo.upsert(region_id, prayer, t)
                changed += 1
                logger.info(
                    "📥 Sheets'dan masjid vaqti olindi: region={} {}={}",
                    region_id, prayer, t,
                )
    return changed


async def run_sheets_sync(*, pull: bool = True) -> None:
    """Scheduler chaqiradigan entry point — pull (ixtiyoriy) + export.

    Args:
        pull: True bo'lsa avval Sheets'dagi qo'lda o'zgartirishlarni DB ga
            oladi. Bot ichidan (admin panel masjid vaqtlarini saqlagach)
            chaqirilganda **False** berish shart — chunki DB allaqachon eng
            yangi holatda, pull esa uni eskirgan Sheet qiymatiga qaytarib
            yuborib, hozirgina kiritilgan vaqtni o'chirib qo'yardi.
    """
    settings = get_settings()
    sa_path = settings.google_sa_path
    if not sa_path.exists():
        logger.debug(
            "Sheets sync o'tkazildi: service account fayli yo'q ({})", sa_path,
        )
        return

    try:
        sheet_id = await _ensure_sheet_id()
        if not sheet_id:
            return

        # 0. DB bo'sh bo'lsa — avval Sheets'dan tiklaymiz (export bo'sh
        #    ma'lumot bilan jadvalni o'chirib yubormasligi uchun ham muhim).
        await restore_from_sheets()

        # 1. Sheet'da qo'lda o'zgartirilgan masjid vaqtlarini DB ga olish
        if pull:
            mt_values = await asyncio.to_thread(
                _read_ws, sheet_id, str(sa_path), "MasjidTimes",
            )
            changed = await _pull_masjid_times(mt_values)
            if changed:
                logger.info("📥 Sheets → DB: {} masjid vaqti yangilandi", changed)

        # 2. DB → Sheets to'liq export
        data = await _collect()
        await asyncio.to_thread(_push, sheet_id, str(sa_path), data)
        total = sum(len(rows) - 1 for rows in data.values())
        logger.info("📊 Google Sheets sync OK: {} varaq, {} qator", len(data), total)
    except Exception as e:  # noqa: BLE001 — sync xatosi botni to'xtatmasin
        logger.warning("Google Sheets sync xato: {}", e)


__all__ = ["restore_from_sheets", "run_sheets_sync"]
