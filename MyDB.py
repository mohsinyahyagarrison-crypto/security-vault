import streamlit as st
import sqlite3
from cryptography.fernet import Fernet
import pandas as pd
import base64

st.set_page_config(page_title="MY DB", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background-color: black;
    }
    h1, h2, h3, p, label, span {
        color: white !important;
    }
    [data-testid="stSidebar"] {
        background-color: #111111;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)


def derive_key(passphrase):
    return base64.urlsafe_b64encode(passphrase.ljust(32)[:32].encode())


conn = sqlite3.connect('vault.db', check_same_thread=False)
c = conn.cursor()
c.execute(
    'CREATE TABLE IF NOT EXISTS secrets (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, encrypted_content BLOB)')
conn.commit()

st.title("🔐 ADMIN CYBER-VAULT")

master_key_input = st.sidebar.text_input("Enter Admin Key", type="password")

if master_key_input == "1234":
    cipher = Fernet(derive_key(master_key_input))
    menu = ["View Vault", "Add Secret", "Delete Secret", "Backup"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Add Secret":
        st.subheader("Store New Asset")
        asset_label = st.text_input("Asset Name")
        asset_value = st.text_input("Secret Content", type="password")
        if st.button("Encrypt & Save"):
            if asset_label and asset_value:
                encrypted_text = cipher.encrypt(asset_value.encode())
                c.execute('INSERT INTO secrets (label, encrypted_content) VALUES (?,?)', (asset_label, encrypted_text))
                conn.commit()
                st.success("Encrypted data stored.")

    elif choice == "View Vault":
        st.subheader("Your Encrypted Assets")
        data = pd.read_sql_query("SELECT * FROM secrets", conn)
        if not data.empty:
            decrypted_list = []
            for index, row in data.iterrows():
                try:
                    decrypted_val = cipher.decrypt(row['encrypted_content']).decode()
                    decrypted_list.append({"ID": row['id'], "Asset": row['label'], "Content": decrypted_val})
                except:
                    decrypted_list.append({"ID": row['id'], "Asset": row['label'], "Content": "DECRYPTION ERROR"})
            st.table(pd.DataFrame(decrypted_list))
        else:
            st.info("Vault is empty.")

    elif choice == "Delete Secret":
        st.subheader("Remove Asset")
        data = pd.read_sql_query("SELECT id, label FROM secrets", conn)
        if not data.empty:
            st.table(data)
            delete_id = st.number_input("Enter ID to Delete", min_value=1, step=1)

            if st.button("Delete & Re-index"):
                c.execute('DELETE FROM secrets WHERE id=?', (delete_id,))

                # Re-indexing logic
                remaining = pd.read_sql_query("SELECT label, encrypted_content FROM secrets", conn)
                c.execute('DELETE FROM secrets')
                c.execute('DELETE FROM sqlite_sequence WHERE name="secrets"')
                for _, row in remaining.iterrows():
                    c.execute('INSERT INTO secrets (label, encrypted_content) VALUES (?,?)',
                              (row['label'], row['encrypted_content']))

                conn.commit()
                st.warning(f"Record {delete_id} removed and database re-indexed.")
                st.rerun()
        else:
            st.info("Nothing to delete.")

    elif choice == "Backup":
        st.subheader("Database Export")
        with open("vault.db", "rb") as f:
            st.download_button(
                label="Download Encrypted vault.db",
                data=f,
                file_name="vault_backup.db",
                mime="application/octet-stream"
            )
        st.info("Download this file and try opening it in Notepad to see the encrypted data.")

elif master_key_input != "" and master_key_input != "1234":
    st.sidebar.error("Incorrect Admin Key")
else:
    st.warning("Please enter the Admin Key in the sidebar to access the vault.")