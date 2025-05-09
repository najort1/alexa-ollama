from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "gemma3:4b"

def gerar_resposta(pergunta):
    instrucoes = (
        "Responda como se estivesse conversando com um amigo de forma descontraída e divertida. "
        "Seja direto, claro e use um toque de bom humor quando fizer sentido. "
        "Evite ser muito formal. Evite jargões técnicos. "
        "Responda de forma leve e criativa, sem parecer um robô. "
        "Limite sua resposta a no máximo 500 caracteres. "
        "Pergunta: "
    )

    pergunta = pergunta.replace("Modo inteligente", "").strip()
    if not pergunta:
        return "Você não disse nada."
    
    prompt_final = f"{instrucoes}{pergunta}"
    payload = {
        "model": MODEL,
        "prompt": prompt_final,
        "stream": False,
        "params":{
            "temperature": 1.2,
            "top_k": 40,
            "top_p": 0.95
        }
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        resposta = response.json().get("response", "Desculpe, não entendi.")
    except Exception as e:
        resposta = f"Erro ao consultar a IA: {e}"
    return resposta.strip()[:800]

@app.route("/alexa", methods=["POST"])
def alexa_webhook():
    data = request.get_json()
    pergunta = data.get("pergunta")
    print("Recebido da Alexa:", data)
    if not pergunta:
        return jsonify({"resposta": "Você não disse nada."})
    resposta = gerar_resposta(pergunta)
    return jsonify({"resposta": resposta})

@app.route("/", methods=["POST"])
def alexa_handler():
    req = request.get_json()

    request_type = req.get("request", {}).get("type")
    if request_type == "LaunchRequest":
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": (
                        "Bem-vindo ao modo inteligente! "
                        "Você pode me perguntar qualquer coisa."
                    )
                },
                "shouldEndSession": False
            }
        })

    if request_type == "IntentRequest":
        intent_name = req["request"]["intent"]["name"]
        if intent_name in ["AMAZON.StopIntent", "AMAZON.CancelIntent"]:
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
        intent = req["request"]["intent"]
        pergunta = intent["slots"]["pergunta"]["value"]
        
    except (KeyError, TypeError):
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": "Desculpe, não entendi sua pergunta. Experimente falar Modo inteligente antes de perguntar."
                },
                "shouldEndSession": False
            }
        })
    resposta = gerar_resposta(pergunta)
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
    app.run(debug=True, port=5000, host="0.0.0.0")