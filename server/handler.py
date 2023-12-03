import asyncio

from aioquic import __version__
from aioquic.asyncio import QuicConnectionProtocol
from aioquic.h3.connection import H3Connection, H3Event, DataReceived, HeadersReceived, H3_ALPN, DatagramReceived, WebTransportStreamDataReceived
from aioquic.h3.exceptions import NoAvailablePushIDError
from aioquic.quic.connection import QuicConnection
from aioquic.quic.events import QuicEvent, ProtocolNegotiated, StreamDataReceived
from typing import Dict, Callable, cast, Optional, Union
from email.utils import formatdate
from time import time
from collections import deque

from application.app import app
from .type.message import WebTransprotSendMessage, WebTransportReceiveMessage

SERVER_NAME = 'webobs.aioquic/' + __version__


class WebTransportHandler:
    def __init__(self,
                 connection: H3Connection,
                 scope: Dict,
                 stream_id: int,
                 transmit: Callable[[], None]) -> None:
        self.connection = connection
        self.scope = scope
        self.stream_id = stream_id
        self.transmit = transmit

        self.message_queue = asyncio.Queue()
        self.http_event_queue = deque()

        self.accepted = False
        self.closed = False

    def http_event_handler(self, event: H3Event) -> None:
        if not self.closed:
            if self.accepted:
                if isinstance(event, DatagramReceived):
                    self.message_queue.put_nowait({
                        'type': WebTransportReceiveMessage.Datagram,
                        'data': event.data
                    })
                elif isinstance(event, WebTransportStreamDataReceived):
                    self.message_queue.put_nowait({
                        'type': WebTransportReceiveMessage.Stream,
                        'stream': event.stream_id,
                        'data': event.data
                    })
            else:
                self.http_event_queue.append(event)

    async def receive(self) -> Dict:
        return await self.message_queue.get()

    async def send(self, message: Dict) -> None:
        end_stream = False

        # establish webtransport connection
        if message['type'] == WebTransprotSendMessage.Accept:
            self.accepted = True
            headers = [
                (b':status', b'200'),
                (b'server', SERVER_NAME.encode()),
                (b'date', formatdate(time(), usegmt=True).encode()),
                (b'sec-webtransport-http3-draft', b'draft02')
            ]
            self.connection.send_headers(stream_id=self.stream_id, headers=headers)

            while self.http_event_queue:
                self.http_event_handler(self.http_event_queue.popleft())

        # close webtransport connection
        elif message['type'] == WebTransprotSendMessage.Close:
            if not self.accepted:
                self.connection.send_headers(stream_id=self.stream_id, headers=[(b':status', b'403')])
            end_stream = True

        # send webtransport stream
        elif message['type'] == WebTransprotSendMessage.Stream:
            self.connection.quic.send_stream_data(stream_id=message['stream'], data=message['data'])

        if end_stream:
            self.closed = True

        self.transmit()

    async def run_asgi(self, asgiApp) -> None:
        await asgiApp(self.scope, self.receive, self.send)
