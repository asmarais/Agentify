import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import re
import json
from datetime import datetime
import logging
from typing import Dict, List, Optional, TypedDict, Annotated
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dataclasses import dataclass
from enum import Enum

from langgraph.graph import StateGraph
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

# Configuration de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StatutInteraction(Enum):
    NOUVEAU = "nouveau"
    EN_COURS = "en_cours"  
    INTERESSE = "interesse"
    DEVIS_DEMANDE = "devis_demande"
    NON_INTERESSE = "non_interesse"
    FERME = "ferme"

class TypeReponse(Enum):
    INTERESSE = "interesse"
    NON_INTERESSE = "non_interesse"
    DEMANDE_DEVIS = "demande_devis"
    BESOIN_INFO = "besoin_info"
    INCONNU = "inconnu"

# État de l'agent LangGraph
class EtatAgent(TypedDict):
    email_contenu: str
    email_expediteur: str
    email_sujet: str
    historique_conversation: List[Dict]
    type_reponse: Optional[TypeReponse]
    reponse_ia: Optional[str]
    statut_interaction: Optional[StatutInteraction]
    question_suivi: Optional[str]
    message_id: str
    branche_assurance: Optional[str]

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
            
            # Table des données client
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS donnees_client (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE,
                    nom TEXT,
                    entreprise TEXT,
                    telephone TEXT,
                    niveau_interet INTEGER DEFAULT 0,
                    dernier_contact TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            ''')
            
            # Table Q&A assurance
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS qa_assurance (
                    id SERIAL PRIMARY KEY,
                    branche TEXT,
                    garantie TEXT,
                    question TEXT,
                    reponse TEXT
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
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_qa_branche 
                ON qa_assurance(branche)
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

# Outils LangGraph mis à jour pour PostgreSQL
@tool
def mettre_a_jour_statut_interaction(email_expediteur: str, nouveau_statut: str) -> str:
    """Met à jour le statut d'interaction dans la base de données PostgreSQL"""
    try:
        # Récupérer la config de la base depuis l'environnement global
        config_db = {
            'host': 'localhost',
            'database': 'Bh',
            'user': 'postgres',
            'password': 'postgres',
            'port': 5432
        }
        
        conn = psycopg2.connect(
            host=config_db['host'],
            database=config_db['database'],
            user=config_db['user'],
            password=config_db['password'],
            port=config_db['port']
        )
        cursor = conn.cursor()
        
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
        cursor.close()
        conn.close()
        
        logger.info(f"Statut mis à jour pour {email_expediteur}: {nouveau_statut}")
        return f"Statut mis à jour avec succès pour {email_expediteur}"
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du statut: {e}")
        return f"Erreur lors de la mise à jour: {str(e)}"

@tool
def rechercher_info_assurance(branche: str, mot_cle: str) -> str:
    """Recherche des informations d'assurance par branche et mot-clé"""
    try:
        config_db = {
            'host': 'localhost',
            'database': 'Bh',
            'user': 'postgres',
            'password': 'postgres',
            'port': 5432
        }
        
        conn = psycopg2.connect(
            host=config_db['host'],
            database=config_db['database'],
            user=config_db['user'],
            password=config_db['password'],
            port=config_db['port']
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute('''
            SELECT question, reponse, garantie
            FROM qa_assurance
            WHERE branche ILIKE %s AND (question ILIKE %s OR reponse ILIKE %s)
            LIMIT 3
        ''', (f'%{branche}%', f'%{mot_cle}%', f'%{mot_cle}%'))
        
        resultats = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if resultats:
            info = "Voici les informations pertinentes :\n\n"
            for row in resultats:
                info += f"**{row['garantie']}**: {row['question']}\n{row['reponse']}\n\n"
            return info
        else:
            return "Aucune information spécifique trouvée. Je peux vous diriger vers un conseiller spécialisé."
            
    except Exception as e:
        logger.error(f"Erreur lors de la recherche d'info: {e}")
        return "Erreur lors de la recherche d'informations."

class ClassificateurEmail:
    """Classification des emails en français uniquement"""

    def __init__(self):
        self.motifs_non_interesse: List[re.Pattern] = [
            re.compile(r'\bnon\b', re.IGNORECASE),
            re.compile(r'pas\s*int[eé]ress[ée]', re.IGNORECASE),
            re.compile(r'pas\s*merci', re.IGNORECASE),
            re.compile(r'd[eé]sinscrire', re.IGNORECASE),
            re.compile(r'pas\s*pour\s*nous', re.IGNORECASE),
            re.compile(r'retirez\s*moi', re.IGNORECASE),
            re.compile(r'pas\s*maintenant', re.IGNORECASE),
            re.compile(r'je refuse', re.IGNORECASE),
            re.compile(r'pas\s*en\s*ce\s*moment', re.IGNORECASE),
            re.compile(r'se\s*d[eé]sabonner', re.IGNORECASE)
        ]

        self.motifs_interesse: List[re.Pattern] = [
            re.compile(r'\boui\b', re.IGNORECASE),
            re.compile(r'je suis int[eé]ress[ée]', re.IGNORECASE),
            re.compile(r'dites\s*m\'en\s*plus', re.IGNORECASE),
            re.compile(r'c[aà]\s*a\s*l[\'’]air\s*int[eé]ressant', re.IGNORECASE),
            re.compile(r'je\s*veux', re.IGNORECASE),
            re.compile(r'envoyez\s*moi', re.IGNORECASE),
            re.compile(r'quand\s*pouvons\s*nous', re.IGNORECASE),
            re.compile(r'planifier', re.IGNORECASE)
        ]

        self.motifs_devis: List[re.Pattern] = [
            re.compile(r'\bdevis\b', re.IGNORECASE),
            re.compile(r'\bprix\b', re.IGNORECASE),
            re.compile(r'\bco[uû]t\b', re.IGNORECASE),
            re.compile(r'estimation', re.IGNORECASE),
            re.compile(r'combien', re.IGNORECASE),
            re.compile(r'tarification', re.IGNORECASE),
            re.compile(r'budget', re.IGNORECASE)
        ]

        self.motifs_info: List[re.Pattern] = [
            re.compile(r'plus\s*d[\'’]informations', re.IGNORECASE),
            re.compile(r'd[eé]tails', re.IGNORECASE),
            re.compile(r'explications?\s*moi', re.IGNORECASE),
            re.compile(r'comment\s*ça\s*fonctionne', re.IGNORECASE),
            re.compile(r'qu[\'’]est\s*ce\s*que\s*c[\'’]est', re.IGNORECASE)
        ]

    def detecter_branche_assurance(self, contenu: str) -> Optional[str]:
        """Détecte la branche d'assurance mentionnée"""
        contenu_lower = contenu.lower()
        
        branches = {
            'auto': ['voiture', 'auto', 'véhicule', 'automobile', 'moto', 'scooter'],
            'habitation': ['maison', 'logement', 'appartement', 'habitation', 'domicile'],
            'santé': ['santé', 'médical', 'maladie', 'hospitalisation', 'soins'],
            'vie': ['vie', 'décès', 'capital', 'épargne', 'retraite'],
            'voyage': ['voyage', 'vacances', 'étranger', 'rapatriement']
        }
        
        for branche, mots_cles in branches.items():
            if any(mot in contenu_lower for mot in mots_cles):
                return branche.title()
        
        return None
    
    def classifier_email(self, contenu: str) -> TypeReponse:
        """Classifie le type de réponse attendu"""
        contenu_clean = re.sub(r'<[^>]+>', '', contenu).lower()
        
        # Vérifier d'abord le non-intérêt (priorité)
        for motif in self.motifs_non_interesse:
            if re.search(motif, contenu_clean):
                logger.info(f"Classifié comme NON_INTERESSE: {motif}")
                return TypeReponse.NON_INTERESSE
        
        # Vérifier les demandes de devis
        for motif in self.motifs_devis:
            if re.search(motif, contenu_clean):
                logger.info(f"Classifié comme DEMANDE_DEVIS: {motif}")
                return TypeReponse.DEMANDE_DEVIS
        
        # Vérifier l'intérêt
        for motif in self.motifs_interesse:
            if re.search(motif, contenu_clean):
                logger.info(f"Classifié comme INTERESSE: {motif}")
                return TypeReponse.INTERESSE
        
        # Vérifier besoin d'info
        for motif in self.motifs_info:
            if re.search(motif, contenu_clean):
                logger.info(f"Classifié comme BESOIN_INFO: {motif}")
                return TypeReponse.BESOIN_INFO
        
        logger.info("Classifié comme INCONNU")
        return TypeReponse.INCONNU

class AgentEmailBHAssurance:
    """Agent email principal utilisant LangGraph et PostgreSQL"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Configuration PostgreSQL
        self.config_db = {
            'host': config.get('db_host', 'localhost'),
            'database': config.get('db_name', 'Bh'),
            'user': config.get('db_user', 'postgres'),
            'password': config.get('db_password', 'postgres'),
            'port': config.get('db_port', 5432)
        }
        
        self.db_manager = GestionnaireBaseDonnees(self.config_db)
        self.classificateur = ClassificateurEmail()
        self.llm = OllamaLLM(model=config.get('modele_llm', 'llama2'))
        
        # Configuration email
        self.email_address = config['email_address']
        self.password = config['password']
        self.imap_server = config['imap_server']
        self.smtp_server = config['smtp_server']
        self.imap_port = config.get('imap_port', 993)
        self.smtp_port = config.get('smtp_port', 587)
        
        # Initialiser les outils
        self.outils = [mettre_a_jour_statut_interaction, rechercher_info_assurance]
        
        # Construire le graphique LangGraph
        self.graphique = self.construire_graphique()
        
        # Charger les données Q&A
        self.charger_donnees_qa()
    
    def charger_donnees_qa(self):
        """Charge les données Q&A d'assurance française dans la base"""
        donnees_qa = [
            ("Généralités", "Définitions", "Qu'est-ce qu'une prime d'assurance ?", 
             "La prime d'assurance est la somme que vous payez régulièrement à la compagnie d'assurance pour bénéficier de la couverture prévue dans votre contrat."),
            ("Généralités", "Définitions", "Qu'est-ce qu'une franchise ?", 
             "La franchise est la partie du sinistre restée à votre charge. Par exemple, si la franchise est de 200 DT et le sinistre de 1 000 DT, l'assurance vous indemnisera 800 DT."),
            ("Auto", "RC", "Que couvre la garantie Vol ?", 
             "Elle indemnise la perte du véhicule ou les dommages dus à une tentative de vol (effraction, bris de serrure, câbles arrachés)."),
            ("Habitation", "Incendie", "Que couvre la garantie incendie habitation ?", 
             "Les dommages matériels causés par un incendie, une explosion ou la foudre."),
            ("Santé", "Soins médicaux", "Est-ce que les consultations chez un généraliste sont remboursées ?", 
             "Oui, dans la limite des plafonds fixés au contrat."),
            ("Auto", "Tous risques", "Que couvre l'assurance tous risques auto ?",
             "Elle couvre tous les dommages subis par votre véhicule, qu'ils soient dus à un accident, un vol, un incendie, ou des actes de vandalisme."),
            ("Habitation", "Vol", "Ma garantie vol habitation couvre-t-elle les bijoux ?",
             "Oui, mais généralement avec un plafond spécifique. Il est recommandé de faire expertiser vos bijoux de valeur."),
            ("Santé", "Hospitalisation", "L'hospitalisation est-elle prise en charge intégralement ?",
             "Cela dépend de votre niveau de couverture. Nos formules Premium couvrent 100% des frais d'hospitalisation."),
            ("Vie", "Capital décès", "Comment fonctionne le capital décès ?",
             "En cas de décès de l'assuré, le capital prévu au contrat est versé aux bénéficiaires désignés."),
            ("Voyage", "Rapatriement", "Que couvre l'assurance rapatriement ?",
             "Elle couvre les frais de transport sanitaire vers un hôpital approprié ou vers votre domicile en cas d'accident ou de maladie grave à l'étranger.")
        ]
        
        conn = self.db_manager.obtenir_connexion()
        cursor = conn.cursor()
        
        try:
            for branche, garantie, question, reponse in donnees_qa:
                cursor.execute('''
                    INSERT INTO qa_assurance (branche, garantie, question, reponse)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                ''', (branche, garantie, question, reponse))
            
            conn.commit()
            logger.info("Données Q&A chargées en PostgreSQL")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Erreur chargement Q&A: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def construire_graphique(self):
        """Construit le graphique LangGraph pour l'agent"""
        workflow = StateGraph(EtatAgent)
        
        # Ajouter les nœuds
        workflow.add_node("analyser_email", self.analyser_email)
        workflow.add_node("generer_reponse", self.generer_reponse)
        workflow.add_node("appliquer_outils", self.appliquer_outils)
        workflow.add_node("finaliser_reponse", self.finaliser_reponse)
        
        # Définir les arêtes
        workflow.set_entry_point("analyser_email")
        workflow.add_edge("analyser_email", "generer_reponse")
        workflow.add_edge("generer_reponse", "appliquer_outils")
        workflow.add_edge("appliquer_outils", "finaliser_reponse")
        
        return workflow.compile()
    
    def analyser_email(self, etat: EtatAgent) -> EtatAgent:
        """Analyse l'email et détermine le type de réponse"""
        logger.info(f"Analyse de l'email de {etat['email_expediteur']}")
        
        # Classifier l'email
        type_reponse = self.classificateur.classifier_email(etat['email_contenu'])
        etat['type_reponse'] = type_reponse
        
        # Détecter la branche d'assurance
        branche = self.classificateur.detecter_branche_assurance(etat['email_contenu'])
        etat['branche_assurance'] = branche
        
        # Déterminer le statut
        if type_reponse == TypeReponse.INTERESSE:
            etat['statut_interaction'] = StatutInteraction.INTERESSE
        elif type_reponse == TypeReponse.DEMANDE_DEVIS:
            etat['statut_interaction'] = StatutInteraction.DEVIS_DEMANDE
        elif type_reponse == TypeReponse.NON_INTERESSE:
            etat['statut_interaction'] = StatutInteraction.NON_INTERESSE
        else:
            etat['statut_interaction'] = StatutInteraction.EN_COURS
        
        logger.info(f"Type de réponse: {type_reponse.value}, Branche: {branche}")
        
        return etat
    
    def generer_reponse(self, etat: EtatAgent) -> EtatAgent:
        """Génère la réponse IA en français"""
        logger.info("Génération de la réponse IA")
        
        # Obtenir l'historique
        historique = self.db_manager.obtenir_historique_conversation(etat['email_expediteur'])
        etat['historique_conversation'] = historique
        
        # Prompt template en français
        prompt_template = self.obtenir_template_prompt(etat['type_reponse'])
        
        # Préparer le contexte
        contexte_historique = self.formater_historique(historique)
        contexte_qa = ""
        
        if etat['branche_assurance']:
            qa_list = self.db_manager.obtenir_qa_par_branche(etat['branche_assurance'])
            if qa_list:
                contexte_qa = "\n".join([f"Q: {qa['question']}\nR: {qa['reponse']}" for qa in qa_list[:3]])
        
        # Générer la réponse
        try:
            prompt = prompt_template.format(
                email_contenu=etat['email_contenu'],
                expediteur=etat['email_expediteur'],
                historique=contexte_historique,
                branche=etat['branche_assurance'] or "Générale",
                contexte_qa=contexte_qa
            )
            
            reponse = self.llm.invoke(prompt)
            etat['reponse_ia'] = reponse.strip()
            
            # Générer question de suivi si intéressé
            if etat['type_reponse'] == TypeReponse.INTERESSE and etat['branche_assurance']:
                etat['question_suivi'] = self.generer_question_suivi(etat['branche_assurance'])
            
            logger.info(f"Réponse générée: {reponse[:100]}...")
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération: {e}")
            etat['reponse_ia'] = self.obtenir_reponse_fallback(etat['type_reponse'])
        
        return etat
    
    def appliquer_outils(self, etat: EtatAgent) -> EtatAgent:
        """Applique les outils nécessaires"""
        logger.info("Application des outils")
        
        # Mettre à jour le statut si nécessaire
        if etat['statut_interaction']:
            try:
                result = mettre_a_jour_statut_interaction.invoke({
                    "email_expediteur": etat['email_expediteur'],
                    "nouveau_statut": etat['statut_interaction'].value
                })
                logger.info(f"Outil appliqué: {result}")
            except Exception as e:
                logger.error(f"Erreur lors de l'application d'outil: {e}")
        
        return etat
    
    def finaliser_reponse(self, etat: EtatAgent) -> EtatAgent:
        """Finalise la réponse avec signature et question de suivi"""
        logger.info("Finalisation de la réponse")
        
        reponse_finale = etat['reponse_ia']
        
        # Ajouter question de suivi si disponible
        if etat.get('question_suivi'):
            reponse_finale += f"\n\n{etat['question_suivi']}"
        
        # Ajouter signature
        reponse_finale += "\n\n---\nCordialement,\nVotre conseiller BH Assurance\nTél: +216 XX XXX XXX\nEmail: contact@bh-assurance.tn"
        
        etat['reponse_ia'] = reponse_finale
        
        return etat
    
    def obtenir_template_prompt(self, type_reponse: TypeReponse) -> ChatPromptTemplate:
        """Obtient le template de prompt selon le type de réponse"""
        templates = {
            TypeReponse.INTERESSE: ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(
                    "Vous êtes un conseiller professionnel chez BH Assurance en Tunisie. "
                    "Le client a exprimé un intérêt pour nos services d'assurance. "
                    "Répondez toujours en français, de manière professionnelle et engageante. "
                    "Respectez strictement la limite de 150 mots."
                ),
                HumanMessagePromptTemplate.from_template(
                    "Générez une réponse professionnelle pour ce client intéressé.\n"
                    "Email du client: {email_contenu}\n"
                    "Branche d'assurance: {branche}\n"
                    "Historique: {historique}\n"
                    "Contexte produits: {contexte_qa}\n\n"
                    "Répondez en:\n"
                    "1. Remerciant le client pour son intérêt\n"
                    "2. Fournissant des informations spécifiques à sa demande pour l'assurance {branche}\n\n"
                    "Maximum 150 mots. Ne signez pas le message."
                )
            ]),
            
            TypeReponse.NON_INTERESSE: ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(
                    "Vous êtes un conseiller professionnel chez BH Assurance en Tunisie. "
                    "Le client n'est pas intéressé par nos services. "
                    "Répondez de façon respectueuse et professionnelle en français. "
                    "Respectez strictement la limite de 80 mots."
                ),
                HumanMessagePromptTemplate.from_template(
                    "Générez une réponse respectueuse pour ce client non intéressé.\n"
                    "Email du client: {email_contenu}\n"
                    "Historique: {historique}\n\n"
                    "Répondez en:\n"
                    "1. Remerciant pour le temps accordé\n"
                    "2. Laissant la porte ouverte pour l'avenir\n"
                    "3. Proposant de rester en contact pour des mises à jour occasionnelles\n\n"
                    "Maximum 80 mots. Ton respectueux et professionnel."
                )
            ]),
            
            TypeReponse.DEMANDE_DEVIS: ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(
                    "Vous êtes un conseiller professionnel chez BH Assurance en Tunisie. "
                    "Le client demande un devis d'assurance. "
                    "Répondez en français de manière professionnelle et rassurante. "
                    "Respectez strictement la limite de 120 mots."
                ),
                HumanMessagePromptTemplate.from_template(
                    "Générez une réponse professionnelle pour cette demande de devis.\n"
                    "Email du client: {email_contenu}\n"
                    "Branche: {branche}\n"
                    "Contexte produits: {contexte_qa}\n\n"
                    "Répondez en:\n"
                    "1. Remerciant pour la demande de devis\n"
                    "2. Expliquant les informations nécessaires pour un devis précis\n"
                    "3. Proposant un rendez-vous pour évaluer ses besoins\n"
                    "4. Mentionnant que le devis est gratuit et sans engagement\n\n"
                    "Maximum 120 mots."
                )
            ]),
            
            TypeReponse.BESOIN_INFO: ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(
                    "Vous êtes un conseiller professionnel chez BH Assurance en Tunisie. "
                    "Le client demande plus d'informations sur nos services. "
                    "Répondez en français de manière informative et utile. "
                    "Respectez strictement la limite de 140 mots."
                ),
                HumanMessagePromptTemplate.from_template(
                    "Générez une réponse informative pour cette demande d'information.\n"
                    "Email du client: {email_contenu}\n"
                    "Branche: {branche}\n"
                    "Contexte produits: {contexte_qa}\n\n"
                    "Répondez en:\n"
                    "1. Fournissant les informations demandées\n"
                    "2. Utilisant le contexte produits disponible\n"
                    "3. Proposant un contact direct pour plus de détails\n"
                    "4. Restant informatif et utile\n\n"
                    "Maximum 140 mots."
                )
            ])
        }
        
        return templates.get(type_reponse, templates[TypeReponse.BESOIN_INFO])
    
    def generer_question_suivi(self, branche: str) -> str:
        """Génère une question de suivi appropriée"""
        questions_suivi = {
            'Auto': "Quel type de véhicule souhaitez-vous assurer et quelle est votre utilisation principale (quotidienne, professionnelle, loisirs) ?",
            'Habitation': "Votre logement est-il une maison individuelle ou un appartement, et êtes-vous propriétaire ou locataire ?",
            'Santé': "Avez-vous des besoins spécifiques en matière de soins médicaux ou souhaitez-vous une couverture familiale ?",
            'Vie': "Cherchez-vous une assurance vie pour la protection de votre famille ou comme placement d'épargne ?",
            'Voyage': "Voyagez-vous fréquemment ou avez-vous un voyage spécifique en vue ?"
        }
        return questions_suivi.get(branche, "Y a-t-il des aspects spécifiques de nos services d'assurance qui vous intéressent particulièrement ?")
    
    def formater_historique(self, historique: List[Dict]) -> str:
        """Formate l'historique de conversation"""
        if not historique:
            return "Pas d'historique précédent"
        
        return "\n".join([
            f"Client: {h['corps'][:100]}... -> Statut: {h['statut']}"
            for h in historique[:2]
        ])
    
    def obtenir_reponse_fallback(self, type_reponse: TypeReponse) -> str:
        """Fournit des réponses de secours"""
        reponses_fallback = {
            TypeReponse.INTERESSE: "Merci pour votre intérêt pour BH Assurance ! Un conseiller vous contactera sous 24h pour discuter de vos besoins spécifiques.",
            TypeReponse.NON_INTERESSE: "Merci pour votre temps. N'hésitez pas à nous recontacter si vos besoins évoluent.",
            TypeReponse.DEMANDE_DEVIS: "Je vais préparer votre devis personnalisé. Un conseiller vous contactera pour finaliser les détails.",
            TypeReponse.BESOIN_INFO: "Je serais ravi de répondre à vos questions. Un expert vous contactera pour vous fournir toutes les informations nécessaires."
        }
        return reponses_fallback.get(type_reponse, "Merci pour votre message. Notre équipe vous répondra rapidement.")
    
    def connecter_imap(self) -> imaplib.IMAP4_SSL:
        """Connexion IMAP"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            return mail
        except Exception as e:
            logger.error(f"Erreur connexion IMAP: {e}")
            raise
    
    def connecter_smtp(self) -> smtplib.SMTP:
        """Connexion SMTP"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.password)
            return server
        except Exception as e:
            logger.error(f"Erreur connexion SMTP: {e}")
            raise
    
    def extraire_contenu_email(self, msg) -> Dict:
        """Extrait le contenu de l'email"""
        donnees_email = {
            'sujet': msg.get('Subject', ''),
            'from': msg.get('From', ''),
            'date': msg.get('Date', ''),
            'corps': '',
            'message_id': msg.get('Message-ID', '')
        }
        
        # Extraction du corps avec gestion charset
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    charset = part.get_content_charset() or 'utf-8'
                    donnees_email['corps'] = part.get_payload(decode=True).decode(charset, errors='ignore')
                    break
        else:
            charset = msg.get_content_charset() or 'utf-8'
            donnees_email['corps'] = msg.get_payload(decode=True).decode(charset, errors='ignore')
        
        return donnees_email
    
    def extraire_email_expediteur(self, champ_from: str) -> str:
        """Extrait l'adresse email du champ From"""
        match = re.search(r'<(.+?)>', champ_from)
        if match:
            return match.group(1)
        return champ_from.strip()
    
    def est_reponse_automatique(self, contenu_email: Dict) -> bool:
        """Vérifie si c'est une réponse automatique"""
        sujet = contenu_email['sujet'].lower()
        corps = contenu_email['corps'].lower()
        
        indicateurs_auto = [
            'réponse automatique', 'réponse auto', 'hors du bureau',
            'vacances', 'absent', 'réponse automatisée',
            'notification de statut de livraison', 'courriel non livré',
            'auto-reply', 'automatic reply', 'out of office', 'noreply',
            'ne pas répondre', 'do not reply'
        ]
        
        return any(indicateur in sujet or indicateur in corps for indicateur in indicateurs_auto)
    
    def generer_id_conversation(self, expediteur_email: str) -> str:
        """Génère un ID unique de conversation"""
        import hashlib
        return hashlib.md5(expediteur_email.encode()).hexdigest()[:16]
    
    def envoyer_reponse(self, destinataire_email: str, sujet: str, texte_reponse: str, message_id_original: str = None):
        """Envoie la réponse email générée par l'IA"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = destinataire_email
            msg['Subject'] = f"Re: {sujet}" if not sujet.startswith('Re:') else sujet
            
            # Référence au message original
            if message_id_original:
                msg['In-Reply-To'] = message_id_original
                msg['References'] = message_id_original
            
            msg.attach(MIMEText(texte_reponse, 'plain', 'utf-8'))
            
            with self.connecter_smtp() as server:
                server.send_message(msg)
            
            logger.info(f"Réponse envoyée à {destinataire_email}")
            
        except Exception as e:
            logger.error(f"Échec envoi réponse à {destinataire_email}: {e}")
    
    def traiter_email_client(self, contenu_email: Dict) -> Optional[InteractionEmail]:
        """Traite l'email client avec LangGraph"""
        expediteur_email = self.extraire_email_expediteur(contenu_email['from'])
        conversation_id = self.generer_id_conversation(expediteur_email)
        
        # Créer l'état initial pour LangGraph
        etat_initial: EtatAgent = {
            'email_contenu': contenu_email['corps'],
            'email_expediteur': expediteur_email,
            'email_sujet': contenu_email['sujet'],
            'historique_conversation': [],
            'type_reponse': None,
            'reponse_ia': None,
            'statut_interaction': None,
            'question_suivi': None,
            'message_id': contenu_email['message_id'],
            'branche_assurance': None
        }
        
        try:
            # Exécuter le graphique LangGraph
            etat_final = self.graphique.invoke(etat_initial)
            
            # Créer l'interaction
            interaction = InteractionEmail(
                email_id=contenu_email['message_id'],
                expediteur_email=expediteur_email,
                sujet=contenu_email['sujet'],
                corps=contenu_email['corps'],
                timestamp=datetime.now(),
                type_reponse=etat_final['type_reponse'],
                reponse_ia=etat_final['reponse_ia'],
                conversation_id=conversation_id,
                statut=etat_final['statut_interaction'],
                branche_assurance=etat_final['branche_assurance']
            )
            
            return interaction
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement avec LangGraph: {e}")
            return None
    
    def surveiller_emails(self):
        """Boucle principale de surveillance des emails"""
        logger.info("🚀 Démarrage de l'agent email BH Assurance avec LangGraph et PostgreSQL...")
        emails_traites = set()
        
        while True:
            try:
                with self.connecter_imap() as mail:
                    mail.select('INBOX')
                    
                    # Rechercher emails non lus
                    status, messages = mail.search(None, 'UNSEEN')
                    
                    if status == 'OK' and messages[0]:
                        email_ids = messages[0].split()
                        logger.info(f"📧 {len(email_ids)} nouveaux emails trouvés")
                        
                        for email_id in email_ids:
                            try:
                                # Récupérer l'email
                                status, msg_data = mail.fetch(email_id, '(RFC822)')
                                if status != 'OK':
                                    continue
                                
                                # Parser l'email
                                raw_email = msg_data[0][1]
                                msg = email.message_from_bytes(raw_email)
                                
                                # Extraire le contenu
                                contenu_email = self.extraire_contenu_email(msg)
                                message_id = contenu_email['message_id']
                                
                                # Éviter les doublons
                                if message_id in emails_traites:
                                    continue
                                
                                # Ignorer les réponses automatiques
                                if self.est_reponse_automatique(contenu_email):
                                    logger.info(f"🔄 Réponse automatique ignorée de {contenu_email['from']}")
                                    continue
                                
                                # Traiter avec LangGraph
                                interaction = self.traiter_email_client(contenu_email)
                                
                                if interaction:
                                    # Sauvegarder en base PostgreSQL
                                    self.db_manager.sauvegarder_interaction(interaction)
                                    
                                    # Envoyer la réponse IA
                                    self.envoyer_reponse(
                                        interaction.expediteur_email,
                                        interaction.sujet,
                                        interaction.reponse_ia,
                                        message_id
                                    )
                                    
                                    # Marquer comme traité
                                    emails_traites.add(message_id)
                                    
                                    logger.info(
                                        f"✅ Email traité: {interaction.expediteur_email} | "
                                        f"Type: {interaction.type_reponse.value} | "
                                        f"Statut: {interaction.statut.value} | "
                                        f"Branche: {interaction.branche_assurance or 'N/A'}"
                                    )
                                
                            except Exception as e:
                                logger.error(f"❌ Erreur traitement email {email_id}: {e}")
                                continue
                    
                    else:
                        logger.info("📭 Aucun nouvel email")
                
                # Attendre avant la prochaine vérification
                time.sleep(self.config.get('intervalle_verification', 30))
                
            except KeyboardInterrupt:
                logger.info("🛑 Arrêt de l'agent par l'utilisateur")
                break
            except Exception as e:
                logger.error(f"❌ Erreur dans la boucle de surveillance: {e}")
                time.sleep(30)
    
    def est_email_francais(self, contenu: str) -> bool:
        """Vérifie si l'email est en français"""
        mots_francais = [
            'bonjour', 'salut', 'merci', 'oui', 'non', 'assurance', 'devis', 
            'prix', 'coût', 'intéressé', 'interessé', 'information', 'détail',
            'voudrais', 'aimerais', 'pouvez', 'vous', 'nous', 'moi', 'je', 'il',
            'elle', 'avoir', 'être', 'faire', 'aller', 'venir', 'voir', 'savoir',
            'francais', 'français', 'tunisie', 'tunisia', 'dinar', 'dt'
        ]
        
        contenu_lower = contenu.lower()
        mots_trouves = sum(1 for mot in mots_francais if mot in contenu_lower)
        
        return mots_trouves >= 2
    
    def obtenir_statistiques(self) -> Dict:
        """Obtient les statistiques de l'agent depuis PostgreSQL"""
        conn = self.db_manager.obtenir_connexion()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Statistiques générales
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_interactions,
                    COUNT(DISTINCT expediteur_email) as clients_uniques,
                    COUNT(CASE WHEN statut = 'interesse' THEN 1 END) as interesses,
                    COUNT(CASE WHEN statut = 'devis_demande' THEN 1 END) as devis_demandes,
                    COUNT(CASE WHEN statut = 'non_interesse' THEN 1 END) as non_interesses
                FROM interactions_email
                WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
            ''')
            
            stats = cursor.fetchone()
            
            # Statistiques par branche
            cursor.execute('''
                SELECT branche_assurance, COUNT(*) as count
                FROM interactions_email
                WHERE branche_assurance IS NOT NULL
                  AND timestamp >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY branche_assurance
                ORDER BY count DESC
            ''')
            
            stats_branches = cursor.fetchall()
            
            return {
                'total_interactions': stats['total_interactions'],
                'clients_uniques': stats['clients_uniques'],
                'interesses': stats['interesses'],
                'devis_demandes': stats['devis_demandes'],
                'non_interesses': stats['non_interesses'],
                'branches_populaires': [
                    {'branche': row['branche_assurance'], 'count': row['count']} 
                    for row in stats_branches
                ]
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération statistiques: {e}")
            return {}
        finally:
            cursor.close()
            conn.close()

class ConfigurationAgent:
    """Configuration de l'agent email BH Assurance avec PostgreSQL"""
    
    @staticmethod
    def creer_config() -> Dict:
        return {
            # Configuration email
            'email_address': 'chatbot.bh01@gmail.com',
            'password': 'dcal asuw qfad kecs',
            'imap_server': 'imap.gmail.com',
            'smtp_server': 'smtp.gmail.com',
            'imap_port': 993,
            'smtp_port': 587,
            'intervalle_verification': 30,
            
            # Configuration LLM
            'modele_llm': 'llama2',
            
            # Configuration PostgreSQL
            'db_host': 'localhost',
            'db_name': 'Bh',
            'db_user': 'postgres',
            'db_password': 'postgres',
            'db_port': 5432,
            
            # Informations contact
            'telephone_contact': '+216 XX XXX XXX',
            'email_contact': 'contact@bh-assurance.tn',
            'site_web': 'www.bh-assurance.tn'
        }

def installer_dependances():
    """Affiche les dépendances requises"""
    dependances = [
        "psycopg2-binary>=2.9.0",
        "langgraph>=0.1.0",
        "langchain-ollama>=0.1.0",
        "langchain-core>=0.1.0"
    ]
    
    print("📦 Dépendances requises:")
    for dep in dependances:
        print(f"  - {dep}")
    print("\nInstallez avec: pip install " + " ".join(dependances))

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
        logger.error(f"❌ Erreur connexion PostgreSQL: {e}")
        print(f"❌ Impossible de se connecter à PostgreSQL: {e}")
        print("Vérifiez que:")
        print("  - PostgreSQL est installé et démarré")
        print("  - La base 'Bh' existe")
        print("  - L'utilisateur 'postgres' a les bonnes permissions")
        return False

def main():
    """Fonction principale pour lancer l'agent"""
    print("🏢 Agent Email BH Assurance - PostgreSQL + LangGraph Edition")
    print("=" * 60)
    
    # Afficher les dépendances
    installer_dependances()
    print()
    
    config = ConfigurationAgent.creer_config()
    
    # Tester la connexion PostgreSQL
    if not tester_connexion_postgresql(config):
        return
    
    try:
        agent = AgentEmailBHAssurance(config)
        
        print("✅ Agent initialisé avec succès")
        print("🐘 Base de données PostgreSQL connectée")
        print("🤖 LangGraph configuré")
        print("📧 Surveillance des emails en cours...")
        print("\nCommandes disponibles:")
        print("  - Ctrl+C: Arrêter l'agent")
        print("  - Statistiques disponibles via agent.obtenir_statistiques()")
        print()
        
        agent.surveiller_emails()
        
    except KeyboardInterrupt:
        print("\n👋 Agent arrêté proprement")
    except Exception as e:
        print(f"❌ Erreur critique: {e}")
        logger.error(f"Erreur critique dans main(): {e}")

def afficher_statistiques():
    """Fonction utilitaire pour afficher les statistiques"""
    config = ConfigurationAgent.creer_config()
    
    if not tester_connexion_postgresql(config):
        return
    
    try:
        agent = AgentEmailBHAssurance(config)
        stats = agent.obtenir_statistiques()
        
        print("\n📊 Statistiques des 7 derniers jours:")
        print("=" * 40)
        print(f"Total interactions: {stats.get('total_interactions', 0)}")
        print(f"Clients uniques: {stats.get('clients_uniques', 0)}")
        print(f"Intéressés: {stats.get('interesses', 0)}")
        print(f"Demandes de devis: {stats.get('devis_demandes', 0)}")
        print(f"Non intéressés: {stats.get('non_interesses', 0)}")
        
        if stats.get('branches_populaires'):
            print("\nBranches les plus demandées:")
            for branche in stats['branches_populaires']:
                print(f"  - {branche['branche']}: {branche['count']} interactions")
    
    except Exception as e:
        print(f"❌ Erreur récupération statistiques: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        afficher_statistiques()
    else:
        main()