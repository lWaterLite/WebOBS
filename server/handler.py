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
                (b'sec-webtransport-http3-draft', b'draft03')
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


class HttpHandler:
    def __init__(self,
                 authority: bytes,
                 connection: H3Connection,
                 protocol: QuicConnectionProtocol,
                 scope: Dict,
                 stream_id: int,
                 stream_ended: bool,
                 transmit: Callable[[], None]
                 ) -> None:

        self.stream_id = stream_id
        self.authority = authority
        self.connection = connection
        self.protocol = protocol
        self.scope = scope

        self.transmit = transmit
        self.message_queue = asyncio.Queue()

        if stream_ended:
            self.message_queue.put_nowait({})

    def http_event_received(self, event: H3Event) -> None:
        if isinstance(event, DataReceived):
            self.message_queue.put_nowait({
                'type': 'http.request',
                'body': event.data,
                'more_body': not event.stream_ended
            })
        elif isinstance(event, HeadersReceived) and event.stream_ended:
            self.message_queue.put_nowait({
                'type': 'http.request',
                'body': b'',
                'more_body': False
            })

    async def receive(self) -> Dict:
        return await self.message_queue.get()

    async def send(self, message: Dict) -> None:
        if message['type'] == 'http.response.start':
            self.connection.send_headers(
                stream_id=self.stream_id,
                headers=[
                            (b':status', str(message['status']).encode()),
                            (b'server', SERVER_NAME.encode()),
                            (b'data', formatdate(time(), usegmt=True).encode())
                        ] + [(keyword, value) for keyword, value in message['headers']]
            )
        elif message['type'] == 'http.response.body':
            self.connection.send_data(
                stream_id=self.stream_id,
                data=message.get('body', b''),
                end_stream=not message.get('more_body', False)
            )
        elif message['type'] == 'http.response.push' and isinstance(self.connection, H3Connection):
            request_headers = [
                                  (b':method', b'GET'),
                                  (b':scheme', b'https'),
                                  (b':authority', self.authority),
                                  (b':path', message['path'].encode())
                              ] + [(keyword, value) for keyword, value in message['headers']]

            try:
                self.connection.send_push_promise(stream_id=self.stream_id, headers=request_headers)
            except NoAvailablePushIDError:
                return

            self.transmit()

    async def run_asgi(self, asgiApp) -> None:
        await asgiApp(self.scope, self.receive, self.send)
