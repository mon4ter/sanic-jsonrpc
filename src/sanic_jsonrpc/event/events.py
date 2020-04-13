from enum import Enum

from ._event import _Event
from ._directions import _Directions as Di
from ._objects import _Objects as Ob
from ._transports import _Transports as Tr

__all__ = [
    'Events',
]


class Events(Enum):
    all = _Event({Di.incoming, Di.outgoing}, {Tr.post, Tr.ws}, {Ob.request, Ob.response, Ob.notification})

    incoming = _Event({Di.incoming}, {Tr.post, Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    outgoing = _Event({Di.outgoing}, {Tr.post, Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    post = _Event({Di.incoming, Di.outgoing}, {Tr.post}, {Ob.request, Ob.response, Ob.notification})
    ws = _Event({Di.incoming, Di.outgoing}, {Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    request = _Event({Di.incoming, Di.outgoing}, {Tr.post, Tr.ws}, {Ob.request})
    response = _Event({Di.incoming, Di.outgoing}, {Tr.post, Tr.ws}, {Ob.response})
    notification = _Event({Di.incoming, Di.outgoing}, {Tr.post, Tr.ws}, {Ob.notification})

    incoming_post = _Event({Di.incoming}, {Tr.post}, {Ob.request, Ob.response, Ob.notification})
    incoming_ws = _Event({Di.incoming}, {Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    outgoing_post = _Event({Di.outgoing}, {Tr.post}, {Ob.request, Ob.response, Ob.notification})
    outgoing_ws = _Event({Di.outgoing}, {Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    incoming_request = _Event({Di.incoming}, {Tr.post, Tr.ws}, {Ob.request})
    incoming_response = _Event({Di.incoming}, {Tr.post, Tr.ws}, {Ob.response})
    incoming_notification = _Event({Di.incoming}, {Tr.post, Tr.ws}, {Ob.notification})
    outgoing_request = _Event({Di.outgoing}, {Tr.post, Tr.ws}, {Ob.request})
    outgoing_response = _Event({Di.outgoing}, {Tr.post, Tr.ws}, {Ob.response})
    outgoing_notification = _Event({Di.outgoing}, {Tr.post, Tr.ws}, {Ob.notification})

    incoming_post_request = _Event({Di.incoming}, {Tr.post}, {Ob.request})
    incoming_post_response = _Event({Di.incoming}, {Tr.post}, {Ob.response})
    incoming_post_notification = _Event({Di.incoming}, {Tr.post}, {Ob.notification})
    incoming_ws_request = _Event({Di.incoming}, {Tr.ws}, {Ob.request})
    incoming_ws_response = _Event({Di.incoming}, {Tr.ws}, {Ob.response})
    incoming_ws_notification = _Event({Di.incoming}, {Tr.ws}, {Ob.notification})
    outgoing_post_request = _Event({Di.outgoing}, {Tr.post}, {Ob.request})
    outgoing_post_response = _Event({Di.outgoing}, {Tr.post}, {Ob.response})
    outgoing_post_notification = _Event({Di.outgoing}, {Tr.post}, {Ob.notification})
    outgoing_ws_request = _Event({Di.outgoing}, {Tr.ws}, {Ob.request})
    outgoing_ws_response = _Event({Di.outgoing}, {Tr.ws}, {Ob.response})
    outgoing_ws_notification = _Event({Di.outgoing}, {Tr.ws}, {Ob.notification})
