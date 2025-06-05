from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])

# Import the backtrader platform
import backtrader as bt

import itertools
from matplotlib.dates import date2num
import backtrader as bt

class KDJStrategy(bt.Strategy):
    
    params = (
        ('stoc_period', 60),  # KDJ指标的周期
        ('k_period', 20),      # K值的平滑周期
        ('d_period', 20),      # D值的平滑周期
    )
    
    def kdj(self, data, period=None, k_period=None, d_period=None):
        if period is None:
            period = self.params.stoc_period
        if k_period is None:
            k_period = self.params.k_period
        if d_period is None:
            d_period = self.params.d_period

        # 计算9日交易日内最高价
        high_s = bt.ind.Highest(data.high, period=period, plot=False)
        low_s = bt.ind.Lowest(data.low, period=period, plot=False)

        # 计算rsv
        rsv = 100 * bt.DivByZero(
            data.close - low_s,
            high_s - low_s,
            zero=None
        )

        # 计算K值和D值
        K = bt.ind.EMA(rsv, period=k_period, plot=False)
        D = bt.ind.EMA(K, period=d_period, plot=False)
        J = 3 * K - 2 * D
        
        return K, D, J
    
    def __init__(self):
        # 初始化KDJ指标

        self.k1, self.d1, self.j1 = self.kdj(self.datas[0])
        self.k2, self.d2, self.j2 = self.kdj(self.datas[1])

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or bt.num2date(self.datas[0].datetime[0])
        print('{}, {}'.format(dt.isoformat(), txt))

    def next(self):
        hs300 = self.datas[0]
        h30269 = self.datas[1]
        # 获取当前的KDJ值
        k1 = self.k1[0]
        d1 = self.d1[0]
        j1 = self.j1[0]
        k2 = self.k2[0]
        d2 = self.d2[0]
        j2 = self.j2[0]
        # 获取当前的收盘价
        close1 = hs300.close[0]
        close2 = h30269.close[0]
        # 获取当前的持仓
        pos1 = self.getposition(hs300).size
        pos2 = self.getposition(h30269).size
        # 打印当前的KDJ值和收盘价
        self.log(f"HS300 KDJ: K={k1:.2f}, D={d1:.2f}, J={j1:.2f}, Close={close1:.2f}")
        self.log(f"H30269 KDJ: K={k2:.2f}, D={d2:.2f}, J={j2:.2f}, Close={close2:.2f}")
        # 如果沪深300的position为0，且j小于0，将h30269的position平仓并买入沪深300
        if pos1==0 and pos2==0:
            self.buy(h30269, size=int(self.broker.getvalue() / close2))  # 一开始就买入H30269
            return
        
        if j1<0:
            if pos1 ==0:
                if pos2 > 0:
                    self.close(h30269, size=pos2)  # 平掉H30269的仓位
                self.buy(hs300, size=int(self.broker.getvalue() / close1))  # 买入沪深300
        elif j1>=100:
            if pos1 > 0:
                self.close(hs300, size=pos1) # 平掉沪深300的仓位
                self.buy(h30269, size=int(self.broker.getvalue() / close2))  # 买入H30269
        
        
        def notify_order(self, order):
        
            if order.status in [order.Submitted, order.Accepted]:
                return
            
            if order.status == order.Rejected:
                self.log(f"Rejected : order_ref:{order.ref}  data_name:{order.p.data._name}")
                
            if order.status == order.Margin:
                self.log(f"Margin : order_ref:{order.ref}  data_name:{order.p.data._name}")
                
            if order.status == order.Cancelled:
                self.log(f"Concelled : order_ref:{order.ref}  data_name:{order.p.data._name}")
                
            if order.status == order.Partial:
                self.log(f"Partial : order_ref:{order.ref}  data_name:{order.p.data._name}")
            
            if order.status == order.Completed:
                if order.isbuy():
                    self.log(f" BUY : data_name:{order.p.data._name} price : {order.executed.price} , cost : {order.executed.value} , commission : {order.executed.comm}")

                else:  # Sell
                    self.log(f" SELL : data_name:{order.p.data._name} price : {order.executed.price} , cost : {order.executed.value} , commission : {order.executed.comm}")
    
    def notify_trade(self, trade):
        # 一个trade结束的时候输出信息
        if trade.isclosed:
            self.log('closed symbol is : {} , total_profit : {} , net_profit : {}' .format(
                            trade.getdataname(),trade.pnl, trade.pnlcomm))
            # self.trade_list.append([self.datas[0].datetime.date(0),trade.getdataname(),trade.pnl,trade.pnlcomm])
            
        if trade.isopen:
            self.log('open symbol is : {} , price : {} ' .format(
                            trade.getdataname(),trade.price))

        
            


if __name__ == '__main__':
    # Create a cerebro entity
    cerebro = bt.Cerebro()
    cerebro.addstrategy(KDJStrategy)
    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    path300 = os.path.join(modpath, '000300perf.csv')
    path30269 = os.path.join(modpath, 'H30269perf.csv')

    # Create a Data Feed
    data300 = bt.feeds.GenericCSVData(
        dataname=path300,
        dtformat=('%Y%m%d'),
        datetime=0,  # Column 0 is the datetime
        open = 1,  # Column 1 is the open price (not present)
        high = 2,  # Column 2 is the high price (not present)
        low =3,  # Column 3 is the low price (not present)
        openinterest=-1,  # Column 4 is the open interest (not present)
        close=4,  # Column 4 is the close price
        volume=6,  # Column 5 is the volume
        timeframe=bt.TimeFrame.Days
        
    )
    
    data30269 = bt.feeds.GenericCSVData(
        dataname=path30269,
        dtformat=('%Y%m%d'),
        datetime=0,  # Column 0 is the datetime
        open=1,  # Column 1 is the open price
        high=2,  # Column 2 is the high price
        low=3,  # Column 3 is the low price
        close=4,  # Column 4 is the close price
        volume=6,  # Column 5 is the volume
        timeframe=bt.TimeFrame.Days,
    )

    # Add the Data Feed to Cerebro
    cerebro.adddata(data300)
    cerebro.adddata(data30269)
    

    # Set our desired cash start
    cerebro.broker.setcash(1000000.0)
    

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()
    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    
    cerebro.plot()