import logging
import sys
import asyncio
import json
import functools

from datetime import datetime
from pytz import timezone
from sqlite3 import connect, PARSE_DECLTYPES, PARSE_COLNAMES
from asyncio.streams import StreamReader, StreamWriter
from concurrent.futures import ThreadPoolExecutor

from config import DB_NAME, TZ, HOST


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class Server:
    def __init__(self, host=HOST[0], port=HOST[1]):
        self.host: str = host
        self.port: int = port
        self.users: dict[str, StreamWriter] = dict()
        self.db_executor = ThreadPoolExecutor(1)

    def listen(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.main())

    async def main(self):
        srv = await asyncio.start_server(
            self.client_connected, self.host, self.port)
        async with srv:
            await srv.serve_forever()

    async def client_connected(
            self, reader: StreamReader, writer: StreamWriter):
        address = writer.get_extra_info('peername')
        logger.info('Start serving %s', address)

        while True:
            data = await reader.read(1024)
            await self.process_data(data, writer)
            if not data:
                break

        logger.info('Stop serving %s', address)
        writer.close()

    async def send_to_all(self, self_writer, sender, message):
        if isinstance(message, bytes):
            message = message.decode()
        for w in self.users.values():
            if w != self_writer:
                w.write(f'{sender}: {message}\n'.encode())
                await w.drain()

    async def send_to_one(self, sender, message, receiver):
        for nick_name, w in self.users.items():
            if nick_name == receiver:
                w.write(f'{sender}: {message}\n'.encode())
                await w.drain()

    async def send_hello(self, self_writer, sender):
        for w in self.users.values():
            if w != self_writer:
                w.write(f'New guest in the chat! - {sender}\n'.encode())
                await w.drain()

    async def process_data(self, data: bytes, writer: StreamWriter):
        data: dict = json.loads(data.decode())
        target = data['target']
        user = data['nick_name']

        if not target == 'hello':
            await self.store_message(data)

        if target == 'hello':
            if user in self.users:
                await self.send_available_messages(writer)
            else:
                await self.send_last_messages(writer)
            self.users[user] = writer
            await self.send_hello(writer, data['nick_name'])
        elif data['target'] == 'all':
            await self.send_to_all(writer, data['nick_name'], data['message'])
        elif data['target'] == 'one_to_one':
            await self.send_to_one(
                user, data['message'], data['receiver']
            )

    async def send_last_messages(self, writer: StreamWriter):
        pass

    async def send_available_messages(self, writer: StreamWriter):
        pass

    async def store_message(self, data: dict):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.db_executor,
            functools.partial(
                self.__create_record_in_db,
                message=data['message'],
                sender=data['nick_name'],
                receiver=data['receiver']
            )
        )

    @staticmethod
    def __create_record_in_db(message, sender, receiver):
        connection = None
        try:
            connection = connect(
                DB_NAME, detect_types=PARSE_DECLTYPES | PARSE_COLNAMES
            )
            cursor = connection.cursor()

            store_message_query = '''
                INSERT INTO main.messages(
                    message, sender, receiver, send_date)
                    VALUES (?, ?, ?, ?);
            '''
            cursor.execute(
                store_message_query,
                (
                    message, sender, receiver,
                    datetime.now(timezone(TZ))
                )
            )
            connection.commit()
        except Exception as er:
            logger.error(f'DB error - {er}')
        finally:
            if connection:
                connection.close()
