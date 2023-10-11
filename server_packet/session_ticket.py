from aioquic.tls import SessionTicket
from typing import Dict, Optional


class SimpleSessionTicketStore:
    def __init__(self) -> None:
        self.tickets: Dict[bytes, SessionTicket] = {}

    def add(self, ticket: SessionTicket) -> None:
        self.tickets[ticket.ticket] = ticket

    def pop(self, tag: bytes) -> Optional[SessionTicket]:
        return self.tickets.pop(tag, None)
