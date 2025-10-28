import backtrader as bt
import pandas as pd

class BollingerWilliamsStrategy(bt.Strategy):
    params = (
        ('boll_period', 20),      # 布林带周期
        ('boll_dev', 2),          # 布林带标准差倍数
        ('will_period', 14),      # 威廉指标周期
        ('contraction_threshold', 0.1),  # 布林带收缩阈值
        ('swing_lookback', 5),    # 寻找拐点的回顾周期
    )
    
    def __init__(self):
        # 布林带指标
        self.bollinger = bt.indicators.BollingerBands(
            self.datas[0], 
            period=self.params.boll_period,
            devfactor=self.params.boll_dev
        )
        
        # 威廉指标
        self.williams = bt.indicators.WilliamsR(
            self.datas[0],
            period=self.params.will_period
        )
        
        # 计算布林带宽度（用于识别收缩）
        self.boll_width = (self.bollinger.lines.top - self.bollinger.lines.bot) / self.bollinger.lines.mid
        
        # 记录布林带收缩状态
        self.contraction_detected = False
        self.contraction_start = None
        
        # 交易状态变量
        self.entry_price = 0
        self.initial_stop = 0
        self.trailing_stop = 0
        self.swing_point = 0
        self.trend_direction = 0  # 1: 多头, -1: 空头, 0: 无趋势
        
        # 用于寻找拐点的数据
        self.highs = []
        self.lows = []
        
    def log(self, txt, dt=None):
        '''日志函数'''
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')
    
    def is_bollinger_contraction(self):
        """判断布林带是否收缩"""
        if len(self.boll_width) < 2:
            return False
        
        # 布林带宽度小于阈值且持续收缩
        current_width = self.boll_width[0]
        prev_width = self.boll_width[-1]
        
        return current_width < self.params.contraction_threshold and current_width < prev_width
    
    def find_swing_point(self):
        """寻找最近的拐点"""
        if len(self.datas[0].close) < self.params.swing_lookback + 1:
            return None, None
        
        # 寻找局部高点和低点
        highs = []
        lows = []
        
        for i in range(-self.params.swing_lookback, 1):
            current_high = self.datas[0].high[i]
            current_low = self.datas[0].low[i]
            
            # 检查是否是局部高点
            is_high = True
            for j in range(max(-len(self.datas[0].high), i-2), min(0, i+3)):
                if j != i and self.datas[0].high[j] >= current_high:
                    is_high = False
                    break
            
            if is_high:
                highs.append((i, current_high))
            
            # 检查是否是局部低点
            is_low = True
            for j in range(max(-len(self.datas[0].low), i-2), min(0, i+3)):
                if j != i and self.datas[0].low[j] <= current_low:
                    is_low = False
                    break
            
            if is_low:
                lows.append((i, current_low))
        
        return highs, lows
    
    def next(self):
        # 确保有足够的数据
        if len(self.datas[0]) < max(self.params.boll_period, self.params.will_period) + 1:
            return
        
        # 检查布林带收缩
        if self.is_bollinger_contraction():
            if not self.contraction_detected:
                self.contraction_detected = True
                self.contraction_start = len(self.datas[0])
                self.log(f'布林带收缩开始, 宽度: {self.boll_width[0]:.4f}')
        
        # 如果布林带不再收缩，重置状态
        elif self.contraction_detected and self.boll_width[0] > self.params.contraction_threshold:
            self.contraction_detected = False
            self.log('布林带收缩结束')
        
        # 寻找拐点
        highs, lows = self.find_swing_point()
        
        # 如果没有持仓且布林带收缩
        if not self.position and self.contraction_detected:
            
            # 多头信号：威廉指标上穿-50
            if (self.williams[-1] <= -50 and self.williams[0] > -50 and 
                self.datas[0].close[0] > self.bollinger.lines.mid[0]):
                
                # 计算初始止损（昨日布林带下轨）
                if len(self.bollinger.lines.bot) > 1:
                    self.initial_stop = self.bollinger.lines.bot[-1]
                    
                    # 进场
                    self.buy()
                    self.entry_price = self.datas[0].close[0]
                    self.trend_direction = 1
                    self.log(f'多头进场, 价格: {self.entry_price:.2f}, 止损: {self.initial_stop:.2f}')
            
            # 空头信号：威廉指标下穿-50
            elif (self.williams[-1] >= -50 and self.williams[0] < -50 and 
                  self.datas[0].close[0] < self.bollinger.lines.mid[0]):
                
                # 计算初始止损（昨日布林带上轨）
                if len(self.bollinger.lines.top) > 1:
                    self.initial_stop = self.bollinger.lines.top[-1]
                    
                    # 进场
                    self.sell()
                    self.entry_price = self.datas[0].close[0]
                    self.trend_direction = -1
                    self.log(f'空头进场, 价格: {self.entry_price:.2f}, 止损: {self.initial_stop:.2f}')
        
        # 持仓中的止损管理
        elif self.position:
            current_price = self.datas[0].close[0]
            
            if self.trend_direction == 1:  # 多头持仓
                # 初始止损阶段
                if self.trailing_stop == 0:
                    stop_loss = self.initial_stop
                else:
                    stop_loss = self.trailing_stop
                
                # 检查是否需要更新跟踪止损
                if lows and len(lows) > 0:
                    latest_low = min([low[1] for low in lows])
                    latest_low_index = max([low[0] for low in lows if low[1] == latest_low])
                    
                    # 如果价格创新高后出现回调低点，更新止损
                    if (current_price > self.entry_price and 
                        latest_low_index > -3 and  # 最近出现的低点
                        latest_low > self.trailing_stop):
                        
                        self.trailing_stop = latest_low
                        self.log(f'更新多头止损到拐点: {self.trailing_stop:.2f}')
                
                # 止损出场
                if current_price <= stop_loss:
                    self.close()
                    self.log(f'多头止损出场, 价格: {current_price:.2f}')
                    self.trend_direction = 0
                    self.trailing_stop = 0
            
            elif self.trend_direction == -1:  # 空头持仓
                # 初始止损阶段
                if self.trailing_stop == 0:
                    stop_loss = self.initial_stop
                else:
                    stop_loss = self.trailing_stop
                
                # 检查是否需要更新跟踪止损
                if highs and len(highs) > 0:
                    latest_high = max([high[1] for high in highs])
                    latest_high_index = max([high[0] for high in highs if high[1] == latest_high])
                    
                    # 如果价格创新低后出现回调高点，更新止损
                    if (current_price < self.entry_price and 
                        latest_high_index > -3 and  # 最近出现的高点
                        latest_high < (self.trailing_stop if self.trailing_stop != 0 else float('inf'))):
                        
                        self.trailing_stop = latest_high
                        self.log(f'更新空头止损到拐点: {self.trailing_stop:.2f}')
                
                # 止损出场
                if current_price >= stop_loss:
                    self.close()
                    self.log(f'空头止损出场, 价格: {current_price:.2f}')
                    self.trend_direction = 0
                    self.trailing_stop = 0

    def notify_trade(self, trade):
        if trade.isclosed:
            self.log(f'交易盈亏, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')

# 回测执行函数
def run_backtest():
    cerebro = bt.Cerebro()
    
    # 添加策略
    cerebro.addstrategy(BollingerWilliamsStrategy)
    
    # 添加数据（这里使用示例数据，请替换为实际数据）
    # 假设我们有一个CSV文件
    data = bt.feeds.YahooFinanceData(
        dataname='AAPL',
        fromdate=pd.to_datetime('2020-01-01'),
        todate=pd.to_datetime('2023-12-31')
    )
    cerebro.adddata(data)
    
    # 设置初始资金
    cerebro.broker.setcash(100000.0)
    
    # 设置手续费
    cerebro.broker.setcommission(commission=0.001)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    print('初始资金: %.2f' % cerebro.broker.getvalue())
    
    # 运行回测
    results = cerebro.run()
    strat = results[0]
    
    # 打印结果
    print('最终资金: %.2f' % cerebro.broker.getvalue())
    print('夏普比率:', strat.analyzers.sharpe.get_analysis())
    print('最大回撤:', strat.analyzers.drawdown.get_analysis())
    print('收益率:', strat.analyzers.returns.get_analysis())
    
    # 绘制图表
    cerebro.plot(style='candlestick')

if __name__ == '__main__':
    run_backtest()