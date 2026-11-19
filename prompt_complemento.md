
---

# Continuação do uso de IA (depois do prompt acima)

## Resumo de como foi o desenvolvimento

- **O que eu escrevi:** a parte inicial do `sumauma.py`, que está no prompt acima em "O que já está pronto": as constantes, o dicionário de territórios e as funções `salvar_dados`, `carregar_dados` e `ler_dados_sensor`. 
- **O que pedi à IA no prompt acima:** a função da API, a avaliação de risco e o alerta, as funções do menu, a função `main` e os arquivos `readme.md` e `prompts.md` (usei o Gemini).
- **O que fiz depois, com o Claude (Anthropic):** os prompts abaixo.

## Prompt 2 — Correção do código

Colei o código completo e pedi: "corrija a identação do meu código".

O Claude corrigiu a indentação e encontrou erros que impediam o programa de funcionar:
- A função de risco devolvia a tupla `NIVEIS_ALERTA` inteira em todas as regras, e não um item dela. No prompt acima, os índices da tupla ficaram em branco (`` a ``).
- As URLs da Open-Meteo estavam incompletas.
- `if name == "main"` estava errado (o correto é `if __name__ == "__main__":`).
- As linhas de comentário da seção 6 estavam sem `#`.

## Prompt 3 — Dados reais

Perguntei como ter dados reais para a demonstração. O Claude pesquisou as fontes e indicou os arquivos diários de focos de calor do INPE. Essa parte **não foi implementada**.

## Prompt 4 — Conexão com o site

Passei o link do site e do repositório do André e pedi para conectar o meu Python a ele.

O Claude leu o código do front. O site guarda os avisos numa API REST (MockAPI, recurso `avisos`, com os campos `k`, `z`, `d`, `s` e `cf`). O Claude fez o Python enviar os alertas para essa API com `requests.post` e criou o arquivo `api_url.txt` para guardar a URL fora do código. A fila offline passou a enviar os alertas de verdade, na ordem de chegada.

## Prompt 5 — Conexão com o ESP32 (Wokwi)

Anexei o exemplo de MQTT e o link do Wokwi do Nicholas e pedi para conectar os três: o ESP32, o meu Python e o site do André.

O Claude fez:
- A leitura da telemetria do ESP32 por MQTT (opção 4 do menu) e, como alternativa, pelo arquivo `leitura_sensor.json` no mesmo formato.
- A validação das mensagens (JSON inválido, valores `-999`).
- O nível final, que é o maior entre o estado do ESP32 e o risco regional.
- O envio de comandos de volta ao ESP32 e a correção de um alarme falso causado pelo eco desse comando.
- Testes com mensagens simuladas e a atualização do README.

## Recursos fora da apostila (aguardando confirmação do professor)

- `requests.post`, com `json=` e `status_code`, usado para enviar os alertas ao site.
- A biblioteca `paho-mqtt`, usada para receber a telemetria do ESP32 em tempo real. Ela é opcional: sem ela, o programa funciona pela leitura do arquivo.
tentei ao máximo não usar coisas que o senhor não ensinou.
mas pesquisei sobre essas coisas para entender como funcionavam.

## O que foi verificado

- Os testes do Claude usaram mensagens simuladas, um servidor de mentira no lugar do site e um cliente MQTT falso.



## cursos utilizados além da ementa básica (e justificativas):


1. paho-mqtt (biblioteca externa): Necessária para comunicação em tempo real (pub/sub) com o microcontrolador ESP32 no Wokwi. Alternativa nativa implementada: Caso a biblioteca não esteja instalada, o sistema opera normalmente lendo o arquivo local leitura_sensor.json.
2. requests (biblioteca externa): Utilizada para enviar os dados via POST para a API REST do site. (Observação: pode ser substituída pela biblioteca nativa urllib.request, já utilizada na consulta de clima).
3. Módulos padrão do Python (math, datetime, os.path, urllib.request): Bibliotecas nativas da linguagem utilizadas para o cálculo de distância geográfica (Haversine), carimbo de data/hora nos logs, verificação de existência dos arquivos JSON e consumo das APIs públicas de clima.
