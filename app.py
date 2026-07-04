import streamlit as st
import pandas as pd
import plotly.express as px
import requests

st.set_page_config(page_title="Kursy walut NBP", layout="wide")

# Lista dostępnych walut
CURRENCIES = ["EUR", "USD", "GBP", "CHF", "JPY", "CZK", "NOK", "SEK"]

# Współrzędne geograficzne krajów emisji walut
GEO = {
    "EUR": ("Strefa Euro", 50.1,  8.7),
    "USD": ("USA",         38.9, -77.0),
    "GBP": ("W. Brytania", 51.5,  -0.1),
    "CHF": ("Szwajcaria",  46.9,   7.4),
    "JPY": ("Japonia",     35.7, 139.7),
    "CZK": ("Czechy",      50.1,  14.4),
    "NOK": ("Norwegia",    59.9,  10.7),
    "SEK": ("Szwecja",     59.3,  18.1),
}

# Pobranie N ostatnich notowań waluty z API NBP - wynik cachowany przez 1 godzinę
@st.cache_data(ttl=3600)
def fetch_data(code, days):
    url = f"https://api.nbp.pl/api/exchangerates/rates/A/{code}/last/{days}/?format=json"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        return pd.DataFrame()
    d = r.json()
    # Budowa listy słowników z odpowiedzi JSON
    rows = [{"date": x["effectiveDate"], "rate": x["mid"], "currency": code}
            for x in d["rates"]]
    return pd.DataFrame(rows)

# Filtry w panelu bocznym
with st.sidebar:
    st.title("Filtry")

    # Widget 1: wybór wielu walut
    selected_currencies = st.multiselect(
        "Waluty", CURRENCIES, default=["EUR", "USD", "GBP"]
    )
    # Widget 2: liczba notowań wstecz (max 200 - limit API NBP to 255)
    days_count = st.slider("Liczba notowań", 30, 200, 90, 10)

    # Widget 3: waluta pokazywana w metrykach KPI
    reference_currency = st.selectbox(
        "Waluta referencyjna (KPI)",
        selected_currencies if selected_currencies else ["EUR"]
    )

# Zatrzymanie aplikacji gdy brak wybranych walut
if not selected_currencies:
    st.warning("Wybierz waluty w panelu bocznym.")
    st.stop()

# Pobranie danych dla każdej wybranej waluty
data_parts = []
for c in selected_currencies:
    df_c = fetch_data(c, days_count)
    if not df_c.empty:
        data_parts.append(df_c)

if not data_parts:
    st.error("Nie udało się pobrać danych z api.nbp.pl")
    st.stop()

# Połączenie danych wszystkich walut w jeden DataFrame
df = pd.concat(data_parts, ignore_index=True)

# Konwersja typów danych
df["date"] = pd.to_datetime(df["date"])
df["rate"] = pd.to_numeric(df["rate"], errors="coerce")

# Usunięcie brakow i duplikatów
df = df.dropna()
df = df.drop_duplicates(subset=["date", "currency"])
df = df.sort_values(["currency", "date"]).reset_index(drop=True)

# Obliczenie kolumn pochodnych - zmiana procentowa i średnia krocząca
df["change_pct"] = df.groupby("currency")["rate"].pct_change() * 100
df["avg_7d"] = df.groupby("currency")["rate"].transform(
    lambda x: x.rolling(7, min_periods=1).mean()
)

st.title("Kursy walut NBP")
st.caption(f"Ostatnie {days_count} notowań")

# Obliczenie metryk dla waluty referencyjnej
df_ref = df[df["currency"] == reference_currency]
col1, col2, col3, col4 = st.columns(4)

if not df_ref.empty:
    current_rate  = df_ref["rate"].iloc[-1]
    first_rate    = df_ref["rate"].iloc[0]
    min_rate      = df_ref["rate"].min()
    max_rate      = df_ref["rate"].max()
    daily_change  = df_ref["change_pct"].iloc[-1]
    period_change = ((current_rate - first_rate) / first_rate * 100) if first_rate > 0 else 0

    col1.metric(f"Kurs {reference_currency}/PLN", f"{current_rate:.4f}", f"{daily_change:+.2f}%")
    col2.metric("Zmiana w okresie", f"{period_change:+.2f}%")
    col3.metric("Minimum",          f"{min_rate:.4f}")
    col4.metric("Maksimum",         f"{max_rate:.4f}")

# Wykres liniowy - kursy wszystkich walut w czasie
fig1 = px.line(
    df, x="date", y="rate", color="currency",
    title="Kursy w czasie",
    labels={"date": "Data", "rate": "Kurs (PLN)", "currency": "Waluta"},
)
fig1.update_layout(height=300, template=None, showlegend=False)
st.plotly_chart(fig1, use_container_width=True)

colA, colB = st.columns(2)

with colA:
    # Histogram - rozkład dziennych zmian procentowych
    fig2 = px.histogram(
        df.dropna(subset=["change_pct"]),
        x="change_pct", color="currency",
        nbins=40, barmode="overlay", opacity=0.4,
        title="Zmiany dzienne (%)",
        labels={"change_pct": "Zmiana (%)", "count": "Liczba dni"},
    )
    fig2.update_layout(height=300, template=None, showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

with colB:
    # Boxplot - statystyczny rozkład kursów per waluta
    fig3 = px.box(
        df, x="currency", y="rate", color="currency",
        title="Boxplot kursów",
        labels={"currency": "Waluta", "rate": "Kurs (PLN)"},
        points="outliers",
    )
    fig3.update_layout(height=300, template=None, showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

# Scatter - zależność między wartością kursu a dzienną zmianą
fig4 = px.scatter(
    df.dropna(subset=["change_pct"]),
    x="rate", y="change_pct", color="currency",
    title="Kurs vs zmiana dzienna",
    labels={"rate": "Kurs (PLN)", "change_pct": "Zmiana (%)", "currency": "Waluta"},
    opacity=0.4,
)
fig4.update_layout(height=300, template=None, showlegend=False)
st.plotly_chart(fig4, use_container_width=True)

# Budowa danych do mapy - ostatni kurs i zmiana dla każdej waluty
map_rows = []
for c in selected_currencies:
    if c not in GEO:
        continue
    df_c = df[df["currency"] == c]
    if df_c.empty:
        continue
    country, lat, lon = GEO[c]
    map_rows.append({
        "currency": c,
        "country":  country,
        "lat":      lat,
        "lon":      lon,
        "rate":     round(df_c["rate"].iloc[-1], 4),
        "change":   round(df_c["change_pct"].iloc[-1], 2)
                    if not df_c["change_pct"].isna().all() else 0,
    })

if map_rows:
    df_map = pd.DataFrame(map_rows)
    # Mapa - punkty na krajach emisji walut (rozmiar=kurs, kolor=zmiana dzienna)
    fig5 = px.scatter_mapbox(
        df_map, lat="lat", lon="lon",
        size="rate",
        color="change",
        color_continuous_scale=["#AAAAAA", "#555555"],
        color_continuous_midpoint=0,
        hover_name="currency",
        hover_data={"country": True, "rate": True, "change": True,
                    "lat": False, "lon": False},
        zoom=1, center={"lat": 30, "lon": 15},
        mapbox_style="open-street-map",
        height=350,
        title="Mapa walut",
    )
    fig5.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0}, template=None)
    st.plotly_chart(fig5, use_container_width=True)

# Tabela surowych danych z opcją pobierania CSV
st.subheader("Dane")
df_show = df[["date", "currency", "rate", "change_pct", "avg_7d"]].copy()
df_show["date"] = df_show["date"].dt.strftime("%Y-%m-%d")
df_show = df_show.sort_values(["currency", "date"], ascending=[True, False])
st.dataframe(df_show, use_container_width=True, height=300)

csv_data = df_show.to_csv(index=False).encode("utf-8")
st.download_button("Pobierz CSV", csv_data, "kursy_nbp.csv", "text/csv")

st.caption("Źródło: Narodowy Bank Polski - api.nbp.pl")