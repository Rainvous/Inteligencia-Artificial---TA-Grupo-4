import pandas as pd
import glob
import os

folder_path = ".."  # Carpeta donde están los archivos (puedes cambiarla)
años_interes = ['2016', '2018']
output_file = "datos_consolidados_precios_constantes_2007.csv"

def extraer_datos_archivo(file_path):
    try:
        # Leer la hoja 'Cuadro1' usando la fila 6 (índice 6) como encabezado (años)
        df = pd.read_excel(file_path, sheet_name='Cuadro1', header=6)
        
        # Normalizar nombres de columnas: convertir a string y eliminar espacios
        df.columns = df.columns.astype(str).str.strip()
        
        # Buscar las columnas de los años (pueden venir como '2016' o '2016.0')
        columnas_años = []
        for año in años_interes:
            for col in df.columns:
                if col == año or col == f"{año}.0":
                    columnas_años.append(col)
                    break
            else:
                # Si no se encuentra, intentar búsqueda parcial
                for col in df.columns:
                    if año in col:
                        columnas_años.append(col)
                        break
        
        if not columnas_años:
            print(f"No se encontraron columnas para {años_interes} en {os.path.basename(file_path)}")
            return None
        
        # Limpiar la columna de actividades (primera columna)
        col_actividad = df.columns[0]
        df[col_actividad] = df[col_actividad].astype(str).str.strip()
        df = df.dropna(subset=[col_actividad])
        df = df[~df[col_actividad].str.match(r'^\d+$', na=False)]
        df = df[df[col_actividad] != '']
        df = df[df[col_actividad] != 'nan']
        
        # Renombrar primera columna a 'Actividad'
        df.rename(columns={col_actividad: 'Actividad'}, inplace=True)
        
        # Palabras clave para filtrar actividades
        keywords = ['Telecom', 'Electricidad', 'Administración']
        mask = pd.Series(False, index=df.index)
        for kw in keywords:
            mask |= df['Actividad'].str.contains(kw, case=False, na=False)
        df_filtrado = df[mask].copy()
        
        if df_filtrado.empty:
            print(f"No se encontraron actividades en {os.path.basename(file_path)}")
            return None
        
        # --- CORRECCIÓN: Leer el nombre del departamento desde la celda A2 (segunda fila) ---
        # Leemos la segunda fila (skiprows=1) y tomamos la primera columna
        depto_raw = pd.read_excel(file_path, sheet_name='Cuadro1', header=None, skiprows=1, nrows=1).iloc[0, 0]
        departamento = str(depto_raw).split(':')[0].strip()
        # Si por algún motivo el nombre queda vacío, usamos el nombre del archivo como respaldo
        if not departamento:
            departamento = os.path.basename(file_path).replace('pbi_dep', '').replace('_16.xlsx', '').replace('_17.xlsx', '')
        
        # Transformar de ancho a largo
        df_melted = df_filtrado.melt(
            id_vars=['Actividad'],
            value_vars=columnas_años,
            var_name='Año',
            value_name='VAB_precios_constantes_2007_miles_soles'
        )
        
        # Limpiar la columna 'Año' (quitar '.0' si existe)
        df_melted['Año'] = df_melted['Año'].astype(str).str.replace('.0', '', regex=False)
        
        df_melted['Departamento'] = departamento
        df_melted.rename(columns={'Actividad': 'Actividad_Economica'}, inplace=True)
        
        print(f"✓ {os.path.basename(file_path)}: {len(df_melted)} registros -> {departamento}")
        return df_melted
        
    except Exception as e:
        print(f"Error en {os.path.basename(file_path)}: {e}")
        return None

def main():
    # Buscar archivos en la carpeta actual y en la carpeta padre (por si acaso)
    archivos = glob.glob(os.path.join(folder_path, "pbi_dep*.xlsx"))
    if not archivos:
        archivos = glob.glob(os.path.join("..", "pbi_dep*.xlsx"))
        if archivos:
            print(f"Archivos encontrados en la carpeta padre: {len(archivos)}")
        else:
            print("No se encontraron archivos Excel. Verifica la ruta.")
            return
    
    print(f"Procesando {len(archivos)} archivos...\n")
    lista_dfs = []
    
    for archivo in archivos:
        df_temp = extraer_datos_archivo(archivo)
        if df_temp is not None:
            lista_dfs.append(df_temp)
    
    if not lista_dfs:
        print("No se extrajeron datos de ningún archivo.")
        return
    
    df_final = pd.concat(lista_dfs, ignore_index=True)
    # Reordenar columnas
    df_final = df_final[['Departamento', 'Actividad_Economica', 'Año', 'VAB_precios_constantes_2007_miles_soles']]
    df_final.sort_values(by=['Departamento', 'Año', 'Actividad_Economica'], inplace=True)
    df_final.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"Archivo guardado: {output_file}")
    print(f"Total de registros: {len(df_final)}")
    print("\nVista previa (primeras 10 filas):")
    print(df_final.head(10))

if __name__ == "__main__":
    main()