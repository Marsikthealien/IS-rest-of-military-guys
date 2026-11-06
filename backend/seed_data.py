"""Тестові дані: 2 роти, у кожній свій командир і 5 військовослужбовців, 1 відповідальний за кадровий облік. Пароль усіх: demo."""
from sqlalchemy.orm import Session

from models import (Commander, HRClerk, LeaveBalance, LeaveNorm, LeaveType, ServiceMember, Unit,
                    hash_password)

YEAR = 2026
# норми живуть у таблиці leave_norms, а не в логіці: (днів на рік, списується з залишку)
NORMS = {
    LeaveType.ANNUAL: (30, True),
    LeaveType.ADDITIONAL: (10, True),
    LeaveType.STUDY: (30, True),
    LeaveType.FAMILY: (10, True),
    LeaveType.SICK: (0, False),
}
# (рота, командир, військовослужбовці)
UNITS = [
    ("1 рота", ("Коваль О.С.", "капітан", "koval"), [
        ("Петренко І.В.", "ст. солдат"), ("Іваненко О.П.", "солдат"), ("Шевченко Т.Г.", "сержант"),
        ("Бондаренко М.С.", "молодший сержант"), ("Мельничук В.Д.", "солдат")]),
    ("2 рота", ("Савчук Д.М.", "капітан", "savchuk"), [
        ("Гончаренко А.Р.", "солдат"), ("Лисенко Б.О.", "ст. солдат"), ("Ткаченко Є.В.", "сержант"),
        ("Кравець Р.І.", "солдат"), ("Мороз Л.С.", "молодший сержант")]),
]


def seed(db: Session) -> None:
    if db.query(Unit).first():
        return
    pw = hash_password("demo")
    db.add_all(LeaveNorm(type=t, daysPerYear=d, debitsBalance=deb) for t, (d, deb) in NORMS.items())
    n = 0
    for name, (cname, crank, clogin), soldiers in UNITS:
        unit = Unit(name=name, maxAbsentShare=0.3)
        db.add(unit)
        db.flush()
        db.add(Commander(fullName=cname, rank=crank, login=clogin, passwordHash=pw,
                         commandLevel="командир роти", unitId=unit.id))
        for sname, rank in soldiers:
            n += 1
            m = ServiceMember(fullName=sname, rank=rank, login=f"soldier{n}", passwordHash=pw,
                              personalNumber=f"А-{1000 + n}", position="стрілець", unitId=unit.id)
            m.balances = [LeaveBalance(year=YEAR, type=t, entitledDays=d) for t, (d, _) in NORMS.items()]
            db.add(m)
    db.add(HRClerk(fullName="Кравчук Н.П.", rank="прапорщик", login="hr", passwordHash=pw))
    db.commit()
