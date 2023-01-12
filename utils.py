import logging

from contextlib import contextmanager
from sqlite3 import connect, PARSE_DECLTYPES, PARSE_COLNAMES, DatabaseError

from config import settings


def config_logger(
        name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
    formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s')
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


server_logger = config_logger('server_logger', 'server.log')
client_logger = config_logger('client_logger', 'client.log')


@contextmanager
def get_cursor(db_name: str = settings.DB_NAME):
    """Create cursor for connection to SQLite db"""
    connection = None
    try:
        connection = connect(
            db_name, detect_types=PARSE_DECLTYPES | PARSE_COLNAMES
        )
        cursor = connection.cursor()
        yield cursor
    except DatabaseError as er:
        server_logger.error(f'DB connection error: {er}')
    finally:
        if connection:
            connection.close()
