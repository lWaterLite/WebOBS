import asyncio
import argparse

from server.server import run_server


def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default='localhost')
    parser.add_argument('--port', type=int, default=4433)
    parser.add_argument('--certifi_file', type=str, default='./certifi/server.pem')
    parser.add_argument('--certifi_key', type=str, default='./certifi/server_key.pem')
    parser.add_argument('--log', type=str, default='./log/sl_log.log')
    parser.add_argument('--retry', type=bool, default=False)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse()

    try:
        asyncio.run(
            run_server(
                host=args.host,
                port=args.port,
                certificate=(args.certifi_file, args.certifi_key),
                log=args.log,
                retry=args.retry
            )
        )
    except KeyboardInterrupt:
        pass
