"""
Moral Person Insurance Product Recommendation System
Based on the complete ranking recommendation system for moral entities
"""

import os
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import warnings

# Set environment variables to avoid PyTorch issues
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Force CPU usage

warnings.filterwarnings('ignore')

class MoralPersonRecommendationSystem:
    """
    Production-ready recommendation system for insurance products for moral entities
    Returns ALL ranked recommendations with complete scoring
    """

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        """
        Initialize the recommendation system

        Args:
            model_name (str): SentenceTransformer model to use
        """
        try:
            import torch
            # Set device to CPU to avoid GPU-related issues
            device = 'cpu'
            print(f"🔧 Initializing SentenceTransformer on {device}...")
            
            # Initialize model with explicit device setting
            self.model = SentenceTransformer(model_name, device=device)
            
            # Ensure model is on CPU and in evaluation mode
            self.model.to(device)
            self.model.eval()
            
            print(f"✅ SentenceTransformer initialized successfully on {device}")
        except Exception as e:
            print(f"❌ Error initializing SentenceTransformer: {e}")
            print("🔄 Trying fallback initialization...")
            try:
                # Fallback: try without device specification
                self.model = SentenceTransformer(model_name)
                print("✅ SentenceTransformer initialized with fallback method")
            except Exception as e2:
                print(f"❌ Fallback initialization failed: {e2}")
                raise RuntimeError(f"Could not initialize SentenceTransformer: {e2}")
        
        self.product_embeddings = {}
        self.product_profiles = {}
        self.is_trained = False

    def train_model(self, product_mapping_file, sheet_name='Sheet1', phy_sheet='phy'):
        """
        Train the model using product mapping data

        Args:
            product_mapping_file (str): Path to Excel file with product mappings
            sheet_name (str): Main sheet name
            phy_sheet (str): Physical products sheet name
        """
        print("📄 Training recommendation model...")

        try:
            # Load product data
            print(f"📊 Loading product data from: {product_mapping_file}")
            all_product = pd.read_excel(product_mapping_file, sheet_name=sheet_name)
            print(f"   - Loaded {len(all_product)} products from {sheet_name}")

            phy_product = pd.read_excel(product_mapping_file, sheet_name=phy_sheet)
            print(f"   - Loaded {len(phy_product)} physical products from {phy_sheet}")

            # Get moral products (difference between all and physical)
            cols = ["LIB_BRANCHE", "LIB_SOUS_BRANCHE", "LIB_PRODUIT", "Profils cibles"]

            # Check if required columns exist
            missing_cols = [col for col in cols if col not in all_product.columns]
            if missing_cols:
                raise ValueError(f"Missing columns in {sheet_name}: {missing_cols}")

            moral_product = all_product.merge(
                phy_product[cols], on=cols, how="left", indicator=True
            ).query('_merge == "left_only"').drop(columns="_merge")

            print(f"   - Extracted {len(moral_product)} moral products")

            # Clean data - handle case where drop indices might not exist
            indices_to_drop = [i for i in [0, 2] if i < len(moral_product)]
            if indices_to_drop:
                moral_product = moral_product.drop(indices_to_drop).reset_index(drop=True)
                print(f"   - Cleaned data, {len(moral_product)} products remaining")

        except Exception as e:
            print(f"❌ Error loading product data: {str(e)}")
            raise

        # Process product profiles
        try:
            # Handle NaN values in Profils cibles
            moral_product['Profils cibles'] = moral_product['Profils cibles'].fillna('')
            moral_product['Profils cibles'] = moral_product['Profils cibles'].apply(
                lambda x: x.split(';') if isinstance(x, str) and x.strip() else []
            )

            # Generate embeddings for product profiles
            all_profile_words = []
            for profiles in moral_product['Profils cibles']:
                if isinstance(profiles, list):
                    all_profile_words.extend([word.strip() for word in profiles if word and word.strip()])

            if not all_profile_words:
                raise ValueError("No valid product profile words found")

            unique_words = list(set(all_profile_words))
            print(f"🔤 Generating embeddings for {len(unique_words)} unique profile words...")

            word_embeddings = self.model.encode(unique_words, convert_to_tensor=False, show_progress_bar=True)
            embedding_dict = dict(zip(unique_words, word_embeddings))

            # Create product embeddings and profiles
            for _, row in moral_product.iterrows():
                product = row['LIB_PRODUIT']
                profiles = row['Profils cibles'] if isinstance(row['Profils cibles'], list) else []

                # Store product profiles
                self.product_profiles[product] = profiles

                # Calculate mean embedding for product
                if profiles:
                    valid_profile_embeddings = [embedding_dict[word.strip()] for word in profiles
                                              if word and word.strip() in embedding_dict]
                    if valid_profile_embeddings:
                        self.product_embeddings[product] = np.mean(valid_profile_embeddings, axis=0)
                    else:
                        self.product_embeddings[product] = np.zeros(len(word_embeddings[0]))
                else:
                    self.product_embeddings[product] = np.zeros(len(word_embeddings[0]))

            self.is_trained = True
            print(f"✅ Model trained with {len(self.product_embeddings)} products")

        except Exception as e:
            print(f"❌ Error processing product profiles: {str(e)}")
            raise

    def save_model(self, save_path):
        """Save the trained model"""
        if not self.is_trained:
            raise ValueError("Model must be trained before saving")

        model_data = {
            'product_embeddings': self.product_embeddings,
            'product_profiles': self.product_profiles,
            'model_name': self.model.get_sentence_embedding_dimension()
        }

        with open(save_path, 'wb') as f:
            pickle.dump(model_data, f)
        print(f"💾 Model saved to {save_path}")

    def load_model(self, model_path):
        """Load a pre-trained model"""
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)

        self.product_embeddings = model_data['product_embeddings']
        self.product_profiles = model_data['product_profiles']
        self.is_trained = True
        print(f"📂 Model loaded from {model_path}")

    def _preprocess_client_data(self, df):
        """
        Preprocess client data for recommendation

        Args:
            df (pd.DataFrame): Raw client data

        Returns:
            pd.DataFrame: Processed client data with embeddings
        """
        print("📄 Preprocessing client data...")
        print(f"   - Input data shape: {df.shape}")

        # Check required columns
        required_cols = ['REF_PERSONNE', 'LIB_SECTEUR_ACTIVITE', 'LIB_ACTIVITE']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"❌ Missing required columns: {missing_cols}")
            print(f"Available columns: {df.columns.tolist()}")
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Filter out invalid records
        initial_len = len(df)
        df = df[df['LIB_SECTEUR_ACTIVITE'].notna()]
        df = df[df['LIB_SECTEUR_ACTIVITE'].str.upper() != 'AUCUN']
        print(f"   - Filtered {initial_len - len(df)} invalid records, {len(df)} remaining")

        # Clean text columns, excluding VILLE and LIB_GOUVERNORAT
        text_cols = ["RAISON_SOCIALE", "MATRICULE_FISCALE", "LIB_SECTEUR_ACTIVITE", "LIB_ACTIVITE"]

        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper()
                df[col] = df[col].replace('NAN', np.nan)

        # Create client segments
        df['Client_Segment'] = df[['LIB_SECTEUR_ACTIVITE', 'LIB_ACTIVITE']].apply(
            lambda row: [str(val) for val in row if pd.notna(val)], axis=1
        )

        # Generate embeddings for client segments
        all_client_words = [word for segment_list in df['Client_Segment'] for word in segment_list]
        unique_client_words = list(set(all_client_words))

        if not unique_client_words:
            raise ValueError("No valid client segment words found")

        print(f"   - Generating embeddings for {len(unique_client_words)} unique client words...")
        client_word_embeddings = self.model.encode(unique_client_words, convert_to_tensor=False)
        client_embedding_dict = dict(zip(unique_client_words, client_word_embeddings))

        # Calculate client embeddings
        df['Client_Embeddings'] = df['Client_Segment'].apply(
            lambda word_list: np.mean([client_embedding_dict[word] for word in word_list
                                     if word in client_embedding_dict], axis=0)
        )

        print(f"✅ Preprocessing completed: {len(df)} clients ready")
        return df

    def parse_expiration_date(self, raw_date):
        """
        Parse expiration date with multiple fallback methods - DATE ONLY

        Args:
            raw_date: Raw date value from the database

        Returns:
            tuple: (parsed_date, formatted_string, will_expire_soon)
        """
        try:
            # Handle NULL, NaN, or empty values
            if pd.isna(raw_date) or str(raw_date).strip().upper() in ['NULL', 'NAN', '']:
                return None, "Unknown", False

            expiration_date = None

            # Method 1: Standard pandas conversion
            expiration_date = pd.to_datetime(raw_date, errors='coerce')

            # Method 2: Try specific formats if pandas failed
            if pd.isna(expiration_date):
                date_formats = [
                    '%Y-%m-%d %H:%M:%S.%f',  # 2030-10-14 00:00:00.000
                    '%Y-%m-%d %H:%M:%S',     # 2030-10-14 00:00:00
                    '%Y-%m-%d',              # 2030-10-14
                    '%d/%m/%Y',              # 14/10/2030
                    '%m/%d/%Y',              # 10/14/2030
                    '%d-%m-%Y',              # 14-10-2030
                    '%Y/%m/%d',              # 2030/10/14
                    '%d.%m.%Y'               # 14.10.2030
                ]

                str_date = str(raw_date).strip()
                for fmt in date_formats:
                    try:
                        expiration_date = pd.to_datetime(str_date, format=fmt, errors='raise')
                        break
                    except:
                        continue

            # Method 3: Excel serial date conversion
            if pd.isna(expiration_date) and isinstance(raw_date, (int, float)) and raw_date > 10000:
                try:
                    excel_epoch = pd.Timestamp('1899-12-30')
                    expiration_date = excel_epoch + pd.Timedelta(days=raw_date)
                except:
                    pass

            # EXTRACT DATE ONLY (remove time component)
            if pd.notna(expiration_date):
                # Convert to date only
                date_only = expiration_date.date()
                formatted_date = date_only.strftime('%y/%m/%d')

                # Compare dates only for expiration check
                six_months_from_now = (pd.Timestamp.now() + pd.Timedelta(days=180)).date()
                will_expire_soon = date_only <= six_months_from_now

                return date_only, formatted_date, will_expire_soon
            else:
                return None, "Unknown", False

        except Exception as e:
            print(f"⚠️ Date parsing error for {repr(raw_date)}: {str(e)}")
            return None, "Unknown", False

    def generate_recommendations(self, client_df, contracts_df=None, show_all_ranked=True, min_score_threshold=0.0):
        """
        Generate product recommendations for clients - SHOWS ALL RANKED RECOMMENDATIONS

        Args:
            client_df (pd.DataFrame): Client data with required columns
            contracts_df (pd.DataFrame, optional): Existing contracts to exclude
            show_all_ranked (bool): If True, show ALL products ranked by score
            min_score_threshold (float): Minimum similarity score to include (0.0 = all)

        Returns:
            dict: Recommendations in JSON format with ALL products ranked
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before generating recommendations")

        print("🎯 Generating ALL RANKED recommendations...")

        # Preprocess client data
        processed_df = self._preprocess_client_data(client_df.copy())

        # Get existing products per client if contracts provided
        existing_products = {}
        if contracts_df is not None:
            # Validate required contract columns
            required_contract_cols = ['REF_PERSONNE', 'LIB_PRODUIT', 'LIB_ETAT_CONTRAT', 'DATE_EXPIRATION']
            missing_contract_cols = [col for col in required_contract_cols if col not in contracts_df.columns]
            if missing_contract_cols:
                print(f"❌ Missing required contract columns: {missing_contract_cols}")
                raise ValueError(f"Missing required contract columns: {missing_contract_cols}")

            # Filter contracts for LIB_ETAT_CONTRAT == "EN COURS"
            contracts_df = contracts_df[contracts_df['LIB_ETAT_CONTRAT'] == 'EN COURS']
            print(f"   - Filtered to {len(contracts_df)} contracts with LIB_ETAT_CONTRAT == 'EN COURS'")

            # Process each contract
            for _, contract in contracts_df.iterrows():
                client_id = contract['REF_PERSONNE']
                product = contract['LIB_PRODUIT']
                raw_expiration = contract['DATE_EXPIRATION']

                # Parse expiration date using improved method
                parsed_date, formatted_date, will_expire_soon = self.parse_expiration_date(raw_expiration)

                if client_id not in existing_products:
                    existing_products[client_id] = []
                existing_products[client_id].append({
                    "product": product,
                    "expiration_date": formatted_date,
                    "will_expire_soon": will_expire_soon
                })

            print(f"✅ Processed {len(existing_products)} clients with existing contracts")

        # Generate recommendations
        recommendations = {"clients": [], "summary": {"total_products_available": len(self.product_embeddings)}}

        for _, client in processed_df.iterrows():
            client_id = client['REF_PERSONNE']
            client_embedding = client['Client_Embeddings']

            # Calculate similarities with ALL products
            all_product_similarities = []

            for product, product_embedding in self.product_embeddings.items():
                if isinstance(client_embedding, np.ndarray) and isinstance(product_embedding, np.ndarray):
                    similarity = cosine_similarity([client_embedding], [product_embedding])[0][0]

                    # Only include if meets minimum threshold
                    if similarity >= min_score_threshold:
                        all_product_similarities.append({
                            'product': product,
                            'similarity': float(similarity),
                            'profiles': self.product_profiles.get(product, [])
                        })

            # Sort by similarity (highest first)
            all_product_similarities.sort(key=lambda x: x['similarity'], reverse=True)

            # Separate existing products from new recommendations
            existing_product_names = []
            available_recommendations = []

            if client_id in existing_products:
                existing_product_names = [p["product"] for p in existing_products[client_id]]
                # Split products into existing vs new recommendations
                available_recommendations = [p for p in all_product_similarities
                                           if p['product'] not in existing_product_names]
            else:
                available_recommendations = all_product_similarities

            # Format client data
            client_data = {
                "REF_PERSONNE": client_id,
                "type": "morale",
                "RAISON_SOCIALE": client.get('RAISON_SOCIALE', ''),
                "matricule_fiscale": client.get('MATRICULE_FISCALE', ''),
                "LIB_SECTEUR_ACTIVITE": client.get('LIB_SECTEUR_ACTIVITE', ''),
                "LIB_ACTIVITE": client.get('LIB_ACTIVITE', ''),
                "current_products": existing_products.get(client_id, []),
                "top_recommendations": [
                    {
                        "rank": idx + 1,
                        "product": rec['product'],
                        "final_score": round(rec['similarity'], 4),
                        "target_profiles": rec['profiles'],
                        "recommendation_strength": self._get_recommendation_strength(rec['similarity'])
                    }
                    for idx, rec in enumerate(available_recommendations)
                ],
                "summary": {
                    "total_available_products": len(available_recommendations),
                    "current_products_count": len(existing_products.get(client_id, [])),
                    "highest_score": round(available_recommendations[0]['similarity'], 4) if available_recommendations else 0,
                    "lowest_score": round(available_recommendations[-1]['similarity'], 4) if available_recommendations else 0,
                    "average_score": round(np.mean([r['similarity'] for r in available_recommendations]), 4) if available_recommendations else 0
                }
            }

            recommendations["clients"].append(client_data)

        print(f"✅ Generated COMPLETE RANKED recommendations for {len(recommendations['clients'])} clients")
        return recommendations

    def _get_recommendation_strength(self, score):
        """
        Convert similarity score to recommendation strength category

        Args:
            score (float): Similarity score between 0 and 1

        Returns:
            str: Recommendation strength category
        """
        if score >= 0.8:
            return "Very Strong"
        elif score >= 0.6:
            return "Strong"
        elif score >= 0.4:
            return "Moderate"
        elif score >= 0.2:
            return "Weak"
        else:
            return "Very Weak"

    def save_recommendations_json(self, recommendations, output_path):
        """Save recommendations to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(recommendations, f, ensure_ascii=False, indent=2)
        print(f"💾 Complete ranked recommendations saved to {output_path}")

    def generate_detailed_summary_report(self, recommendations, output_path):
        """Generate a detailed summary report with ranking analysis"""

        total_clients = len(recommendations["clients"])
        total_available_products = recommendations.get("summary", {}).get("total_products_available", 0)

        # Analyze recommendation scores
        all_scores = []
        score_distributions = {"Very Strong": 0, "Strong": 0, "Moderate": 0, "Weak": 0, "Very Weak": 0}
        product_recommendation_count = {}

        for client in recommendations["clients"]:
            for rec in client["top_recommendations"]:
                score = rec["similarity_score"]
                all_scores.append(score)
                strength = rec["recommendation_strength"]
                score_distributions[strength] += 1

                product = rec["product"]
                if product not in product_recommendation_count:
                    product_recommendation_count[product] = {"count": 0, "total_score": 0, "ranks": []}
                product_recommendation_count[product]["count"] += 1
                product_recommendation_count[product]["total_score"] += score
                product_recommendation_count[product]["ranks"].append(rec["rank"])

        # Calculate average scores per product
        for product in product_recommendation_count:
            count = product_recommendation_count[product]["count"]
            total_score = product_recommendation_count[product]["total_score"]
            product_recommendation_count[product]["avg_score"] = total_score / count
            product_recommendation_count[product]["avg_rank"] = np.mean(product_recommendation_count[product]["ranks"])

        # Generate report
        report = f"""
MORAL PERSON RECOMMENDATION SYSTEM ANALYSIS REPORT
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================

OVERVIEW:
- Total clients processed: {total_clients}
- Total products available: {total_available_products}
- Total recommendation pairs generated: {len(all_scores)}
- Average recommendations per client: {len(all_scores) / total_clients:.1f}

SCORE DISTRIBUTION:
"""

        for strength, count in score_distributions.items():
            percentage = (count / len(all_scores)) * 100 if all_scores else 0
            report += f"- {strength}: {count:,} ({percentage:.1f}%)\n"

        if all_scores:
            report += f"""
SCORE STATISTICS:
- Highest similarity score: {max(all_scores):.4f}
- Lowest similarity score: {min(all_scores):.4f}
- Average similarity score: {np.mean(all_scores):.4f}
- Median similarity score: {np.median(all_scores):.4f}
- Standard deviation: {np.std(all_scores):.4f}

TOP 15 MOST FREQUENTLY RECOMMENDED PRODUCTS:
Rank | Product Name | Times Recommended | Avg Score | Avg Rank
-----|--------------|-------------------|-----------|----------"""

            # Sort products by recommendation frequency
            sorted_products = sorted(product_recommendation_count.items(),
                                   key=lambda x: x[1]["count"], reverse=True)

            for i, (product, stats) in enumerate(sorted_products[:15], 1):
                report += f"\n{i:2d}   | {product[:40]:<40} | {stats['count']:6d}        | {stats['avg_score']:8.4f}  | {stats['avg_rank']:8.1f}"

            report += f"""

TOP 15 HIGHEST SCORING PRODUCTS (by average score):
Rank | Product Name | Times Recommended | Avg Score | Avg Rank
-----|--------------|-------------------|-----------|----------"""

            # Sort products by average score
            sorted_by_score = sorted(product_recommendation_count.items(),
                                   key=lambda x: x[1]["avg_score"], reverse=True)

            for i, (product, stats) in enumerate(sorted_by_score[:15], 1):
                report += f"\n{i:2d}   | {product[:40]:<40} | {stats['count']:6d}        | {stats['avg_score']:8.4f}  | {stats['avg_rank']:8.1f}"

        report += f"""

SAMPLE CLIENT ANALYSIS:
Below are detailed recommendations for the first 3 clients:
"""

        # Show detailed breakdown for first 3 clients
        for i, client in enumerate(recommendations["clients"][:3], 1):
            report += f"""
--- CLIENT {i}: {client.get('RAISON_SOCIALE', 'N/A')[:50]} ---
Sector: {client.get('LIB_SECTEUR_ACTIVITE', 'N/A')}
Activity: {client.get('LIB_ACTIVITE', 'N/A')}
Current products: {client['summary']['current_products_count']}
Available recommendations: {client['summary']['total_available_products']}
Score range: {client['summary']['lowest_score']:.4f} - {client['summary']['highest_score']:.4f} (avg: {client['summary']['average_score']:.4f})

TOP 10 RECOMMENDATIONS:"""

            for rec in client["all_ranked_recommendations"][:10]:
                report += f"""
  {rec['rank']:2d}. {rec['product'][:50]:<50} | Score: {rec['similarity_score']:6.4f} | {rec['recommendation_strength']}"""

        report += f"""

QUALITY INSIGHTS:
- Products are ranked by similarity score from highest to lowest
- Recommendation strength categories help identify the most suitable matches
- Higher scores (closer to 1.0) indicate better semantic similarity
- Consider focusing on "Strong" and "Very Strong" recommendations for immediate action

FILES GENERATED:
- Complete ranked recommendations: JSON format with ALL products scored and ranked
- This analysis report: Detailed statistics and insights
"""

        # Save report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"📈 Detailed analysis report saved to {output_path}")

def run_moral_person_pipeline(client_data_path, product_mapping_path, contracts_path=None,
                             output_path="moral_person_recommendations.json",
                             save_model_path="moral_recommendation_model.pkl",
                             min_score_threshold=0.0):
    """
    Complete pipeline that generates ALL ranked recommendations for moral persons

    Args:
        client_data_path (str): Path to client data Excel file
        product_mapping_path (str): Path to product mapping Excel file
        contracts_path (str, optional): Path to contracts data
        output_path (str): Output JSON file path
        save_model_path (str): Path to save trained model
        min_score_threshold (float): Minimum similarity score to include (0.0 = show all)
    """

    print("🚀 Starting MORAL PERSON Recommendation Pipeline")
    print("=" * 60)

    try:
        # Initialize system
        rec_system = MoralPersonRecommendationSystem()

        # Train model
        print(f"🎯 Training model with product mapping: {product_mapping_path}")
        rec_system.train_model(product_mapping_path)

        # Save trained model
        print(f"💾 Saving model to: {save_model_path}")
        rec_system.save_model(save_model_path)

        # Load client data
        print(f"📊 Loading client data from: {client_data_path}")
        try:
            client_df = pd.read_excel(client_data_path, sheet_name='personne_morale')
            print(f"✅ Loaded {len(client_df)} clients")
        except Exception as e:
            print(f"❌ Error loading client data: {str(e)}")
            print("   - Trying to load without sheet specification...")
            client_df = pd.read_excel(client_data_path)
            print(f"✅ Loaded {len(client_df)} clients from default sheet")

        # Load contracts if provided
        contracts_df = None
        if contracts_path:
            print(f"📋 Loading contracts data from: {contracts_path}")
            try:
                contracts_df = pd.read_excel(contracts_path, sheet_name='Contrats')

                # Filter for moral products only
                moral_products = list(rec_system.product_embeddings.keys())
                contracts_df = contracts_df[contracts_df['LIB_PRODUIT'].isin(moral_products)]
                print(f"✅ Loaded {len(contracts_df)} relevant moral product contracts")

            except Exception as e:
                print(f"⚠️ Warning: Could not load contracts data: {str(e)}")
                contracts_df = None

        # Generate ALL RANKED recommendations
        print("🎯 Generating COMPLETE RANKED recommendations...")
        recommendations = rec_system.generate_recommendations(
            client_df,
            contracts_df,
            show_all_ranked=True,
            min_score_threshold=min_score_threshold
        )

        # Save to JSON
        print(f"💾 Saving complete recommendations to: {output_path}")
        rec_system.save_recommendations_json(recommendations, output_path)

        # Generate detailed analysis report
        analysis_path = f"detailed_analysis_{output_path.replace('.json', '.txt')}"
        rec_system.generate_detailed_summary_report(recommendations, analysis_path)

        print("🎉 MORAL PERSON pipeline completed successfully!")
        print(f"📁 Files generated:")
        print(f"   - {output_path} (Complete ranked recommendations)")
        print(f"   - {save_model_path} (Trained model)")
        print(f"   - {analysis_path} (Detailed analysis report)")

        return recommendations

    except Exception as e:
        print(f"❌ Pipeline failed: {str(e)}")
        raise

def prepare_moral_client_data(recommendations, contracts_df=None):
    """
    Prepare moral client data in the format similar to physical persons

    Args:
        recommendations (dict): Generated recommendations
        contracts_df (pd.DataFrame, optional): Contracts data for expired products

    Returns:
        dict: Formatted data structure
    """
    clients_data = []

    for client in recommendations["clients"]:
        # Get expired products if contracts data provided
        expired_products = []
        if contracts_df is not None:
            client_contracts = contracts_df[
                (contracts_df['REF_PERSONNE'] == client['REF_PERSONNE']) &
                (contracts_df['LIB_ETAT_CONTRAT'] == 'EXPIRE')
            ]

            for _, contract in client_contracts.iterrows():
                expired_products.append({
                    "product": contract['LIB_PRODUIT'],
                    "date d'expiration": contract.get('DATE_EXPIRATION', 'Unknown')
                })

        # Format top recommendations
        top_recommendations = []
        for rec in client["all_ranked_recommendations"]:
            top_recommendations.append({
                "rank": rec['rank'],
                "product": rec['product'],
                "final_score": rec['similarity_score'],
                "recommendation_strength": rec['recommendation_strength'],
                "target_profiles": rec['target_profiles']
            })


        # Create client data
        client_data = {
            "REF_PERSONNE": client['REF_PERSONNE'],
            "type": "morale",
            "raison_sociale": client.get('RAISON_SOCIALE', 'N/A'),
            "matricule_fiscale": client.get('matricule_fiscale', 'N/A'),
            "secteur_activite": client.get('LIB_SECTEUR_ACTIVITE', 'N/A'),
            "activite": client.get('LIB_ACTIVITE', 'N/A'),
            "current_products": client.get('current_products', []),
            "expired_products": expired_products,
            "top_recommendations": top_recommendations
        }

        clients_data.append(client_data)
    print(f"✅ Prepared data for client: {client_data}")

    return {"clients": clients_data}