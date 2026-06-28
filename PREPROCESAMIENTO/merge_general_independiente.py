import pandas as pd
import os
import unicodedata
import re

# ------------------------------------------------------------
# CONFIGURACIÓN (cambia la ruta si es necesario)
# ------------------------------------------------------------
folder_path = "./files"   # Carpeta donde están los archivos

vab_file = os.path.join(folder_path, "datos_consolidados_precios_constantes_2007.csv")
edu_2016_file = os.path.join(folder_path, "dataset_2016_con_target.csv")
edu_2018_file = os.path.join(folder_path, "dataset_2018_con_target.csv")
cuartil_2024_file = os.path.join(folder_path, "dataset_2024_con_target.csv")

# ------------------------------------------------------------
# Función de normalización de nombres (para regiones y provincias)
# ------------------------------------------------------------
def normalizar_nombre(nombre):
    if not isinstance(nombre, str):
        return ""
    nombre = nombre.upper()
    nombre = ''.join(c for c in unicodedata.normalize('NFD', nombre) if unicodedata.category(c) != 'Mn')
    nombre = re.sub(r'[^A-Z0-9\s]', '', nombre)
    if nombre in ['LIMA METROPOLITANA', 'LIMA PROVINCIA']:
        nombre = 'LIMA'
    return ' '.join(nombre.split())

# ------------------------------------------------------------
# 1. Datos educativos 2016 y 2018 a nivel distrital (sin agrupar)
# ------------------------------------------------------------
def leer_educacion_distrito(ruta, año):
    # Leer con detección automática de separador
    df = pd.read_csv(ruta, sep=None, engine='python', encoding='utf-8-sig')
    # Normalizar nombres de columnas
    df.columns = [col.strip().upper() for col in df.columns]
    
    # Verificar columnas necesarias
    required = ['REGION', 'PROVINCIA', 'DISTRITO', 'MEDIDA PROMEDIO COMPRENSION LECTORA',
                'MEDIDA PROMEDIO MATEMATICA', 'LECT_PREVIO AL INICIO', 'LECT_EN INICIO',
                'LECT_EN PROCESO', 'LECT_SATISFACTORIO', 'MAT_PREVIO AL INICIO',
                'MAT_EN INICIO', 'MAT_EN PROCESO', 'MAT_SATISFACTORIO']
    for col in required:
        if col not in df.columns:
            print(f"Falta columna {col} en {ruta}")
            return pd.DataFrame()
    
    # Normalizar nombres de región y provincia
    df['REGION'] = df['REGION'].apply(normalizar_nombre)
    df['PROVINCIA'] = df['PROVINCIA'].str.upper().str.strip()
    
    # Seleccionar las columnas de interés (incluyendo distrito, pero luego lo eliminaremos)
    cols = ['REGION', 'PROVINCIA', 'DISTRITO'] + required[3:]  # las métricas
    df = df[cols].copy()
    
    # Renombrar columnas métricas añadiendo el año
    df.rename(columns={c: f'{c}_{año}' for c in required[3:]}, inplace=True)
    return df

edu_2016 = leer_educacion_distrito(edu_2016_file, 2016)
edu_2018 = leer_educacion_distrito(edu_2018_file, 2018)

if edu_2016.empty or edu_2018.empty:
    print("Error: no se pudieron leer los archivos educativos.")
    exit()

# ------------------------------------------------------------
# 2. VAB departamental (pivotado)
# ------------------------------------------------------------
df_vab = pd.read_csv(vab_file, encoding='utf-8-sig')
df_vab.rename(columns={'Departamento': 'REGION'}, inplace=True)
df_vab['REGION'] = df_vab['REGION'].apply(normalizar_nombre)
# Pivotear
pivot_vab = df_vab.pivot_table(index='REGION',
                               columns=['Actividad_Economica', 'Año'],
                               values='VAB_precios_constantes_2007_miles_soles')
pivot_vab.columns = [f'VAB_{act.replace(", ", "_").replace(".", "").replace(" ", "_")}_{año}'
                     for act, año in pivot_vab.columns]
pivot_vab.reset_index(inplace=True)

# ------------------------------------------------------------
# 3. Cuartil 2024 a nivel distrital (sin agrupar)
# ------------------------------------------------------------
df_cuartil = pd.read_csv(cuartil_2024_file, sep=None, engine='python', encoding='utf-8-sig')
df_cuartil.columns = [col.strip().upper() for col in df_cuartil.columns]
df_cuartil['REGION'] = df_cuartil['REGION'].apply(normalizar_nombre)
df_cuartil['PROVINCIA'] = df_cuartil['PROVINCIA'].str.upper().str.strip()
# Seleccionar solo las columnas necesarias
cuartil = df_cuartil[['REGION', 'PROVINCIA', 'DISTRITO', 'CUARTIL']].copy()
cuartil.rename(columns={'CUARTIL': 'CUARTIL_2024'}, inplace=True)

# ------------------------------------------------------------
# 4. Combinar todo a nivel distrital
# ------------------------------------------------------------
# Unir educación 2016 y 2018 por distrito
final = edu_2016.merge(edu_2018, on=['REGION', 'PROVINCIA', 'DISTRITO'], how='outer')
# Agregar VAB por región (departamento)
final = final.merge(pivot_vab, on='REGION', how='left')
# Agregar cuartil 2024 por distrito
final = final.merge(cuartil, on=['REGION', 'PROVINCIA', 'DISTRITO'], how='left')

# Eliminar la columna DISTRITO (como solicitado)
if 'DISTRITO' in final.columns:
    final.drop(columns=['DISTRITO'], inplace=True)

# Eliminar columnas duplicadas (por precaución)
final = final.loc[:, ~final.columns.duplicated()]

# Reordenar columnas (opcional, para claridad)
cols_2016 = [c for c in final.columns if '_2016' in c and not c.startswith('VAB')]
cols_2018 = [c for c in final.columns if '_2018' in c and not c.startswith('VAB')]
cols_vab = [c for c in final.columns if c.startswith('VAB')]
orden = ['REGION', 'PROVINCIA'] + sorted(cols_2016) + sorted(cols_2018) + sorted(cols_vab) + ['CUARTIL_2024']
# Solo mantener las columnas que existen
orden = [c for c in orden if c in final.columns]
final = final[orden]

# Guardar resultado
salida = os.path.join(folder_path, 'dataset_consolidado_distrital_sin_distrito.csv')
final.to_csv(salida, index=False, encoding='utf-8-sig')

print(f"Archivo generado: {salida}")
print(f"Número de distritos: {len(final)}")
print("\nVista previa (primeras 5 filas):")
print(final.head())