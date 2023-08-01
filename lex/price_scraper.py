import requests
from bs4 import BeautifulSoup
from collections import namedtuple

OHLC = namedtuple("OHLC", ["open", "high", "low", "close"])

class PriceSnapper:
    def __init__(self, symbol, bar_length=10):
        self.prices = list()
        self.symbol = symbol
        self.bar_length = bar_length
        self.current_ohlc = None
        self.counter = 0

    def snap_prices(self):

        def _strip(quote_str):
            ## expecting a string in the form: "price x size", ie.  51.20 x 1000 
            price, volume = [float(x.strip()) for x in quote_str.split('x')]
            return price, volume

        try:
            url = f'https://finance.yahoo.com/quote/{self.symbol}'

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
                self.counter += 1

                bid_price, bid_volume = _strip(bid_quote)
                ask_price, ask_volume = _strip(ask_quote)
                self.prices.extend([bid_price, ask_price])

                #self.volume.extend([bid_volume, ask_volume])
                if self.counter >= self.bar_length:
                    close_price = round((bid_price + ask_price)*0.5,2)
                    open_price = round((self.prices[0] + self.prices[1])*0.5,2)
                    high_price = max(self.prices)
                    low_price  = min(self.prices)
                    # Create a named tuple with OHLC values and return it
                    ohlc = OHLC(open=open_price, high=high_price, low=low_price, close=close_price)
                    self.current_ohlc = ohlc

                    self.prices = []
                    self.counter = 0
                    return ohlc                   
                else:
                    return None

        except requests.exceptions.RequestException as e:
            print(e)
            return None 
        except Exception as e:
            print(f"Error: {e}")
            return None 


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
    bid_price, ask_price  = get_bid_ask('SPY')

    print(f"Bid Price: {bid_price}")
    print(f"Ask Price: {ask_price}")

    p = PriceSnapper('SPY')
    print(p.snap_prices())


