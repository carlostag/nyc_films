import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import xml.etree.ElementTree as ET
import os

# 1. Configuración de la página de Streamlit
st.set_page_config(
    page_title="NYC Movie Map",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 Scenes from the City: NYC Filming Locations")
st.markdown("""
Esta aplicación visualiza las localizaciones de rodaje icónicas en la ciudad de Nueva York. 
Los datos provienen del libro *Scenes from the City*.
""")

# 2. Función robusta para cargar y procesar el XML
@st.cache_data
def load_data(xml_path):
    if not os.path.exists(xml_path):
        return None
    
    ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        table = root.find('.//ss:Table', ns)
        
        data_rows = []
        for row in table.findall('ss:Row', ns):
            # Creamos una fila predefinida para evitar desplazamientos por celdas vacías
            temp_row = [None] * 25
            col_idx = 0
            for cell in row.findall('ss:Cell', ns):
                # Manejo del atributo ss:Index de Excel
                idx_attr = cell.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
                if idx_attr:
                    col_idx = int(idx_attr) - 1
                
                data_node = cell.find('ss:Data', ns)
                if data_node is not None:
                    temp_row[col_idx] = data_node.text
                col_idx += 1
            data_rows.append(temp_row)

        # Convertir a DataFrame
        df_raw = pd.DataFrame(data_rows)
        
        # Localizar la fila de cabecera 'Film'
        header_row_idx = df_raw[df_raw[0] == 'Film'].index[0]
        df = pd.DataFrame(data_rows[header_row_idx + 1:], columns=data_rows[header_row_idx])

        # Limpieza de datos críticos
        df = df.dropna(subset=['LATITUDE', 'LONGITUDE', 'Film'])
        df['LATITUDE'] = pd.to_numeric(df['LATITUDE'], errors='coerce')
        df['LONGITUDE'] = pd.to_numeric(df['LONGITUDE'], errors='coerce')
        
        # Eliminar filas donde la conversión a número falló
        return df.dropna(subset=['LATITUDE', 'LONGITUDE'])
    
    except Exception as e:
        st.error(f"Error procesando el XML: {e}")
        return None

# 3. Carga de datos
archivo_xml = 'Interactive_Map_Data.xml'
df = load_data(archivo_xml)

if df is not None:
    # --- BARRA LATERAL (Filtros) ---
    st.sidebar.header("🔍 Filtros")
    films = sorted(df['Film'].unique())
    selected_film = st.sidebar.selectbox("Selecciona una película", ["Todas"] + films)

    # Filtrar el DataFrame
    filtered_df = df if selected_film == "Todas" else df[df['Film'] == selected_film]

    # --- MAPA ---
    # Usamos tiles de CartoDB para evitar errores 403 y tener un fondo limpio
    m = folium.Map(
        location=[40.7306, -73.9352], 
        zoom_start=11, 
        tiles='CartoDB positron'
    )

    # Añadir puntos al mapa
    for _, row in filtered_df.iterrows():
        # Limpiar textos para el popup
        popup_text = f"""
        <div style='font-family: sans-serif; min-width: 150px;'>
            <h4 style='margin:0; color:#E53935;'>{row['Film']}</h4>
            <p style='margin:5px 0;'><b>Año:</b> {row['Year']}</p>
            <p style='margin:5px 0;'><b>Lugar:</b> {row['Location Display Text']}</p>
            <hr>
            <a href='{row['IMDB LINK']}' target='_blank' style='color:#1E88E5;'>Ver en IMDB</a>
        </div>
        """
        
        # USAMOS CIRCLE MARKER: Más rápido, no depende de iconos externos y es más profesional
        folium.CircleMarker(
            location=[row['LATITUDE'], row['LONGITUDE']],
            radius=7,
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f"{row['Film']} ({row['Year']})",
            color="#C62828",       # Rojo oscuro para el borde
            fill=True,
            fill_color="#EF5350",  # Rojo claro para el centro
            fill_opacity=0.7,
            weight=2
        ).add_to(m)

    # Mostrar el mapa en la app
    st_folium(m, width="100%", height=600)

    # --- TABLA DE DATOS ---
    with st.expander("Ver lista de localizaciones seleccionadas"):
        st.dataframe(filtered_df[['Film', 'Year', 'Borough', 'Neighborhood', 'Location Display Text']], use_container_width=True)

else:
    st.error(f"No se pudo cargar el archivo '{archivo_xml}'. Verifica que esté en la misma carpeta que este script.")
