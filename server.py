import logging
import sys
import asyncio
from asyncio.streams import StreamReader, StreamWriter


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class Server:
    def __init__(self, host="127.0.0.1", port=8000):
        self.host: str = host
        self.port: int = port
        self.writers: list[StreamWriter] = []

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
        self.writers.append(writer)
        await self.send_message(writer, address, 'New guest in chat!')

        while True:
            data = await reader.read(1024)
            if not data:
                break
            await self.send_message(writer, address, data)

        logger.info('Stop serving %s', address)
        try:
            self.writers.remove(writer)
        except ValueError:
            pass
        writer.close()

    async def send_message(self, self_writer, addr, message):
        if isinstance(message, bytes):
            message = message.decode()
        for w in self.writers:
            if w != self_writer:
                w.write(f"{addr}: {message}\n".encode())
                await w.drain()
