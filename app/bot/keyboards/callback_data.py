"""Callback data konstantalari — bitta joyda saqlanadi.

Format: "<action>:<arg>" yoki "<action>" (arg yo'q bo'lsa)
"""
from __future__ import annotations

# ---------- Hudud / obuna ----------
CB_VILOYAT = "viloyat"          # viloyat:<id>
CB_TUMAN = "tuman"              # tuman:<id> — toggle obuna
CB_BACK_VILOYAT = "back:viloyat"

# ---------- Asosiy menyu ----------
CB_MAIN_MENU = "menu"
CB_SELECT_REGION = "select_region"
CB_MY_TIMES = "my_times"
CB_NEXT_FARZ = "next_farz"
CB_NAFL_NOW = "nafl_now"
CB_SETTINGS = "settings"

# ---------- Onboarding ----------
CB_ONBOARD_LOCATION = "onboard:location"
CB_ONBOARD_LIST = "onboard:list"
CB_ONBOARD_SEARCH = "onboard:search"

# ---------- Tomorrow times ----------
CB_TOMORROW_TIMES = "my_times_tom"

# ---------- Lokatsiya tasdiq ----------
CB_LOC_CONFIRM = "loc:ok"          # loc:ok:<region_id>
CB_LOC_CANCEL = "loc:cancel"

# ---------- Sozlamalar ----------
CB_TOGGLE_FARZ = "toggle:farz"
CB_TOGGLE_NAFL = "toggle:nafl"
CB_TOGGLE_DAILY = "toggle:daily"
CB_TOGGLE_QUIET = "toggle:quiet"

# ---------- Admin ----------
CB_ADMIN_ROOT = "admin:root"
CB_ADMIN_STATS = "admin:stats"
CB_ADMIN_CHANNELS = "admin:channels"
CB_ADMIN_MASJID = "admin:masjid"
CB_ADMIN_BROADCAST = "admin:broadcast"
CB_ADMIN_TEST_POST = "admin:test_post"

# ---------- Admin: Channel CRUD ----------
CB_CH_ADD = "ch:add"
CB_CH_VIEW = "ch:view"               # ch:view:<id>
CB_CH_TOGGLE = "ch:toggle"           # ch:toggle:<id>
CB_CH_DELETE = "ch:del"              # ch:del:<id>
CB_CH_DELETE_OK = "ch:del_ok"        # ch:del_ok:<id>
CB_CH_VILOYAT = "ch_vil"             # ch_vil:<region_id>
CB_CH_TUMAN = "ch_tum"               # ch_tum:<region_id>
CB_CH_BACK_VIL = "ch_vil_back"
CB_CH_CANCEL = "ch:cancel"
CB_CH_TEMPLATE_EDIT = "ch:tmpl"      # ch:tmpl:<id>
CB_CH_TEMPLATE_CLEAR = "ch:tmpl_clr" # ch:tmpl_clr:<id>

# ---------- Admin: Masjid time edit ----------
CB_MT_VILOYAT = "mt_vil"             # mt_vil:<region_id>
CB_MT_TUMAN = "mt_tum"               # mt_tum:<region_id>
CB_MT_BACK_VIL = "mt_back_vil"
CB_MT_PRAYER = "mt_pray"             # mt_pray:<region_id>:<prayer_name>
CB_MT_BACK_PRAYERS = "mt_back_pray"  # bitta region detail'ga qaytish
CB_MT_CANCEL = "mt:cancel"

# ---------- Admin: Broadcast ----------
CB_BC_CONFIRM = "bc:send"
CB_BC_CANCEL = "bc:cancel"
