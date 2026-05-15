import pandas as pd
import sys

def leer_archivo(filename):
    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        return pd.read_excel(filename)
    elif filename.endswith(".csv"):
        return pd.read_csv(filename, encoding="utf-8")
    else:
        raise ValueError("El archivo debe ser .csv, .xlsx o .xls")

def resumen_urbano(filename):
    try:
        df = leer_archivo(filename)

        print("\n=== RESUMEN GENERAL DEL ARCHIVO ===")
        print(f"Archivo: {filename}")
        print(f"Filas: {len(df):,}")
        print(f"Columnas: {len(df.columns):,}")
        print(f"Celdas totales: {df.size:,}")
        print(f"Celdas vacías: {df.isna().sum().sum():,}")
        print(f"Porcentaje de datos faltantes: {df.isna().sum().sum() / df.size * 100:.2f}%")

        print("\n=== COLUMNAS DISPONIBLES ===")
        for col in df.columns:
            print(f"- {col}")

        print("\n=== COMUNAS PRESENTES ===")
        comuna_cols = [c for c in df.columns if "comuna" in c.lower()]
        for col in comuna_cols[:5]:
            print(f"\nColumna: {col}")
            print(df[col].value_counts(dropna=False).head(10))

        # Filtro San Miguel si existe
        df_smg = df.copy()
        if comuna_cols:
            col_comuna = comuna_cols[0]
            df_smg = df[df[col_comuna].astype(str).str.upper().str.contains("SAN MIGUEL", na=False)]

            print("\n=== FILTRO SAN MIGUEL ===")
            print(f"Registros encontrados para San Miguel: {len(df_smg):,}")

        if len(df_smg) == 0:
            print("\nNo se encontraron registros filtrados para San Miguel. Se analizará el archivo completo.")
            df_smg = df.copy()

        print("\n=== CALIDAD DE DATOS PRINCIPALES ===")
        columnas_clave = [
            "rol", "direccion_sii", "lat", "lon",
            "valorTotal", "valorAfecto", "valorExento",
            "supTerreno", "supConsMt2",
            "valorComercial_clp_m2",
            "destinoDescripcion",
            "ubicacion", "sector"
        ]

        for col in columnas_clave:
            if col in df_smg.columns:
                vacios = df_smg[col].isna().sum()
                print(f"{col}: {len(df_smg) - vacios:,} datos válidos / {vacios:,} vacíos")

        print("\n=== RESUMEN TERRITORIAL ===")
        if "lat" in df_smg.columns and "lon" in df_smg.columns:
            print(f"Predios con coordenadas: {df_smg[['lat', 'lon']].dropna().shape[0]:,}")
            print(f"Latitud mínima/máxima: {df_smg['lat'].min()} / {df_smg['lat'].max()}")
            print(f"Longitud mínima/máxima: {df_smg['lon'].min()} / {df_smg['lon'].max()}")

        print("\n=== DESTINOS / USOS DEL SUELO ===")
        posibles_destinos = [
            "destinoDescripcion",
            "txt_cod_destino",
            "dc_cod_destino",
            "ubicacion",
            "sector"
        ]

        for col in posibles_destinos:
            if col in df_smg.columns:
                print(f"\nColumna: {col}")
                counts = df_smg[col].value_counts(dropna=False).head(15)
                percentages = df_smg[col].value_counts(dropna=False, normalize=True).head(15) * 100
                for value, count in counts.items():
                    pct = percentages[value]
                    print(f"{value}: {count:,} ({pct:.1f}%)")

        print("\n=== SUPERFICIES ===")
        columnas_superficie = [
            "supTerreno",
            "supConsMt2",
            "sup_construida_total",
            "pol_area_m2"
        ]

        for col in columnas_superficie:
            if col in df_smg.columns:
                serie = pd.to_numeric(df_smg[col], errors="coerce")
                print(f"\n{col}")
                print(f"Promedio: {serie.mean():,.2f}")
                print(f"Mediana: {serie.median():,.2f}")
                print(f"Mínimo: {serie.min():,.2f}")
                print(f"Máximo: {serie.max():,.2f}")

        print("\n=== AVALÚOS Y VALORES ===")
        columnas_valor = [
            "valorTotal",
            "valorAfecto",
            "valorExento",
            "valorComercial_clp_m2",
            "obs_valor_comercial_m2_suelo",
            "dc_avaluo_fiscal",
            "dc_contribucion_semestral"
        ]

        for col in columnas_valor:
            if col in df_smg.columns:
                serie = pd.to_numeric(df_smg[col], errors="coerce")
                print(f"\n{col}")
                print(f"Promedio: {serie.mean():,.0f}")
                print(f"Mediana: {serie.median():,.0f}")
                print(f"Mínimo: {serie.min():,.0f}")
                print(f"Máximo: {serie.max():,.0f}")

        print("\n=== CONSTRUCCIÓN ===")
        columnas_construccion = [
            "n_lineas_construccion",
            "anio_construccion_min",
            "anio_construccion_max",
            "materiales",
            "calidades",
            "pisos_max",
            "serie"
        ]

        for col in columnas_construccion:
            if col in df_smg.columns:
                print(f"\nColumna: {col}")
                if df_smg[col].dtype == "object":
                    print(df_smg[col].value_counts(dropna=False).head(10))
                else:
                    serie = pd.to_numeric(df_smg[col], errors="coerce")
                    print(f"Promedio: {serie.mean():,.2f}")
                    print(f"Mediana: {serie.median():,.2f}")
                    print(f"Mínimo: {serie.min():,.2f}")
                    print(f"Máximo: {serie.max():,.2f}")

        print("\n=== VARIABLES ÚTILES PARA VIALIDAD URBANA ===")
        print("Este archivo puede servir para:")
        print("- Identificar intensidad de uso del suelo por sector.")
        print("- Ubicar predios habitacionales, comerciales, industriales u otros destinos.")
        print("- Cruzar avalúo y valor comercial con zonas de mayor presión urbana.")
        print("- Detectar sectores con mayor densidad construida.")
        print("- Relacionar usos del suelo con generación potencial de viajes.")
        print("- Apoyar diagnóstico de accesibilidad, equipamientos y demanda urbana.")
        print("- Complementar mapas en QGIS usando lat/lon o coordenadas UTM.")

        print("\n=== MUESTRA DE DATOS ===")
        columnas_muestra = [
            c for c in [
                "rol", "nombreComuna", "direccion_sii", "lat", "lon",
                "valorTotal", "supTerreno", "supConsMt2",
                "destinoDescripcion", "sector", "ubicacion"
            ] if c in df_smg.columns
        ]

        print(df_smg[columnas_muestra].head(10).to_string(index=False))

    except Exception as e:
        print(f"Error al procesar el archivo: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python resumen_urbano.py <archivo.csv o archivo.xlsx>")
        sys.exit(1)

    resumen_urbano(sys.argv[1])