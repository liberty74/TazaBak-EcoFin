# TazaBAK EcoFin — backend.
#
# Слои разложены так, чтобы правка кода не пересобирала зависимости: torch
# приезжает вместе с ultralytics и весит больше гигабайта, и пересобирать его
# на каждое изменение эндпоинта нельзя.
FROM python:3.12-slim

# Ultralytics тянет OpenCV, а тому нужны системные библиотеки, которых в slim
# нет. libgl1 и libglib2.0-0 — минимум, без них падает уже импорт cv2.
# libgomp1 нужен torch для многопоточности на CPU, curl — для healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models/huggingface \
    YOLO_CONFIG_DIR=/models/ultralytics

WORKDIR /app

# Ставим CPU-сборку torch: образ с CUDA весит на несколько гигабайт больше,
# а видеокарты в контейнере всё равно нет.
COPY requirements.txt ./
RUN pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements.txt

# Веса запекаются в образ, чтобы контейнер работал офлайн. На защите Wi-Fi
# может не быть, а первый холодный запрос иначе уходит качать 600 МБ CLIP с
# Hugging Face и выглядит как зависшее приложение.
RUN mkdir -p /models \
    && python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')" \
    && python -c "\
from transformers import CLIPModel, CLIPProcessor;\
name='openai/clip-vit-base-patch32';\
CLIPModel.from_pretrained(name);\
CLIPProcessor.from_pretrained(name)"

COPY app ./app
COPY static ./static
COPY main.py simulator.py ./

# Приложение пишет в базу и в static — от root это работает, но незачем.
RUN useradd --create-home --uid 10001 tazabak \
    && mkdir -p /data \
    && chown -R tazabak:tazabak /app /models /data
USER tazabak

EXPOSE 8000

# Проверка живости берёт тот же /health, что и фронтенд: если он отвечает,
# значит поднялись и база, и миграции.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
