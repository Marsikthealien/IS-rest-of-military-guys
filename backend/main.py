import asyncio
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta

from fastapi import Depends, FastAPI, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import clock
from database import SessionLocal, engine, get_db
from errors import ApiError, detail
from models import (Base, Commander, HRClerk, LeaveBalance, LeaveNorm, LeaveRequest, LeaveStatus,
                    LeaveType, ServiceMember, Unit, User)
from schemas import (BalanceOut, DecisionIn, DecisionRecordOut, LeaveRequestIn, LeaveRequestOut,
                     LoginIn, NormIn, NormOut, NotificationOut, OpenOut, ScheduleEntryOut, SubmitOut,
                     UserOut, decision_out, entry_out, request_out)
from seed_data import seed
from services.notifications import NotificationService

REMINDER_AFTER = timedelta(hours=72)  # календарні години від submittedAt


def _tick(db: Session, at: datetime) -> None:
    """Таймер (раз на хвилину і через /dev/tick): нагадування командиру та завершення відпусток."""
    notifications = NotificationService(db)
    due = db.query(LeaveRequest).filter(
        LeaveRequest.status.in_([LeaveStatus.SUBMITTED, LeaveStatus.UNDER_REVIEW]),
        LeaveRequest.reminderSent.is_(False)).all()
    for req in due:
        if at - req.submittedAt >= REMINDER_AFTER:
            notifications.deadlineReached(req.id)
    for req in db.query(LeaveRequest).filter(LeaveRequest.status == LeaveStatus.SCHEDULED,
                                             LeaveRequest.dateTo < at.date()).all():
        req.complete()
    db.commit()


async def _tick_loop():
    while True:
        await asyncio.sleep(60)
        with SessionLocal() as db:
            _tick(db, clock.now())


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    task = asyncio.create_task(_tick_loop())
    yield
    task.cancel()


app = FastAPI(title="ІС «Відпустка»", lifespan=lifespan)


@app.exception_handler(ApiError)
async def api_error_handler(_, exc: ApiError):
    return JSONResponse(exc.body, status_code=exc.status)


# ---- "автентифікація": POST /login перевіряє пароль, далі роль передається заголовком X-User-Id
def current_user(x_user_id: int | None = Header(None), db: Session = Depends(get_db)) -> User:
    user = db.get(User, x_user_id) if x_user_id is not None else None
    if user is None:
        raise detail(401, "Невідомий користувач (заголовок X-User-Id)")
    return user


def require(user: User, cls):
    if not isinstance(user, cls):
        raise detail(403, "Недостатньо прав для цієї дії")
    return user


def _user_out(u: User) -> UserOut:
    return UserOut(id=u.id, login=u.login, fullName=u.fullName, rank=u.rank, role=u.role)


def _remaining(bal: LeaveBalance) -> int | None:
    return bal.remainingDays if bal.norm.debitsBalance else None  # None = без ліміту (SICK)


@app.post("/login", response_model=UserOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(login=data.login).first()
    if user is None or not user.authenticate(data.password):
        raise detail(401, "Неправильний логін або пароль")
    return _user_out(user)


@app.get("/balance", response_model=list[BalanceOut])
def get_balance(year: int = 2026, user: User = Depends(current_user)):
    member = require(user, ServiceMember)
    rows = [b for t in LeaveType if (b := member.getBalance(t, year))]
    return [BalanceOut(type=b.type.value, entitledDays=b.entitledDays, usedDays=b.usedDays,
                       reservedDays=b.reservedDays, remainingDays=_remaining(b)) for b in rows]


@app.post("/requests", response_model=SubmitOut, status_code=201)
def submit_request(data: LeaveRequestIn, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    member = require(user, ServiceMember)
    type_ = LeaveType(data.type) if data.type in LeaveType.__members__ else None
    req = member.submitRequest(type_, data.dateFrom, data.dateTo, data.comment)
    db.commit()
    return SubmitOut(id=req.id, status=req.status.value, durationDays=req.durationDays,
                     remainingAfter=_remaining(req._balance()))


@app.get("/requests", response_model=list[LeaveRequestOut])
def list_requests(user: User = Depends(current_user)):
    if isinstance(user, ServiceMember):
        rows = user.getMyRequests()
    else:
        rows = require(user, Commander).getPendingRequests()
    return [request_out(r) for r in rows]


@app.post("/requests/{request_id}/cancel", response_model=LeaveRequestOut)
def cancel(request_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member = require(user, ServiceMember)
    member.cancelRequest(request_id)
    db.commit()
    return request_out(db.get(LeaveRequest, request_id))


@app.post("/requests/{request_id}/open", response_model=OpenOut)
def open_request(request_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    req = require(user, Commander)._request(request_id)
    req.open()
    overlaps = [e for s in req.member.unit.schedules for e in s.findOverlaps(req.dateFrom, req.dateTo)]
    db.commit()
    return OpenOut(request=request_out(req),
                   overlaps=[entry_out(e) for e in overlaps if e.requestId != req.id])


@app.post("/requests/{request_id}/approve", response_model=LeaveRequestOut)
def approve(request_id: int, body: DecisionIn | None = None, user: User = Depends(current_user),
            db: Session = Depends(get_db)):
    req = require(user, Commander).approve(request_id, body.comment if body else None)
    db.commit()
    return request_out(req)


@app.post("/requests/{request_id}/reject", response_model=LeaveRequestOut)
def reject(request_id: int, body: DecisionIn | None = None, user: User = Depends(current_user),
           db: Session = Depends(get_db)):
    try:
        req = require(user, Commander).reject(request_id, body.reason if body else None)
    except ValueError as e:  # порожня причина
        raise ApiError(422, {"errors": {"reason": str(e)}})
    db.commit()
    return request_out(req)


@app.get("/schedule", response_model=list[ScheduleEntryOut])
def get_schedule(unitId: int | None = None, year: int | None = None,
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not isinstance(user, (Commander, HRClerk)):
        raise detail(403, "Недостатньо прав для цієї дії")
    year = year or clock.now().year
    if isinstance(user, Commander):  # командир бачить лише свій підрозділ
        scheds = [user.unit._schedule(year)]
    else:
        units = db.query(Unit).filter(Unit.id == unitId) if unitId else db.query(Unit)
        scheds = [user.getSchedule(u.id, date(year, 1, 1)) for u in units]
    entries = [e for s in scheds if s for e in s.entries]
    return [entry_out(e) for e in sorted(entries, key=lambda e: e.dateFrom)]


@app.get("/history", response_model=list[DecisionRecordOut])
def get_history(dateFrom: date | None = None, dateTo: date | None = None, status: str | None = None,
                user: User = Depends(current_user)):
    hr = require(user, HRClerk)
    if status is not None and status not in LeaveStatus.__members__:
        raise ApiError(422, {"errors": {"status": "Невідомий статус"}})
    rows = hr.getUnitHistory(dateFrom, dateTo, LeaveStatus(status) if status else None)
    return [decision_out(d) for d in rows]


def _norm_out(n: LeaveNorm) -> NormOut:
    return NormOut(type=n.type.value, daysPerYear=n.daysPerYear, debitsBalance=n.debitsBalance)


@app.get("/norms", response_model=list[NormOut])
def get_norms(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require(user, HRClerk)
    return [_norm_out(n) for n in db.query(LeaveNorm).all()]


@app.put("/norms/{type}", response_model=NormOut)
def put_norm(type: str, body: NormIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    hr = require(user, HRClerk)
    if type not in LeaveType.__members__:
        raise detail(404, "Невідомий тип відпустки")
    try:
        norm = hr.updateNorm(LeaveType(type), body.daysPerYear)
    except ValueError as e:
        raise ApiError(422, {"errors": {"daysPerYear": str(e)}})
    db.commit()
    return _norm_out(norm)


@app.get("/notifications", response_model=list[NotificationOut])
def get_notifications(mark_read: bool = False, user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    rows = user.getNotifications()
    out = [NotificationOut(id=n.id, requestId=n.requestId, text=n.text,
                           createdAt=n.createdAt, isRead=n.isRead) for n in rows]
    if mark_read:  # відповідь показує стан до прочитання
        for n in rows:
            n.markRead()
        db.commit()
    return out


# ---- службові ендпоінти розробки
@app.post("/dev/tick")
def dev_tick(at: datetime | None = Query(None, alias="now"), db: Session = Depends(get_db)):
    """Підміна часу для тестів: та сама логіка, що й у фоновому таймері."""
    _tick(db, (at or clock.now()).replace(tzinfo=None))
    return {"ok": True}


@app.get("/dev/users", response_model=list[UserOut])
def dev_users(db: Session = Depends(get_db)):
    """Список користувачів для перемикача ролей."""
    return [_user_out(u) for u in db.query(User).order_by(User.id).all()]
