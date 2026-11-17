Estou desenvolvendo um projeto acadêmico em Python chamado **SUMAÚMA** (Rede comunitária de saúde e prevenção climática em Manaus), para o desafio Global Solution (CitizenTech - 1º ano de Engenharia de Software da FIAP).

Sou iniciante em programação, então preciso que você:
1. Me ajude a terminar este código passo a passo, explicando cada nova linha de forma bem simples e didática.
2. **Restrição obrigatória:** Use APENAS recursos básicos e nativos do Python vistos na ementa da disciplina (variáveis, constantes, f-strings, if/elif/else, match/case, while, for, funções com parâmetros e return, listas — incluindo fila com append e pop(0) —, tuplas, dicionários, arquivos JSON e try/except). Não use bibliotecas externas instaladas via pip (como requests ou pandas).

### O que o programa precisa fazer:
- **Integração com Edge Computing (ESP32):** Ler automaticamente um arquivo JSON local (`leitura_sensor.json`) que simula os sensores de temperatura, umidade e fumaça tóxica (0 a 100 ppm), sem que o morador precise digitar valores técnicos.
- **Previsão de risco via API + Modo Offline:** Consultar uma API gratuita de clima (Open-Meteo, usando a biblioteca nativa `urllib.request`) para Manaus. Se não houver internet, capturar o erro com `try/except` e operar 100% offline usando apenas os dados locais.
- **Alertas estilo Defesa Civil:** Calcular o risco automaticamente e disparar na tela um aviso de emergência (com bipe sonoro `\a`) orientando os meios de proteção contra fumaça densa/tóxica (máscara PFF2/pano úmido, andar abaixado, vedar frestas) e indicando o abrigo seguro e a rota de fuga daquele território.
- **Fila Offline para Bombeiros:** Se o alerta ocorrer sem internet, salvar na lista `fila_offline` dentro do JSON. Quando o usuário escolher sincronizar no menu, despachar os alertas usando lógica de fila (`pop(0)`).

### O que já está pronto no meu arquivo `sumauma.py` (continue exatamente daqui):

```python
import json
import os
import urllib.request
import urllib.error
from datetime import datetime

ARQUIVO_DADOS = "sumauma_registro.json"
ARQUIVO_SENSOR_EDGE = "leitura_sensor.json"
LATITUDE_MANAUS = -3.1190
LONGITUDE_MANAUS = -60.0217

NIVEIS_ALERTA = ("NORMAL", "ATENÇÃO", "ALERTA LARANJA", "EMERGENCIA CRITICA")

TERRITORIOS_MANAUS = {
    "1": {
        "nome": "Comunidade Ribeirinha do Catalão",
        "abrigo": "Escola Municipal Fluvial São José (Área aberta e ventilada)",
        "rota_fuga": "Seguir pelo trapiche principal norte, afastando-se da margem seca.",
        "contatos": "Bombeiros (193) | Defesa Civil Manaus (199) | Barco-Ambulância (194)"
    },
    "2": {
        "nome": "Bairro Educandos / Área de Palafitas",
        "abrigo": "Ginásio Poliesportivo da Zona Sul (Ponto alto e seguro)",
        "rota_fuga": "Subir pela Av. Principal em direção ao centro comunitário.",
        "contatos": "Bombeiros (193) | Defesa Civil (199) | UBS Educandos"
    },
    "3": {
        "nome": "Comunidade Indígena Parque das Tribos",
        "abrigo": "Centro Cultural Indígena (Ponto validado pelas lideranças)",
        "rota_fuga": "Seguir pela via central pavimentada rumo à saída oeste.",
        "contatos": "Bombeiros (193) | Saúde Indígena (DSEI Manaus) | Defesa Civil (199)"
    }
}

def salvar_dados(dados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)

def carregar_dados():
    if not os.path.exists(ARQUIVO_DADOS):
        estrutura_inicial = {
            "ocorrencias": [],
            "fila_offline": []
        }
        salvar_dados(estrutura_inicial)
        return estrutura_inicial
    try:
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, IOError):
        return {"ocorrencias": [], "fila_offline": []}

def ler_dados_sensor():
    if not os.path.exists(ARQUIVO_SENSOR_EDGE):
        leitura_simulada = {
            "territorio_id": "1",
            "temperatura": 32.5,
            "umidade": 28.0,
            "fumaca_ppm": 75
        }
        with open(ARQUIVO_SENSOR_EDGE, "w", encoding="utf-8") as arquivo:
            json.dump(leitura_simulada, arquivo, indent=4, ensure_ascii=False)
        return leitura_simulada
    
    try:
        with open(ARQUIVO_SENSOR_EDGE, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, IOError):
        return None
```

### O que falta fazer agora:
1. Criar a função `consultar_api_previsao_manaus()` usando `urllib.request` e `try/except`.
2. Criar as funções `avaliar_risco_e_protecao()` e `disparar_alerta_defesa_civil()` (usando os índices corretos `` a `` da tupla `NIVEIS_ALERTA`).
3. Criar as funções do menu (`processar_leitura_automatica`, `sincronizar_fila_offline` com `pop(0)`, `listar_historico`) e a função principal `main()` com `while True` e `match/case`.
4. Ao final, gerar os arquivos `readme.md` (com a Ficha da CitizenTech) e `prompts.md` (documentando o uso de IA conforme exigido pela FIAP).

Por favor, continue a partir do Passo 3 (função da API) explicando linha por linha para iniciantes.
