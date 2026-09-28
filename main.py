from datetime import date, datetime
from itertools import count
from threading import Lock
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, field_validator

app = FastAPI(
    title="API de Lista de Tarefas (To-Do)",
    description="API REST para gerenciamento de tarefas com filtros, ordenação, paginação e consulta por período.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# "Banco de dados" em memória
# ---------------------------------------------------------------------------
tarefas_db: dict[int, dict] = {}
_gerador_id = count(1)
_lock = Lock()


def agora() -> datetime:
    return datetime.now().replace(microsecond=0)


# ---------------------------------------------------------------------------
# Modelos (schemas)
# ---------------------------------------------------------------------------
def _limpar_tags(tags: list[str]) -> list[str]:
    vistas: set[str] = set()
    resultado: list[str] = []
    for tag in tags:
        tag = tag.strip()
        if tag and tag.lower() not in vistas:
            vistas.add(tag.lower())
            resultado.append(tag)
    return resultado


class TarefaCriar(BaseModel):
    titulo: str = Field(..., min_length=1, examples=["Estudar Python"])
    descricao: str = Field("", examples=["Revisar funções e classes"])
    tags: list[str] = Field(default_factory=list, examples=[["python", "estudos"]])

    @field_validator("titulo")
    @classmethod
    def titulo_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("O título não pode ser vazio.")
        return v

    @field_validator("tags")
    @classmethod
    def normalizar_tags(cls, v: list[str]) -> list[str]:
        return _limpar_tags(v)


class TarefaAtualizar(BaseModel):
    titulo: str = Field(..., min_length=1)
    descricao: str = ""
    concluida: bool
    tags: list[str] = Field(default_factory=list)

    @field_validator("titulo")
    @classmethod
    def titulo_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("O título não pode ser vazio.")
        return v

    @field_validator("tags")
    @classmethod
    def normalizar_tags(cls, v: list[str]) -> list[str]:
        return _limpar_tags(v)


class Tarefa(BaseModel):
    id: int
    titulo: str
    descricao: str
    concluida: bool
    tags: list[str]
    data_criacao: datetime
    data_atualizacao: datetime


class ListaTarefas(BaseModel):
    pagina: int
    limite: int
    total: int
    tarefas: list[Tarefa]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/tarefas", response_model=Tarefa, status_code=status.HTTP_201_CREATED)
def criar_tarefa(dados: TarefaCriar):
    """Cria uma tarefa. id, concluida, data_criacao e data_atualizacao são automáticos."""
    with _lock:
        novo_id = next(_gerador_id)
        momento = agora()
        tarefa = {
            "id": novo_id,
            "titulo": dados.titulo,
            "descricao": dados.descricao,
            "concluida": False,
            "tags": dados.tags,
            "data_criacao": momento,
            "data_atualizacao": momento,
        }
        tarefas_db[novo_id] = tarefa
    return tarefa


@app.get("/tarefas", response_model=ListaTarefas)
def listar_tarefas(
    concluida: Optional[bool] = Query(None, description="Filtra por situação (true/false)"),
    tag: Optional[str] = Query(None, description="Filtra por tag (sem diferenciar maiúsculas)"),
    titulo: Optional[str] = Query(None, description="Filtra títulos que contenham o texto"),
    data_inicio: Optional[date] = Query(None, description="Criadas a partir desta data (AAAA-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Criadas até esta data, inclusive (AAAA-MM-DD)"),
    ordenar_por: Literal["id", "titulo", "data_criacao", "data_atualizacao"] = Query("id"),
    ordem: Literal["asc", "desc"] = Query("asc"),
    pagina: int = Query(1, ge=1, description="Número da página"),
    limite: int = Query(10, ge=1, le=100, description="Tarefas por página"),
):
    """Lista tarefas com filtros combináveis, ordenação e paginação."""
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="data_inicio não pode ser posterior a data_fim.",
        )

    resultado = list(tarefas_db.values())

    if concluida is not None:
        resultado = [t for t in resultado if t["concluida"] == concluida]

    if tag:
        alvo = tag.strip().lower()
        resultado = [t for t in resultado if alvo in (x.lower() for x in t["tags"])]

    if titulo:
        trecho = titulo.strip().lower()
        resultado = [t for t in resultado if trecho in t["titulo"].lower()]

    if data_inicio:
        resultado = [t for t in resultado if t["data_criacao"].date() >= data_inicio]

    if data_fim:
        resultado = [t for t in resultado if t["data_criacao"].date() <= data_fim]

    if ordenar_por == "titulo":
        chave = lambda t: t["titulo"].lower()
    else:
        chave = lambda t: t[ordenar_por]
    resultado.sort(key=chave, reverse=(ordem == "desc"))

    total = len(resultado)
    inicio = (pagina - 1) * limite
    return {
        "pagina": pagina,
        "limite": limite,
        "total": total,
        "tarefas": resultado[inicio : inicio + limite],
    }


def _buscar_ou_404(id: int) -> dict:
    tarefa = tarefas_db.get(id)
    if tarefa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarefa com id {id} não encontrada.",
        )
    return tarefa


@app.get("/tarefas/{id}", response_model=Tarefa)
def consultar_tarefa(id: int):
    return _buscar_ou_404(id)


@app.put("/tarefas/{id}", response_model=Tarefa)
def atualizar_tarefa(id: int, dados: TarefaAtualizar):
    with _lock:
        tarefa = _buscar_ou_404(id)
        tarefa.update(
            titulo=dados.titulo,
            descricao=dados.descricao,
            concluida=dados.concluida,
            tags=dados.tags,
            data_atualizacao=agora(),
        )
    return tarefa


@app.delete("/tarefas/{id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_tarefa(id: int):
    with _lock:
        _buscar_ou_404(id)
        del tarefas_db[id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)
