import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Configuration de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StatutInteraction(Enum):
    NOUVEAU = "nouveau"
    INTERESSE = "interesse"
    DEVIS_DEMANDE = "devis_demande"
    NON_INTERESSE = "non_interesse"
    FERME = "ferme"
    EN_COURS = "en_cours"


class TypeReponse(Enum):
    INTERESSE = "interesse"
    NON_INTERESSE = "non_interesse"
    DEMANDE_DEVIS = "demande_devis"
    BESOIN_INFO = "besoin_info"
    INCONNU = "inconnu"
    EN_COURS = "en_cours"

@dataclass
class InteractionEmail:
    email_id: str
    expediteur_email: str
    sujet: str
    corps: str
    timestamp: datetime
    type_reponse: TypeReponse
    reponse_ia: str
    conversation_id: str
    statut: StatutInteraction
    branche_assurance: Optional[str] = None

class GestionnaireBaseDonnees:
    """Gestionnaire de base de données PostgreSQL pour l'agent email"""
    
    def __init__(self, config_db: Dict):
        self.config_db = config_db
        self.init_base_donnees()
    
    def obtenir_connexion(self):
        """Obtient une connexion à la base PostgreSQL"""
        try:
            conn = psycopg2.connect(
                host=self.config_db['host'],
                database=self.config_db['database'],
                user=self.config_db['user'],
                password=self.config_db['password'],
                port=self.config_db['port']
            )
            return conn
        except Exception as e:
            logger.error(f"Erreur connexion PostgreSQL: {e}")
            raise
    
    def init_base_donnees(self):
        """Initialise la base de données avec les tables nécessaires"""
        conn = self.obtenir_connexion()
        cursor = conn.cursor()
        
        try:
            # Table des conversations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    expediteur_email TEXT NOT NULL,
                    cree_le TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    derniere_maj TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    statut TEXT DEFAULT 'actif'
                )
            ''')
            
            # Table des interactions email
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interactions_email (
                    id SERIAL PRIMARY KEY,
                    email_id TEXT UNIQUE,
                    conversation_id TEXT,
                    expediteur_email TEXT NOT NULL,
                    sujet TEXT,
                    corps TEXT,
                    type_reponse TEXT,
                    reponse_ia TEXT,
                    statut TEXT,
                    branche_assurance TEXT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            ''')
            
            
            # Créer des index pour améliorer les performances
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_interactions_expediteur 
                ON interactions_email(expediteur_email)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_interactions_timestamp 
                ON interactions_email(timestamp)
            ''')
            
            conn.commit()
            logger.info("Base de données PostgreSQL initialisée avec succès")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Erreur lors de l'initialisation de la base: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def sauvegarder_interaction(self, interaction: InteractionEmail):
        """Sauvegarde l'interaction email"""
        conn = self.obtenir_connexion()
        cursor = conn.cursor()
        
        try:
            # Insérer ou ignorer la conversation
            cursor.execute('''
                INSERT INTO conversations (id, expediteur_email)
                VALUES (%s, %s)
                ON CONFLICT (id) DO NOTHING
            ''', (interaction.conversation_id, interaction.expediteur_email))
            
            # Mettre à jour la dernière modification
            cursor.execute('''
                UPDATE conversations 
                SET derniere_maj = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (interaction.conversation_id,))
            
            # Insérer ou remplacer l'interaction
            cursor.execute('''
                INSERT INTO interactions_email 
                (email_id, conversation_id, expediteur_email, sujet, corps, 
                 type_reponse, reponse_ia, statut, branche_assurance, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (email_id) DO UPDATE SET
                    type_reponse = EXCLUDED.type_reponse,
                    reponse_ia = EXCLUDED.reponse_ia,
                    statut = EXCLUDED.statut,
                    branche_assurance = EXCLUDED.branche_assurance,
                    timestamp = EXCLUDED.timestamp
            ''', (interaction.email_id, interaction.conversation_id, 
                  interaction.expediteur_email, interaction.sujet, 
                  interaction.corps, interaction.type_reponse.value, 
                  interaction.reponse_ia, interaction.statut.value,
                  interaction.branche_assurance, interaction.timestamp))
            
            conn.commit()
            logger.info(f"Interaction sauvegardée: {interaction.expediteur_email}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Erreur lors de la sauvegarde: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def obtenir_historique_conversation(self, expediteur_email: str, limite: int = 5) -> List[Dict]:
        """Obtient l'historique de conversation"""
        conn = self.obtenir_connexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT corps, reponse_ia, type_reponse, statut, timestamp
                FROM interactions_email
                WHERE expediteur_email = %s
                ORDER BY timestamp DESC
                LIMIT %s
            ''', (expediteur_email, limite))
            
            historique = []
            for row in cursor.fetchall():
                historique.append({
                    'corps': row['corps'],
                    'reponse_ia': row['reponse_ia'],
                    'type_reponse': row['type_reponse'],
                    'statut': row['statut'],
                    'timestamp': row['timestamp']
                })
            
            return historique
            
        except Exception as e:
            logger.error(f"Erreur récupération historique: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def obtenir_qa_par_branche(self, branche: str) -> List[Dict]:
        """Obtient les Q&A pour une branche d'assurance"""
        conn = self.obtenir_connexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT question, reponse, garantie
                FROM qa_assurance
                WHERE branche = %s
            ''', (branche,))
            
            qa_list = []
            for row in cursor.fetchall():
                qa_list.append({
                    'question': row['question'],
                    'reponse': row['reponse'],
                    'garantie': row['garantie']
                })
            
            return qa_list
            
        except Exception as e:
            logger.error(f"Erreur récupération Q&A: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def mettre_a_jour_statut_derniere_interaction(self, email_expediteur: str, nouveau_statut: str) -> bool:
        """Met à jour le statut de la dernière interaction"""
        conn = self.obtenir_connexion()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE interactions_email 
                SET statut = %s
                WHERE expediteur_email = %s
                  AND timestamp = (
                      SELECT MAX(timestamp) 
                      FROM interactions_email 
                      WHERE expediteur_email = %s
                  )
            ''', (nouveau_statut, email_expediteur, email_expediteur))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Erreur mise à jour statut: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

def tester_connexion_postgresql(config: Dict) -> bool:
    """Teste la connexion PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=config['db_host'],
            database=config['db_name'],
            user=config['db_user'],
            password=config['db_password'],
            port=config['db_port']
        )
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Connexion PostgreSQL réussie: {version[0]}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur connexion PostgreSQL: {e}")
        print(f"Impossible de se connecter à PostgreSQL: {e}")
        print("Vérifiez que:")
        print("  - PostgreSQL est installé et démarré")
        print("  - La base 'Bh' existe")
        print("  - L'utilisateur 'postgres' a les bonnes permissions")
        return False