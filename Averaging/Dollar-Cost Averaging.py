import yfinance as yf  
from enum import Enum
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

class Interval(Enum):
    DAILY = '1d'
    WEEKLY = '1wk'
    MONTHLY = '1mo'
    
    def __str__(self):
        return self.value
    
start_date = "2018-12-01"
end_date = "2024-12-01"
interval = Interval.MONTHLY
amount = 100
outputs = []
tickers = ["QQQ", "QLD", "TQQQ", "VOO", "SSO", "UPRO"]
export_csv = False

# Function to implement dollar-cost averaging
# output layout:
# Date | Shares | Total Shares | Total Value

def dollar_cost_averaging(ticker: str, start_date : str, end_date : str, interval :Interval, amount : int):
    # Download historical data as a pandas DataFrame
    data = yf.download(ticker, start=start_date, end=end_date, interval=interval.value)
    
    output = pd.DataFrame(index=data.index, columns=["Price", "Shares", "Total Shares", "Total Value", "Spend", "Cost", "ROI"], dtype=float)
    
    
    # copy close price to output
    output['Price'] = data['Close']
    
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
    output['ROI'] = round((output['Total Value'] - output['Cost']) / output['Cost'], 2) + 1
   
    # Plot the data
    output_name = start_date + "-" + end_date + " " +  ticker + " " + interval.value
    if(export_csv):
        output.to_csv(output_name + ".csv")
   
    output.Name = output_name
    return output

def quick_dollar_cost_averaging(ticker: str):
    return dollar_cost_averaging(ticker, start_date, end_date, interval, amount)


def display_seprate(data: pd.DataFrame, ax :plt.Axes):
    data.plot(y=["Cost", "Total Value"], title=data.Name, ax=ax)
    
    # Add annotations
    last_date = data.index[-1]
    last_roi = data['ROI'].iloc[-1]
    ax.annotate(f'ROI: {last_roi:.2f}', xy=(last_date, data['Total Value'].iloc[-1]), 
                 xytext=(last_date, data['Total Value'].iloc[-1] + 1000),
                 horizontalalignment='left')

def display_combine(data: pd.DataFrame, ax :plt.Axes, color: str):
    data.plot(y=["Total Value"], title=data.Name, ax=ax, color=color, label=[data.Name])
    
    
    # Add annotations
    last_date = data.index[-1]
    last_roi = data['ROI'].iloc[-1]
    ax.annotate(f'ROI: {last_roi:.2f}', xy=(last_date, data['Total Value'].iloc[-1]), 
                 xytext=(last_date, data['Total Value'].iloc[-1] + 1000),
                 horizontalalignment='left')

# Generate output
for ticker in tickers:
    outputs.append( quick_dollar_cost_averaging(ticker))

# Create the first figure to combine all plots
fig, ax_combine = plt.subplots( figsize=( 11.69,8.27))
colors = ['b', 'g', 'r', 'c', 'm', 'y']  # Different colors for each line
for output, color in zip(outputs, colors):
    display_combine(output, ax_combine, color)
outputs[0].plot(y=["Cost"], ax=ax_combine, color='k', label=["Cost"])
# plt.savefig("Dollar-Cost Averaging combine.png")
plt.savefig("Dollar-Cost Averaging combine.pdf")


# Create a separate figure for each plot
sep_fig = plt.figure(figsize=(11.69*1.75,8.27*1.75))
for i in range(len(outputs)):
    ax = sep_fig.add_subplot(2, 3, i+1)
    display_seprate(outputs[i], ax)

# plt.savefig("Dollar-Cost Averaging separate.png")
plt.savefig("Dollar-Cost Averaging separate.pdf")