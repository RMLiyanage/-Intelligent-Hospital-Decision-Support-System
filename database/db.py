

import logging
from typing import Any, Optional, Tuple, Union

import pymysql
import pymysql.cursors
from flask import current_app, g

logger = logging.getLogger(__name__)


def get_db() -> pymysql.connections.Connection:
    if 'db' not in g:
        g.db = pymysql.connect(
            host=current_app.config['DB_HOST'],
            port=current_app.config['DB_PORT'],
            user=current_app.config['DB_USER'],
            password=current_app.config['DB_PASSWORD'],
            database=current_app.config['DB_NAME'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            connect_timeout=10,
        )
    return g.db


def close_db(e: Optional[Exception] = None) -> None:
 
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass


def query_db(
    sql: str,
    args: Union[Tuple, list] = (),
    one: bool = False,
) -> Any:

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(sql, args)
            res = cursor.fetchone() if one else cursor.fetchall()
            db.commit()
            return res
    except pymysql.Error as e:
        logger.error("DB query error: %s | SQL: %s | Args: %s", e, sql, args)
        raise


def execute_db(
    sql: str,
    args: Union[Tuple, list] = (),
    commit: bool = True,
) -> int:
 
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(sql, args)
            if commit:
                db.commit()
            return cursor.lastrowid
    except pymysql.Error as e:
        db.rollback()
        logger.error("DB execute error: %s | SQL: %s | Args: %s", e, sql, args)
        raise


def execute_many(
    sql: str,
    args_list: list,
    commit: bool = True,
) -> int:

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.executemany(sql, args_list)
            if commit:
                db.commit()
            return cursor.rowcount
    except pymysql.Error as e:
        db.rollback()
        logger.error("DB executemany error: %s | SQL: %s", e, sql)
        raise


def init_app(app) -> None:

    app.teardown_appcontext(close_db)
