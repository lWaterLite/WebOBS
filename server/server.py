import asyncio

from aioquic.h3.connection import H3_ALPN
from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio.server import serve
from pathlib import Path
from typing import Tuple

from server.session import SimpleSessionTicketStore
from server.protocol import HttpServerProtocol
from server.log import logger, Foreground


async def run_server(host: str, port: int,
                     certificate: Tuple[str, str],
                     log: str,
                     retry: bool) -> None:
    secrets_log_file = open(log, 'a')

    configuration = QuicConfiguration(
        # for 'siduck', see at https://datatracker.ietf.org/doc/html/draft-pardue-quic-siduck-00
        # for short, it's a new ALPN ID for Quic datagram frame, still in draft.
        alpn_protocols=H3_ALPN + ['siduck'],
        is_client=False,
        max_datagram_frame_size=64 * 1024,
        secrets_log_file=secrets_log_file
    )
    # certificate = Path('./certifi/server.pem')
    # private_key = Path('./certifi/server_key.pem')
    certificate_file = Path(certificate[0])
    certificate_key = Path(certificate[1])
    configuration.load_cert_chain(certfile=certificate_file, keyfile=certificate_key)

    logs = f'{logger("run server on", foreground=Foreground.GREEN)} ' \
           f'{logger(f"{host}:{port}", foreground=Foreground.CYAN)}'
    print(logs)

    sessionStore = SimpleSessionTicketStore()
    await serve(host, port,
                configuration=configuration,
                create_protocol=HttpServerProtocol,
                session_ticket_fetcher=sessionStore.pop,
                session_ticket_handler=sessionStore.add,
                retry=retry)
    await asyncio.Future()
