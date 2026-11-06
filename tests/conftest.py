import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import clock  # noqa: E402
import main  # noqa: E402
from database import get_db  # noqa: E402
from models import Base, User  # noqa: E402
from seed_data import seed  # noqa: E402

T0 = datetime(2026, 11, 16, 10, 0)  # поточна дата зі сценаріїв docs/18-test-scenarios-sprint-1.md


@pytest.fixture
def env(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as db:
        seed(db)
    clk = {"now": T0}
    monkeypatch.setattr(clock, "now", lambda: clk["now"])

    def override():
        with Session() as db:
            yield db

    main.app.dependency_overrides[get_db] = override
    with Session() as db:
        ids = {u.login: u.id for u in db.query(User).all()}
    yield TestClient(main.app), ids, clk
    main.app.dependency_overrides.clear()


def h(uid: int) -> dict:
    return {"X-User-Id": str(uid)}
