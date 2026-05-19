# Design — Socle du serveur MCP Odoo (Phase 1)

- **Date** : 2026-05-19
- **Statut** : validé en brainstorming, à transformer en plan d'implémentation
- **Périmètre** : Phase 1 (le socle) uniquement. Les phases 2 à 4 feront chacune l'objet de leur propre cadrage.

## 1. Contexte & objectif

Remplacer le MCP tiers actuel (Pantalytics, `pnl-mcp`) par un **serveur MCP maison** : propre, sécurisé, sous notre contrôle total, sans dépendance à un service externe.

- **Utilisateurs** : 4 collègues, utilisant Claude **principalement sur mobile** (app Claude / claude.ai).
- **Usage** : prospection commerciale et gestion Odoo (CRM, devis, commandes, factures, achats, livraisons, newsletters).
- **Odoo cible** : `magin.odoo.com` — Odoo 19 Enterprise (Online / SaaS).
- **Base de test** : `https://magin-support-20260519-qudg.odoo.com` (copie de la production, fournie par l'utilisateur).
- **Compte Odoo** : les 4 collègues **partagent un seul et même compte Odoo**. Aucune attribution individuelle n'est nécessaire ni possible.

### Motivation (« le rendre plus puissant »)

Au-delà de la simple parité avec le MCP tiers, le socle apporte une capacité que le tiers n'avait pas : **exécuter les actions/boutons de workflow d'Odoo** (confirmer un devis, valider une commande, comptabiliser une facture, créer une livraison…).

## 2. Feuille de route (4 phases)

| Phase | Contenu | Statut |
|---|---|---|
| **1. Le socle** | Serveur MCP : hébergement, sécurité, couche générique complète, garde-fous, bibliothèque de savoir-faire. | **Ce document** |
| 2. Pack prospection | Outils métier de haut niveau pour le CRM. | À cadrer |
| 3. Pack cycle de vente | Outils métier devis → commande → livraison → facture. | À cadrer |
| 4. Pack newsletter | Création de campagnes email selon les templates de marque. | À cadrer |

Chaque phase aura sa propre spéc → plan → réalisation. **Le socle débloque déjà ~80 % des besoins** via la couche générique ; les phases 2-4 ne font qu'améliorer le confort et la sûreté.

## 3. Décisions de cadrage

| Sujet | Décision |
|---|---|
| Déploiement | Serveur MCP **distant**, hébergé sur un **VPS Hostinger** (plan KVM 1, ~5-6 €/mois, à souscrire). |
| Transport | MCP distant via **HTTPS**, ajouté comme **connecteur** dans l'app Claude. Fonctionne sur mobile. |
| Langage | **Python** + framework **FastMCP**. |
| API Odoo | API standard Odoo (**XML-RPC**). |
| Opérations | **Parité totale** avec le MCP tiers (lire / créer / modifier / supprimer / importer) **+ exécution d'actions de workflow Odoo**. |
| Identité | Un seul compte Odoo partagé → une seule clé API. Pas d'OAuth multi-utilisateurs. |
| Test | Validation complète sur la **base de test Odoo** avant bascule sur la production. |

## 4. Architecture d'ensemble

```
 [ Téléphone d'un collègue ] — App Claude
        │  (1) demande en langage naturel
        ▼
 ┌─── LLM de Claude (cloud Anthropic) ──────────────────┐
 │  • interprète la demande                             │
 │  • mobilise éventuellement un savoir-faire (skill)   │
 │  • décide quel(s) outil(s) MCP appeler + arguments   │
 └────────────────────┬─────────────────────────────────┘
                       │  appel d'outil précis (HTTPS)
                       ▼
 ┌─── VPS Hostinger ──────────────────────────────────┐
 │   Caddy      → HTTPS + sous-domaine                │
 │     │          (ex. mcp.<domaine>.com)             │
 │     ▼                                              │
 │   Serveur MCP Python (FastMCP), service systemd    │
 │     • vérifie le secret d'accès                    │
 │     • traduit les demandes en appels Odoo          │
 └─────┬──────────────────────────────────────────────┘
       │  API standard Odoo (clé API du compte partagé)
       ▼
 [ magin.odoo.com ]  — Odoo, compte partagé
                       ▲
                       │  résultat brut
 ┌─── LLM de Claude ───┴────────────────────────────────┐
 │  • interprète le résultat (peut rappeler un outil)   │
 │  • rédige la réponse pour le collègue                │
 └──────────────────────────────────────────────────────┘
```

**Principe clé** : le serveur MCP ne contient **aucune IA**. Toute l'interprétation se fait dans le LLM de Claude, *avant* (comprendre + choisir l'outil) et *après* (interpréter le résultat + répondre). Le serveur est un exécutant déterministe. Le LLM peut **boucler** : appeler un outil, voir le résultat, en appeler un autre.

**Pièces** : le **VPS** (la machine), **Caddy** (portier HTTPS), le **serveur MCP Python** (cerveau qui parle à Odoo). Une seule clé API Odoo, stockée uniquement sur le VPS, jamais sur les téléphones.

## 5. Sécurité (5 couches)

1. **Portillon d'accès — secret partagé.** À l'ajout du connecteur, le collègue saisit une fois un mot de passe partagé connu des 4. Sans lui, le serveur refuse tout. Répond à la seule question pertinente : « est-ce l'un de nos 4, ou un inconnu ? ».
2. **HTTPS de bout en bout.** Caddy chiffre tout le trafic (certificat gratuit, renouvellement automatique).
3. **Clé API Odoo confinée.** Stockée uniquement sur le VPS, dans un fichier protégé. Jamais sur les téléphones ni dans Claude. Téléphone perdu → changer le secret partagé suffit.
4. **Liste blanche de modèles.** Parité totale sur les *opérations*, mais le serveur ne travaille que sur une **liste de modèles métier** définie en config (CRM, contacts, devis/commandes, factures, achats, livraisons, newsletters…). Les tables système d'Odoo (utilisateurs, réglages, droits) restent hors d'atteinte.
5. **Durcissement du VPS.** Pare-feu n'ouvrant que le port HTTPS, accès SSH par clé, mises à jour de sécurité.

## 6. Catalogue d'outils — couche générique complète (v1)

La couche générique est **complète dès la v1** : ce sont des primitives toujours nécessaires, pas des options spéculatives.

### Groupe A — Découverte & lecture
- État de la connexion Odoo.
- Lister les modèles métier disponibles.
- **Inspecter les champs d'un modèle** (noms, types, obligatoires, valeurs possibles). *Outil fondamental : sans lui, Claude devine les champs et échoue.*
- Chercher des records (avec pagination : limite, décalage, tri).
- Lire le détail d'un record.
- Compter des records sans tout télécharger.
- Statistiques agrégées (regroupements : « CA par mois », « leads par étape »).

### Groupe B — Écriture
- Créer un ou plusieurs records.
- Modifier un ou plusieurs records.
- Supprimer un ou plusieurs records *(encadré — §7)*.
- Import massif de records *(encadré — §7)*.
- Joindre un fichier (envoi) à un record.
- **Télécharger** un fichier joint existant.
- Poster un message dans le chatter d'un record.

### Groupe C — Actions Odoo (le gain de puissance)
- **Exécuter une action de workflow Odoo** : confirmer un devis, valider une commande, comptabiliser une facture, créer une livraison, valider un bon de commande, envoyer un document par email…
- **Composer et envoyer un email** depuis Odoo vers un contact / client : Claude rédige l'objet et le corps, le serveur l'envoie via la messagerie d'Odoo (l'email part de l'adresse du compte Odoo, est tracé dans le chatter du record concerné). Distinct du message chatter *interne* du groupe B, qui n'est pas un vrai email. Par sûreté — un email est visible du destinataire et difficile à rétracter — l'envoi se fait après **confirmation explicite**.
- **Générer le PDF / rapport officiel** d'un record (devis, facture, bon de livraison).
- Gouverné par une **liste blanche d'actions** en config : seules les actions métier autorisées sont exécutables — pas n'importe quelle méthode interne d'Odoo.

### Groupe D — Bibliothèque de savoir-faire
- Lister les skills métier disponibles.
- Récupérer le contenu d'un skill (Claude s'en sert pour bien exécuter).

> Les groupes A et B assurent la **parité** avec le MCP tiers. Les groupes C et D sont le gain de puissance.

## 7. Garde-fous, anti-doublons & audit

### Garde-fous sur les opérations massives (suppression & import)
- **Deux temps** : essai à blanc d'abord (le serveur ne touche à rien, renvoie un aperçu des records concernés), exécution seulement après **confirmation explicite**.
- **Plafond strict** : pas plus de N records par appel (valeur par défaut à fixer, ex. 50). Au-delà : refusé, il faut découper.

### Anti-doublons (création de contacts & leads)
- Avant création, le serveur cherche automatiquement un existant (email, téléphone, nom similaire).
- Correspondance probable trouvée → ne crée pas en aveugle, signale l'existant et propose de compléter ou de forcer.
- Création forcée possible via un indicateur explicite.

### Journal d'audit
- Chaque écriture (création / modification / suppression / import / action) est journalisée sur le VPS : horodatage, opération, modèle, records concernés, résumé, succès/échec.
- Seule traçabilité disponible (compte Odoo partagé) : enregistre **quoi et quand**, pas **qui**.
- Consultable par Claude (outil dédié) et directement sur le VPS.

## 8. Structure du code

Modules indépendants, une responsabilité chacun.

```
odoo-mcp-server/
├── config.py        → charge la config (clé API Odoo, listes blanches,
│                       plafonds, secret d'accès) depuis un fichier protégé
├── auth.py          → portillon : vérifie le secret partagé
├── odoo_client.py   → point de passage UNIQUE vers Odoo (connexion,
│                       appels API, sessions)
├── guardrails.py    → essai à blanc + plafond + confirmation
├── dedup.py         → détection des doublons (contacts / leads)
├── audit.py         → écrit le journal d'audit
├── skills/          → bibliothèque de savoir-faire (documents)
│   └── loader.py    → les charge et les sert à Claude
├── tools/           → un module par groupe d'outils — AUTO-DÉCOUVERTS
│   ├── read.py        (chercher, lire, inspecter champs, compter, stats)
│   ├── write.py       (créer, modifier, supprimer, importer, fichiers)
│   └── actions.py     (exécuter les workflows Odoo, générer PDF)
└── server.py        → démarre le serveur MCP, branche le tout
```

- `odoo_client.py` est le **seul** module à parler à Odoo → un seul endroit à maintenir.
- Le dossier `tools/` est **auto-découvert** : ajouter un outil = déposer un fichier.
- `skills/` se remplit de simples documents → étoffer le savoir-faire sans code.

## 9. Leviers d'extension (« étoffer au fur et à mesure »)

Le socle est conçu pour grandir avec l'usage réel, via trois leviers du moins au plus coûteux :

| Levier | Pour ajouter… | Coût |
|---|---|---|
| 1. Config | un modèle ou une action Odoo à la liste blanche | éditer un fichier, recharger — zéro code |
| 2. Skill | un savoir-faire (charte, procédure) | écrire un document — zéro code |
| 3. Module outil | une vraie capacité technique nouvelle | un petit module isolé dans `tools/` |

La couche **générique** est figée et complète en v1 ; c'est la couche **métier** (phases 2-4) qui s'étoffe via ces leviers.

## 10. Gestion des erreurs

- Erreurs Odoo **traduites en messages clairs** pour Claude (jamais de jargon technique brut).
- Le serveur ne plante pas sur une demande mal formée : il renvoie une erreur structurée et reste debout.
- Odoo injoignable → message clair + nouvelle tentative automatique.
- Secret refusé / plafond dépassé / confirmation manquante → refus net et explicite.

## 11. Tests

1. **Logique interne** (garde-fous, anti-doublons, audit, config, sécurité) : tests automatisés **sans Odoo**, rendus possibles par le découpage en modules.
2. **Dialogue avec Odoo** : testé contre la **base de test** `magin-support-20260519-qudg.odoo.com`, jamais la production.
3. Bascule sur la production seulement après validation complète sur la base de test.

## 12. Hors périmètre du socle

- Outils métier de haut niveau (« mon pipeline », « relances du jour »…) → phases 2-3.
- Création de newsletters au design de marque → phase 4.
- OAuth / identité multi-utilisateurs → non requis (compte Odoo partagé).
- Hébergement mutualisé Hostinger → écarté (incompatible avec un service permanent).

## 13. Points ouverts pour l'implémentation

- Choix du sous-domaine pour l'URL du connecteur.
- Valeur exacte du plafond d'opérations massives (défaut proposé : 50).
- Liste blanche initiale précise des modèles et des actions.
- Mécanisme exact du secret partagé côté connecteur Claude (jeton statique vs. OAuth minimal) — à trancher au plan d'implémentation selon ce que l'app Claude accepte pour un connecteur personnalisé.
