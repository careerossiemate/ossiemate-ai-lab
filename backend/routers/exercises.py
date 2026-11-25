"""Draft exercise routes; live execution is disabled until cloud validation."""
import os
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from shared.user_authorization import require_authorised_user
from shared.controlled_execution import execute

router = APIRouter(prefix="/api/lab")

class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    profile: Literal["standard", "advanced"] = "standard"
    conversation_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")

@router.get("/capabilities")
def capabilities(user=Depends(require_authorised_user)):
    return {"03": os.getenv("LIVE_CHAT_ENABLED", "false").lower() == "true",
            "04": False, "05": False, "06": False, "AG01": False, "AG02": False, "AG03": False, "AG04": False, "AG05": False, "AG06": False, "AG07": False, "AG08": False, "AG09": False, "AG10": False, "LG01": False, "LG02": False, "LG03": False, "LG04": False, "LG05": False, "LG06": False, "LG07": False, "VS01": False, "VS02": False, "VS03": False, "VS04": False, "VS05": False, "VS06": False, "VS07": False, "VS08": False}

@router.post("/03/run")
def run_chat(body: ChatRequest, user=Depends(require_authorised_user)):
    if os.getenv("LIVE_CHAT_ENABLED", "false").lower() != "true":
        raise HTTPException(503, "Live chat awaits cloud validation.")
    try:
        return execute(user, body.prompt, body.profile, body.conversation_id)
    except ValueError as exc:
        raise HTTPException(400, "Invalid chat request.") from exc
