from sqlalchemy.orm import Session

import clock
from models import LeaveRequest, LeaveStatus, Notification, User

EVENT_TEXT = {
    LeaveStatus.SUBMITTED: "Нова заявка №{id}",
    LeaveStatus.SCHEDULED: "Заявку №{id} погоджено, внесено до графіка",
    LeaveStatus.REJECTED: "Заявку №{id} відхилено. Причина: {reason}",
    LeaveStatus.CANCELLED: "Заявку №{id} скасовано",
}


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def _send(self, user: User, req: LeaveRequest, text: str) -> Notification:
        n = Notification(userId=user.id, requestId=req.id, text=text, createdAt=clock.now())
        self.db.add(n)
        return n

    def notifyCommander(self, req: LeaveRequest) -> Notification:
        return self._send(req.member.unit.commander, req, EVENT_TEXT[LeaveStatus.SUBMITTED].format(id=req.id))

    def notify(self, user: User, event: LeaveStatus, req: LeaveRequest) -> Notification:
        reason = next((d.reason for d in reversed(req.decisions) if d.reason), "")
        return self._send(user, req, EVENT_TEXT[event].format(id=req.id, reason=reason))

    def deadlineReached(self, requestId: int) -> Notification:
        """Нагадування командиру: 72 год без рішення (одне на заявку)."""
        req = self.db.get(LeaveRequest, requestId)
        req.reminderSent = True
        return self._send(req.member.unit.commander, req,
                          f"Строк розгляду заявки №{req.id} сплив (72 год з моменту подання)")
