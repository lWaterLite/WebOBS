import asyncio
import os

from starlette.responses import HTMLResponse
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from . import media_stream_handler
from .utils import repeat_send_chunk_task
from server.type.message import WebTransportReceiveMessage, WebTransprotSendMessage

TEMPLATE_ROOT = os.path.join(os.path.dirname(__file__), 'templates')


async def index(request):
    html = open(TEMPLATE_ROOT + '/index.html', 'r')
    return HTMLResponse(html.read())


async def streamer(request):
    html = open(TEMPLATE_ROOT + '/wt/streamer.html', 'r')
    return HTMLResponse(html.read())


async def receiver(request):
    html = open(TEMPLATE_ROOT + '/wt/receiver.html', 'r')
    return HTMLResponse(html.read())


async def wt_push(receive, send):
    message = await receive()

    if message['type'] == WebTransportReceiveMessage.Connection:
        if not media_stream_handler.is_push_connect_set:
            media_stream_handler.is_push_connect_set = True
            await send({'type': WebTransprotSendMessage.Accept})

    elif message['type'] == WebTransportReceiveMessage.Stream:
        await media_stream_handler.frame_handler(message['data'])


async def wt_get(receive, send):
    message = await receive()
    if message['type'] == WebTransportReceiveMessage.Connection:
        if not media_stream_handler.is_get_connect_set:
            await send({'type': WebTransprotSendMessage.Accept})
            media_stream_handler.is_get_connect_set = True
    elif message['type'] == WebTransportReceiveMessage.Stream:
        # await send_chunk(send, message['stream'])
        asyncio.create_task(repeat_send_chunk_task(send, message['stream'], 0.045))


starletteApp = Starlette(routes=[
    Route('/', index),
    Route('/index', index),
    Route('/wt/streamer', streamer),
    Route('/wt/receiver', receiver),
    Mount('/', StaticFiles(directory=TEMPLATE_ROOT, html=True))
])


async def app(scope, receive, send) -> None:
    if scope['type'] == 'webtransport':
        if scope['path'] == '/wt/push':
            await wt_push(receive, send)
        elif scope['path'] == '/wt/get':
            await wt_get(receive, send)
    else:
        await starletteApp(scope, receive, send)
