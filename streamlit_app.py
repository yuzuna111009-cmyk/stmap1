import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
from datetime import datetime, timezone, timedelta

# --- ページ設定 ---
st.set_page_config(page_title="九州気温 3D Map", layout="wide")
st.title("九州主要都市の現在の気温 3Dカラムマップ（改良版）")

# 九州7県のデータ
kyushu_capitals = {
    'Fukuoka':    {'lat': 33.5904, 'lon': 130.4017},
    'Saga':       {'lat': 33.2494, 'lon': 130.2974},
    'Nagasaki':   {'lat': 32.7450, 'lon': 129.8739},
    'Kumamoto':   {'lat': 32.7900, 'lon': 130.7420},
    'Oita':       {'lat': 33.2381, 'lon': 131.6119},
    'Miyazaki':   {'lat': 33.9110, 'lon': 131.4240},
    'Kagoshima':  {'lat': 31.5600, 'lon': 130.5580}
}

# --- データ取得 ---
@st.cache_data(ttl=600)
def fetch_weather_data():
    weather_info = []
    BASE_URL = 'https://api.open-meteo.com/v1/forecast'

    for city, coords in kyushu_capitals.items():
        params = {
            'latitude': coords['lat'],
            'longitude': coords['lon'],
            'current': 'temperature_2m'
        }
        response = requests.get(BASE_URL, params=params)
        data = response.json()

        weather_info.append({
            'City': city,
            'lat': coords['lat'],
            'lon': coords['lon'],
            'Temperature': data['current']['temperature_2m'],
            'Time': data['current']['time']
        })

    return pd.DataFrame(weather_info)

with st.spinner("最新の気温データを取得中..."):
    df = fetch_weather_data()

#--- 日本時間に変換（修正版） ---
df['Time'] = pd.to_datetime(df['Time'])

# Open-Meteo の時刻は UTC なので明示的に指定
df['Time'] = df['Time'].dt.tz_localize('UTC')

# 日本時間へ変換
df['Time'] = df['Time'].dt.tz_convert('Asia/Tokyo')

obs_time = df['Time'].iloc[0]

st.caption(f"観測時刻（日本時間）: {obs_time.strftime('%Y-%m-%d %H:%M')}")
# --- 高さスケール調整 ---
scale = st.slider("柱の高さスケール（1℃あたり）", 1000, 5000, 3000)
df['elevation'] = df['Temperature'] * scale

# --- 色を気温で変える ---
def temp_color(temp):
    if temp < 5:
        return [0, 100, 255, 180]
    elif temp < 10:
        return [0, 200, 200, 180]
    elif temp < 15:
        return [255, 200, 0, 180]
    else:
        return [255, 80, 0, 180]

df['color'] = df['Temperature'].apply(temp_color)

# --- レイアウト ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("取得データ")
    st.dataframe(df[['City', 'Temperature']], use_container_width=True)

    st.metric("平均気温", f"{df['Temperature'].mean():.1f} ℃")
    st.metric("最高気温", f"{df['Temperature'].max():.1f} ℃")

    if st.button("データを更新"):
        st.cache_data.clear()
        st.rerun()

with col2:
    st.subheader("3D カラムマップ")

    view_state = pdk.ViewState(
        latitude=32.7,
        longitude=131.0,
        zoom=6.2,
        pitch=45,
    )

    layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position='[lon, lat]',
        get_elevation='elevation',
        radius=12000,
        get_fill_color='color',
        pickable=True,
        auto_highlight=True,
    )

    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>{City}</b><br>気温: {Temperature} ℃",
            "style": {"color": "white"}
        }
    ))
