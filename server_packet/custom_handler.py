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

SERVER_NAME = 'webobs.aioquic/' + __version__


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
        self.authority = authority
        self.connection = connection
        self.protocol = protocol
        self.scope = scope
        self.stream_id = stream_id
        self.transmit = transmit
        self.queue = asyncio.Queue()

        if stream_ended:
            self.queue.put_nowait({'type': 'http.request'})

    def http_event_received(self, event: H3Event) -> None:
        if isinstance(event, DataReceived):
            self.queue.put_nowait({
                'type': 'http.request',
                'body': event.data,
                'more_body': not event.stream_ended
            })
        elif isinstance(event, HeadersReceived) and event.stream_ended:
            self.queue.put_nowait({
                'type': 'http.request',
                'body': b'',
                'more_body': False
            })

    async def receive(self) -> Dict:
        return await self.queue.get()

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
                push_stream_id = self.connection.send_push_promise(stream_id=self.stream_id, headers=request_headers)
            except NoAvailablePushIDError:
                return

            cast(HttpServerProtocol, self.protocol).http_event_received(
                HeadersReceived(headers=request_headers, stream_id=push_stream_id, stream_ended=True)
            )
            self.transmit()

    async def run_asgi(self, app) -> None:
        await app(self.scope, self.receive, self.send)


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
        self.queue = asyncio.Queue()
        self.http_event_queue = deque()
        self.accepted = False
        self.closed = False

    def http_event_received(self, event: H3Event) -> None:
        if not self.closed:
            if self.accepted:
                if isinstance(event, DatagramReceived):
                    self.queue.put_nowait({
                        'type': 'webtransport.datagram.receive',
                        'data': event.data
                    })
                elif isinstance(event, WebTransportStreamDataReceived):
                    self.queue.put_nowait({
                        'type': 'webtransport.stream.receive',
                        'stream': event.stream_id,
                        'data': event.data
                    })
            else:
                self.http_event_queue.append(event)

    async def receive(self) -> Dict:
        return await self.queue.get()

    async def send(self, message: Dict) -> None:
        data = b''
        end_stream = False

        if message['type'] == 'webtransport.accept':
            self.accepted = True
            headers = [
                (b':status', b'200'),
                (b'server', SERVER_NAME.encode()),
                (b'date', formatdate(time(), usegmt=True).encode()),
                (b'sec-webtransport-http3-draft', b'draft02')
            ]
            self.connection.send_headers(stream_id=self.stream_id, headers=headers)
            while self.http_event_queue:
                self.http_event_received(self.http_event_queue.popleft())
        elif message['type'] == 'webtransport.close':
            if not self.accepted:
                self.connection.send_headers(stream_id=self.stream_id, headers=[(b':status', b'403')])
            end_stream = True
        elif message['type'] == 'webtransport.datagram.send':
            self.connection.send_datagram(flow_id=self.stream_id, data=message['data'])
        elif message['type'] == 'webtransport.stream.send':
            self.connection._quic.send_stream_data(stream_id=message['stream'], data=message['data'])

        if data or end_stream:
            self.connection.send_data(stream_id=self.stream_id, data=data, end_stream=end_stream)

        if end_stream:
            self.closed = True

        self.transmit()

    async def run_asgi(self, app) -> None:
        self.queue.put_nowait({'type': 'webtransport.connect'})

        try:
            await app(self.scope, self.receive, self.send)
        except Exception as e:
            print(e)
            if not self.closed:
                await self.send({'type': 'webtransport.close'})
        # finally:
        #     if not self.closed:
        #         await self.send({'type': 'webtransport.close'})


BaseHandler = Union[HttpHandler, WebTransportHandler]


class HttpServerProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._handlers: Dict[int, BaseHandler] = {}
        self._http: Optional[H3Connection] = None

    def quic_event_received(self, event: QuicEvent) -> None:
        if isinstance(event, ProtocolNegotiated):
            if event.alpn_protocol in H3_ALPN:
                self._http = H3Connection(self._quic, enable_webtransport=True)

        if self._http is not None:
            http_events = self._http.handle_event(event)     # Transform QuicEvent to H3Event
            for http_event in http_events:
                self.http_event_received(http_event)

    def http_event_received(self, event: H3Event):
        if isinstance(event, HeadersReceived) and event.stream_id not in self._handlers:
            authority = None
            headers = []
            http_version = '3'
            raw_path = b''
            method = ''
            protocol = None
            for header, value in event.headers:
                if header == b':authority':
                    authority = value
                elif header == b':method':
                    method = value.decode()
                elif header == b':path':
                    raw_path = value
                elif header == b':protocol':
                    protocol = value.decode()
                elif header and not header.startswith(b':'):
                    headers.append((header, value))

            if b'?' in raw_path:
                path, query_string = raw_path.split(b'?', maxsplit=1)
            else:
                path, query_string = raw_path, b''
            path = path.decode()
            print(f'HTTP request {method} {path}')

            client_addr = self._http._quic._network_paths[0].addr
            client = (client_addr[0], client_addr[1])

            handler: BaseHandler
            scope: Dict
            if method == 'CONNECT' and protocol == 'websocket':
                # TODO WebSocket
                return
            elif method == 'CONNECT' and protocol == 'webtransport':
                # TODO WebTransport
                scope = {
                    'client': client,
                    'headers': headers,
                    'http_version': http_version,
                    'method': method,
                    'path': path,
                    'query_string': query_string,
                    'raw_path': raw_path,
                    'root_path': '',
                    'scheme': 'https',
                    'type': 'webtransport'
                }
                handler = WebTransportHandler(
                    connection=self._http,
                    scope=scope,
                    stream_id=event.stream_id,
                    transmit=self.transmit
                )
            else:
                extensions: Dict[str, Dict] = {}
                if isinstance(self._http, H3Connection):
                    extensions['http.response.push'] = {}

                scope = {
                    'client': client,
                    'extensions': extensions,
                    'headers': headers,
                    'http_version': http_version,
                    'method': method,
                    'path': path,
                    'query_string': query_string,
                    'raw_path': raw_path,
                    'root_path': '',
                    'scheme': 'https',
                    'type': 'http'
                }
                handler = HttpHandler(authority=authority, connection=self._http, protocol=self, scope=scope,
                                      stream_id=event.stream_id, stream_ended=event.stream_ended,
                                      transmit=self.transmit)

            self._handlers[event.stream_id] = handler
            asyncio.ensure_future(handler.run_asgi(app))

        elif isinstance(event, (DataReceived, HeadersReceived)) and event.stream_id in self._handlers:
            handler = self._handlers[event.stream_id]
            handler.http_event_received(event)
        elif isinstance(event, DatagramReceived):
            handler = self._handlers[event.flow_id]
            handler.http_event_received(event)
        elif isinstance(event, WebTransportStreamDataReceived):
            handler = self._handlers[event.session_id]
            handler.http_event_received(event)
            asyncio.ensure_future(handler.run_asgi(app))

