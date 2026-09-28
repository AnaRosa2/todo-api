from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def limpar():
    main.tarefas_db.clear()
    main._gerador_id = __import__("itertools").count(1)
    yield


def criar(titulo, tags=None, descricao=""):
    r = client.post("/tarefas", json={"titulo": titulo, "descricao": descricao, "tags": tags or []})
    assert r.status_code == 201
    return r.json()


def test_criar_tarefa():
    t = criar("Estudar Python", ["python", "estudos"], "Revisar funções")
    assert t["id"] == 1
    assert t["concluida"] is False
    assert t["data_criacao"] == t["data_atualizacao"]
    assert t["tags"] == ["python", "estudos"]


def test_titulo_vazio_retorna_422():
    assert client.post("/tarefas", json={"titulo": "  "}).status_code == 422


def test_consultar_e_404():
    criar("A")
    assert client.get("/tarefas/1").status_code == 200
    assert client.get("/tarefas/99").status_code == 404


def test_atualizar_muda_data_atualizacao():
    t = criar("A")
    main.tarefas_db[1]["data_atualizacao"] = datetime(2020, 1, 1)
    r = client.put("/tarefas/1", json={"titulo": "B", "descricao": "d", "concluida": True, "tags": ["x"]})
    assert r.status_code == 200
    novo = r.json()
    assert novo["titulo"] == "B" and novo["concluida"] is True
    assert novo["data_criacao"] == t["data_criacao"]
    assert novo["data_atualizacao"] != "2020-01-01T00:00:00"
    assert client.put("/tarefas/99", json={"titulo": "B", "concluida": True}).status_code == 404


def test_excluir():
    criar("A")
    assert client.delete("/tarefas/1").status_code == 204
    assert client.delete("/tarefas/1").status_code == 404
    assert client.get("/tarefas").json()["total"] == 0


def test_filtros():
    criar("Estudar Python", ["python", "estudos"])
    criar("Exercícios de Python", ["python"])
    criar("Comprar pão", ["casa"])
    client.put("/tarefas/2", json={"titulo": "Exercícios de Python", "concluida": True, "tags": ["python"]})

    assert client.get("/tarefas?concluida=true").json()["total"] == 1
    assert client.get("/tarefas?concluida=false").json()["total"] == 2
    assert client.get("/tarefas?tag=PYTHON").json()["total"] == 2
    assert client.get("/tarefas?tag=estudos").json()["total"] == 1
    assert client.get("/tarefas?titulo=python").json()["total"] == 2
    assert client.get("/tarefas?concluida=false&tag=python").json()["total"] == 1


def test_ordenacao():
    criar("banana")
    criar("Abacaxi")
    criar("caju")
    titulos = lambda q: [t["titulo"] for t in client.get(f"/tarefas?{q}").json()["tarefas"]]
    assert titulos("ordenar_por=titulo&ordem=asc") == ["Abacaxi", "banana", "caju"]
    assert titulos("ordenar_por=titulo&ordem=desc") == ["caju", "banana", "Abacaxi"]
    assert titulos("ordenar_por=id&ordem=desc") == ["caju", "Abacaxi", "banana"]
    assert client.get("/tarefas?ordenar_por=inexistente").status_code == 422
    assert client.get("/tarefas?ordem=xyz").status_code == 422


def test_ordenar_por_data_criacao():
    for n in "ABC":
        criar(n)
    base = datetime(2026, 9, 1, 10, 0, 0)
    for i, tid in enumerate([3, 1, 2]):
        main.tarefas_db[tid]["data_criacao"] = base + timedelta(days=i)
    ids = lambda o: [t["id"] for t in client.get(f"/tarefas?ordenar_por=data_criacao&ordem={o}").json()["tarefas"]]
    assert ids("asc") == [3, 1, 2]
    assert ids("desc") == [2, 1, 3]


def test_filtro_e_ordenacao_combinados():
    criar("A", ["python"])
    criar("B", ["python"])
    criar("C", ["java"])
    r = client.get("/tarefas?concluida=false&tag=python&ordenar_por=data_criacao&ordem=desc").json()
    assert r["total"] == 2


def test_paginacao():
    for i in range(35):
        criar(f"T{i}")
    r = client.get("/tarefas?pagina=2&limite=10").json()
    assert (r["pagina"], r["limite"], r["total"]) == (2, 10, 35)
    assert [t["id"] for t in r["tarefas"]] == list(range(11, 21))
    assert len(client.get("/tarefas?pagina=4&limite=10").json()["tarefas"]) == 5
    assert client.get("/tarefas?pagina=5&limite=10").json()["tarefas"] == []
    assert client.get("/tarefas?pagina=0").status_code == 422


def test_periodo():
    for n in "ABC":
        criar(n)
    datas = {1: datetime(2026, 8, 31, 23, 59), 2: datetime(2026, 9, 5, 12, 0), 3: datetime(2026, 9, 9, 23, 59)}
    for tid, d in datas.items():
        main.tarefas_db[tid]["data_criacao"] = d
    ids = lambda q: sorted(t["id"] for t in client.get(f"/tarefas?{q}").json()["tarefas"])
    assert ids("data_inicio=2026-09-01&data_fim=2026-09-09") == [2, 3]
    assert ids("data_inicio=2026-09-06") == [3]
    assert ids("data_fim=2026-08-31") == [1]
    assert client.get("/tarefas?data_inicio=2026-09-10&data_fim=2026-09-01").status_code == 400
