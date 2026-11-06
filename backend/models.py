"""Моделі строго за Class Diagram (docs/15-class.md + SYNC-SPEC.md розділ 2). Імена дослівно за діаграмою."""
import enum
import hashlib
import hmac
from datetime import date, datetime, time, timedelta

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, object_session, relationship

import clock
from errors import detail


class Base(DeclarativeBase):
    pass


class LeaveType(str, enum.Enum):
    ANNUAL = "ANNUAL"
    ADDITIONAL = "ADDITIONAL"
    STUDY = "STUDY"
    FAMILY = "FAMILY"
    SICK = "SICK"


class LeaveStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class User(Base):
    """Абстрактний користувач; ролі - joined-наслідування."""
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    fullName: Mapped[str] = mapped_column(String)
    rank: Mapped[str] = mapped_column(String)
    login: Mapped[str] = mapped_column(String, unique=True)
    passwordHash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    __mapper_args__ = {"polymorphic_on": "role"}

    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", order_by="Notification.id.desc()")

    def authenticate(self, password: str) -> bool:
        return hmac.compare_digest(self.passwordHash, hash_password(password))

    def getNotifications(self) -> list["Notification"]:
        return list(self.notifications)


class Unit(Base):
    __tablename__ = "units"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    maxAbsentShare: Mapped[float] = mapped_column(Float, default=0.3)

    members: Mapped[list["ServiceMember"]] = relationship(back_populates="unit")
    commander: Mapped["Commander | None"] = relationship(back_populates="unit", uselist=False)
    schedules: Mapped[list["VacationSchedule"]] = relationship(back_populates="unit")

    def getMembers(self) -> list["ServiceMember"]:
        return list(self.members)

    def _schedule(self, year: int, create: bool = False) -> "VacationSchedule | None":
        sched = next((s for s in self.schedules if s.year == year), None)
        if sched is None and create:
            sched = VacationSchedule(unit=self, year=year)
            object_session(self).add(sched)
        return sched


class ServiceMember(User):
    __tablename__ = "service_members"
    id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    personalNumber: Mapped[str] = mapped_column(String)
    position: Mapped[str] = mapped_column(String)
    unitId: Mapped[int] = mapped_column(ForeignKey("units.id"))
    __mapper_args__ = {"polymorphic_identity": "SERVICE_MEMBER"}

    unit: Mapped[Unit] = relationship(back_populates="members")
    balances: Mapped[list["LeaveBalance"]] = relationship(
        back_populates="member", cascade="all, delete-orphan")
    requests: Mapped[list["LeaveRequest"]] = relationship(back_populates="member")

    def submitRequest(self, type: LeaveType | None, dateFrom: date | None, dateTo: date | None,
                      comment: str | None = None) -> "LeaveRequest":
        """Чернетка живе на клієнті: заявка створюється на сервері одразу при поданні."""
        from errors import ApiError
        from services.validation import ValidationService  # відкладено: services імпортують models
        db = object_session(self)
        req = LeaveRequest(memberId=self.id, type=type, dateFrom=dateFrom, dateTo=dateTo,
                           comment=comment, status=LeaveStatus.DRAFT, createdAt=clock.now())
        validation = ValidationService(db)
        errors = validation.validateCompleteness(req)
        if errors:
            raise ApiError(422, {"errors": errors})
        result = validation.checkBalance(req)
        if not result.isValid:
            raise ApiError(422, result.model_dump(exclude={"isValid"}))
        db.add(req)
        db.flush()  # member і id потрібні submit()
        req.submit()
        return req

    def cancelRequest(self, requestId: int) -> None:
        req = object_session(self).get(LeaveRequest, requestId)
        if req is None:
            raise detail(404, "Заявку не знайдено")
        if req.memberId != self.id:
            raise detail(403, "Скасувати можна лише власну заявку")
        req.cancel()

    def getBalance(self, type: LeaveType, year: int) -> "LeaveBalance | None":
        # ponytail: на рік без власного залишку діє найновіший наявний (TC-10), перенесення між роками - коли з'явиться річне нарахування
        return (object_session(self).query(LeaveBalance)
                .filter(LeaveBalance.memberId == self.id, LeaveBalance.type == type,
                        LeaveBalance.year <= year)
                .order_by(LeaveBalance.year.desc()).first())

    def getMyRequests(self) -> list["LeaveRequest"]:
        return (object_session(self).query(LeaveRequest).filter_by(memberId=self.id)
                .order_by(LeaveRequest.id.desc()).all())


class Commander(User):
    __tablename__ = "commanders"
    id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    commandLevel: Mapped[str] = mapped_column(String)
    unitId: Mapped[int] = mapped_column(ForeignKey("units.id"))
    __mapper_args__ = {"polymorphic_identity": "COMMANDER"}

    unit: Mapped[Unit] = relationship(back_populates="commander")

    def getPendingRequests(self) -> list["LeaveRequest"]:
        return (object_session(self).query(LeaveRequest)
                .join(ServiceMember, LeaveRequest.memberId == ServiceMember.id)
                .filter(ServiceMember.unitId == self.unitId,
                        LeaveRequest.status.in_([LeaveStatus.SUBMITTED, LeaveStatus.UNDER_REVIEW]))
                .order_by(LeaveRequest.id.desc()).all())

    def approve(self, requestId: int, comment: str | None = None) -> "LeaveRequest":
        from services.approval import ApprovalService
        return ApprovalService(object_session(self)).approve(requestId, self.id, comment)

    def reject(self, requestId: int, reason: str | None) -> "LeaveRequest":
        from services.approval import ApprovalService
        return ApprovalService(object_session(self)).reject(requestId, self.id, reason)

    def _request(self, requestId: int) -> "LeaveRequest":
        """Заявка свого підрозділу (Commander 1 -> 1 Unit); спільна для /open, approve, reject."""
        req = object_session(self).get(LeaveRequest, requestId)
        if req is None:
            raise detail(404, "Заявку не знайдено")
        if req.member.unitId != self.unitId:
            raise detail(403, "Заявка іншого підрозділу")
        return req


class HRClerk(User):
    __tablename__ = "hr_clerks"
    id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    __mapper_args__ = {"polymorphic_identity": "HR_CLERK"}

    def getSchedule(self, unitId: int, month: date) -> "VacationSchedule | None":
        """Графік підрозділу на рік, до якого належить month."""
        unit = object_session(self).get(Unit, unitId)
        return unit._schedule(month.year) if unit else None

    def getUnitHistory(self, dateFrom: date | None = None, dateTo: date | None = None,
                       status: LeaveStatus | None = None) -> list["DecisionRecord"]:
        q = object_session(self).query(DecisionRecord)
        if dateFrom:
            q = q.filter(DecisionRecord.decidedAt >= datetime.combine(dateFrom, time.min))
        if dateTo:
            q = q.filter(DecisionRecord.decidedAt < datetime.combine(dateTo + timedelta(days=1), time.min))
        if status:
            q = q.filter(DecisionRecord.toStatus == status)
        return q.order_by(DecisionRecord.id.desc()).all()

    def updateNorm(self, type: LeaveType, daysPerYear: int) -> "LeaveNorm":
        if daysPerYear < 0:
            raise ValueError("Кількість днів не може бути від'ємною")
        norm = object_session(self).get(LeaveNorm, type)
        norm.daysPerYear = daysPerYear
        return norm


class LeaveNorm(Base):
    """Довідник норм (D1): норми не зашиті в код."""
    __tablename__ = "leave_norms"
    type: Mapped[LeaveType] = mapped_column(Enum(LeaveType), primary_key=True)
    daysPerYear: Mapped[int] = mapped_column(Integer)
    debitsBalance: Mapped[bool] = mapped_column(Boolean, default=True)


class LeaveBalance(Base):
    __tablename__ = "leave_balances"
    id: Mapped[int] = mapped_column(primary_key=True)
    memberId: Mapped[int] = mapped_column(ForeignKey("service_members.id"))
    year: Mapped[int] = mapped_column(Integer)
    type: Mapped[LeaveType] = mapped_column(Enum(LeaveType), ForeignKey("leave_norms.type"))
    entitledDays: Mapped[int] = mapped_column(Integer)
    usedDays: Mapped[int] = mapped_column(Integer, default=0)
    reservedDays: Mapped[int] = mapped_column(Integer, default=0)

    member: Mapped[ServiceMember] = relationship(back_populates="balances")
    norm: Mapped[LeaveNorm] = relationship()

    @property
    def remainingDays(self) -> int:
        return self.entitledDays - self.usedDays - self.reservedDays

    # типи без списання (SICK, norm.debitsBalance = false) залишок не чіпають
    def canCover(self, days: int) -> bool:
        return not self.norm.debitsBalance or days <= self.remainingDays

    def reserve(self, days: int) -> None:
        if self.norm.debitsBalance:
            self.reservedDays += days

    def release(self, days: int) -> None:
        if self.norm.debitsBalance:
            self.reservedDays -= days

    def debit(self, days: int) -> None:
        if self.norm.debitsBalance:
            self.reservedDays -= days
            self.usedDays += days


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    memberId: Mapped[int] = mapped_column(ForeignKey("service_members.id"))
    dateFrom: Mapped[date] = mapped_column(Date)
    dateTo: Mapped[date] = mapped_column(Date)
    type: Mapped[LeaveType] = mapped_column(Enum(LeaveType))
    status: Mapped[LeaveStatus] = mapped_column(Enum(LeaveStatus), default=LeaveStatus.DRAFT)
    comment: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime, default=lambda: clock.now())
    submittedAt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reminderSent: Mapped[bool] = mapped_column(Boolean, default=False)

    member: Mapped[ServiceMember] = relationship(back_populates="requests")
    decisions: Mapped[list["DecisionRecord"]] = relationship(
        back_populates="request", cascade="all, delete-orphan", order_by="DecisionRecord.id")

    @property
    def durationDays(self) -> int:
        from services.validation import ValidationService
        return ValidationService.calcDuration(self.dateFrom, self.dateTo)

    def _balance(self) -> "LeaveBalance | None":
        return self.member.getBalance(self.type, self.dateFrom.year)

    def _require(self, *allowed: LeaveStatus) -> None:
        if self.status not in allowed:
            raise detail(409, "Дія неможлива в поточному статусі заявки")

    def changeStatus(self, to: LeaveStatus, by: User | None, reason: str | None = None) -> "DecisionRecord":
        """Єдине місце зміни статусу: пише DecisionRecord (by=None - дія системи)."""
        rec = DecisionRecord(fromStatus=self.status, toStatus=to, decidedAt=clock.now(),
                             changedById=by.id if by else None, reason=reason)
        self.decisions.append(rec)
        self.status = to
        return rec

    def submit(self) -> None:
        """Чернетка -> Подано: резерв днів, DecisionRecord, сповіщення командира."""
        from services.notifications import NotificationService
        self.submittedAt = clock.now()
        self.changeStatus(LeaveStatus.SUBMITTED, self.member)
        bal = self._balance()
        if bal:
            bal.reserve(self.durationDays)
        NotificationService(object_session(self)).notifyCommander(self)

    def cancel(self) -> None:
        from services.notifications import NotificationService
        self._require(LeaveStatus.SUBMITTED)
        self.changeStatus(LeaveStatus.CANCELLED, self.member)
        bal = self._balance()
        if bal:
            bal.release(self.durationDays)
        NotificationService(object_session(self)).notify(self.member, LeaveStatus.CANCELLED, self)

    def open(self) -> None:
        """Відкриває командир підрозділу військовослужбовця."""
        self._require(LeaveStatus.SUBMITTED)
        self.changeStatus(LeaveStatus.UNDER_REVIEW, self.member.unit.commander)

    def approve(self, by: Commander, comment: str | None = None) -> None:
        self._require(LeaveStatus.UNDER_REVIEW)
        self.changeStatus(LeaveStatus.APPROVED, by).comment = comment

    def reject(self, by: Commander, reason: str | None) -> None:
        self._require(LeaveStatus.UNDER_REVIEW)
        if not reason or not reason.strip():
            raise ValueError("Вкажіть причину відхилення")
        self.changeStatus(LeaveStatus.REJECTED, by, reason.strip())
        bal = self._balance()
        if bal:
            bal.release(self.durationDays)

    def complete(self) -> None:
        self._require(LeaveStatus.SCHEDULED)
        self.changeStatus(LeaveStatus.COMPLETED, None)


class DecisionRecord(Base):
    __tablename__ = "decision_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    requestId: Mapped[int] = mapped_column(ForeignKey("leave_requests.id"))
    fromStatus: Mapped[LeaveStatus] = mapped_column(Enum(LeaveStatus))
    toStatus: Mapped[LeaveStatus] = mapped_column(Enum(LeaveStatus))
    decidedAt: Mapped[datetime] = mapped_column(DateTime)
    changedById: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    comment: Mapped[str | None] = mapped_column(String, nullable=True)

    request: Mapped[LeaveRequest] = relationship(back_populates="decisions")
    changedBy: Mapped[User | None] = relationship()


class VacationSchedule(Base):
    __tablename__ = "vacation_schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    unitId: Mapped[int] = mapped_column(ForeignKey("units.id"))
    year: Mapped[int] = mapped_column(Integer)

    unit: Mapped[Unit] = relationship(back_populates="schedules")
    entries: Mapped[list["ScheduleEntry"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan")

    def addEntry(self, req: LeaveRequest) -> "ScheduleEntry":
        entry = ScheduleEntry(request=req, dateFrom=req.dateFrom, dateTo=req.dateTo)
        self.entries.append(entry)
        return entry

    def findOverlaps(self, dateFrom: date, dateTo: date) -> list["ScheduleEntry"]:
        return [e for e in self.entries if e.dateFrom <= dateTo and dateFrom <= e.dateTo]


class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    scheduleId: Mapped[int] = mapped_column(ForeignKey("vacation_schedules.id"))
    requestId: Mapped[int] = mapped_column(ForeignKey("leave_requests.id"), unique=True)
    dateFrom: Mapped[date] = mapped_column(Date)
    dateTo: Mapped[date] = mapped_column(Date)

    schedule: Mapped[VacationSchedule] = relationship(back_populates="entries")
    request: Mapped[LeaveRequest] = relationship()


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    userId: Mapped[int] = mapped_column(ForeignKey("users.id"))
    requestId: Mapped[int | None] = mapped_column(ForeignKey("leave_requests.id"), nullable=True)
    text: Mapped[str] = mapped_column(String)
    createdAt: Mapped[datetime] = mapped_column(DateTime, default=lambda: clock.now())
    isRead: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="notifications")

    def markRead(self) -> None:
        self.isRead = True
