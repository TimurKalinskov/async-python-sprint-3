import time

import aiounittest
import asyncio
import unittest
import os

from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from test_db import create_test_db
from client import Client
from server import Server


class ChatTest(aiounittest.AsyncTestCase):
    test_db = 'test_db.db'

    @classmethod
    def setUpClass(cls) -> None:
        create_test_db(cls.test_db)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.remove(cls.test_db)
        except FileNotFoundError as er:
            pass

    async def test_server(self):
        server = Server(db_name=self.test_db)
        client = Client('test_user')
        thread_server = Thread(target=server.listen)
        thread_client = Thread(target=client.connect)
        thread_server.run()
        time.sleep(1)
        thread_client.run()

        time.sleep(5)


if __name__ == '__main__':
    unittest.main()
