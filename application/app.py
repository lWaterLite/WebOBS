import asyncio
import os
import struct

from starlette.responses import HTMLResponse
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.types import Scope, Receive, Send
from starlette.staticfiles import StaticFiles

from . import media_stream_handler

TEMPLATE_ROOT = os.path.join(os.path.dirname(__file__), 'templates')


async def index(request):
    html = open(TEMPLATE_ROOT + '/index.html', 'r')
    await request.send_push_promise('/main.css')
    return HTMLResponse(html.read())


async def wt_test_push(scope, receive, send):
    message = await receive()
    if message['type'] == 'webtransport.connect':
        if not media_stream_handler.is_connect_set:
            media_stream_handler.is_connect_set = True
            await send({'type': 'webtransport.accept'})
    elif message['type'] == 'webtransport.stream.receive':
        await media_stream_handler.frame_handler(message['data'])


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
            await media_stream_handler.push(frame)
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
            frame_index = media_stream_handler.get_pre_index() + 5
            frame = media_stream_handler.get_chunk(frame_index)
            frame_index += 1

            data = {
                'type': 'webtransport.stream.send',
                'data': frame,
                'stream': 3
            }
            await send(data)
            await media_stream_handler.delete()
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


async def send_chunk(send, stream_id):
    # chunk_id = media_stream_handler.get_pre_index() + 5
    # data = media_stream_handler.get_chunk(chunk_id)
    # await media_stream_handler.delete()
    d = b'f' * 4000
    print('sending...')
    await send({
        'type': 'webtransport.stream.send',
        'data': d,
        'stream': stream_id
    })


async def repeat_send_chunk_task(send, stream_id):
    # while media_stream_handler.is_connect_set:
    while True:
        print('looping...')
        await send_chunk(send, stream_id)
        await asyncio.sleep(1)


connect_set = False


async def wt_test_get(scope, receive: Receive, send: Send):
    global connect_set
    message = await receive()
    if message['type'] == 'webtransport.connect':
        if not connect_set:
            await send({'type': 'webtransport.accept'})
            connect_set = True
    elif message['type'] == 'webtransport.stream.receive':
        print(message['data'])
        # await send_chunk(send, message['stream'])
        asyncio.create_task(repeat_send_chunk_task(send, message['stream']))


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
