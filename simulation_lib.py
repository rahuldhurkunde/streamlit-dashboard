from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import dateutil.relativedelta

class Wallet:
    def __init__(self, initial_capital, contribution_amount, contribution_freq):
        """
        contribution_freq: 'Monthly', 'Quarterly', 'Annually', 'None'
        """
        self.initial_capital = initial_capital
        self.contribution_amount = contribution_amount
        self.contribution_freq = contribution_freq

    def simulate_portfolio(self, price_df):
        """
        Simulates the portfolio value over time given the price history.
        Assumes all capital is invested into the stock immediately.
        
        price_df: DataFrame with 'Date' and 'Price'.
        Returns: DataFrame with 'Date', 'Portfolio Value', 'Invested Capital'
        """
        df = price_df.copy()
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').reset_index(drop=True)
        
        portfolio_values = []
        invested_capital_values = []
        
        current_shares = 0.0
        total_invested = 0.0
        
        # Determine contribution dates
        start_date = df['Date'].iloc[0]
        next_contribution_date = self._get_next_contribution_date(start_date, start_date)
        
        # Initial Investment
        initial_price = df['Price'].iloc[0]
        if initial_price > 0:
            current_shares += self.initial_capital / initial_price
            total_invested += self.initial_capital
        
        for idx, row in df.iterrows():
            current_date = row['Date']
            price = row['Price']
            
            # Check for contributions
            # We add contribution if current_date >= next_contribution_date
            # But strictly speaking we should only add it once per period. 
            # Simple logic: if today matches or passes the scheduled date, and we haven't contributed for this 'slot' yet.
            # Simplified: If current_date >= next_contribution_date
            
            if self.contribution_freq != 'None' and current_date >= next_contribution_date:
                # Invest contribution
                if price > 0:
                    current_shares += self.contribution_amount / price
                    total_invested += self.contribution_amount
                
                # Advance next contribution date
                next_contribution_date = self._get_next_contribution_date(start_date, next_contribution_date)
                
                # Handle case where gaps in data might make us skip multiple contributions? 
                # For now, let's assume simple one-step advance. 
                # If there's a huge gap, we might miss contributions, but for stock data usually gaps are just weekends/holidays.
                # If the gap is huge, we should probably add all missed contributions.
                # Let's keep it simple: one contribution per trigger.
            
            portfolio_value = current_shares * price
            portfolio_values.append(portfolio_value)
            invested_capital_values.append(total_invested)
            
        result = pd.DataFrame({
            'Date': df['Date'],
            'Portfolio Value': portfolio_values,
            'Invested Capital': invested_capital_values
        })
        return result

    def _get_next_contribution_date(self, start_date, last_date):
        if self.contribution_freq == 'Monthly':
            return last_date + dateutil.relativedelta.relativedelta(months=1)
        elif self.contribution_freq == 'Quarterly':
            return last_date + dateutil.relativedelta.relativedelta(months=3)
        elif self.contribution_freq == 'Annually':
            return last_date + dateutil.relativedelta.relativedelta(years=1)
        else:
            return last_date + timedelta(days=36500) # Far future

class PredictionModel(ABC):
    @abstractmethod
    def train(self, dates, prices):
        """
        dates: array-like of datetime objects or ordinal
        prices: array-like of float
        """
        pass

    @abstractmethod
    def predict(self, future_dates):
        """
        future_dates: array-like of datetime objects
        Returns: (predictions, lower_bound, upper_bound)
        """
        pass

class LinearRegressionPredictor(PredictionModel):
    def __init__(self):
        self.model = LinearRegression()
        self.std_dev = 0.0

    def train(self, dates, prices):
        # Convert dates to ordinal for regression
        dates_ord = np.array([d.toordinal() for d in dates]).reshape(-1, 1)
        self.model.fit(dates_ord, prices)
        
        # Calculate standard deviation of residuals for uncertainty
        predictions = self.model.predict(dates_ord)
        residuals = prices - predictions
        self.std_dev = np.std(residuals)

    def predict(self, future_dates):
        dates_ord = np.array([d.toordinal() for d in future_dates]).reshape(-1, 1)
        predictions = self.model.predict(dates_ord)
        
        # Simple uncertainty: +/- 2 std devs (approx 95% CI)
        lower_bound = predictions - (2 * self.std_dev)
        upper_bound = predictions + (2 * self.std_dev)
        
        return predictions, lower_bound, upper_bound

# Factory or Manager
class SimulationBackend:
    def __init__(self):
        self.models = {
            "Linear Regression": LinearRegressionPredictor
        }

    def get_model(self, model_name):
        if model_name in self.models:
            return self.models[model_name]()
        raise ValueError(f"Model {model_name} not found.")

