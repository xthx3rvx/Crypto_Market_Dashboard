import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import datetime
import io

# ----------------------------------------
# CONFIGURATION
# ----------------------------------------
st.set_page_config(page_title="🪙 Crypto Market Dashboard", layout="wide")
COIN_OPTIONS = ["bitcoin", "ethereum", "ripple", "litecoin", "cardano", "solana", "dogecoin"]
CURRENCY_OPTIONS = ["usd", "inr", "eur"]

# ----------------------------------------
# UTILITY FUNCTIONS
# ----------------------------------------
@st.cache_data(ttl=300)
def fetch_market_data(selected_coins, currency):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': currency,
        'ids': ','.join(selected_coins),
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1,
        'sparkline': False
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Market data fetch failed: {response.status_code} - {response.text}")

@st.cache_data(ttl=300)
def fetch_historical_data(coin, currency, from_date, to_date):
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart/range"
    from_ts = int(from_date.timestamp())
    to_ts = int(to_date.timestamp())
    params = {
        'vs_currency': currency,
        'from': from_ts,
        'to': to_ts
    }
    r = requests.get(url, params=params)
    if r.status_code == 200:
        return r.json()
    else:
        raise Exception(f"Historical data fetch failed for {coin}: {r.status_code} - {r.text}")

def format_market_data(raw_data):
    df = pd.DataFrame(raw_data)
    df = df[["name", "symbol", "current_price", "price_change_percentage_24h", "market_cap"]].copy()
    df.columns = ["Name", "Symbol", "Price", "24h Change (%)", "Market Cap"]
    df.fillna({"Price": 0, "24h Change (%)": 0, "Market Cap": 0}, inplace=True)
    return df

def format_complete_historical_data(data):
    prices = data.get("prices", [])
    market_caps = data.get("market_caps", [])
    total_volumes = data.get("total_volumes", [])
    if not prices:
        return pd.DataFrame()
    df = pd.DataFrame({
        'Timestamp': [p[0] for p in prices],
        'Price': [p[1] for p in prices],
        'Market_Cap': [mc[1] if mc else 0 for mc in market_caps],
        'Volume': [tv[1] if tv else 0 for tv in total_volumes]
    })
    df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')
    df = df[['Date', 'Price', 'Market_Cap', 'Volume']]
    df['Price'] = df['Price'].round(2)
    df['Market_Cap'] = df['Market_Cap'].round(0)
    df['Volume'] = df['Volume'].round(0)
    return df

def download_button_csv(df, filename="crypto_data.csv"):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download as CSV",
        data=csv,
        file_name=filename,
        mime="text/csv"
    )

def download_button_excel(df, filename="crypto_data.xlsx"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button(
        label="⬇ Download as Excel",
        data=buffer.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ----------------------------------------
# SIDEBAR CONFIGURATION
# ----------------------------------------
st.sidebar.title("⚙ Settings")
currency = st.sidebar.selectbox("Select Currency", CURRENCY_OPTIONS)
coins_selected = st.sidebar.multiselect("Select Coins", COIN_OPTIONS, default=["bitcoin", "ethereum"])

if not coins_selected:
    st.sidebar.warning("Please select at least one coin.")
    st.stop()

st.sidebar.markdown("### 📅 Historical Price Range")
default_start = datetime.datetime.now() - datetime.timedelta(days=30)
start_date = st.sidebar.date_input("Start Date", value=default_start)
end_date = st.sidebar.date_input("End Date", value=datetime.datetime.now())

if isinstance(start_date, datetime.date) and not isinstance(start_date, datetime.datetime):
    start_date = datetime.datetime.combine(start_date, datetime.time.min)
if isinstance(end_date, datetime.date) and not isinstance(end_date, datetime.datetime):
    end_date = datetime.datetime.combine(end_date, datetime.time.max)

# ----------------------------------------
# MAIN CONTENT
# ----------------------------------------
st.title("🪙 Live Cryptocurrency Market Dashboard")
st.markdown("Real-time data, trends and insights powered by CoinGecko API.")

# FETCH & DISPLAY MARKET DATA
st.header("🔢 Current Market Overview")
try:
    raw_market_data = fetch_market_data(coins_selected, currency)
    market_df = format_market_data(raw_market_data)
    st.dataframe(market_df.set_index("Name"), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💰 Coin Prices")
        fig_price = px.bar(market_df, x="Name", y="Price", color="Price", title="Live Prices")
        st.plotly_chart(fig_price, use_container_width=True)
    with col2:
        st.subheader("📈 24h Change (%)")
        fig_change = px.bar(
            market_df, x="Name", y="24h Change (%)", color="24h Change (%)",
            color_continuous_scale="RdYlGn", title="24 Hour Change"
        )
        st.plotly_chart(fig_change, use_container_width=True)

    download_button_csv(market_df, "live_crypto_data.csv")
    download_button_excel(market_df, "live_crypto_data.xlsx")

except Exception as e:
    st.error("🚫 Failed to load market data.")
    st.text(str(e))

# ----------------------------------------
# HISTORICAL DATA CHARTS
# ----------------------------------------
st.header("📊 Historical Price Trend")
tabs = st.tabs([coin.capitalize() for coin in coins_selected])

for i, coin in enumerate(coins_selected):
    with tabs[i]:
        st.subheader(f"{coin.capitalize()} Price from {start_date.date()} to {end_date.date()}")
        try:
            with st.spinner("Loading historical data..."):
                hist_data = fetch_historical_data(coin, currency, start_date, end_date)
                hist_df = format_complete_historical_data(hist_data)
                if hist_df.empty:
                    st.warning("No historical data available for this range.")
                else:
                     # Line chart
                    fig_line = px.line(
                        hist_df, x="Date", y="Price",
                        title=f"{coin.capitalize()} Historical Price Trend",
                        labels={"Price": f"Price ({currency.upper()})"}
                    )
                    st.plotly_chart(fig_line, use_container_width=True)

                    # Data table
                    with st.expander("📋 Historical Data Table"):
                        st.dataframe(hist_df, use_container_width=True)

                    # Download buttons
                    download_button_csv(hist_df, f"{coin}_historical_data.csv")
                    download_button_excel(hist_df, f"{coin}_historical_data.xlsx")

        except Exception as err:
            st.error(f"Error loading historical data for {coin}:")
            st.code(str(err))

# ----------------------------------------
# MARKET CAP DOMINANCE
# ----------------------------------------
st.header("📌 Market Cap Dominance")
try:
    dominance_data = market_df[["Name", "Market Cap"]].sort_values("Market Cap", ascending=False)
    fig_donut = px.pie(dominance_data, names="Name", values="Market Cap", hole=0.4, title="Market Cap Share")
    st.plotly_chart(fig_donut, use_container_width=True)
except Exception as e:
    st.warning("Could not load market cap dominance data.")
    st.text(str(e))

# ----------------------------------------
# FOOTER
# ----------------------------------------
st.caption("📅 Last updated: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
st.caption("Data Source: CoinGecko API")
