import struct

from typing import Dict


class MediaStreamHandler:
    def __init__(self):
        self.is_push_connect_set = False
        self.is_get_connect_set = False
        self._frame = None
        self._index: int = 0
        self._pre_index: int = 0
        self._video_chunk: Dict[int, bytes] = {}

    def get_pre_index(self):
        return self._pre_index

    async def frame_handler(self, frame: bytes):
        try:
            first4 = struct.unpack('!I', frame[:4])[0]
        except Exception as e:
            print(frame)
            print(e)
            return
        if first4 == 0xFFFFFFFF:
            if self._frame is not None:

                # push property but params, stupid I'm. This cost me nearly 1 hour to fix...
                await self._push_chunk(self._frame)
            self._frame = frame

        else:
            self._frame += frame

    async def _push_chunk(self, data: bytes):
        self._video_chunk[self._index] = data
        self._index += 1

    def get_chunk(self, require: int):
        if require in self._video_chunk:
            return self._video_chunk[require], True
        else:
            return None, False

    async def delete(self):
        del self._video_chunk[self._pre_index]
        self._pre_index += 1
