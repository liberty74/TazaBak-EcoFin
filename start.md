# Как запустить TazaBAK

Два способа. Docker — когда нужно просто показать работающий продукт. Ручной
запуск — когда правишь код и хочешь видеть изменения без пересборки.

---

# Способ 1. Docker — весь стенд одной командой

Поднимает сразу три сервиса: PostgreSQL, backend и frontend.

```powershell
cd C:\Users\admin\Desktop\TazaBak-EcoFin
docker compose up --build
```

Готово, когда в логах появится `Application startup complete`.

| Что | Адрес |
|---|---|
| Интерфейс | <http://localhost:5173> |
| API и Swagger | <http://localhost:8000/docs> |
| Проверка живости | <http://localhost:8000/health> |
| PostgreSQL с хоста | `localhost:5432`, база `tazabak`, пользователь `tazabak`, пароль `tazabak` |

Вход: житель `123` / `123`, диспетчер `dispatcher-1` / `123`, ключ диспетчера
`123`.

## Команды на каждый день

```powershell
docker compose up -d          # запустить в фоне
docker compose ps             # что поднято и здорово ли
docker compose logs -f backend   # смотреть логи backend
docker compose stop           # остановить, данные сохранить
docker compose down           # остановить и убрать контейнеры
docker compose down -v        # ... и стереть базу вместе с загруженными фото
```

`down -v` удаляет тома. Демо-данные засеются заново при следующем запуске, но
всё, что вы наделали руками, пропадёт.

## Что где хранится

| Том | Что внутри |
|---|---|
| `tazabak-postgres` | База: пользователи, баллы, телеметрия, тревоги |
| `tazabak-static` | Загруженные фото хлеба и кадры камеры |

Тома переживают `docker compose down` и перезагрузку компьютера. Пропадают
только по `down -v`.

## Открыть с телефона или другого компьютера

По умолчанию адрес backend вшит в бандл как `http://localhost:8000`. Для
браузера на телефоне `localhost` — это сам телефон, поэтому страница откроется,
а данные не загрузятся.

Vite подставляет адрес во время компиляции, менять его в рантайме нельзя, —
значит фронтенд нужно пересобрать под адрес ноутбука:

```powershell
$env:VITE_API_BASE_URL = 'http://192.168.10.5:8000'
docker compose up -d --build frontend
```

IP смотрите в выводе `scripts\start-local.ps1` или в `ipconfig`. После этого
сайт открывается по `http://192.168.10.5:5173` с любого устройства в той же
сети.

## Первая сборка долгая

Ставится torch и в образ запекаются веса YOLOv8 и CLIP — около 20 минут и
несколько гигабайт. Дальше всё берётся из слоёв Docker, и стенд поднимается за
секунды.

Веса запекаются намеренно: на защите Wi-Fi может не быть, а иначе первый же
запрос уходил бы качать 600 МБ с Hugging Face и выглядел как зависшее
приложение.

## Если что-то не поднялось

**`failed to connect to the docker API`** — не запущен Docker Desktop. Запустите
его и дождитесь, пока значок кита перестанет мигать.

**`port is already allocated`** — порт занят другим процессом. Чаще всего это
локальный `uvicorn` или `npm run dev`, оставшийся с прошлого раза. Docker и
ручной запуск нельзя держать одновременно: они спорят за 8000 и 5173.

```powershell
netstat -ano | Select-String ":8000 "      # узнать PID
Stop-Process -Id <PID> -Force
```

**Frontend поднялся, но данных нет** — откройте <http://localhost:8000/health>.
Если он не отвечает, смотрите `docker compose logs backend`.

**Хочу свой ключ Gemini** — положите его в `.env` рядом с `docker-compose.yml`:

```env
GEMINI_API_KEY=ваш_ключ
```

Без ключа советы Баки собираются локальными правилами по тем же числам —
стенд остаётся рабочим и без интернета.

---

# Способ 2. Ручной запуск — для разработки

Здесь backend перезапускается сам при правке кода, а frontend обновляет
страницу на лету. Для показа железа этот способ тоже удобнее: плата ESP32
ходит на адрес ноутбука, и его печатает скрипт запуска.

## Всё сразу

```powershell
cd C:\Users\admin\Desktop\TazaBak-EcoFin
powershell -ExecutionPolicy Bypass -File scripts\start-local.ps1
```

Скрипт поднимет оба сервера, при необходимости поставит зависимости фронтенда
и напечатает IP ноутбука для прошивки ESP32.

## Или руками, в двух терминалах

```powershell
# первый терминал — backend
cd C:\Users\admin\Desktop\TazaBak-EcoFin
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```powershell
# второй терминал — frontend
cd C:\Users\admin\Desktop\TazaBak-EcoFin\frontend
npm install
npm run dev -- --host 0.0.0.0
```

`--host 0.0.0.0` обязателен в обоих, если рядом работает плата: с `localhost`
сервер слушает только сам себя, и ESP32 из той же сети до него не достучится.

## Первый запуск: окружение

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

При первом старте создаются таблицы, папки `static/bio`, `static/vision`,
`static/shop` и демо-данные.

## Проверить, что стенд живой

```powershell
.venv\Scripts\python.exe scripts\check-local.py
```

Двенадцать проверок по звеньям: backend, база, приём замеров, пожарная
блокировка, очередь команд, WebSocket, интерфейс, правило брандмауэра. Первый
же провал называет порвавшееся звено — это точнее, чем открывать экраны и
гадать.

---

# Плата ESP32

В [`firmware/municipal_esp32/municipal_esp32.ino`](firmware/municipal_esp32/municipal_esp32.ino):

```cpp
#define TAZABAK_CLOUD 0                       // 0 — стенд рядом, 1 — облако
constexpr char BACKEND_HOST[] = "192.168.10.5";   // IP из вывода start-local.ps1
```

IP выдаёт роутер, и он меняется после переподключения к Wi-Fi — сверяйте перед
каждым показом. Плата с чужим адресом выглядит исправной: Wi-Fi подключён, а в
мониторе порта бесконечное `WebSocket disconnected`.

**Брандмауэр.** Windows по умолчанию отбивает входящие соединения, и плата
получает молчание вместо ответа. Один раз выполните в PowerShell от
администратора:

```powershell
New-NetFirewallRule -DisplayName 'TazaBAK local stand' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000,5173 -Profile Any -RemoteAddress LocalSubnet
```

Подробности по сборке железа — [`docs/HARDWARE.md`](docs/HARDWARE.md).

---

# Что выбрать

| Задача | Способ |
|---|---|
| Показать продукт жюри или другу | Docker |
| Правлю код и хочу видеть результат сразу | Ручной запуск |
| Работаю с платой ESP32 | Ручной запуск |
| Нужен PostgreSQL как в облаке | Docker |
| Проверить, что всё собирается с нуля | Docker |
