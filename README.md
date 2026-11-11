# TTMC Generator

Outil pour créer et imprimer des cartes de jeu *Tu te mets combien en…* personnalisées, avec génération des questions par IA.

Chaque carte contient 10 questions/réponses sur un thème donné. L'outil génère un PDF prêt à imprimer en format US Letter paysage, avec 4 cartes recto/verso par feuille (3 plis croisés + découpe).

---

## Prérequis

Avant d'installer, assure-toi d'avoir :

1. **[uv](https://docs.astral.sh/uv/)** — installé automatiquement par le script d'installation
2. **[Typst](https://github.com/typst/typst/releases)** — moteur de mise en page pour générer les PDFs. Télécharge le binaire pour ton système et mets-le dans ton PATH
3. **Une clé API Anthropic** — obtiens-en une sur [console.anthropic.com](https://console.anthropic.com). Elle sera saisie directement dans l'interface web

---

## Installation

### macOS / Linux

```bash
./install.sh
```

### Windows

Double-cliquer sur `install.bat`.

Le script installe `uv` puis les dépendances Python dans un virtualenv local (`.venv/`). Il ne modifie rien en dehors du dossier du projet.

---

## Lancer l'application

### macOS / Linux

```bash
./lancer.sh
```

### Windows

Double-cliquer sur `lancer.bat`.

L'interface s'ouvre automatiquement dans le navigateur à l'adresse `http://localhost:5173`.

---

## Désinstallation

Supprimer le dossier du projet. Tout est contenu dedans.

Pour désinstaller `uv` si tu l'avais installé via ce projet :

```bash
# macOS / Linux
rm -rf ~/.local/bin/uv ~/.local/bin/uvx

# Windows : supprimer %USERPROFILE%\.local\bin\uv.exe
```

---

## Utilisation

### 1. Configurer la clé API et la couleur

En bas de la barre latérale gauche :
- **Couleur du thème** : color picker qui définit la couleur de l'en-tête sur toutes les cartes
- **Clé API Anthropic** : colle ta clé `sk-ant-…` ici. Elle est sauvegardée localement dans `config.json` et n'est jamais partagée

### 2. Créer une carte

Clique sur **+** dans la barre latérale pour créer une nouvelle carte. Donne-lui un thème (ex. "Mario", "Pokémon", "Années 2000").

### 3. Générer les questions par IA

- **✨ Générer tout** : génère les 10 questions et réponses d'un coup
- **✨** sur chaque ligne : régénère une seule question/réponse

Les questions sont générées par ordre de difficulté croissante (1 = évidence, 10 = quasi impossible) avec un mélange de culture générale et de questions personnelles sur le/la destinataire (réponse `[Destinataire]` — c'est lui/elle qui répond en live).

### 4. Modifier manuellement

Les champs question et réponse sont éditables directement dans l'interface.

### 5. Enregistrer

Clique sur **💾 Enregistrer**. Les cartes sont sauvegardées dans `data/` au format JSON.

### 6. Configurer le prompt IA

Clique sur **Configurer le prompt IA** pour personnaliser les instructions envoyées au modèle. Variables disponibles : `{theme}`, `{questions_existantes}`, `{reponses_existantes}`.

### 7. Exporter en PDF

- **Exporter cette carte** : génère un PDF pour la carte ouverte
- **Exporter toutes les cartes** : génère un PDF par tranche de 4 cartes

Les PDFs sont enregistrés dans `output/` sous la forme `page-1.pdf`, `page-2.pdf`, etc.

### 8. Imprimer

Chaque PDF est une feuille US Letter paysage avec 4 cartes différentes :

```
[ Questions 1 ][ Réponses 1 ][ Questions 2 ][ Réponses 2 ]
[ Questions 3 ][ Réponses 3 ][ Questions 4 ][ Réponses 4 ]
```

Imprimer en **recto/verso** (retourner sur le bord court), puis :
- Plier en deux verticalement (pli central)
- Plier en deux horizontalement
- Découper les 3 bords extérieurs pour séparer les 4 cartes

Le bord central est commun au recto et au verso — pas besoin de le couper.

---

## Structure du projet

```
ttmc-generator/
├── app.py           — serveur Flask local
├── cartes.typ       — template Typst (mise en page)
├── pyproject.toml   — dépendances Python
├── install.sh / .bat
├── lancer.sh / .bat
├── prompt.txt       — prompt IA par défaut (personnalisable)
├── tests/
│   └── test_generate.py
├── static/
│   └── index.html   — interface web
├── data/            — JSONs des cartes (ignoré par git)
└── output/          — PDFs générés (ignoré par git)
```

---

## Format JSON d'une carte

```json
{
  "theme": "Mario",
  "items": [
    {
      "num": 1,
      "question": "Comment s'appelle le célèbre moustachu en salopette rouge de Nintendo ?",
      "reponse": "Mario"
    }
  ]
}
```

---

## Générer un PDF manuellement (sans l'interface)

```bash
typst compile cartes.typ \
  --root . \
  --input config=/config.json \
  --input data1=/data/mario.json \
  --input data2=/data/pokemon.json \
  --input data3=/data/blackmink.json \
  --input data4=/data/annees2000.json \
  output/page-1.pdf
```

---

## Tests

```bash
# Tests mock uniquement
uv run python tests/test_generate.py

# Tests mock + tests réels API (clé lue depuis config.json)
uv run python tests/test_generate.py --real
```

---

## Licence

Ce projet est publié sous licence **Creative Commons Attribution - Pas d'Utilisation Commerciale 4.0 International (CC BY-NC 4.0)**.

Tu es libre de partager, redistribuer et modifier ce projet, à condition de :
- Créditer l'auteur original
- Ne pas en faire un usage commercial

[Voir le texte complet de la licence](https://creativecommons.org/licenses/by-nc/4.0/deed.fr)
