
import streamlit as st
import pandas as pd
import gspread
import os
import json
from google.oauth2 import service_account
from datetime import datetime

### ESTO ESTÁ LISTO!!! ### 

# Configuración de la página
st.set_page_config(page_title="Encuesta CCK", layout="wide")

# Función para obtener credenciales
def get_gcp_credentials():
    """
    Intenta obtener credenciales de múltiples fuentes, en orden de preferencia:
    1. Secretos de Streamlit
    2. Variables de entorno 
    3. Archivo local de credenciales
    """
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/spreadsheets',
             'https://www.googleapis.com/auth/drive']
    
    # Opción 1: Streamlit secrets
    if hasattr(st, 'secrets') and 'google_credentials' in st.secrets:
        try:
            creds_dict = st.secrets["google_credentials"]
            creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')  # Corrección de formato
            return service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
        except Exception as e:
            st.error(f"Error cargando credenciales desde Streamlit secrets: {e}")
            st.stop()

    # Opción 2: Variables de entorno
    elif "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
        return service_account.Credentials.from_service_account_file(os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=scope)

    # Opción 3: Archivo local (si existe)
    elif os.path.exists("credentials.json"):
        return service_account.Credentials.from_service_account_file("credentials.json", scopes=scope)

    else:
        st.error("No se encontraron credenciales válidas")
        st.stop()

# Obtener credenciales
creds = get_gcp_credentials()

# Conectar con Google Sheets
gc = gspread.authorize(creds)

try:
    spreadsheet = gc.open("Nombre de tu Hoja")  # Reemplaza con el nombre real
    worksheet = spreadsheet.sheet1
    data = worksheet.get_all_records()

    st.write("✅ **Conexión exitosa a Google Sheets**", data)

except Exception as e:
    st.error(f"❌ **Error al conectar con Google Sheets:** {e}")
