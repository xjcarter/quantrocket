import yfinance as yf

def fetch_1min_data_for_SPY(date):
    # Define the ticker symbol for SPY
    ticker = "SPY"
    
    # Define the date in the format "YYYY-MM-DD"
    start_date = date
    
    # Define the end date (same as start date for 1-minute data)
    end_date = date
    
    # Fetch the historical 1-minute data using yfinance
    data = yf.download(ticker, start=start_date, end=end_date, interval="1m")
    
    return data

# Specify the date for which you want to fetch the data
date_to_fetch = "2023-07-14"

# Fetch the historical 1-minute data for SPY on the specified date
historical_data = fetch_1min_data_for_SPY(date_to_fetch)

# Display the fetched data
print(historical_data)

