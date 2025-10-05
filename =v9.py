import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="📈 Data Saham Indonesia", layout="wide")
st.title("📊 Data Saham Indonesia via Yahoo")

# Inputs
symbol = st.text_input("Masukkan kode saham (misal: .JK):",)
interval = st.selectbox("Pilih interval data:", ["1m", "5m", "15m", "30m", "60m", "1d", "1wk", "1mo"])
periode = st.selectbox("Pilih periode:", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "5y", "max"])

def flatten_column(col, expected_len=None, col_name=""):
    """
    Mengembalikan pd.Series 1D dengan panjang expected_len (jika diberikan).
    - Mampu menangani:
      * pd.Series berisi scalar
      * pd.Series berisi np.ndarray/list per sel
      * numpy.ndarray 2D shape (n,1) atau (n,m)
      * scalar / single value
    - Jika length mismatch: jika result length ==1, akan broadcast; jika > expected_len, akan trim;
      jika < expected_len dan !=1, akan pad NaN.
    """
    # Normalize to numpy/pandas first
    # Determine expected length from provided arg if ada
    n = expected_len

    # helper to coerce single element -> scalar
    def elem_to_scalar(x):
        try:
            if isinstance(x, (pd.Series, np.ndarray)):
                arr = np.asarray(x)
                if arr.size == 0:
                    return np.nan
                return arr.flatten()[0]
            elif isinstance(x, (list, tuple)):
                return x[0] if len(x) > 0 else np.nan
            else:
                return x
        except Exception:
            return np.nan

    # Case A: pd.Series
    if isinstance(col, pd.Series):
        # If series contains array/list elements per cell
        if col.dtype == 'O' and col.apply(lambda x: isinstance(x, (np.ndarray, list, tuple, pd.Series))).any():
            out = col.apply(elem_to_scalar).reset_index(drop=True)
        else:
            # If first element is ndarray of shape (n,1) and looks like the whole column packed
            first = col.iloc[0]
            if isinstance(first, np.ndarray) and first.ndim == 2 and first.shape[0] == len(col):
                # col is a Series whose first element is an ndarray with length == rows -> use that ndarray
                arr = np.asarray(first).squeeze()
                out = pd.Series(arr).reset_index(drop=True)
            else:
                out = col.reset_index(drop=True)
        # ensure dtype scalar (not object arrays)
        try:
            out = pd.Series(out.values)
        except Exception:
            out = out

    # Case B: numpy array directly
    elif isinstance(col, np.ndarray):
        arr = np.asarray(col)
        if arr.ndim == 2 and (arr.shape[1] == 1 or arr.shape[0] != 1):
            out = pd.Series(arr.squeeze())
        elif arr.ndim == 1:
            out = pd.Series(arr)
        else:
            # fallback flatten then to series
            out = pd.Series(arr.flatten())

    # Other (scalar / list)
    else:
        try:
            arr = np.asarray(col)
            if arr.ndim == 0:
                out = pd.Series([arr.item()])
            elif arr.ndim == 1:
                out = pd.Series(arr)
            elif arr.ndim == 2 and arr.shape[1] == 1:
                out = pd.Series(arr.squeeze())
            else:
                out = pd.Series(arr.flatten())
        except Exception:
            out = pd.Series([np.nan])

    # Now ensure length matches expected_len if provided
    if expected_len is not None:
        if len(out) == expected_len:
            return out.reset_index(drop=True)
        elif len(out) == 1:
            # broadcast single scalar to full length
            return pd.Series([out.iloc[0]] * expected_len)
        elif len(out) > expected_len:
            return out.iloc[:expected_len].reset_index(drop=True)
        else:  # len(out) < expected_len but >1 -> pad with NaN
            pad = pd.Series([np.nan] * (expected_len - len(out)))
            return pd.concat([out.reset_index(drop=True), pad], ignore_index=True)
    else:
        return out.reset_index(drop=True)

if st.button("🫴🏻 Ambil Data"):
    st.info("Mengambil data dari Yahoo Finance...")
    try:
        data = yf.download(symbol, period=periode, interval=interval, progress=False)

        if data.empty:
            st.warning("⚠️ Data kosong — cek symbol/interval/periode.")
        else:
            st.success(f"Data {symbol} berhasil diambil ({len(data)} baris)")

            data_reset = data.reset_index()  # index -> kolom

            # determine date column name
            date_col_candidate = None
            for c in ["Datetime", "Date", "timestamp", "Index", "index"]:
                if c in data_reset.columns:
                    date_col_candidate = c
                    break
            if date_col_candidate is None:
                # fallback to index values (after reset_index it's usually 'index' or first column)
                date_col_candidate = data_reset.columns[0]

            nrows = len(data_reset)

            # flatten each required column robustly
            try:
                date_s = flatten_column(data_reset[date_col_candidate], expected_len=nrows, col_name="Date")
            except Exception:
                # if date_col_candidate somehow invalid, use index
                date_s = pd.Series(pd.date_range(end=pd.Timestamp.now(), periods=nrows)).dt.strftime("%Y-%m-%d %H:%M:%S")

            open_s = flatten_column(data_reset["Open"], expected_len=nrows) if "Open" in data_reset.columns else pd.Series([np.nan]*nrows)
            high_s = flatten_column(data_reset["High"], expected_len=nrows) if "High" in data_reset.columns else pd.Series([np.nan]*nrows)
            low_s = flatten_column(data_reset["Low"], expected_len=nrows) if "Low" in data_reset.columns else pd.Series([np.nan]*nrows)
            close_s = flatten_column(data_reset["Close"], expected_len=nrows) if "Close" in data_reset.columns else pd.Series([np.nan]*nrows)
            vol_s = flatten_column(data_reset["Volume"], expected_len=nrows) if "Volume" in data_reset.columns else pd.Series([np.nan]*nrows)

            # convert numerics safely
            open_s = pd.to_numeric(open_s, errors="coerce")
            high_s = pd.to_numeric(high_s, errors="coerce")
            low_s = pd.to_numeric(low_s, errors="coerce")
            close_s = pd.to_numeric(close_s, errors="coerce")
            vol_s = pd.to_numeric(vol_s, errors="coerce")

            # format date strings (include time for intraday)
            try:
                date_dt = pd.to_datetime(date_s, errors="coerce")
                if interval in ["1m", "5m", "15m", "30m", "60m"]:
                    date_fmt = date_dt.dt.strftime("%Y-%m-%d %H:%M")
                else:
                    date_fmt = date_dt.dt.strftime("%Y-%m-%d")
            except Exception:
                date_fmt = date_s.astype(str)

            df_final = pd.DataFrame({
                "Date": date_fmt,
                "Open": open_s,
                "High": high_s,
                "Low": low_s,
                "Close": close_s,
                "Volume (Lembar)": vol_s,
                "Value (Rp)": ["-"] * nrows,
                "Frequency": ["-"] * nrows,
                "Market Cap (Rp)": ["-"] * nrows
            })

            # Quick debug: kalau ada kolom yang masih 2D / object with array inside, tampilkan ringkasan
            bad_cols = []
            for c in ["Open","High","Low","Close","Volume (Lembar)"]:
                sample = df_final[c].iloc[:3].tolist()
                if any(isinstance(x, (np.ndarray, list, tuple, pd.Series)) for x in sample):
                    bad_cols.append((c, type(sample[0]), getattr(sample[0], "shape", None)))

            if bad_cols:
                st.warning("⚠️ Terdeteksi kolom bermasalah setelah flattening (sample). Menampilkan detail debug:")
                st.write(bad_cols)

            # show table & chart
            st.dataframe(df_final, use_container_width=True, height=500)

            if df_final["Close"].notna().any():
                st.line_chart(df_final.set_index("Date")["Close"])
            else:
                st.warning("⚠️ Tidak bisa menampilkan grafik karena kolom Close kosong atau bukan angka.")

            csv = df_final.to_csv(index=False).encode("utf-8")
            st.download_button("💾 Download CSV", csv, file_name=f"{symbol.replace('.', '_')}_{periode}_{interval}.csv", mime="text/csv")

    except Exception as e:
        # Tampilkan debug yang lebih jelas supaya mudah diperbaiki
        st.error("Terjadi error saat mengambil / memproses data:")
        st.exception(e)
        # Tampilkan beberapa info tambahan (bisa bantu diagnosa)
        try:
            st.write("info yf download object types:")
            st.write({col: type(data[col]) for col in data.columns})
        except Exception:
            pass
