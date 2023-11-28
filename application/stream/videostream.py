import time
import struct

from typing import Dict


class VideoStreamCollect:
    def __init__(self):
        self.stream_data: Dict[int, bytes] = {}
        self.stream_start = None
        self.stream_last = None
        self.last_cleanup_time = time.time()
        self.link_id = None

    async def process_and_store_data(self, data):
        first4 = struct.unpack('!I', data[:4])[0]
        seq_id = None
        if first4 == 0xFFFFFFFF:
            seq_id = struct.unpack("!I", data[16:20])[0]
            link_id = struct.unpack('!I', data[4:8])[0]
            if self.link_id is None:
                self.link_id = link_id
            else:
                if link_id != self.link_id:
                    return

            if self.stream_start is None:
                self.stream_start = seq_id
                self.stream_last = seq_id
            else:
                if seq_id > self.stream_last:
                    self.stream_last = seq_id

        if seq_id not in self.stream_data and seq_id is not None:
            self.stream_data[seq_id] = b""
        if seq_id is not None:
            self.stream_data[seq_id] += data

        if time.time() - self.last_cleanup_time >= 20:
            self.last_cleanup_time = time.time()
            await self.cleanup_stream()

    async def cleanup_stream(self):
        while self.stream_data:
            if self.stream_start in self.stream_data.keys():
                del self.stream_data

            while not(self.stream_start in self.stream_data.keys()) and self.stream_start <= self.stream_last:
                self.stream_start += 1

            if len(self.stream_data.keys()) <= 100:
                break

