"""
Tests pour la génération de questions TTMC.

Mocks seulement  : uv run python tests/test_generate.py
Avec tests réels : uv run python tests/test_generate.py --real

Les tests réels appellent l'API Anthropic (clé dans config.json ou ANTHROPIC_API_KEY).
Les tests d'intégration démarrent le serveur Flask en mode test.
"""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

# Racine du projet
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ── Logique extraite de app.py (à garder en sync) ───────────

def extract_items(message):
    text_block = next((b for b in message.content if b.type == "text"), None)
    if text_block is None:
        text_block = next((b for b in message.content if hasattr(b, "text")), None)
    if text_block is None:
        blocs = [(b.type, vars(b)) for b in message.content]
        raise ValueError(f"Aucun bloc texte. Blocs reçus : {blocs}")

    raw = text_block.text.strip()
    start = raw.find("[")
    end   = raw.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError(f"Réponse non parseable : {raw[:200]}")

    return json.loads(raw[start:end])


# ── Helpers mock ─────────────────────────────────────────────

def make_block(type_, **kwargs):
    return SimpleNamespace(type=type_, **kwargs)

def make_message(blocks, input_tokens=100, output_tokens=200):
    return SimpleNamespace(
        content=blocks,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )

VALID_JSON = '[{"num": 1, "question": "Quel est le Pokémon le plus connu ?", "reponse": "Pikachu"}]'


# ── Tests mock : extraction ──────────────────────────────────

MOCK_SCENARIOS = [
    (
        "Texte brut",
        make_message([make_block("text", text=VALID_JSON)]),
    ),
    (
        "Thinking + texte",
        make_message([
            make_block("thinking", thinking="Je réfléchis...", signature="abc123"),
            make_block("text", text=VALID_JSON),
        ]),
    ),
    (
        "Thinking vide (signature seulement) + texte",
        make_message([
            make_block("thinking", thinking="", signature="abc123"),
            make_block("text", text=VALID_JSON),
        ]),
    ),
    (
        "Plusieurs blocs thinking + texte",
        make_message([
            make_block("thinking", thinking="Réflexion 1...", signature="s1"),
            make_block("thinking", thinking="Réflexion 2...", signature="s2"),
            make_block("text", text=VALID_JSON),
        ]),
    ),
    (
        "Prose avant le JSON",
        make_message([make_block("text", text=f"Voici :\n{VALID_JSON}\nBonne génération !")]),
    ),
    (
        "JSON dans bloc markdown",
        make_message([make_block("text", text=f"```json\n{VALID_JSON}\n```")]),
    ),
    (
        "Bloc inconnu sans .text suivi de texte",
        make_message([
            make_block("tool_use", id="x", name="search"),
            make_block("text", text=VALID_JSON),
        ]),
    ),
    (
        "Thinking only — doit échouer proprement",
        make_message([make_block("thinking", thinking="", signature="abc")]),
        True,  # attendu : exception
    ),
]


def run_mock_tests():
    print("── Tests mock : extraction ─────────────────────────")
    passed = failed = 0
    for scenario in MOCK_SCENARIOS:
        name, message = scenario[0], scenario[1]
        expect_fail = len(scenario) > 2 and scenario[2]
        try:
            items = extract_items(message)
            if expect_fail:
                print(f"  ❌  {name} → aurait dû échouer")
                failed += 1
            else:
                assert isinstance(items, list) and len(items) > 0
                assert "question" in items[0] and "reponse" in items[0]
                print(f"  ✅  {name}")
                passed += 1
        except Exception as e:
            if expect_fail:
                print(f"  ✅  {name} → échoue comme attendu : {e}")
                passed += 1
            else:
                print(f"  ❌  {name} → {e}")
                failed += 1
    return passed, failed


# ── Tests d'intégration Flask ────────────────────────────────

def run_integration_tests(api_key):
    print("── Tests d'intégration Flask ───────────────────────")

    import app as flask_app

    original_load_config = flask_app.load_config
    flask_app.load_config = lambda: {**original_load_config(), "api_key": api_key}

    client = flask_app.app.test_client()
    passed = failed = 0

    carte = {
        "theme": "Pokémon",
        "items": [{"num": i, "question": "", "reponse": ""} for i in range(1, 11)],
    }

    # Test 1 : générer toutes les questions
    print("  → POST /api/generate (toutes les questions)")
    r = client.post("/api/generate",
                    json={"theme": carte["theme"], "items": carte["items"]},
                    content_type="application/json")
    data = r.get_json()
    if r.status_code == 200 and "items" in data and len(data["items"]) > 0:
        print(f"  ✅  Génération complète → {len(data['items'])} items")
        passed += 1
        for key in ("num", "question", "reponse"):
            if key not in data["items"][0]:
                print(f"  ❌  Clé '{key}' manquante")
                failed += 1
    else:
        print(f"  ❌  Génération complète → status={r.status_code} error={data.get('error', '')}")
        failed += 1

    # Test 2 : générer une seule question
    print("  → POST /api/generate (question 3 seulement)")
    r = client.post("/api/generate",
                    json={"theme": carte["theme"], "items": carte["items"], "target_num": 3},
                    content_type="application/json")
    data = r.get_json()
    if r.status_code == 200 and "items" in data:
        print(f"  ✅  Génération question 3 → {data['items']}")
        passed += 1
    else:
        print(f"  ❌  Génération question 3 → status={r.status_code} error={data.get('error', '')}")
        failed += 1

    # Test 3 : clé API manquante
    print("  → POST /api/generate (sans clé API)")
    flask_app.load_config = lambda: {"api_key": ""}
    r = client.post("/api/generate",
                    json={"theme": "Test", "items": []},
                    content_type="application/json")
    data = r.get_json()
    if r.status_code == 400 and "error" in data:
        print(f"  ✅  Sans clé → erreur 400 correcte")
        passed += 1
    else:
        print(f"  ❌  Sans clé → status={r.status_code}")
        failed += 1

    flask_app.load_config = original_load_config
    return passed, failed


# ── Chargement de la clé ─────────────────────────────────────

def load_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    config_path = ROOT / "config.json"
    if config_path.exists():
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        return cfg.get("api_key", "")
    return ""


# ── Tests réels API ──────────────────────────────────────────

def run_real_api_tests(api_key):
    print("── Tests réels API Anthropic ───────────────────────")
    try:
        import anthropic
    except ImportError:
        print("  ⚠️  anthropic non installé")
        return 0, 0

    client = anthropic.Anthropic(api_key=api_key)
    passed = failed = 0

    prompt = (
        'Génère 2 questions sur les Pokémon. '
        'Réponds UNIQUEMENT avec un tableau JSON : '
        '[{"num": 1, "question": "...", "reponse": "..."}]'
    )

    for model, name in [
        ("claude-haiku-4-5", "Haiku 4.5"),
        ("claude-sonnet-5-5", "Sonnet 5.5 (max_tokens=8192)"),
    ]:
        try:
            message = client.messages.create(
                model=model,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            blocs = [b.type for b in message.content]
            print(f"  [{name}] blocs : {blocs}")
            items = extract_items(message)
            assert isinstance(items, list) and len(items) > 0
            print(f"  ✅  {name} → {len(items)} items")
            passed += 1
        except Exception as e:
            print(f"  ❌  {name} → {e}")
            failed += 1

    return passed, failed


# ── Runner ───────────────────────────────────────────────────

if __name__ == "__main__":
    real = "--real" in sys.argv

    mp, mf = run_mock_tests()
    rp = rf = ip = if_ = 0

    if real:
        api_key = load_api_key()
        if not api_key:
            print("  ⚠️  Clé API introuvable")
        else:
            rp, rf = run_real_api_tests(api_key)
            ip, if_ = run_integration_tests(api_key)

    total_p = mp + rp + ip
    total_f = mf + rf + if_
    print(f"\n{total_p} passés, {total_f} échoués")
    sys.exit(0 if total_f == 0 else 1)
