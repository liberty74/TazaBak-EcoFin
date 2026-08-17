# TazaBAK — «Миска добра» frontend

Адаптивный React-интерфейс для жителей, волонтёров и диспетчеров экосистемы TazaBAK.

## Локальный запуск

Требуется Node.js 20+ и запущенный FastAPI backend.

```powershell
Copy-Item .env.example .env
npm install
npm run dev
```

Frontend: http://localhost:5173  
Backend: http://127.0.0.1:8000  
Swagger: http://127.0.0.1:8000/docs

Backend запускается из родительской папки:

```powershell
cd ..
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Демо-профили: `123`, `volunteer-1`, `dispatcher-1`; пароль для каждого — `123`. При входе диспетчера введите ключ `123` (значение `DISPATCHER_API_KEY` в backend `.env`).

`GEMINI_API_KEY` также задаётся только в backend `.env` и никогда не помещается во frontend.

## Проверки

```powershell
npm run typecheck
npm run test:run
npm run build
```

При 403 в панели диспетчера повторно введите ключ. При сетевой ошибке проверьте `/health`, `VITE_API_BASE_URL` и CORS backend.
