"""API FastAPI exposant l'agent RAG LangChain (rag_agent.py) pour PocketBase.

Lancement :uvicorn API_REST:app --host 127.0.0.1 --port 8000 --reload
   

Endpoints principaux :
    GET  /operational                    -> etat de l'API
    POST /chat                      -> pose une question a l'agent {"message": str, "num_tel": str}
    GET  /history/{num_tel}         -> recupere l'historique d'un client
    DELETE /history/{num_tel}       -> reinitialise l'historique d'un client
"""
#%pip install fastapi
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import rag_agent


logger = logging.getLogger(__name__)
startup_error: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global startup_error
    try:
        rag_agent.init_retriever()
        startup_error = None
    except Exception as exc:
        startup_error = str(exc)
        logger.exception("Initialisation retriever impossible au demarrage")
    yield


app = FastAPI(
    title="SISMA Agent API",
    description="API REST exposant l'agent RAG LangChain (rag_agent.py) a destination de PocketBase.",
    version="1.0.0",
    lifespan=lifespan,
)

# A restreindre a l'origine de votre instance PocketBase en production (par exemple telegram ou whatsapp)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str | None = Field(default=None, description="Question posee par l'utilisateur")
    num_tel: str = Field(description="Numero de telephone du client")


class ChatResponse(BaseModel):
    answer: str
  # num_tel: str


class HistoryTurn(BaseModel):
    user: str
    assistant: str


@app.get("/operational", response_model=dict)
def operational():
    """Verifie que l'API et le retriever sont operationnels."""
    return {
        "status": "ok",
        "retriever_ready": rag_agent.retriever is not None,
        "startup_error": startup_error,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Envoie une question a l'agent RAG et retourne sa reponse."""
    question = (request.message or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="La question ne peut pas etre vide (utilisez 'message' ou 'question').")

    if rag_agent.retriever is None:
        try:
            rag_agent.init_retriever()
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Service indisponible: retriever non initialise ({exc})",
            ) from exc

    try:
        answer, _ = rag_agent.ask_rag(question, request.num_tel)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement de la question : {exc}") from exc

    return ChatResponse(answer=answer)


@app.get("/history/{num_tel}", response_model=list[HistoryTurn])
def get_history(num_tel: str):
    """Retourne l'historique de conversation d'une session."""
    return rag_agent.load_conversation_history(num_tel)


@app.delete("/history/{num_tel}")
def delete_history(num_tel: str):
    """Reinitialise l'historique de conversation d'une session."""
    rag_agent.clear_conversation_history(num_tel)
    return {"status": "cleared", "num_tel": num_tel}
