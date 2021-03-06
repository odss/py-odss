import asyncio
import sys
import threading


class StandardStreamReaderProtocol(asyncio.StreamReaderProtocol):
    def connection_made(self, transport):
        # The connection is already made
        if self._stream_reader._transport is not None:
            return
        # Make the connection
        super().connection_made(transport)

    # def connection_lost(self, exc):
    #     state = self.__dict__.copy()
    #     super().connection_lost(exc)
    #     self.__dict__.update(state)


class StandardStreamWriter(asyncio.StreamWriter):
    def write(self, data):
        if isinstance(data, str):
            data = data.encode()
        super().write(data)


async def open_standard_pipe_connection(pipe_in, pipe_out, pipe_err, *, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    # Reader
    in_reader = asyncio.StreamReader(loop=loop)
    protocol = StandardStreamReaderProtocol(in_reader, loop=loop)
    await loop.connect_read_pipe(lambda: protocol, pipe_in)

    # Out writer
    out_transport, _ = await loop.connect_write_pipe(lambda: protocol, pipe_out)
    out_writer = StandardStreamWriter(out_transport, protocol, in_reader, loop)

    # Err writer
    # err_transport, _ = await loop.connect_write_pipe(lambda: protocol, pipe_err)
    # err_writer = asyncio.StreamWriter(err_transport, protocol, in_reader, loop)

    return in_reader, out_writer, None


async def create_standard_streams(stdin, stdout, stderr, *, loop=None):
    return await open_standard_pipe_connection(stdin, stdout, stderr, loop=loop)


async def get_standard_streams(*, use_stderr=False, loop=None):
    in_reader, out_writer, err_writer = await open_standard_pipe_connection(
        sys.stdin, sys.stdout, sys.stderr, loop=loop
    )
    return in_reader, err_writer if use_stderr else out_writer


class AStream:
    def __init__(self, loop=None):
        self.streams = None
        self.loop = loop

    async def get_streams(self):
        if self.streams is None:
            self.streams = await get_standard_streams(loop=self.loop)
        return self.streams

    async def input(self, prompt="", *, use_stderr=False, loop=None):
        reader, writer = await self.get_streams()
        writer.write(prompt.encode())
        await writer.drain()

        data = await reader.readline()
        data = data.decode()
        if not data.endswith("\n"):
            raise EOFError

        return data.rstrip("\n")

    async def write(self, data):
        print(f"write: {threading.current_thread().name}")

        reader, writer = await self.get_streams()
        writer.write(data)
