"""Pydantic-схеми; імена полів збігаються з контрактом API (docs/17-prototype.md, SYNC-SPEC.md розділ 4)."""
from datetime import date, datetime

from pydantic import BaseModel


class LeaveRequestIn(BaseModel):
    # усі поля необов'язкові: повноту перевіряє ValidationService (422 з errors по полях)
    type: str | None = None
    dateFrom: date | None = None
    dateTo: date | None = None
    comment: str | None = None


class DecisionIn(BaseModel):
    comment: str | None = None
    reason: str | None = None


class ValidationResult(BaseModel):
    isValid: bool
    errors: dict[str, str] = {}
    remainingDays: int | None = None
    remainingAfter: int | None = None
    durationDays: int | None = None


class BalanceOut(BaseModel):
    type: str
    entitledDays: int
    usedDays: int
    reservedDays: int
    remainingDays: int | None  # None = без ліміту (SICK)


class DecisionRecordOut(BaseModel):
    requestId: int
    memberName: str
    fromStatus: str
    toStatus: str
    decidedAt: datetime
    changedBy: str | None
    reason: str | None
    comment: str | None


class LeaveRequestOut(BaseModel):
    id: int
    memberId: int
    memberName: str
    type: str
    dateFrom: date
    dateTo: date
    durationDays: int
    status: str
    comment: str | None
    createdAt: datetime
    submittedAt: datetime | None
    reminderSent: bool
    decisions: list[DecisionRecordOut]


class SubmitOut(BaseModel):
    id: int
    status: str
    durationDays: int
    remainingAfter: int | None


class OpenOut(BaseModel):
    request: LeaveRequestOut
    overlaps: list["ScheduleEntryOut"]


class ScheduleEntryOut(BaseModel):
    id: int
    requestId: int
    unitId: int
    unitName: str
    memberName: str
    rank: str
    type: str
    dateFrom: date
    dateTo: date


class NotificationOut(BaseModel):
    id: int
    requestId: int | None
    text: str
    createdAt: datetime
    isRead: bool


class LoginIn(BaseModel):
    login: str
    password: str


class NormOut(BaseModel):
    type: str
    daysPerYear: int
    debitsBalance: bool


class NormIn(BaseModel):
    daysPerYear: int


class UserOut(BaseModel):
    id: int
    login: str
    fullName: str
    rank: str
    role: str


OpenOut.model_rebuild()


def decision_out(d) -> DecisionRecordOut:
    m = d.request.member
    return DecisionRecordOut(
        requestId=d.requestId, memberName=f"{m.rank} {m.fullName}",
        fromStatus=d.fromStatus.value, toStatus=d.toStatus.value, decidedAt=d.decidedAt,
        changedBy=d.changedBy.fullName if d.changedBy else "система",
        reason=d.reason, comment=d.comment)


def request_out(r) -> LeaveRequestOut:
    return LeaveRequestOut(
        id=r.id, memberId=r.memberId, memberName=f"{r.member.rank} {r.member.fullName}",
        type=r.type.value, dateFrom=r.dateFrom, dateTo=r.dateTo, durationDays=r.durationDays,
        status=r.status.value, comment=r.comment, createdAt=r.createdAt,
        submittedAt=r.submittedAt, reminderSent=r.reminderSent,
        decisions=[decision_out(d) for d in r.decisions])


def entry_out(e) -> ScheduleEntryOut:
    m = e.request.member
    return ScheduleEntryOut(
        id=e.id, requestId=e.requestId, unitId=m.unitId, unitName=m.unit.name,
        memberName=m.fullName, rank=m.rank, type=e.request.type.value,
        dateFrom=e.dateFrom, dateTo=e.dateTo)
