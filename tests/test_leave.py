from datetime import timedelta

from conftest import T0, h

BODY = {"type": "ANNUAL", "dateFrom": "2026-12-01", "dateTo": "2026-12-14"}  # 14 дн.


def submit(client, uid, body=BODY):
    return client.post("/requests", json=body, headers=h(uid))


def annual(client, uid):
    return next(b for b in client.get("/balance?year=2026", headers=h(uid)).json() if b["type"] == "ANNUAL")


def texts(client, uid):
    return [n["text"] for n in client.get("/notifications", headers=h(uid)).json()]


def tick(client, at):
    assert client.post("/dev/tick", params={"now": at.isoformat()}).status_code == 200


def status_of(client, uid, rid):
    return next(r["status"] for r in client.get("/requests", headers=h(uid)).json() if r["id"] == rid)


def to_review(c, ids, body=BODY):
    rid = submit(c, ids["soldier1"], body).json()["id"]
    assert c.post(f"/requests/{rid}/open", headers=h(ids["koval"])).status_code == 200
    return rid


# ---- сценарії docs/18 (Sprint 1)
def test_tc01_correct_request(env):
    c, ids, _ = env
    r = submit(c, ids["soldier1"])
    assert r.status_code == 201 and r.json()["status"] == "SUBMITTED"
    assert r.json()["durationDays"] == 14 and r.json()["remainingAfter"] == 16
    b = annual(c, ids["soldier1"])
    assert (b["reservedDays"], b["remainingDays"]) == (14, 16)
    assert texts(c, ids["koval"]) == [f"Нова заявка №{r.json()['id']}"]
    assert texts(c, ids["savchuk"]) == []  # інша рота


def test_tc02_no_type(env):
    c, ids, _ = env
    r = submit(c, ids["soldier1"], {"dateFrom": "2026-12-01", "dateTo": "2026-12-14"})
    assert r.status_code == 422 and r.json()["errors"] == {"type": "Не вказано тип відпустки"}
    assert c.get("/requests", headers=h(ids["soldier1"])).json() == []  # нічого не збережено


def test_tc05_past_date(env):
    c, ids, _ = env
    r = submit(c, ids["soldier1"], {"type": "ANNUAL", "dateFrom": "2026-11-10", "dateTo": "2026-11-15"})
    assert r.status_code == 422 and r.json()["errors"]["dateFrom"] == "Дата початку не може бути в минулому"


def test_tc06_exceeds_balance(env):
    c, ids, _ = env
    r = submit(c, ids["soldier1"], {"type": "ANNUAL", "dateFrom": "2026-12-01", "dateTo": "2027-01-10"})
    assert r.status_code == 422 and r.json()["errors"]["dateTo"] == "Перевищено залишок на 11 дн."
    assert r.json()["remainingDays"] == 30


def test_tc07_boundary(env):
    c, ids, _ = env
    r = submit(c, ids["soldier1"], {"type": "ANNUAL", "dateFrom": "2026-12-01", "dateTo": "2026-12-30"})
    assert r.status_code == 201 and r.json()["durationDays"] == 30 and r.json()["remainingAfter"] == 0


def test_tc08_sick_does_not_debit(env):
    c, ids, _ = env
    r = submit(c, ids["soldier1"], {"type": "SICK", "dateFrom": "2026-12-01", "dateTo": "2026-12-20"})
    assert r.status_code == 201
    assert annual(c, ids["soldier1"])["remainingDays"] == 30


def test_tc10_second_request_counts_reserve(env):
    c, ids, _ = env
    assert submit(c, ids["soldier1"]).status_code == 201
    r = submit(c, ids["soldier1"], {"type": "ANNUAL", "dateFrom": "2027-02-01", "dateTo": "2027-02-20"})
    assert r.status_code == 422 and r.json()["errors"]["dateTo"] == "Перевищено залишок на 4 дн."
    assert r.json()["remainingDays"] == 16


# ---- скасування
def test_cancel_from_submitted_releases(env):
    c, ids, _ = env
    s = ids["soldier1"]
    rid = submit(c, s).json()["id"]
    r = c.post(f"/requests/{rid}/cancel", headers=h(s))
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    assert [d["toStatus"] for d in r.json()["decisions"]] == ["SUBMITTED", "CANCELLED"]
    assert annual(c, s)["reservedDays"] == 0 and annual(c, s)["remainingDays"] == 30
    assert texts(c, s) == [f"Заявку №{rid} скасовано"]


def test_cancel_other_statuses_409(env):
    c, ids, _ = env
    s, koval = ids["soldier1"], ids["koval"]
    rid = to_review(c, ids)
    assert c.post(f"/requests/{rid}/cancel", headers=h(s)).status_code == 409  # На розгляді
    c.post(f"/requests/{rid}/approve", json={}, headers=h(koval))
    assert c.post(f"/requests/{rid}/cancel", headers=h(s)).status_code == 409  # Внесено до графіка
    rid2 = to_review(c, ids, {"type": "ANNUAL", "dateFrom": "2026-12-20", "dateTo": "2026-12-22"})
    c.post(f"/requests/{rid2}/reject", json={"reason": "ні"}, headers=h(koval))
    assert c.post(f"/requests/{rid2}/cancel", headers=h(s)).status_code == 409  # Відхилено


def test_cancel_foreign_request_403(env):
    c, ids, _ = env
    rid = submit(c, ids["soldier1"]).json()["id"]
    assert c.post(f"/requests/{rid}/cancel", headers=h(ids["soldier2"])).status_code == 403


# ---- нагадування (72 год від submittedAt, одне)
def test_reminder_exactly_one_for_submitted_and_under_review(env):
    c, ids, _ = env
    koval = ids["koval"]
    r1 = submit(c, ids["soldier1"]).json()["id"]  # лишається Подано
    r2 = to_review(c, ids, {"type": "ANNUAL", "dateFrom": "2026-12-20", "dateTo": "2026-12-22"})
    tick(c, T0 + timedelta(hours=71, minutes=59))
    assert not any("Строк розгляду" in t for t in texts(c, koval))
    tick(c, T0 + timedelta(hours=72))
    tick(c, T0 + timedelta(hours=100))
    tick(c, T0 + timedelta(hours=200))
    for rid in (r1, r2):
        assert sum(t.startswith(f"Строк розгляду заявки №{rid} ") for t in texts(c, koval)) == 1
    assert status_of(c, ids["soldier1"], r1) == "SUBMITTED"  # ескалації немає
    assert status_of(c, ids["soldier1"], r2) == "UNDER_REVIEW"


# ---- розгляд
def test_open_shows_overlaps(env):
    c, ids, _ = env
    koval = ids["koval"]
    first = to_review(c, ids)
    c.post(f"/requests/{first}/approve", json={}, headers=h(koval))
    rid = submit(c, ids["soldier2"], {"type": "ANNUAL", "dateFrom": "2026-12-10", "dateTo": "2026-12-12"}).json()["id"]
    body = c.post(f"/requests/{rid}/open", headers=h(koval)).json()
    assert body["request"]["status"] == "UNDER_REVIEW"
    assert [o["requestId"] for o in body["overlaps"]] == [first]
    assert c.post(f"/requests/{rid}/open", headers=h(koval)).status_code == 409  # повторно
    assert c.post(f"/requests/{rid}/open", headers=h(ids["savchuk"])).status_code == 403  # інша рота


def test_approve_single_scheduled_notification(env):
    c, ids, _ = env
    s, koval = ids["soldier1"], ids["koval"]
    rid = to_review(c, ids)
    r = c.post(f"/requests/{rid}/approve", json={"comment": "ok"}, headers=h(koval))
    assert r.status_code == 200 and r.json()["status"] == "SCHEDULED"
    assert [d["toStatus"] for d in r.json()["decisions"]] == ["SUBMITTED", "UNDER_REVIEW", "APPROVED", "SCHEDULED"]
    b = annual(c, s)
    assert (b["usedDays"], b["reservedDays"], b["remainingDays"]) == (14, 0, 16)
    assert texts(c, s) == [f"Заявку №{rid} погоджено, внесено до графіка"]
    sched = c.get("/schedule", headers=h(ids["hr"])).json()
    assert len(sched) == 1 and sched[0]["requestId"] == rid
    assert len(c.get("/schedule", headers=h(koval)).json()) == 1
    assert c.get("/schedule", headers=h(ids["savchuk"])).json() == []  # графік іншої роти порожній


def test_approve_requires_under_review(env):
    c, ids, _ = env
    rid = submit(c, ids["soldier1"]).json()["id"]
    assert c.post(f"/requests/{rid}/approve", json={}, headers=h(ids["koval"])).status_code == 409
    assert c.post(f"/requests/{rid}/approve", json={}, headers=h(ids["savchuk"])).status_code == 403


def test_reject_without_reason_422_then_with_reason(env):
    c, ids, _ = env
    s, koval = ids["soldier1"], ids["koval"]
    rid = to_review(c, ids)
    assert c.post(f"/requests/{rid}/reject", json={"reason": "  "}, headers=h(koval)).status_code == 422
    assert c.post(f"/requests/{rid}/reject", headers=h(koval)).status_code == 422
    assert status_of(c, s, rid) == "UNDER_REVIEW" and annual(c, s)["reservedDays"] == 14
    r = c.post(f"/requests/{rid}/reject", json={"reason": "потреба служби"}, headers=h(koval))
    assert r.status_code == 200 and r.json()["status"] == "REJECTED"
    assert annual(c, s)["remainingDays"] == 30
    assert texts(c, s) == [f"Заявку №{rid} відхилено. Причина: потреба служби"]


# ---- таймер завершення
def test_completed_after_date_to(env):
    c, ids, _ = env
    rid = to_review(c, ids)
    c.post(f"/requests/{rid}/approve", json={}, headers=h(ids["koval"]))
    tick(c, T0.replace(month=12, day=14, hour=23))  # dateTo ще не минула
    hist = c.get("/history?status=COMPLETED", headers=h(ids["hr"])).json()
    assert hist == []
    tick(c, T0.replace(month=12, day=15, hour=0, minute=1))
    hist = c.get("/history?status=COMPLETED", headers=h(ids["hr"])).json()
    assert len(hist) == 1 and hist[0]["fromStatus"] == "SCHEDULED" and hist[0]["changedBy"] == "система"


# ---- HRClerk
def test_unit_history(env):
    c, ids, _ = env
    hr = ids["hr"]
    rid = to_review(c, ids)
    c.post(f"/requests/{rid}/approve", json={"comment": "ok"}, headers=h(ids["koval"]))
    all_ = c.get("/history", headers=h(hr)).json()
    assert [(d["fromStatus"], d["toStatus"]) for d in reversed(all_)] == [
        ("DRAFT", "SUBMITTED"), ("SUBMITTED", "UNDER_REVIEW"), ("UNDER_REVIEW", "APPROVED"),
        ("APPROVED", "SCHEDULED")]
    assert all_[0]["requestId"] == rid and all_[0]["memberName"].endswith("Петренко І.В.")
    only = c.get("/history?status=APPROVED", headers=h(hr)).json()
    assert len(only) == 1 and only[0]["comment"] == "ok" and only[0]["changedBy"] == "Коваль О.С."
    assert len(c.get("/history?dateFrom=2026-11-16&dateTo=2026-11-16", headers=h(hr)).json()) == 4
    assert c.get("/history?dateFrom=2026-11-17", headers=h(hr)).json() == []
    assert c.get("/history", headers=h(ids["koval"])).status_code == 403


def test_update_norm(env):
    c, ids, _ = env
    hr = ids["hr"]
    norms = {n["type"]: n["daysPerYear"] for n in c.get("/norms", headers=h(hr)).json()}
    assert norms["FAMILY"] == 10
    r = c.put("/norms/FAMILY", json={"daysPerYear": 12}, headers=h(hr))
    assert r.status_code == 200 and r.json()["daysPerYear"] == 12
    assert {n["type"]: n["daysPerYear"] for n in c.get("/norms", headers=h(hr)).json()}["FAMILY"] == 12
    assert c.put("/norms/FAMILY", json={"daysPerYear": -1}, headers=h(hr)).status_code == 422
    assert c.put("/norms/NOPE", json={"daysPerYear": 1}, headers=h(hr)).status_code == 404
    assert c.put("/norms/FAMILY", json={"daysPerYear": 5}, headers=h(ids["koval"])).status_code == 403


# ---- вхід
def test_login(env):
    c, ids, _ = env
    r = c.post("/login", json={"login": "koval", "password": "demo"})
    assert r.status_code == 200 and r.json()["id"] == ids["koval"] and r.json()["role"] == "COMMANDER"
    assert c.post("/login", json={"login": "koval", "password": "bad"}).status_code == 401
    assert c.post("/login", json={"login": "nobody", "password": "demo"}).status_code == 401
