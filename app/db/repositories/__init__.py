"""Repository pattern — har model uchun CRUD."""
from app.db.repositories.base import BaseRepository
from app.db.repositories.channel_repo import ChannelRepository
from app.db.repositories.masjid_time_repo import MasjidTimeRepository
from app.db.repositories.post_log_repo import PostLogRepository
from app.db.repositories.region_repo import RegionRepository
from app.db.repositories.stats_repo import StatsRepository
from app.db.repositories.subscribed_chat_repo import SubscribedChatRepository
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.repositories.user_repo import UserRepository

__all__ = [
    "BaseRepository",
    "ChannelRepository",
    "MasjidTimeRepository",
    "PostLogRepository",
    "RegionRepository",
    "StatsRepository",
    "SubscribedChatRepository",
    "SubscriptionRepository",
    "UserRepository",
]
