import sqlite3
from config import DB_NAME


sqlite_connection = None
try:
    sqlite_connection = sqlite3.connect(DB_NAME)
    sqlite_create_table_query = '''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL DEFAULT 'all',
            message TEXT,
            send_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    '''

    cursor = sqlite_connection.cursor()
    print('База данных подключена к SQLite')
    cursor.execute(sqlite_create_table_query)
    sqlite_connection.commit()
    print('Таблица "messages" создана')

    sqlite_create_table_query = '''
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nick_name TEXT NOT NULL,
            reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    '''

    cursor = sqlite_connection.cursor()
    print('База данных подключена к SQLite')
    cursor.execute(sqlite_create_table_query)
    sqlite_connection.commit()
    print('Таблица "messages" создана')

    cursor.close()

except sqlite3.Error as error:
    print('Ошибка при подключении к sqlite', error)
finally:
    if sqlite_connection:
        sqlite_connection.close()
        print('Соединение с SQLite закрыто')
