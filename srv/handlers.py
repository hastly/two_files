import asyncio
from datetime import datetime
from enum import Enum
from functools import wraps
from uuid import uuid4, UUID
from aiohttp import web
from aiohttp.web_exceptions import (
    HTTPNotFound,
    HTTPGone,
    HTTPFound,
    HTTPConflict,
    HTTPBadRequest,
    HTTPServerError,
)
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from srv.process import process


class SessionStatus(Enum):
    complete = "Result file ready"
    open = "Session is idle, waiting for 2 files"
    wait = "Session waiting for second file"
    process = "Session processing both files"
    expired = "Session expired"
    failed = "Session finished with error"


def check_session(func):
    @wraps(func)
    async def wrapped(request, *args, **kwargs):
        session_id = UUID(request.match_info["session_id"])
        session = request.app["sessions"].get(session_id, None)
        if session is None:
            raise HTTPNotFound
        if (
            session["status"] == SessionStatus.expired
            or (datetime.now() - session["open_at"]).total_seconds() > 3600
        ):
            session["status"] = SessionStatus.expired
            raise HTTPGone
        return await func(request, {"id": session_id, "data": session}, *args, **kwargs)

    return wrapped


async def ping(_: Request) -> Response:
    """
    ---
    description: This end-point allow to test that service is up.
    tags:
    - Health check
    produces:
    - text/plain
    responses:
        "200":
            description: successful operation. Return "pong" text
    """
    return web.Response(text="pong")


async def register(request: Request) -> Response:
    """
    ---
    description: Start session to upload two files and get status and comparison result
    tags:
    - Session
    produces:
    - text/plain
    responses:
        "200":
            description: successful operation. Returns session_id to use in query chain
    """
    session_id = uuid4()
    request.app["sessions"][session_id] = {
        "status": SessionStatus.open,
        "open_at": datetime.now(),
    }
    return web.Response(text=f"{session_id.hex}")


@check_session
async def status(_: Request, session):
    """
    ---
    description: Indicate status of the session
    tags:
    - Session
    produces:
    - text/plain
    responses:
        "200":
            description: success. Wait for result
        "302":
            description: success. Redirects to result static file download URL
        "404":
            description: failure. Session not found
        "410":
            description: failure. Session expired
    """
    if session["data"]["status"] == SessionStatus.complete:
        raise HTTPFound(location=session["data"]["url"])
    return web.Response(text=f"{session['data']['status']}")


@check_session
async def drop(request: Request, session) -> Response:
    """
    ---
    description: Indicate status of the session
    tags:
    - Session
    produces:
    - text/plain
    responses:
        "200":
            description: success. Deleted
        "404":
            description: failure. Session not found
    """
    del request.app["sessions"][session["id"]]
    return web.Response()


@check_session
async def upload(request, session):
    """
    ---
    description: Upload one of two files in the frames of designated session
    tags:
    - Session
    produces:
    - text/plain
    responses:
        "200":
            description: success. File accepted
        "404":
            description: failure. Session not found
        "409":
            description: failure. Session already processing/processed two files
        "410":
            description: failure. Session expired
    """

    async def start_process(data_left, meta_data):
        """
        wrapper to provide contents of the both independently uploaded files to process
        :param data_left: record with filename and iterator through the first file content
        :param meta_data: iterator through the first file content
        :return: processing task
        """
        ev = asyncio.Event()
        meta_data["waiter"] = ev

        async def waiter():
            await ev.wait()

        yield asyncio.create_task(waiter())
        data_right = yield
        yield asyncio.create_task(process(data_left, data_right, meta_data))

    open_at = session["data"]["open_at"]
    if session["data"]["status"] not in (SessionStatus.open, SessionStatus.wait):
        raise HTTPConflict

    meta = {
        "open_at": open_at,
        "session_id": session["id"],
        "output_path": request.app["config"]["base_path"] / "static/output",
        "buff_size": request.app["config"]["buff_suze"],
        "lookup_distance": request.app["config"]["lookup_distance"],
        "similar_threshold": request.app["config"]["similar_threshold"],
        "output_separator": request.app["config"]["output_separator"],
    }

    file_url = None

    is_first = session["data"]["status"] == SessionStatus.open
    # reader = name = result = None
    body_reader = await request.multipart()
    async for field in body_reader:
        if field.name == "file":
            reader = field
            name = field.filename

            if reader is None:
                raise HTTPBadRequest

            data = {
                "reader": reader,
                "file_name": name,
            }

            if is_first:
                session["data"]["status"] = SessionStatus.wait
                gen = start_process(data, meta)
                session["data"]["start_process"] = gen
                res = await anext(gen)
                await asyncio.wait_for(res, timeout=600)
            else:
                session["data"]["status"] = SessionStatus.process
                gen = session["data"]["start_process"]
                await anext(gen)
                process_task = await gen.asend(data)
                file_url = await asyncio.wait_for(process_task, timeout=600)

            break
    if is_first:
        return web.Response(status=201, reason="OK", text="First file OK")
    if file_url is not None:
        session["data"]["status"] = SessionStatus.complete
        session["data"]["url"] = file_url
        return web.Response(status=201, reason="OK", text="Second file OK")
    else:
        session["data"]["status"] = SessionStatus.failed
        return HTTPServerError
