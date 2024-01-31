from typing import List

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from rq import Queue

from an_at_sync.program import Program, ProgramSettings


def handle_webhook(payload: List[dict]):
    program = Program(settings=ProgramSettings())

    for result in program.handle_webhook(payload):
        program.write_result(result)


wsgi = FastAPI()

wsgi.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")

webhooks = APIRouter(
    prefix="/webhooks",
    tags=["webhook"],
)


@webhooks.post("/actionnetwork")
def actionnetwork(payload: List[dict]):
    settings = ProgramSettings()
    q = Queue(connection=Redis.from_url(settings.redis_url))
    q.enqueue(handle_webhook, payload)

    return {"success": True}


api_router.include_router(webhooks)

wsgi.include_router(api_router)
