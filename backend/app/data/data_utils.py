import pandas as pd
from typing import Dict, Any
import os

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