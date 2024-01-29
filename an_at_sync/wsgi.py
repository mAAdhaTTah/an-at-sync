from typing import List

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from an_at_sync.program import Program, ProgramSettings

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
    program = Program(settings=ProgramSettings())

    for result in program.handle_webhook(payload):
        program.write_result(result)

    return {"success": True}


api_router.include_router(webhooks)

wsgi.include_router(api_router)
