import importlib
import app.models.Predictions.Recommendation as recommendation
from importlib import reload
import pandas as pd
import os

# Add parent directory to path to import shared modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
print(parent_dir)

importlib.reload(recommendation)
def get_data():
    data_path = parent_dir + '/data/'
    personne_path= data_path +'personne_phy_final.xlsx'
    df=pd.read_excel(personne_path )
    return len(df),df
def generate_recommendations(a,b,df):
    model_path=parent_dir + '/models/'
    data_path = parent_dir + '/data/'

    excel_filename = data_path + 'mapping_produit_profile.pkl'
    clustersPath= model_path + 'penetration_par_cluster.xlsx'
    contrats_path=data_path +'contratcs_final.xlsx'
    
    kmeans_filename=model_path+'kmeans_model_20250829_223401.joblib'

    
    contrats=pd.read_excel(contrats_path)
    
# Forcez le rechargement du module

    categorical_cols = ["CODE_SEXE", "SITUATION_FAMILIALE", "LIB_PROFESSION", "LIB_SECTEUR_ACTIVITE"]
    # Recréez l'instance
    data_processor = recommendation.DataPreprocessing(
     
    
        kmeans_path=kmeans_filename,
        profile_mapping_path=excel_filename,
        clustersPath=clustersPath
    
    )
    df=df.iloc[a:b]
    data_processor.input_processing( df, categorical_cols)
    
    df=data_processor.clustering_layer( df)
    df=data_processor.client_segmentation(df)
    contrat,detail=data_processor.filtrer_contrats_plusieurs_personnes(df,contrats)
    recommendation_df1=data_processor.get_top_products_for_clients_df_vectorized_matrix( df,contrat,detail)
    data=data_processor.prepare_client_data(recommendation_df1, contrat)
    return data
#print(generate_recommendations(0,5)) 