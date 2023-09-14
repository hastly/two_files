import pathlib

from srv.handlers import upload, ping, register, status, drop

PROJECT_ROOT = pathlib.Path(__file__).parent.parent


def setup_routes(app):
    app.router.add_post("/ping", ping, name="ping")
    app.router.add_post("/upload/", register, name="register")
    app.router.add_post("/upload/{session_id}", upload, name="upload")
    app.router.add_get("/upload/{session_id}", status, name="status")
    app.router.add_delete("/upload/{session_id}", drop, name="drop")
    setup_static_routes(app)


def setup_static_routes(app):
    app.router.add_static("/static/", path=PROJECT_ROOT / "static", name="static")
