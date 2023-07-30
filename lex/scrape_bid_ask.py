import requests
from bs4 import BeautifulSoup

def get_bid_ask(symbol):

    def _strip(quote_str):
        ## expecting a string in the form: "price x size", ie.  51.20 x 1000 
        price, volume = [float(x.strip()) for x in quote_str.split('x')]
        return price, volume

    try:
        url = f'https://finance.yahoo.com/quote/{symbol}'

        ## tells the site what browser you are using
        ## to find out this info - just go to google.com and type: 'my user agent'
        headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        ## return price x size, ie.  51.20 x 1000 
        bid_quote = soup.find('td', {'data-test': 'BID-value'}).text
        ask_quote = soup.find('td', {'data-test': 'ASK-value'}).text

        if all([bid_quote, ask_quote]):
            bid_price, bid_volume = _strip(bid_quote)
            ask_price, ask_volume = _strip(ask_quote)
        else:
            bid_price = ask_price = None

        return bid_price, ask_price

    except requests.exceptions.RequestException as e:
        print(e)
        print("Error: Unable to retrieve data. Please check your internet connection.")
        return None, None 
    except Exception as e:
        print(f"Error: {e}")
        return None, None 

if __name__ == "__main__":
    bid_price, ask_price = get_bid_ask('SPY')

    print(f"Bid Price: {bid_price}")
    print(f"Ask Price: {ask_price}")

