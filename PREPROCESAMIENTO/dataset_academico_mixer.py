import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import filedialog

# ══════════════════════════════════════════════════════════════════════════════
# 1. SELECTOR DE ARCHIVOS
# ══════════════════════════════════════════════════════════════════════════════
root = tk.Tk()
root.withdraw()

print("Selecciona el archivo de MEDIDA PROMEDIO:")
FILE_PROMEDIO = filedialog.askopenfilename(
    title="Seleccionar archivo de Medida Promedio",
    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
)

print("Selecciona el archivo de NIVEL DE DESEMPEÑO:")
FILE_DESEMPENO = filedialog.askopenfilename(
    title="Seleccionar archivo de Nivel de Desempeño",
    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
)

root.destroy()

if not FILE_PROMEDIO or not FILE_DESEMPENO:
    raise SystemExit("Selección cancelada.")

print(f"   ✔ Promedio  : {FILE_PROMEDIO}")
print(f"   ✔ Desempeño : {FILE_DESEMPENO}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. LEER ARCHIVOS Y NORMALIZAR NOMBRES DE COLUMNAS
#    Se asignan nombres explícitos para evitar problemas de encoding con tildes
# ══════════════════════════════════════════════════════════════════════════════
df_prom = pd.read_csv(FILE_PROMEDIO,  skiprows=2, encoding="utf-8", dtype=str)
df_des  = pd.read_csv(FILE_DESEMPENO, skiprows=3, encoding="utf-8", dtype=str)

df_prom.columns = [
    "Codigo Geografico", "REGION", "PROVINCIA", "DISTRITO",
    "Cobertura IE", "Cobertura Estudiantes",
    "Medida Promedio Comprension Lectora",
    "Medida Promedio Matematica"
]

df_des.columns = [
    "Codigo Geografico", "REGION", "PROVINCIA", "DISTRITO",
    "Cobertura IE", "Cobertura Estudiantes",
    "Lect_Previo al Inicio", "Lect_En inicio", "Lect_En proceso", "Lect_Satisfactorio",
    "Mat_Previo al Inicio",  "Mat_En inicio",  "Mat_En proceso",  "Mat_Satisfactorio",
]

KEY_COLS = ["Codigo Geografico", "REGION", "PROVINCIA", "DISTRITO"]


# ══════════════════════════════════════════════════════════════════════════════
# 3. ELIMINAR COLUMNA "Cobertura IE"
# ══════════════════════════════════════════════════════════════════════════════
for df in (df_prom, df_des):
    if "Cobertura IE" in df.columns:
        df.drop(columns=["Cobertura IE"], inplace=True)


# ══════════════════════════════════════════════════════════════════════════════
# 4. FILTRAR FILAS NO VÁLIDAS
#    Solo pasan filas cuyo código geográfico sea numérico (ej: "010101")
#    Descarta pie de página, notas y filas vacías
# ══════════════════════════════════════════════════════════════════════════════
def filtrar_filas(df, nombre=""):
    mascara = df["Codigo Geografico"].str.strip().str.match(r"^\d+$", na=False)
    descartadas = df[~mascara]["Codigo Geografico"].dropna().unique()
    if len(descartadas):
        print(f"   ⚠ [{nombre}] Filas descartadas: {list(descartadas)}")
    return df[mascara].reset_index(drop=True)

df_prom = filtrar_filas(df_prom, "Medida Promedio")
df_des  = filtrar_filas(df_des,  "Nivel de Desempeño")


# ══════════════════════════════════════════════════════════════════════════════
# 5. LIMPIAR VALORES NUMÉRICOS
#    "100,0" → 100.0  |  "-" o vacío → NaN
# ══════════════════════════════════════════════════════════════════════════════
def limpiar_num(serie: pd.Series) -> pd.Series:
    return (
        serie.str.strip()
             .replace({"-": np.nan, "": np.nan})
             .str.replace(",", ".", regex=False)
             .astype(float)
    )

for df in (df_prom, df_des):
    for col in df.columns:
        if col not in KEY_COLS:
            df[col] = limpiar_num(df[col])


# ══════════════════════════════════════════════════════════════════════════════
# 6. MERGE
# ══════════════════════════════════════════════════════════════════════════════
df_merged = pd.merge(
    df_prom, df_des,
    on=KEY_COLS,
    how="outer",
    suffixes=("_prom", "_des")
)


# ══════════════════════════════════════════════════════════════════════════════
# 7. RESOLVER "Cobertura Estudiantes" DUPLICADA
#    iguales → conservar valor | distintos → promedio
# ══════════════════════════════════════════════════════════════════════════════
def resolver_cobertura(row):
    v1, v2 = row["Cobertura Estudiantes_prom"], row["Cobertura Estudiantes_des"]
    if pd.isna(v1) and pd.isna(v2): return np.nan
    if pd.isna(v1): return v2
    if pd.isna(v2): return v1
    return v1 if v1 == v2 else round((v1 + v2) / 2, 1)

df_merged["Cobertura Estudiantes"] = df_merged.apply(resolver_cobertura, axis=1)
df_merged.drop(columns=["Cobertura Estudiantes_prom", "Cobertura Estudiantes_des"], inplace=True)


# ══════════════════════════════════════════════════════════════════════════════
# 8. ORDEN FINAL DE COLUMNAS
# ══════════════════════════════════════════════════════════════════════════════
col_order = (
    KEY_COLS
    + ["Cobertura Estudiantes"]
    + ["Medida Promedio Comprension Lectora", "Medida Promedio Matematica"]
    + ["Lect_Previo al Inicio", "Lect_En inicio", "Lect_En proceso", "Lect_Satisfactorio"]
    + ["Mat_Previo al Inicio",  "Mat_En inicio",  "Mat_En proceso",  "Mat_Satisfactorio"]
)
df_merged = df_merged[col_order]


# ══════════════════════════════════════════════════════════════════════════════
# 9. EXPORTAR
# ══════════════════════════════════════════════════════════════════════════════
OUTPUT = "dataset_merged.csv"
df_merged.to_csv(OUTPUT, index=False, encoding="utf-8-sig", sep=";")

print(f"\n✔  {OUTPUT} guardado")
print(f"   Filas: {len(df_merged)} | Columnas: {len(df_merged.columns)}")
print()
print(df_merged.head(3).to_string())