import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from rigbook.db import init_db
from rigbook.flrig import router as flrig_router
from rigbook.routes.contacts import router as contacts_router
from rigbook.routes.settings import router as settings_router


class _SuccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return '" 200 ' not in msg and '" 304 ' not in msg


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Rigbook", lifespan=lifespan)

app.include_router(contacts_router)
app.include_router(settings_router)
app.include_router(flrig_router)

static_dir = Path(__file__).parent / "static"
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


def run() -> None:
    logging.getLogger("uvicorn.access").addFilter(_SuccessFilter())
    uvicorn.run("rigbook.main:app", host="0.0.0.0", port=8073)
