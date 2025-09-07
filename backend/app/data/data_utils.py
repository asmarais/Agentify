
import base64
from io import BytesIO
from typing import Dict, Any
from matplotlib import pyplot as plt
import pandas as pd
import os
import seaborn as sns
# Add parent directory to path to import shared modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
print(parent_dir)


def get_data_stat():
    data_path = parent_dir + '/data/'
    contrats_path= data_path +'contratcs_final.xlsx'
    sinistres_path= data_path +'Data.xlsx'
    contrats=pd.read_excel(contrats_path )
    
    sinistres=pd.read_excel(contrats_path,sheet_name='sinistres' )
    return contrats,sinistres
def generate_person_dashboard(person_id,contrats,sinistres):
   

    # Configuration du style des graphiques
    plt.style.use('default')
    sns.set_palette("husl")
    
    # Initialiser sinistres si non fourni
    if sinistres is None:
        sinistres = pd.DataFrame()
    
    # Filtrer les contrats de la personne
    person_contrats = contrats[contrats['REF_PERSONNE'] == person_id].copy()

    # Convertir les dates en format datetime
    date_columns = ['EFFET_CONTRAT', 'DATE_EXPIRATION', 'PROCHAIN_TERME']
    for col in date_columns:
        if col in person_contrats.columns:
            person_contrats[col] = pd.to_datetime(person_contrats[col], errors='coerce')



    # Fonction pour convertir un graphique en image base64
    def fig_to_base64(fig):
        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)
        image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        buf.close()
        return image_base64

    # Statistiques des contrats
    stats_contrats = person_contrats['LIB_ETAT_CONTRAT'].value_counts().to_dict()
    total_contrats = len(person_contrats)

    # Contrats par état avec produits
    contrats_en_cours = person_contrats[person_contrats['LIB_ETAT_CONTRAT'] == 'EN COURS']
    contrats_expires = person_contrats[person_contrats['LIB_ETAT_CONTRAT'] != 'EN COURS']

    produits_en_cours = contrats_en_cours['LIB_PRODUIT'].value_counts().to_dict()
    produits_expires = contrats_expires['LIB_PRODUIT'].value_counts().to_dict()

    # Statistiques de paiement
    paiement_stats = person_contrats['statut_paiement'].value_counts().to_dict() if 'statut_paiement' in person_contrats.columns else {}

    # Calculer les totaux payés et non payés en TND
    total_paye = 0
    total_non_paye = 0
    if 'somme_quittances' in person_contrats.columns:
        total_paye = person_contrats[person_contrats['statut_paiement'] == 'payé']['somme_quittances'].sum() if 'statut_paiement' in person_contrats.columns else 0
        total_non_paye = person_contrats[person_contrats['statut_paiement'] == 'Non payé']['somme_quittances'].sum() if 'statut_paiement' in person_contrats.columns else 0

    # 1. Graphique: Évolution du nombre de contrats dans le temps
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    if not person_contrats.empty and 'EFFET_CONTRAT' in person_contrats.columns and not person_contrats['EFFET_CONTRAT'].isna().all():
        contrats_par_annee = person_contrats.groupby(person_contrats['EFFET_CONTRAT'].dt.year).size()
        ax1.plot(contrats_par_annee.index, contrats_par_annee.values, marker='o')
        ax1.set_title("Évolution du nombre de contrats souscrits par année")
        ax1.set_xlabel("Année")
        ax1.set_ylabel("Nombre de contrats")
        ax1.grid(True, linestyle='--', alpha=0.7)
    else:
        ax1.text(0.5, 0.5, 'Aucune donnée de contrat', ha='center', va='center', transform=ax1.transAxes)
    img1 = fig_to_base64(fig1)
    plt.close(fig1)

    # 2. Graphique: Répartition des contrats par statut de paiement
    fig2, ax2 = plt.subplots(figsize=(8, 8))
    if paiement_stats:
        colors = ['#4CAF50' if x == 'payé' else '#F44336' for x in paiement_stats.keys()]
        ax2.pie(paiement_stats.values(), labels=paiement_stats.keys(), autopct='%1.1f%%', startangle=90, colors=colors)
        ax2.set_title("Répartition des contrats par statut de paiement")
    else:
        ax2.text(0.5, 0.5, 'Aucune donnée de paiement', ha='center', va='center', transform=ax2.transAxes)
    img2 = fig_to_base64(fig2)
    plt.close(fig2)

    # 3. Graphique: Répartition des contrats par branche
    fig3, ax3 = plt.subplots(figsize=(10, 6))
    if 'branche' in person_contrats.columns:
        branche_stats = person_contrats['branche'].value_counts()
        ax3.bar(range(len(branche_stats)), branche_stats.values)
        ax3.set_title("Répartition des contrats par branche")
        ax3.set_xlabel("Branche")
        ax3.set_ylabel("Nombre de contrats")
        ax3.set_xticks(range(len(branche_stats)))
        ax3.set_xticklabels(branche_stats.index, rotation=45, ha='right')
        ax3.grid(True, linestyle='--', alpha=0.7, axis='y')
    else:
        ax3.text(0.5, 0.5, 'Aucune donnée de branche', ha='center', va='center', transform=ax3.transAxes)
    img3 = fig_to_base64(fig3)
    plt.close(fig3)

    # 4. Graphique: Montant des quittances par produit
    fig4, ax4 = plt.subplots(figsize=(10, 6))
    if not contrats_en_cours.empty and 'somme_quittances' in contrats_en_cours.columns:
        quittances_par_produit = contrats_en_cours.groupby('LIB_PRODUIT')['somme_quittances'].sum().sort_values(ascending=False)
        ax4.bar(range(len(quittances_par_produit)), quittances_par_produit.values)
        ax4.set_title("Montant des quittances par produit (contrats en cours)")
        ax4.set_xlabel("Produit")
        ax4.set_ylabel("Somme des quittances (TND)")
        ax4.set_xticks(range(len(quittances_par_produit)))
        ax4.set_xticklabels(quittances_par_produit.index, rotation=45, ha='right')
        ax4.grid(True, linestyle='--', alpha=0.7, axis='y')
    else:
        ax4.text(0.5, 0.5, 'Aucun contrat en cours ou données manquantes', ha='center', va='center', transform=ax4.transAxes)
    img4 = fig_to_base64(fig4)
    plt.close(fig4)

    # 5. Graphique: Capital assuré par type de produit
    fig5, ax5 = plt.subplots(figsize=(10, 6))
    if 'Capital_assure' in person_contrats.columns:
        capital_par_produit = person_contrats.groupby('LIB_PRODUIT')['Capital_assure'].sum().sort_values(ascending=False)
        ax5.bar(range(len(capital_par_produit)), capital_par_produit.values)
        ax5.set_title("Capital assuré par type de produit")
        ax5.set_xlabel("Produit")
        ax5.set_ylabel("Capital assuré (TND)")
        ax5.set_xticks(range(len(capital_par_produit)))
        ax5.set_xticklabels(capital_par_produit.index, rotation=45, ha='right')
        ax5.grid(True, linestyle='--', alpha=0.7, axis='y')
    else:
        ax5.text(0.5, 0.5, 'Données de capital non disponibles', ha='center', va='center', transform=ax5.transAxes)
    img5 = fig_to_base64(fig5)
    plt.close(fig5)

    # 6. Graphique: Évolution des souscriptions mensuelles
    fig6, ax6 = plt.subplots(figsize=(10, 6))
    if not person_contrats.empty and 'EFFET_CONTRAT' in person_contrats.columns:
        deux_ans = pd.Timestamp.now() - pd.DateOffset(years=2)
        contrats_recent = person_contrats[person_contrats['EFFET_CONTRAT'] >= deux_ans]
        if not contrats_recent.empty:
            contrats_par_mois = contrats_recent.resample('M', on='EFFET_CONTRAT').size()
            ax6.bar(range(len(contrats_par_mois)), contrats_par_mois.values)
            ax6.set_title("Souscriptions mensuelles (2 dernières années)")
            ax6.set_xlabel("Mois")
            ax6.set_ylabel("Nombre de contrats")
            
            # Formater les étiquettes de l'axe x
            n = len(contrats_par_mois)
            step = max(1, n // 6)
            indices = list(range(0, n, step))
            if n-1 not in indices:
                indices.append(n-1)
            
            labels = [contrats_par_mois.index[i].strftime('%b %Y') for i in indices]
            ax6.set_xticks(indices)
            ax6.set_xticklabels(labels, rotation=45)
            ax6.grid(True, linestyle='--', alpha=0.7, axis='y')
        else:
            ax6.text(0.5, 0.5, 'Aucun contrat récent', ha='center', va='center', transform=ax6.transAxes)
    else:
        ax6.text(0.5, 0.5, 'Aucune donnée de contrat', ha='center', va='center', transform=ax6.transAxes)
    img6 = fig_to_base64(fig6)
    plt.close(fig6)

    # 7. Graphique: Total payé vs non payé
    fig7, ax7 = plt.subplots(figsize=(8, 6))
    categories = ['Payé', 'Non payé']
    montants = [total_paye, total_non_paye]
    if any(montants):
        colors = ['#4CAF50', '#F44336']
        bars = ax7.bar(categories, montants, color=colors)
        ax7.set_title("Montant total payé vs non payé")
        ax7.set_ylabel("Montant (TND)")
        
        for i, v in enumerate(montants):
            ax7.text(i, v + max(montants)*0.01, f'{v:,.0f} TND', ha='center', va='bottom')
        
        ax7.grid(True, linestyle='--', alpha=0.7, axis='y')
    else:
        ax7.text(0.5, 0.5, 'Aucune donnée financière', ha='center', va='center', transform=ax7.transAxes)
    img7 = fig_to_base64(fig7)
    plt.close(fig7)

    # Calculer des KPI supplémentaires
    if len(contrats_expires) > 0:
        produits_uniques_expires = contrats_expires['LIB_PRODUIT'].nunique()
        produits_uniques_encours = contrats_en_cours['LIB_PRODUIT'].nunique()
        taux_renouvellement = (produits_uniques_encours / produits_uniques_expires * 100) if produits_uniques_expires > 0 else 0
    else:
        taux_renouvellement = 0

    valeur_totale = person_contrats['somme_quittances'].sum() if 'somme_quittances' in person_contrats.columns else 0

    # Traitement des sinistres
    total_sinistres = 0
    sinistres_par_etat = {}
    sinistres_par_branche = {}
    sinistres_par_type = {}
    montant_total_sinistres = 0
    montant_encaisse = 0
    montant_a_encaisse = 0
    taux_sinistralite = 0
    img8, img9, img10, img11 = "", "", "", ""

    if not sinistres.empty and 'NUM_CONTRAT' in sinistres.columns:
        person_sinistres = sinistres[sinistres['NUM_CONTRAT'].isin(person_contrats['NUM_CONTRAT'])].copy()
        
        # Convertir les dates en format datetime
        date_columns = ['DATE_SURVENANCE', 'DATE_DECLARATION', 'DATE_OUVERTURE']
        for col in date_columns:
            if col in person_sinistres.columns:
                person_sinistres[col] = pd.to_datetime(person_sinistres[col], errors='coerce')

        # Statistiques des sinistres
        total_sinistres = len(person_sinistres)
        if 'LIB_ETAT_SINISTRE' in person_sinistres.columns:
            sinistres_par_etat = person_sinistres['LIB_ETAT_SINISTRE'].value_counts().to_dict()
        if 'LIB_BRANCHE' in person_sinistres.columns:
            sinistres_par_branche = person_sinistres['LIB_BRANCHE'].value_counts().to_dict()
        if 'LIB_TYPE_SINISTRE' in person_sinistres.columns:
            sinistres_par_type = person_sinistres['LIB_TYPE_SINISTRE'].value_counts().to_dict()

        # Calculer les montants des sinistres
        if 'MONTANT_ENCAISSE' in person_sinistres.columns:
            montant_encaisse = person_sinistres['MONTANT_ENCAISSE'].sum()
        if 'MONTANT_A_ENCAISSER' in person_sinistres.columns:
            montant_a_encaisse = person_sinistres['MONTANT_A_ENCAISSER'].sum()
        
        montant_total_sinistres = montant_encaisse + montant_a_encaisse

        # Taux de sinistralité
        if valeur_totale > 0:
            taux_sinistralite = (montant_total_sinistres / valeur_totale) * 100

        # Graphiques des sinistres
        # Graphique 8: Répartition des sinistres par état
        fig8, ax8 = plt.subplots(figsize=(8, 8))
        if total_sinistres > 0 and sinistres_par_etat:
            ax8.pie(list(sinistres_par_etat.values()), labels=list(sinistres_par_etat.keys()), 
                   autopct='%1.1f%%', startangle=90)
            ax8.set_title("Répartition des sinistres par état")
        else:
            ax8.text(0.5, 0.5, 'Aucun sinistre', ha='center', va='center', transform=ax8.transAxes)
        img8 = fig_to_base64(fig8)
        plt.close(fig8)

        # Graphique 9: Évolution du nombre de sinistres dans le temps
        fig9, ax9 = plt.subplots(figsize=(10, 6))
        if not person_sinistres.empty and 'DATE_SURVENANCE' in person_sinistres.columns:
            sinistres_par_annee = person_sinistres.groupby(person_sinistres['DATE_SURVENANCE'].dt.year).size()
            ax9.plot(sinistres_par_annee.index, sinistres_par_annee.values, marker='o', linestyle='-', color='red')
            ax9.set_title("Évolution du nombre de sinistres par année")
            ax9.set_xlabel("Année")
            ax9.set_ylabel("Nombre de sinistres")
            ax9.grid(True, linestyle='--', alpha=0.7)
        else:
            ax9.text(0.5, 0.5, 'Aucun sinistre', ha='center', va='center', transform=ax9.transAxes)
        img9 = fig_to_base64(fig9)
        plt.close(fig9)

        # Graphique 10: Répartition des sinistres par branche
        fig10, ax10 = plt.subplots(figsize=(10, 6))
        if total_sinistres > 0 and sinistres_par_branche:
            branches = list(sinistres_par_branche.keys())
            counts = list(sinistres_par_branche.values())
            ax10.bar(range(len(branches)), counts)
            ax10.set_title("Répartition des sinistres par branche")
            ax10.set_xlabel("Branche")
            ax10.set_ylabel("Nombre de sinistres")
            ax10.set_xticks(range(len(branches)))
            ax10.set_xticklabels(branches, rotation=45, ha='right')
            ax10.grid(True, linestyle='--', alpha=0.7, axis='y')
        else:
            ax10.text(0.5, 0.5, 'Aucun sinistre', ha='center', va='center', transform=ax10.transAxes)
        img10 = fig_to_base64(fig10)
        plt.close(fig10)

        # Graphique 11: Montants des sinistres
        fig11, ax11 = plt.subplots(figsize=(8, 6))
        if total_sinistres > 0:
            categories = ['Encaisse', 'À encaisser', 'Total']
            montants = [montant_encaisse, montant_a_encaisse, montant_total_sinistres]
            colors = ['#4CAF50', '#FF9800', '#F44336']
            ax11.bar(categories, montants, color=colors)
            ax11.set_title("Montants des sinistres (TND)")
            ax11.set_ylabel("Montant (TND)")
            
            for i, v in enumerate(montants):
                ax11.text(i, v + max(montants)*0.01, f'{v:,.0f} TND', ha='center', va='bottom')
            
            ax11.grid(True, linestyle='--', alpha=0.7, axis='y')
        else:
            ax11.text(0.5, 0.5, 'Aucun sinistre', ha='center', va='center', transform=ax11.transAxes)
        img11 = fig_to_base64(fig11)
        plt.close(fig11)

    # Retourner toutes les données
    return {
        'person_info': {
            'id': person_id,
            'age': age,
            'total_contrats': total_contrats,
            'stats_contrats': stats_contrats,
            'produits_en_cours': produits_en_cours,
            'produits_expires': produits_expires,
            'paiement_stats': paiement_stats,
            'total_paye': total_paye,
            'total_non_paye': total_non_paye,
            'taux_renouvellement': taux_renouvellement,
            'valeur_totale': valeur_totale,
            'total_sinistres': total_sinistres,
            'sinistres_par_etat': sinistres_par_etat,
            'sinistres_par_branche': sinistres_par_branche,
            'sinistres_par_type': sinistres_par_type,
            'montant_total_sinistres': montant_total_sinistres,
            'montant_encaisse': montant_encaisse,
            'montant_a_encaisse': montant_a_encaisse,
            'taux_sinistralite': taux_sinistralite
        },
        'graphs': {
            'evolution_contrats': img1,
            'repartition_paiement': img2,
            'repartition_branche': img3,
            'quittances_par_produit': img4,
            'capital_assure': img5,
            'souscriptions_mensuelles': img6,
            'total_paye_non_paye': img7,
            'sinistres_etat': img8,
            'evolution_sinistres': img9,
            'sinistres_branche': img10,
            'montants_sinistres': img11
        }
    }
def load_excel_data(file_path: str) -> Dict[str, Any]:
    """
    Load data from an Excel file into a dictionary.
    
    Args:
        file_path (str): Path to the Excel file (.xlsx or .xls)
    
    Returns:
        Dict[str, Any]: Data loaded from the Excel file as a dictionary
    
    Raises:
        FileNotFoundError: If the Excel file is not found
        ValueError: If the Excel file is empty or invalid
    """
    try:
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Check if the DataFrame is empty
        if df.empty:
            raise ValueError("Excel file is empty")
        
        # Convert DataFrame to dictionary (records format)
        return df.to_dict(orient="records")
    
    except FileNotFoundError:
        raise FileNotFoundError(f"Excel file not found: {file_path}")
    except Exception as e:
        raise ValueError(f"Failed to load Excel file: {str(e)}")

def get_garanties() -> Dict[str, str]:
    """
    Extract guarantees from the client data.

    Returns:
        Dict[str, str]: A dictionary mapping product names to their guarantees.
    """
   
    dir = os.path.dirname(os.path.abspath(__file__))
 
    file_path = os.path.join(dir, "Description_garanties.xlsx")

    garanties_file = load_excel_data(file_path)
    garanties = {item["LIB_PRODUIT"]: item["Description"] for item in garanties_file}

    return garanties