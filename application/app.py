import asyncio
import os
import struct

from starlette.responses import HTMLResponse
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.types import Scope, Receive, Send
from starlette.staticfiles import StaticFiles
from typing import Dict

from .stream.videostream import VideoStreamCollect

TEMPLATE_ROOT = os.path.join(os.path.dirname(__file__), 'templates')

collects: Dict[int, VideoStreamCollect] = {}
stack = []


async def index(request):
    html = open(TEMPLATE_ROOT + '/index.html', 'r')
    await request.send_push_promise('/main.css')
    return HTMLResponse(html.read())


# async def wt_push(scope, receive: Receive, send: Send) -> None:
#     global stack
#     message = await receive()
#     if message['type'] == 'webtransport.connect':
#         await send({'type': 'webtransport.accept'})
#     else:
#         return
#
#     first_recv = True
#     link_id = None
#     while True:
#         try:
#             message = await receive()
#             if message['type'] == 'webtransport.datagram.receive':
#                 await send({
#                     'type': 'webtransport.datagram.send',
#                     'data': message['data']
#                 })
#             elif message['type'] == 'webtransport.stream.receive':
#                 data = message['data']
#                 stack.append(data)
#                 if not data:
#                     del collects[link_id]
#                     break
#
#                 if first_recv:
#                     vsc = VideoStreamCollect()
#                     await vsc.process_and_store_data(data)
#                     link_id = vsc.link_id
#                     collects[link_id] = vsc
#                     first_recv = False
#                 else:
#                     await collects[link_id].process_and_store_data(data)
#
#                 # await send({
#                 #     'type': 'webtransport.stream.send',
#                 #     'data': message['data'],
#                 #     'stream': message['stream']
#                 # })
#         except Exception:
#             break


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
            stack.append(frame)
            frame = data
        else:
            frame += data




async def wt_get(scope, receive: Receive, send: Send):
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
        vsc = collects[link_id]
        stream_start = vsc.stream_start
        while True:
            stream_last = vsc.stream_last
            if stream_start <= stream_last and stream_start in vsc.stream_data.keys():
                d = {
                    'type': 'webtransport.stream.send',
                    'data': vsc.stream_data[stream_start],
                    'stream': stream_id
                }
                await send(d)
                stream_start += 1
                await asyncio.sleep(1)


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
    else:
        await starletteApp(scope, receive, send)
