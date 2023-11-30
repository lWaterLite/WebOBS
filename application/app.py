import asyncio
import os
import struct

from starlette.responses import HTMLResponse
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.types import Scope, Receive, Send
from starlette.staticfiles import StaticFiles

from . import media_handler

TEMPLATE_ROOT = os.path.join(os.path.dirname(__file__), 'templates')

is_connect_set = False


async def index(request):
    html = open(TEMPLATE_ROOT + '/index.html', 'r')
    await request.send_push_promise('/main.css')
    return HTMLResponse(html.read())


async def wt_test_push(scope, receive, send):
    global is_connect_set
    message = await receive()
    if message['type'] == 'webtransport.connect':
        if not is_connect_set:
            is_connect_set = True
            await send({'type': 'webtransport.accept'})
    elif message['type'] == 'webtransport.stream.receive':
        print('asgi receive stream')


async def push_frame(receive):
    frame = None
    message = await receive()
    data = message['data']
    first4 = struct.unpack('!I', data[:4])[0]
    if first4 == 0xFFFFFFFF:
        if frame is not None:
            await media_handler.push(frame)
            frame = data
    else:
        frame += data


async def wt_push(scope, receive, send):
    global stack

    message = await receive()
    if message['type'] == 'webtransport.connect':
        await send({'type': 'webtransport.accept'})

    message = await receive()
    if message['type'] == 'webtransport.stream.receive':
        frame = message['data']
    else:
        return

    while True:
        message = await receive()
        data = message['data']
        first4 = struct.unpack('!I', data[:4])[0]
        if first4 == 0xFFFFFFFF:
            await media_handler.push(frame)
            frame = data
        else:
            frame += data


async def wt_get(scope, receive: Receive, send: Send):
    message = await receive()
    if message['type'] == 'webtransport.connect':
        await send({'type': 'webtransport.accept'})
    else:
        return

    while True:
        try:
            frame_index = media_handler.get_pre_index() + 5
            frame = media_handler.get(frame_index)
            frame_index += 1

            data = {
                'type': 'webtransport.stream.send',
                'data': frame,
                'stream': 3
            }
            await send(data)
            await media_handler.delete()
            await asyncio.sleep(1)
        except Exception:
            break

    # vsc = collects[link_id]
    # stream_start = vsc.stream_start
    # while True:
    #     stream_last = vsc.stream_last
    #     if stream_start <= stream_last and stream_start in vsc.stream_data.keys():
    #         d = {
    #             'type': 'webtransport.stream.send',
    #             'data': vsc.stream_data[stream_start],
    #             'stream': stream_id
    #         }
    #         await send(d)
    #         stream_start += 1
    #         await asyncio.sleep(1)


async def wt_test_get(scope, receive: Receive, send: Send):
    message = await receive()
    if message['type'] == 'webtransport.connect':
        await send({'type': 'webtransport.accept'})
    else:
        return

    link_id = None
    message = await receive()
    stream_id = message['stream']
    if message['type'] == 'webtransport.stream.receive':
        link_id = struct.unpack('!I', message['data'][0:4])[0]

    if link_id is None:
        return
    else:
        print(link_id)
        count = b'1' * 4000
        while True:
            d = {
                'type': 'webtransport.stream.send',
                'data': bytes(count),
                'stream': stream_id
            }
            await send(d)
            await asyncio.sleep(1)


starletteApp = Starlette(routes=[
    Route('/', index),
    Mount('/', StaticFiles(directory=TEMPLATE_ROOT, html=True))
])


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope['type'] == 'webtransport':
        if scope['path'] == '/wt/push':
            await wt_push(scope, receive, send)
        elif scope['path'] == '/wt/get':
            await wt_get(scope, receive, send)
        elif scope['path'] == '/wt/test/get':
            await wt_test_get(scope, receive, send)
        elif scope['path'] == '/wt/test/push':
            await wt_test_push(scope, receive, send)
    else:
        await starletteApp(scope, receive, send)
