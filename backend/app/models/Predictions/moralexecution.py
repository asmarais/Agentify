import importlib
from app.models.Predictions import moralrecommendation as moral_recommendation
from importlib import reload
import pandas as pd
import os

# Set environment variables to avoid PyTorch issues
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Force CPU usage


def generate_moral_recommendations(
    client_data_file="Data.xlsx",
    product_mapping_file="Mappingprod.xlsx",
    contracts_file="Data.xlsx",
    output_model="moral_recommendation_model.pkl",
    base_data_dir=None,
    start: int = 0,
    end: int = None
):
    """
    Generate recommendations for moral persons using the MoralPersonRecommendationSystem.

    Args:
        client_data_file (str): Filename for client data Excel file.
        product_mapping_file (str): Filename for product mapping Excel file.
        contracts_file (str): Filename for contracts Excel file.
        output_model (str): Path to save the trained model.
        base_data_dir (str): Base directory for the data files. Defaults to ../../data relative to this script.
        start (int): Starting index for pagination (default=0).
        end (int): Ending index for pagination (default=None, meaning no limit).

    Returns:
        dict | list: Paginated recommendations.
    """

    # Reload the module to get the latest updates
    importlib.reload(moral_recommendation)

    # Setup data directory
    if base_data_dir is None:
        parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        base_data_dir = os.path.join(parent_dir, 'data')

    # Build full paths
    client_data_path = os.path.join(base_data_dir, client_data_file)
    product_mapping_path = os.path.join(base_data_dir, product_mapping_file)
    contracts_path = os.path.join(base_data_dir, contracts_file)

    # Check required files
    for name, path in [
        ("Client Data", client_data_path),
        ("Product Mapping", product_mapping_path),
        ("Contracts", contracts_path),
    ]:
        if os.path.exists(path):
            print(f"✅ {name}: Found")
        else:
            print(f"❌ {name}: NOT FOUND - {path}")

    # Create recommendation system
    print("🤖 Initializing recommendation system...")
    try:
        rec_system = moral_recommendation.MoralPersonRecommendationSystem()
        print("✅ Recommendation system initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing recommendation system: {e}")
        if "meta tensor" in str(e).lower() or "torch" in str(e).lower():
            print("🔧 PyTorch/SentenceTransformer issue detected. Trying with environment cleanup...")
            try:
                # Try to clear any cached models
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                # Retry initialization
                rec_system = moral_recommendation.MoralPersonRecommendationSystem()
                print("✅ Recommendation system initialized after cleanup")
            except Exception as e2:
                raise RuntimeError(f"Failed to initialize recommendation system: {e2}")
        else:
            raise

    # Train model
    print("Training model with product mapping...")
    rec_system.train_model(product_mapping_path)

    # Save model
    print(f"Saving model to: {output_model}")
    rec_system.save_model(output_model)

    # Load client data
    print(f"Loading moral client data from: {client_data_path}")
    try:
        client_df = pd.read_excel(client_data_path, sheet_name='personne_morale')
        print(f"✅ Loaded {len(client_df)} moral clients")
        
        # Apply pagination to the dataframe BEFORE processing
        if end is not None:
            client_df = client_df.iloc[start:end]
        else:
            client_df = client_df.iloc[start:]
            
        print(f"📊 Processing {len(client_df)} clients (from index {start} to {end if end else 'end'})")
        
    except Exception as e:
        print(f"Warning: Could not load from 'personne_morale' sheet: {str(e)}")
        print("   - Trying default sheet...")
        client_df = pd.read_excel(client_data_path)
        
        # Apply pagination to the dataframe BEFORE processing
        if end is not None:
            client_df = client_df.iloc[start:end]
        else:
            client_df = client_df.iloc[start:]
            
        print(f"✅ Loaded {len(client_df)} clients from default sheet")

    # Load contracts data
    contracts_df = None
    if contracts_path:
        print(f"Loading contracts data from: {contracts_path}")
        try:
            contracts_df = pd.read_excel(contracts_path, sheet_name='Contrats')

            # Filter relevant products
            moral_products = list(rec_system.product_embeddings.keys())
            contracts_df = contracts_df[contracts_df['LIB_PRODUIT'].isin(moral_products)]
            print(f"✅ Loaded {len(contracts_df)} relevant moral product contracts")

        except Exception as e:
            print(f"Warning: Could not load contracts data: {str(e)}")

    # Generate recommendations
    print("Generating COMPLETE RANKED recommendations for moral persons...")
    recommendations = rec_system.generate_recommendations(
        client_df,
        contracts_df,
        show_all_ranked=True,
        min_score_threshold=0.0
    )

    # Apply pagination
    if isinstance(recommendations, (list, tuple)):
        return recommendations[start:end]
    elif isinstance(recommendations, dict):
        # If it's a dict, convert to list of items before slicing
        items = list(recommendations.items())[start:end]
        return dict(items)
    else:
        return recommendations
