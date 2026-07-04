# Kursy walut NBP

Interaktywny dashboard kursów walut Narodowego Banku Polskiego.

## Źródło danych
API NBP: https://api.nbp.pl

## Co robi aplikacja

Pobiera historyczne kursy walut (EUR, USD, GBP i inne) i prezentuje
je w formie 5 wykresów: liniowy, histogram, boxplot, scatter, mapa.
Filtry pozwalają wybrać waluty i długość okresu analizy.

## Uruchomienie lokalne

pip install streamlit pandas plotly requests
streamlit run app.py

## Link do aplikacji

http://localhost:8501/#kursy-walut-nbp