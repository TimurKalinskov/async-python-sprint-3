import asyncio
# import aiohttp
from asyncio.streams import StreamReader, StreamWriter


class Client:
    allow_commands = [
        'send', 'send-to', 'delay-send', 'delay-send-to', 'exit', 'quit'
    ]
    def __init__(self, nick: str, server_host='127.0.0.1', server_port=8000):
        self.nick = nick
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
            if command[0] == 'send':
                await self.send_all(''.join(command[1:]))
            elif command[0] == 'send-to':
                await self.send_all(''.join(command[1:]))
            elif command[0] in ['exit', 'quit']:
                self.writer.close()
                break

    def _loop_in_thread(self, loop):
        asyncio.set_event_loop(loop)
        asyncio.get_event_loop().create_task(self.main())
        loop.run_forever()

    async def main(self):
        self.reader, self.writer = await asyncio.open_connection(
            self.server_host, self.server_port
        )
        while True:
            data = await self.reader.read(1024)
            print(data.decode())
            if not data:
                break
        print('Close the connection')
        self.writer.close()

    async def send_all(self, message: str = ''):
        self.writer.write(f'{self.nick}_*_{message}'.encode())
        await self.writer.drain()


if __name__ == '__main__':
    client = Client('test')
    client.connect()
