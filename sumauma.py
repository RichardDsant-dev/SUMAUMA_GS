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
