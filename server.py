import asyncio
import aiosqlite
import json

from datetime import datetime, timedelta
from pytz import timezone
from asyncio.streams import StreamReader, StreamWriter
from concurrent.futures import ThreadPoolExecutor

from utils import server_logger
from config import settings
from structs import Target
from sql_queries import (
    get_message_query, store_message_query, store_user_query, get_user_query,
    delete_message_query, append_count_query, reset_limit_query
)


class Server:
    def __init__(self, host: str = settings.HOST, port: int = settings.PORT,
                 db_name: str = settings.DB_NAME) -> None:
        self.host: str = host
        self.port: int = port
        self.db_name = db_name
        self.users: dict[str, list[StreamWriter]] = dict()
        self.db_executor = ThreadPoolExecutor(1)
        self.online_users: list = list()

    def listen(self) -> None:
        """Start server and run db tasks"""
        print(f'Start server {self.host}:{self.port}')
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        main_task = loop.create_task(self.main())
        delete_messages_task = loop.create_task(self.delete_old_messages())
        reset_limit_task = loop.create_task(self.reset_limit_messages())
        loop.run_until_complete(asyncio.wait([
            main_task, delete_messages_task, reset_limit_task
        ]))

    async def main(self) -> None:
        """Start server"""
        srv = await asyncio.start_server(
            self.client_connected, self.host, self.port)
        async with srv:
            await srv.serve_forever()

    async def client_connected(
            self, reader: StreamReader, writer: StreamWriter) -> None:
        """Start listening to the connected client"""
        address = writer.get_extra_info('peername')
        server_logger.info('Start serving %s', address)

        while data := await reader.read(1024):
            await self.process_data(data, writer, address)

        server_logger.info('Stop serving %s', address)
        await self.disconnect_user(writer)

    async def disconnect_user(self, writer: StreamWriter) -> None:
        """Close client StreamWriter and send notifications to other clients"""
        offline_flag = False
        username = None
        for user, w_list in self.users.items():
            if writer in w_list:
                w_list.remove(writer)
                if not w_list:
                    offline_flag = True
                    username = user
                    try:
                        self.online_users.remove(user)
                        server_logger.info(f'User {user} has left the chat')
                    except ValueError as er:
                        server_logger.error(
                            f'Unable to remove user {user} from the list: {er}'
                        )
                    break
        writer.close()
        if offline_flag:
            for w_list in self.users.values():
                for w in w_list:
                    w.write(
                        f'{username} has left the chat'.encode()
                    )
                    await w.drain()

    async def send_to_all(
            self, self_writer: StreamWriter, sender: str, message: bytes | str
    ) -> None:
        """Send message to all clients"""
        if isinstance(message, bytes):
            message = message.decode()
        for w_list in self.users.values():
            for w in w_list:
                if w != self_writer:
                    w.write(
                        f'{datetime.now(timezone(settings.TZ))} '
                        f'{sender} to all: '
                        f'{message}'.encode()
                    )
                    await w.drain()

    async def send_to_one(
            self, self_writer: StreamWriter, sender: str,
            message: str, receiver: str
    ) -> None:
        """Send private message"""
        for username, w_list in self.users.items():
            if username in (receiver, sender):
                for w in w_list:
                    if w != self_writer:
                        w.write(
                            f'{datetime.now(timezone(settings.TZ))} '
                            f'{sender} to {receiver}: '
                            f'{message}'.encode()
                        )
                        await w.drain()

    async def send_hello(self, sender: str) -> None:
        """Send a welcome message"""
        if sender in self.online_users:
            return
        self.online_users.append(sender)
        for user, w_list in self.users.items():
            if user != sender:
                for w in w_list:
                    w.write(f'New guest in the chat! - {sender}'.encode())
                    await w.drain()

    async def process_data(
            self, data: bytes, writer: StreamWriter, address: tuple[str, int]
    ) -> None:
        """Process the data received from the client"""
        data: dict = json.loads(data.decode())
        target = data['target']
        user = data['username']
        count_messages = 0

        exist_user = await self.get_user(user)
        if not exist_user:
            await self.reg_user(user)
            reg_date = datetime.now(timezone(settings.TZ))
        else:
            reg_date = exist_user[1]
            count_messages = exist_user[2]

        match target:
            case Target.HELLO:
                if user not in self.users:
                    self.users[user] = [writer]
                else:
                    self.users[user].append(writer)
                await self.send_available_messages(user, writer, reg_date)
                await self.send_hello(user)
            case Target.ALL:
                if count_messages >= settings.LIMIT_MESSAGES:
                    await self.send_limit_warning(writer)
                else:
                    await self.store_message(data)
                    await self.send_to_all(writer, user, data['message'])
                    await self.append_count_message(user, count_messages)
            case Target.ONE_TO_ONE:
                await self.store_message(data)
                await self.send_to_one(
                    writer, user, data['message'], data['receiver']
                )
            case Target.STATUS:
                await self.send_status(writer, user, address)

    @staticmethod
    async def send_available_messages(
            user: str, writer: StreamWriter, reg_date: datetime) -> None:
        """Get and send messages available to the client"""
        messages = []

        try:
            async with aiosqlite.connect(settings.DB_NAME) as db:
                async with db.execute(
                        get_message_query,
                        (user, reg_date, user, user, reg_date)
                ) as cursor:
                    messages = await cursor.fetchall()
        except aiosqlite.DatabaseError as er:
            server_logger.error(f'DB error - get messages: {er}')

        for m in messages:
            message = f'{m[0]} {m[1]} to {m[2]}: {m[3]}\n'.encode()
            writer.write(message)
            await writer.drain()

    @staticmethod
    async def store_message(data: dict) -> None:
        """Store message in DB"""
        receiver = data['receiver'] or 'all'
        try:
            async with aiosqlite.connect(settings.DB_NAME) as db:
                await db.execute(
                    store_message_query,
                    (
                        data['message'], data['username'], receiver,
                        datetime.now(timezone(settings.TZ))
                    )
                )
                await db.commit()
        except aiosqlite.DatabaseError as er:
            server_logger.error(f'DB error - record message: {er}')

    @staticmethod
    async def reg_user(username: str) -> None:
        """Register a user"""
        try:
            async with aiosqlite.connect(settings.DB_NAME) as db:
                await db.execute(
                    store_user_query,
                    (username, datetime.now(timezone(settings.TZ)))
                )
                await db.commit()
                server_logger.info(f'Create new user in DB - {username}')
        except aiosqlite.DatabaseError as er:
            server_logger.error(f'DB error - registration: {er}')

    @staticmethod
    async def get_user(username: str) -> tuple[str]:
        """Get user from DB"""
        user = tuple()
        try:
            async with aiosqlite.connect(settings.DB_NAME) as db:
                async with db.execute(get_user_query, (username,)) as cursor:
                    user = await cursor.fetchone()
        except aiosqlite.DatabaseError as er:
            server_logger.error(f'DB error - get user: {er}')
        return user

    @staticmethod
    async def delete_old_messages() -> None:
        """Delete old messages"""
        deadline_date = datetime.now(timezone(settings.TZ)) - timedelta(
            minutes=settings.LIFETIME_MESSAGES)

        while True:
            try:
                async with aiosqlite.connect(settings.DB_NAME) as db:
                    await db.execute(delete_message_query, (deadline_date,))
                    await db.commit()
                    if db.total_changes != 0:
                        server_logger.info('Deleting old messages')
            except aiosqlite.DatabaseError as er:
                server_logger.error(f'DB error - deleting messages: {er}')
            await asyncio.sleep(60)

    @staticmethod
    async def append_count_message(username: str, count_messages: int) -> None:
        """Add to message counter for the user"""
        count_messages += 1
        try:
            async with aiosqlite.connect(settings.DB_NAME) as db:
                await db.execute(append_count_query, (count_messages, username))
                await db.commit()
        except aiosqlite.DatabaseError as er:
            server_logger.error(f'DB error - updating count messages: {er}')

    @staticmethod
    async def reset_limit_messages() -> None:
        """Reset the message counter for the user"""
        while True:
            try:
                async with aiosqlite.connect(settings.DB_NAME) as db:
                    await db.execute(
                        reset_limit_query
                    )
                    await db.commit()
                    server_logger.info('Reset message counter')
            except aiosqlite.DatabaseError as er:
                server_logger.error(f'DB error - reset limits: {er}')
            await asyncio.sleep(60 * settings.UPDATE_PERIOD)

    async def send_status(self, writer: StreamWriter, username: str,
                          address: tuple[str, int]) -> None:
        """Send status information about the chat"""
        message = 'Your username - "{}"\nYour address - {}\nYour port - {}\n' \
                  'Users online - {}:\n{}'\
            .format(username, address[0], address[1], len(self.online_users),
                    ', '.join(self.online_users))
        writer.write(message.encode())
        await writer.drain()

    @staticmethod
    async def send_limit_warning(writer: StreamWriter):
        """Send message counter alert"""
        writer.write('You have reached the limit for sending messages '
                     'to the general chat'.encode())
        await writer.drain()


if __name__ == '__main__':
    server = Server()
    try:
        server.listen()
    except KeyboardInterrupt:
        print(f'\nStopping server {server.host}:{server.port}')
