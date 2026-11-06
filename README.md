# ІС «Відпустка» - MVP (Sprint 1)

React (Vite, shadcn/ui) + FastAPI + SQLite + SQLAlchemy. Код відповідає `SYNC-SPEC.md` і Class Diagram:
8 статусів `LeaveStatus`, скасування `cancel()` лише зі статусу «Подано», одне нагадування командиру
через 72 год від `submittedAt`. Імена класів, атрибутів і методів збігаються з діаграмою (camelCase).

## Запуск (2 команди, у двох терміналах)

```bash
# 1. бекенд (http://127.0.0.1:8000, база `backend/vacations_v3.db` і тестові дані створюються автоматично)
python3 -m venv venv && venv/bin/pip install -r backend/requirements.txt && cd backend && ../venv/bin/uvicorn main:app

# 2. фронтенд (http://localhost:5173, API проксується на бекенд)
cd frontend && npm install && npm run dev
```

Тести: `venv/bin/python -m pytest tests`

## Ролі

Перемикач у шапці викликає `POST /login` (`User.authenticate`, пароль усіх тестових користувачів `demo`),
далі фронтенд передає заголовок `X-User-Id`. Тестові дані: 2 роти, у кожній свій командир (Коваль, Савчук)
і 5 військовослужбовців, 1 відповідальний за кадровий облік (Кравчук).

- Військовослужбовець: залишок днів, нова заявка, «Мої заявки», кнопка «Скасувати» (лише Подано).
- Командир: заявки свого підрозділу (відкрити, погодити, відхилити з причиною), «Графік відпусток».
- Відповідальний за кадровий облік: «Графік відпусток», «Історія підрозділу», «Довідник норм».

Чернетка існує лише у формі на клієнті: заявка створюється на сервері при поданні.

## API

`POST /login`, `GET /balance`, `POST /requests`, `GET /requests`, `POST /requests/{id}/cancel|open|approve|reject`,
`GET /schedule`, `GET /history`, `GET /norms`, `PUT /norms/{type}`,
`GET /notifications` (`?mark_read=true` позначає прочитаними).
Службові: `GET /dev/users` (список для перемикача ролей), `POST /dev/tick?now=ISO` (підміна часу для таймера).

Таймер у `main.py` раз на хвилину (та сама логіка в `/dev/tick`): викликає `NotificationService.deadlineReached`
для заявок у статусах «Подано» і «На розгляді» через 72 год від `submittedAt` (якщо `reminderSent` хибне)
і переводить «Внесено до графіка» у «Виконано» після `dateTo`.
