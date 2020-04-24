from enum import Enum

from .predicate import Predicate
from .directions import Directions as Di
from .objects import Objects as Ob
from .transports import Transports as Tr

__all__ = [
    'Predicates',
]


class Predicates(Enum):
    any = Predicate({Di.incoming, Di.outgoing}, {Tr.post, Tr.ws}, {Ob.request, Ob.response, Ob.notification})

    incoming = Predicate({Di.incoming}, {Tr.post, Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    outgoing = Predicate({Di.outgoing}, {Tr.post, Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    post = Predicate({Di.incoming, Di.outgoing}, {Tr.post}, {Ob.request, Ob.response, Ob.notification})
    ws = Predicate({Di.incoming, Di.outgoing}, {Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    request = Predicate({Di.incoming, Di.outgoing}, {Tr.post, Tr.ws}, {Ob.request})
    response = Predicate({Di.incoming, Di.outgoing}, {Tr.post, Tr.ws}, {Ob.response})
    notification = Predicate({Di.incoming, Di.outgoing}, {Tr.post, Tr.ws}, {Ob.notification})

    incoming_post = Predicate({Di.incoming}, {Tr.post}, {Ob.request, Ob.response, Ob.notification})
    incoming_ws = Predicate({Di.incoming}, {Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    outgoing_post = Predicate({Di.outgoing}, {Tr.post}, {Ob.request, Ob.response, Ob.notification})
    outgoing_ws = Predicate({Di.outgoing}, {Tr.ws}, {Ob.request, Ob.response, Ob.notification})
    incoming_request = Predicate({Di.incoming}, {Tr.post, Tr.ws}, {Ob.request})
    incoming_notification = Predicate({Di.incoming}, {Tr.post, Tr.ws}, {Ob.notification})
    outgoing_response = Predicate({Di.outgoing}, {Tr.post, Tr.ws}, {Ob.response})
    outgoing_notification = Predicate({Di.outgoing}, {Tr.post, Tr.ws}, {Ob.notification})

    incoming_post_request = Predicate({Di.incoming}, {Tr.post}, {Ob.request})
    incoming_post_notification = Predicate({Di.incoming}, {Tr.post}, {Ob.notification})
    incoming_ws_request = Predicate({Di.incoming}, {Tr.ws}, {Ob.request})
    incoming_ws_notification = Predicate({Di.incoming}, {Tr.ws}, {Ob.notification})
    outgoing_post_response = Predicate({Di.outgoing}, {Tr.post}, {Ob.response})
    outgoing_post_notification = Predicate({Di.outgoing}, {Tr.post}, {Ob.notification})
    outgoing_ws_response = Predicate({Di.outgoing}, {Tr.ws}, {Ob.response})
    outgoing_ws_notification = Predicate({Di.outgoing}, {Tr.ws}, {Ob.notification})
