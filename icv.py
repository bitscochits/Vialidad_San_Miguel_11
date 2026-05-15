import pandas as pd

# Pesos del índice
pesos = {
    "seguridad_peatonal": 0.30,
    "accesibilidad": 0.20,
    "movilidad_activa": 0.20,
    "transporte_publico": 0.15,
    "conectividad_vial": 0.15
}

# Puntajes de criticidad por segmento
# 0 = baja criticidad, 1 = alta criticidad
data = [
    {
        "segmento": "Tramo previo",
        "seguridad_peatonal": 0.70,
        "accesibilidad": 0.60,
        "movilidad_activa": 0.70,
        "transporte_publico": 0.50,
        "conectividad_vial": 0.60
    },
    {
        "segmento": "Tramo corto crítico",
        "seguridad_peatonal": 0.60,
        "accesibilidad": 0.50,
        "movilidad_activa": 0.60,
        "transporte_publico": 0.40,
        "conectividad_vial": 0.50
    },
    {
        "segmento": "Inicio de curvatura",
        "seguridad_peatonal": 0.70,
        "accesibilidad": 0.60,
        "movilidad_activa": 0.70,
        "transporte_publico": 0.50,
        "conectividad_vial": 0.60
    },
    {
        "segmento": "Intersección curva",
        "seguridad_peatonal": 0.90,
        "accesibilidad": 0.80,
        "movilidad_activa": 0.80,
        "transporte_publico": 0.70,
        "conectividad_vial": 0.80
    },
    {
        "segmento": "Salida intersección",
        "seguridad_peatonal": 0.70,
        "accesibilidad": 0.60,
        "movilidad_activa": 0.60,
        "transporte_publico": 0.50,
        "conectividad_vial": 0.60
    }
]

df = pd.DataFrame(data)

# Calcular índice
df["ICV_criticidad"] = sum(df[col] * peso for col, peso in pesos.items())

# Ordenar de mayor a menor criticidad
df = df.sort_values("ICV_criticidad", ascending=False)

print(df)

df.to_csv("icv_criticidad_tramo.csv", index=False, encoding="utf-8-sig")