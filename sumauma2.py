# ==============================================================================
# SUMAÚMA | Monitoramento climático e prevenção de queimadas (Manaus - AM)
# FIAP · Global Solution 2026.2 · CitizenTech
# ==============================================================================
import json
import math
import os.path
import datetime
import urllib.request
import urllib.error

try:
    import requests
except:
    requests = None

try:
    import paho.mqtt.client as mqtt
except:
    mqtt = None

# ==============================================================================
# 1. CONFIGURAÇÕES E CONSTANTES
# ==============================================================================
ARQUIVO_DADOS = "sumauma_registro.json"
ARQUIVO_SENSOR_EDGE = "leitura_sensor.json"
ARQUIVO_API_URL = "api_url.txt"

LATITUDE_MANAUS = -3.1190
LONGITUDE_MANAUS = -60.0217

NIVEIS_ALERTA = ("NORMAL", "ATENÇÃO", "ALERTA LARANJA", "EMERGENCIA CRITICA")
ESTADOS_ESP32 = ("NORMAL", "ATENCAO", "ALERTA", "CRITICO")

# Raios de alcance do alerta no celular do cidadão (em km)
RAIO_PERIGO_FOGO_KM = 3.0     # Fogo próximo: risco direto de chamas e calor
RAIO_PERIGO_FUMACA_KM = 8.0   # Fumaça densa: risco respiratório levado pelo vento

# MQTT (mesmos tópicos do ESP32 no Wokwi)
BROKER = "broker.hivemq.com"
PORTA = 1883
TOPICO_TELEMETRIA = "fiap/gs/sumauma/ribeirinha01/telemetria"
TOPICO_COMANDO = "fiap/gs/sumauma/ribeirinha01/comando"
ID_CLIENTE_MQTT = "py_sumauma_richard"

SEM_DADO = -999
LIMITE_CHAMA_FRONT_PCT = 40.0
MENSAGENS_POR_CONSULTA_API = 12
MENSAGENS_ENTRE_COMANDOS = 6
TTL_COMANDO_S = 60

TIPO_FUMACA = 0
TIPO_FOGO_NA_MATA = 2

# Territórios monitorados com coordenadas geográficas da estação
TERRITORIOS_MANAUS = {
    "1": {
        "nome": "Comunidade Ribeirinha do Catalão",
        "lat": -3.1536,
        "lon": -59.9142,
        "abrigo": "Escola Municipal Fluvial São José (Área aberta e ventilada)",
        "rota_fuga": "Seguir pelo trapiche principal norte, afastando-se da margem seca.",
        "contatos": "Bombeiros (193) | Defesa Civil Manaus (199) | Barco-Ambulância (194)"
    },
    "2": {
        "nome": "Bairro Educandos / Área de Palafitas",
        "lat": -3.1444,
        "lon": -60.0089,
        "abrigo": "Ginásio Poliesportivo da Zona Sul (Ponto alto e seguro)",
        "rota_fuga": "Subir pela Av. Principal em direção ao centro comunitário.",
        "contatos": "Bombeiros (193) | Defesa Civil (199) | UBS Educandos"
    },
    "3": {
        "nome": "Comunidade Indígena Parque das Tribos",
        "lat": -3.0031,
        "lon": -60.0683,
        "abrigo": "Centro Cultural Indígena (Ponto validado pelas lideranças)",
        "rota_fuga": "Seguir pela via central pavimentada rumo à saída oeste.",
        "contatos": "Bombeiros (193) | Saúde Indígena (DSEI Manaus) | Defesa Civil (199)"
    }
}

# Simulação de cidadãos cadastrados para receber alertas no celular
CIDADAOS_CADASTRADOS = [
    {"nome": "Dona Maria (Catalão)", "telefone": "(92) 99111-1111", "lat": -3.1580, "lon": -59.9180},
    {"nome": "Seu João (Vila Buriti)", "telefone": "(92) 99222-2222", "lat": -3.1350, "lon": -59.9500},
    {"nome": "Lucas (Cidade Nova)", "telefone": "(92) 99333-3333", "lat": -3.0250, "lon": -59.9650}
]

ESTACOES = {"ribeirinha01": "1"}

ESTADO_TEMPO_REAL = {
    "ultimo_indice": None,
    "mensagens": 0,
    "msg_ultima_api": -999,
    "msg_ultimo_cmd": -999,
    "dados_api": None
}


# ==============================================================================
# 2. MANIPULAÇÃO DE ARQUIVOS JSON
# ==============================================================================
def salvar_dados(dados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)


def carregar_dados():
    if not os.path.exists(ARQUIVO_DADOS):
        estrutura_inicial = {"ocorrencias": [], "fila_offline": []}
        salvar_dados(estrutura_inicial)
        return estrutura_inicial
    try:
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except:
        return {"ocorrencias": [], "fila_offline": []}


def ler_url_api():
    if not os.path.exists(ARQUIVO_API_URL):
        return ""
    try:
        with open(ARQUIVO_API_URL, "r", encoding="utf-8") as arquivo:
            return arquivo.read().replace("\n", "").replace(" ", "")
    except:
        return ""


# ==============================================================================
# 3. TELEMETRIA DO ESP32
# ==============================================================================
def numero_valido(valor):
    if type(valor) == int or type(valor) == float:
        if valor != SEM_DADO:
            return valor
    return None


def normalizar_telemetria(dados):
    if type(dados) != dict:
        return None

    estado = dados.get("estado")
    if estado not in ESTADOS_ESP32:
        return None

    estacao = dados.get("estacao", "ribeirinha01")
    indicadores = numero_valido(dados.get("indicadores"))
    if indicadores is None:
        indicadores = 0

    indice_edge = ESTADOS_ESP32.index(estado)
    motivo = dados.get("motivo", "OK")

    indice_proprio = indice_edge
    if motivo == "COMANDO_PYTHON":
        indice_proprio = 0

    return {
        "estacao": estacao,
        "territorio_id": ESTACOES.get(estacao, "1"),
        "temperatura": numero_valido(dados.get("temp_c")),
        "umidade": numero_valido(dados.get("umid_pct")),
        "fumaca_pct": numero_valido(dados.get("fumaca_pct")),
        "chama_pct": numero_valido(dados.get("chama_pct")),
        "rio_cm": numero_valido(dados.get("rio_cm")),
        "indicadores": int(indicadores),
        "estado_edge": indice_edge,
        "estado_proprio": indice_proprio,
        "motivo": motivo,
        "remoto": dados.get("remoto") == True,
        "buffered": dados.get("buffered") == True
    }


def ler_dados_sensor():
    if not os.path.exists(ARQUIVO_SENSOR_EDGE):
        leitura_simulada = {
            "estacao": "ribeirinha01", "t_s": 120, "rio_cm": 150.0,
            "temp_c": 36.0, "umid_pct": 24.0, "fumaca_pct": 70,
            "qualidade_ar": "RUIM", "chama_pct": 0, "taxa_temp_c_min": 0.4,
            "indicadores": 2, "estado": "ALERTA", "motivo": "INCENDIO_PROVAVEL",
            "remoto": False, "buffered": False
        }
        with open(ARQUIVO_SENSOR_EDGE, "w", encoding="utf-8") as arquivo:
            json.dump(leitura_simulada, arquivo, indent=4, ensure_ascii=False)
        return normalizar_telemetria(leitura_simulada)

    try:
        with open(ARQUIVO_SENSOR_EDGE, "r", encoding="utf-8") as arquivo:
            return normalizar_telemetria(json.load(arquivo))
    except:
        return None


# ==============================================================================
# 4. CONSULTA ÀS APIS GRATUITAS (Clima + Fumaça)
# ==============================================================================
def buscar_clima_e_queimadas():
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
        with urllib.request.urlopen(url_clima, timeout=5) as resp_c:
            clima = json.loads(resp_c.read().decode("utf-8"))["current"]

        with urllib.request.urlopen(url_queimadas, timeout=5) as resp_a:
            ar = json.loads(resp_a.read().decode("utf-8"))["current"]

        return {
            "online": True,
            "temp_api": clima["temperature_2m"],
            "umidade_api": clima["relative_humidity_2m"],
            "vento_api": clima["wind_speed_10m"],
            "pm25_api": ar["pm2_5"],
            "co_api": ar["carbon_monoxide"]
        }
    except:
        return {
            "online": False,
            "temp_api": None,
            "umidade_api": None,
            "vento_api": None,
            "pm25_api": None,
            "co_api": None
        }


def obter_dados_api(usar_cache):
    estado = ESTADO_TEMPO_REAL
    if usar_cache and estado["dados_api"] is not None:
        passadas = estado["mensagens"] - estado["msg_ultima_api"]
        if passadas < MENSAGENS_POR_CONSULTA_API:
            return estado["dados_api"]

    estado["dados_api"] = buscar_clima_e_queimadas()
    estado["msg_ultima_api"] = estado["mensagens"]
    return estado["dados_api"]


# ==============================================================================
# 5. INTELIGÊNCIA DE RISCO E ALERTA GEOLOCALIZADO (DEFESA CIVIL)
# ==============================================================================
def avaliar_indice_risco(sensor, dados_api):
    indice_edge = sensor["estado_proprio"]

    pm25 = 0
    vento = 0
    if dados_api["online"]:
        if dados_api["pm25_api"] is not None:
            pm25 = dados_api["pm25_api"]
        if dados_api["vento_api"] is not None:
            vento = dados_api["vento_api"]

    temp = sensor["temperatura"]
    umid = sensor["umidade"]
    quente_e_seco = False
    if temp is not None and umid is not None:
        quente_e_seco = temp >= 35.0 and umid <= 25.0

    indice_regional = 0
    if pm25 >= 150:
        indice_regional = 3
    elif vento >= 25.0 or quente_e_seco:
        indice_regional = 2
    elif pm25 >= 50:
        indice_regional = 1

    indice_final = indice_edge
    if indice_regional > indice_final:
        indice_final = indice_regional
    return indice_final, indice_regional


def eh_apenas_calor_extremo(sensor, indice_regional):
    """Identifica se o alerta foi causado SOMENTE por temperatura alta (ex: 39°C no sol),
    sem fumaça, sem chama e sem subida brusca de fogo."""
    return sensor["motivo"] == "CALOR_EXTREMO" and sensor["indicadores"] == 1 and indice_regional == 0


def calcular_distancia_km(lat1, lon1, lat2, lon2):
    """Calcula a distância em km entre a estação e o morador (Fórmula de Haversine)."""
    raio_terra_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return raio_terra_km * c


def notificar_cidadaos_proximos(indice, territorio, apenas_calor):
    """Dispara aviso adequado ao celular: orientação de hidratação no calor ou evacuação no fogo."""
    if indice == 0:
        return  # Situação NORMAL não envia nada

    if apenas_calor:
        raio_maximo_km = RAIO_PERIGO_FUMACA_KM  # Alcance regional (8 km)
        titulo = "DEFESA CIVIL - AVISO DE CALOR INTENSO"
    elif indice >= 2:
        raio_maximo_km = RAIO_PERIGO_FOGO_KM    # Risco direto de fogo (3 km)
        titulo = "DEFESA CIVIL - ALERTA DE INCÊNDIO PRÓXIMO"
    else:
        raio_maximo_km = RAIO_PERIGO_FUMACA_KM  # Fumaça densa (8 km)
        titulo = "DEFESA CIVIL - ALERTA DE FUMAÇA DENSA"

    print("\n" + "*" * 60)
    print(f"DISPARO CELULAR (CELL BROADCAST) | Raio de alcance: {raio_maximo_km} km")
    print("*" * 60)

    enviados = 0
    for pessoa in CIDADAOS_CADASTRADOS:
        distancia = calcular_distancia_km(
            territorio["lat"], territorio["lon"],
            pessoa["lat"], pessoa["lon"]
        )

        if distancia <= raio_maximo_km:
            enviados += 1
            if apenas_calor:
                mensagem_curta = (
                    f"[{titulo}] Temperatura elevada em {territorio['nome']}. "
                    f"Sem risco de incêndio no local. Beba bastante água, procure locais ventilados e evite sol forte."
                )
            else:
                mensagem_curta = (
                    f"[{titulo}] Foco a {distancia:.1f} km ({territorio['nome']}). "
                    f"ZONA SEGURA: {territorio['abrigo']}. "
                    f"ROTA: {territorio['rota_fuga']} Emergência: 193."
                )
            print(f"-> ENVIADO para {pessoa['nome']} ({distancia:.1f} km):")
            print(f"   \"{mensagem_curta}\"")
        else:
            print(f"-> IGNORADO para {pessoa['nome']} ({distancia:.1f} km - fora da área afetada).")

    if enviados == 0:
        print("Nenhum morador cadastrado dentro do raio de alcance.")
    print("*" * 60 + "\n")


def texto_valor(valor, unidade):
    if valor is None:
        return "sem dado"
    return f"{valor}{unidade}"


def exibir_boletim_defesa_civil(nivel, indice_regional, territorio, sensor, dados_api, apenas_calor):
    """Exibe o boletim completo no terminal com orientações adequadas ao motivo."""
    print("\n" + "=" * 60)
    if dados_api["online"]:
        print("STATUS DA REDE: ONLINE (ESP32 + Satélite/API Manaus)")
    else:
        print("STATUS DA REDE: OFFLINE (Operando 100% pelo sensor do ESP32)")
    print(f"COMUNIDADE: {territorio['nome']}")
    print(f"SITUAÇÃO ATUAL: >>> {nivel} <<< (Motivo: {sensor['motivo']})")
    print("=" * 60)

    print(f"[ESP32] Estado: {ESTADOS_ESP32[sensor['estado_edge']]} | Indicadores de fogo: {sensor['indicadores']}/4")
    print(f"[Sensores] Temp: {texto_valor(sensor['temperatura'], '°C')} | Umidade: {texto_valor(sensor['umidade'], '%')} | Fumaça: {texto_valor(sensor['fumaca_pct'], '%')} | Chama: {texto_valor(sensor['chama_pct'], '%')} | Rio: {texto_valor(sensor['rio_cm'], ' cm')}")
    if dados_api["online"]:
        print(f"[Clima Manaus] Temp: {dados_api['temp_api']}°C | Vento: {dados_api['vento_api']} km/h | Fumaça Ar (PM2.5): {dados_api['pm25_api']} µg/m³")

    if nivel == NIVEIS_ALERTA[0]:
        print("\nAmbiente seguro. Nenhuma medida necessária no momento.")
    elif apenas_calor:
        print("\n[!] ORIENTAÇÕES PARA CALOR EXTREMO (SEM INDÍCIO DE INCÊNDIO):")
        print("  1. Beba bastante água e evite exposição direta ao sol.")
        print("  2. Atenção redobrada com crianças e idosos em locais abafados.")
        print("  3. Não é necessária evacuação no momento.")
    else:
        print("\a")
        print("\n[!] ORIENTAÇÕES DE PROTEÇÃO CONTRA FUMAÇA TÓXICA:")
        print("  1. Proteja nariz e boca com máscara PFF2/N95 ou pano limpo molhado.")
        print("  2. Se houver fumaça densa, ande abaixado (o ar limpo fica perto do chão).")
        print("  3. Feche portas e janelas e vede as frestas com panos úmidos.")
        print("\n[!] PLANO DE EVACUAÇÃO DA COMUNIDADE:")
        print(f"  -> ZONA SEGURA:   {territorio['abrigo']}")
        print(f"  -> ROTA DE FUGA:  {territorio['rota_fuga']}")
        print(f"  -> EMERGÊNCIA:    {territorio['contatos']}")
    print("=" * 60 + "\n")


# ==============================================================================
# 6. CONEXÃO COM O SITE (ENVIA TODOS OS DADOS TÉCNICOS + MOTIVO)
# ==============================================================================
def montar_aviso_front(registro):
    tipo = TIPO_FUMACA
    if registro.get("chama_detectada", False):
        tipo = TIPO_FOGO_NA_MATA

        detalhes = (
        f"[{registro.get('data_hora', '')}] {registro['nivel']} ({registro.get('motivo')}) em {registro['territorio']} | "
        f"ESP32: {registro.get('estado_esp32')} | "
        f"Fumaça: {texto_valor(registro.get('fumaca_pct'), '%')} | "
        f"Chama: {texto_valor(registro.get('chama_pct'), '%')} | "
        f"Temp: {texto_valor(registro.get('temperatura'), '°C')} | "
        f"Umid: {texto_valor(registro.get('umidade'), '%')} | "
        f"Rio: {texto_valor(registro.get('rio_cm'), ' cm')} | "
        f"PM2.5: {texto_valor(registro.get('pm25_api'), ' µg/m³')} | "
        f"Vento: {texto_valor(registro.get('vento_api'), ' km/h')}."
    )

    return {
        "k": tipo,
        "z": "Manaus",
        "d": detalhes,
        "s": 0,
        "cf": 0
    }


def enviar_aviso_para_front(registro):
    url = ler_url_api()
    if url == "" or requests is None:
        return False

    try:
        resposta = requests.post(url, json=montar_aviso_front(registro), timeout=5)
        return resposta.status_code == 200 or resposta.status_code == 201
    except:
        return False


# ==============================================================================
# 7. CICLO PRINCIPAL
# ==============================================================================
def enviar_comando_esp32(cliente, sensor, indice_regional):
    if cliente is None or sensor["buffered"]:
        return

    estado = ESTADO_TEMPO_REAL
    if estado["mensagens"] - estado["msg_ultimo_cmd"] < MENSAGENS_ENTRE_COMANDOS:
        return

    comando = None
    if indice_regional >= 2 and (indice_regional > sensor["estado_proprio"] or sensor["remoto"]):
        comando = {"estado": ESTADOS_ESP32[indice_regional], "ttl_s": TTL_COMANDO_S, "origem": "python"}
    elif indice_regional < 2 and sensor["remoto"]:
        comando = {"estado": "NORMAL", "origem": "python"}

    if comando is not None:
        cliente.publish(TOPICO_COMANDO, json.dumps(comando))
        estado["msg_ultimo_cmd"] = estado["mensagens"]
        print(f"-> Comando enviado ao ESP32: {comando}")


def registrar_e_enviar(registro, nivel, dados_api):
    banco = carregar_dados()
    banco["ocorrencias"].append(registro)

    # Tenta enviar diretamente para o site (independente da API pública de clima)
    enviado = enviar_aviso_para_front(registro)

    if enviado:
        print("-> Todos os dados técnicos foram enviados para o site SUMAÚMA!")
    elif nivel != NIVEIS_ALERTA[0]:
        banco["fila_offline"].append(registro)
        print("-> Site indisponível: ocorrência salva na FILA OFFLINE.")

    salvar_dados(banco)


def processar_leitura(sensor, cliente=None, tempo_real=False):
    if tempo_real:
        ESTADO_TEMPO_REAL["mensagens"] += 1

    dados_api = obter_dados_api(tempo_real)
    indice, indice_regional = avaliar_indice_risco(sensor, dados_api)
    nivel = NIVEIS_ALERTA[indice]
    territorio = TERRITORIOS_MANAUS.get(sensor["territorio_id"], TERRITORIOS_MANAUS["1"])
    apenas_calor = eh_apenas_calor_extremo(sensor, indice_regional)

    enviar_comando_esp32(cliente, sensor, indice_regional)

    if tempo_real and ESTADO_TEMPO_REAL["ultimo_indice"] == indice:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {nivel} ({sensor['motivo']}) | Fumaça: {texto_valor(sensor['fumaca_pct'], '%')} | Temp: {texto_valor(sensor['temperatura'], '°C')}")
        return
    ESTADO_TEMPO_REAL["ultimo_indice"] = indice

    exibir_boletim_defesa_civil(nivel, indice_regional, territorio, sensor, dados_api, apenas_calor)
    notificar_cidadaos_proximos(indice, territorio, apenas_calor)
    if apenas_calor:
        print("-> Onda de calor isolada: mantido apenas no terminal (não enviado ao site).")
        return

    chama = False
    if sensor["chama_pct"] is not None:
        chama = sensor["chama_pct"] >= LIMITE_CHAMA_FRONT_PCT

    modo_envio = "Online" if dados_api["online"] else "Offline (Na Fila)"

    registro = {
        "data_hora": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "territorio": territorio["nome"],
        "nivel": nivel,
        "estado_esp32": ESTADOS_ESP32[sensor["estado_edge"]],
        "motivo": sensor["motivo"],
        "fumaca_pct": sensor["fumaca_pct"],
        "chama_pct": sensor["chama_pct"],
        "chama_detectada": chama,
        "temperatura": sensor["temperatura"],
        "umidade": sensor["umidade"],
        "rio_cm": sensor["rio_cm"],
        "pm25_api": dados_api["pm25_api"],
        "vento_api": dados_api["vento_api"],
        "modo_envio": modo_envio
    }
    registrar_e_enviar(registro, nivel, dados_api)


# ==============================================================================
# 8. MQTT: TEMPO REAL COM O ESP32
# ==============================================================================
def ao_conectar(cliente, userdata, flags, rc, *args):
    print("Conectado ao broker MQTT (rc =", rc, "). Aguardando telemetria...")
    cliente.subscribe(TOPICO_TELEMETRIA)


def ao_receber(cliente, userdata, msg):
    try:
        dados = json.loads(msg.payload.decode("utf-8"))
    except:
        return

    sensor = normalizar_telemetria(dados)
    if sensor is not None:
        try:
            processar_leitura(sensor, cliente, True)
        except:
            pass


def escutar_esp32():
    if mqtt is None:
        print("\nBiblioteca paho-mqtt não instalada. Use a opção 1.\n")
        return

    try:
        cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=ID_CLIENTE_MQTT)
    except:
        cliente = mqtt.Client(client_id=ID_CLIENTE_MQTT)

    cliente.on_connect = ao_conectar
    cliente.on_message = ao_receber
    ESTADO_TEMPO_REAL["ultimo_indice"] = None
    ESTADO_TEMPO_REAL["dados_api"] = None

    try:
        cliente.connect(BROKER, PORTA, keepalive=60)
        print("\nEscutando o ESP32. Aperte Ctrl+C para voltar ao menu.\n")
        cliente.loop_forever()
    except:
        pass
    cliente.disconnect()
    print("\nEscuta encerrada.\n")


# ==============================================================================
# 9. FUNÇÕES DO MENU
# ==============================================================================
def executar_monitoramento():
    sensor = ler_dados_sensor()
    if sensor is None:
        print("\nArquivo leitura_sensor.json inválido.\n")
        return
    print("\nProcessando telemetria e verificando raio de risco...")
    processar_leitura(sensor, None, False)


def sincronizar_fila_bombeiros():
    banco = carregar_dados()
    fila = banco["fila_offline"]

    if len(fila) == 0:
        print("\nNenhum alerta pendente na fila offline.\n")
        return

    while len(fila) > 0:
        alerta_antigo = fila[0]
        if not enviar_aviso_para_front(alerta_antigo):
            print("Falha ao enviar ao site. O restante continua na fila.")
            break
        fila.pop(0)
        print(f"[ENVIADO AO SITE] {alerta_antigo['data_hora']} | {alerta_antigo['territorio']}")

    banco["fila_offline"] = fila
    salvar_dados(banco)


def mostrar_historico():
    banco = carregar_dados()
    lista = banco["ocorrencias"]

    if len(lista) == 0:
        print("\nNenhuma ocorrência registrada.\n")
        return

    print("\n--- HISTÓRICO DE MONITORAMENTO SUMAÚMA ---")
    for indice, item in enumerate(lista, start=1):
        print(f"{indice}. [{item['data_hora']}] {item['territorio']} -> {item['nivel']} ({item.get('motivo')})")
    print(f"Fila offline: {len(banco['fila_offline'])} alerta(s)\n")


# ==============================================================================
# 10. MENU PRINCIPAL
# ==============================================================================
def iniciar_sistema():
    while True:
        print("=== REDE SUMAÚMA | MONITORAMENTO CLIMÁTICO E PREVENÇÃO (MANAUS) ===")
        print("1 - Verificar sensor pelo arquivo (leitura_sensor.json)")
        print("2 - Sincronizar alertas offline com o site")
        print("3 - Ver histórico de ocorrências")
        print("4 - Escutar o ESP32 em tempo real (MQTT)")
        print("0 - Encerrar sistema")

        escolha = input("Digite a opção: ")

        match escolha:
            case "1":
                executar_monitoramento()
            case "2":
                sincronizar_fila_bombeiros()
            case "3":
                mostrar_historico()
            case "4":
                escutar_esp32()
            case "0":
                print("\nEncerrando Sistema SUMAÚMA.")
                break
            case _:
                print("\nOpção inválida.\n")


if __name__ == "__main__":
    iniciar_sistema()