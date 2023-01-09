import time
import aiounittest
import asyncio
import unittest
import os
import nest_asyncio
import _thread

from asyncio.streams import StreamReader, StreamWriter

from test_db import create_test_db
from client import Client
from server import Server


nest_asyncio.apply()


class ChatTest(aiounittest.AsyncTestCase):
    test_db = 'test_db.db'

    @classmethod
    def setUpClass(cls) -> None:
        create_test_db(cls.test_db)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.remove(cls.test_db)
        except FileNotFoundError:
            pass

    async def test_client(self):
        # start server
        server = Server(db_name=self.test_db)
        _thread.start_new_thread(server.listen, ())
        time.sleep(1)

        client1 = Client('test_user_1')
        reader, writer = await client1.connect_to_server()
        self.assertIsInstance(reader, StreamReader)
        self.assertIsInstance(writer, StreamWriter)

        client2 = Client('test_user_2')
        _thread.start_new_thread(client2.connect, ())
        time.sleep(1)
        self.assertIsInstance(client2.reader, StreamReader)
        self.assertIsInstance(client2.writer, StreamWriter)

        _thread.start_new_thread(client1.connect, ())
        time.sleep(1)
        await client1.send_all('test message')


if __name__ == '__main__':
    unittest.main()
