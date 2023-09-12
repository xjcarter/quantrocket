
def avg_price(curr_pos, curr_price, fill_pos, fill_price):
    tot = curr_pos + fill_pos
    v = (curr_pos * curr_price) + (fill_pos * fill_price)
    return v/tot

