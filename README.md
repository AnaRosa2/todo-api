# API de Lista de Tarefas (To-Do)

API REST feita com **FastAPI** para gerenciar tarefas: CRUD completo, filtros por
query parameters, ordenação, paginação e consulta por período.
Os dados ficam em memória (reiniciar o servidor zera as tarefas).

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

- API: http://127.0.0.1:8000
- Documentação interativa (Swagger): http://127.0.0.1:8000/docs

## Testes

```bash
pytest -v
```

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/tarefas` | Cria tarefa (201) |
| GET | `/tarefas` | Lista com filtros, ordenação e paginação |
| GET | `/tarefas/{id}` | Consulta uma tarefa (404 se não existir) |
| PUT | `/tarefas/{id}` | Atualiza uma tarefa (404 se não existir) |
| DELETE | `/tarefas/{id}` | Exclui uma tarefa (204, ou 404 se não existir) |

### Query parameters de `GET /tarefas`

| Parâmetro | Descrição |
|-----------|-----------|
| `concluida` | `true` ou `false` |
| `tag` | tarefas que possuem a tag (ignora maiúsculas/minúsculas) |
| `titulo` | título que contenha o texto (ignora maiúsculas/minúsculas) |
| `data_inicio`, `data_fim` | período de criação, formato `AAAA-MM-DD`, ambos inclusivos |
| `ordenar_por` | `id` (padrão), `titulo`, `data_criacao`, `data_atualizacao` |
| `ordem` | `asc` (padrão) ou `desc` |
| `pagina` | página, mínimo 1 (padrão 1) |
| `limite` | itens por página, de 1 a 100 (padrão 10) |

Todos podem ser combinados, por exemplo:

```
GET /tarefas?concluida=false&tag=python&ordenar_por=data_criacao&ordem=desc&pagina=1&limite=10
GET /tarefas?data_inicio=2026-09-01&data_fim=2026-09-09
```

### Exemplo de resposta da listagem

```json
{
  "pagina": 1,
  "limite": 10,
  "total": 1,
  "tarefas": [
    {
      "id": 1,
      "titulo": "Estudar Python",
      "descricao": "Revisar funções e classes",
      "concluida": false,
      "tags": ["python", "estudos"],
      "data_criacao": "2026-09-09T08:30:00",
      "data_atualizacao": "2026-09-09T08:30:00"
    }
  ]
}
```

## Exemplos com curl

```bash
curl -X POST http://127.0.0.1:8000/tarefas -H "Content-Type: application/json" \
  -d '{"titulo":"Estudar Python","descricao":"Revisar funções e classes","tags":["python","estudos"]}'

curl "http://127.0.0.1:8000/tarefas?tag=python&ordenar_por=titulo&ordem=asc"

curl -X PUT http://127.0.0.1:8000/tarefas/1 -H "Content-Type: application/json" \
  -d '{"titulo":"Estudar FastAPI","descricao":"Rotas e parâmetros","concluida":true,"tags":["python","fastapi"]}'

curl -X DELETE http://127.0.0.1:8000/tarefas/1
```

## Integrantes

- Ana Rosa Pereira Chaves

