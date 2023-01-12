import asyncio
from asyncio.streams import StreamReader, StreamWriter

from structs import RequestData, Command
from config import settings
from utils import client_logger


class Client:
    def __init__(self, username: str, server_host: str = settings.HOST,
                 server_port: int = settings.PORT) -> None:
        self.username = username
        self.server_host = server_host
        self.server_port = server_port
        self.writer = None
        self.reader = None
        self.event_loop = asyncio.new_event_loop()

    def connect(self) -> None:
        """The main method of connecting to the server"""
        print(111111)
        try:
            self.event_loop.run_until_complete(self.connect_to_server())
        except ConnectionRefusedError:
            print('Server is not available!')
            client_logger.warning('Server is not available')
            return
        read_task = self.event_loop.create_task(self.read_data())
        send_task = self.event_loop.create_task(self.send_command())
        self.event_loop.run_until_complete(asyncio.wait([read_task, send_task]))

    async def connect_to_server(self) -> (StreamReader, StreamWriter):
        """Connect to the server and send notification to other users"""
        self.reader, self.writer = await asyncio.open_connection(
            self.server_host, self.server_port
        )
        client_logger.info('Connect to server')
        await self.send_hello_message()
        return self.reader, self.writer

    async def send_command(self) -> None:
        """Listen commands and execute"""
        print(
            'Welcome to chat! '
            'To display a list of available commands, type "help"'
        )
        while True:
            await asyncio.sleep(0.3)
            command = await self.event_loop.run_in_executor(
                None, lambda: input(f'{self.username}: ')
            )
            if not command.strip():
                continue
            command = command.split()
            match command[0]:
                case Command.EXIT | Command.QUIT:
                    self.writer.close()
                    break
                case Command.SEND:
                    await self.send_all(' '.join(command[1:]))
                case Command.SEND_TO:
                    await self.send_all(' '.join(command[1:]))
                case Command.STATUS:
                    await self.get_status()
                case Command.HELP:
                    self.get_help()
                case _:
                    print(f'Command "{command[0]}" is not allowed')

    async def read_data(self) -> None:
        """Receiving incoming data and printing"""
        while data := await self.reader.read(1024):
            print(f'\n{data.decode()}')

        print('Close the connection')
        client_logger.info('Close the connection')
        self.writer.close()

    async def send_all(self, message: str = '') -> None:
        """Send message to all users"""
        request_data = RequestData(
            username=self.username,
            message=message,
        )
        self.writer.write(request_data.to_string_json().encode())
        await self.writer.drain()

    async def send_hello_message(self) -> None:
        """Send notification to all users"""
        request_data = RequestData(self.username, target='hello')
        self.writer.write(request_data.to_string_json().encode())
        await self.writer.drain()

    async def send_to(self, receiver: str, message: str = '') -> None:
        """Send private message"""
        request_data = RequestData(
            username=self.username,
            target='one_to_one',
            message=message,
            receiver=receiver,
        )
        self.writer.write(request_data.to_string_json().encode())
        await self.writer.drain()

    async def get_status(self) -> None:
        """Get status information about a chat"""
        request_data = RequestData(
            username=self.username,
            target='status'
        )
        self.writer.write(request_data.to_string_json().encode())
        await self.writer.drain()

    @staticmethod
    def get_help() -> None:
        """Print help information"""
        print('status - get your username, address and users online')
        print('send <message> - send message to all')
        print('send-to <username> <message> - send private message to user')
        print('quit or exit - leave the chat')
        print('help - get get available commands')
