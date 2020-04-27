from asyncio import Future, Queue, ensure_future, shield
from collections import defaultdict
from functools import partial
from typing import Any, AnyStr, Callable, Coroutine, Dict, List, Optional, Type, Union

from fashionable import ModelAttributeError, ModelError, UNSET
from ujson import dumps, loads

from .._context import Context
from .._middleware import Objects, Predicates
from .._routing import ArgError, ResultError, Route
from ..errors import INTERNAL_ERROR, INVALID_PARAMS, INVALID_REQUEST, METHOD_NOT_FOUND, PARSE_ERROR
from ..loggers import error_logger, logger, traffic_logger
from ..models import Error, Notification, Request, Response
from ..types import AnyJsonrpc

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

    def _handle_incoming(
            self, ctx: Context, failure_cb: Callable[[Response], None], success_cb: Callable[[Future], None]
    ) -> bool:
        route = self._routes.get((ctx.transport, ctx.object, ctx.incoming.method))

        if not route:
            if ctx.object is Objects.request:
                failure_cb(Response(error=METHOD_NOT_FOUND, id=ctx.incoming.id))
            else:
                logger.info("Unhandled %r", ctx.incoming)

            return False

        fut = self._register_call(partial(route.call, ctx.incoming.params, ctx.dict), ctx)

        if ctx.object is Objects.request:
            success_cb(fut)

        return True

    def _register_call(self, call: Callable[[], Coroutine], ctx: Context) -> Future:
        fut = shield(self._call(call, ctx))
        self._calls.put_nowait(fut)
        return fut

    async def _run_middlewares(self, ctx: Context):
        for route in self._middlewares[(ctx.direction, ctx.transport, ctx.object)]:
            logger.debug("Calling middleware %r", route.method)
            await route.call([], ctx.dict)

    async def _call(self, call: Callable[[], Coroutine], ctx: Context) -> Optional[Response]:
        error = UNSET
        result = UNSET

        try:
            await self._run_middlewares(ctx)
        except Error as err:
            error = err
        except Exception as err:
            error_logger.error("Middlewares before incoming %r failed: %s", ctx.incoming, err, exc_info=err)
            error = INTERNAL_ERROR
        else:
            traffic_logger.debug("--> %r", ctx.incoming)

            try:
                ret = await call()
            except ResultError as err:
                error_logger.error("%r failed: %s", ctx.incoming, err, exc_info=err)
                error = INTERNAL_ERROR
            except ArgError as err:
                logger.debug("Invalid %r: %s", ctx.incoming, err)
                error = INVALID_PARAMS
            except Error as err:
                error = err
            except Exception as exc:
                exc_type = type(exc)
                route = self._exceptions.get(exc_type)

                if route:
                    logger.debug("Calling %s handler %r", exc_type, route.method)

                    try:
                        ret = await route.call(exc, ctx.dict)
                    except Exception as err:
                        error_logger.error(
                            "Recovery from %s while handling %r failed: %s", err, ctx.incoming, exc, exc_info=exc
                        )
                    else:
                        if isinstance(ret, Error):
                            error = ret
                        else:
                            result = ret

                if error is UNSET and result is UNSET:
                    error_logger.error("%r failed: %s", ctx.incoming, exc, exc_info=exc)
                    error = INTERNAL_ERROR
            else:
                if isinstance(ret, Error):
                    error = ret
                else:
                    result = ret

        if ctx.object is Objects.request:
            response = Response(result=result, error=error, id=ctx.incoming.id)
            ctx = ctx(response)

            try:
                await self._run_middlewares(ctx)
            except Error as err:
                response.result = UNSET
                response.error = err
            except Exception as err:
                error_logger.error("Middlewares after %r failed: %s", ctx.incoming, err, exc_info=err)
                response.result = UNSET
                response.error = INTERNAL_ERROR

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

    def __init__(self):
        self._middlewares = defaultdict(list)
        self._exceptions = {}
        self._routes = {}
        self._calls = None

    def middleware(self, predicate: Union[Predicates, str], name: Optional[str] = None) -> Callable:
        if isinstance(predicate, Callable):
            return self.middleware(Predicates.any)(predicate)

        if isinstance(predicate, str):
            predicate = Predicates[predicate]

        predicate = predicate.value

        def deco(func: Callable) -> Callable:
            route = Route.from_inspect(func, name, {})
            route.result = None
            keys = {
                (d, t, o)
                for d in predicate.directions
                for t in predicate.transports
                for o in predicate.objects
            }

            for key in keys:
                self._middlewares[key].append(route)

            return func
        return deco

    def exception(self, *exceptions: Type[Exception]):
        def deco(func: Callable) -> Callable:
            route = Route.from_inspect(func, None, {})
            route.result = None

            for exception in exceptions:
                self._exceptions[exception] = route

            return func
        return deco

    def __call__(
            self,
            method_: Optional[str] = None,
            *,
            predicate_: Predicates = Predicates.incoming,
            **annotations: type
    ) -> Callable:
        if isinstance(method_, Callable):
            return self.__call__(predicate_=predicate_)(method_)

        predicate = predicate_.value

        def deco(func: Callable) -> Callable:
            route = Route.from_inspect(func, method_, annotations)
            self._routes.update({
                (t, o, route.method): route
                for t in predicate.transports
                for o in predicate.objects
            })
            return func
        return deco

    def post(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, predicate_=Predicates.incoming_post, **annotations)

    def ws(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, predicate_=Predicates.incoming_ws, **annotations)

    def request(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, predicate_=Predicates.incoming_request, **annotations)

    def notification(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, predicate_=Predicates.incoming_notification, **annotations)

    def post_request(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, predicate_=Predicates.incoming_post_request, **annotations)

    def ws_request(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, predicate_=Predicates.incoming_ws_request, **annotations)

    def post_notification(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, predicate_=Predicates.incoming_post_notification, **annotations)

    def ws_notification(self, method_: Optional[str] = None, **annotations: type) -> Callable:
        return self.__call__(method_, predicate_=Predicates.incoming_ws_notification, **annotations)
