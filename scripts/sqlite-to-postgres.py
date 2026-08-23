"""Перенос данных локального стенда из SQLite в PostgreSQL.

Нужен при переезде с ручного запуска на Docker: ручной стенд по умолчанию
пишет в `tazabak.db`, докер — в PostgreSQL в томе. Это две независимые базы, и
адрес камеры, тревоги и история замеров, накопленные в одной, во второй не
появляются сами.

Запуск при поднятом `docker compose`:

    .venv\\Scripts\\python.exe scripts\\sqlite-to-postgres.py

Перенос замещающий: все таблицы PostgreSQL очищаются и заполняются заново из
SQLite. Демонстрационные данные в PostgreSQL засеиваются при старте и своей
истории не несут, поэтому сливать две базы построчно незачем.

Перед запуском стоит снять копию:

    docker compose exec -T db pg_dump -U tazabak -d tazabak > pg_before.sql
"""

from __future__ import annotations

import io
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import psycopg

DEFAULT_SQLITE = Path(__file__).resolve().parent.parent / "tazabak.db"
DEFAULT_DSN = "postgresql://tazabak:tazabak@localhost:5432/tazabak"

out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", write_through=True)


def log(message: str) -> None:
    print(message, file=out)


def parse_datetime(value: object) -> object:
    """SQLite хранит даты строками, PostgreSQL ждёт настоящий timestamp."""

    if value is None or isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        # Запас на случай записи без микросекунд или с лишним хвостом.
        return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")


def convert(value: object, pg_type: str) -> object:
    """Привести значение из SQLite к типу, который ждёт столбец PostgreSQL."""

    if value is None:
        return None
    if pg_type == "boolean":
        # В SQLite булево — это 0 или 1, изредка строка.
        if isinstance(value, str):
            return value.lower() in {"1", "true", "t", "yes"}
        return bool(value)
    if pg_type in {"timestamp without time zone", "timestamp with time zone"}:
        return parse_datetime(value)
    if pg_type == "date":
        parsed = parse_datetime(value)
        return parsed.date() if isinstance(parsed, datetime) else value
    if pg_type in {"json", "jsonb"} and isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def main() -> int:
    sqlite_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SQLITE
    dsn = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DSN

    if not sqlite_path.exists():
        log(f"Не найдена база SQLite: {sqlite_path}")
        return 1

    sqlite_db = sqlite3.connect(sqlite_path)
    sqlite_db.row_factory = sqlite3.Row

    tables = [
        row[0]
        for row in sqlite_db.execute(
            "select name from sqlite_master where type='table' "
            "and name not like 'sqlite_%' order by name"
        )
    ]

    moved: dict[str, int] = {}
    skipped_columns: list[str] = []

    with psycopg.connect(dsn, autocommit=False) as pg:
        with pg.cursor() as cur:
            # Внешние ключи на время переноса отключаются: иначе порядок таблиц
            # пришлось бы выстраивать вручную, а одна ошибка в нём оставила бы
            # базу наполовину перенесённой. Требует прав суперпользователя —
            # у владельца базы в образе postgres они есть.
            cur.execute("SET session_replication_role = replica")

            for table in tables:
                cur.execute(
                    "select column_name, data_type from information_schema.columns "
                    "where table_schema='public' and table_name=%s",
                    (table,),
                )
                pg_columns = {name: kind for name, kind in cur.fetchall()}
                if not pg_columns:
                    log(f"  пропуск {table}: таблицы нет в PostgreSQL")
                    continue

                sqlite_columns = [
                    row[1] for row in sqlite_db.execute(f'pragma table_info("{table}")')
                ]
                # Столбцы, оставшиеся от прежних версий схемы, переносить некуда.
                shared = [name for name in sqlite_columns if name in pg_columns]
                skipped_columns.extend(
                    f"{table}.{name}" for name in sqlite_columns if name not in pg_columns
                )

                cur.execute(f'delete from "{table}"')

                quoted = ", ".join(f'"{name}"' for name in shared)
                rows = sqlite_db.execute(f'select {quoted} from "{table}"').fetchall()

                if rows:
                    placeholders = ", ".join(["%s"] * len(shared))
                    cur.executemany(
                        f'insert into "{table}" ({quoted}) values ({placeholders})',
                        [
                            tuple(convert(row[name], pg_columns[name]) for name in shared)
                            for row in rows
                        ],
                    )

                moved[table] = len(rows)

            # Счётчики id остаются на старых значениях, и следующая вставка
            # столкнулась бы с уже занятым первичным ключом.
            cur.execute(
                "select table_name, column_name from information_schema.columns "
                "where table_schema='public' and column_default like 'nextval%'"
            )
            sequences = cur.fetchall()
            for table, column in sequences:
                cur.execute(
                    f"select setval(pg_get_serial_sequence('{table}', '{column}'), "
                    f'coalesce((select max("{column}") from "{table}"), 1))'
                )

            cur.execute("SET session_replication_role = DEFAULT")
        pg.commit()

    log("Перенесено строк:")
    for table, count in sorted(moved.items()):
        log(f"  {table}: {count}")

    if skipped_columns:
        log("\nСтолбцы, которых нет в PostgreSQL — пропущены:")
        for name in skipped_columns:
            log(f"  {name}")

    log(f"\nСброшено счётчиков id: {len(sequences)}")
    log("\nПроверить перенос: .venv\\Scripts\\python.exe scripts\\check-local.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
