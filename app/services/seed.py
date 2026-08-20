"""Idempotent demo-data bootstrap for the first application start.

Every entity is matched by a stable natural key.  Existing rows are never
overwritten, so restarting the API cannot reset balances or user changes.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    BinContainer,
    CollectionEvent,
    CostProfile,
    Device,
    ForumMessage,
    PointTransaction,
    ShopItem,
    Telemetry,
    User,
    VolunteerTask,
    WriteOffRecord,
    utcnow,
)
from app.services.passwords import hash_password


logger = logging.getLogger(__name__)


def _seed_users(db: Session) -> None:
    """Create role-aware demo accounts and their opening ledger entries."""

    # Классы школьникам не проставляются: зачёт должен наполняться реальными
    # регистрациями и принятыми сдачами хлеба. Выдуманные «8Б» и «9А» давали
    # на экране строки с нулевыми килограммами и баллами из стартового
    # баланса — цифры, за которыми не стоит ни одна сдача.
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
        # Пилотные площадки Кокшетау. Координаты ориентировочные и уточняются
        # при монтаже: для расчёта экономики важна плотность точек на маршруте.
        (
            "municipal-abaya-12",
            "municipal",
            "Площадка Абая, 12",
            "г. Кокшетау, ул. Абая, 12",
            53.2871,
            69.3902,
        ),
        (
            "municipal-auezova-31",
            "municipal",
            "Площадка Ауэзова, 31",
            "г. Кокшетау, ул. Ауэзова, 31",
            53.2905,
            69.3961,
        ),
        (
            "municipal-tashenova-7",
            "municipal",
            "Площадка Ташенова, 7",
            "г. Кокшетау, ул. Ж. Ташенова, 7",
            53.2938,
            69.4012,
        ),
        (
            "municipal-gorkogo-45",
            "municipal",
            "Площадка Горького, 45",
            "г. Кокшетау, ул. Горького, 45",
            53.2822,
            69.3958,
        ),
        (
            "municipal-satpaeva-19",
            "municipal",
            "Площадка Сатпаева, 19",
            "г. Кокшетау, ул. Сатпаева, 19",
            53.2790,
            69.4025,
        ),
        (
            "municipal-vasilkovsky-3",
            "municipal",
            "Площадка мкр. Васильковский, 3",
            "г. Кокшетау, мкр. Васильковский, 3",
            53.2996,
            69.4104,
        ),
        (
            "municipal-akan-sery-22",
            "municipal",
            "Площадка Акана Сері, 22",
            "г. Кокшетау, ул. Акана Сері, 22",
            53.2864,
            69.4081,
        ),
        (
            "municipal-ualikhanova-58",
            "municipal",
            "Площадка Уалиханова, 58",
            "г. Кокшетау, ул. Ш. Уалиханова, 58",
            53.2917,
            69.3874,
        ),
        (
            "municipal-nazarbaeva-104",
            "municipal",
            "Площадка пр. Назарбаева, 104",
            "г. Кокшетау, пр. Н. Назарбаева, 104",
            53.2953,
            69.4143,
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


PILOT_ORG_NAME = "Коммунальная служба Кокшетау (пилот)"
COLLECTION_HISTORY_DAYS = 30


def _seed_cost_profile(db: Session) -> None:
    """Economic parameters of the pilot operator.

    Values are pilot estimates and are meant to be corrected from the
    dispatcher panel once real route data arrives:

    * 1.5 км и 6 минут — среднее расстояние и время обслуживания одной
      площадки внутри городского маршрута;
    * 26 л/100 км — типовой расход мусоровоза на базе МАЗ;
    * 331 ₸/л — дизель в Казахстане, июль 2026;
    * 3.5 рейса в неделю — действующий график вывоза, с которым сравнивается
      вывоз по фактической заполненности;
    * 2.68 кг CO2 на литр — коэффициент сжигания дизельного топлива.

    Тариф выведен из этих же цифр, а не назначен произвольно.

    Один заезд на площадку стоит оператору 379 ₸ (0.39 л дизеля — 129 ₸,
    шесть минут бригады — 250 ₸). На десяти контейнерах график даёт 150
    заездов в месяц, вывоз по факту заполненности — 92, то есть мы
    экономим 58 заездов, или около 2 200 ₸ на контейнер в месяц.

    * 1 000 ₸ подписки — меньше половины создаваемой экономии (45%).
      Клиент оставляет себе около 1 200 ₸ на бак каждый месяц, иначе
      платформу незачем покупать. Прежние 5 000 ₸ были вдвое больше всей
      экономии, оператор уходил в минус, и срок окупаемости не
      определялся — тариф был назначен без опоры на расчёт.
    * 28 000 ₸ установки — комплектующие и монтаж одного бака: ESP32
      около 2 500 ₸, HC-SR04 — 800 ₸, DS18B20 — 1 000 ₸, привод SG90 —
      1 200 ₸, корпус и проводка — 3 000 ₸, питание с солнечной панелью —
      8 000 ₸, монтаж — 5 000 ₸. Итого около 21 500 ₸, остальное —
      гарантия и запас на брак.
    """

    if db.scalar(select(CostProfile).where(CostProfile.org_name == PILOT_ORG_NAME)):
        return

    db.add(
        CostProfile(
            org_name=PILOT_ORG_NAME,
            city="Кокшетау",
            is_default=True,
            km_per_stop=1.5,
            minutes_per_stop=6.0,
            fuel_consumption_l_per_100km=26.0,
            fuel_price_kzt_per_liter=331.0,
            crew_cost_kzt_per_hour=2_500.0,
            baseline_trips_per_week=3.5,
            fill_threshold_percent=80.0,
            co2_kg_per_liter=2.68,
            bread_avg_weight_kg=0.4,
            bread_cost_kzt_per_kg=450.0,
            install_price_kzt=28_000.0,
            subscription_kzt_per_month=1_000.0,
        )
    )
    db.flush()


def _seed_collection_history(db: Session) -> None:
    """Thirty days of servicing history so the savings chart opens populated.

    Live telemetry creates these events by itself when a bin is emptied. This
    backfill only gives a fresh database something to draw, and every row is
    marked ``SEED`` so demo data can never be mistaken for measurements.
    """

    already_seeded = db.scalar(
        select(func.count())
        .select_from(CollectionEvent)
        .where(CollectionEvent.source == "SEED")
    )
    if already_seeded:
        return

    containers = db.scalars(
        select(BinContainer)
        .join(Device, Device.id == BinContainer.device_id)
        .where(Device.kind == "municipal")
        .order_by(BinContainer.id.asc())
    ).all()
    if not containers:
        return

    period_end = utcnow()
    period_start = period_end - timedelta(days=COLLECTION_HISTORY_DAYS)

    for container in containers:
        # Deterministic per container: the same database always demos the same.
        generator = random.Random(f"tazabak:{container.device_id}")
        moment = period_start + timedelta(hours=generator.uniform(0, 48))
        while moment < period_end:
            db.add(
                CollectionEvent(
                    device_id=container.device_id,
                    container_id=container.id,
                    collected_at=moment,
                    # A bin is serviced once it passes the dispatch threshold,
                    # so the level before the visit sits just above it.
                    fill_ema_before_percent=round(generator.uniform(80.0, 96.0), 2),
                    fill_raw_before_percent=round(generator.uniform(82.0, 99.0), 2),
                    source="SEED",
                )
            )
            moment += timedelta(days=generator.uniform(2.2, 4.0))


def _seed_recent_telemetry(db: Session) -> None:
    """Readings of the current filling cycle, so the forecast has a trend.

    The physical prototype is deliberately excluded: it sends its own real
    telemetry during a demo, and synthetic history would corrupt it.
    """

    containers = db.scalars(
        select(BinContainer)
        .join(Device, Device.id == BinContainer.device_id)
        .where(
            Device.kind == "municipal",
            BinContainer.device_id != "municipal-prototype-001",
        )
        .order_by(BinContainer.id.asc())
    ).all()

    now = utcnow()
    for container in containers:
        already_measured = db.scalar(
            select(func.count())
            .select_from(Telemetry)
            .where(Telemetry.device_id == container.device_id)
        )
        if already_measured:
            continue

        generator = random.Random(f"tazabak:telemetry:{container.device_id}")
        # Each site fills at its own pace, and each is at its own point in the
        # cycle, so the dispatcher sees a spread of arrival times.
        fill_now = generator.uniform(24.0, 88.0)
        rate_per_hour = generator.uniform(0.5, 1.6)

        last_collected = db.scalar(
            select(CollectionEvent.collected_at)
            .where(CollectionEvent.device_id == container.device_id)
            .order_by(CollectionEvent.collected_at.desc())
            .limit(1)
        )
        earliest = now - timedelta(hours=14)
        if last_collected is not None:
            earliest = max(earliest, last_collected + timedelta(hours=1))

        moments: list[datetime] = []
        moment = now
        while moment > earliest:
            moments.append(moment)
            moment -= timedelta(hours=2)
        moments.reverse()
        if len(moments) < 3:
            continue

        fill_ema = None
        for moment in moments:
            hours_before = (now - moment).total_seconds() / 3600.0
            trend = max(0.0, fill_now - rate_per_hour * hours_before)
            # HC-SR04 is noisy; the smoothed series follows the trend itself.
            raw = min(100.0, max(0.0, trend + generator.uniform(-2.5, 2.5)))
            fill_ema = trend if fill_ema is None else 0.3 * raw + 0.7 * fill_ema
            temp_in = generator.uniform(18.0, 24.0)
            temp_out = temp_in - generator.uniform(0.5, 3.0)
            db.add(
                Telemetry(
                    device_id=container.device_id,
                    distance_cm=round(25.0 - raw / 100.0 * 18.0, 2),
                    temp_in_c=round(temp_in, 2),
                    temp_out_c=round(temp_out, 2),
                    temperature_delta_c=round(temp_in - temp_out, 2),
                    delta_rate_c_per_sec=0.0,
                    sampling_interval_seconds=7200.0,
                    fill_raw_percent=round(raw, 2),
                    fill_ema_percent=round(fill_ema, 2),
                    fire_score=round(0.7 * (temp_in - temp_out), 4),
                    fire_streak=0,
                    measured_at=moment,
                    received_at=moment,
                )
            )

        if fill_ema is not None:
            container.last_fill_level = round(fill_ema, 2)


def _seed_write_offs(db: Session) -> None:
    """Four weeks of a bakery's evening leftovers.

    The weekday forecast needs several samples of the same weekday before it
    can say anything, so a fresh database starts with a month of history.
    """

    profile = db.scalar(select(CostProfile).where(CostProfile.org_name == PILOT_ORG_NAME))
    if profile is None:
        return
    if db.scalar(
        select(func.count())
        .select_from(WriteOffRecord)
        .where(WriteOffRecord.profile_id == profile.id)
    ):
        return

    # Пн, Вт, Ср, Чт, Пт, Сб, Вс — по пятницам разбирают лучше, по выходным
    # пекут с запасом и остаётся больше.
    weekday_factor = (1.0, 1.15, 1.0, 0.95, 0.8, 1.25, 1.3)
    products = (
        ("Хлеб пшеничный", 8.0, 450.0),
        ("Багет", 3.0, 520.0),
        ("Булочки", 4.0, 600.0),
    )

    today = date.today()
    for day_offset in range(1, 29):
        day = today - timedelta(days=day_offset)
        for product, base_kg, cost in products:
            generator = random.Random(f"tazabak:writeoff:{product}:{day.isoformat()}")
            written = base_kg * weekday_factor[day.weekday()] * generator.uniform(0.85, 1.15)
            donated = written * generator.uniform(0.7, 0.9)
            db.add(
                WriteOffRecord(
                    profile_id=profile.id,
                    occurred_on=day,
                    product=product,
                    kg_written_off=round(written, 2),
                    kg_donated=round(donated, 2),
                    cost_kzt_per_kg=cost,
                )
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
            _seed_cost_profile(db)
            db.flush()
            _seed_collection_history(db)
            _seed_recent_telemetry(db)
            _seed_write_offs(db)
            db.commit()
            logger.info("Demo data seed completed")
        except Exception:
            db.rollback()
            logger.exception("Demo data seed failed")
            raise
