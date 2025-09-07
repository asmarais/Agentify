import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import StandardScaler
from tensorflow import keras  # or import keras
from datetime import datetime, timedelta
from sklearn.metrics.pairwise import cosine_similarity
import joblib

class DataPreprocessing:
    def __init__(self, kmeans_path,profile_mapping_path,clustersPath):
        # Charger les variables d'environnement
       
        # Récupérer le token depuis les variables d'environnement
        
        HF_TOKEN = "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"
        self.model = SentenceTransformer("all-MiniLM-L6-v2", use_auth_token=HF_TOKEN  )
                                         # Pour les modèles privés)
        #self.encoder = keras.models.load_model(encoder_path)
        self.final_kmeans = joblib.load(kmeans_path)
        self.embedding_cache = {}  # Cache for embeddings to avoid recomputation
        self.X=np.array([])
        self.mapping_profile = pd.read_pickle(profile_mapping_path)
        self.cluster_products_df=pd.read_excel(clustersPath)
    def set_kmeans_model(self, kmeans_model):
        self.final_kmeans = kmeans_model
        
    def input_processing(self,  df, categorical_cols):
    
        """Process input data for autoencoder"""
        embeddings_list = []
        embedding_dims = []
        
        for col in categorical_cols:
            print(f"Creating embeddings for {col}...")
            
            # Get unique values and check cache
            unique_vals = df[col].unique()
            unique_vals_to_encode = [val for val in unique_vals if val not in self.embedding_cache]
            
            if unique_vals_to_encode:
                # Encode only new values
                new_embeddings = self.model.encode(unique_vals_to_encode, 
                                                 convert_to_tensor=False,
                                                 show_progress_bar=True)
                # Update cache
                self.embedding_cache.update(dict(zip(unique_vals_to_encode, new_embeddings)))
            
            # Get embeddings from cache
            col_embeddings = np.array([self.embedding_cache[val] for val in df[col]])
            embeddings_list.append(col_embeddings)
            
        
        # Scale numerical features
        autoencoder_input = np.concatenate(embeddings_list, axis=1)
        scaler = StandardScaler()
        age_scaled = scaler.fit_transform(df[["DATE_NAISSANCE"]])
        
        self.X = np.hstack([autoencoder_input, age_scaled])
        #return self.X
    
    """def autoencoder_layer(self, X):
       Pass data through autoencoder
        return self.encoder.predict(X)"""
    def clustering_layer(self, df):
        """Predict clusters using KMeans and assign to DataFrame"""
        
        
        # Make a copy to avoid modifying the original DataFrame
        result_df = df.copy()
        
        # Predict clusters
        clusters = self.final_kmeans.predict(self.X)
        
        # Calculate distances to each cluster center
        distances = self.final_kmeans.transform(self.X)
        
        # For each sample, get the ordered list of clusters by proximity (closest first)
        ordered_clusters_list = []
        for i in range(len(distances)):
            # Get distances for this sample
            sample_distances = distances[i]
            # Get cluster indices sorted by distance (ascending order)
            sorted_clusters = np.argsort(sample_distances)
            ordered_clusters_list.append(sorted_clusters.tolist())
        
        # Add clusters and ordered clusters to DataFrame
        result_df['cluster'] = clusters
        result_df['clusters'] = ordered_clusters_list  # Ordered list of clusters by proximity
        
        return result_df

# Get clusters ordered by increasing distance for each sample
        return np.argsort(distances, axis=1)
    def client_segmentation(self, df, cols=None):
        """Create client segment embeddings"""
        if cols is None:
            cols = ['CODE_SEXE', 'SITUATION_FAMILIALE', 
                   'LIB_SECTEUR_ACTIVITE', 'LIB_PROFESSION', 
                   'CATEGORIE_AGE']
        
        try:
            segment_data = df[cols]
            segment = segment_data.apply(lambda row: [str(val) for val in row if pd.notna(val)], axis=1).tolist()
            
            all_words = [word for sublist in segment for word in sublist]
            if not all_words:
                return np.array([])
            
            unique_words = list(set(all_words))
            words_to_encode = [word for word in unique_words if word not in self.embedding_cache]
            
            if words_to_encode:
                new_embeddings = self.model.encode(words_to_encode,
                                                 convert_to_tensor=False,
                                                 show_progress_bar=True)
                self.embedding_cache.update(dict(zip(words_to_encode, new_embeddings)))
            
            # Calculate average embeddings
            average_embeddings = []
            for word_list in segment:
                valid_embeddings = [self.embedding_cache[word] for word in word_list if word in self.embedding_cache]
                if valid_embeddings:
                    avg_embedding = np.mean(valid_embeddings, axis=0)
                else:
                    avg_embedding = np.zeros(self.model.get_sentence_embedding_dimension())
                average_embeddings.append(avg_embedding)
            df['segment_embedding']=average_embeddings
            return df
            
        except Exception as e:
            print(f"Error in client_segmentation: {e}")
            return np.array([])
    



    def product_by_cluster(self,df,contrats):
      # Calcul du taux de pénétration
# -- ÉTAPE 0 : FILTRER UNIQUEMENT LES CONTRATS "EN COURS" --
        contrats_actifs = contrats[contrats.LIB_ETAT_CONTRAT=='EN COURS'].copy()

        # -- ÉTAPE 1 : FUSIONNER LES DONNÉES --
        contrats_avec_cluster = pd.merge(contrats_actifs, df[['REF_PERSONNE', 'cluster']], on='REF_PERSONNE', how='left')

        # Nettoyer les données sans cluster
        contrats_avec_cluster = contrats_avec_cluster.dropna(subset=['cluster'])
        contrats_avec_cluster['cluster'] = contrats_avec_cluster['cluster'].astype(int)

        # -- ÉTAPE 2 : CRÉER UNE TABLE DE CLIENTS UNIQUES PAR PRODUIT ET CLUSTER --
        clients_uniques_par_produit = contrats_avec_cluster.drop_duplicates(subset=['REF_PERSONNE', 'LIB_PRODUIT'])

        # -- ÉTAPE 3 : CALCUL DU TAUX DE PÉNÉTRATION PAR CLUSTER ET PRODUIT --

        # Compter le nombre de clients uniques par produit et cluster
        cluster_product_counts = clients_uniques_par_produit.groupby(['cluster', 'LIB_PRODUIT']).size().reset_index(name='nb_clients')

        # Calculer le nombre total de clients par cluster
        cluster_total_clients = df.groupby('cluster')['REF_PERSONNE'].nunique().reset_index(name='total_clients')

        # Fusionner et calculer le pourcentage de pénétration
        penetration_df = pd.merge(cluster_product_counts, cluster_total_clients, on='cluster')
        penetration_df['penetration_pourcentage'] = (penetration_df['nb_clients'] / penetration_df['total_clients']) * 100

        # Trier par cluster et par taux de pénétration (décroissant)
        penetration_df = penetration_df.sort_values(['cluster', 'penetration_pourcentage'], ascending=[True, False])

        # -- ÉTAPE 4 : CRÉATION DU DATAFRAME FINAL --
        # Le DataFrame penetration_df contient déjà toutes les informations nécessaires :
        # cluster | LIB_PRODUIT | nb_clients | total_clients | penetration_pourcentage

        # DataFrame final avec les clusters et leurs produits ordonnés par pénétration
        result_df = penetration_df[['cluster', 'LIB_PRODUIT', 'penetration_pourcentage', 'nb_clients', 'total_clients']]

        # Renommer les colonnes pour plus de clarté
        result_df = result_df.rename(columns={
            'cluster': 'Cluster',
            'LIB_PRODUIT': 'Produit',
            'penetration_pourcentage': 'Taux_Penetration',
            'nb_clients': 'Nb_Clients_Produit',
            'total_clients': 'Nb_Clients_Total_Cluster'
        })

        # Réinitialiser l'index pour un DataFrame propre
        result_df = result_df.reset_index(drop=True)
   
    def filtrer_contrats_client_avec_details(self,ref_personne, contrats_df, date_reference=None):
      """
      Filtre les contrats d'un client et retourne deux DataFrames:
      1. Contrats filtrés selon les critères
      2. Produits restants avec états et période avant 1 an
      
      Parameters:
      -----------
      ref_personne : str
          Référence de la personne
      contrats_df : pd.DataFrame
          DataFrame des contrats avec colonnes:
          ['REF_PERSONNE', 'LIB_PRODUIT', 'LIB_ETAT_CONTRAT', 'EFFET_CONTRAT']
      date_reference : datetime, optional
          Date de référence pour le calcul (par défaut date actuelle)
      
      Returns:
      --------
      tuple
          (contrats_filtres_df, produits_details_df)
      """
      
      if date_reference is None:
          date_reference = datetime.now()
      
      # Filtrer les contrats de ce client
      contrats_client = contrats_df[contrats_df['REF_PERSONNE'] == ref_personne].copy()
      
      if contrats_client.empty:
          return pd.DataFrame(), pd.DataFrame()
      
      # Convertir EFFET_CONTRAT en datetime si ce n'est pas déjà fait
      if not pd.api.types.is_datetime64_any_dtype(contrats_client['EFFET_CONTRAT']):
          contrats_client['EFFET_CONTRAT'] = pd.to_datetime(contrats_client['EFFET_CONTRAT'], errors='coerce')
      
      # Trier par produit et date pour garder le dernier contrat par produit
      contrats_client = contrats_client.sort_values(['LIB_PRODUIT', 'EFFET_CONTRAT'], ascending=[True, False])
      
      # Garder seulement le dernier contrat par produit
      contrats_uniques = contrats_client.drop_duplicates(subset=['LIB_PRODUIT'], keep='first')
      
      # Appliquer les règles de filtrage
      contrats_filtres = []
      produits_details = []
      
      for _, contrat in contrats_uniques.iterrows():
          produit = contrat['LIB_PRODUIT']
          etat = contrat['LIB_ETAT_CONTRAT']
          date_effet = contrat['EFFET_CONTRAT']
          ref_personne=contrat['REF_PERSONNE']
          
          # Initialiser les valeurs par défaut
          periode_restante = None
          jours_restants = None
          statut_periode = "N/A"
          
          # Vérifier si la date d'effet est valide
          if pd.isna(date_effet):
              # Ajouter quand même au details avec statut d'erreur
          
              continue
          
          # Calculer la durée depuis le début
          duree_ecoulee = date_reference - date_effet
          duree_total_1_an = timedelta(days=365)
          
          # Calculer la période restante avant 1 an
          if duree_ecoulee < duree_total_1_an:
              periode_restante = duree_total_1_an - duree_ecoulee
              jours_restants = periode_restante.days
              statut_periode = f"{jours_restants} jours restants"
          else:
              periode_restante = timedelta(days=0)
              jours_restants = 0
              statut_periode = "Dépassé 1 an"
          contrat_garde = True
          # Règle 1: Contrat expiré → on le garde
          if etat=='EXPIRE':
              contrats_filtres.append(contrat)
              continue
              
          
          # Règle 2: Contrat en cours et moins de 6 mois depuis le début → on le garde
          else:
              contrat_garde = False
              if etat == 'EN COURS':
                 
                  if duree_ecoulee < timedelta(days=180):  # 6 mois ≈ 180 jours
                      contrats_filtres.append(contrat)
                      contrat_garde = True
                      statut_decision = "En cours (<6 mois)"
                  else:
                      statut_decision = "En cours (>6 mois)"
              else:
                
                statut_decision = "RESILIE"
    
              if not contrat_garde:
                # Ajouter aux détails des produits
                produits_details.append({
                    'LIB_PRODUIT': produit,
                    'LIB_ETAT_CONTRAT': etat,
                    'EFFET_CONTRAT': date_effet,
                    'REF_PERSONNE':ref_personne,
                    'PERIODE_RESTANTE': periode_restante,
                    'JOURS_RESTANTS': jours_restants,
                     'statut':statut_decision
                   
                })
      
      # Créer les DataFrames finaux
      contrats_filtres_df = pd.DataFrame(contrats_filtres) if contrats_filtres else pd.DataFrame()
      produits_details_df = pd.DataFrame(produits_details) if produits_details else pd.DataFrame()
      
      return contrats_filtres_df, produits_details_df
    def filtrer_contrats_plusieurs_personnes(self, dataframe_persons, contrats_df, date_reference=None):
      """
      Filtre les contrats de plusieurs personnes et retourne deux DataFrames:
      1. Contrats filtrés selon les critères
      2. Produits restants avec états et période avant 1 an
      
      Parameters:
      -----------
      dataframe_persons : pd.DataFrame
          DataFrame contenant la colonne 'REF_PERSONNE' pour les personnes à traiter
      contrats_df : pd.DataFrame
          DataFrame des contrats avec colonnes:
          ['REF_PERSONNE', 'LIB_PRODUIT', 'LIB_ETAT_CONTRAT', 'EFFET_CONTRAT']
      date_reference : datetime, optional
          Date de référence pour le calcul (par défaut date actuelle)
      
      Returns:
      --------
      tuple
          (contrats_filtres_df, produits_details_df)
      """
  
      if date_reference is None:
          date_reference = datetime.now()
  
      contrats_filtres_agg = []
      produits_details_agg = []
  
      for ref_personne in dataframe_persons['REF_PERSONNE'].unique():
          # Filtrer contrats pour la personne actuelle
          contrats_client = contrats_df[contrats_df['REF_PERSONNE'] == ref_personne].copy()
  
          if contrats_client.empty:
              continue
  
          # Convertir EFFET_CONTRAT en datetime si besoin
          if not pd.api.types.is_datetime64_any_dtype(contrats_client['EFFET_CONTRAT']):
              contrats_client['EFFET_CONTRAT'] = pd.to_datetime(contrats_client['EFFET_CONTRAT'], errors='coerce')
  
          contrats_client = contrats_client.sort_values(['LIB_PRODUIT', 'EFFET_CONTRAT'], ascending=[True, False])
          contrats_uniques = contrats_client.drop_duplicates(subset=['LIB_PRODUIT'], keep='first')
  
          contrats_filtres = []
          produits_details = []
  
          for _, contrat in contrats_uniques.iterrows():
              produit = contrat['LIB_PRODUIT']
              etat = contrat['LIB_ETAT_CONTRAT']
              date_effet = contrat['EFFET_CONTRAT']
              ref_personne=contrat['REF_PERSONNE']
              periode_restante = None
              jours_restants = None
              statut_periode = "N/A"
              contrat_garde = False
  
              if pd.isna(date_effet):
                
                  continue
  
              duree_ecoulee = date_reference - date_effet
              duree_total_1_an = timedelta(days=365)
  
              if duree_ecoulee < duree_total_1_an:
                  periode_restante = duree_total_1_an - duree_ecoulee
                  jours_restants = periode_restante.days
                  statut_periode = f"{jours_restants} "
              else:
                  periode_restante = timedelta(days=0)
                  jours_restants = 0
                  statut_periode = "Dépassé 1 an"
  
              if etat == 'EXPIRE':
                  contrats_filtres.append(contrat)
              else:
                contrat_garde = False
                if etat == 'EN COURS':

                    if duree_ecoulee < timedelta(days=180):  # 6 mois ≈ 180 jours
                        contrats_filtres.append(contrat)
                        contrat_garde = True
                        statut_decision = "En cours (<6 mois)"
                    else:
                        statut_decision = "En cours (>6 mois)"
                else:

                  statut_decision = "RESILIE"

                if not contrat_garde:
                  # Ajouter aux détails des produits
                  produits_details.append({
                      'LIB_PRODUIT': produit,
                      'LIB_ETAT_CONTRAT': etat,
                      'EFFET_CONTRAT': date_effet,
                      
                      'JOURS_RESTANTS': jours_restants,
                      'REF_PERSONNE':ref_personne,

                  })
          if contrats_filtres:
              contrats_filtres_agg.append(pd.DataFrame(contrats_filtres))
          if produits_details:
              produits_details_agg.append(pd.DataFrame(produits_details))
  
      contrats_filtres_df = pd.concat(contrats_filtres_agg, ignore_index=True) if contrats_filtres_agg else pd.DataFrame()
      produits_details_df = pd.concat(produits_details_agg, ignore_index=True) if produits_details_agg else pd.DataFrame()
  
      return contrats_filtres_df, produits_details_df
  
    def get_top_products_by_similarity(self,client_segment_embedding, clusters_ordered, cluster_products_df, 
                                mapping_profile, n_products=3):
         """
         Calculate cosine similarity between client segment and products in clusters,
         moving to next cluster if current cluster doesn't have enough products.

         Parameters:
         -----------
         client_segment_embedding : np.array
             Embedding vector of the client segment
         clusters_ordered : list
             List of cluster IDs ordered by proximity (closest first)
         cluster_products_df : pd.DataFrame
             DataFrame containing cluster IDs and the products they contain
             Should have columns: ['cluster', 'LIB_PRODUIT']
         mapping_profile : dict
             Dictionary mapping product names to their embeddings
             Format: {'lib_produit': embedding_array}
         n_products : int, default=3
             Number of top similar products to return

         Returns:
         --------
         pd.DataFrame
             DataFrame with top n_products and their cosine similarity scores
         """

         results = []
         processed_products = set()
         
         # Iterate through clusters in order of proximity
         for cluster_id in clusters_ordered:
             # Get products in current cluster
             cluster_products = cluster_products_df[cluster_products_df['cluster'] == cluster_id]['LIB_PRODUIT'].tolist()

             # Filter out products already processed from previous clusters
             new_products = [prod for prod in cluster_products if prod not in processed_products]

             if not new_products:
                 continue  # Skip if no new products in this cluster

             # Calculate similarity for each new product in this cluster
             for product in new_products:
                 if product in mapping_profile:
                     product_embedding = mapping_profile[product]

                     # Ensure embeddings are numpy arrays with same shape
                     if (isinstance(client_segment_embedding, np.ndarray) and
                         isinstance(product_embedding, np.ndarray) and
                         client_segment_embedding.shape == product_embedding.shape):

                         similarity = cosine_similarity([client_segment_embedding], [product_embedding])[0][0]

                         results.append({
                             'LIB_PRODUIT': product,
                             'cluster': cluster_id,
                             'cosine_similarity': similarity
                         })

                     processed_products.add(product)

             # Check if we have enough products
             if len(results) >= n_products:
                 break

         # Convert to DataFrame and sort by similarity
         results_df = pd.DataFrame(results)

         if not results_df.empty:
             results_df = results_df.sort_values('cosine_similarity', ascending=False).head(n_products)

         return results_df

# Optimized vectorized version
    def get_top_products_by_similarity(self,client_segment_embedding, clusters_ordered, cluster_products_df, 
                                    mapping_profile, n_products=3):
             """
             Calculate cosine similarity between client segment and products in clusters,
             moving to next cluster if current cluster doesn't have enough products.
    
             Parameters:
             -----------
             client_segment_embedding : np.array
                 Embedding vector of the client segment
             clusters_ordered : list
                 List of cluster IDs ordered by proximity (closest first)
             cluster_products_df : pd.DataFrame
                 DataFrame containing cluster IDs and the products they contain
                 Should have columns: ['cluster', 'LIB_PRODUIT']
             mapping_profile : dict
                 Dictionary mapping product names to their embeddings
                 Format: {'lib_produit': embedding_array}
             n_products : int, default=3
                 Number of top similar products to return
    
             Returns:
             --------
             pd.DataFrame
                 DataFrame with top n_products and their cosine similarity scores
             """
    
             results = []
             processed_products = set()
             
             # Iterate through clusters in order of proximity
             for cluster_id in clusters_ordered:
                 # Get products in current cluster
                 cluster_products = cluster_products_df[cluster_products_df['cluster'] == cluster_id]['LIB_PRODUIT'].tolist()
    
                 # Filter out products already processed from previous clusters
                 new_products = [prod for prod in cluster_products if prod not in processed_products]
    
                 if not new_products:
                     continue  # Skip if no new products in this cluster
    
                 # Calculate similarity for each new product in this cluster
                 for product in new_products:
                     if product in mapping_profile:
                         product_embedding = mapping_profile[product]
    
                         # Ensure embeddings are numpy arrays with same shape
                         if (isinstance(client_segment_embedding, np.ndarray) and
                             isinstance(product_embedding, np.ndarray) and
                             client_segment_embedding.shape == product_embedding.shape):
    
                             similarity = cosine_similarity([client_segment_embedding], [product_embedding])[0][0]
    
                             results.append({
                                 'LIB_PRODUIT': product,
                                 'cluster': cluster_id,
                                 'cosine_similarity': similarity
                             })
    
                         processed_products.add(product)
    
                 # Check if we have enough products
                 if len(results) >= n_products:
                     break
    
             # Convert to DataFrame and sort by similarity
             results_df = pd.DataFrame(results)
    
             if not results_df.empty:
                 results_df = results_df.sort_values('cosine_similarity', ascending=False).head(n_products)
    
             return results_df
    
    # Optimized vectorized version
    def get_top_products_by_similarity(self,client_segment_embedding, clusters_ordered, cluster_products_df, 
                                    mapping_profile, n_products=3):
             """
             Calculate cosine similarity between client segment and products in clusters,
             moving to next cluster if current cluster doesn't have enough products.
    
             Parameters:
             -----------
             client_segment_embedding : np.array
                 Embedding vector of the client segment
             clusters_ordered : list
                 List of cluster IDs ordered by proximity (closest first)
             cluster_products_df : pd.DataFrame
                 DataFrame containing cluster IDs and the products they contain
                 Should have columns: ['cluster', 'LIB_PRODUIT']
             mapping_profile : dict
                 Dictionary mapping product names to their embeddings
                 Format: {'lib_produit': embedding_array}
             n_products : int, default=3
                 Number of top similar products to return
    
             Returns:
             --------
             pd.DataFrame
                 DataFrame with top n_products and their cosine similarity scores
             """
    
             results = []
             processed_products = set()
             
             # Iterate through clusters in order of proximity
             for cluster_id in clusters_ordered:
                 # Get products in current cluster
                 cluster_products = cluster_products_df[cluster_products_df['cluster'] == cluster_id]['LIB_PRODUIT'].tolist()
    
                 # Filter out products already processed from previous clusters
                 new_products = [prod for prod in cluster_products if prod not in processed_products]
    
                 if not new_products:
                     continue  # Skip if no new products in this cluster
    
                 # Calculate similarity for each new product in this cluster
                 for product in new_products:
                     if product in mapping_profile:
                         product_embedding = mapping_profile[product]
    
                         # Ensure embeddings are numpy arrays with same shape
                         if (isinstance(client_segment_embedding, np.ndarray) and
                             isinstance(product_embedding, np.ndarray) and
                             client_segment_embedding.shape == product_embedding.shape):
    
                             similarity = cosine_similarity([client_segment_embedding], [product_embedding])[0][0]
    
                             results.append({
                                 'LIB_PRODUIT': product,
                                 'cluster': cluster_id,
                                 'cosine_similarity': similarity
                             })
    
                         processed_products.add(product)
    
                 # Check if we have enough products
                 if len(results) >= n_products:
                     break
    
             # Convert to DataFrame and sort by similarity
             results_df = pd.DataFrame(results)
    
             if not results_df.empty:
                 results_df = results_df.sort_values('cosine_similarity', ascending=False).head(n_products)
    
             return results_df
    
# Optimized vectorized version
    def get_top_products_for_clients_df_vectorized(self, clients_df, n_products=3):
           """
           Optimized version using vectorized operations for better performance.
           """
           print(f"Début de la fonction - Nombre de clients: {len(clients_df)}")
           
           all_recommendations = []
        
           # Pre-process cluster products for faster lookup
           # Prepend 'ASSURANCE DECES VIE ENTIERE' to all values
           cluster_products_dict = {key: ['ASSURANCE DECES VIE ENTIERE'] + value 
                         for key, value in cluster_products_dict.items()}
           print(f"Clusters disponibles: {list(cluster_products_dict.keys())}")
        
           # Iterate through each client
           for i, (_, client_row) in enumerate(clients_df.iterrows()):
               if i % 100 == 0:  # Print every 100 clients
                   print(f"Traitement client {i}/{len(clients_df)}")
                   
               ref_peronne = client_row['REF_PERSONNE']
               client_embedding = client_row['Segment_Embeddings']
               clusters_ordered = client_row['clusters']  # Client-specific ordered clusters
        
               print(f"Client {ref_peronne}: clusters_ordered = {clusters_ordered}")
               print(f"Type de clusters_ordered: {type(clusters_ordered)}")
               print(f"Type de client_embedding: {type(client_embedding)}")
        
               # Ensure clusters_ordered is a list
               if not isinstance(clusters_ordered, list):
                   print(f"Warning: clusters_ordered for client {ref_peronne} is not a list: {clusters_ordered}")
                   continue
        
               results = []
               processed_products = set()
        
               # Iterate through clusters in the client's specific order
               for cluster_id in clusters_ordered:
                   print(f"  Cluster {cluster_id}")
                   
                   # Skip if cluster doesn't exist
                   if cluster_id not in cluster_products_dict:
                       print(f"    Cluster {cluster_id} non trouvé dans cluster_products_dict")
                       continue
        
                   cluster_products = cluster_products_dict[cluster_id]
                   print(f"    Produits dans cluster: {len(cluster_products)}")
                   
                   # Filter out products already processed
                   new_products = [prod for prod in cluster_products if prod not in processed_products]
                   print(f"    Nouveaux produits à traiter: {len(new_products)}")
                   
                   if not new_products:
                       print(f"    Aucun nouveau produit dans cluster {cluster_id}")
                       continue
        
                   # Calculate similarities for all new products in this cluster at once
                   product_embeddings = []
                   valid_products = []
        
                   for product in new_products:
                       # Use DataFrame lookup instead of dictionary
                       product_match = self.mapping_profile[self.mapping_profile['LIB_PRODUIT'] == product]
                       
                       if not product_match.empty:
                           product_embedding = np.array(product_match['Segment_Embeddings'])[0]
                           print(product_embedding)
                           # Check if embeddings are valid numpy arrays with same shape
                           if (isinstance(client_embedding, np.ndarray) and
                               isinstance(product_embedding, np.ndarray) and
                               client_embedding.shape == product_embedding.shape):
                               
                               product_embeddings.append(product_embedding)
                               valid_products.append(product)
                               processed_products.add(product)
                           else:
                               print(f"    Problème d'embedding pour le produit {product}")
                               print(f"      client_embedding type: {type(client_embedding)}, shape: {client_embedding.shape if hasattr(client_embedding, 'shape') else 'N/A'}")
                               print(f"      product_embedding type: {type(product_embedding)}, shape: {product_embedding.shape if hasattr(product_embedding, 'shape') else 'N/A'}")
                       else:
                           print(f"    Produit {product} non trouvé dans mapping_profile")
        
                   print(f"    Produits valides avec embeddings: {len(valid_products)}")
        
                   if valid_products:
                       try:
                           # Vectorized similarity calculation
                           similarities = cosine_similarity([client_embedding], product_embeddings)[0]
                           print(f"    Similarités calculées: {similarities}")
                           
                           for product, similarity in zip(valid_products, similarities):
                               results.append({
                                   'LIB_PRODUIT': product,
                                   'cluster': cluster_id,
                                   'cosine_similarity': similarity
                               })
                       except Exception as e:
                           print(f"    Erreur lors du calcul de similarité: {e}")
                           print(f"    client_embedding shape: {client_embedding.shape}")
                           print(f"    product_embeddings shapes: {[e.shape for e in product_embeddings]}")
        
                   # Check if we have enough products
                   if len(results) >= n_products:
                       print(f"    Suffisamment de produits trouvés: {len(results)}")
                       break
        
               # Process results for this client
               print(f"  Résultats pour client {ref_peronne}: {len(results)} produits")
               
               if results:
                   results_df = pd.DataFrame(results)
                   results_df = results_df.sort_values('cosine_similarity', ascending=False).head(n_products)
                   results_df['REF_PERSONNE'] = ref_peronne
                   results_df['rank'] = range(1, len(results_df) + 1)
        
                   all_recommendations.append(results_df)
               else:
                   print(f"  AUCUN résultat pour client {ref_peronne}")
        
           # Combine all recommendations
           print(f"Nombre total de recommandations: {len(all_recommendations)}")
           
           if all_recommendations:
               final_df = pd.concat(all_recommendations, ignore_index=True)
               print(f"DataFrame final créé avec {len(final_df)} lignes")
               return final_df[['REF_PERSONNE', 'LIB_PRODUIT', 'cluster', 'cosine_similarity', 'rank']]
           else:
               print("Aucune recommandation générée")
               return pd.DataFrame(columns=['REF_PERSONNE', 'LIB_PRODUIT', 'cluster', 'cosine_similarity', 'rank'])
    def get_top_products_for_clients_df_vectorized_matrix(self, clients_df,contrats,etats, n_products=3):
          """
          Version corrigée : ne prend que n_products par cluster au maximum
          """
          print(f"Début de la fonction - Nombre de clients: {len(clients_df)}")
        
          # Pre-process cluster products for faster lookup
          cluster_products_dict = self.cluster_products_df.groupby('cluster')['LIB_PRODUIT'].apply(list).to_dict()
          cluster_products_dict = {key: ['ASSURANCE DECES VIE ENTIERE'] + value 
                         for key, value in cluster_products_dict.items()}
          # Prepare all client data
          clients_data = []
          for _, row in clients_df.iterrows():
              if not isinstance(row['clusters'], list):
                  continue
              clients_data.append({
                  'REF_PERSONNE': row['REF_PERSONNE'],
                  'client_embedding': row['segment_embedding'],
                  'clusters_ordered': row['clusters'],
                  'type':'physique',
                  'age':row['DATE_NAISSANCE'],
                  'profession':row['LIB_PROFESSION'],
                  'sexe':row['CODE_SEXE']


              })
        
          if not clients_data:
              return pd.DataFrame(columns=['REF_PERSONNE', 'LIB_PRODUIT', 'cluster', 'cosine_similarity', 'rank'])
        
          all_results = []
        
          # Process each client
          for client_data in clients_data:
              ref_personne = client_data['REF_PERSONNE']
              client_embedding = client_data['client_embedding']
              clusters_ordered = client_data['clusters_ordered']
              typePerson=client_data['type']
              age=client_data['age']
              profession=client_data['profession']
              sexe=client_data['sexe']
              not_to_get_products=contrats[contrats.REF_PERSONNE==ref_personne].LIB_PRODUIT.unique()
              client_results = []
              processed_products = set()
              products_needed = n_products
        
              # Process clusters in order
              for cluster_rank, cluster_id in enumerate(clusters_ordered):
                  if cluster_id not in cluster_products_dict:
                      continue
        
                  # Get ALL products from this cluster
                  cluster_products = cluster_products_dict[cluster_id]
                  cluster_products = [product for product in cluster_products if product not in not_to_get_products]
                  # Get embeddings and calculate similarities for ALL products in the cluster
                  product_embeddings = []
                  valid_products = []
        
                  for product in cluster_products:
                      # Skip if we've already processed this product from a previous cluster
                      if product in processed_products:
                          continue
                          
                      product_match = self.mapping_profile[self.mapping_profile['LIB_PRODUIT'] == product]
                      if not product_match.empty:
                          product_embedding = np.array(product_match['Segment_Embeddings'])[0]
                          if (isinstance(client_embedding, np.ndarray) and 
                              isinstance(product_embedding, np.ndarray) and
                              client_embedding.shape == product_embedding.shape):
        
                              product_embeddings.append(product_embedding)
                              valid_products.append(product)
                              processed_products.add(product)
        
                  if valid_products:
                      # Calculate similarities for ALL products in this cluster
                      similarities = cosine_similarity([client_embedding], product_embeddings)[0]
        
                      # Add ALL products from this cluster to results
                      for product, similarity in zip(valid_products, similarities):
                          client_results.append({
                              'REF_PERSONNE': ref_personne,
                              'LIB_PRODUIT': product,
                              'cluster': cluster_id,
                              'cluster_rank': cluster_rank,
                              'cosine_similarity': similarity,
                              'age':age,
                              'sexe':sexe,
                              'profession':profession,
                              'type':typePerson,
                              'ville':None,
                              "gouvernorat": None
                          })
        
                      # Check if we have enough products
                      if len(client_results) >= n_products:
                          break
        
              # Final processing for this client
              if client_results:
                  client_df = pd.DataFrame(client_results)
                  client_df = client_df.sort_values('cosine_similarity', ascending=False)
                  client_df['rank'] = range(1, len(client_df) + 1)
                  all_results.append(client_df)
        
          # Combine all results
          if all_results:
              final_df = pd.concat(all_results, ignore_index=True)
              final_df = final_df[['REF_PERSONNE', 'LIB_PRODUIT', 'cluster', 'cosine_similarity', 'rank','type','age','sexe','ville','profession','gouvernorat']]

# Effectuer une jointure gauche avec le dataframe etats
              final_df = final_df.merge(
                  etats[['REF_PERSONNE', 'LIB_PRODUIT', 'LIB_ETAT_CONTRAT','JOURS_RESTANTS']],
                  on=['REF_PERSONNE', 'LIB_PRODUIT'],
                  how='left'
              )

              return final_df
          else:
              return pd.DataFrame(columns=['REF_PERSONNE', 'LIB_PRODUIT', 'cluster', 'cosine_similarity', 'rank'])
    def prepare_client_data(self,recommendation_df, contrat_df):
        """
        Adapte les dataframes au format JSON demandé avec gestion du sexe

        Args:
            recommendation_df: DataFrame avec les recommandations
            contrat_df: DataFrame avec les contrats expirés

        Returns:
            dict: Données structurées au format JSON
        """

        # Préparer les données des clients
        clients_data = []

        # Grouper par REF_PERSONNE
        grouped = recommendation_df.groupby('REF_PERSONNE')

        for ref_personne, group in grouped:
            # Prendre la première ligne pour les infos du client
            client_info = group.iloc[0]

            # Convertir le sexe M->homme, F->femme
            sexe = client_info.get('sexe')
            if sexe == 'M':
                sexe_json = "homme"
            elif sexe == 'F':
                sexe_json = "femme"
            else:
                sexe_json = "non spécifié"

            # Récupérer les produits expirés pour ce client
            expired_products = []
            client_contrats = contrat_df[contrat_df['REF_PERSONNE'] == ref_personne]

            for _, contrat in client_contrats.iterrows():
                expired_products.append({
                    "product": contrat['LIB_PRODUIT'],
                    "date d'expiration": contrat['DATE_EXPIRATION'] 
                    if pd.notna(contrat['DATE_EXPIRATION']) else None
                })

            # Préparer les top recommandations
            top_recommendations = []
            for _, row in group.iterrows():
                top_recommendations.append({
                    "rank": int(row['rank']),
                    "product": row['LIB_PRODUIT'],
                    "final_score": float(row['cosine_similarity']),
                    "etat": row['LIB_ETAT_CONTRAT'],
                    "Jours restants": int(row['JOURS_RESTANTS']) if pd.notna(row['JOURS_RESTANTS']) else 0
                })

            # Trier les recommandations par rank
            top_recommendations.sort(key=lambda x: x['rank'])

            # Créer l'objet client
            client_data = {
                "REF_PERSONNE": ref_personne,
                "type": client_info['type'],
                "name": "Nom Client",  # À adapter si vous avez une colonne pour le nom
                "age": int(client_info['age']) if pd.notna(client_info['age']) else None,
                "sexe": sexe_json,  # Champ sexe ajouté
                "profession": client_info['profession'],
                "ville": client_info['ville'],
                "gouvernorat": client_info['gouvernorat'],
                "current_products": [],  # Toujours vide comme demandé
                "expired_products": expired_products,
                "top_recommendations": top_recommendations
            }

            clients_data.append(client_data)

        return {"clients": clients_data}