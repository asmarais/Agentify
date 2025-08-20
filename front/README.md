# Interface Recherche Client et Génération Pitch

Cette application Streamlit permet de rechercher un client, compléter ses informations, analyser ses besoins, générer des recommandations et un pitch commercial, et envoyer le message sur plusieurs canaux.

## Fonctionnalités

- **Recherche client** par référence
- **Affichage des informations client** (nom, âge, métier, contrats souscrits, contacts)
- **Complétion des informations manquantes** via un formulaire
- **Analyse et recommandations** basées sur le profil client
- **Génération automatique de pitch commercial**
- **Affinage du pitch** via une interface de chat avec l'IA
- **Envoi multicanal** (Email, WhatsApp, SMS)

## Installation

1. Clonez ce dépôt
2. Installez les dépendances :

```bash
pip install -r requirements.txt
```

## Utilisation

1. Lancez l'application :

```bash
streamlit run app.py
```

2. Accédez à l'application dans votre navigateur (généralement à l'adresse http://localhost:8501)
3. Utilisez la barre latérale pour rechercher un client par sa référence
4. Complétez les informations manquantes si nécessaire
5. Cliquez sur "Analyser" pour générer des recommandations et un pitch commercial
6. Affinez le pitch via l'interface de chat
7. Envoyez le message via le canal de votre choix

## Données de test

L'application génère automatiquement des données fictives pour les tests. Vous pouvez voir les références clients disponibles dans la section "Références clients disponibles" de la barre latérale.

## Structure du projet

- `app.py` : Application Streamlit principale
- `data_generator.py` : Module de génération de données fictives
- `requirements.txt` : Liste des dépendances
- `clients_data.csv` : Fichier de données clients généré automatiquement (créé au premier lancement)