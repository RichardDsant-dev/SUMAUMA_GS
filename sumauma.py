import json
import os.path
import datetime
import requests

# ==============================================================================
# 1. CONFIGURAÇÕES E CONSTANTES DO SISTEMA SUMAÚMA
# ==============================================================================
ARQUIVO_DADOS = "sumauma_registro.json"
ARQUIVO_SENSOR_EDGE = "leitura_sensor.json"

# Coordenadas centrais de Manaus - AM
LATITUDE_MANAUS = -3.1190
LONGITUDE_MANAUS = -60.0217

# Tupla com os níveis oficiais de alerta da Defesa Civil Comunitária
NIVEIS_ALERTA = ("NORMAL", "ATENÇÃO", "ALERTA LARANJA", "EMERGENCIA CRITICA")

# Dicionário com os territórios monitorados e rotas de evacuação
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


# ==============================================================================
# 1.1 CONEXÃO COM O FRONT-END (API REST "avisos" no MockAPI)
# ==============================================================================
# A URL da API fica num arquivo de texto à parte (api_url.txt), com uma linha só:
#   https://SEU_ID.mockapi.io/api/v1/avisos
# Assim a URL não vai escrita no código. Peça ao André (front) a mesma
# VITE_API_URL que ele usa no .env.
ARQUIVO_API_URL = "api_url.txt"

# Tipos de aviso que o front entende (campo "k"):
# 0 = Fumaça no ar | 1 = Fogo perto de casa | 2 = Fogo na mata
TIPO_FUMACA = 0
TIPO_FOGO_NA_MATA = 2


def ler_url_api():
    """Lê a URL da API do front. Devolve texto vazio se o arquivo não existir."""
    if not os.path.exists(ARQUIVO_API_URL):
        return ""
    try:
        arquivo = open(ARQUIVO_API_URL, "r")
        texto = arquivo.read()
        arquivo.close()
        return texto.replace("\n", "").replace(" ", "")
    except:
        return ""


def montar_aviso_front(registro):
    """Converte um registro do SUMAÚMA no formato que o front espera.
    k = tipo, z = local, d = detalhes, s = etapa (0 = Enviado), cf = confirmação."""
    tipo = TIPO_FUMACA
    if registro["chama_detectada"]:
        tipo = TIPO_FOGO_NA_MATA

    detalhes = (
        f"[Sensor SUMAÚMA] {registro['nivel']} em {registro['territorio']}: "
        f"fumaça {registro['fumaca_ppm']} ppm, {registro['temperatura']}°C, "
        f"umidade {registro['umidade']}%."
    )

    return {
        "k": tipo,
        "z": "Manaus",
        "d": detalhes,
        "s": 0,
        "cf": 0
    }


def enviar_aviso_para_front(registro):
    """Envia um alerta para o front. Devolve True se deu certo, False se falhou."""
    url = ler_url_api()
    if url == "":
        return False

    try:
        resposta = requests.post(url, json=montar_aviso_front(registro))
        return resposta.status_code == 200 or resposta.status_code == 201
    except:
        return False


# ==============================================================================
# 2. MANIPULAÇÃO DE ARQUIVOS JSON (Persistência Local)
# ==============================================================================
def salvar_dados(dados):
    """Salva o histórico e a fila offline no arquivo JSON principal."""
    arquivo = open(ARQUIVO_DADOS, "w")
    arquivo.write(json.dumps(dados))
    arquivo.close()


def carregar_dados():
    """Carrega os registros salvos ou cria o arquivo pela primeira vez."""
    if not os.path.exists(ARQUIVO_DADOS):
        estrutura_inicial = {
            "ocorrencias": [],
            "fila_offline": []
        }
        salvar_dados(estrutura_inicial)
        return estrutura_inicial

    try:
        arquivo = open(ARQUIVO_DADOS, "r")
        texto = arquivo.read()
        arquivo.close()
        return json.loads(texto)
    except:
        return {"ocorrencias": [], "fila_offline": []}


def ler_dados_sensor():
    """Lê os dados gerados pelo sensor local (Edge) sem precisar digitar nada."""
    if not os.path.exists(ARQUIVO_SENSOR_EDGE):
        # Cria uma leitura de exemplo caso o arquivo ainda não exista
        leitura_simulada = {
            "territorio_id": "1",
            "temperatura": 35.5,
            "umidade": 24.0,
            "fumaca_ppm": 160,
            "chama_detectada": False
        }
        arquivo = open(ARQUIVO_SENSOR_EDGE, "w")
        arquivo.write(json.dumps(leitura_simulada))
        arquivo.close()
        return leitura_simulada

    try:
        arquivo = open(ARQUIVO_SENSOR_EDGE, "r")
        texto = arquivo.read()
        arquivo.close()
        return json.loads(texto)
    except:
        return {
            "territorio_id": "1",
            "temperatura": 30.0,
            "umidade": 50.0,
            "fumaca_ppm": 20,
            "chama_detectada": False
        }


# ==============================================================================
# 3. CONSULTA ÀS APIS GRATUITAS (Clima + Fumaça de Queimadas)
# ==============================================================================
def buscar_clima_e_queimadas():
    """Busca temperatura, vento, umidade e partículas de queimadas (PM2.5 e CO)."""
    url_clima = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={LATITUDE_MANAUS}&longitude={LONGITUDE_MANAUS}"
        f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
    )

    url_queimadas = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality?"
        f"latitude={LATITUDE_MANAUS}&longitude={LONGITUDE_MANAUS}"
        f"&current=pm2_5,carbon_monoxide"
    )

    try:
        # Consulta 1: Clima atual em Manaus
        r_clima = requests.get(url_clima)
        clima = r_clima.json()["current"]

        # Consulta 2: Qualidade do ar / fumaça de queimadas na região
        r_ar = requests.get(url_queimadas)
        ar = r_ar.json()["current"]

        return {
            "online": True,
            "temp_api": clima["temperature_2m"],
            "umidade_api": clima["relative_humidity_2m"],
            "vento_api": clima["wind_speed_10m"],
            "pm25_api": ar["pm2_5"],
            "co_api": ar["carbon_monoxide"]
        }

    except:
        # Se a internet cair, o sistema não trava e assume o modo Offline-First
        return {
            "online": False,
            "temp_api": None,
            "umidade_api": None,
            "vento_api": None,
            "pm25_api": None,
            "co_api": None
        }


# ==============================================================================
# 4. INTELIGÊNCIA DE RISCO E ALERTA COMUNITÁRIO
# ==============================================================================
def avaliar_nivel_risco(sensor, dados_api):
    """Cruza os dados locais do sensor com a API para definir o nível da tupla."""
    fumaca_local = sensor.get("fumaca_ppm", 0)
    temp_local = sensor.get("temperatura", 28.0)
    umidade_local = sensor.get("umidade", 60.0)
    chama = sensor.get("chama_detectada", False)

    # Pega os dados da API se houver conexão
    pm25_regiao = 0
    vento_regiao = 0
    if dados_api["online"]:
        pm25_regiao = dados_api["pm25_api"]
        vento_regiao = dados_api["vento_api"]

    # Regra 1: Fogo confirmado ou fumaça densa tóxica
    if chama or fumaca_local >= 300 or pm25_regiao >= 150:
        return NIVEIS_ALERTA[3]  # EMERGENCIA CRITICA

    # Regra 2: Fumaça alta ou clima muito seco com vento propício para incêndio
    elif fumaca_local >= 150 or (temp_local >= 35.0 and umidade_local <= 25.0) or vento_regiao >= 25.0:
        return NIVEIS_ALERTA[2]  # ALERTA LARANJA

    # Regra 3: Fumaça moderada ou calor acima do normal
    elif fumaca_local >= 70 or temp_local >= 33.0 or pm25_regiao >= 50:
        return NIVEIS_ALERTA[1]  # ATENÇÃO

    # Regra 4: Tudo dentro da normalidade
    else:
        return NIVEIS_ALERTA[0]  # NORMAL


def exibir_boletim_defesa_civil(nivel, territorio, sensor, dados_api):
    """Exibe o alerta na tela com linguagem clara para a comunidade."""
    print("\n" + "=" * 60)
    if dados_api["online"]:
        print("STATUS DA REDE: ONLINE (Sensor Local + Satélite/API Manaus)")
    else:
        print("STATUS DA REDE: OFFLINE (Operando 100% pelo Sensor Local)")
    print(f"COMUNIDADE: {territorio['nome']}")
    print(f"SITUAÇÃO ATUAL: >>> {nivel} <<<")
    print("=" * 60)

    print(f"[Sensor Local] Temp: {sensor['temperatura']}°C | Umidade: {sensor['umidade']}% | Fumaça: {sensor['fumaca_ppm']} ppm")
    if dados_api["online"]:
        print(f"[Clima Manaus] Temp: {dados_api['temp_api']}°C | Vento: {dados_api['vento_api']} km/h | Fumaça Ar (PM2.5): {dados_api['pm25_api']} µg/m³")

    # Se não estiver NORMAL, dispara alerta sonoro e instruções de sobrevivência
    if nivel != NIVEIS_ALERTA[0]:
        print("\a")  # Bipe sonoro no terminal
        print("\n[!] ORIENTAÇÕES DE PROTEÇÃO CONTRA FUMAÇA TÓXICA:")
        print("  1. Proteja nariz e boca com máscara PFF2/N95 ou pano limpo molhado.")
        print("  2. Se houver fumaça densa, ande abaixado (o ar limpo fica perto do chão).")
        print("  3. Feche portas e janelas e vede as frestas com panos úmidos.")
        print("\n[!] PLANO DE EVACUAÇÃO DA COMUNIDADE:")
        print(f"  -> ROTA DE FUGA: {territorio['rota_fuga']}")
        print(f"  -> ABRIGO SEGURO: {territorio['abrigo']}")
        print(f"  -> EMERGÊNCIA:   {territorio['contatos']}")
    else:
        print("\nAmbiente seguro. Nenhuma medida de evacuação necessária no momento.")
    print("=" * 60 + "\n")


# ==============================================================================
# 5. FUNÇÕES PRINCIPAIS DO MENU
# ==============================================================================
def executar_monitoramento():
    """Realiza o ciclo completo: lê sensor, consulta API, alerta e salva."""
    sensor = ler_dados_sensor()
    id_territorio = str(sensor.get("territorio_id", "1"))
    territorio = TERRITORIOS_MANAUS.get(id_territorio, TERRITORIOS_MANAUS["1"])

    print("\nLendo sensores locais e verificando previsão de queimadas em Manaus...")
    dados_api = buscar_clima_e_queimadas()
    nivel = avaliar_nivel_risco(sensor, dados_api)

    exibir_boletim_defesa_civil(nivel, territorio, sensor, dados_api)

    # Monta o registro da ocorrência
    modo_envio = "Offline (Na Fila)"
    if dados_api["online"]:
        modo_envio = "Online"

    registro = {
        "data_hora": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "territorio": territorio["nome"],
        "nivel": nivel,
        "fumaca_ppm": sensor["fumaca_ppm"],
        "temperatura": sensor["temperatura"],
        "umidade": sensor["umidade"],
        "chama_detectada": sensor.get("chama_detectada", False),
        "modo_envio": modo_envio
    }

    banco = carregar_dados()
    banco["ocorrencias"].append(registro)

    # Lógica da Fila Offline FIFO: o alerta vai para o painel (front) ou fica na fila
    if nivel != NIVEIS_ALERTA[0]:
        enviado = False
        if dados_api["online"]:
            enviado = enviar_aviso_para_front(registro)

        if enviado:
            print("-> Alerta enviado para o painel SumaÚma (front)!")
        else:
            banco["fila_offline"].append(registro)
            if dados_api["online"]:
                print("-> Painel indisponível (confira o api_url.txt): alerta guardado na FILA OFFLINE.")
            else:
                print("-> Sem internet: Alerta guardado na FILA OFFLINE para envio assim que a rede voltar.")

    salvar_dados(banco)


def sincronizar_fila_bombeiros():
    """Envia os alertas acumulados na fila offline por ordem de chegada (FIFO)."""
    banco = carregar_dados()
    fila = banco["fila_offline"]

    if len(fila) == 0:
        print("\nTudo em dia! Não há nenhum alerta pendente na fila offline.\n")
        return

    print(f"\nExistem {len(fila)} alerta(s) aguardando envio. Testando conexão...")
    teste_rede = buscar_clima_e_queimadas()

    if not teste_rede["online"]:
        print("Ainda estamos sem internet. Os alertas continuam salvos com segurança na fila.\n")
        return

    print("Conexão restabelecida! Despachando alertas por ordem de chegada (FIFO):\n")
    while len(fila) > 0:
        alerta_antigo = fila[0]  # O primeiro que entrou na fila

        # Alertas antigos podem não ter esses campos; usamos valores padrão
        alerta_antigo.setdefault("umidade", 0)
        alerta_antigo.setdefault("chama_detectada", False)

        if not enviar_aviso_para_front(alerta_antigo):
            print("  Não foi possível enviar ao painel. O restante continua na fila.")
            break

        fila.pop(0)  # Só retira da fila depois que o envio deu certo
        print(f"  [ENVIADO] {alerta_antigo['data_hora']} | {alerta_antigo['territorio']} | Nível: {alerta_antigo['nivel']}")

    banco["fila_offline"] = fila
    salvar_dados(banco)

    if len(fila) == 0:
        print("\nTodos os alertas foram sincronizados com o painel SumaÚma!\n")
    else:
        print(f"\nAinda restam {len(fila)} alerta(s) na fila.\n")


def mostrar_historico():
    """Lista todas as leituras já registradas no sistema."""
    banco = carregar_dados()
    lista = banco["ocorrencias"]

    if len(lista) == 0:
        print("\nAinda não há ocorrências registradas no histórico.\n")
        return

    print("\n--- HISTÓRICO DE MONITORAMENTO SUMAÚMA ---")
    for indice, item in enumerate(lista, start=1):
        print(f"{indice}. [{item['data_hora']}] {item['territorio']} -> {item['nivel']} (Fumaça: {item['fumaca_ppm']} ppm)")

    print(f"\nAlertas aguardando na fila offline: {len(banco['fila_offline'])}")
    print("-" * 45 + "\n")


# ==============================================================================
# 6. MENU PRINCIPAL (Ponto de Partida do Programa)
# ==============================================================================
def iniciar_sistema():
    while True:
        print("=== REDE SUMAÚMA | MONITORAMENTO CLIMÁTICO E PREVENÇÃO (MANAUS) ===")
        print("1 - Verificar sensores e risco de queimadas agora")
        print("2 - Sincronizar alertas offline com os Bombeiros")
        print("3 - Ver histórico de ocorrências")
        print("0 - Encerrar sistema")

        escolha = input("Digite o número da opção desejada: ")

        match escolha:
            case "1":
                executar_monitoramento()
            case "2":
                sincronizar_fila_bombeiros()
            case "3":
                mostrar_historico()
            case "0":
                print("\nEncerrando o Sistema SUMAÚMA. Mantenha-se seguro!")
                break
            case _:
                print("\nOpção inválida! Por favor, digite 1, 2, 3 ou 0.\n")


iniciar_sistema()
