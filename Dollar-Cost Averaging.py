import yfinance as yf  
from enum import Enum
import pandas as pd

class Interval(Enum):
    DAILY = '1d'
    WEEKLY = '1wk'
    MONTHLY = '1mo'
    
    def __str__(self):
        return self.value
    


start_date = "2020-01-01"
end_date = "2021-01-01"
interval = Interval.MONTHLY
amount = 1000
ticker = "AAPL"

# Function to implement dollar-cost averaging
# output layout:
# Date | Shares | Total Shares | Total Value

def dollar_cost_averaging(ticker: str, start_date : str, end_date : str, interval :Interval, amount : int):
    # Download historical data as a pandas DataFrame
    data = yf.download(ticker, start=start_date, end=end_date, interval=interval.value)
    
    output = pd.DataFrame(index=data.index, columns=["Shares", "Total Shares", "Total Value", "Spend", "Cost", "Return on Investment"], dtype=float)
    
    
    
    # Calculate the number of shares to buy each time
    output['Shares'] = amount / data['Close']
    
    # Calculate the total number of shares owned
    output['Total Shares'] = output['Shares'].cumsum()
    
    # Calculate the total value of the investment
    output['Total Value'] =  data['Close']
    output['Total Value'] = output['Total Value'] * output['Total Shares']
    
    # Calculate the spend of the investment
    output['Spend'] = amount 
    
    # Calculate the cost of the investment
    output['Cost'] = output['Spend'].cumsum()
    
    # Calculate the return of the investment
    output['Return on Investment'] = (output['Total Value'] - output['Cost'])/output['Cost']
   
    return output

