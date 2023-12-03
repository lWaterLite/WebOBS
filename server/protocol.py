import asyncio
from typing import Dict, Optional, Union

from aioquic.asyncio import QuicConnectionProtocol
from aioquic.h3.connection import H3Connection, H3Event, DataReceived, HeadersReceived, H3_ALPN, \
    WebTransportStreamDataReceived
from aioquic.quic.events import QuicEvent, ProtocolNegotiated

from application.app import app
from .type.message import WebTransportReceiveMessage
from .handler import WebTransportHandler
from .log import logger, Foreground

BaseHandler = Union[WebTransportHandler]


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
            query_string = query_string.decode()

            logs = f'{logger("H3 request", foreground=Foreground.GREEN)} ' \
                   f'{logger(f"{method}", foreground=Foreground.CYAN)} ' \
                   f'{path}'
            print(logs)

            handler: BaseHandler
            scope: Dict

            if method == 'CONNECT' and protocol == 'webtransport':
                scope = {
                    'authority': authority,
                    'headers': headers,
                    'http_version': http_version,
                    'method': method,
                    'path': path,
                    'query_string': query_string,
                    'scheme': 'https',
                    'type': 'webtransport'
                }
                handler = WebTransportHandler(
                    connection=self._http,
                    scope=scope,
                    stream_id=event.stream_id,
                    transmit=self.transmit
                )
                handler.message_queue.put_nowait({'type': WebTransportReceiveMessage.Connection})
            else:
                # extensions: Dict[str, Dict] = {}
                # if isinstance(self._http, H3Connection):
                #     extensions['http.response.push'] = {}
                #
                # scope = {
                #     'extensions': extensions,
                #     'headers': headers,
                #     'http_version': http_version,
                #     'method': method,
                #     'path': path,
                #     'query_string': query_string,
                #     'raw_path': raw_path,
                #     'root_path': '',
                #     'scheme': 'https',
                #     'type': 'http'
                # }
                # handler = HttpHandler(authority=authority, connection=self._http, protocol=self, scope=scope,
                #                       stream_id=event.stream_id, stream_ended=event.stream_ended,
                #                       transmit=self.transmit)
                return

            self._handlers[event.stream_id] = handler
            asyncio.ensure_future(handler.run_asgi(app))

        elif isinstance(event, (DataReceived, HeadersReceived)) and event.stream_id in self._handlers:
            handler = self._handlers[event.stream_id]
            handler.http_event_handler(event)
        elif isinstance(event, WebTransportStreamDataReceived):
            handler = self._handlers[event.session_id]
            handler.http_event_handler(event)
            asyncio.ensure_future(handler.run_asgi(app))
