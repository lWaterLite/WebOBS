from typing import Dict


class MediaHandler:
    def __init__(self):
        self.__index: int = 0
        self.__pre_index: int = 0
        self.__video_stack: Dict[int, bytes] = {}

    def get_pre_index(self):
        return self.__pre_index

    async def push(self, data: bytes):
        self.__video_stack[self.__index] = data
        print(f'pushing frame {self.__index}')
        self.__index += 1

    def get(self, require: int):
        if require in self.__video_stack:
            return self.__video_stack[require]
        else:
            return self.__video_stack[self.__index]

    async def delete(self):
        del self.__video_stack[self.__pre_index]
        self.__pre_index += 1
