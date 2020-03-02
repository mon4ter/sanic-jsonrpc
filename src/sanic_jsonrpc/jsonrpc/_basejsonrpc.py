from asyncio import shield, Future, Queue, ensure_future
from time import monotonic
from typing import Any, AnyStr, Callable, Dict, List, Optional, Union, Tuple

from fashionable import ModelError, ModelAttributeError, UNSET
from ujson import dumps, loads

from .._routing import Route, ArgError, ResultError
from ..errors import INTERNAL_ERROR, INVALID_PARAMS, INVALID_REQUEST, METHOD_NOT_FOUND, PARSE_ERROR
from ..loggers import access_logger, error_logger, logger, traffic_logger
from ..models import Error, Notification, Request, Response
from ..types import AnyJsonrpc, Incoming

__all__ = [
    'BaseJsonrpc',
]


class BaseJsonrpc:
    @staticmethod
    def _parse_json(json: AnyStr) -> Union[Dict, List[Dict], Response]:
        try:
            return loads(json)
        except (TypeError, ValueError):
            return Response(error=PARSE_ERROR)

    @staticmethod
    def _parse_message(message: Dict) -> AnyJsonrpc:
        try:
            return Request(**message)
        except (TypeError, ModelError) as err:
            if isinstance(err, ModelAttributeError) and err.kwargs['attr'] == 'id':
                return Notification(**message)

            return Response(error=INVALID_REQUEST)

    def _parse_messages(self, json: AnyStr) -> Union[AnyJsonrpc, List[AnyJsonrpc]]:
        messages = self._parse_json(json)

        if isinstance(messages, Response):
            return messages

        if isinstance(messages, list):
            if not messages:
                return Response(error=INVALID_REQUEST)

            return [self._parse_message(m) for m in messages]

        return self._parse_message(messages)

    def _serialize(self, obj: Any) -> str:
        try:
            return dumps(obj)
        except Exception as err:
            error_logger.error("Failed to serialize object %r: %s", obj, err, exc_info=err)
            return self._serialize(dict(Response(error=INTERNAL_ERROR)))

    def _serialize_responses(self, responses: List[Response], single: bool) -> Optional[str]:
        if not responses:
            return None

        if single:
            return self._serialize(dict(responses[0]))

        return self._serialize([dict(r) for r in responses])

    def _route(self, incoming: Incoming, is_post: bool) -> Optional[Union[Route, Response]]:
        is_request = isinstance(incoming, Request)
        route = self._routes.get((is_post, is_request, incoming.method))

        if route:
            return route

        if is_request:
            return Response(error=METHOD_NOT_FOUND, id=incoming.id)

    def _register_call(self, *args, **kwargs) -> Future:
        fut = shield(self._call(*args, **kwargs))
        self._calls.put_nowait(fut)
        return fut

    async def _call(self, incoming: Incoming, route: Route, customs: Dict[type, Any]) -> Optional[Response]:
        access_log = self.access_log

        if access_log:
            start = monotonic()
        else:
            start = None

        traffic_logger.debug("--> %r", incoming)

        error = UNSET
        result = UNSET

        try:
            ret = await route.call(incoming.params, customs)
        except ResultError as err:
            error_logger.error("%r failed: %s", incoming, err, exc_info=err)
            error = INTERNAL_ERROR
        except ArgError as err:
            logger.debug("Invalid %r: %s", incoming, err)
            error = INVALID_PARAMS
        except Error as err:
            error = err
        except Exception as err:
            error_logger.error("%r failed: %s", incoming, err, exc_info=err)
            error = INTERNAL_ERROR
        else:
            if isinstance(ret, Error):
                error = ret
            else:
                result = ret

        is_request = isinstance(incoming, Request)

        if access_log:
            access_logger.info("", extra={
                'type': incoming.__class__.__name__,
                'method': incoming.method,
                'id': incoming.id if is_request else '',
                'time': '{:.6f}'.format((monotonic() - start) * 1000),
                'error': error.code if error is not UNSET else '',
            })

        if is_request:
            response = Response(result=result, error=error, id=incoming.id)
            traffic_logger.debug("<-- %r", response)
            return response

    @staticmethod
    def _finalise_future(fut: Future) -> Optional[Union[Response, str]]:
        if fut.done():
            err = fut.exception()

            if err:
                error_logger.error("%s", err, exc_info=err)
            else:
                return fut.result()
        else:
            fut.cancel()

    async def _processing(self):
        calls = self._calls

        while True:
            call = await calls.get()
            await call

    async def _start_processing(self, _app, _loop):
        self._calls = Queue()
        self._processing_task = ensure_future(self._processing())

    async def _stop_processing(self, _app, _loop):
        self._processing_task.cancel()

        calls = self._calls

        while not calls.empty():
            await calls.get_nowait()

    def __init__(self, *, access_log: bool = True):
        self.access_log = access_log
        self._routes = {}
        self._calls = None

    def __call__(
            self,
            method_: Optional[str] = None,
            *,
            is_post_: Tuple[bool, ...] = (True, False),
            is_request_: Tuple[bool, ...] = (True, False),
            **annotations: type
    ) -> Callable:
        if isinstance(method_, Callable):
            return self.__call__(is_post_=is_post_, is_request_=is_request_)(method_)

        def deco(func: Callable) -> Callable:
            route = Route.from_inspect(func, method_, annotations)
            self._routes.update({(ip, ir, route.method): route for ip in is_post_ for ir in is_request_})
            return func
        return deco

    def post(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, is_post_=(True,), **annotations)

    def ws(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, is_post_=(False,), **annotations)

    def request(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, is_request_=(True,), **annotations)

    def notification(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, is_request_=(False,), **annotations)

    def post_request(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, is_post_=(True,), is_request_=(True,), **annotations)

    def ws_request(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, is_post_=(False,), is_request_=(True,), **annotations)

    def post_notification(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, is_post_=(True,), is_request_=(False,), **annotations)

    def ws_notification(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, is_post_=(False,), is_request_=(False,), **annotations)
