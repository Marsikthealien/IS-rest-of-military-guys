from datetime import date

from sqlalchemy.orm import Session

import clock
from models import LeaveNorm, LeaveRequest, LeaveType, ServiceMember
from schemas import ValidationResult

# типи з річним лімітом на одну заявку (V7)
LIMIT_TYPES = (LeaveType.FAMILY, LeaveType.STUDY)


class ValidationService:
    def __init__(self, db: Session):
        self.db = db

    def validateCompleteness(self, req: LeaveRequest) -> dict[str, str]:
        """V1-V5. Повертає errors по полях (порожній = заявка повна)."""
        errors: dict[str, str] = {}
        if req.type is None:
            errors["type"] = "Не вказано тип відпустки"
        if req.dateFrom is None:
            errors["dateFrom"] = "Вкажіть дату початку"
        elif req.dateFrom < clock.now().date():
            errors["dateFrom"] = "Дата початку не може бути в минулому"
        if req.dateTo is None:
            errors["dateTo"] = "Вкажіть дату кінця"
        elif req.dateFrom is not None and req.dateTo < req.dateFrom:
            errors["dateTo"] = "Дата кінця раніша за дату початку"
        return errors

    @staticmethod
    def calcDuration(dateFrom: date, dateTo: date) -> int:
        return (dateTo - dateFrom).days + 1

    def checkBalance(self, req: LeaveRequest) -> ValidationResult:
        """V6-V7. Рік залишку = рік дати початку; req ще не збережена."""
        days = self.calcDuration(req.dateFrom, req.dateTo)
        norm = self.db.get(LeaveNorm, req.type)
        if not norm.debitsBalance:  # SICK: з залишку не списується
            return ValidationResult(isValid=True, durationDays=days)
        bal = self.db.get(ServiceMember, req.memberId).getBalance(req.type, req.dateFrom.year)
        remaining = bal.remainingDays if bal else 0
        errors: dict[str, str] = {}
        if req.type in LIMIT_TYPES and days > norm.daysPerYear:
            errors["dateTo"] = f"Перевищено ліміт для цього типу на {days - norm.daysPerYear} дн."
        elif bal is None or not bal.canCover(days):
            errors["dateTo"] = f"Перевищено залишок на {days - remaining} дн."
        return ValidationResult(isValid=not errors, errors=errors, remainingDays=remaining,
                                remainingAfter=remaining - days, durationDays=days)
