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


starletteApp = Starlette(routes=[
    Route('/', index),
    Mount('/', StaticFiles(directory=TEMPLATE_ROOT, html=True))
])


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    await starletteApp(scope, receive, send)
