"""Testes automatizados da API de tarefas (To-Do) com Pytest e TestClient."""
from datetime import datetime

CAMPOS = {"id", "titulo", "descricao", "concluida", "tags", "data_criacao", "data_atualizacao"}


def ids_da(client, query=""):
    """Faz GET /tarefas e devolve só a lista de ids, na ordem retornada."""
    resposta = client.get(f"/tarefas?{query}")
    assert resposta.status_code == 200
    return [t["id"] for t in resposta.json()["tarefas"]]


# ===========================================================================
# 3.1 Criação de tarefas (POST /tarefas)
# ===========================================================================
def test_criar_tarefa_com_dados_validos(client):
    resposta = client.post(
        "/tarefas",
        json={"titulo": "Estudar Python", "descricao": "Revisar funções e classes", "tags": ["python", "estudos"]},
    )
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["titulo"] == "Estudar Python"
    assert corpo["descricao"] == "Revisar funções e classes"
    assert corpo["tags"] == ["python", "estudos"]


def test_tarefa_criada_possui_campos_obrigatorios(client):
    corpo = client.post("/tarefas", json={"titulo": "A", "descricao": "B", "tags": ["x"]}).json()
    assert set(corpo.keys()) == CAMPOS


def test_id_da_tarefa_e_gerado_automaticamente(client, criar_tarefa):
    primeira = criar_tarefa("Primeira")
    segunda = criar_tarefa("Segunda")
    assert isinstance(primeira["id"], int)
    assert primeira["id"] != segunda["id"]
    assert segunda["id"] == primeira["id"] + 1


def test_tarefa_e_criada_com_concluida_false(client):
    # mesmo que o cliente tente enviar concluida=true, a API deve ignorar
    corpo = client.post("/tarefas", json={"titulo": "A", "concluida": True}).json()
    assert corpo["concluida"] is False


def test_datas_de_criacao_e_atualizacao_sao_preenchidas_automaticamente(client, relogio):
    corpo = client.post("/tarefas", json={"titulo": "A"}).json()
    esperado = relogio.atual.isoformat()
    assert corpo["data_criacao"] == esperado
    assert corpo["data_atualizacao"] == esperado


def test_criar_tarefa_com_varias_tags(client):
    tags = ["python", "fastapi", "backend", "estudos"]
    corpo = client.post("/tarefas", json={"titulo": "A", "tags": tags}).json()
    assert corpo["tags"] == tags


def test_criar_tarefa_sem_titulo_retorna_422(client):
    resposta = client.post("/tarefas", json={"descricao": "sem título", "tags": []})
    assert resposta.status_code == 422


def test_criar_tarefa_com_titulo_vazio_retorna_422(client):
    assert client.post("/tarefas", json={"titulo": "   "}).status_code == 422
    assert client.post("/tarefas", json={"titulo": ""}).status_code == 422


# ===========================================================================
# 3.2 Consulta de tarefas (GET /tarefas e GET /tarefas/{id})
# ===========================================================================
def test_listar_tarefas_retorna_lista_vazia_quando_nao_ha_tarefas(client):
    resposta = client.get("/tarefas")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["tarefas"] == []
    assert corpo["total"] == 0


def test_listar_tarefas_retorna_todas_as_tarefas_cadastradas(client, tarefas_exemplo):
    corpo = client.get("/tarefas").json()
    assert sorted(t["id"] for t in corpo["tarefas"]) == tarefas_exemplo


def test_cada_tarefa_da_listagem_possui_os_campos_esperados(client, tarefas_exemplo):
    for tarefa in client.get("/tarefas").json()["tarefas"]:
        assert set(tarefa.keys()) == CAMPOS


def test_quantidade_de_tarefas_retornadas_corresponde_as_cadastradas(client, criar_tarefa):
    for i in range(3):
        criar_tarefa(f"Tarefa {i}")
    corpo = client.get("/tarefas").json()
    assert len(corpo["tarefas"]) == 3
    assert corpo["total"] == 3


def test_consultar_tarefa_existente(client, criar_tarefa):
    criada = criar_tarefa("Estudar", "Descrição", ["python"])
    resposta = client.get(f"/tarefas/{criada['id']}")
    assert resposta.status_code == 200


def test_tarefa_consultada_possui_os_dados_corretos(client, criar_tarefa):
    criada = criar_tarefa("Estudar", "Descrição", ["python"])
    corpo = client.get(f"/tarefas/{criada['id']}").json()
    assert corpo == criada


def test_consultar_tarefa_inexistente_retorna_404(client):
    resposta = client.get("/tarefas/999")
    assert resposta.status_code == 404
    assert "não encontrada" in resposta.json()["detail"]


def test_paginacao_retorna_pagina_limite_e_total(client, criar_tarefa):
    for i in range(25):
        criar_tarefa(f"Tarefa {i}")
    corpo = client.get("/tarefas?pagina=2&limite=10").json()
    assert (corpo["pagina"], corpo["limite"], corpo["total"]) == (2, 10, 25)
    assert [t["id"] for t in corpo["tarefas"]] == list(range(11, 21))
    ultima = client.get("/tarefas?pagina=3&limite=10").json()
    assert len(ultima["tarefas"]) == 5


# ===========================================================================
# 3.3 Atualização de tarefas (PUT /tarefas/{id})
# ===========================================================================
def test_atualizar_titulo_e_descricao(client, criar_tarefa):
    criada = criar_tarefa("Antigo", "Desc antiga", ["a"])
    resposta = client.put(
        f"/tarefas/{criada['id']}",
        json={"titulo": "Novo", "descricao": "Desc nova", "concluida": False, "tags": ["a"]},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["titulo"] == "Novo"
    assert corpo["descricao"] == "Desc nova"
    assert client.get(f"/tarefas/{criada['id']}").json()["titulo"] == "Novo"


def test_alterar_tarefa_de_pendente_para_concluida(client, criar_tarefa):
    criada = criar_tarefa("A")
    assert criada["concluida"] is False
    corpo = client.put(
        f"/tarefas/{criada['id']}",
        json={"titulo": "A", "descricao": "", "concluida": True, "tags": []},
    ).json()
    assert corpo["concluida"] is True


def test_atualizar_tags_da_tarefa(client, criar_tarefa):
    criada = criar_tarefa("A", tags=["python"])
    corpo = client.put(
        f"/tarefas/{criada['id']}",
        json={"titulo": "A", "descricao": "", "concluida": False, "tags": ["fastapi", "backend"]},
    ).json()
    assert corpo["tags"] == ["fastapi", "backend"]


def test_atualizar_modifica_data_atualizacao(client, relogio, criar_tarefa):
    criada = criar_tarefa("A")
    relogio.definir(datetime(2026, 9, 2, 15, 30, 0))
    corpo = client.put(
        f"/tarefas/{criada['id']}",
        json={"titulo": "B", "descricao": "", "concluida": False, "tags": []},
    ).json()
    assert corpo["data_atualizacao"] != criada["data_atualizacao"]
    assert corpo["data_atualizacao"] == "2026-09-02T15:30:00"


def test_atualizar_nao_altera_data_criacao(client, relogio, criar_tarefa):
    criada = criar_tarefa("A")
    relogio.definir(datetime(2026, 9, 2, 15, 30, 0))
    corpo = client.put(
        f"/tarefas/{criada['id']}",
        json={"titulo": "B", "descricao": "", "concluida": True, "tags": []},
    ).json()
    assert corpo["data_criacao"] == criada["data_criacao"]


def test_atualizar_tarefa_inexistente_retorna_404(client):
    resposta = client.put(
        "/tarefas/999",
        json={"titulo": "X", "descricao": "", "concluida": False, "tags": []},
    )
    assert resposta.status_code == 404


# ===========================================================================
# 3.4 Exclusão de tarefas (DELETE /tarefas/{id})
# ===========================================================================
def test_excluir_tarefa_existente(client, criar_tarefa):
    criada = criar_tarefa("A")
    resposta = client.delete(f"/tarefas/{criada['id']}")
    assert resposta.status_code == 204


def test_exclusao_retorna_204_sem_conteudo(client, criar_tarefa):
    criada = criar_tarefa("A")
    resposta = client.delete(f"/tarefas/{criada['id']}")
    assert resposta.status_code == 204
    assert resposta.content == b""


def test_tarefa_excluida_deixa_de_aparecer_na_listagem(client, tarefas_exemplo):
    client.delete("/tarefas/3")
    ids = ids_da(client)
    assert 3 not in ids
    assert len(ids) == 3


def test_consultar_tarefa_excluida_retorna_404(client, criar_tarefa):
    criada = criar_tarefa("A")
    client.delete(f"/tarefas/{criada['id']}")
    assert client.get(f"/tarefas/{criada['id']}").status_code == 404


def test_excluir_tarefa_inexistente_retorna_404(client):
    assert client.delete("/tarefas/999").status_code == 404


def test_excluir_a_mesma_tarefa_duas_vezes_retorna_404_na_segunda(client, criar_tarefa):
    criada = criar_tarefa("A")
    assert client.delete(f"/tarefas/{criada['id']}").status_code == 204
    assert client.delete(f"/tarefas/{criada['id']}").status_code == 404


# ===========================================================================
# 4. Filtros (GET /tarefas?...)
# ===========================================================================
def test_filtrar_tarefas_concluidas(client, tarefas_exemplo):
    corpo = client.get("/tarefas?concluida=true").json()
    assert [t["id"] for t in corpo["tarefas"]] == [2]
    assert all(t["concluida"] is True for t in corpo["tarefas"])


def test_filtrar_tarefas_pendentes(client, tarefas_exemplo):
    corpo = client.get("/tarefas?concluida=false").json()
    assert sorted(t["id"] for t in corpo["tarefas"]) == [1, 3, 4]
    assert all(t["concluida"] is False for t in corpo["tarefas"])


def test_filtrar_concluidas_sem_resultados(client, criar_tarefa):
    criar_tarefa("Pendente")
    corpo = client.get("/tarefas?concluida=true").json()
    assert corpo["tarefas"] == []
    assert corpo["total"] == 0


def test_filtrar_tarefas_por_tag(client, tarefas_exemplo):
    corpo = client.get("/tarefas?tag=python").json()
    assert sorted(t["id"] for t in corpo["tarefas"]) == [1, 2]
    assert all("python" in t["tags"] for t in corpo["tarefas"])


def test_filtrar_tarefas_por_outra_tag(client, tarefas_exemplo):
    assert sorted(ids_da(client, "tag=estudos")) == [1, 4]


def test_filtrar_por_tag_ignora_maiusculas_e_minusculas(client, tarefas_exemplo):
    assert sorted(ids_da(client, "tag=PYTHON")) == [1, 2]


def test_filtrar_por_tag_sem_resultados(client, tarefas_exemplo):
    corpo = client.get("/tarefas?tag=inexistente").json()
    assert corpo["tarefas"] == []
    assert corpo["total"] == 0


def test_filtrar_tarefas_por_titulo(client, tarefas_exemplo):
    corpo = client.get("/tarefas?titulo=python").json()
    assert sorted(t["id"] for t in corpo["tarefas"]) == [1, 2]
    assert all("python" in t["titulo"].lower() for t in corpo["tarefas"])


def test_filtrar_por_titulo_aceita_correspondencia_parcial(client, tarefas_exemplo):
    assert ids_da(client, "titulo=final") == [4]


def test_filtrar_por_titulo_ignora_maiusculas_e_minusculas(client, tarefas_exemplo):
    assert sorted(ids_da(client, "titulo=PYTHON")) == [1, 2]


def test_filtrar_por_titulo_sem_resultados(client, tarefas_exemplo):
    corpo = client.get("/tarefas?titulo=rust").json()
    assert corpo["tarefas"] == []
    assert corpo["total"] == 0


def test_filtrar_por_periodo(client, tarefas_exemplo):
    # tarefas criadas em 01/09, 03/09, 05/09 e 07/09
    assert sorted(ids_da(client, "data_inicio=2026-09-02&data_fim=2026-09-05")) == [2, 3]


def test_filtro_de_periodo_inclui_os_dias_das_pontas(client, tarefas_exemplo):
    assert sorted(ids_da(client, "data_inicio=2026-09-01&data_fim=2026-09-07")) == [1, 2, 3, 4]


def test_filtrar_por_periodo_sem_resultados(client, tarefas_exemplo):
    assert ids_da(client, "data_inicio=2026-10-01&data_fim=2026-10-31") == []


def test_filtrar_por_periodo_invalido_retorna_400(client, tarefas_exemplo):
    resposta = client.get("/tarefas?data_inicio=2026-09-10&data_fim=2026-09-01")
    assert resposta.status_code == 400


# ===========================================================================
# 4.1 Combinação de filtros
# ===========================================================================
def test_combinar_filtros_concluida_e_tag(client, tarefas_exemplo):
    corpo = client.get("/tarefas?concluida=false&tag=python").json()
    assert [t["id"] for t in corpo["tarefas"]] == [1]
    assert all(t["concluida"] is False and "python" in t["tags"] for t in corpo["tarefas"])


def test_combinar_filtros_sem_resultados(client, tarefas_exemplo):
    # a única tarefa concluída (id 2) não tem a tag java
    assert ids_da(client, "concluida=true&tag=java") == []


def test_combinar_filtros_com_ordenacao(client, tarefas_exemplo):
    corpo = client.get(
        "/tarefas?concluida=false&tag=estudos&ordenar_por=data_criacao&ordem=desc"
    ).json()
    assert [t["id"] for t in corpo["tarefas"]] == [4, 1]
    assert all(t["concluida"] is False and "estudos" in t["tags"] for t in corpo["tarefas"])


def test_combinar_filtro_de_titulo_e_periodo(client, tarefas_exemplo):
    assert ids_da(client, "titulo=python&data_inicio=2026-09-02&data_fim=2026-09-30") == [2]


# ===========================================================================
# 5. Ordenação
# ===========================================================================
def test_ordenar_tarefas_por_data_criacao_asc(client, tarefas_exemplo):
    assert ids_da(client, "ordenar_por=data_criacao&ordem=asc") == [1, 2, 3, 4]


def test_ordenar_tarefas_por_data_criacao_desc(client, tarefas_exemplo):
    assert ids_da(client, "ordenar_por=data_criacao&ordem=desc") == [4, 3, 2, 1]


def test_ordenar_tarefas_por_data_atualizacao_asc(client, tarefas_exemplo):
    # atualizações: t3=05/09, t4=07/09, t2=10/09, t1=12/09
    assert ids_da(client, "ordenar_por=data_atualizacao&ordem=asc") == [3, 4, 2, 1]


def test_ordenar_tarefas_por_data_atualizacao_desc(client, tarefas_exemplo):
    assert ids_da(client, "ordenar_por=data_atualizacao&ordem=desc") == [1, 2, 4, 3]


def test_ordenar_tarefas_por_titulo_asc(client, tarefas_exemplo):
    # Comprar pão, Estudar Python, Exercícios de Python, Projeto final com Java
    assert ids_da(client, "ordenar_por=titulo&ordem=asc") == [3, 1, 2, 4]


def test_ordenar_tarefas_por_titulo_desc(client, tarefas_exemplo):
    assert ids_da(client, "ordenar_por=titulo&ordem=desc") == [4, 2, 1, 3]


def test_ordenar_tarefas_por_id_asc(client, tarefas_exemplo):
    assert ids_da(client, "ordenar_por=id&ordem=asc") == [1, 2, 3, 4]


def test_ordenar_tarefas_por_id_desc(client, tarefas_exemplo):
    assert ids_da(client, "ordenar_por=id&ordem=desc") == [4, 3, 2, 1]


def test_ordenacao_padrao_e_por_id_crescente(client, tarefas_exemplo):
    assert ids_da(client) == [1, 2, 3, 4]


# ===========================================================================
# 6. Validação e tratamento de erros
# ===========================================================================
def test_erro_ao_criar_tarefa_sem_titulo(client):
    resposta = client.post("/tarefas", json={"descricao": "x"})
    assert resposta.status_code == 422
    erros = resposta.json()["detail"]
    assert any("titulo" in erro["loc"] for erro in erros)


def test_erro_ao_consultar_tarefa_inexistente(client):
    resposta = client.get("/tarefas/12345")
    assert resposta.status_code == 404
    assert "detail" in resposta.json()


def test_erro_ao_atualizar_tarefa_inexistente(client):
    resposta = client.put(
        "/tarefas/12345",
        json={"titulo": "X", "descricao": "", "concluida": False, "tags": []},
    )
    assert resposta.status_code == 404
    assert "detail" in resposta.json()


def test_erro_ao_excluir_tarefa_inexistente(client):
    resposta = client.delete("/tarefas/12345")
    assert resposta.status_code == 404
    assert "detail" in resposta.json()


def test_erro_ao_enviar_texto_no_campo_concluida(client, criar_tarefa):
    criada = criar_tarefa("A")
    resposta = client.put(
        f"/tarefas/{criada['id']}",
        json={"titulo": "A", "descricao": "", "concluida": "talvez", "tags": []},
    )
    assert resposta.status_code == 422
    assert any("concluida" in erro["loc"] for erro in resposta.json()["detail"])


def test_erro_ao_enviar_tags_com_tipo_invalido(client):
    resposta = client.post("/tarefas", json={"titulo": "A", "tags": "python"})
    assert resposta.status_code == 422


def test_erro_ao_enviar_titulo_com_tipo_invalido(client):
    resposta = client.post("/tarefas", json={"titulo": 123})
    assert resposta.status_code == 422


def test_erro_ao_atualizar_sem_titulo(client, criar_tarefa):
    criada = criar_tarefa("A")
    resposta = client.put(f"/tarefas/{criada['id']}", json={"concluida": True})
    assert resposta.status_code == 422


def test_erro_ao_consultar_id_que_nao_e_numero(client):
    assert client.get("/tarefas/abc").status_code == 422


def test_erro_com_valor_invalido_no_filtro_concluida(client):
    assert client.get("/tarefas?concluida=talvez").status_code == 422


def test_erro_com_campo_de_ordenacao_invalido(client):
    assert client.get("/tarefas?ordenar_por=inexistente").status_code == 422


def test_erro_com_ordem_invalida(client):
    assert client.get("/tarefas?ordenar_por=titulo&ordem=cima").status_code == 422


def test_erro_com_data_em_formato_invalido(client):
    assert client.get("/tarefas?data_inicio=09-09-2026").status_code == 422


def test_erro_com_paginacao_invalida(client):
    assert client.get("/tarefas?pagina=0").status_code == 422
    assert client.get("/tarefas?limite=0").status_code == 422
