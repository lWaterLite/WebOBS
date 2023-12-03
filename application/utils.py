import asyncio

from . import media_stream_handler
from server.type.message import WebTransprotSendMessage


async def send_chunk(send, stream_id):
    chunk_id = media_stream_handler.get_pre_index()
    data, state = media_stream_handler.get_chunk(chunk_id)
    if state:
        await media_stream_handler.delete()
        await send({
            'type': WebTransprotSendMessage.Stream,
            'data': data,
            'stream': stream_id
        })
    else:
        return


async def repeat_send_chunk_task(send, stream_id, fps):
    while media_stream_handler.is_get_connect_set:
        await send_chunk(send, stream_id)
        await asyncio.sleep(fps)
