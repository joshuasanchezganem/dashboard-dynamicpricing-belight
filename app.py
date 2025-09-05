import re
import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import plotly.io as pio

from googleapiclient.discovery import build
from google.oauth2 import service_account

def cargar_bd(spreedsheet):

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    KEY = 'key.json'
    SS = '19HvKbrNvKE1TnNUvpw0B0NtNQEBNtYNes0VOhNhsHnY'

    creds = None
    creds = service_account.Credentials.from_service_account_file(KEY, scopes=SCOPES)

    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    result = sheet.values().get(spreadsheetId=SS, range=f'{spreedsheet}!A1:I10000000').execute()

    values = result.get('values', [])
    data = values[1:]
    heads = values[0]

    df = pd.DataFrame(data, columns=heads)

    df["Fecha_Hora"] = pd.to_datetime(df["Fecha_Hora"])

    df[['Precio', 'Precio_Descuento', 'Cantidad']] = df[['Precio', 'Precio_Descuento', 'Cantidad']].astype(float)
    df[['Cantidad']] = df[['Cantidad']].astype(int)

    return df



pio.templates.default = "plotly"

ss_query = 'Sheet1'

df_final = cargar_bd(ss_query)

df_final = df_final[df_final["Retailer"] != "Costco"]
df_final["Fecha_Hora"] = pd.to_datetime(df_final["Fecha_Hora"])
df_final["Fecha"] = df_final["Fecha_Hora"].dt.date

# Valores únicos para filtros
modelos = sorted(df_final["Modelo"].unique())
retailers = sorted(df_final["Retailer"].unique())

ultimos_7_dias = df_final["Fecha_Hora"].max() - pd.Timedelta(days=7)

df_ofertas = df_final[
    (df_final["Precio_Descuento"] > 0) &
    (df_final["Fecha_Hora"] >= ultimos_7_dias)
].copy()

df_ofertas["Descuento_%"] = ((df_ofertas["Precio_Descuento"] - df_ofertas["Precio"]) / df_ofertas["Precio_Descuento"] * 100).round(0).astype(int)

# Ordenar de mayor a menor descuento
df_ofertas = df_ofertas.sort_values(by="Descuento_%", ascending=False)

df_ofertas["Etiqueta"] = (
    "💸 " + df_ofertas["Descuento_%"].astype(str) +
    "% de Descuento en " + df_ofertas["Modelo"] +
    " en " + df_ofertas["Retailer"]
)

# Crear app
app = dash.Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Dashboard Comparativo de Precios", style={'textAlign': 'center'}),

    html.Div([
        html.Label("Selecciona fechas:", style={"fontWeight": "bold"}),
        dcc.DatePickerRange(
            id="date-filter",
            start_date=df_final["Fecha_Hora"].min().date(),
            end_date=df_final["Fecha_Hora"].max().date(),
            display_format='YYYY-MM-DD',
            style={"width": "100%"}
        )
    ], style={
        "padding": "20px",
        "margin": "20px",
        "backgroundColor": "#ffffff",
        "borderRadius": "10px",
        "boxShadow": "0 0 5px rgba(0, 0, 0, 0.1)"
        }),

    html.Div([
        html.Label("Selecciona productos:", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id="modelo-filter",
            options=[{"label": m, "value": m} for m in modelos],
            value=modelos,
            multi=True,
            placeholder="Selecciona productos...",
            style={"maxHeight": "40px", "overflow": "hidden", "whiteSpace": "nowrap", "textOverflow": "ellipsis"}
        )
    ], style={
        "padding": "20px",
        "margin": "20px",
        "backgroundColor": "#ffffff",
        "borderRadius": "10px",
        "boxShadow": "0 0 5px rgba(0, 0, 0, 0.1)"
        }),

    html.Div([
        html.Label("Selecciona retailers:", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id="retailer-filter",
            options=[{"label": r, "value": r} for r in retailers],
            value=retailers,
            multi=True,
            placeholder="Selecciona retailers...",
            style={"maxHeight": "40px", "overflow": "hidden", "whiteSpace": "nowrap", "textOverflow": "ellipsis"}
        )
    ], style={
        "padding": "20px",
        "margin": "20px",
        "backgroundColor": "#ffffff",
        "borderRadius": "10px",
        "boxShadow": "0 0 5px rgba(0, 0, 0, 0.1)"
        }),

    html.Div([
        html.H3("Ofertas recientes (últimos 7 días)", style={"textAlign": "center"}),

        html.Div([
            # === IZQUIERDA: Lista de Ofertas ===
            html.Div([
                html.Ul(id="ofertas-recientes", style={"listStyleType": "none", "padding": 0})
            ], style={
                "marginBottom": "20px",
                "display": "flex",
                "flexWrap": "wrap",
            }),

            # === DERECHA: Gráfico de evolución ===
            html.Div([
                dcc.Graph(id="grafica-ofertas")
            ])
    ])], style={"padding": "20px", "margin": "20px", "backgroundColor": "#ffffff", "borderRadius": "10px"}),

    html.Div([
        html.H3("Heatmap de Precios Promedio por Retailer y Modelo"),
        dcc.Graph(id="heatmap")
    ], style={"padding": "20px", "margin": "20px", "backgroundColor": "#ffffff", "borderRadius": "10px"}),

    html.Div([
        html.H3("Top Retailers con Mejores Precios Promedio"),
        dcc.Graph(id="bar-top-retailers")
    ], style={"padding": "20px", "margin": "20px", "backgroundColor": "#ffffff", "borderRadius": "10px"}),

    html.Div([
        html.Label("Selecciona 2 retailers para comparar:", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id="retailer-comparativa",
            options=[{"label": r, "value": r} for r in retailers],
            value=retailers[:2],
            multi=True,
            placeholder="Selecciona solo 2 retailers",
            style={"maxWidth": "400px"}
        ),
        html.Div(id="error-retailers", style={"color": "red", "fontWeight": "bold", "marginLeft": "20px"})
    ]),

    html.Div([
        html.H3("Evolución de precios por hora"),
        dcc.Graph(id="line-hora"),

        html.H3("Evolución de precios por día (ultimos 7 días)"),
        dcc.Graph(id="line-dia")
    ], style={"padding": "20px", "margin": "20px", "backgroundColor": "#ffffff", "borderRadius": "10px"}),
])

@app.callback(
    Output("error-retailers", "children"),
    Input("retailer-comparativa", "value")
)
def validar_retailers_seleccionados(retailers_sel):
    if len(retailers_sel) != 2:
        return "Por favor selecciona exactamente 2 retailers para hacer la comparativa."
    return ""

@app.callback(
    [
        Output("heatmap", "figure"),
        Output("bar-top-retailers", "figure"),
        Output("line-hora", "figure"),
        Output("line-dia", "figure")
    ],
    [
        Input("date-filter", "start_date"),
        Input("date-filter", "end_date"),
        Input("modelo-filter", "value"),
        Input("retailer-filter", "value"),
        Input("retailer-comparativa", "value")
    ]
)
def update_graphs(start_date, end_date, selected_modelos, selected_retailers, retailers_sel):
    color_map = {
        "Hydrolit": "#ec00ff",
        "Electrolit": "#ffc3c3",
        "SueroX": "#ffebc3",
        "FlashLyte": "#c3ffe2",
        "GatorLyte": "#c3dcff"
    }
    df_filtered = df_final[
        (df_final["Fecha"] >= pd.to_datetime(start_date).date()) &
        (df_final["Fecha"] <= pd.to_datetime(end_date).date()) &
        (df_final["Modelo"].isin(selected_modelos)) &
        (df_final["Retailer"].isin(selected_retailers))
    ]

    pivot_df = df_filtered[~df_filtered['Producto'].str.contains('1,5|1.5|1,4|1.4|1,2|1.2|2l|2 l|5l|5 l|6l|6 l|3l|3 l', case=False, na=False)].pivot_table(
        index="Retailer", columns="Modelo", values="Precio", aggfunc='mean'
    ).fillna(0).round(0).astype(int)

    heatmap = px.imshow(pivot_df, text_auto=True, aspect="auto", color_continuous_scale="Blues", labels={"color": "Precio"})

    avg_price = df_filtered.groupby("Retailer")["Precio"].mean().nsmallest(5)
    top_5 = avg_price.index.tolist()

    bar_df = df_filtered[df_filtered["Retailer"].isin(top_5)]
    bar_df = bar_df.groupby(["Retailer", "Modelo"])["Precio"].mean().reset_index().round(2)

    bar_fig = px.bar(bar_df, x="Retailer", y="Precio", color="Modelo", barmode="group", text="Precio",color_discrete_map=color_map)
    bar_fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')

    if len(retailers_sel) != 2:
        return px.line(title="Selecciona dos retailers para comparar")
    
    df_filtrado = df_final[
        (df_final["Fecha"] >= pd.to_datetime(start_date).date()) &
        (df_final["Fecha"] <= pd.to_datetime(end_date).date()) &
        (df_final["Modelo"].isin(selected_modelos)) &
        (df_final["Retailer"].isin(retailers_sel))
    ].copy()

    df_filtrado["Hora"] = df_filtrado["Fecha_Hora"].dt.hour
    line_hora_df = df_filtrado.groupby(["Hora", "Modelo", "Retailer"])["Precio"].mean().reset_index()

    line_hora_df["Etiqueta"] = line_hora_df["Modelo"] + " (" + line_hora_df["Retailer"] + ")"

    line_hora = px.line(
        line_hora_df,
        x="Hora",
        y="Precio",
        color="Etiqueta",
        markers=True,
        title="Comparativa por hora"
    )

    last_7 = df_filtrado["Fecha_Hora"].max() - pd.Timedelta(days=7)
    df_last_7 = df_filtrado[df_filtrado["Fecha_Hora"] >= last_7].copy()
    df_last_7["Fecha"] = df_last_7["Fecha_Hora"].dt.date

    line_dia_df = df_last_7.groupby(["Fecha", "Modelo", "Retailer"])["Precio"].mean().reset_index()

    line_dia_df["Etiqueta"] = line_dia_df["Modelo"] + " (" + line_dia_df["Retailer"] + ")"

    line_dia = px.line(
        line_dia_df,
        x="Fecha",
        y="Precio",
        color="Etiqueta",
        markers=True,
        title="Comparativa por día (últimos 7 días)"
    )

    return heatmap, bar_fig, line_hora, line_dia

@app.callback(
    [
        Output("ofertas-recientes", "children"),
        Output("grafica-ofertas", "figure")
    ],
    [
        Input("date-filter", "start_date"),
        Input("date-filter", "end_date"),
        Input("modelo-filter", "value"),
        Input("retailer-filter", "value")
    ]
)
def actualizar_ofertas(start_date, end_date, modelos_seleccionados, retailers_seleccionados):
    df_filtrado = df_final[
        (df_final["Fecha_Hora"].dt.date >= pd.to_datetime(start_date).date()) &
        (df_final["Fecha_Hora"].dt.date <= pd.to_datetime(end_date).date()) &
        (df_final["Modelo"].isin(modelos_seleccionados)) &
        (df_final["Retailer"].isin(retailers_seleccionados))
    ].copy()

    if df_filtrado.empty:
        return [html.Div("No hay ofertas recientes en este rango de fechas.")], px.bar(title="Sin datos")

    # Calcular descuento y cantidad
    df_filtrado["Descuento (%)"] = ((df_filtrado["Precio_Descuento"] - df_filtrado["Precio"]) / df_filtrado["Precio_Descuento"] * 100).round(2)
    # df_filtrado["Cantidad"] = df_filtrado["Producto"].apply(extraer_cantidad_promocion)

    # =============================
    # 🟢 Sección 1: Promociones por Paquete (ej. 2x, 3 por, etc.)
    paquetes = df_filtrado[df_filtrado["Cantidad"] > 1].drop_duplicates(["Modelo", "Retailer"]).head(5)

    etiquetas_paquete = [
        html.Div(
            f"📦 {int(row['Cantidad'])} por ${int(row['Precio'])} en {row['Modelo']} ({row['Retailer']})",
            style={
                "display": "inline-block",
                "backgroundColor": "#fffbe6",
                "color": "#b38f00",
                "padding": "10px",
                "margin": "5px",
                "borderRadius": "10px",
                "fontWeight": "bold",
                "whiteSpace": "nowrap"
            }
        )
        for _, row in paquetes.iterrows()
    ]

    # =============================
    # 🔵 Sección 2: Descuentos tradicionales (precio rebajado)
    descuentos = df_filtrado[(df_filtrado["Cantidad"] == 1) & (df_filtrado["Precio_Descuento"] > 0)].sort_values("Descuento (%)", ascending=False).drop_duplicates(["Modelo", "Retailer"]).head(5)

    etiquetas_descuento = [
        html.Div(
            f"💸 {row['Descuento (%)']}% de descuento en {row['Modelo']} en {row['Retailer']}",
            style={
                "display": "inline-block",
                "backgroundColor": "#e6f7ff",
                "color": "#007acc",
                "padding": "10px",
                "margin": "5px",
                "borderRadius": "10px",
                "fontWeight": "bold",
                "whiteSpace": "nowrap"
            }
        )
        for _, row in descuentos.iterrows()
    ]

    # Combinar ambas secciones con títulos
    etiquetas = [
        html.H4("📦 Promociones por Paquete"),
        *etiquetas_paquete,
        html.H4("💸 Descuentos Individuales"),
        *etiquetas_descuento
    ]

    # Top descuentos por producto-retailer
    top_descuentos = (
        df_filtrado[(df_filtrado["Precio_Descuento"] > 0)].groupby(["Modelo", "Retailer"])["Descuento (%)"]
        .max()
        .reset_index()
        .sort_values(by="Descuento (%)", ascending=False)
        .head(10)
    )

    top_descuentos["Producto_Retailer"] = top_descuentos["Modelo"] + " - " + top_descuentos["Retailer"]

    fig_top_desc = px.bar(
        top_descuentos,
        x="Producto_Retailer",
        y="Descuento (%)",
        color="Retailer",
        text="Descuento (%)",
        title="Top descuentos recientes por producto y retailer"
    )
    fig_top_desc.update_traces(textposition='outside')
    fig_top_desc.update_layout(xaxis_tickangle=-45)

    return etiquetas, fig_top_desc

if __name__ == "__main__":
    app.run_server(debug=True)