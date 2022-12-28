import asyncio
# import aiohttp
from asyncio.streams import StreamReader, StreamWriter

from structs import RequestData
from config import HOST


class Client:
    allow_commands = [
        'send', 'send-to', 'delay-send', 'delay-send-to', 'exit', 'quit'
    ]

    def __init__(self, nick: str, server_host=HOST[0], server_port=HOST[1]):
        self.nick_name = nick
        self.server_host = server_host
        self.server_port = server_port
        self.writer = None
        self.reader = None
        self.event_loop = asyncio.new_event_loop()

    def connect(self):
        task1 = self.event_loop.create_task(self.main())
        task2 = self.event_loop.create_task(self.send_command())
        self.event_loop.run_until_complete(asyncio.wait([task1, task2]))

    async def send_command(self):
        while True:
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

    async def main(self):
        self.reader, self.writer = await asyncio.open_connection(
            self.server_host, self.server_port
        )
        await self.send_hello_message()
        while True:
            data = await self.reader.read(1024)
            print(data.decode())
            if not data:
                break
        print('Close the connection')
        self.writer.close()

    async def send_all(self, message: str = ''):
        request_data = RequestData(
            nick_name=self.nick_name,
            message=message,
        )
        self.writer.write(request_data.to_string_json().encode())
        await self.writer.drain()

    async def send_hello_message(self):
        request_data = RequestData(self.nick_name, target='hello')
        self.writer.write(request_data.to_string_json().encode())
        await self.writer.drain()

    async def send_to(self, receiver: str, message: str = ''):
        request_data = RequestData(
            nick_name=self.nick_name,
            target='one_to_one',
            message=message,
            receiver=receiver,
        )
        self.writer.write(request_data.to_string_json().encode())
        await self.writer.drain()
