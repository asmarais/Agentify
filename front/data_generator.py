import pandas as pd
import random
from faker import Faker

def generate_fake_clients(num_clients=50):
    """
    Génère un DataFrame pandas contenant des données clients fictives
    
    Args:
        num_clients (int): Nombre de clients à générer
        
    Returns:
        pandas.DataFrame: DataFrame contenant les données clients fictives
    """
    # Initialisation de Faker avec locale française
    fake = Faker(['fr_FR'])
    
    # Listes de valeurs possibles
    metiers = [
        "Ingénieur", "Médecin", "Enseignant", "Commercial", "Consultant", 
        "Artisan", "Fonctionnaire", "Retraité", "Étudiant", "Entrepreneur",
        "Avocat", "Comptable", "Infirmier", "Architecte", "Agriculteur",
        "Chauffeur", "Restaurateur", "Artiste", "Développeur", "Cadre"
    ]
    
    situations_familiales = ["Célibataire", "En couple", "Marié(e)", "Divorcé(e)", "Veuf/Veuve"]
    
    contrats_types = ["Auto", "Habitation", "Santé", "Prévoyance", "Épargne", "Retraite", "Vie"]
    
    # Création des données
    data = {
        "ref_client": [f"CLI{str(i+1000).zfill(5)}" for i in range(num_clients)],
        "nom": [fake.last_name() for _ in range(num_clients)],
        "prenom": [fake.first_name() for _ in range(num_clients)],
        "age": [random.randint(18, 80) for _ in range(num_clients)],
        "metier": [random.choice(metiers) if random.random() > 0.2 else "" for _ in range(num_clients)],
        "situation_familiale": [random.choice(situations_familiales) if random.random() > 0.2 else "" for _ in range(num_clients)],
        "email": [fake.email() if random.random() > 0.15 else "" for _ in range(num_clients)],
        "telephone": [fake.phone_number() if random.random() > 0.15 else "" for _ in range(num_clients)],
    }
    
    # Génération des contrats souscrits
    contrats_souscrits = []
    for _ in range(num_clients):
        num_contrats = random.choices([0, 1, 2, 3, 4], weights=[0.1, 0.3, 0.3, 0.2, 0.1])[0]
        if num_contrats == 0:
            contrats_souscrits.append("")
        else:
            selected_contrats = random.sample(contrats_types, num_contrats)
            contrats_souscrits.append(", ".join(selected_contrats))
    
    data["contrats_souscrits"] = contrats_souscrits
    
    # Création du DataFrame
    df = pd.DataFrame(data)
    
    return df

# Test de la fonction si exécuté directement
if __name__ == "__main__":
    clients_df = generate_fake_clients(5)
    print(clients_df.head())