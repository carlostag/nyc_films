import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import xml.etree.ElementTree as ET
import os

# Configuración de la página
st.set_page_config(page_title="NYC Movie Map", layout="wide")

st.title("🎬 Scenes from the City: NYC Filming Locations")
st.markdown("Explora las localizaciones de rodaje de películas clásicas en Nueva York.")

@st.cache_data
def load_data(xml_path):
    if not os.path.exists(xml_path):
        return None
    
    ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
    tree = ET.parse(xml_path)
    root = tree.getroot()
    table = root.find('.//ss:Table', ns)
    
    data_rows = []
    for row in table.findall('ss:Row', ns):
        # Inicializamos una fila con valores nulos (el dataset tiene unas 22 columnas)
        temp_row = [None] * 25
        col_idx = 0
        for cell in row.findall('ss:Cell', ns):
            # Manejo del índice de Excel para evitar desplazamientos
            idx_attr = cell.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
            if idx_attr:
                col_idx = int(idx_attr) - 1
            
            data_node = cell.find('ss:Data', ns)
            if data_node is not None:
                temp_row[col_idx] = data_node.text
            col_idx += 1
        data_rows.append(temp_row)

    # Crear DataFrame. La fila con índice 1 (segunda fila real) suele ser la cabecera
    df_raw = pd.DataFrame(data_rows)
    # Buscamos la fila que contiene la palabra 'Film' para usarla como cabecera
    try:
        header_row_idx = df_raw[df_raw[0] == 'Film'].index[0]
        df = pd.DataFrame(data_rows[header_row_idx + 1:], columns=data_rows[header_row_idx])
    except IndexError:
        return None

    # Limpieza de datos
    df = df.dropna(subset=['LATITUDE', 'LONGITUDE', 'Film'])
    df['LATITUDE'] = pd.to_numeric(df['LATITUDE'], errors='coerce')
    df['LONGITUDE'] = pd.to_numeric(df['LONGITUDE'], errors='coerce')
    return df.dropna(subset=['LATITUDE', 'LONGITUDE'])

# Cargar datos
df = load_data('Interactive_Map_Data.xml')

if df is not None:
    # Filtros en la barra lateral
    st.sidebar.header("Filtros")
    films = sorted(df['Film'].unique())
    selected_film = st.sidebar.selectbox("Selecciona una película", ["Todas"] + films)

    filtered_df = df if selected_film == "Todas" else df[df['Film'] == selected_film]

    # Crear Mapa con CartoDB (para evitar bloqueos de tiles)
    m = folium.Map(location=[40.7306, -73.9352], zoom_start=11, tiles='CartoDB positron')

    for _, row in filtered_df.iterrows():
        popup_content = f"""
        <div style='font-family: sans-serif; font-size: 12px;'>
            <b>Película:</b> {row['Film']}<br>
            <b>Año:</b> {row['Year']}<br>
            <b>Lugar:</b> {row['Location Display Text']}<br>
            <a href='{row['IMDB LINK']}' target='_blank'>Ver en IMDB</a>
        </div>
        """
        folium.Marker(
            location=[row['LATITUDE'], row['LONGITUDE']],
            popup=folium.Popup(popup_content, max_width=250),
            tooltip=row['Film']
        ).add_to(m)

    # Mostrar mapa
    st_folium(m, width="100%", height=600)
    
    st.dataframe(filtered_df[['Film', 'Year', 'Borough', 'Neighborhood']])
else:
    st.error("No se pudo encontrar el archivo 'Interactive_Map_Data.xml'. Asegúrate de que esté en la raíz del repositorio.")
