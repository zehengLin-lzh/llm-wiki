"""WebSocket chat endpoint for querying the wiki."""

from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.query_engine import QueryEngine
from app.llm.router import ProviderRouter

log = structlog.get_logger()

router = APIRouter(tags=["chat"])

_query_engine: QueryEngine | None = None
_provider_router: ProviderRouter | None = None


def init_chat_router(query_engine: QueryEngine, provider_router: ProviderRouter) -> None:
    global _query_engine, _provider_router
    _query_engine = query_engine
    _provider_router = provider_router


@router.websocket("/ws/chat")
async def chat_ws(ws: WebSocket):
    await ws.accept()
    log.info("chat.connected")

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "data": "Invalid JSON"})
                continue

            if msg.get("type") != "user_message":
                continue

            content = msg.get("content", "").strip()
            if not content:
                continue

            history = msg.get("history", [])
            provider = await _provider_router.get_provider()

            log.info("chat.query", content=content[:80], provider=provider.name)

            async for event in _query_engine.query(content, history, provider):
                await ws.send_json(event.to_dict())

    except WebSocketDisconnect:
        log.info("chat.disconnected")
    except Exception as e:
        log.error("chat.error", error=str(e))
        try:
            await ws.send_json({"type": "error", "data": str(e)})
        except Exception:
            pass
