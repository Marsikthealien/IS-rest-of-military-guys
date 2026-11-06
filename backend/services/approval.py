from sqlalchemy.orm import Session

from models import Commander, LeaveRequest, LeaveStatus, ScheduleEntry
from services.notifications import NotificationService


class ApprovalService:
    def __init__(self, db: Session):
        self.db = db
        self.notifications = NotificationService(db)

    def approve(self, requestId: int, commanderId: int, comment: str | None = None) -> LeaveRequest:
        """Транзакція погодження: APPROVED -> графік + debit -> SCHEDULED."""
        by = self.db.get(Commander, commanderId)
        req = by._request(requestId)
        req.approve(by, comment)
        self.updateSchedule(req)
        req.changeStatus(LeaveStatus.SCHEDULED, by)
        self.notifications.notify(req.member, LeaveStatus.SCHEDULED, req)
        return req

    def reject(self, requestId: int, commanderId: int, reason: str | None) -> LeaveRequest:
        by = self.db.get(Commander, commanderId)
        req = by._request(requestId)
        req.reject(by, reason)  # ValueError, якщо причина порожня
        self.notifications.notify(req.member, LeaveStatus.REJECTED, req)
        return req

    def updateSchedule(self, req: LeaveRequest) -> ScheduleEntry:
        sched = req.member.unit._schedule(req.dateFrom.year, create=True)
        entry = sched.addEntry(req)
        bal = req._balance()
        if bal:
            bal.debit(req.durationDays)
        return entry
