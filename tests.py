import time
import aiounittest
import unittest
import os
import nest_asyncio
import _thread

from contextlib import contextmanager
from sqlite3 import connect, PARSE_DECLTYPES, PARSE_COLNAMES
from asyncio.streams import StreamReader, StreamWriter

from test_db import create_test_db
from client import Client
from server import Server
from config import LIMIT_MESSAGES


nest_asyncio.apply()
test_db_name = 'test_db.db'


@contextmanager
def get_cursor():
    """Create cursor for connection to SQLite db"""
    connection = connect(
        test_db_name, detect_types=PARSE_DECLTYPES | PARSE_COLNAMES
    )
    cursor = connection.cursor()
    yield cursor

    if connection:
        connection.close()


class ChatTest(aiounittest.AsyncTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        create_test_db(test_db_name)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.remove(test_db_name)
        except FileNotFoundError:
            pass

    async def test_messaging(self) -> None:
        # start server
        server = Server(db_name=test_db_name)
        _thread.start_new_thread(server.listen, ())
        time.sleep(1)

        get_users_query = 'SELECT * FROM main.registrations'
        get_messages_query = 'SELECT * FROM main.messages'

        # make sure the database is empty
        with get_cursor() as cursor:
            users = cursor.execute(get_users_query).fetchall()
            self.assertEqual(len(users), 0)
            messages = cursor.execute(get_messages_query).fetchall()
            self.assertEqual(len(messages), 0)

        # connect first client
        client1 = Client('test_user_1')
        reader, writer = await client1.connect_to_server()
        self.assertIsInstance(reader, StreamReader)
        self.assertIsInstance(writer, StreamWriter)

        # connect second client
        client2 = Client('test_user_2')
        reader, writer = await client2.connect_to_server()
        self.assertIsInstance(reader, StreamReader)
        self.assertIsInstance(writer, StreamWriter)

        # little time to save the data to the database
        time.sleep(0.1)
        with get_cursor() as cursor:
            users = cursor.execute(get_users_query).fetchall()
            # testing storing new users
            self.assertEqual(len(users), 2)
            self.assertEqual(users[0][1], 'test_user_1')
            self.assertEqual(users[0][3], 0)

        # testing sending messages to all
        await client1.send_all('test message')
        time.sleep(0.1)

        with get_cursor() as cursor:
            messages = cursor.execute(get_messages_query).fetchall()
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0][1], 'test_user_1')
            self.assertEqual(messages[0][2], 'all')
            self.assertEqual(messages[0][3], 'test message')
            users = cursor.execute(get_users_query).fetchall()
            self.assertEqual(users[0][3], 1)

        # testing sending private messages
        await client2.send_to('test_user_1', 'test private message')
        time.sleep(0.5)
        with get_cursor() as cursor:
            messages = cursor.execute(get_messages_query).fetchall()
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[1][1], 'test_user_2')
            self.assertEqual(messages[1][2], 'test_user_1')
            self.assertEqual(messages[1][3], 'test private message')
            users = cursor.execute(get_users_query).fetchall()
            self.assertEqual(users[1][3], 0)

        # testing message limit
        for m in range(LIMIT_MESSAGES + 2):
            await client2.send_all('limited message')
            time.sleep(0.2)

        with get_cursor() as cursor:
            get_messages_query = 'SELECT * FROM main.messages ' \
                                 'WHERE message = "limited message"'
            messages = cursor.execute(get_messages_query).fetchall()
            self.assertEqual(len(messages), LIMIT_MESSAGES)


if __name__ == '__main__':
    unittest.main()
