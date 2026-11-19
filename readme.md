# Rede SUMAÚMA — Monitoramento Climático e Prevenção de Queimadas (Manaus - AM)

**FIAP · Engenharia de Software · Global Solution 2026.2 · CitizenTech**  
**Integrantes:** André Gonzales Bento, Isabella Rodrigues Afonso, Nicholas Franco Vidal, Richard Henrique Dias dos Santos, Samuel Kayto Takiuchi.

---

## 1. Sobre o Projeto (Ficha CitizenTech)
O **SUMAÚMA** é uma rede comunitária de proteção climática e saúde pública desenvolvida para territórios vulneráveis de Manaus (AM), como comunidades ribeirinhas, áreas de palafitas e aldeias indígenas.

O ecossistema integra **Edge Computing (ESP32)**, **Inteligência de Dados (Python)** e **Interface Web (Painel Comunitário)** em uma arquitetura *Offline-First*:
1. **Sensores na Ponta (ESP32 / Wokwi):** Monitoram continuamente temperatura, umidade, fumaça, chama, taxa de aquecimento e nível do rio, disparando sirene/LEDs locais sem depender de internet.
2. **Orquestração e Inteligência (Python):** Cruza a telemetria do ESP32 com APIs climáticas de Manaus (Open-Meteo), filtra alarmes falsos (diferenciando onda de calor isolada de incêndio real) e envia comandos preventivos de volta ao ESP32 via MQTT.
3. **Alerta Geolocalizado Estilo Defesa Civil (Cell Broadcast):** Calcula a distância geográfica (km) até os moradores cadastrados (fórmula de Haversine) e envia uma mensagem curta com a **Zona Segura** e a **Rota de Fuga** **apenas para quem está dentro do raio de perigo** (3 km para fogo, 8 km para fumaça), evitando pânico e spam em quem mora longe.
4. **Painel Web e Mapa Comunitário (Site):** Recebe via API REST o pacote técnico completo (nível de risco, motivo exato, temperatura, umidade, fumaça, chama e nível do rio) para exibição no site e acompanhamento pelas lideranças e órgãos de resposta.

---

## 2. Arquitetura e Fluxo de Dados

```text
[ESP32 no Wokwi] ──(MQTT / HiveMQ)──► [Python (sumauma2.py)] ──(REST API)──► [Site Web / Mapa]
       ▲                                       │
       └──────────(Comando MQTT)───────────────┴──(Alerta Geolocalizado)───► [Celular do Cidadão]
```

---

## 3. Requisitos e Instalação

* **Python 3.10 ou superior** (necessário para a estrutura `match/case`).
* **Bibliotecas externas:** `paho-mqtt` (comunicação em tempo real com o Wokwi) e `requests` (envio dos dados para a API do site).
* **Conexão com a internet** (opcional: sem internet, o sistema opera 100% pelo sensor local e salva os alertas na fila offline FIFO).

### Passo a passo de instalação (Windows / PowerShell)
Abra o terminal na pasta do projeto (`D:\ESTUDOS FIAP\SUMAUMA_GS`) e instale as dependências no ambiente virtual:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install paho-mqtt requests
```

### Configuração da API do Site (`api_url.txt`)
Garanta que o arquivo `api_url.txt` exista na mesma pasta do código contendo a URL do endpoint de avisos do site:

```powershell
& ".\.venv\Scripts\python.exe" -c "u='https://' + '6afcd2592a9c141d36b7c239' + '.mockapi.io/api/v1/avisos'; open('api_url.txt', 'w').write(u)"
```

---

## 4. Como Executar o Sistema Completo (Wokwi + Python + Site)

Para rodar a demonstração completa em tempo real:

1. **Inicie o Hardware (Wokwi):**
   * Abra o projeto do ESP32 no **Wokwi** e clique em **Play** para iniciar a simulação e conectar ao Wi-Fi/MQTT.
2. **Inicie o Cérebro (Python):**
   * No terminal PowerShell, dentro da pasta do projeto, execute:
   ```powershell
   & ".\.venv\Scripts\python.exe" sumauma2.py
   ```
3. **Ative a Escuta em Tempo Real:**
   * No menu do terminal, digite **`4`** (*Escutar o ESP32 em tempo real (MQTT)*) e aperte **Enter**.
   * Aguarde aparecer: `Conectado ao broker MQTT (rc = Success ). Aguardando telemetria...`
4. **Simule uma Ocorrência e Veja a Integração:**
   * No **Wokwi**, aumente os controles de **fumaça** ou **chama** do sensor.
   * Em até 5 segundos, o **Python** receberá a telemetria, emitirá o bipe de emergência, disparará o alerta geolocalizado com a **Zona Segura** apenas para os moradores próximos e enviará todos os dados técnicos para o **Site**.
   * Atualize o painel web (**https://vercel.app**) para visualizar a ocorrência registrada.

*(Para encerrar a escuta em tempo real e voltar ao menu, aperte `Ctrl + C`).*

---

## 5. Funcionalidades do Menu (`sumauma2.py`)

| Opção | Função | Descrição |
| :---: | :--- | :--- |
| **1** | Verificar sensor pelo arquivo | Lê `leitura_sensor.json` (Plano B caso não esteja usando o Wokwi/MQTT), cruza com a API de clima e processa alertas. |
| **2** | Sincronizar alertas offline | Envia para o site, por ordem de chegada (`FIFO / pop(0)`), todos os alertas acumulados enquanto a internet/API estava fora do ar. |
| **3** | Ver histórico de ocorrências | Lista todas as leituras registradas no arquivo local `sumauma_registro.json` e mostra quantos alertas aguardam na fila. |
| **4** | Escutar o ESP32 em tempo real | Conecta via MQTT (`://hivemq.com`) ao ESP32 no Wokwi, processa telemetria ao vivo, envia comandos de volta à placa, alerta cidadãos próximos e atualiza o site. |
| **0** | Encerrar sistema | Finaliza a execução com segurança. |

---

## 6. Regras de Inteligência e Prevenção de Falsos Positivos

* **Níveis de Risco:** `NORMAL` → `ATENÇÃO` → `ALERTA LARANJA` → `EMERGENCIA CRITICA`.
* **Filtro de Calor Extremo (`CALOR_EXTREMO`):** Se o sensor registrar temperatura alta isolada (ex.: 39 °C sob sol forte) sem fumaça, sem chama e com umidade normal, o Python orienta hidratação e sombra no boletim técnico e **não** dispara evacuação de incêndio nos celulares.
* **Raio de Alcance Geolocalizado (Haversine):**
  * **Fogo / Incêndio Provável ou Confirmado:** Alerta cidadãos em até **3,0 km** do foco.
  * **Fumaça Densa na Região:** Alerta cidadãos em até **8,0 km** do foco.
  * Moradores fora do raio de risco não recebem notificações desnecessárias.

---

## 7. Arquivos do Projeto

| Arquivo | Função |
| :--- | :--- |
| `sumauma2.py` | Código principal do sistema em Python. |
| `api_url.txt` | Guarda a URL da API REST do site (`MockAPI`). |
| `leitura_sensor.json` | Simulação local de telemetria do ESP32 (usada na Opção 1). |
| `sumauma_registro.json` | Banco local com o histórico de ocorrências e a fila offline. *(Apague este arquivo antes de gravar demonstrações para zerar o histórico).* |
| `readme.md` | Documentação técnica e guia de execução. |
| `prompts.md` | Registro transparente do uso de Inteligência Artificial no desenvolvimento. |
