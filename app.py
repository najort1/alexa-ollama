from flask import Flask, request, jsonify
import requests
import json
import os
import time
from datetime import datetime, timedelta
import threading
import sqlite3

app = Flask(__name__)

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "gemma3:1b"

# Configurações do histórico
MAX_HISTORY_SIZE = 10
MAX_CONTEXT_EXCHANGES = 5
HISTORY_DB_PATH = "historico_conversas.db"
INACTIVE_SESSION_TIMEOUT = 3600

INSTRUCOES = (
    "Pode responder perguntas, contar piadas, criar músicas, inventar histórias e participar de conversas leves. "
    "Limite sua resposta a no máximo 800 caracteres. "
    "Não use emojis nem formatações de texto. "
    "Use apenas pontuação simples: ponto, vírgula, dois pontos e ponto e vírgula. "
    "Não use aspas, parênteses, colchetes, barras ou asteriscos. "
    "Escreva números romanos por extenso."
)


historicos_cache = {}
session_last_access = {}


def inicializar_db():
    conn = sqlite3.connect(HISTORY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS historico (
        session_id TEXT,
        timestamp INTEGER,
        indice INTEGER,
        pergunta TEXT,
        resposta TEXT,
        PRIMARY KEY (session_id, indice)
    )
    ''')
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_session_timestamp ON historico (session_id, timestamp)
    ''')
    conn.commit()
    conn.close()

# Carregar histórico do banco de dados para memória
def carregar_historico(session_id):
    if session_id in historicos_cache:
        return
    
    conn = sqlite3.connect(HISTORY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT pergunta, resposta FROM historico WHERE session_id = ? ORDER BY indice",
        (session_id,)
    )
    historicos_cache[session_id] = [
        {"usuario": row[0], "assistente": row[1]}
        for row in cursor.fetchall()
    ]
    conn.close()
    session_last_access[session_id] = time.time()

# Salvar interação no banco de dados
def salvar_interacao(session_id, pergunta, resposta, indice=None):
    conn = sqlite3.connect(HISTORY_DB_PATH)
    cursor = conn.cursor()
    
    if indice is None:
        # Obter o próximo índice disponível
        cursor.execute(
            "SELECT MAX(indice) FROM historico WHERE session_id = ?",
            (session_id,)
        )
        resultado = cursor.fetchone()
        indice = 0 if resultado[0] is None else resultado[0] + 1
    
    timestamp = int(time.time())
    cursor.execute(
        "INSERT OR REPLACE INTO historico (session_id, timestamp, indice, pergunta, resposta) VALUES (?, ?, ?, ?, ?)",
        (session_id, timestamp, indice, pergunta, resposta)
    )
    conn.commit()
    conn.close()


def limpar_historico(session_id):
    historicos_cache[session_id] = []
    session_last_access[session_id] = time.time()
    
    conn = sqlite3.connect(HISTORY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM historico WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

# Atualizar histórico com nova interação
def atualizar_historico(session_id, usuario, assistente):
    # Carregar histórico se não estiver em cache
    if session_id not in historicos_cache:
        carregar_historico(session_id)
    else:
        session_last_access[session_id] = time.time()
    
    # Adicionar nova interação ao cache
    if session_id not in historicos_cache:
        historicos_cache[session_id] = []
    
    historicos_cache[session_id].append({
        "usuario": usuario,
        "assistente": assistente
    })
    
    # Limitar tamanho do histórico em cache
    if len(historicos_cache[session_id]) > MAX_HISTORY_SIZE:
        # Remover registros antigos mantendo apenas os MAX_HISTORY_SIZE mais recentes
        historicos_cache[session_id] = historicos_cache[session_id][-MAX_HISTORY_SIZE:]
    
    # Salvar no banco de dados
    indice = len(historicos_cache[session_id]) - 1
    salvar_interacao(session_id, usuario, assistente, indice)


def obter_historico(session_id, max_trocas=MAX_CONTEXT_EXCHANGES):
    if session_id not in historicos_cache:
        carregar_historico(session_id)
    else:
        session_last_access[session_id] = time.time()
    
    return historicos_cache.get(session_id, [])[-max_trocas:]


def montar_contexto(historico):
    if not historico:
        return ""
    
    
    # Construir contexto básico com o histórico
    contexto_base = "\n".join(
        f"Usuário: {par['usuario']}\nAssistente: {par['assistente']}"
        for par in historico
    )
    
    return contexto_base + "\n\n"

def gerar_resposta(pergunta, historico=None):
    pergunta = pergunta.replace("Modo inteligente", "").strip()
    if not pergunta:
        return "Você não disse nada."

    contexto = montar_contexto(historico)
    prompt = f"{INSTRUCOES}\n{contexto}Usuário: {pergunta}\nAssistente:"

    print("=== [LOG] Prompt enviado para IA ===")
    print(prompt)

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        resposta = response.json().get("response", "Desculpe, não entendi.")
        print("=== [LOG] Resposta da IA ===")
        print(resposta)
        return resposta.strip()[:800]
    except Exception as e:
        print(f"=== [LOG] Erro ao consultar a IA: {e}")
        return f"Erro ao consultar a IA: {e}"

# Limpar sessões inativas periodicamente
def limpar_sessoes_inativas():
    while True:
        try:
            tempo_atual = time.time()
            sessoes_para_remover = []
            
            for session_id, ultimo_acesso in session_last_access.items():
                if tempo_atual - ultimo_acesso > INACTIVE_SESSION_TIMEOUT:
                    sessoes_para_remover.append(session_id)
            
            for session_id in sessoes_para_remover:
                if session_id in historicos_cache:
                    del historicos_cache[session_id]
                del session_last_access[session_id]
                print(f"=== [LOG] Sessão inativa removida do cache: {session_id} ===")
            
            # 15 minutos por iteração
            time.sleep(900)
        except Exception as e:
            print(f"=== [LOG] Erro ao limpar sessões inativas: {e}")
            time.sleep(60)  # Em caso de erro, tentar novamente em 1 minuto

@app.route("/alexa", methods=["POST"])
def webhook_alexa_teste():
    data = request.get_json()
    pergunta = data.get("pergunta")
    if not pergunta:
        return jsonify({"resposta": "Você não disse nada."})
    resposta = gerar_resposta(pergunta)
    return jsonify({"resposta": resposta})

@app.route("/", methods=["POST"])
def webhook_alexa():
    req = request.get_json()
    session_id = req.get("session", {}).get("sessionId", "default")
    print(f"=== [LOG] Sessão: {session_id} ===")

    request_type = req.get("request", {}).get("type")

    if request_type == "LaunchRequest":
        print(f"=== [LOG] Nova sessão iniciada: {session_id} ===")
        limpar_historico(session_id)
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": "Bem-vindo ao modo inteligente! Você pode me perguntar qualquer coisa."
                },
                "shouldEndSession": False
            }
        })

    if request_type == "IntentRequest":
        intent_name = req["request"]["intent"]["name"]
        if intent_name in ["AMAZON.StopIntent", "AMAZON.CancelIntent"]:
            print(f"=== [LOG] Sessão encerrada: {session_id} ===")
            # Deletar somente do cache, não do banco de dados
            if session_id in historicos_cache:
                del historicos_cache[session_id]
            if session_id in session_last_access:
                del session_last_access[session_id]
            return jsonify({
                "version": "1.0",
                "response": {
                    "outputSpeech": {
                        "type": "PlainText",
                        "text": "Até logo! Sempre que precisar de conhecimento, estarei por aqui."
                    },
                    "shouldEndSession": True
                }
            })

    try:
        pergunta = req["request"]["intent"]["slots"]["pergunta"]["value"]
        print(f"=== [LOG] Pergunta recebida: {pergunta} ===")
    except (KeyError, TypeError):
        print("=== [LOG] Erro ao extrair a pergunta do intent ===")
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": "Desculpe, não entendi sua pergunta. Diga Modo inteligente antes de perguntar."
                },
                "shouldEndSession": False
            }
        })

    historico = obter_historico(session_id)
    print(f"=== [LOG] Histórico da sessão {session_id}: {len(historico)} trocas ===")

    resposta = gerar_resposta(pergunta, historico)
    atualizar_historico(session_id, pergunta, resposta)

    return jsonify({
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": resposta
            },
            "shouldEndSession": False
        }
    })

if __name__ == "__main__":
    inicializar_db()
    
    # Iniciar thread para limpeza de sessões inativas
    thread_limpeza = threading.Thread(target=limpar_sessoes_inativas, daemon=True)
    thread_limpeza.start()
    
    app.run(debug=True, port=5000, host="0.0.0.0")