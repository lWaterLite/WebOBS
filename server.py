import asyncio

from aioquic.h3.connection import H3_ALPN
from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio.server import serve
from pathlib import Path

from server_packet.session_ticket import SimpleSessionTicketStore
from server_packet.custom_handler import HttpServerProtocol


async def run_server(host: str, port: int,
                     server_configuration: QuicConfiguration,
                     session_ticket_store: SimpleSessionTicketStore,
                     retry: bool
                     ) -> None:
    print(f'run server on {host}:{port}')
    await serve(host, port,
                configuration=server_configuration,
                create_protocol=HttpServerProtocol,
                session_ticket_fetcher=session_ticket_store.pop,
                session_ticket_handler=session_ticket_store.add,
                retry=retry)
    await asyncio.Future()


# quic_logger = QuicFileLogger('./log')
quic_logger = None
secrets_log_file = open('./log/sllog.log', 'a')

configuration = QuicConfiguration(
    # for 'siduck', see at https://datatracker.ietf.org/doc/html/draft-pardue-quic-siduck-00
    # for short, it's a new ALPN ID for Quic datagram frame, still in draft.
    alpn_protocols=H3_ALPN + ['siduck'],
    is_client=False,
    max_datagram_frame_size=64 * 1024,
    quic_logger=quic_logger,
    secrets_log_file=secrets_log_file
)

certificate = Path('./cert/server.pem')
private_key = Path('./cert/server_key.pem')
configuration.load_cert_chain(certfile=certificate, keyfile=private_key)

if __name__ == '__main__':
    try:
        asyncio.run(
            run_server(
                host='localhost',
                port=4433,
                server_configuration=configuration,
                session_ticket_store=SimpleSessionTicketStore(),
                retry=False
            )
        )
    except KeyboardInterrupt:
        pass
