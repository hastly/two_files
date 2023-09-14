import os
import pathlib

import aiohttp_jinja2
import jinja2
from loguru import logger
from aiohttp import web
from aiohttp_swagger import setup_swagger

from srv.api import setup_routes
from srv.middleware import setup_middlewares

APP_NAME = "TWO_FILES"
BASE_DIR = pathlib.Path(__file__).parent.parent


def create_app():
    app = web.Application()

    config = {
        "buff_suze": os.environ.get(f"{APP_NAME}_BUFF_SIZE", 10000),
        "lookup_distance": os.environ.get(f"{APP_NAME}_LOOKUP_DISTANCE", 10),
        "similar_threshold": os.environ.get(f"{APP_NAME}_SIMILAR_THRESHOLD", 0.33),
        "output_separator": os.environ.get(f"{APP_NAME}_OUTPUT_SEPARATOR", "=>"),
        "base_path": BASE_DIR,
    }

    app["config"] = config
    app["logger"] = logger
    app["sessions"] = {}

    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(str(BASE_DIR / "tmpl")))
    setup_routes(app)
    setup_middlewares(app)
    setup_swagger(app, swagger_url="//")

    return app


if __name__ == "__main__":
    web.run_app(create_app())
