Rede SUMAÚMA — Monitoramento Climático e Prevenção (Manaus)

Sistema em Python, executado no terminal, que monitora o risco de queimadas em comunidades de Manaus (AM). Ele cruza as leituras de um sensor local com dados de clima e qualidade do ar obtidos por API, define um nível de alerta e mostra orientações de proteção e o plano de evacuação da comunidade.

Funciona também sem internet (modo offline-first): os alertas ficam em uma fila e são enviados na ordem de chegada (FIFO) quando a rede volta.

Requisitos
Python 3.10 ou superior (o programa usa match/case)
Biblioteca requests
Conexão com a internet (opcional: sem ela, o programa usa só o sensor local)
Instalação
Confirme a versão do Python:
python --version
Coloque o arquivo sumauma.py em uma pasta.
Instale a dependência:
pip install requests
Como executar

Abra o terminal na pasta do arquivo e rode:

python sumauma.py

No Windows, se python não funcionar, use py sumauma.py.

Menu
Opção	O que faz
1	Lê o sensor, consulta as APIs, mostra o boletim e salva a ocorrência
2	Sincroniza com os Bombeiros os alertas guardados na fila offline
3	Mostra o histórico de ocorrências
0	Encerra o sistema
Níveis de alerta
Nível	Quando ocorre
NORMAL	Nenhuma das condições abaixo
ATENÇÃO	Fumaça ≥ 70 ppm, ou temperatura ≥ 33 °C, ou PM2.5 ≥ 50
ALERTA LARANJA	Fumaça ≥ 150 ppm, ou (temperatura ≥ 35 °C e umidade ≤ 25%), ou vento ≥ 25 km/h
EMERGENCIA CRITICA	Chama detectada, ou fumaça ≥ 300 ppm, ou PM2.5 ≥ 150

Fora do nível NORMAL, o programa emite um bipe e exibe as orientações contra fumaça tóxica, a rota de fuga, o abrigo seguro e os contatos de emergência do território.

Simulando o sensor

Na primeira execução, o programa cria o arquivo leitura_sensor.json com valores de exemplo. Edite-o para testar situações diferentes:

json
{
    "territorio_id": "2",
    "temperatura": 36.0,
    "umidade": 20.0,
    "fumaca_ppm": 320,
    "chama_detectada": false
}
Campo	Descrição
territorio_id	"1" Catalão, "2" Educandos, "3" Parque das Tribos
temperatura	Temperatura local em °C
umidade	Umidade relativa local em %
fumaca_ppm	Concentração de fumaça em ppm
chama_detectada	true ou false
Testando o modo offline
Desligue a internet.
Edite leitura_sensor.json para um nível acima de NORMAL e escolha a opção 1. O alerta é guardado na fila offline.
Ligue a internet de novo.
Escolha a opção 2 para enviar a fila por ordem de chegada.
APIs utilizadas

Ambas são gratuitas e não exigem chave de acesso (Open-Meteo):

Clima atual (temperatura, umidade, vento): https://api.open-meteo.com/v1/forecast
Qualidade do ar (PM2.5 e monóxido de carbono): https://air-quality-api.open-meteo.com/v1/air-quality

A fumaça de queimadas é estimada pelo PM2.5. As APIs não fazem previsão de incêndio: o nível de alerta vem das regras da tabela acima.

Arquivos gerados
Arquivo	Conteúdo
leitura_sensor.json	Leitura do sensor local (editável para testes)
sumauma_registro.json	Histórico de ocorrências e fila offline

Para zerar o histórico, apague sumauma_registro.json.

Problemas comuns
SyntaxError perto de match: a versão do Python é anterior à 3.10. Atualize.
ModuleNotFoundError: No module named 'requests': rode pip install requests.
Sempre aparece OFFLINE: verifique a conexão com a internet e se o acesso às URLs da Open-Meteo não está bloqueado pela rede.
Opção inválida ao digitar um número válido: digite só o número, sem espaços.