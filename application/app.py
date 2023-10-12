import os

from starlette.responses import HTMLResponse
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.types import Scope, Receive, Send
from starlette.staticfiles import StaticFiles


TEMPLATE_ROOT = os.path.join(os.path.dirname(__file__), 'templates')


async def index(request):
    html = open(TEMPLATE_ROOT+'/index.html', 'r')
    await request.send_push_promise('/main.css')
    return HTMLResponse(html.read())


async def wt(scope, receive: Receive, send: Send) -> None:
    message = await receive()
    assert message['type'] == 'webtransport.connect'
    await send({'type': 'webtransport.accept'})

    while True:
        message = await receive()
        print(message)
        if message['type'] == 'webtransport.datagram.receive':
            await send({
                'type': 'webtransport.datagram.send',
                'data': message['data']
            })
        elif message['type'] == 'webtransport.stream.receive':
            await send({
                'type': 'webtransport.stream.send',
                'data': message['data'],
                'stream': message['stream']
            })


starletteApp = Starlette(routes=[
    Route('/', index),
    Mount('/', StaticFiles(directory=TEMPLATE_ROOT, html=True))
])


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope['type'] == 'webtransport' and scope['path'] == '/wt':
        await wt(scope, receive, send)
    else:
        await starletteApp(scope, receive, send)
