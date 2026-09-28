"""Fixtures compartilhadas pelos testes da API de tarefas."""
import itertools
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

import main


class Relogio:
    """Relógio controlável: substitui main.agora() para deixar as datas previsíveis."""

    def __init__(self, inicio: datetime):
        self.atual = inicio

    def __call__(self) -> datetime:
        return self.atual

    def definir(self, momento: datetime) -> None:
        self.atual = momento

    def avancar(self, **kwargs) -> None:
        self.atual += timedelta(**kwargs)


@pytest.fixture(autouse=True)
def banco_limpo():
    """Zera o "banco" em memória e o contador de ids antes de cada teste."""
    main.tarefas_db.clear()
    main._gerador_id = itertools.count(1)
    yield
    main.tarefas_db.clear()


@pytest.fixture
def client():
    """Instância do TestClient (sem precisar subir servidor)."""
    return TestClient(main.app)


@pytest.fixture
def relogio(monkeypatch):
    """Relógio falso, começando em 01/09/2026 08:00:00."""
    falso = Relogio(datetime(2026, 9, 1, 8, 0, 0))
    monkeypatch.setattr(main, "agora", falso)
    return falso


@pytest.fixture
def criar_tarefa(client):
    """Função auxiliar para criar uma tarefa via API e devolver o JSON."""

    def _criar(titulo="Tarefa de teste", descricao="", tags=None):
        resposta = client.post(
            "/tarefas",
            json={"titulo": titulo, "descricao": descricao, "tags": tags or []},
        )
        assert resposta.status_code == 201
        return resposta.json()

    return _criar


@pytest.fixture
def tarefas_exemplo(client, relogio, criar_tarefa):
    """
    Massa de dados reutilizada nos testes de filtros e ordenação.

    id | título                    | tags             | criada em  | concluída | atualizada em
    1  | Estudar Python            | python, estudos  | 01/09/2026 | não       | 12/09/2026
    2  | Exercícios de Python      | python           | 03/09/2026 | sim       | 10/09/2026
    3  | Comprar pão               | casa             | 05/09/2026 | não       | 05/09/2026
    4  | Projeto final com Java    | java, estudos    | 07/09/2026 | não       | 07/09/2026
    """
    dados = [
        (datetime(2026, 9, 1, 8, 0, 0), "Estudar Python", "Revisar funções", ["python", "estudos"]),
        (datetime(2026, 9, 3, 9, 0, 0), "Exercícios de Python", "Lista 1", ["python"]),
        (datetime(2026, 9, 5, 10, 0, 0), "Comprar pão", "Padaria", ["casa"]),
        (datetime(2026, 9, 7, 11, 0, 0), "Projeto final com Java", "Entrega", ["java", "estudos"]),
    ]
    for momento, titulo, descricao, tags in dados:
        relogio.definir(momento)
        criar_tarefa(titulo, descricao, tags)

    # tarefa 2 vira concluída em 10/09
    relogio.definir(datetime(2026, 9, 10, 10, 0, 0))
    client.put(
        "/tarefas/2",
        json={"titulo": "Exercícios de Python", "descricao": "Lista 1", "concluida": True, "tags": ["python"]},
    )
    # tarefa 1 é editada em 12/09 (continua pendente)
    relogio.definir(datetime(2026, 9, 12, 10, 0, 0))
    client.put(
        "/tarefas/1",
        json={"titulo": "Estudar Python", "descricao": "Revisar funções e classes", "concluida": False, "tags": ["python", "estudos"]},
    )
    return [1, 2, 3, 4]
