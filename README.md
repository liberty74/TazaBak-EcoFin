# TazaBAK EcoFin

Smart City & GreenTech MVP для управления отходами в Кокшетау — платформа
Future Minds Hackathon 2026, трек **EcoFin**.

## О разработке — что было до хакатона и что делается сейчас

Команда развивает свою предыдущую разработку — платформу мониторинга
контейнерных площадок, созданную в начале августа 2026
(исходный репозиторий: [`liberty74/TazaBak`](https://github.com/liberty74/TazaBak)).

Разрешение на развитие собственной предыдущей разработки как основы для
проекта на треке EcoFin получено от Оргкомитета Future Minds Hackathon 2026.

В этом репозитории:

- **Базовые коммиты `base(backend)`, `base(frontend)`, `base(iot)`** — перенос
  существующей платформы: FastAPI backend, React/Vite frontend, прошивка ESP32.
  Это стартовая точка, а не работа, выполненная во время хакатона.
- **Все коммиты после базовых** — новый экономический слой EcoFin, разработанный
  в период онлайн-этапа хакатона (15–25 августа 2026): расчёт сэкономленных
  рейсов, топлива, денег и CO₂, прогноз заполнения контейнеров, планировщик
  маршрута, кабинет малого бизнеса и AI-рекомендации на посчитанных метриках.

## Что умеет MVP

- роли `user`, `volunteer`, `dispatcher`;
- регистрация и вход пользователей;
- SQLite + SQLAlchemy с автоматическим созданием таблиц;
- идемпотентный seed демо-данных;
- анализ фото хлеба через YOLOv8;
- статусы `approve`, `reject`, `invalid`;
- QR-префиксы `GOOD`, `BAD`, `NONE`;
- начисление и списание баллов через единый ledger;
- магазин и процедурная генерация Eco-NFT в SVG;
- волонтёрские задания и подтверждение выполнения диспетчером;
- карта контейнеров;
- телеметрия ESP32;
- EMA-фильтр заполненности;
- FireScore и алерт `FIRE_RISK`;
- mock-детекция `ILLEGAL_DUMP` по кадру ESP32-CAM;
- WebSocket-команды `OPEN_LID` и `CLOSE_LID`;
- диспетчерская панель;
- AI-помощник Баки с Gemini и offline fallback;
- симулятор телеметрии и анализа хлеба.

## Архитектура

```text
ESP32 + HC-SR04 + DS18B20 + SG90
             │ HTTP telemetry / WebSocket
ESP32-CAM ───┤
             ▼
        FastAPI backend
             │
       SQLAlchemy ORM
             │
          SQLite
             │
       React/Vite frontend
```

Backend отвечает за бизнес-логику и безопасность, frontend — за интерфейс, SQLite — за сохранение состояния, ESP32 — за датчики и физические действия.

## Структура проекта

```text
app/main.py              создание FastAPI, роутеры, CORS, startup
app/config.py            настройки из .env
app/database.py          engine, SessionLocal, Base, миграции
app/models.py            SQLAlchemy-модели таблиц
app/schemas.py           Pydantic v2 request/response-схемы
app/security.py          проверка X-Dispatcher-Key
app/middleware.py        лимит размера multipart-запросов

app/api/                 HTTP/WebSocket endpoints
app/services/            бизнес-логика, не зависящая от HTTP
static/                  изображения и SVG-файлы
frontend/                React/Vite сайт
firmware/                прошивка ESP32
tests/                   pytest-тесты
simulator.py             симулятор IoT и Bio-потока
```

## Требования

- Python 3.10 или новее;
- Node.js 18 или новее;
- npm;
- Git — только для управления репозиторием;
- Windows PowerShell, Linux или macOS.

## Локальная настройка backend

```powershell
cd TazaBak-EcoFin
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Создай `.env` на основе `.env.example`.

Минимальная конфигурация:

```env
DATABASE_URL=sqlite:///./tazabak.db
APP_ENV=development
SEED_DEMO_DATA=true
DISPATCHER_API_KEY=123
GEMINI_API_KEY=
```

Если ключ Gemini отсутствует, `/api/ai/chat` работает в offline-fallback-режиме и возвращает локальный экологический совет.

## Запуск backend

```powershell
cd TazaBak-EcoFin
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Адреса:

```text
API:      http://localhost:8000
Swagger:  http://localhost:8000/docs
OpenAPI:  http://localhost:8000/openapi.json
Health:   http://localhost:8000/health
```

При первом запуске автоматически создаются `tazabak.db`, папки `static/bio`, `static/vision`, `static/shop` и демо-данные.

## Запуск frontend

Во втором терминале:

```powershell
cd TazaBak-EcoFin\frontend
npm install
npm run dev
```

Frontend откроется на:

```text
http://localhost:5173
```

По умолчанию frontend обращается к `http://127.0.0.1:8000`. Другой адрес можно задать в `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Демо-пользователи

Seed создаёт роли:

| Username | Роль | Назначение |
|---|---|---|
| `123` | `user` | сдача хлеба, баллы, магазин |
| `volunteer-1` | `volunteer` | регистрация на добрые дела |
| `dispatcher-1` | `dispatcher` | панель мониторинга |

Диспетчерские операции дополнительно требуют заголовок:

```http
X-Dispatcher-Key: 123
```

В production нужно заменить демонстрационный ключ.

## Основные endpoints

### Авторизация

```text
POST /api/auth/register
POST /api/auth/login
```

### Профиль и карта

```text
GET /api/users/{user_id}
GET /api/users/{user_id}/transactions
GET /api/users/{user_id}/nfts
GET /api/users/{user_id}/dashboard
GET /api/leaderboard
GET /api/containers
```

### Волонтёрство

```text
GET  /api/volunteer/tasks
POST /api/volunteer/tasks/{task_id}/register
POST /api/volunteer/tasks/{task_id}/complete
```

`complete` выполняется диспетчером и требует `X-Dispatcher-Key`.

### Магазин и Eco-NFT

```text
GET  /api/shop/items
POST /api/shop/buy
POST /api/shop/mint-nft
```

### Сообщество и AI

```text
GET  /api/community/chat
POST /api/community/chat
POST /api/ai/chat
```

### IoT и компьютерное зрение

```text
POST /api/bio/analyze
POST /api/sensors/ingest
POST /api/vision/frame
WS   /ws/device/{device_id}
```

### Диспетчер

```text
GET   /api/dispatch/summary
GET   /api/dispatch/briefing
PATCH /api/alerts/{alert_id}/resolve
GET   /api/dispatcher/devices/status
PUT   /api/dispatcher/devices/{device_id}/camera
POST  /api/dispatcher/devices/{device_id}/command
GET   /api/dispatcher/commands
```

Все dispatcher endpoints требуют `X-Dispatcher-Key`.

## Сценарий сдачи хлеба

Frontend отправляет multipart-запрос:

```text
POST /api/bio/analyze
file=<image>
user_id=123
device_id=bio-demo-001
idempotency_key=<unique-key>
```

Backend:

1. проверяет пользователя и устройство;
2. сохраняет и валидирует изображение;
3. запускает YOLOv8;
4. классифицирует найденные классы;
5. сохраняет `BioAnalysis`;
6. начисляет 15 баллов при `approve`;
7. создаёт `OPEN_LID`;
8. отправляет команду через WebSocket.

Результаты:

```text
approve — хлеб найден и пригоден
reject  — обнаружен класс плесени/порчи
invalid — подходящий хлеб не найден
```

Коды имеют уникальный префикс:

```text
GOOD...... — approve, 15 баллов
BAD.......  — reject, 0 баллов
NONE...... — invalid, 0 баллов
```

## Сценарий муниципального контейнера

ESP32 отправляет:

```json
{
  "device_id": "municipal-prototype-001",
  "distance": 45,
  "temp_in": 24,
  "temp_out": 21
}
```

Endpoint `/api/sensors/ingest`:

1. сохраняет измерение;
2. рассчитывает заполненность для физического бака высотой 25 см;
3. считает `0%` при расстоянии `25 см` и `100%` при `7 см`;
4. применяет EMA с `alpha=0.3` между физическими границами;
5. сохраняет FireScore как диагностическую метрику;
6. при температуре единственного DS18B20 **строго выше 50°C** сразу создаёт `FIRE_RISK`;
7. создаёт `CLOSE_LID`;
8. отправляет команду подключённому устройству по WebSocket.

Формулы:

```text
raw_fill = (25 - distance) / (25 - 7) * 100

EMA = 0.3 * current_raw + 0.7 * previous_ema

FireScore = 0.7 * (temp_in - temp_out)
          + 0.3 * delta_rate

FIRE_RISK = temp_in > 50°C
```

`temp_out` сохраняется для совместимости и диагностического FireScore, но не
участвует в принятии пожарного решения для текущего макета с одним DS18B20.

## WebSocket ESP32

ESP32 подключается к:

```text
ws://<компьютер>:8000/ws/device/municipal-prototype-001
```

Backend может отправить:

```json
{"action":"CLOSE_LID","command_id":15}
```

или:

```json
{"action":"OPEN_LID","command_id":16}
```

В текущем MVP реестр подключённых устройств хранится в памяти одного процесса. Поэтому Uvicorn запускается с одним worker.

## ESP32-CAM

Кадр отправляется в:

```text
POST /api/vision/frame
```

Поток MJPEG можно сохранить через диспетчерский endpoint:

```text
PUT /api/dispatcher/devices/{device_id}/camera
```

```json
{
  "stream_url": "http://192.168.1.50:81/stream"
}
```

Frontend получает поток через:

```text
GET /api/cameras/{device_id}/stream
```

После сохранения MJPEG URL backend каждые 5 секунд:

1. получает JPEG через стандартный endpoint ESP32-CAM `/capture`;
2. запускает `yolov8n.pt`;
3. сохраняет размеченный кадр в `static/vision`;
4. создаёт или обновляет один открытый `ILLEGAL_DUMP` без спама дублями;
5. показывает кадр с рамками и классы объектов в окне «Камера ИИ».

Ручной анализ для презентации:

```text
POST /api/dispatcher/devices/{device_id}/camera/analyze
```

Последний обработанный кадр:

```text
GET /api/dispatcher/devices/{device_id}/camera/analysis
```

## Симулятор

Один тестовый цикл:

```powershell
python simulator.py --once
```

Несколько сценариев:

```powershell
python simulator.py --cycles 3 --interval 2
```

Симулятор проходит фазы `normal`, `filling`, `heating`, `fire`, `cooldown`, отправляет HTTP-запросы и проверяет изменение баланса.

## Тесты

```powershell
pip install -r requirements-dev.txt
pytest -q
```

Тесты используют отдельную временную SQLite-базу и не изменяют рабочий `tazabak.db`.

## Docker

```powershell
docker build -t tazabak-backend .
docker run --env-file .env -p 8000:8000 tazabak-backend
```

## Ограничения текущего MVP

- SQLite подходит для локальной демонстрации и небольшого MVP;
- WebSocket-реестр рассчитан на один Uvicorn worker;
- `/api/vision/frame` использует mock-триггер, а подключённая ESP32-CAM анализируется реальным YOLOv8 (заменяется на единый реальный путь в рамках EcoFin-модуля);
- QR-коды генерируются с уникальным префиксом и случайным числовым суффиксом;
- JWT-аутентификация пока не используется;
- для production понадобятся PostgreSQL, Redis/WebSocket broker, полноценные миграции и секретный менеджер.
