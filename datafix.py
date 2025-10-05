import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Data Saham Indonesia", layout="wide")
st.title("📈 Data Saham Indonesia (Yahoo Finance)")

# Input kode saham & periode
symbol = st.text_input("Masukkan kode saham:", "MDKA.JK")
periode = st.selectbox("Pilih periode:", ["1wk","1mo","3mo","6mo","1y","5y","max"])

if st.button("Ambil Data"):
    data = yf.download(symbol, period=periode)

    if data.empty:
        st.warning("⚠️ Data tidak ditemukan. Cek kode saham atau koneksi internet.")
    else:
        st.success(f"Data {symbol} berhasil diambil ✅")
        data_reset = data.reset_index()

        # Fungsi aman ambil scalar numeric
        def get_scalar(x):
            try:
                if isinstance(x, (np.ndarray, list, tuple, pd.Series)):
                    return float(np.array(x).flatten()[0])
                else:
                    return float(x)
            except:
                return np.nan

        # Fungsi aman ambil scalar tanggal
        def get_date_scalar(x):
            try:
                if isinstance(x, (pd.Series, np.ndarray, list, tuple)):
                    x = x[0]  # ambil elemen pertama
                return pd.to_datetime(x).strftime("%Y-%m-%d")
            except:
                return np.nan

        # Siapkan DataFrame lengkap
        rows = []
        for i in range(len(data_reset)):
            row = {
                "Date": get_date_scalar(data_reset.loc[i, "Date"]) if "Date" in data_reset.columns else np.nan,
                "Open": get_scalar(data_reset.loc[i, "Open"]) if "Open" in data_reset.columns else np.nan,
                "High": get_scalar(data_reset.loc[i, "High"]) if "High" in data_reset.columns else np.nan,
                "Low": get_scalar(data_reset.loc[i, "Low"]) if "Low" in data_reset.columns else np.nan,
                "Close": get_scalar(data_reset.loc[i, "Close"]) if "Close" in data_reset.columns else np.nan,
                "Volume (Lembar)": get_scalar(data_reset.loc[i, "Volume"]) if "Volume" in data_reset.columns else np.nan,
                "Value (Rp)": "-",
                "Frequency": "-",
                "Market Cap (Rp)": "-"
            }
            rows.append(row)

        df_final = pd.DataFrame(rows)

        # Tampilkan semua baris (scroll otomatis jika banyak)
        st.dataframe(df_final)

        # Chart Close jika ada angka
        if df_final["Close"].notna().any():
            st.line_chart(df_final.set_index("Date")["Close"])
        else:
            st.warning("⚠️ Tidak bisa menampilkan grafik karena data Close bukan angka.")

        # Download CSV
        csv = df_final.to_csv(index=False).encode("utf-8")
        st.download_button("💾 Download CSV", csv, file_name=f"{symbol}.csv")
