import pandas as pd

# 1. Aquí definimos la "receta" (la función que ya tenías)
def calcular_cuartiles(df, col_name='Medida Promedio Matematica'):
    # Convertimos a número por si hay espacios en blanco
    df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
    
    # q=4 significa 'Cuartiles'. 
    # El puntaje más bajo recibe Q4, el más alto recibe Q1
    df['CUARTIL'] = pd.qcut(df[col_name], q=4, labels=['Q4', 'Q3', 'Q2', 'Q1'])
    
    return df

# ==========================================
# 2. APLICACIÓN PRÁCTICA (La ejecución real)
# ==========================================

# A. Cargar los archivos originales (usamos sep=';' porque así están tus datos)
print("Cargando archivos...")
df_2016 = pd.read_csv('dataset_merged_2016.csv', sep=';')
df_2018 = pd.read_csv('dataset_merged_2018.csv', sep=';')
df_2024 = pd.read_csv('dataset_merged_2024.csv', sep=';')

# B. Aplicar la función a cada dataframe
print("Calculando cuartiles...")
df_2016 = calcular_cuartiles(df_2016)
df_2018 = calcular_cuartiles(df_2018)
df_2024 = calcular_cuartiles(df_2024)

# C. Guardar el resultado en nuevos archivos para no sobreescribir los originales
print("Guardando nuevos archivos...")
df_2016.to_csv('dataset_2016_con_target.csv', sep=';', index=False)
df_2018.to_csv('dataset_2018_con_target.csv', sep=';', index=False)
df_2024.to_csv('dataset_2024_con_target.csv', sep=';', index=False)

print("Archivos generados")