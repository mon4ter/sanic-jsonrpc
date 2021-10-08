from asyncio import Future, Queue, ensure_future, iscoroutine, shield
from collections import defaultdict
from typing import Any, AnyStr, Callable, Dict, List, Optional, Type, Union

from fashionable import ArgError, CIStr, Func, ModelAttributeError, ModelError, RetError, UNSET
from ujson import dumps, loads

from .._context import Context
from .._middleware import Objects, Predicates
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

    @staticmethod
    async def _func(func: Func, ctx: Context, *args, **kwargs) -> Any:
        ret = func[ctx.dict](*args, **kwargs)

        if iscoroutine(ret):
            ret = await ret

        return ret

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

    @classmethod
    def _parse_messages(cls, json: AnyStr) -> Union[AnyJsonrpc, List[AnyJsonrpc]]:
        messages = cls._parse_json(json)

        if isinstance(messages, Response):
            return messages

        if isinstance(messages, list):
            if not messages:
                return Response(error=INVALID_REQUEST)

            return [cls._parse_message(m) for m in messages]

        return cls._parse_message(messages)

    @classmethod
    def _serialize(cls, obj: Any) -> str:
        try:
            return dumps(obj)
        except Exception as err:
            error_logger.error("Failed to serialize object %r: %s", obj, err, exc_info=err)
            return cls._serialize(Response(error=INTERNAL_ERROR))

    def _handle_incoming(
            self, ctx: Context, failure_cb: Callable[[Response], None], success_cb: Callable[[Future], None]
    ) -> bool:
        func = self._routes.get((
            ctx.transport,
            ctx.object,
            CIStr(ctx.incoming.method) if self._case_insensitive else ctx.incoming.method,
        ))

        if not func:
            if ctx.object is Objects.request:
                failure_cb(Response(error=METHOD_NOT_FOUND, id=ctx.incoming.id))
            else:
                logger.info("Unhandled %r", ctx.incoming)

            return False

        fut = self._register_call(func, ctx)

        if ctx.object is Objects.request:
            success_cb(fut)

        return True

    def _register_call(self, func: Func, ctx: Context) -> Future:
        fut = shield(self._call(func, ctx))
        self._calls.put_nowait(fut)
        return fut

    async def _run_middlewares(self, ctx: Context):
        for func in self._middlewares[(ctx.direction, ctx.transport, ctx.object)]:
            logger.debug("Calling middleware %r", func.name)
            await self._func(func, ctx)

    async def _call(self, func: Func, ctx: Context) -> Optional[Response]:
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
            params = ctx.incoming.params

            try:
                if params is UNSET:
                    ret = await self._func(func, ctx)
                elif isinstance(params, list):
                    ret = await self._func(func, ctx, *params)
                elif isinstance(params, dict):
                    ret = await self._func(func, ctx, **params)
                else:
                    ret = await self._func(func, ctx, params)
            except RetError as err:
                error_logger.error(err, exc_info=err)
                error = INTERNAL_ERROR
            except ArgError as err:
                logger.debug(err)
                error = INVALID_PARAMS
            except Error as err:
                error = err
            except Exception as exc:
                exc_type = type(exc)
                handler = self._exceptions.get(exc_type)

                if handler:
                    logger.debug("Calling %s handler %r", exc_type, handler.name)

                    try:
                        ret = await self._func(handler, ctx, exc)
                    except Exception as err:
                        error_logger.error(
                            "Recovery from %s while handling %r failed: %s", exc, ctx.incoming, err, exc_info=err
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

    def __init__(self, *, case_insensitive: bool):
        self._middlewares = defaultdict(list)
        self._exceptions = {}
        self._routes = {}
        self._calls = None
        self._case_insensitive = case_insensitive

    def middleware(self, predicate: Union[Predicates, str], name: Optional[str] = None) -> Callable:
        if isinstance(predicate, Callable):
            return self.middleware(Predicates.any)(predicate)

        if isinstance(predicate, str):
            predicate = Predicates[predicate]

        predicate = predicate.value

        def deco(func: Callable) -> Callable:
            func = Func.fashionable(func, name, False, {'return_': Func.empty})
            keys = {
                (d, t, o)
                for d in predicate.directions
                for t in predicate.transports
                for o in predicate.objects
            }

            for key in keys:
                self._middlewares[key].append(func)

            return func
        return deco

    def exception(self, *exceptions: Type[Exception]):
        def deco(func: Callable) -> Callable:
            func = Func.fashionable(func, None, False, {'return_': Func.empty})

            for exception in exceptions:
                self._exceptions[exception] = func

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
            if 'result' in annotations:
                annotations['return_'] = annotations.pop('result')

            func = Func.fashionable(func, method_, self._case_insensitive, annotations)
            self._routes.update({
                (t, o, CIStr(func.name) if self._case_insensitive else func.name): func
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
