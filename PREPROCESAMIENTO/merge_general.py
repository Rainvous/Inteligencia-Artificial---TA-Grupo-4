import pandas as pd
import os
import unicodedata
import re

folder_path = "./files"

# ------------------------------------------------------------
# Función para leer CSV con detección automática de separador
# ------------------------------------------------------------
def leer_csv_auto(ruta):
    # Intentar con sep=None para que pandas infiera el separador
    try:
        df = pd.read_csv(ruta, sep=None, engine='python', encoding='utf-8-sig')
    except:
        df = pd.read_csv(ruta, sep=None, engine='python', encoding='latin1')
    # Normalizar nombres de columnas: mayúsculas, sin espacios
    df.columns = [col.strip().upper() for col in df.columns]
    return df

# ------------------------------------------------------------
# Función de normalización de nombres (para REGION y PROVINCIA)
# ------------------------------------------------------------
def normalizar_nombre(nombre):
    if not isinstance(nombre, str):
        return ""
    nombre = nombre.upper()
    nombre = ''.join(c for c in unicodedata.normalize('NFD', nombre) if unicodedata.category(c) != 'Mn')
    nombre = re.sub(r'[^A-Z0-9\s]', '', nombre)
    # Unificar Lima
    if nombre in ['LIMA METROPOLITANA', 'LIMA PROVINCIA']:
        nombre = 'LIMA'
    return ' '.join(nombre.split())

# ------------------------------------------------------------
# 1. Datos educativos 2016 y 2018 a nivel provincia
# ------------------------------------------------------------
def procesar_educacion_provincia(ruta, año):
    df = leer_csv_auto(ruta)
    # Verificar columnas necesarias
    required = ['REGION', 'PROVINCIA', 'MEDIDA PROMEDIO COMPRENSION LECTORA', 
                'MEDIDA PROMEDIO MATEMATICA', 'LECT_PREVIO AL INICIO', 'LECT_EN INICIO',
                'LECT_EN PROCESO', 'LECT_SATISFACTORIO', 'MAT_PREVIO AL INICIO',
                'MAT_EN INICIO', 'MAT_EN PROCESO', 'MAT_SATISFACTORIO']
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"Faltan columnas en {ruta}: {missing}")
        print("Columnas disponibles:", df.columns.tolist())
        return pd.DataFrame()
    # Normalizar nombres de región y provincia
    df['REGION'] = df['REGION'].apply(normalizar_nombre)
    df['PROVINCIA'] = df['PROVINCIA'].str.upper().str.strip()
    # Agrupar por región y provincia (promedio)
    cols_agrupar = ['REGION', 'PROVINCIA']
    cols_metricas = required[2:]  # las que no son clave
    df_agg = df.groupby(cols_agrupar, as_index=False)[cols_metricas].mean()
    # Renombrar columnas añadiendo el año
    df_agg.rename(columns={c: f'{c}_{año}' for c in cols_metricas}, inplace=True)
    return df_agg

edu_2016 = procesar_educacion_provincia(os.path.join(folder_path, "dataset_2016_con_target.csv"), 2016)
edu_2018 = procesar_educacion_provincia(os.path.join(folder_path, "dataset_2018_con_target.csv"), 2018)

# ------------------------------------------------------------
# 2. VAB departamental (pivotado)
# ------------------------------------------------------------
df_vab = leer_csv_auto(os.path.join(folder_path, "datos_consolidados_precios_constantes_2007.csv"))
df_vab.rename(columns={'DEPARTAMENTO': 'REGION'}, inplace=True)
df_vab['REGION'] = df_vab['REGION'].apply(normalizar_nombre)

pivot_vab = df_vab.pivot_table(index='REGION',
                               columns=['ACTIVIDAD_ECONOMICA', 'AÑO'],
                               values='VAB_PRECIOS_CONSTANTES_2007_MILES_SOLES')
pivot_vab.columns = [f'VAB_{act.replace(", ", "_").replace(".", "").replace(" ", "_")}_{año}'
                     for act, año in pivot_vab.columns]
pivot_vab.reset_index(inplace=True)

# ------------------------------------------------------------
# 3. Cuartil 2024 a nivel provincia (moda)
# ------------------------------------------------------------
df_cuartil = leer_csv_auto(os.path.join(folder_path, "dataset_2024_con_target.csv"))
# Normalizar nombres
df_cuartil['REGION'] = df_cuartil['REGION'].apply(normalizar_nombre)
df_cuartil['PROVINCIA'] = df_cuartil['PROVINCIA'].str.upper().str.strip()

def moda(x):
    return x.mode().iloc[0] if not x.mode().empty else None

cuartil_prov = df_cuartil.groupby(['REGION', 'PROVINCIA'], as_index=False).agg(CUARTIL_2024=('CUARTIL', moda))

# ------------------------------------------------------------
# 4. Combinar
# ------------------------------------------------------------
if edu_2016.empty or edu_2018.empty:
    print("No se pudieron procesar los datos educativos. Revise los archivos.")
    exit()

final = edu_2016.merge(edu_2018, on=['REGION', 'PROVINCIA'], how='outer')
final = final.merge(pivot_vab, on='REGION', how='left')
final = final.merge(cuartil_prov, on=['REGION', 'PROVINCIA'], how='left')

# Eliminar duplicados de columnas (por precaución)
final = final.loc[:, ~final.columns.duplicated()]

# Reordenar columnas
cols_2016 = [c for c in final.columns if '_2016' in c and not c.startswith('VAB')]
cols_2018 = [c for c in final.columns if '_2018' in c and not c.startswith('VAB')]
cols_vab = [c for c in final.columns if c.startswith('VAB')]
orden = ['REGION', 'PROVINCIA'] + sorted(cols_2016) + sorted(cols_2018) + sorted(cols_vab) + ['CUARTIL_2024']
final = final[orden]

salida = os.path.join(folder_path, 'dataset_consolidado_provincial.csv')
final.to_csv(salida, index=False, encoding='utf-8-sig')

print(f"Archivo generado: {salida}")
print(f"Número de provincias: {len(final)}")
print("\nVista previa:")
print(final.head())