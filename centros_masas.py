import pandas as pd
import numpy as np
import sys

def leer_archivo(filename):
    if filename.endswith((".xlsx", ".xls")):
        return pd.read_excel(filename)
    elif filename.endswith(".csv"):
        return pd.read_csv(filename, encoding="utf-8", low_memory=False)
    else:
        raise ValueError("El archivo debe ser .csv, .xlsx o .xls")

def calcular_centros(filename):
    df = leer_archivo(filename)

    # Filtrar San Miguel correctamente
    if "nombreComuna" in df.columns:
        df = df[df["nombreComuna"].astype(str).str.upper().str.contains("SAN MIGUEL", na=False)]
    elif "obs_comuna" in df.columns:
        df = df[df["obs_comuna"].astype(str).str.upper().str.contains("SAN MIGUEL", na=False)]
    elif "comuna" in df.columns:
        df = df[df["comuna"].astype(str).str.contains("16106", na=False)]

    # Asegurar coordenadas numéricas
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    df = df.dropna(subset=["lat", "lon"])

    print("\n=== DATOS USADOS ===")
    print(f"Registros con coordenadas válidas: {len(df):,}")

    # Elegir columna de peso
    # Cambia esta línea si tu columna de m² predestinados tiene otro nombre
    columna_peso = "sup_construida_total"

    if columna_peso not in df.columns:
        raise ValueError(f"No existe la columna {columna_peso}")

    df[columna_peso] = pd.to_numeric(df[columna_peso], errors="coerce").fillna(0)

    # Quitar pesos 0 para centro de masa
    df_peso = df[df[columna_peso] > 0].copy()

    resultados = []

    # Centroide simple
    resultados.append({
        "tipo_centro": "Centroide simple",
        "destino": "Todos",
        "lat_centro": df["lat"].mean(),
        "lon_centro": df["lon"].mean(),
        "peso_total_m2": np.nan,
        "n_registros": len(df)
    })

    # Centro de masa general
    peso_total = df_peso[columna_peso].sum()

    resultados.append({
        "tipo_centro": "Centro de masa",
        "destino": "Todos",
        "lat_centro": (df_peso["lat"] * df_peso[columna_peso]).sum() / peso_total,
        "lon_centro": (df_peso["lon"] * df_peso[columna_peso]).sum() / peso_total,
        "peso_total_m2": peso_total,
        "n_registros": len(df_peso)
    })

    # Diccionario de destinos
    destinos = {
        "H": "Habitacional",
        "Z": "Estacionamiento",
        "L": "Bodega / Almacenaje",
        "C": "Comercio",
        "O": "Oficina",
        "I": "Industria",
        "E": "Educación y cultura",
        "S": "Salud",
        "D": "Deporte y recreación",
        "T": "Transporte y telecom.",
        "P": "Administración pública"
    }

    # Usar mejor dc_cod_destino
    col_destino = "dc_cod_destino"

    if col_destino not in df_peso.columns:
        raise ValueError(f"No existe la columna {col_destino}")

    # Centro de masa por destino
    for codigo, nombre in destinos.items():
        sub = df_peso[df_peso[col_destino].astype(str).str.upper() == codigo]

        if len(sub) == 0:
            continue

        peso_destino = sub[columna_peso].sum()

        if peso_destino == 0:
            continue

        resultados.append({
            "tipo_centro": "Centro de masa por destino",
            "destino": nombre,
            "lat_centro": (sub["lat"] * sub[columna_peso]).sum() / peso_destino,
            "lon_centro": (sub["lon"] * sub[columna_peso]).sum() / peso_destino,
            "peso_total_m2": peso_destino,
            "n_registros": len(sub)
        })

    resultados_df = pd.DataFrame(resultados)

    print("\n=== CENTROS CALCULADOS ===")
    print(resultados_df.to_string(index=False))

    # Guardar resultado
    output = "centros_masa_san_miguel.csv"
    resultados_df.to_csv(output, index=False, encoding="utf-8-sig")

    print(f"\nArchivo guardado como: {output}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python centros_masa.py <archivo.csv o archivo.xlsx>")
        sys.exit(1)

    calcular_centros(sys.argv[1])