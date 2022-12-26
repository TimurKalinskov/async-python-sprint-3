import asyncio
# import aiohttp
from asyncio.streams import StreamReader, StreamWriter
from threading import Thread


class Client:
    def __init__(self, nick: str, server_host='127.0.0.1', server_port=8000):
        self.nick = nick
        self.server_host = server_host
        self.server_port = server_port
        self.writer = None
        self.reader = None
        self.event_loop = asyncio.new_event_loop()

    def connect(self):
        Thread(
            target=self._loop_in_thread, args=(self.event_loop,), daemon=True
        ).start()

    def send_message(self, message: str = ''):
        asyncio.run_coroutine_threadsafe(self.send(message), self.event_loop)

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

    async def send(self, message: str = ''):
        self.writer.write(f'{self.nick} * {message}'.encode())
        await self.writer.drain()


if __name__ == '__main__':
    client = Client('test')
    client.connect()
    # client.send_message('Hello')



