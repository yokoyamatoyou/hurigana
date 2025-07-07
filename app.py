from __future__ import annotations
import pandas as pd
import streamlit as st
from core.utils import process_dataframe, to_excel_bytes

st.set_page_config(page_title="Furigana Checker")
st.title("Excel フリガナ信頼度チェッカー")

uploaded = st.file_uploader("Excelを選択", type=["xlsx"])

if "df" not in st.session_state and uploaded:
    st.session_state.df = pd.read_excel(uploaded)

if "df" in st.session_state:
    df = st.session_state.df
    st.write("アップロードしたデータ:")
    st.dataframe(df.head())

    columns = list(df.columns)
    name_col = st.selectbox("名前列を選択", columns, key="name_col")
    furi_col = st.selectbox("フリガナ列を選択", columns, key="furi_col")

    if st.button("解析実行"):
        with st.spinner("解析中..."):
            out_df = process_dataframe(df, name_col, furi_col)
        st.session_state.out_df = out_df

if "out_df" in st.session_state:
    st.write("結果プレビュー:")
    st.dataframe(st.session_state.out_df.head())
    bytes_data = to_excel_bytes(st.session_state.out_df)
    st.download_button(
        label="保存してダウンロード",
        data=bytes_data,
        file_name="判定結果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
