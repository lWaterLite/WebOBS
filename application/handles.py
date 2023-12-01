import struct

from typing import Dict


class MediaStreamHandler:
    def __init__(self):
        self.is_connect_set = False
        self._frame = None
        self._index: int = 0
        self._pre_index: int = 0
        self._video_chunk: Dict[int, bytes] = {}

    def get_pre_index(self):
        return self._pre_index

    async def frame_handler(self, frame: bytes):
        first4 = struct.unpack('!I', frame[:4])[0]
        if first4 == 0xFFFFFFFF:
            if self._frame is not None:
                await self._push_chunk(frame)
            self._frame = frame

        else:
            self._frame += frame

    async def _push_chunk(self, data: bytes):
        self._video_chunk[self._index] = data
        print(f'pushing frame {self._index}')
        self._index += 1

    def get_chunk(self, require: int):
        if require in self._video_chunk:
            return self._video_chunk[require]
        else:
            return self._video_chunk[self._index]

    async def delete(self):
        del self._video_chunk[self._pre_index]
        self._pre_index += 1
