import numpy as np
from collections import namedtuple

OHLC = namedtuple("OHLC", ["open", "high", "low", "close"])

class SimulatedPriceGenerator:
    def __init__(self, starting_price, average_range, std_dev):
        self.current_price = starting_price
        self.average_range = average_range
        self.std_dev = std_dev

    def generate_ohlc(self):
        # Simulate Brownian motion using normally distributed random numbers
        price_change = np.random.normal(scale=self.std_dev)
        self.current_price += price_change

        # Round all the prices to two decimal places
        self.current_price = round(self.current_price, 2)
        high_price = round(self.current_price + self.average_range / 2, 2)
        low_price = round(self.current_price - self.average_range / 2, 2)

        # Calculate OHLC values based on the current price and rounded values
        open_price = self.current_price
        close_price = self.current_price

        # Create a named tuple with OHLC values and return it
        ohlc = OHLC(open=open_price, high=high_price, low=low_price, close=close_price)
        return ohlc

# Example usage:
starting_price = 100.0
average_range = 0.5
std_dev = 0.2

price_generator = SimulatedPriceGenerator(starting_price, average_range, std_dev)

# Generate 10 simulated 1-minute bars
for _ in range(10):
    ohlc = price_generator.generate_ohlc()
    print(ohlc)
    # Access OHLC values with associated price labels
    # print(ohlc.open, ohlc.high, ohlc.low, ohlc.close)

