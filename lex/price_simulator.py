import numpy as np
from collections import namedtuple

OHLC = namedtuple("OHLC", ["open", "high", "low", "close"])

class SimulatedPriceGenerator:
    def __init__(self, starting_price, average_range, std_dev):
        self.current_price = starting_price
        self.average_range = average_range
        self.std_dev = std_dev
        self.current_ohlc = None
        self.has_ohlc = False

    def _range_selector(self, a, b):
        import random

        if a >= b:
            raise ValueError("Invalid range. A must be less than B.")

        selected_number = random.uniform(a, b)
        return selected_number

    def generate_ohlc(self):
        # Simulate Brownian motion using normally distributed random numbers
        price_change = np.random.normal(scale=self.std_dev)
        self.current_price += price_change

        # Round all the prices to two decimal places
        self.current_price = round(self.current_price, 2)
        high_price = round(self.current_price + self.average_range / 2, 2)
        low_price = round(self.current_price - self.average_range / 2, 2)

        # Calculate OHLC values based on the current price and rounded values
        open_price = round(self._range_selector(low_price, high_price), 2) 
        close_price = self.current_price

        # Create a named tuple with OHLC values and return it
        ohlc = OHLC(open=open_price, high=high_price, low=low_price, close=close_price)
        self.current_ohlc = ohlc
        self.has_ohlc = True
        return ohlc

    def get_current_price(self):
        v = self.generate_ohlc()
        return v.close


class FirstLastPriceGenerator:
    def __init__(self, starting_price, ending_price):
        self.starting_price = starting_price
        self.ending_price = ending_price 
        self.average_range = starting_price/10.0
        self.current_ohlc = None
        self.has_ohlc = False

    def _range_selector(self, a, b):
        import random

        if a >= b:
            raise ValueError("Invalid range. A must be less than B.")

        selected_number = random.uniform(a, b)
        return selected_number

    def generate_ohlc(self):
        if self.has_ohlc == False:
            self.current_price = self.starting_price
        else:
            self.current_price = self.ending_price

        # Round all the prices to two decimal places
        high_price = round(self.current_price + self.average_range / 2, 2)
        low_price = round(self.current_price - self.average_range / 2, 2)

        # Calculate OHLC values based on the current price and rounded values
        open_price = round(self._range_selector(low_price, high_price), 2) 
        close_price = self.current_price

        # Create a named tuple with OHLC values and return it
        ohlc = OHLC(open=open_price, high=high_price, low=low_price, close=close_price)
        self.current_ohlc = ohlc
        self.has_ohlc = True
        return ohlc

    def get_current_price(self):
        v = self.generate_ohlc()
        return v.close

if __name__ == "__main__":
    # Example usage:
    starting_price = 100.0
    ending_price = 111.0
    average_range = 0.5
    std_dev = 0.2

    price_generator = SimulatedPriceGenerator(starting_price, average_range, std_dev)

    # Generate 10 simulated 1-minute bars
    for _ in range(10):
        ohlc = price_generator.generate_ohlc()
        print(ohlc)
        # Access OHLC values with associated price labels
        # print(ohlc.open, ohlc.high, ohlc.low, ohlc.close)

    print("\n")
    print('first-last generator:')
    price_generator = FirstLastPriceGenerator(starting_price, ending_price)
    for _ in range(10):
        ohlc = price_generator.generate_ohlc()
        print(ohlc)
        # Access OHLC values with associated price labels
        # print(ohlc.open, ohlc.high, ohlc.low, ohlc.close)
