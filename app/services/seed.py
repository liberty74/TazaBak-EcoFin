"""Idempotent demo-data bootstrap for the first application start.

Every entity is matched by a stable natural key.  Existing rows are never
overwritten, so restarting the API cannot reset balances or user changes.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    BinContainer,
    Device,
    ForumMessage,
    PointTransaction,
    ShopItem,
    User,
    VolunteerTask,
)
from app.services.passwords import hash_password


logger = logging.getLogger(__name__)


def _seed_users(db: Session) -> None:
    """Create role-aware demo accounts and their opening ledger entries."""

    demo_users = (
        # username, role, opening balance, tier
        ("123", "user", 120, "Eco-Hero"),
        ("volunteer-1", "volunteer", 40, "Eco-Volunteer"),
        ("dispatcher-1", "dispatcher", 0, "Dispatcher"),
        ("Айгерім", "user", 280, "Eco-Legend"),
        ("Диас", "user", 190, "Eco-Hero"),
        ("Мадина", "user", 150, "Eco-Activist"),
    )
    existing_users = {
        user.username: user for user in db.scalars(select(User)).all()
    }

    for username, role, points, tier in demo_users:
        existing_user = existing_users.get(username)
        if existing_user is not None:
            # Demo accounts remain usable after upgrading an existing database.
            if not existing_user.password_hash:
                existing_user.password_hash = hash_password("123")
            continue

        user = User(
            username=username,
            password_hash=hash_password("123"),
            role=role,
            points=points,
            status_tier=tier,
        )
        db.add(user)
        db.flush()

        # A zero-value transaction is forbidden by the database constraint.
        if points:
            db.add(
                PointTransaction(
                    user_id=user.id,
                    amount=points,
                    balance_after=points,
                    transaction_type="OPENING_BALANCE",
                    description="Стартовый демо-баланс",
                    reference_id=f"seed:user:{username}",
                )
            )


def _seed_containers(db: Session) -> None:
    container_data = (
        (
            "bio-central-park-001",
            "bio",
            "Центральный парк",
            "г. Кокшетау, Центральный парк",
            53.2833,
            69.3833,
        ),
        (
            "bio-nish-fmn-001",
            "bio",
            "НИШ ФМН",
            "г. Кокшетау, ул. Жумабаева, 57",
            53.2944,
            69.4048,
        ),
        (
            "municipal-prototype-001",
            "municipal",
            "Умный бак — прототип",
            "Демонстрационный макет TazaBAK",
            53.2833,
            69.3833,
        ),
    )
    existing_container_devices = set(
        db.scalars(select(BinContainer.device_id)).all()
    )

    for device_id, kind, name, address, latitude, longitude in container_data:
        if db.get(Device, device_id) is None:
            db.add(Device(id=device_id, kind=kind))
            db.flush()
        if device_id not in existing_container_devices:
            db.add(
                BinContainer(
                    device_id=device_id,
                    name=name,
                    address=address,
                    latitude=latitude,
                    longitude=longitude,
                    is_active=True,
                    last_fill_level=0.0,
                )
            )


def _seed_volunteer_tasks(db: Session) -> None:
    today = date.today()
    # Titles are natural keys, so new tasks are inserted once without duplicates.
    task_data = (
        ("Сбор хлеба у пекарен", 45, 0, time(9, 0), "Забрать сухой хлеб у партнёрских пекарен и доставить его в хаб."),
        ("Очистка территории вокруг демонстрационного бака", 60, 0, time(10, 30), "Убрать территорию вокруг макета TazaBAK и сообщить о повреждениях."),
        ("Доставка хлеба в приют", 70, 1, time(14, 0), "Доставить проверенный хлеб в городской приют для животных."),
        ("Проверка бокса в Центральном парке", 35, 1, time(11, 0), "Проверить чистоту бокса и заполнить короткий чек-лист."),
        ("Сортировка сухого хлеба в хабе", 50, 2, time(10, 0), "Отделить подходящий сухой хлеб от упаковки и крошек."),
        ("Уборка у ДК Кокшетау", 55, 2, time(16, 0), "Собрать мусор вокруг точки сбора и сделать фотоотчёт."),
        ("Информирование жителей о Миске добра", 40, 3, time(12, 0), "Рассказать посетителям, какой хлеб можно сдавать в бокс."),
        ("Сбор вторсырья у школы", 45, 3, time(15, 0), "Помочь организовать раздельный сбор бумаги и пластика."),
        ("Замена информационной наклейки на боксе", 30, 4, time(10, 0), "Проверить и аккуратно заменить инструкцию на контейнере."),
        ("Подготовка корма для приюта", 65, 4, time(13, 0), "Подготовить безопасный сухой хлеб для передачи животным."),
        ("Эко-рейд по дворам микрорайона", 60, 5, time(11, 0), "Осмотреть точки сбора и отметить переполненные контейнеры."),
        ("Уборка береговой зоны", 80, 5, time(15, 30), "Собрать мусор у водоёма вместе с командой волонтёров."),
        ("Фотоотчёт о точках сбора", 35, 6, time(10, 30), "Сделать актуальные фото трёх боксов для карты проекта."),
        ("Сбор хлеба у кафе-партнёров", 50, 6, time(17, 0), "Забрать подготовленный сухой хлеб у кафе по маршруту."),
        ("Помощь на эко-уроке", 45, 7, time(9, 30), "Помочь провести короткий урок о пищевых отходах для школьников."),
        ("Проверка доступа к боксу", 30, 7, time(14, 0), "Проверить, что зона вокруг бокса свободна и безопасна."),
        ("Посадка цветов у контейнерной площадки", 55, 8, time(11, 0), "Озеленить территорию у точки сбора вместе с жителями."),
        ("Маршрутная доставка в приют", 75, 8, time(15, 0), "Доставить собранный корм по согласованному маршруту."),
        ("Сортировка упаковки от хлеба", 40, 9, time(10, 0), "Отделить бумажную и пластиковую упаковку для переработки."),
        ("Дежурство у демонстрационного бокса", 45, 9, time(18, 0), "Подсказать посетителям правила сдачи хлеба в течение часа."),
        ("Уборка детской площадки", 60, 10, time(12, 0), "Собрать мелкий мусор и рассортировать вторсырьё."),
        ("Создание эко-памяток", 35, 10, time(16, 0), "Подготовить и раздать памятки о правильной сдаче хлеба."),
        ("Проверка контейнеров после выходных", 50, 11, time(9, 0), "Осмотреть точки, зафиксировать заполненность и чистоту."),
        ("Сбор макулатуры в офисах", 55, 11, time(14, 30), "Помочь собрать бумагу для сдачи на переработку."),
        ("Эко-субботник в парке", 85, 12, time(10, 0), "Участие в большой уборке территории Центрального парка."),
        ("Проверка кормовых запасов приюта", 50, 12, time(15, 0), "Помочь сверить переданные объёмы корма и оформить отчёт."),
        ("Раздача многоразовых мешочков", 40, 13, time(11, 0), "Помочь на городской эко-акции и объяснить правила повторного использования."),
        ("Уборка вокруг остановки", 45, 13, time(17, 0), "Собрать мусор вокруг остановки и отсортировать вторсырьё."),
        ("Проверка камеры у контейнера", 35, 14, time(10, 0), "Проверить обзор камеры и чистоту объектива без вмешательства в технику."),
        ("Финальный недельный эко-отчёт", 60, 14, time(18, 0), "Собрать результаты недели и передать их координатору волонтёров."),
        ("Сбор пластиковых крышечек", 40, 15, time(11, 0), "Собрать и передать крышечки в городской пункт переработки."),
        ("Обновление карты эко-точек", 45, 15, time(15, 0), "Проверить адреса и время работы точек сбора для карты проекта."),
        ("Помощь на благотворительной ярмарке", 70, 16, time(12, 0), "Помочь провести эко-ярмарку в поддержку приюта для животных."),
    )
    existing_task_titles = set(db.scalars(select(VolunteerTask.title)).all())

    for title, reward, day_offset, task_time, description in task_data:
        if title not in existing_task_titles:
            db.add(
                VolunteerTask(
                    title=title,
                    reward_points=reward,
                    date=today + timedelta(days=day_offset),
                    time=task_time,
                    description=description,
                    status="open",
                )
            )


def _seed_shop_items(db: Session) -> None:
    item_data = (
        (
            "Уважение",
            "Цифровой знак признательности от сообщества.",
            25,
            "/static/shop/respect.svg",
        ),
        (
            "Эко-значок",
            "Коллекционный значок активиста «Миска добра».",
            60,
            "/static/shop/badge.svg",
        ),
        (
            "Шоппер TazaBAK",
            "Многоразовая сумка для ежедневных добрых дел.",
            90,
            "/static/shop/bag.svg",
        ),
    )
    existing_item_titles = set(db.scalars(select(ShopItem.title)).all())

    for title, description, price, image_url in item_data:
        if title not in existing_item_titles:
            db.add(
                ShopItem(
                    title=title,
                    description=description,
                    price_points=price,
                    image_url=image_url,
                )
            )


def _seed_forum_messages(db: Session) -> None:
    message_count = db.scalar(select(func.count()).select_from(ForumMessage))
    if not message_count:
        db.add_all(
            [
                ForumMessage(
                    username="Айгерім",
                    text="Добро пожаловать в чат сообщества «Миска добра»!",
                ),
                ForumMessage(
                    username="Диас",
                    text="Сегодня отвёз сухой хлеб в контейнер у парка 🌱",
                ),
            ]
        )


def seed_initial_data(
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """Insert missing natural-keyed demo rows without resetting user changes."""

    with session_factory() as db:
        try:
            _seed_users(db)
            _seed_containers(db)
            _seed_volunteer_tasks(db)
            _seed_shop_items(db)
            _seed_forum_messages(db)
            db.commit()
            logger.info("Demo data seed completed")
        except Exception:
            db.rollback()
            logger.exception("Demo data seed failed")
            raise
