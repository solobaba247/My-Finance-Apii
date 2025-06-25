# app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd

# Initialize the Flask app
app = Flask(__name__)
# Enable CORS to allow requests from your Blogspot domain
CORS(app)

# Map our app's intervals to yfinance intervals
YFINANCE_INTERVALS = {
    'Daily': '1d',
    '60min': '60m',
    '30min': '30m',
    '15min': '15m',
    '5min': '5m',
}

# The main API endpoint
@app.route('/get_market_data')
def get_market_data():
    # Get parameters from the request URL (e.g., ?symbol=AAPL&interval=5min)
    symbol = request.args.get('symbol')
    interval_key = request.args.get('interval', 'Daily') # Default to 'Daily' if not provided
    asset_type = request.args.get('assetType', 'STOCKS')

    if not symbol:
        return jsonify({"Error Message": "Stock symbol parameter is required."}), 400

    # Convert our interval name to the yfinance format
    yf_interval = YFINANCE_INTERVALS.get(interval_key)
    if not yf_interval:
        return jsonify({"Error Message": f"Invalid interval: {interval_key}"}), 400
        
    # For Forex, yfinance uses a specific format like "EURUSD=X"
    if asset_type == 'FOREX':
        symbol = f"{symbol.replace('/', '')}=X"

    try:
        # Fetch data using yfinance
        # Use a sensible period for each interval to avoid massive downloads
        period = "1y" # 1 year for daily
        if yf_interval != '1d':
            period = "7d" # 7 days for intraday to get enough data

        data = yf.download(tickers=symbol, period=period, interval=yf_interval)

        if data.empty:
            return jsonify({"Error Message": f"No data found for symbol {symbol} with interval {yf_interval}. It might be a delisted ticker or an invalid interval for this period."}), 404

        # The rest of the JS code expects data in a specific format,
        # similar to Alpha Vantage. We must replicate that format.
        time_series_key = f"Time Series ({interval_key})"
        
        # yfinance gives timezone-aware timestamps. We convert to UTC and format.
        data.index = data.index.tz_convert('UTC')

        # Format the data into the JSON structure our frontend expects
        formatted_data = {}
        for timestamp, row in data.iterrows():
            # Format the timestamp to match what the old API gave
            # e.g., '2023-10-27 15:55:00'
            date_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            formatted_data[date_str] = {
                "1. open": str(row['Open']),
                "2. high": str(row['High']),
                "3. low": str(row['Low']),
                "4. close": str(row['Close']),
                "5. volume": str(row['Volume'])
            }
            
        # The final structure must match the old API response
        response_json = {
            time_series_key: formatted_data,
            "Meta Data": {
                "1. Information": "Market data from yfinance",
                "2. Symbol": symbol,
            }
        }
        
        return jsonify(response_json)

    except Exception as e:
        # Catch any other errors from yfinance or processing
        return jsonify({"Error Message": f"An error occurred: {str(e)}"}), 500

# This allows you to run the server directly for testing
if __name__ == '__main__':
    app.run(debug=True, port=5000)