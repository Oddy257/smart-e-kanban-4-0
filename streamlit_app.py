import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Smart e-Kanban 4.0",
    page_icon="🏭",
    layout="wide"
)

st.title("🏭 Smart e-Kanban 4.0")
st.caption("Réapprovisionnement intelligent d'une ligne de production")

# ============================================================
# BASE SQLITE
# ============================================================

conn = sqlite3.connect("smart_ekanban.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS composants (
    code TEXT PRIMARY KEY,
    nom TEXT,
    stock INTEGER,
    consommation_jour REAL,
    delai_jours INTEGER,
    stock_securite INTEGER,
    point_commande REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS mouvements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    code_composant TEXT,
    type_mouvement TEXT,
    quantite INTEGER,
    stock_avant INTEGER,
    stock_apres INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS reapprovisionnements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    code_composant TEXT,
    quantite INTEGER,
    statut TEXT
)
""")

conn.commit()

# ============================================================
# DONNEES INITIALES
# ============================================================

cursor.execute("SELECT COUNT(*) FROM composants")
nb = cursor.fetchone()[0]

if nb == 0:
    donnees = [
        ("C01", "Roulement", 150, 20, 3, 20),
        ("C02", "Rotor", 35, 8, 4, 10),
        ("C03", "Stator", 90, 10, 3, 15),
        ("C04", "Carter", 60, 12, 2, 12),
        ("C05", "Capteur", 25, 5, 4, 8),
        ("C06", "Connecteur", 100, 15, 2, 20),
        ("C07", "Visserie", 400, 80, 2, 100),
        ("C08", "Câble", 70, 10, 3, 15)
    ]

    for code, nom, stock, conso, delai, securite in donnees:
        pc = conso * delai + securite

        cursor.execute("""
        INSERT INTO composants
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            code,
            nom,
            stock,
            conso,
            delai,
            securite,
            pc
        ))

    conn.commit()

# ============================================================
# FONCTIONS
# ============================================================

def enregistrer_mouvement(code, type_mouvement, quantite, avant, apres):
    cursor.execute("""
    INSERT INTO mouvements
    (date, code_composant, type_mouvement, quantite, stock_avant, stock_apres)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        code,
        type_mouvement,
        quantite,
        avant,
        apres
    ))
    conn.commit()


def demande_active_existe(code):
    cursor.execute("""
    SELECT COUNT(*)
    FROM reapprovisionnements
    WHERE code_composant = ?
    AND statut = 'A TRAITER'
    """, (code,))

    return cursor.fetchone()[0] > 0


def verifier_reapprovisionnement(code):
    cursor.execute("""
    SELECT nom, stock, stock_securite, point_commande
    FROM composants
    WHERE code = ?
    """, (code,))

    resultat = cursor.fetchone()

    if resultat is None:
        return

    nom, stock, securite, point_commande = resultat

    if stock <= point_commande and not demande_active_existe(code):
        quantite = int(point_commande - stock + securite)

        cursor.execute("""
        INSERT INTO reapprovisionnements
        (date, code_composant, quantite, statut)
        VALUES (?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            code,
            quantite,
            "A TRAITER"
        ))

        conn.commit()


def consommer(code, quantite):
    cursor.execute(
        "SELECT stock FROM composants WHERE code = ?",
        (code,)
    )

    resultat = cursor.fetchone()

    if resultat is None:
        return False, "Composant introuvable."

    stock_avant = resultat[0]

    if quantite <= 0:
        return False, "Quantité invalide."

    if quantite > stock_avant:
        return False, "Stock insuffisant."

    stock_apres = stock_avant - quantite

    cursor.execute("""
    UPDATE composants
    SET stock = ?
    WHERE code = ?
    """, (stock_apres, code))

    conn.commit()

    enregistrer_mouvement(
        code,
        "SORTIE",
        quantite,
        stock_avant,
        stock_apres
    )

    verifier_reapprovisionnement(code)

    return True, f"Stock mis à jour : {stock_apres}"


def receptionner(code, quantite):
    cursor.execute(
        "SELECT stock FROM composants WHERE code = ?",
        (code,)
    )

    resultat = cursor.fetchone()

    if resultat is None:
        return False, "Composant introuvable."

    if quantite <= 0:
        return False, "Quantité invalide."

    stock_avant = resultat[0]
    stock_apres = stock_avant + quantite

    cursor.execute("""
    UPDATE composants
    SET stock = ?
    WHERE code = ?
    """, (stock_apres, code))

    cursor.execute("""
    UPDATE reapprovisionnements
    SET statut = 'RECEPTIONNEE'
    WHERE code_composant = ?
    AND statut = 'A TRAITER'
    """, (code,))

    conn.commit()

    enregistrer_mouvement(
        code,
        "ENTREE",
        quantite,
        stock_avant,
        stock_apres
    )

    return True, f"Réception enregistrée. Nouveau stock : {stock_apres}"
# ============================================================
# REINITIALISATION DE LA DEMONSTRATION
# ============================================================

def reinitialiser_demo():

    donnees_initiales = [
        ("C01", "Roulement", 150, 20, 3, 20),
        ("C02", "Rotor", 35, 8, 4, 10),
        ("C03", "Stator", 90, 10, 3, 15),
        ("C04", "Carter", 60, 12, 2, 12),
        ("C05", "Capteur", 25, 5, 4, 8),
        ("C06", "Connecteur", 100, 15, 2, 20),
        ("C07", "Visserie", 400, 80, 2, 100),
        ("C08", "Câble", 70, 10, 3, 15)
    ]

    cursor.execute("DELETE FROM mouvements")
    cursor.execute("DELETE FROM reapprovisionnements")
    cursor.execute("DELETE FROM composants")

    for code, nom, stock, conso, delai, securite in donnees_initiales:

        point_commande = conso * delai + securite

        cursor.execute("""
        INSERT INTO composants
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            code,
            nom,
            stock,
            conso,
            delai,
            securite,
            point_commande
        ))

    conn.commit()
# ============================================================
# MENU
# ============================================================

menu = st.sidebar.radio(
    "Navigation",
    [
        "📊 Dashboard",
        "📦 Mouvement de stock",
        "🔔 Réapprovisionnement",
        "📜 Historique"
    ]
)
st.sidebar.divider()

if st.sidebar.button("🔄 Réinitialiser la démonstration"):
    reinitialiser_demo()
    st.sidebar.success("Données réinitialisées.")
    st.rerun()
# ============================================================
# DASHBOARD
# ============================================================

if menu == "📊 Dashboard":

    stocks = pd.read_sql_query("""
    SELECT
        code AS Code,
        nom AS Composant,
        stock AS Stock,
        point_commande AS Point_commande,
        CASE
            WHEN stock <= stock_securite THEN 'URGENT'
            WHEN stock <= point_commande THEN 'A REAPPROVISIONNER'
            ELSE 'NORMAL'
        END AS Etat
    FROM composants
    """, conn)

    c1, c2, c3 = st.columns(3)

    c1.metric("Références", len(stocks))
    c2.metric(
        "Stocks à surveiller",
        (stocks["Etat"] != "NORMAL").sum()
    )
    c3.metric(
        "Stock total",
        int(stocks["Stock"].sum())
    )

    st.subheader("État des stocks")
    st.dataframe(stocks, use_container_width=True)

    st.subheader("Niveau de stock")
    st.bar_chart(
        stocks.set_index("Composant")["Stock"]
    )

# ============================================================
# MOUVEMENTS
# ============================================================

elif menu == "📦 Mouvement de stock":

    composants = pd.read_sql_query(
        "SELECT code, nom FROM composants",
        conn
    )

    options = {
        f"{row['code']} - {row['nom']}": row["code"]
        for _, row in composants.iterrows()
    }

    choix = st.selectbox(
        "Choisir un composant",
        list(options.keys())
    )

    code = options[choix]

    quantite = st.number_input(
        "Quantité",
        min_value=1,
        value=1
    )

    col1, col2 = st.columns(2)

    if col1.button("📤 Enregistrer une consommation"):
        ok, message = consommer(code, int(quantite))

        if ok:
            st.success(message)
        else:
            st.error(message)

    if col2.button("📥 Enregistrer une réception"):
        ok, message = receptionner(code, int(quantite))

        if ok:
            st.success(message)
        else:
            st.error(message)

# ============================================================
# REAPPROVISIONNEMENTS
# ============================================================

elif menu == "🔔 Réapprovisionnement":

    demandes = pd.read_sql_query("""
    SELECT *
    FROM reapprovisionnements
    ORDER BY id DESC
    """, conn)

    st.subheader("Demandes de réapprovisionnement")

    if len(demandes) == 0:
        st.info("Aucune demande de réapprovisionnement.")
    else:
        st.dataframe(
            demandes,
            use_container_width=True
        )

# ============================================================
# HISTORIQUE
# ============================================================

elif menu == "📜 Historique":

    historique = pd.read_sql_query("""
    SELECT *
    FROM mouvements
    ORDER BY id DESC
    """, conn)

    st.subheader("Historique des mouvements")

    if len(historique) == 0:
        st.info("Aucun mouvement enregistré.")
    else:
        st.dataframe(
            historique,
            use_container_width=True
        )
