import numpy as np

def calculate_position_size(portfolio_value, stop_loss_pct, max_risk_pct=1.5):
    """
    Calculates position size using fixed fractional risk management.
    """
    if stop_loss_pct <= 0:
        return 0
    risk_amount = portfolio_value * (max_risk_pct / 100)
    position_size = risk_amount / (stop_loss_pct / 100)
    return min(position_size, portfolio_value)

def get_risk_reward_params(price, stop_loss_pct=7.0, target_pct=10.0):
    stop_loss_price = round(price * (1 - stop_loss_pct / 100), 2)
    take_profit_price = round(price * (1 + target_pct / 100), 2)
    rr_ratio = round(target_pct / stop_loss_pct, 2)
    return stop_loss_price, take_profit_price, rr_ratio
