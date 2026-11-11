// ============================================================
// TTMC – Générateur de cartes
// US Letter paysage, 3 plis croisés → 8 panneaux sur 1 page
// 4 cartes différentes, chacune en recto/verso
// Disposition : [ R1 ][ V1 ][ R2 ][ V2 ]
//               [ R3 ][ V3 ][ R4 ][ V4 ]
// inputs : config, data1, data2, data3, data4
// ============================================================

// ── Dimensions d'un panneau ─────────────────────────────────
#let margin = 6mm
#let card-w = (11in - 2 * margin) / 4
#let card-h = (8.5in - 2 * margin) / 2

// ── Config globale ──────────────────────────────────────────
#let cfg     = json(sys.inputs.at("config", default: "config.json"))
#let couleur = rgb(cfg.color)

// ── Chargement des 4 cartes ─────────────────────────────────
#let load-carte(key) = {
  let path = sys.inputs.at(key, default: "")
  if path == "" { return none }
  let src = json(path)
  (
    theme:     src.theme,
    questions: src.items.map(it => (num: it.num, texte: it.question)),
    reponses:  src.items.map(it => (num: it.num, texte: it.reponse)),
  )
}

#let cartes = (
  load-carte("data1"),
  load-carte("data2"),
  load-carte("data3"),
  load-carte("data4"),
)

// ── Composant : une ligne item ───────────────────────────────
#let item-row(num, texte) = {
  pad(x: 0pt, y: 1pt,
    grid(
      columns: (20pt, 1fr),
      column-gutter: 4pt,
      align(horizon,
        text(weight: "bold", size: 13pt, fill: couleur, str(num))
      ),
      align(horizon,
        text(size: 6pt, fill: black, texte)
      ),
    )
  )
  line(length: 100%, stroke: 0.3pt + luma(200))
}

// ── Composant : un panneau ───────────────────────────────────
#let panneau(carte, items-key) = {
  // Carte absente → panneau vide
  if carte == none {
    return block(width: card-w, height: card-h, fill: none, stroke: none)[]
  }
  let items = carte.at(items-key)
  block(
    width: card-w,
    height: card-h,
    stroke: 0.5pt + luma(180),
    inset: 0pt,
    fill: couleur,
    clip: true,
  )[
    // En-tête
    #block(
      width: 100%,
      inset: (x: 8pt, top: 5pt, bottom: 4pt),
    )[
      #set par(leading: 2pt)
      #align(center)[
        #text(size: 6pt, fill: white, style: "italic")[Tu te mets combien en…]
        #linebreak()
        #text(size: 14pt, weight: "bold", fill: white)[#upper(carte.theme) ?]
      ]
    ]
    // Corps blanc
    #pad(x: 4pt)[
      #block(
        width: card-w - 8pt,
        height: card-h - 38pt,
        fill: white,
        radius: 4pt,
        inset: (x: 6pt, top: 3pt, bottom: 0pt),
        clip: true,
      )[
        #set par(leading: 2pt)
        #stack(
          spacing: 0pt,
          ..items.map(it => item-row(it.num, it.texte))
        )
      ]
    ]
  ]
}

// ── Mise en page ────────────────────────────────────────────
#set page(paper: "us-letter", flipped: true, margin: 6mm)
#set text(lang: "fr", font: "Arial")
#set par(leading: 3pt, spacing: 3pt)

#let c1 = cartes.at(0)
#let c2 = cartes.at(1)
#let c3 = cartes.at(2)
#let c4 = cartes.at(3)

#grid(
  columns: (card-w, card-w, card-w, card-w),
  rows: (card-h, card-h),
  gutter: 0pt,

  // Ligne du haut : cartes 1 et 2
  panneau(c1, "questions"),  // R1
  panneau(c1, "reponses"),   // V1
  panneau(c2, "questions"),  // R2
  panneau(c2, "reponses"),   // V2

  // Ligne du bas : cartes 3 et 4
  panneau(c3, "questions"),  // R3
  panneau(c3, "reponses"),   // V3
  panneau(c4, "questions"),  // R4
  panneau(c4, "reponses"),   // V4
)
