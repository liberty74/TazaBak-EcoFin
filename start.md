back:
cd C:\Users\admin\Desktop\TazaBak\backend

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


front:
cd C:\Users\admin\Desktop\TazaBak\backend\frontend

npm install
npm run dev