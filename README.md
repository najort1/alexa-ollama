# Assistente de IA para Alexa com Flask e Ollama

Este projeto implementa uma API Flask que integra um modelo de linguagem local (via Ollama) para responder perguntas de forma descontraída e divertida, podendo ser utilizada como backend para skills da Alexa ou outros clientes.

## Funcionalidades

- Responde perguntas de forma leve, criativa e com bom humor.
- Limita as respostas a 800 caracteres.
- Integração fácil com Alexa e outros sistemas via HTTP POST.
- Utiliza modelos locais via Ollama, sem depender de serviços externos.
- **Memória de conversação:** mantém histórico das interações do usuário, permitindo respostas mais contextuais.
- **Persistência de histórico:** utiliza banco de dados SQLite para armazenar o histórico das conversas.
- **Gerenciamento de sessões:** cada usuário tem seu próprio histórico, com limpeza automática de sessões inativas.

## Requisitos

- Python 3.8+
- Instale o Flask via pip: `pip install flask`
- Instale o requests via pip: `pip install requests`
- [Ollama](https://ollama.com/) rodando localmente com o modelo desejado (ex: `gemma3:4b`)

## Instalação

1. Clone este repositório:
   ```bash
   git clone https://github.com/najort1/alexa-ollama.git
   cd alexa-ollama
   ```

2. Instale as dependências:
   ```bash
   pip install flask requests
   ```

3. Instale e rode o Ollama:
   - Baixe e instale o Ollama conforme seu sistema operacional a partir do [site oficial](https://ollama.com/).
   - Inicie o serviço Ollama:
     ```bash
     ollama serve
     ```
   - Baixe o modelo desejado (exemplo com gemma3:4b):
     ```bash
     ollama pull gemma3:4b
     ```

## Configuração

- O modelo padrão utilizado é `gemma3:1b`. Você pode alterar a variável `MODEL` no arquivo `app.py` para outro modelo disponível no Ollama.
- O serviço Flask roda por padrão em `http://0.0.0.0:5000`.
- O histórico das conversas é armazenado no arquivo `historico_conversas.db` (SQLite), criado automaticamente na primeira execução.

## Uso

### Via Alexa

Configure sua skill para enviar requisições POST para o endpoint `/` ou `/alexa` deste servidor, conforme esperado pelo seu código.

### Teste Manual

Você pode testar a API usando o `curl` ou ferramentas como Postman:

```bash
curl -X POST http://localhost:5000/alexa -H "Content-Type: application/json" -d "{\"pergunta\": \"Qual a capital da Franca\"}"
```

Resposta esperada:
```json
{"resposta": "Paris, claro! A cidade das luzes e dos croissants deliciosos."}
```

## Memória e Histórico de Conversa

- O assistente mantém um histórico das últimas interações de cada usuário (sessão), permitindo respostas mais contextuais.
- O histórico é salvo em um banco de dados SQLite, garantindo persistência mesmo após reiniciar o servidor.
- Cada sessão é identificada por um `session_id` (usado pela Alexa ou definido como "default" em requisições simples).
- Sessões inativas são limpas automaticamente após um tempo configurável.

## Parâmetros do Modelo

Os parâmetros de geração podem ser ajustados no arquivo `app.py` para personalizar o comportamento das respostas:

- **temperature**: Controla a criatividade da resposta. Valores mais altos (ex: 1.2) tornam as respostas mais variadas e criativas, enquanto valores mais baixos (ex: 0.7) deixam as respostas mais conservadoras.
- **top_k**: Limita o número de opções consideradas para cada palavra gerada. Um valor maior permite mais variedade, um valor menor restringe as opções.
- **top_p**: Controla a diversidade das respostas considerando apenas as palavras mais prováveis até que a soma de suas probabilidades atinja o valor definido (ex: 0.95). Valores mais baixos tornam as respostas mais previsíveis.

Exemplo de configuração no `app.py`:
```python
"params":{
    "temperature": 1.2,
    "top_k": 40,
    "top_p": 0.95
}
```

Ajuste esses parâmetros conforme necessário para o seu caso de uso.

## Estrutura do Projeto

```
.
├── app.py
├── historico_conversas.db
└── README.md
```

## Observações

- O modelo roda localmente, garantindo privacidade e controle total dos dados.
- O histórico de conversas é persistente e pode ser limpo por sessão.
- Ajuste os parâmetros de geração (`temperature`, `top_k`, `top_p`, etc.) em `app.py` conforme necessário para o seu caso de uso.