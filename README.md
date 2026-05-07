# BioCore — Servidor Central

Servidor Flask que recebe leituras dos sensores do ESP32, armazena no banco de dados e distribui os dados em tempo real para o app mobile e o painel web.

## Visão Geral

```
ESP32 (Wi-Fi)  ──────────────────────────────────┐
                                                  ▼
ESP32 (BLE) ──► ponte.py ──► POST /api/leitura ──► Flask ──► SQLite
                                                        │
                                          SSE /api/stream
                                                        │
                                          ┌─────────────┴─────────────┐
                                       App Mobile              Painel Web
```

O ESP32 pode se comunicar com o servidor de duas formas:
- **Wi-Fi direto** — envia HTTP para `/api/leitura`
- **Bluetooth (BLE)** — usa o script `ponte.py` como intermediário

## Tecnologias

| Camada | Tecnologia |
|--------|------------|
| Servidor | Python + Flask 3 |
| Banco de dados | SQLite (WAL mode) |
| Tempo real | Server-Sent Events (SSE) |
| BLE | Bleak 0.21 |

## Estrutura de Arquivos

```
server/
├── app.py              # Ponto de entrada — inicializa o servidor
├── config.py           # Host, porta e caminho do banco
├── database.py         # Criação das tabelas e migrações
├── ponte.py            # Ponte Bluetooth: ESP32 ↔ Flask
├── scan.py             # Utilitário para escanear dispositivos BLE
├── requirements.txt
├── models/
│   ├── leituras.py     # Salva e busca leituras dos sensores
│   └── comandos.py     # Enfileira e consome comandos
├── routes/
│   ├── esp32.py        # Endpoints usados pelo ESP32
│   └── painel.py       # Endpoints usados pelo app e painel web
└── templates/
    └── index.html      # Painel web com SSE e histórico
```

## Banco de Dados

### Tabela `leituras`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INTEGER | Chave primária |
| `dispositivo_id` | TEXT | Identificador do ESP32 |
| `timestamp` | DATETIME | Data e hora da leitura |
| `umidade_solo_bruto` | INTEGER | Valor bruto do sensor de solo |
| `umidade_solo_percent` | REAL | Umidade do solo em % |
| `temperatura` | REAL | Temperatura em °C |
| `umidade_ar` | REAL | Umidade do ar em % |
| `luminosidade_bruto` | INTEGER | Valor bruto do LDR |
| `luminosidade_percent` | REAL | Luminosidade em % |
| `bomba` | INTEGER | Estado da bomba (0 = desligada, 1 = ligada) |

### Tabela `comandos`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INTEGER | Chave primária |
| `dispositivo_id` | TEXT | Identificador do ESP32 de destino |
| `bomba` | INTEGER | Comando para bomba (0/1) ou NULL |
| `luz` | INTEGER | Comando para luz (0/1) ou NULL |
| `criado_em` | DATETIME | Quando o comando foi criado |
| `executado` | INTEGER | 0 = pendente, 1 = executado pelo ESP32 |

## API

### Endpoints do ESP32

#### `POST /api/leitura`
Recebe uma leitura dos sensores.

**Body JSON:**
```json
{
  "dispositivo_id": "esp32-biocore-01",
  "umidade_solo_bruto": 1800,
  "umidade_solo_percent": 62.5,
  "temperatura": 24.3,
  "umidade_ar": 58.0,
  "luminosidade_bruto": 900,
  "luminosidade_percent": 44.0,
  "bomba": false
}
```

**Resposta:** `{"ok": true}` — HTTP 201

---

#### `GET /api/comando?dispositivo_id=esp32-biocore-01`
O ESP32 consulta se há algum comando pendente. Retorna o comando mais recente não executado e o marca como executado.

**Resposta (com comando pendente):**
```json
{"bomba": true}
```
**Resposta (sem comandos):**
```json
{}
```

---

#### `GET /api/stream`
Stream SSE — o app e o painel web se conectam aqui para receber leituras em tempo real. Envia um `keepalive` a cada 25 segundos para manter a conexão ativa.

---

### Endpoints do App / Painel Web

#### `GET /api/leituras`
Retorna as últimas leituras armazenadas.

| Parâmetro | Descrição | Padrão |
|-----------|-----------|--------|
| `dispositivo_id` | Filtra por dispositivo (opcional) | — |
| `limite` | Quantidade de registros (máx 500) | 100 |

**Exemplo:** `/api/leituras?dispositivo_id=esp32-biocore-01&limite=20`

---

#### `POST /api/comando`
Envia um comando para um dispositivo. O ESP32 buscará o comando na próxima chamada a `/api/comando`.

**Body JSON:**
```json
{"dispositivo_id": "esp32-biocore-01", "bomba": true}
{"dispositivo_id": "esp32-biocore-01", "luz": false}
{"dispositivo_id": "esp32-biocore-01", "bomba": true, "luz": false}
```

**Resposta:** `{"ok": true}` — HTTP 201

---

#### `GET /`
Painel web com cards dos sensores em tempo real, controle de bomba e luz, e tabela de histórico de leituras.

## Como Executar

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv venv
source venv/activate        # Linux/macOS
venv\Scripts\activate       # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Iniciar o servidor
python app.py
```

O servidor inicia em `http://0.0.0.0:5001`. O banco de dados `biocore.db` é criado automaticamente na primeira execução.

## Ponte Bluetooth (BLE)

Se o ESP32 não tiver conexão Wi-Fi, use o `ponte.py` para conectar via Bluetooth:

```bash
# Em um terminal: inicie o servidor Flask
python app.py

# Em outro terminal: inicie a ponte BLE
python ponte.py
```

O script escaneia por um dispositivo chamado `BioCore`, conecta via GATT e:
- Recebe leituras do ESP32 → repassa para `POST /api/leitura`
- Verifica comandos pendentes a cada 3 segundos → envia para o ESP32 via BLE

Para listar dispositivos BLE próximos:
```bash
python scan.py
```

## Configuração

Edite `config.py` para alterar host, porta ou caminho do banco:

```python
HOST    = "0.0.0.0"   # escuta em todas as interfaces
PORT    = 5001
DB_PATH = "biocore.db"
```

Para acessar o servidor de fora da rede local, use uma VPN como o **Tailscale** e aponte o app mobile para o IP da VPN.
