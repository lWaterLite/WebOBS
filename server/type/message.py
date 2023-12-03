from enum import Enum, auto


class WebTransprotSendMessage(Enum):
    Accept = auto()
    Close = auto()
    Stream = auto()
    Datagram = auto()


class WebTransportReceiveMessage(Enum):
    Connection = auto()
    Stream = auto()
    Datagram = auto()
