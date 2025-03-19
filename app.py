import streamlit as st
import pandas as pd
import gspread
import os
import json
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account
from datetime import datetime
import uuid

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
            return service_account.Credentials.from_service_account_info(
                st.secrets["google_credentials"], scopes=scope)
        except Exception as e:
            pass
    
    # Opción 2: Variable de entorno con JSON
    if 'GOOGLE_APPLICATION_CREDENTIALS_JSON' in os.environ:
        try:
            credentials_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            credentials_dict = json.loads(credentials_json)
            return service_account.Credentials.from_service_account_info(
                credentials_dict, scopes=scope)
        except Exception as e:
            pass
    
    # Opción 3: Variable de entorno con ruta al archivo
    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        try:
            creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            return Credentials.from_service_account_file(creds_path, scopes=scope)
        except Exception as e:
            pass
    
    # Opción 4: Archivo local (menos seguro para producción)
    try:
        return Credentials.from_service_account_file("credentials.json", scopes=scope)
    except Exception as e:
        st.error("No se pudieron cargar las credenciales. Asegúrate de tener las credenciales correctamente configuradas.")
        return None

# Función para conectar con Google Sheets
def connect_to_gsheets(spreadsheet_name):
    credentials = get_gcp_credentials()
    
    if credentials is None:
        return None
    
    gc = gspread.authorize(credentials)
    
    # Abrir una hoja específica por ID
    try:
        spreadsheet = gc.open_by_key("10vcVWojXWDOZPlXnwIqPtinDtSSwq6evz4mDwTdkz-o")
        
        # Asegurarse de que existe la hoja de trabajo
        try:
            worksheet = spreadsheet.worksheet("Respuestas")
            
            # Añadir encabezados siempre (aunque la hoja ya exista)
            headers = [
                "ID_Respuesta", "Nombre_Cliente", "Fecha_Respuesta", 
                "Nivel_Cargo", "Fecha_Inicio", "Departamento",
                "Evento", "Probabilidad", "Ocurrencia", "Detección", 
                "Estructura", "Impacto", "Responsabilidad", "Autoeficacia"
            ]
            worksheet.update('A1', [headers])
            
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="Respuestas", rows=1000, cols=50)
            
            # Añadir encabezados a la hoja (columnas específicas)
            headers = [
                "ID_Respuesta", "Nombre_Cliente", "Fecha_Respuesta", 
                "Nivel_Cargo", "Fecha_Inicio", "Departamento",
                "Evento", "Probabilidad", "Ocurrencia", "Detección", 
                "Estructura", "Impacto", "Responsabilidad", "Autoeficacia"
            ]
            worksheet.update('A1', [headers])
        
        return worksheet
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {str(e)}")
        return None

# Función para guardar respuestas en Google Sheets
def save_response(worksheet, response_data):
    if worksheet is None:
        return False
        
    try:
        # Obtener todas las filas actuales
        all_values = worksheet.get_all_values()
        
        # La nueva fila será después de la última fila existente
        row_to_update = len(all_values) + 1
        
        # Preparar valores
        values = list(response_data.values())
        
        # Actualizar la celda directamente usando rangos
        cell_range = f'A{row_to_update}'
        
        # Actualizar como una lista de listas
        worksheet.update(cell_range, [values])
        
        return True
    except Exception as e:
        st.error(f"Error al guardar en Google Sheets: {str(e)}")
        return False
        
# Lista de posibles eventos críticos
eventos_criticos = [
    "Fuga de información confidencial",
    "Caída prolongada de los sistemas informáticos",
    "Incumplimiento regulatorio",
    "Fraude interno",
    "Crisis reputacional en redes sociales",
    "Falla en la cadena de suministro",
    "Desastre natural que afecta las instalaciones",
    "Ciberataque",
    "Conflicto laboral grave",
    "Error crítico en producto o servicio"
]

# Inicializar el estado de la sesión
if 'page' not in st.session_state:
    st.session_state.page = "inicio"
if 'respuestas' not in st.session_state:
    st.session_state.respuestas = {}
if 'evento_actual' not in st.session_state:
    st.session_state.evento_actual = None
if 'n_eventos_respondidos' not in st.session_state:
    st.session_state.n_eventos_respondidos = 0
if 'total_eventos' not in st.session_state:
    st.session_state.total_eventos = 3  # Número de eventos a evaluar por participante
if 'error_credenciales' not in st.session_state:
    st.session_state.error_credenciales = False
if 'nombre_cliente' not in st.session_state:
    st.session_state.nombre_cliente = ""
if 'response_id' not in st.session_state:
    st.session_state.response_id = str(uuid.uuid4())[:8]  # ID único para cada sesión de respuesta

# Función para cambiar de página
def cambiar_pagina(nueva_pagina, evento=None):
    st.session_state.page = nueva_pagina
    if evento is not None:
        st.session_state.evento_actual = evento

# Verificar credenciales al inicio
if 'credenciales_verificadas' not in st.session_state:
    try:
        test_worksheet = connect_to_gsheets("Test_Conexion_CCK")
        if test_worksheet is not None:
            st.session_state.credenciales_verificadas = True
        else:
            st.session_state.credenciales_verificadas = False
            st.session_state.error_credenciales = True
    except Exception as e:
        st.session_state.credenciales_verificadas = False
        st.session_state.error_credenciales = True
        st.session_state.error_mensaje = str(e)

# Página de inicio y consentimiento
if st.session_state.page == "inicio":
    st.title("CCK")
    st.markdown("### Introducción y Consentimiento")
    st.markdown("""
    El propósito de este cuestionario es evaluar su percepción sobre la probabilidad, el impacto 
    y la preparación de su organización frente a una serie de posibles eventos críticos. Sus 
    respuestas nos ayudarán a identificar áreas clave para mejorar los procesos internos, la 
    detección temprana y la preparación organizacional.
    
    La participación es completamente anónima y voluntaria, y sus respuestas serán utilizadas 
    únicamente con fines de evaluación interna. No serán compartidas con terceros bajo ninguna 
    circunstancia.
    
    Por favor, responda cada pregunta basándose en su experiencia y percepción actual sobre estos eventos. 
    No existen respuestas correctas o incorrectas.
    
    El tiempo estimado para completar el cuestionario es de 5 a 10 minutos.
    """)
    
    # Añadir campo para nombre del cliente
    st.session_state.nombre_cliente = st.text_input("Nombre del cliente/organización:", 
                                                   value=st.session_state.nombre_cliente)
    
    consentimiento = st.radio("Por favor, indique su consentimiento a continuación:", 
                             ["Estoy de acuerdo, deseo continuar", "No estoy de acuerdo, deseo salir."])
    
    if st.button("Continuar"):
        if consentimiento == "Estoy de acuerdo, deseo continuar":
            # Generar un nuevo ID de respuesta al comenzar una nueva encuesta
            st.session_state.response_id = str(uuid.uuid4())[:8]
            cambiar_pagina("instrucciones")
        else:
            st.error("Ha decidido no participar en la encuesta. Gracias por su tiempo.")
            st.stop()
    
    # Mostrar advertencia de credenciales si es necesario
    if st.session_state.error_credenciales:
        st.warning("⚠️ Advertencia: Hay un problema con las credenciales de Google Sheets. Las respuestas se guardarán localmente, pero no se enviarán a Google Sheets.")

# Página de instrucciones
elif st.session_state.page == "instrucciones":
    st.title("CCK")
    st.markdown("### Cómo llenar el cuestionario")
    st.markdown("""
    Se le presentará una serie de posibles eventos o situaciones sobre los cuales queremos conocer su opinión.
    
    Para cada uno de ellos, le pedimos que:
    
    1. Lea cuidadosamente cada pregunta
    2. Seleccione la opción que mejor refleje su percepción o experiencia con respecto a la situación planteada
    3. Use las escalas provistas para evaluar su respuesta. Cada escala está diseñada para capturar diferentes niveles de probabilidad, impacto o preparación
    
    Si tiene dudas sobre alguna pregunta, elija la respuesta que mejor se acerque a su opinión actual.
    """)
    
    if st.button("Comenzar encuesta"):
        # Seleccionar aleatoriamente eventos para evaluar
        import random
        eventos_seleccionados = random.sample(eventos_criticos, st.session_state.total_eventos)
        st.session_state.eventos_seleccionados = eventos_seleccionados
        cambiar_pagina("evaluacion", eventos_seleccionados[0])

# Página de evaluación de eventos
elif st.session_state.page == "evaluacion":
    evento = st.session_state.evento_actual
    st.title("CCK")
    st.subheader(f"Evaluación del evento: {evento}")
    
    # Container para realizar un seguimiento del progreso
    progreso = st.container()
    progreso.progress((st.session_state.n_eventos_respondidos) / st.session_state.total_eventos)
    progreso.write(f"Evento {st.session_state.n_eventos_respondidos + 1} de {st.session_state.total_eventos}")
    
    # Inicializar respuestas para este evento si no existen
    if evento not in st.session_state.respuestas:
        st.session_state.respuestas[evento] = {}
    
    # Preguntas sobre el evento
    with st.form(key=f"form_{evento}"):
        # Probabilidad
        st.markdown("### Probabilidad")
        probabilidad = st.radio(
            f"¿Qué tan probable considera que es la ocurrencia de un evento como {evento}?",
            ["Extremadamente improbable", "Algo improbable", "Ni probable ni improbable", 
             "Algo probable", "Extremadamente probable"],
            key=f"probabilidad_{evento}"
        )
        
        # Ocurrencia
        st.markdown("### Ocurrencia pasada")
        ocurrencia = st.radio(
            f"¿Con qué frecuencia se han presentado situaciones de {evento} en el pasado?",
            ["Nunca", "1 vez", "Entre 2 y 3 veces", "Más de 4 veces"],
            key=f"ocurrencia_{evento}"
        )
        
        # Detección
        st.markdown("### Detección")
        deteccion = st.radio(
            f"¿Qué tan fácil considera que es anticipar una situación de {evento} antes de que ocurra?",
            ["Extremadamente difícil", "Algo difícil", "Ni fácil ni difícil", 
             "Algo fácil", "Extremadamente fácil"],
            key=f"deteccion_{evento}"
        )
        
        # Estructura
        st.markdown("### Estructura Organizacional")
        estructura = st.radio(
            f'¿Qué tan de acuerdo está con la siguiente afirmación? "La estructura y los procesos internos de la organización favorecen la probabilidad de que una situación como {evento} ocurra."',
            ["Totalmente en desacuerdo", "Algo en desacuerdo", "Ni de acuerdo ni en desacuerdo", 
             "Algo de acuerdo", "Totalmente de acuerdo"],
            key=f"estructura_{evento}"
        )
        
        # Impacto
        st.markdown("### Impacto")
        impacto = st.radio(
            f"Si {evento} ocurriera, ¿qué tan negativo considera que sería para la organización?",
            ["Nada negativo", "Poco negativo", "Moderadamente negativo", 
             "Muy negativo", "Extremadamente negativo"],
            key=f"impacto_{evento}"
        )
        
        # Responsabilidad
        st.markdown("### Responsabilidad")
        responsabilidad = st.radio(
            f"En caso de que ocurriera {evento}, ¿qué nivel de responsabilidad tendría la organización?",
            ["Ninguna", "Poca", "Moderada", "Mucha", "Muchísima"],
            key=f"responsabilidad_{evento}"
        )
        
        # Autoeficacia
        st.markdown("### Autoeficacia")
        autoeficacia = st.radio(
            f"¿Qué tan preparado considera que está su organización para responder ante {evento} en caso de que ocurriera?",
            ["Nada preparado", "Poco preparada", "Moderadamente preparada", 
             "Muy preparada", "Totalmente preparado"],
            key=f"autoeficacia_{evento}"
        )
        
        # Botón para enviar respuestas
        submitted = st.form_submit_button("Siguiente")
        
        if submitted:
            # Guardar respuestas
            st.session_state.respuestas[evento] = {
                "Evento": evento,
                "Probabilidad": probabilidad,
                "Ocurrencia": ocurrencia,
                "Detección": deteccion,
                "Estructura": estructura,
                "Impacto": impacto,
                "Responsabilidad": responsabilidad,
                "Autoeficacia": autoeficacia
            }
            
            # Incrementar contador de eventos respondidos
            st.session_state.n_eventos_respondidos += 1
            
            # Determinar si pasar al siguiente evento o a los datos demográficos
            if st.session_state.n_eventos_respondidos < st.session_state.total_eventos:
                siguiente_evento = st.session_state.eventos_seleccionados[st.session_state.n_eventos_respondidos]
                cambiar_pagina("evaluacion", siguiente_evento)
            else:
                cambiar_pagina("demograficos")
            
            st.rerun()

# Página de datos demográficos
elif st.session_state.page == "demograficos":
    st.title("CCK")
    st.subheader("Datos demográficos")
    
    st.markdown("""
    Por último... Antes de finalizar quisiéramos reunir algunos datos sobre su cargo y 
    experiencia en la organización. La información suministrada es estrictamente confidencial y no 
    será compartida con otros miembros de la organización. Su uso se limitará estrictamente para 
    el análisis de vulnerabilidades.
    """)
    
    with st.form(key="demograficos_form"):
        # Nivel de cargo
        nivel = st.selectbox(
            "¿Cuál es su nivel de cargo actual dentro de la organización?",
            ["C-Level (Ejecutivo: CEO, CFO, COO, etc.)", "Director", "Gerente", 
             "Coordinador/Supervisor", "Analista/Especialista", "Asistente/Operativo"]
        )
        
        # Fecha de inicio
        antiguedad = st.date_input(
            "¿En qué fecha comenzó a trabajar en la organización?",
            format="DD/MM/YYYY"
        )
        
        # Departamento
        departamento = st.selectbox(
            "¿A qué área o departamento pertenece dentro de la organización?",
            ["Dirección General", "Recursos Humanos", "Finanzas", "Operaciones", 
             "Tecnología/IT", "Marketing y Ventas", "Logística y Cadena de Suministro", 
             "Legal y Cumplimiento", "Investigación y Desarrollo"]
        )
        
        # Botón para enviar datos demográficos
        submit_demo = st.form_submit_button("Finalizar encuesta")
        
        if submit_demo:
            # Guardar datos demográficos
            st.session_state.demograficos = {
                "Nivel_Cargo": nivel,
                "Fecha_Inicio": antiguedad.strftime("%d/%m/%Y"),
                "Departamento": departamento
            }
            
            cambiar_pagina("guardar")
            st.rerun()

# Página para guardar los datos
elif st.session_state.page == "guardar":
    st.title("CCK")
    st.subheader("Guardando sus respuestas")
    
    # Fecha y hora actual
    fecha_hora_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Obtener el worksheet para guardar datos
    worksheet = None
    if st.session_state.credenciales_verificadas:
        try:
            worksheet = connect_to_gsheets("Respuestas Encuesta CCK")
        except Exception as e:
            st.error(f"Error al conectar con Google Sheets: {str(e)}")
            st.session_state.error_credenciales = True
    
    # Crear un diccionario con todas las respuestas (una fila por evento)
    guardar_exitoso = True
    progress_bar = st.progress(0)
    
    for i, (evento, respuestas) in enumerate(st.session_state.respuestas.items()):
        # Preparar datos para este evento específico
        datos_evento = {
            "ID_Respuesta": st.session_state.response_id,
            "Nombre_Cliente": st.session_state.nombre_cliente,
            "Fecha_Respuesta": fecha_hora_actual,
            "Nivel_Cargo": st.session_state.demograficos["Nivel_Cargo"],
            "Fecha_Inicio": st.session_state.demograficos["Fecha_Inicio"],
            "Departamento": st.session_state.demograficos["Departamento"],
            "Evento": evento,
            "Probabilidad": respuestas["Probabilidad"],
            "Ocurrencia": respuestas["Ocurrencia"],
            "Detección": respuestas["Detección"],
            "Estructura": respuestas["Estructura"],
            "Impacto": respuestas["Impacto"],
            "Responsabilidad": respuestas["Responsabilidad"],
            "Autoeficacia": respuestas["Autoeficacia"]
        }
        
        # Guardar datos en Google Sheets para este evento
        if worksheet and not st.session_state.error_credenciales:
            try:
                if not save_response(worksheet, datos_evento):
                    st.session_state.error_credenciales = True
                    guardar_exitoso = False
                    break
            except Exception as e:
                st.error(f"Error al guardar respuesta para evento {evento}: {str(e)}")
                st.session_state.error_credenciales = True
                guardar_exitoso = False
                break
        
        # Actualizar barra de progreso
        progress_bar.progress((i + 1) / len(st.session_state.respuestas))
    
    # Mensajes de éxito o error
    if not st.session_state.error_credenciales and guardar_exitoso:
        st.success("¡Gracias por completar la encuesta! Sus respuestas han sido guardadas correctamente.")
    
    # Si hay problemas con las credenciales, ofrecer descarga
    if st.session_state.error_credenciales or not guardar_exitoso:
        st.warning("No se pudieron guardar todas las respuestas en Google Sheets.")
        st.info("Sus respuestas están listas para ser descargadas como archivo CSV.")
        
        # Preparar datos para descarga
        todas_respuestas = []
        for evento, respuestas in st.session_state.respuestas.items():
            datos_evento = {
                "ID_Respuesta": st.session_state.response_id,
                "Nombre_Cliente": st.session_state.nombre_cliente,
                "Fecha_Respuesta": fecha_hora_actual,
                "Nivel_Cargo": st.session_state.demograficos["Nivel_Cargo"],
                "Fecha_Inicio": st.session_state.demograficos["Fecha_Inicio"],
                "Departamento": st.session_state.demograficos["Departamento"],
                "Evento": evento,
                "Probabilidad": respuestas["Probabilidad"],
                "Ocurrencia": respuestas["Ocurrencia"],
                "Detección": respuestas["Detección"],
                "Estructura": respuestas["Estructura"],
                "Impacto": respuestas["Impacto"],
                "Responsabilidad": respuestas["Responsabilidad"],
                "Autoeficacia": respuestas["Autoeficacia"]
            }
            todas_respuestas.append(datos_evento)
        
        # Crear DataFrame para descargar
        df_respuestas = pd.DataFrame(todas_respuestas)
        csv = df_respuestas.to_csv(index=False)
        
        st.download_button(
            label="Descargar respuestas como CSV",
            data=csv,
            file_name=f"encuesta_cck_respuestas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Botón para reiniciar la encuesta
    if st.button("Iniciar nueva encuesta"):
        # Mantener solo el estado de las credenciales y nombre del cliente
        credenciales_verificadas = st.session_state.credenciales_verificadas
        error_credenciales = st.session_state.error_credenciales
        nombre_cliente = st.session_state.nombre_cliente
        
        if hasattr(st.session_state, 'error_mensaje'):
            error_mensaje = st.session_state.error_mensaje
        
        # Reiniciar el resto de valores del estado de sesión
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Restaurar el estado de las credenciales y nombre del cliente
        st.session_state.credenciales_verificadas = credenciales_verificadas
        st.session_state.error_credenciales = error_credenciales
        st.session_state.nombre_cliente = nombre_cliente
        
        if 'error_mensaje' in locals():
            st.session_state.error_mensaje = error_mensaje
        
        st.rerun()

# Añadir información en el pie de página
st.markdown("---")
st.info("Esta encuesta es confidencial y los datos recopilados serán utilizados únicamente con fines estadísticos.")