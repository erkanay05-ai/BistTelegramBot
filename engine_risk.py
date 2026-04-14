def calculate_position(price: float, capital: float, risk_per_trade_pct: float = 1.0, stop_loss_pct: float = None) -> dict:
    risk_amount = capital * (risk_per_trade_pct / 100)
    if stop_loss_pct is None: stop_loss_pct = 5.0
    price_risk = price * (stop_loss_pct / 100)
    if price_risk == 0: return {"error": "Invalid price risk"}
    num_shares = int(risk_amount / price_risk)
    total_cost = num_shares * price
    return {
        "num_shares": num_shares,
        "total_cost": round(total_cost, 2),
        "risk_amount": round(risk_amount, 2),
        "stop_loss_price": round(price - price_risk, 2),
        "stop_loss_pct": stop_loss_pct
    }

def calculate_atr_risk(price: float, atr: float, capital: float, risk_per_trade_pct: float = 1.0, multiplier: float = 2.0) -> dict:
    risk_amount = capital * (risk_per_trade_pct / 100)
    stop_loss_dist = atr * multiplier
    if stop_loss_dist == 0: return {"error": "Invalid ATR"}
    num_shares = int(risk_amount / stop_loss_dist)
    total_cost = num_shares * price
    return {
        "num_shares": num_shares,
        "total_cost": round(total_cost, 2),
        "risk_amount": round(risk_amount, 2),
        "stop_loss_price": round(price - stop_loss_dist, 2),
        "stop_loss_pct": round((stop_loss_dist / price) * 100, 2)
    }
