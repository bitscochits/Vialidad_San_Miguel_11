import os
import pandas as pd
import numpy as np
import sys

# ============================================================
# CONFIGURACIÓN
# ============================================================

COLUMNA_PESO = "sup_construida_total"
COL_DESTINO = "dc_cod_destino"
OUTPUT_DIR = "san_miguel_analisis"


def asegurar_salida():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def ruta_salida(nombre):
    return os.path.join(OUTPUT_DIR, nombre)

DESTINOS = {
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
    "P": "Administración pública",
}


# ============================================================
# LECTURA Y LIMPIEZA
# ============================================================

def leer_archivo(filename):
    if filename.endswith((".xlsx", ".xls")):
        return pd.read_excel(filename)
    elif filename.endswith(".csv"):
        return pd.read_csv(filename, encoding="utf-8", low_memory=False)
    else:
        raise ValueError("El archivo debe ser .csv, .xlsx o .xls")


def filtrar_san_miguel(df):
    filtros = []

    if "nombreComuna" in df.columns:
        filtros.append(
            df["nombreComuna"]
            .astype(str)
            .str.upper()
            .str.contains("SAN MIGUEL", na=False)
        )

    if "obs_comuna" in df.columns:
        filtros.append(
            df["obs_comuna"]
            .astype(str)
            .str.upper()
            .str.contains("SAN MIGUEL", na=False)
        )

    if "cap__observatorio_de_mercado_de_suelo_urbano_2025__comuna" in df.columns:
        filtros.append(
            df["cap__observatorio_de_mercado_de_suelo_urbano_2025__comuna"]
            .astype(str)
            .str.upper()
            .str.contains("SAN MIGUEL", na=False)
        )

    if "comuna" in df.columns:
        filtros.append(
            df["comuna"]
            .astype(str)
            .str.contains("16106", na=False)
        )

    if "predioPublicado_comuna" in df.columns:
        filtros.append(
            df["predioPublicado_comuna"]
            .astype(str)
            .str.contains("16106", na=False)
        )

    if not filtros:
        print("No se encontró columna comunal. Se analizará el archivo completo.")
        return df.copy()

    filtro_final = filtros[0]
    for f in filtros[1:]:
        filtro_final = filtro_final | f

    return df[filtro_final].copy()


def preparar_base(df):
    df = filtrar_san_miguel(df)

    if "lat" not in df.columns or "lon" not in df.columns:
        raise ValueError("El archivo debe tener columnas lat y lon.")

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"]).copy()

    if COLUMNA_PESO not in df.columns:
        raise ValueError(f"No existe la columna {COLUMNA_PESO}")

    df[COLUMNA_PESO] = pd.to_numeric(df[COLUMNA_PESO], errors="coerce").fillna(0)

    for col in [
        "pisos_max",
        "anio_construccion_min",
        "anio_construccion_max",
        "valorComercial_clp_m2",
        "valorTotal",
        "dc_avaluo_fiscal",
        "pol_area_m2",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if COL_DESTINO in df.columns:
        df["destino_limpio"] = (
            df[COL_DESTINO]
            .astype(str)
            .str.upper()
            .map(DESTINOS)
            .fillna("Otro / sin clasificar")
        )
    elif "destinoDescripcion" in df.columns:
        df["destino_limpio"] = df["destinoDescripcion"].fillna("Otro / sin clasificar")
    else:
        df["destino_limpio"] = "Otro / sin clasificar"

    return df


# ============================================================
# ANÁLISIS
# ============================================================

def resumen_general(df):
    print("\n=== RESUMEN SAN MIGUEL ===")
    print(f"Registros con coordenadas válidas: {len(df):,}")

    if len(df) == 0:
        return

    print(f"Latitud mínima/máxima: {df['lat'].min():.6f} / {df['lat'].max():.6f}")
    print(f"Longitud mínima/máxima: {df['lon'].min():.6f} / {df['lon'].max():.6f}")

    if COLUMNA_PESO in df.columns:
        print("\n--- Superficie construida ---")
        print(f"Total m² construidos: {df[COLUMNA_PESO].sum():,.0f}")
        print(f"Mediana m² construidos: {df[COLUMNA_PESO].median():,.0f}")

    if "pisos_max" in df.columns:
        print("\n--- Densificación ---")
        print(f"Pisos promedio: {df['pisos_max'].mean():.2f}")
        print(f"Pisos mediana: {df['pisos_max'].median():.2f}")
        print(f"Pisos máximo: {df['pisos_max'].max():.2f}")

    if "anio_construccion_min" in df.columns:
        print("\n--- Año de construcción ---")
        print(f"Año promedio: {df['anio_construccion_min'].mean():.0f}")
        print(f"Año mediano: {df['anio_construccion_min'].median():.0f}")

    if "valorComercial_clp_m2" in df.columns:
        print("\n--- Valor comercial del suelo ---")
        print(f"Promedio CLP/m²: {df['valorComercial_clp_m2'].mean():,.0f}")
        print(f"Mediana CLP/m²: {df['valorComercial_clp_m2'].median():,.0f}")


def tabla_usos(df):
    usos = (
        df.groupby("destino_limpio")
        .agg(
            n_predios=("destino_limpio", "size"),
            sup_construida_total_m2=(COLUMNA_PESO, "sum"),
            pisos_mediana=("pisos_max", "median") if "pisos_max" in df.columns else ("destino_limpio", "size"),
            valor_m2_mediana=("valorComercial_clp_m2", "median") if "valorComercial_clp_m2" in df.columns else ("destino_limpio", "size"),
        )
        .reset_index()
        .sort_values("n_predios", ascending=False)
    )

    usos["pct_predios"] = usos["n_predios"] / usos["n_predios"].sum()

    total_sup = usos["sup_construida_total_m2"].sum()
    if total_sup > 0:
        usos["pct_sup_construida"] = usos["sup_construida_total_m2"] / total_sup
    else:
        usos["pct_sup_construida"] = 0

    print("\n=== USOS DE SUELO SAN MIGUEL ===")
    print(usos.to_string(index=False))

    usos.to_csv(ruta_salida("usos_suelo_san_miguel.csv"), index=False, encoding="utf-8-sig")
    return usos


def calcular_centros(df):
    resultados = []

    df_peso = df[df[COLUMNA_PESO] > 0].copy()

    resultados.append({
        "tipo_centro": "Centroide simple",
        "destino": "Todos",
        "lat_centro": df["lat"].mean(),
        "lon_centro": df["lon"].mean(),
        "peso_total_m2": np.nan,
        "n_registros": len(df)
    })

    if len(df_peso) > 0:
        peso_total = df_peso[COLUMNA_PESO].sum()

        resultados.append({
            "tipo_centro": "Centro de masa",
            "destino": "Todos",
            "lat_centro": (df_peso["lat"] * df_peso[COLUMNA_PESO]).sum() / peso_total,
            "lon_centro": (df_peso["lon"] * df_peso[COLUMNA_PESO]).sum() / peso_total,
            "peso_total_m2": peso_total,
            "n_registros": len(df_peso)
        })

        for destino, sub in df_peso.groupby("destino_limpio"):
            peso_destino = sub[COLUMNA_PESO].sum()

            if peso_destino <= 0:
                continue

            resultados.append({
                "tipo_centro": "Centro de masa por destino",
                "destino": destino,
                "lat_centro": (sub["lat"] * sub[COLUMNA_PESO]).sum() / peso_destino,
                "lon_centro": (sub["lon"] * sub[COLUMNA_PESO]).sum() / peso_destino,
                "peso_total_m2": peso_destino,
                "n_registros": len(sub)
            })

    centros = pd.DataFrame(resultados)

    print("\n=== CENTROS DE MASA SAN MIGUEL ===")
    print(centros.to_string(index=False))

    centros.to_csv(ruta_salida("centros_masa_san_miguel.csv"), index=False, encoding="utf-8-sig")
    return centros


def generar_tabla_resumen(df, usos):
    resumen = {
        "registros_georreferenciados": len(df),
        "uso_dominante": usos.iloc[0]["destino_limpio"] if len(usos) > 0 else "sin información",
        "pisos_mediana": df["pisos_max"].median() if "pisos_max" in df.columns else np.nan,
        "anio_construccion_mediana": df["anio_construccion_min"].median() if "anio_construccion_min" in df.columns else np.nan,
        "valor_comercial_m2_mediana": df["valorComercial_clp_m2"].median() if "valorComercial_clp_m2" in df.columns else np.nan,
        "sup_construida_total_m2": df[COLUMNA_PESO].sum(),
    }

    resumen_df = pd.DataFrame([resumen])
    resumen_df.to_csv(ruta_salida("resumen_san_miguel.csv"), index=False, encoding="utf-8-sig")

    print("\n=== RESUMEN EXPORTADO ===")
    print(resumen_df.to_string(index=False))

    return resumen_df


def generar_texto_informe(df, usos):
    if len(df) == 0 or len(usos) == 0:
        return

    uso_principal = usos.iloc[0]["destino_limpio"]
    pct_uso_principal = usos.iloc[0]["pct_predios"] * 100

    pisos_mediana = df["pisos_max"].median() if "pisos_max" in df.columns else np.nan
    anio_mediana = df["anio_construccion_min"].median() if "anio_construccion_min" in df.columns else np.nan
    valor_mediana = df["valorComercial_clp_m2"].median() if "valorComercial_clp_m2" in df.columns else np.nan

    texto = f"""
=== TEXTO BASE PARA EL INFORME ===

La base predial georreferenciada de San Miguel considera {len(df):,} registros con coordenadas válidas,
lo que permite construir una caracterización territorial de la comuna a partir de usos de suelo, densificación,
valor comercial y distribución espacial de actividades.

El uso predominante corresponde a {uso_principal}, representando aproximadamente {pct_uso_principal:.1f}% de los predios georreferenciados.
Esta condición confirma el carácter principalmente residencial de la comuna, aunque se observa presencia relevante de estacionamientos,
bodegas, comercio y equipamientos, lo que introduce una mayor diversidad funcional y potenciales tensiones de movilidad.

La estructura edificada presenta una mediana de {pisos_mediana:.0f} pisos y un año mediano de construcción cercano a {anio_mediana:.0f},
lo que sugiere procesos recientes de densificación y renovación urbana. Además, el valor comercial mediano del suelo alcanza aproximadamente
{valor_mediana:,.0f} CLP/m², lo que evidencia presión inmobiliaria y consolidación urbana.

Desde el punto de vista de la vialidad urbana, estos patrones son relevantes porque una comuna predominantemente residencial,
pero densificada y funcionalmente mixta, genera una demanda de viajes diversa: viajes cotidianos de residentes, desplazamientos hacia equipamientos,
actividad logística asociada a bodegas y comercio, y presión sobre estacionamientos, cruces y paraderos.
"""

    print(texto)

    with open(ruta_salida("texto_diagnostico_san_miguel.txt"), "w", encoding="utf-8") as f:
        f.write(texto)


# ============================================================
# EJECUCIÓN
# ============================================================

def analizar_san_miguel(filename):
    df = leer_archivo(filename)
    df = preparar_base(df)

    asegurar_salida()
    df.to_csv(ruta_salida("predios_san_miguel_filtrados.csv"), index=False, encoding="utf-8-sig")

    resumen_general(df)
    usos = tabla_usos(df)
    calcular_centros(df)
    generar_tabla_resumen(df, usos)
    generar_texto_informe(df, usos)

    print("\n=== ARCHIVOS GENERADOS ===")
    print(f"- {ruta_salida('predios_san_miguel_filtrados.csv')}")
    print(f"- {ruta_salida('usos_suelo_san_miguel.csv')}")
    print(f"- {ruta_salida('centros_masa_san_miguel.csv')}")
    print(f"- {ruta_salida('resumen_san_miguel.csv')}")
    print(f"- {ruta_salida('texto_diagnostico_san_miguel.txt')}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python analizar_san_miguel.py <archivo.csv o archivo.xlsx>")
        sys.exit(1)

    analizar_san_miguel(sys.argv[1])