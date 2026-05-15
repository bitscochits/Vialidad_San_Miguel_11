import os
import pandas as pd
import numpy as np
import sys
import math

# ============================================================
# CONFIGURACIÓN
# ============================================================

TRAMO_COORDS = [
    (-33.47931769482621, -70.64934060119235),  # inicio tramo
    (-33.47837723581224, -70.65057903313969),  # fin del tramo
]

BUFFER_METROS = 300
COLUMNA_PESO = "sup_construida_total"
COL_DESTINO = "dc_cod_destino"
OUTPUT_DIR = "tramo_analisis"


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
# LECTURA
# ============================================================

def leer_archivo(filename):
    if filename.endswith((".xlsx", ".xls")):
        return pd.read_excel(filename)
    elif filename.endswith(".csv"):
        return pd.read_csv(filename, encoding="utf-8", low_memory=False)
    else:
        raise ValueError("El archivo debe ser .csv, .xlsx o .xls")


# ============================================================
# FILTRO SAN MIGUEL
# ============================================================

def filtrar_san_miguel(df):
    filtros = []

    if "nombreComuna" in df.columns:
        filtros.append(df["nombreComuna"].astype(str).str.upper().str.contains("SAN MIGUEL", na=False))

    if "obs_comuna" in df.columns:
        filtros.append(df["obs_comuna"].astype(str).str.upper().str.contains("SAN MIGUEL", na=False))

    if "cap__observatorio_de_mercado_de_suelo_urbano_2025__comuna" in df.columns:
        filtros.append(
            df["cap__observatorio_de_mercado_de_suelo_urbano_2025__comuna"]
            .astype(str)
            .str.upper()
            .str.contains("SAN MIGUEL", na=False)
        )

    if "comuna" in df.columns:
        filtros.append(df["comuna"].astype(str).str.contains("16106", na=False))

    if "predioPublicado_comuna" in df.columns:
        filtros.append(df["predioPublicado_comuna"].astype(str).str.contains("16106", na=False))

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
# DISTANCIA AL TRAMO
# ============================================================

def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )

    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def distancia_a_tramo_m(lat, lon, tramo_coords):
    """
    Versión simple: distancia al punto más cercano del eje definido.
    Para informe y buffer exploratorio funciona bien.
    """
    return min(
        haversine_m(lat, lon, punto_lat, punto_lon)
        for punto_lat, punto_lon in tramo_coords
    )


def filtrar_buffer_tramo(df):
    df["distancia_tramo_m"] = df.apply(
        lambda row: distancia_a_tramo_m(row["lat"], row["lon"], TRAMO_COORDS),
        axis=1
    )

    return df[df["distancia_tramo_m"] <= BUFFER_METROS].copy()


# ============================================================
# ANÁLISIS
# ============================================================

def resumen_general(df_tramo):
    print("\n=== RESUMEN DEL ÁREA DE INFLUENCIA DEL TRAMO ===")
    print(f"Buffer usado: {BUFFER_METROS} m")
    print(f"Predios dentro del buffer: {len(df_tramo):,}")

    if len(df_tramo) == 0:
        print("No hay predios dentro del buffer. Revisa las coordenadas del tramo.")
        return

    print(f"Distancia promedio al tramo: {df_tramo['distancia_tramo_m'].mean():.1f} m")
    print(f"Distancia máxima al tramo: {df_tramo['distancia_tramo_m'].max():.1f} m")

    print("\n--- Superficie construida ---")
    print(f"Total m² construidos: {df_tramo[COLUMNA_PESO].sum():,.0f}")
    print(f"Mediana m² construidos: {df_tramo[COLUMNA_PESO].median():,.0f}")

    if "pisos_max" in df_tramo.columns:
        print("\n--- Densificación ---")
        print(f"Pisos promedio: {df_tramo['pisos_max'].mean():.2f}")
        print(f"Pisos mediana: {df_tramo['pisos_max'].median():.2f}")
        print(f"Pisos máximo: {df_tramo['pisos_max'].max():.2f}")

    if "anio_construccion_min" in df_tramo.columns:
        print("\n--- Año de construcción ---")
        print(f"Año promedio: {df_tramo['anio_construccion_min'].mean():.0f}")
        print(f"Año mediano: {df_tramo['anio_construccion_min'].median():.0f}")

    if "valorComercial_clp_m2" in df_tramo.columns:
        print("\n--- Valor comercial del suelo ---")
        print(f"Promedio CLP/m²: {df_tramo['valorComercial_clp_m2'].mean():,.0f}")
        print(f"Mediana CLP/m²: {df_tramo['valorComercial_clp_m2'].median():,.0f}")


def tabla_usos(df_tramo):
    usos = (
        df_tramo.groupby("destino_limpio")
        .agg(
            n_predios=("destino_limpio", "size"),
            sup_construida_total_m2=(COLUMNA_PESO, "sum"),
            pisos_mediana=("pisos_max", "median") if "pisos_max" in df_tramo.columns else ("destino_limpio", "size"),
            valor_m2_mediana=("valorComercial_clp_m2", "median") if "valorComercial_clp_m2" in df_tramo.columns else ("destino_limpio", "size"),
        )
        .reset_index()
        .sort_values("n_predios", ascending=False)
    )

    usos["pct_predios"] = usos["n_predios"] / usos["n_predios"].sum()

    total_sup = usos["sup_construida_total_m2"].sum()
    usos["pct_sup_construida"] = (
        usos["sup_construida_total_m2"] / total_sup if total_sup > 0 else 0
    )

    print("\n=== USOS DE SUELO EN EL ÁREA DE INFLUENCIA DEL TRAMO ===")
    print(usos.to_string(index=False))

    usos.to_csv(ruta_salida("usos_suelo_tramo.csv"), index=False, encoding="utf-8-sig")
    return usos


def calcular_centros(df_tramo):
    resultados = []

    if len(df_tramo) == 0:
        return pd.DataFrame()

    df_peso = df_tramo[df_tramo[COLUMNA_PESO] > 0].copy()

    resultados.append({
        "tipo_centro": "Centroide simple tramo",
        "destino": "Todos",
        "lat_centro": df_tramo["lat"].mean(),
        "lon_centro": df_tramo["lon"].mean(),
        "peso_total_m2": np.nan,
        "n_registros": len(df_tramo),
    })

    if len(df_peso) > 0:
        peso_total = df_peso[COLUMNA_PESO].sum()

        resultados.append({
            "tipo_centro": "Centro de masa tramo",
            "destino": "Todos",
            "lat_centro": (df_peso["lat"] * df_peso[COLUMNA_PESO]).sum() / peso_total,
            "lon_centro": (df_peso["lon"] * df_peso[COLUMNA_PESO]).sum() / peso_total,
            "peso_total_m2": peso_total,
            "n_registros": len(df_peso),
        })

        for destino, sub in df_peso.groupby("destino_limpio"):
            peso_destino = sub[COLUMNA_PESO].sum()

            if peso_destino <= 0:
                continue

            resultados.append({
                "tipo_centro": "Centro de masa por destino tramo",
                "destino": destino,
                "lat_centro": (sub["lat"] * sub[COLUMNA_PESO]).sum() / peso_destino,
                "lon_centro": (sub["lon"] * sub[COLUMNA_PESO]).sum() / peso_destino,
                "peso_total_m2": peso_destino,
                "n_registros": len(sub),
            })

    centros = pd.DataFrame(resultados)

    print("\n=== CENTROS DE MASA DEL TRAMO ===")
    print(centros.to_string(index=False))


    centros.to_csv(ruta_salida("centros_masa_tramo.csv"), index=False, encoding="utf-8-sig")
    return centros


def generar_tabla_resumen(df_tramo, usos):
    resumen = {
        "buffer_metros": BUFFER_METROS,
        "predios_georreferenciados": len(df_tramo),
        "uso_dominante": usos.iloc[0]["destino_limpio"] if len(usos) > 0 else "sin información",
        "pisos_mediana": df_tramo["pisos_max"].median() if "pisos_max" in df_tramo.columns else np.nan,
        "anio_construccion_mediana": df_tramo["anio_construccion_min"].median() if "anio_construccion_min" in df_tramo.columns else np.nan,
        "valor_comercial_m2_mediana": df_tramo["valorComercial_clp_m2"].median() if "valorComercial_clp_m2" in df_tramo.columns else np.nan,
        "sup_construida_total_m2": df_tramo[COLUMNA_PESO].sum(),
    }

    resumen_df = pd.DataFrame([resumen])
    resumen_df.to_csv(ruta_salida("resumen_tramo.csv"), index=False, encoding="utf-8-sig")

    print("\n=== RESUMEN EXPORTADO DEL TRAMO ===")
    print(resumen_df.to_string(index=False))

    return resumen_df


def generar_texto_informe(df_tramo, usos):
    if len(df_tramo) == 0 or len(usos) == 0:
        return

    uso_principal = usos.iloc[0]["destino_limpio"]
    pct_uso_principal = usos.iloc[0]["pct_predios"] * 100

    pisos_mediana = df_tramo["pisos_max"].median() if "pisos_max" in df_tramo.columns else np.nan
    anio_mediana = df_tramo["anio_construccion_min"].median() if "anio_construccion_min" in df_tramo.columns else np.nan
    valor_mediana = df_tramo["valorComercial_clp_m2"].median() if "valorComercial_clp_m2" in df_tramo.columns else np.nan

    texto = f"""
=== TEXTO BASE PARA EL INFORME ===

El área de influencia del tramo, definida mediante un buffer de {BUFFER_METROS} metros alrededor del eje vial analizado,
concentra {len(df_tramo):,} predios georreferenciados. El uso predominante corresponde a {uso_principal},
representando aproximadamente {pct_uso_principal:.1f}% de los predios del entorno inmediato.

La estructura edificada presenta una mediana de {pisos_mediana:.0f} pisos y un año mediano de construcción cercano a {anio_mediana:.0f}.
Estos resultados sugieren presencia de densificación y renovación urbana reciente en el entorno del tramo,
lo que aumenta la presión sobre la infraestructura vial, especialmente sobre cruces peatonales, paraderos,
accesos locales y espacios de detención.

Desde el punto de vista de la movilidad, la combinación de usos residenciales, estacionamientos, bodegas,
comercio y equipamientos genera una demanda diversa. Por ello, el tramo no debe entenderse únicamente
como un corredor vehicular, sino como un espacio urbano sometido a múltiples presiones de movilidad:
viajes cotidianos de residentes, flujos de paso por Gran Avenida, actividad logística y desplazamientos
asociados a servicios.
"""

    print(texto)

    with open(ruta_salida("texto_diagnostico_tramo.txt"), "w", encoding="utf-8") as f:
        f.write(texto)


# ============================================================
# EJECUCIÓN
# ============================================================

def analizar_tramo(filename):
    df = leer_archivo(filename)
    df = preparar_base(df)

    print("\n=== BASE SAN MIGUEL CON COORDENADAS ===")
    print(f"Registros válidos: {len(df):,}")

    asegurar_salida()

    df_tramo = filtrar_buffer_tramo(df)

    df_tramo.to_csv(ruta_salida("predios_tramo_filtrados.csv"), index=False, encoding="utf-8-sig")

    resumen_general(df_tramo)
    usos = tabla_usos(df_tramo)
    calcular_centros(df_tramo)
    generar_tabla_resumen(df_tramo, usos)
    generar_texto_informe(df_tramo, usos)

    print("\n=== ARCHIVOS GENERADOS ===")
    print(f"- {ruta_salida('predios_tramo_filtrados.csv')}")
    print(f"- {ruta_salida('usos_suelo_tramo.csv')}")
    print(f"- {ruta_salida('centros_masa_tramo.csv')}")
    print(f"- {ruta_salida('resumen_tramo.csv')}")
    print(f"- {ruta_salida('texto_diagnostico_tramo.txt')}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python analizar_tramo.py <archivo.csv o archivo.xlsx>")
        sys.exit(1)

    analizar_tramo(sys.argv[1])