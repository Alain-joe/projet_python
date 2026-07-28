from ninja import Schema
from datetime import datetime
from typing import Optional


class NotificationSchema(Schema):
    id: int
    titre: str
    message: str
    lu: bool
    created_at: datetime
    type_notification: str