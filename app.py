"""
TTMC Generator — serveur Flask local
Lance avec : uv run python app.py
"""

import json
import logging
import os
import subprocess
import threading
import traceback
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
import anthropic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ttmc.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ── Chemins ────────────────────────────────────────────────
BASE   = Path(__file__).parent
DATA   = BASE / "data"
OUTPUT = BASE / "output"
DATA.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)

CONFIG_FILE = BASE / "config.json"
PROMPT_FILE = BASE / "prompt.txt"
TYPST_FILE  = BASE / "cartes.typ"
USAGE_FILE  = BASE / "usage.json"

# Sonnet 5.5 — prix par token
PRICE_INPUT_PER_TOKEN  = 2.00 / 1_000_000   # $2 / MTok
PRICE_OUTPUT_PER_TOKEN = 10.00 / 1_000_000  # $10 / MTok

# ── Config par défaut ───────────────────────────────────────
DEFAULT_CONFIG = {"color": "#3a7a2a", "api_key": ""}

DEFAULT_PROMPT = """Tu es un créateur de questions pour un jeu de culture générale inspiré de "Tu te mets combien en...".

Consignes générales :
- Les questions doivent être fun et légères.
- Chaque question doit avoir une réponse courte et précise.
- Ne répète pas les questions déjà existantes.
- Réponds UNIQUEMENT avec un tableau JSON valide de la forme :
  [{"num": 1, "question": "...", "reponse": "..."}, ...]
- Ne génère que les questions manquantes ou demandées.

Difficulté croissante — règle stricte :
- Question 1 : réponse évidente pour tout le monde, même quelqu'un qui ne connaît pas du tout le thème.
- Questions 2-4 : accessibles à quelqu'un qui connaît vaguement le thème.
- Questions 5-7 : nécessitent de connaître le thème correctement.
- Questions 8-9 : pour les vrais connaisseurs.
- Question 10 : quasi impossible, même pour un expert.

Types de questions — mélange 50/50 :

1. Questions de culture générale sur le thème : faits vérifiables, assure-toi que la réponse est exacte.

2. Questions personnelles sur le/la destinataire liées au thème :
   - Porte uniquement sur ses goûts, préférences ou opinions — des choses qu'il/elle peut répondre instantanément.
   - Ne fabrique aucun fait. La question doit pouvoir s'appliquer à n'importe qui.
   - Mets exactement "[Destinataire]" comme réponse — c'est lui/elle qui répondra en live pendant le jeu.

   Formulation — règle absolue : toujours à la 3e personne.

   ✅ Correct :
   - "Quel est le type préféré du/de la destinataire ?"
   - "Le/la destinataire préférait-il/elle les cartes ou les peluches ?"

   ❌ Interdit :
   - "Toi, quel est ton type préféré ?" (2e personne)
   - "Quel est le premier X qu'a obtenu le/la destinataire ?" (souvenir précis invérifiable)
   - "Quelle théorie le/la destinataire connaissait-il/elle ?" (fait inventé)

Thème de la carte : {theme}

Questions déjà existantes :
{questions_existantes}

Réponses déjà existantes :
{reponses_existantes}
"""

app = Flask(__name__, static_folder="static")


# ── Helpers config ──────────────────────────────────────────
def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def load_prompt() -> str:
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8")
    return DEFAULT_PROMPT


def save_prompt(text: str):
    PROMPT_FILE.write_text(text, encoding="utf-8")


def track_usage(cost_usd: float):
    data = json.loads(USAGE_FILE.read_text(encoding="utf-8")) if USAGE_FILE.exists() else {"total_usd": 0.0}
    data["total_usd"] = round(data["total_usd"] + cost_usd, 6)
    USAGE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── Routes API ──────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# Usage
@app.route("/api/usage", methods=["GET"])
def get_usage():
    if USAGE_FILE.exists():
        return jsonify(json.loads(USAGE_FILE.read_text(encoding="utf-8")))
    return jsonify({"total_usd": 0.0})


# Config
@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def post_config():
    cfg = load_config()
    cfg.update(request.json)
    save_config(cfg)
    return jsonify({"ok": True})


# Prompt
@app.route("/api/prompt", methods=["GET"])
def get_prompt():
    return jsonify({"prompt": load_prompt()})


@app.route("/api/prompt", methods=["POST"])
def post_prompt():
    save_prompt(request.json["prompt"])
    return jsonify({"ok": True})


# Cartes
@app.route("/api/cartes", methods=["GET"])
def list_cartes():
    files = sorted(DATA.glob("*.json"))
    cartes = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            cartes.append({"slug": f.stem, "theme": data.get("theme", f.stem)})
        except Exception:
            pass
    return jsonify(cartes)


@app.route("/api/cartes/<slug>", methods=["GET"])
def get_carte(slug):
    path = DATA / f"{slug}.json"
    if not path.exists():
        return jsonify({"error": "not found"}), 404
    return jsonify(json.loads(path.read_text(encoding="utf-8")))


@app.route("/api/cartes/<slug>", methods=["POST"])
def save_carte(slug):
    path = DATA / f"{slug}.json"
    path.write_text(json.dumps(request.json, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"ok": True})


@app.route("/api/cartes/<slug>", methods=["DELETE"])
def delete_carte(slug):
    path = DATA / f"{slug}.json"
    if path.exists():
        path.unlink()
    return jsonify({"ok": True})


# Génération IA
@app.route("/api/generate", methods=["POST"])
def generate():
    body = request.json
    cfg  = load_config()
    api_key = cfg.get("api_key", "")
    if not api_key:
        return jsonify({"error": "Clé API manquante. Configure-la dans les paramètres."}), 400

    theme   = body.get("theme", "")
    items   = body.get("items", [])
    target_num = body.get("target_num")

    questions_existantes = "\n".join(
        f"{it['num']}. {it['question']}" for it in items if it.get("question")
    ) or "Aucune"
    reponses_existantes = "\n".join(
        f"{it['num']}. {it['reponse']}" for it in items if it.get("reponse")
    ) or "Aucune"

    base_prompt = load_prompt().replace('{', '{{').replace('}', '}}') \
        .replace('{{theme}}', theme) \
        .replace('{{questions_existantes}}', questions_existantes) \
        .replace('{{reponses_existantes}}', reponses_existantes)

    if target_num is not None:
        user_msg = (
            f"{base_prompt}\n\n"
            f"Génère uniquement la question et la réponse numéro {target_num}."
        )
    else:
        user_msg = (
            f"{base_prompt}\n\n"
            f"Génère les questions et réponses pour les numéros : {list(range(1, 11))}."
        )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-5-5",
            max_tokens=8192,
            messages=[{"role": "user", "content": user_msg}],
        )
        # Comptabiliser le coût
        usage = message.usage
        cost = usage.input_tokens * PRICE_INPUT_PER_TOKEN + usage.output_tokens * PRICE_OUTPUT_PER_TOKEN
        track_usage(cost)

        # Sonnet 5.5 peut retourner des blocs "thinking" avant le texte
        log.info(f"Blocs reçus : {[(b.type, getattr(b, 'text', '')[:80]) for b in message.content]}")
        text_block = next((b for b in message.content if b.type == "text"), None)
        if text_block is None:
            text_block = next((b for b in message.content if hasattr(b, "text")), None)
        if text_block is None:
            log.error(f"Contenu complet : {message.content}")
            raise ValueError("Aucun bloc texte dans la réponse du modèle")
        raw = text_block.text.strip()
        # Extraire le JSON du texte
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        if start == -1 or end == 0:
            raise ValueError(f"Réponse du modèle non parseable : {raw[:200]}")
        generated = json.loads(raw[start:end])
        return jsonify({"items": generated})
    except Exception as e:
        log.error("Erreur /api/generate :\n" + traceback.format_exc())
        return jsonify({"error": str(e)}), 500


# Génération PDF
@app.route("/api/export", methods=["POST"])
def export():
    body  = request.json
    slugs = body.get("slugs")
    cfg   = load_config()

    if not TYPST_FILE.exists():
        return jsonify({"error": "cartes.typ introuvable"}), 500

    # Écrire config.json à jour (couleur uniquement)
    typst_cfg = {"color": cfg.get("color", "#3a7a2a")}
    CONFIG_FILE.write_text(json.dumps(typst_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    config_abs = "/" + str(CONFIG_FILE.relative_to(BASE))

    all_files = sorted(DATA.glob("*.json")) if not slugs else [DATA / f"{s}.json" for s in slugs]
    missing = [f for f in all_files if not f.exists()]
    files   = [f for f in all_files if f.exists()]

    results = [{"slug": f.stem, "ok": False, "error": "fichier introuvable"} for f in missing]

    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    for batch_num, batch in enumerate(chunks(files, 4), 1):
        out_pdf = OUTPUT / f"page-{batch_num}.pdf"

        cmd = ["typst", "compile", TYPST_FILE.name,
               "--root", str(BASE),
               "--input", f"config={config_abs}"]
        for i, f in enumerate(batch, 1):
            cmd += ["--input", f"data{i}=/" + str(f.relative_to(BASE))]
        cmd.append(str(out_pdf))

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=BASE)
            if r.returncode == 0:
                for f in batch:
                    results.append({"slug": f.stem, "ok": True, "file": str(out_pdf)})
            else:
                for f in batch:
                    results.append({"slug": f.stem, "ok": False, "error": r.stderr})
        except Exception as e:
            log.error(f"Erreur export batch {batch_num} :\n" + traceback.format_exc())
            for f in batch:
                results.append({"slug": f.stem, "ok": False, "error": str(e)})

    return jsonify({"results": results})


# ── Lancement ───────────────────────────────────────────────
if __name__ == "__main__":
    import socket
    def port_libre(p):
        with socket.socket() as s:
            return s.connect_ex(('localhost', p)) != 0
    port = next(p for p in range(5173, 5200) if port_libre(p))
    url  = f"http://localhost:{port}"
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"TTMC Generator → {url}")
    app.run(port=port, debug=False)
