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

    yf_interval = YFINANCE_INTERVALS.get(interval_key)
    if not yf_interval:
        return jsonify({"Error Message": f"Invalid interval: {interval_key}"}), 400
        
    if asset_type == 'FOREX':
        symbol = f"{symbol.replace('/', '')}=X"

    try:
        period = "1y" # 1 year for daily
        # For intraday, yfinance can only provide up to 60 days of history
        if yf_interval != '1d':
            period = "60d" 

        data = yf.download(tickers=symbol, period=period, interval=yf_interval)

        if data.empty:
            return jsonify({"Error Message": f"No data found for symbol {symbol} with interval {yf_interval}. It might be a delisted ticker or an invalid interval for this period."}), 404

        # ======================================================================== #
        # === FIX IS HERE: Robustly handle timezone-naive and timezone-aware data === #
        # ======================================================================== #
        # The goal is to ensure all timestamps are in UTC before we process them.
        
        if data.index.tz is None:
            # If the index is "naive" (no timezone), we must first 'localize' it.
            # We assume UTC as the standard timezone for naive timestamps.
            data = data.tz_localize('UTC')
        else:
            # If it's already "aware" (has a timezone), just convert it to UTC.
            data = data.tz_convert('UTC')
        
        # Now, data.index is guaranteed to be timezone-aware and in UTC.

        time_series_key = f"Time Series ({interval_key})"
        
        formatted_data = {}
        for timestamp, row in data.iterrows():
            date_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            formatted_data[date_str] = {
                "1. open": str(row['Open']),
                "2. high": str(row['High']),
                "3. low": str(row['Low']),
                "4. close": str(row['Close']),
                "5. volume": str(row['Volume'])
            }
            
        response_json = {
            time_series_key: formatted_data,
            "Meta Data": {
                "1. Information": "Market data from yfinance",
                "2. Symbol": symbol,
            }
        }
        
        return jsonify(response_json)

    except Exception as e:
        return jsonify({"Error Message": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
