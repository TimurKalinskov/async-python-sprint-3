import asyncio
from asyncio.streams import StreamReader, StreamWriter

from structs import RequestData
from config import HOST


class Client:
    allow_commands = [
        'send', 'send-to', 'status', 'exit', 'quit', 'help'
    ]

    def __init__(self, username: str, server_host=HOST[0], server_port=HOST[1]):
        self.username = username
        self.server_host = server_host
        self.server_port = server_port
        self.writer = None
        self.reader = None
        self.event_loop = asyncio.new_event_loop()

    def connect(self):
        try:
            self.event_loop.run_until_complete(self.connect_to_server())
        except ConnectionRefusedError:
            print('Server is not available!')
            return
        read_task = self.event_loop.create_task(self.read_data())
        send_task = self.event_loop.create_task(self.send_command())
        self.event_loop.run_until_complete(asyncio.wait([read_task, send_task]))

    async def connect_to_server(self):
        self.reader, self.writer = await asyncio.open_connection(
            self.server_host, self.server_port
        )

    async def send_command(self):
        print(
            'Welcome to chat! '
            'To display a list of available commands, type "help"'
        )
        while True:
            await asyncio.sleep(0.3)
            command = await self.event_loop.run_in_executor(
                None, lambda: input('Enter command: ')
            )
            if not command:
                continue
            command = command.split()
            if not command[0] in self.allow_commands:
                print(f'Command "{command[0]}" is not allowed')
                continue
            elif command[0] in ['exit', 'quit']:
                self.writer.close()
                break
            elif command[0] == 'send':
                await self.send_all(' '.join(command[1:]))
            elif command[0] == 'send-to':
                await self.send_to(command[1], ' '.join(command[2:]))
            elif command[0] == 'status':
                await self.get_status()
            elif command[0] == 'help':
                self.get_help()

    async def read_data(self):
        await self.send_hello_message()
        while True:
            data = await self.reader.read(1024)
            print(f'\n{data.decode()}')
            if not data:
                break
        print('Close the connection')
        self.writer.close()

    async def send_all(self, message: str = ''):
        request_data = RequestData(
            username=self.username,
            message=message,
        )
        self.writer.write(request_data.to_string_json().encode())
        await self.writer.drain()

    async def send_hello_message(self):
        request_data = RequestData(self.username, target='hello')
        self.writer.write(request_data.to_string_json().encode())
        await self.writer.drain()

    async def send_to(self, receiver: str, message: str = ''):
        request_data = RequestData(
            username=self.username,
            target='one_to_one',
            message=message,
            receiver=receiver,
        )
        self.writer.write(request_data.to_string_json().encode())
        await self.writer.drain()

    async def get_status(self):
        request_data = RequestData(
            username=self.username,
            target='status'
        )
        self.writer.write(request_data.to_string_json().encode())
        await self.writer.drain()

    @staticmethod
    def get_help():
        print('status - get your username, address and users online')
        print('send <message> - send message to all')
        print('send-to <username> <message> - send private message to user')
        print('quit or exit - leave the chat')
        print('help - get get available commands')
