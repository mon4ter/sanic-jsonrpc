from enum import Enum

from .event import Event
from .directions import Directions as Di
from .objects import Objects as Ob
from .transports import Transports as Tr

__all__ = [
    'Events',
]


class Events(Enum):
    all = Event({Di.incoming, Di.outgoing}, {Tr.post, Tr.ws}, {Ob.request, Ob.response, Ob.notification})

    incoming = Event({Di.incoming}, {Tr.post, Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    outgoing = Event({Di.outgoing}, {Tr.post, Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    post = Event({Di.incoming, Di.outgoing}, {Tr.post}, {Ob.request, Ob.response, Ob.notification})
    ws = Event({Di.incoming, Di.outgoing}, {Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    request = Event({Di.incoming, Di.outgoing}, {Tr.post, Tr.ws}, {Ob.request})
    response = Event({Di.incoming, Di.outgoing}, {Tr.post, Tr.ws}, {Ob.response})
    notification = Event({Di.incoming, Di.outgoing}, {Tr.post, Tr.ws}, {Ob.notification})

    incoming_post = Event({Di.incoming}, {Tr.post}, {Ob.request, Ob.response, Ob.notification})
    incoming_ws = Event({Di.incoming}, {Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    outgoing_post = Event({Di.outgoing}, {Tr.post}, {Ob.request, Ob.response, Ob.notification})
    outgoing_ws = Event({Di.outgoing}, {Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    incoming_request = Event({Di.incoming}, {Tr.post, Tr.ws}, {Ob.request})
    incoming_response = Event({Di.incoming}, {Tr.post, Tr.ws}, {Ob.response})
    incoming_notification = Event({Di.incoming}, {Tr.post, Tr.ws}, {Ob.notification})
    outgoing_request = Event({Di.outgoing}, {Tr.post, Tr.ws}, {Ob.request})
    outgoing_response = Event({Di.outgoing}, {Tr.post, Tr.ws}, {Ob.response})
    outgoing_notification = Event({Di.outgoing}, {Tr.post, Tr.ws}, {Ob.notification})

    incoming_post_request = Event({Di.incoming}, {Tr.post}, {Ob.request})
    incoming_post_response = Event({Di.incoming}, {Tr.post}, {Ob.response})
    incoming_post_notification = Event({Di.incoming}, {Tr.post}, {Ob.notification})
    incoming_ws_request = Event({Di.incoming}, {Tr.ws}, {Ob.request})
    incoming_ws_response = Event({Di.incoming}, {Tr.ws}, {Ob.response})
    incoming_ws_notification = Event({Di.incoming}, {Tr.ws}, {Ob.notification})
    outgoing_post_request = Event({Di.outgoing}, {Tr.post}, {Ob.request})
    outgoing_post_response = Event({Di.outgoing}, {Tr.post}, {Ob.response})
    outgoing_post_notification = Event({Di.outgoing}, {Tr.post}, {Ob.notification})
    outgoing_ws_request = Event({Di.outgoing}, {Tr.ws}, {Ob.request})
    outgoing_ws_response = Event({Di.outgoing}, {Tr.ws}, {Ob.response})
    outgoing_ws_notification = Event({Di.outgoing}, {Tr.ws}, {Ob.notification})
