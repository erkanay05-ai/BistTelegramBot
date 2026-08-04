import os
import json
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bist_bot.db")
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    chat_id = Column(String(50), primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Watchlist(Base):
    __tablename__ = "watchlists"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(50), index=True)
    ticker = Column(String(10), index=True)
    __table_args__ = (UniqueConstraint('chat_id', 'ticker', name='_chat_ticker_uc'),)

class Alarm(Base):
    __tablename__ = "alarms"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(50), index=True)
    ticker = Column(String(10), index=True)
    target = Column(Float)
    condition = Column(String(10))  # 'above' or 'below'
    active = Column(Boolean, default=True)
    created_at = Column(String(50))

class SignalTrack(Base):
    __tablename__ = "signal_tracks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(50), index=True)
    ticker = Column(String(10), index=True)
    active = Column(Boolean, default=True)
    created_at = Column(String(50))
    last_rsi = Column(Float, nullable=True)
    last_macd_diff = Column(Float, nullable=True)
    last_above_sma20 = Column(Boolean, nullable=True)

class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(50), index=True)
    ticker = Column(String(10), index=True)
    quantity = Column(Integer)
    avg_price = Column(Float)
    __table_args__ = (UniqueConstraint('chat_id', 'ticker', name='_chat_portfolio_ticker_uc'),)

class SignalLog(Base):
    """Gonderilen her yonlu sinyalin (Al/Sat) kaydi; isabet oranini olcmek icin."""
    __tablename__ = "signal_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(50), index=True)
    ticker = Column(String(10), index=True)
    signal_type = Column(String(30))   # 'scan' | 'reversal'
    direction = Column(String(20))     # 'Al' | 'Güçlü Al' | 'Sat'
    price_at_signal = Column(Float)
    created_at = Column(String(50), index=True)
    price_5d = Column(Float, nullable=True)
    return_5d_pct = Column(Float, nullable=True)
    checked_5d_at = Column(String(50), nullable=True)
    price_10d = Column(Float, nullable=True)
    return_10d_pct = Column(Float, nullable=True)
    checked_10d_at = Column(String(50), nullable=True)

# Setup database session
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)

def get_session():
    return Session()

def init_db():
    Base.metadata.create_all(engine)
    
    # Run SQLite migration to add missing columns to signal_tracks if they don't exist
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            result = conn.execute(text("PRAGMA table_info(signal_tracks)"))
            columns = [row[1] for row in result.fetchall()]
            if 'last_rsi' not in columns:
                conn.execute(text("ALTER TABLE signal_tracks ADD COLUMN last_rsi REAL"))
            if 'last_macd_diff' not in columns:
                conn.execute(text("ALTER TABLE signal_tracks ADD COLUMN last_macd_diff REAL"))
            if 'last_above_sma20' not in columns:
                conn.execute(text("ALTER TABLE signal_tracks ADD COLUMN last_above_sma20 BOOLEAN"))
    except Exception as e:
        print(f"Migration error for signal_tracks columns: {e}")
        
    # Check if migration is needed
    migrate_from_files()

def migrate_from_files():
    session = get_session()
    try:
        # 1. Migrate Users
        users_file = "users.txt"
        if os.path.exists(users_file):
            with open(users_file, "r") as f:
                chat_ids = [line.strip() for line in f if line.strip()]
            for cid in chat_ids:
                if not session.query(User).filter_by(chat_id=cid).first():
                    session.add(User(chat_id=cid))
            print(f"Migrated {len(chat_ids)} users.")
            # Rename to avoid repeating migration
            try: os.rename(users_file, users_file + ".bak")
            except: pass

        # 2. Migrate Watchlists
        wl_file = "watchlists.json"
        if os.path.exists(wl_file):
            with open(wl_file, "r") as f:
                try: wl_data = json.load(f)
                except: wl_data = {}
            count = 0
            for cid, tickers in wl_data.items():
                for ticker in tickers:
                    if not session.query(Watchlist).filter_by(chat_id=cid, ticker=ticker).first():
                        session.add(Watchlist(chat_id=cid, ticker=ticker))
                        count += 1
            print(f"Migrated {count} watchlist items.")
            try: os.rename(wl_file, wl_file + ".bak")
            except: pass

        # 3. Migrate Alarms
        alarm_file = "alarms.json"
        if os.path.exists(alarm_file):
            with open(alarm_file, "r") as f:
                try: alarm_data = json.load(f)
                except: alarm_data = {}
            count = 0
            for cid, alarms in alarm_data.items():
                for a in alarms:
                    # check duplicate
                    exists = session.query(Alarm).filter_by(
                        chat_id=cid, ticker=a['ticker'], target=a['target'], condition=a['condition']
                    ).first()
                    if not exists:
                        session.add(Alarm(
                            chat_id=cid,
                            ticker=a['ticker'],
                            target=a['target'],
                            condition=a['condition'],
                            active=a.get('active', True),
                            created_at=a.get('created_at', datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
                        ))
                        count += 1
            print(f"Migrated {count} alarms.")
            try: os.rename(alarm_file, alarm_file + ".bak")
            except: pass

        # 4. Migrate Signal Tracks
        st_file = "signal_tracks.json"
        if os.path.exists(st_file):
            with open(st_file, "r") as f:
                try: st_data = json.load(f)
                except: st_data = {}
            count = 0
            for cid, tracks in st_data.items():
                for t in tracks:
                    exists = session.query(SignalTrack).filter_by(chat_id=cid, ticker=t['ticker']).first()
                    if not exists:
                        session.add(SignalTrack(
                            chat_id=cid,
                            ticker=t['ticker'],
                            active=t.get('active', True),
                            created_at=t.get('created_at', datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
                        ))
                        count += 1
            print(f"Migrated {count} signal tracks.")
            try: os.rename(st_file, st_file + ".bak")
            except: pass

        # 5. Migrate Portfolios
        port_file = "portfolios.json"
        if os.path.exists(port_file):
            with open(port_file, "r") as f:
                try: port_data = json.load(f)
                except: port_data = {}
            count = 0
            for cid, holdings in port_data.items():
                for ticker, details in holdings.items():
                    exists = session.query(Portfolio).filter_by(chat_id=cid, ticker=ticker).first()
                    if not exists:
                        session.add(Portfolio(
                            chat_id=cid,
                            ticker=ticker,
                            quantity=details['quantity'],
                            avg_price=details['avg_price']
                        ))
                        count += 1
            print(f"Migrated {count} portfolio holdings.")
            try: os.rename(port_file, port_file + ".bak")
            except: pass

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Migration error: {e}")
    finally:
        session.close()

# User Helpers
def db_add_user(chat_id):
    chat_id = str(chat_id)
    session = get_session()
    try:
        user = session.query(User).filter_by(chat_id=chat_id).first()
        if not user:
            session.add(User(chat_id=chat_id))
            session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def db_get_users():
    session = get_session()
    try:
        users = session.query(User).all()
        return [u.chat_id for u in users]
    finally:
        session.close()

# Watchlist Helpers
def db_get_watchlists():
    session = get_session()
    try:
        wlists = session.query(Watchlist).all()
        result = {}
        for wl in wlists:
            result.setdefault(wl.chat_id, []).append(wl.ticker)
        return result
    finally:
        session.close()

def db_get_user_watchlist(chat_id):
    chat_id = str(chat_id)
    session = get_session()
    try:
        wl = session.query(Watchlist).filter_by(chat_id=chat_id).all()
        return [item.ticker for item in wl]
    finally:
        session.close()

def db_add_to_watchlist(chat_id, ticker):
    chat_id = str(chat_id)
    ticker = ticker.upper()
    session = get_session()
    try:
        exists = session.query(Watchlist).filter_by(chat_id=chat_id, ticker=ticker).first()
        if not exists:
            session.add(Watchlist(chat_id=chat_id, ticker=ticker))
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def db_remove_from_watchlist(chat_id, ticker):
    chat_id = str(chat_id)
    ticker = ticker.upper()
    session = get_session()
    try:
        item = session.query(Watchlist).filter_by(chat_id=chat_id, ticker=ticker).first()
        if item:
            session.delete(item)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

# Alarm Helpers
def db_get_alarms():
    session = get_session()
    try:
        all_alarms = session.query(Alarm).all()
        result = {}
        for a in all_alarms:
            # We map to the dict structure expected in main.py
            alarm_dict = {
                'ticker': a.ticker,
                'target': a.target,
                'condition': a.condition,
                'active': a.active,
                'created_at': a.created_at
            }
            result.setdefault(a.chat_id, []).append(alarm_dict)
        return result
    finally:
        session.close()

def db_get_user_alarms(chat_id):
    chat_id = str(chat_id)
    session = get_session()
    try:
        user_alarms = session.query(Alarm).filter_by(chat_id=chat_id).all()
        return [{
            'ticker': a.ticker,
            'target': a.target,
            'condition': a.condition,
            'active': a.active,
            'created_at': a.created_at
        } for a in user_alarms]
    finally:
        session.close()

def db_add_alarm(chat_id, ticker, target, condition, created_at=None):
    chat_id = str(chat_id)
    ticker = ticker.upper()
    if not created_at:
        created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    session = get_session()
    try:
        exists = session.query(Alarm).filter_by(chat_id=chat_id, ticker=ticker, target=target, condition=condition).first()
        if not exists:
            session.add(Alarm(chat_id=chat_id, ticker=ticker, target=target, condition=condition, active=True, created_at=created_at))
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def db_remove_alarm(chat_id, ticker, target):
    chat_id = str(chat_id)
    ticker = ticker.upper()
    session = get_session()
    try:
        alarms = session.query(Alarm).filter_by(chat_id=chat_id, ticker=ticker, target=target).all()
        if alarms:
            for a in alarms:
                session.delete(a)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def db_deactivate_alarm(chat_id, ticker, target, condition):
    chat_id = str(chat_id)
    ticker = ticker.upper()
    session = get_session()
    try:
        alarm = session.query(Alarm).filter_by(chat_id=chat_id, ticker=ticker, target=target, condition=condition).first()
        if alarm:
            # Instead of setting active=False, we can just delete it, as main.py deletes triggered alarms
            session.delete(alarm)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

# Signal Track Helpers
def db_get_signal_tracks():
    session = get_session()
    try:
        tracks = session.query(SignalTrack).all()
        result = {}
        for t in tracks:
            track_dict = {
                'ticker': t.ticker,
                'active': t.active,
                'created_at': t.created_at,
                'last_rsi': t.last_rsi,
                'last_macd_diff': t.last_macd_diff,
                'last_above_sma20': t.last_above_sma20
            }
            result.setdefault(t.chat_id, []).append(track_dict)
        return result
    finally:
        session.close()

def db_get_user_signal_tracks(chat_id):
    chat_id = str(chat_id)
    session = get_session()
    try:
        tracks = session.query(SignalTrack).filter_by(chat_id=chat_id).all()
        return [{
            'ticker': t.ticker,
            'active': t.active,
            'created_at': t.created_at,
            'last_rsi': t.last_rsi,
            'last_macd_diff': t.last_macd_diff,
            'last_above_sma20': t.last_above_sma20
        } for t in tracks]
    finally:
        session.close()

def db_add_signal_track(chat_id, ticker, created_at=None):
    chat_id = str(chat_id)
    ticker = ticker.upper()
    if not created_at:
        created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    session = get_session()
    try:
        exists = session.query(SignalTrack).filter_by(chat_id=chat_id, ticker=ticker).first()
        if not exists:
            session.add(SignalTrack(chat_id=chat_id, ticker=ticker, active=True, created_at=created_at))
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def db_remove_signal_track(chat_id, ticker):
    chat_id = str(chat_id)
    ticker = ticker.upper()
    session = get_session()
    try:
        track = session.query(SignalTrack).filter_by(chat_id=chat_id, ticker=ticker).first()
        if track:
            session.delete(track)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def db_save_signal_tracks(data):
    session = get_session()
    try:
        for chat_id, user_tracks in data.items():
            chat_id = str(chat_id)
            current_tickers = [t['ticker'].upper() for t in user_tracks]
            
            # Remove any tracks not in current_tickers
            if not current_tickers:
                session.query(SignalTrack).filter_by(chat_id=chat_id).delete(synchronize_session=False)
            else:
                session.query(SignalTrack).filter(
                    SignalTrack.chat_id == chat_id,
                    ~SignalTrack.ticker.in_(current_tickers)
                ).delete(synchronize_session=False)
            
            # Add or update current tracks
            for t in user_tracks:
                ticker = t['ticker'].upper()
                track = session.query(SignalTrack).filter_by(chat_id=chat_id, ticker=ticker).first()
                if track:
                    track.last_rsi = t.get('last_rsi')
                    track.last_macd_diff = t.get('last_macd_diff')
                    track.last_above_sma20 = t.get('last_above_sma20')
                else:
                    session.add(SignalTrack(
                        chat_id=chat_id,
                        ticker=ticker,
                        active=t.get('active', True),
                        created_at=t.get('created_at', datetime.datetime.now().strftime('%Y-%m-%d %H:%M')),
                        last_rsi=t.get('last_rsi'),
                        last_macd_diff=t.get('last_macd_diff'),
                        last_above_sma20=t.get('last_above_sma20')
                    ))
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def db_save_alarms(data):
    session = get_session()
    try:
        for chat_id, user_alarms in data.items():
            chat_id = str(chat_id)
            current_targets = [(a['ticker'].upper(), a['target'], a['condition']) for a in user_alarms]
            
            # Delete alarms for this user that are not in current_targets
            db_alarms = session.query(Alarm).filter_by(chat_id=chat_id).all()
            for dba in db_alarms:
                key = (dba.ticker.upper(), dba.target, dba.condition)
                if key not in current_targets:
                    session.delete(dba)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def db_save_portfolios(data):
    session = get_session()
    try:
        for chat_id, holdings in data.items():
            chat_id = str(chat_id)
            current_tickers = [t.upper() for t in holdings.keys()]
            
            # Remove any holdings not in current_tickers
            if not current_tickers:
                session.query(Portfolio).filter_by(chat_id=chat_id).delete(synchronize_session=False)
            else:
                session.query(Portfolio).filter(
                    Portfolio.chat_id == chat_id,
                    ~Portfolio.ticker.in_(current_tickers)
                ).delete(synchronize_session=False)
            
            # Add or update current holdings
            for ticker, details in holdings.items():
                ticker = ticker.upper()
                item = session.query(Portfolio).filter_by(chat_id=chat_id, ticker=ticker).first()
                if item:
                    item.quantity = details['quantity']
                    item.avg_price = details['avg_price']
                else:
                    session.add(Portfolio(
                        chat_id=chat_id,
                        ticker=ticker,
                        quantity=details['quantity'],
                        avg_price=details['avg_price']
                    ))
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

# Portfolio Helpers
def db_get_portfolios():
    session = get_session()
    try:
        portfolios = session.query(Portfolio).all()
        result = {}
        for p in portfolios:
            result.setdefault(p.chat_id, {})[p.ticker] = {
                'quantity': p.quantity,
                'avg_price': p.avg_price
            }
        return result
    finally:
        session.close()

def db_get_user_portfolio(chat_id):
    chat_id = str(chat_id)
    session = get_session()
    try:
        holdings = session.query(Portfolio).filter_by(chat_id=chat_id).all()
        return {h.ticker: {'quantity': h.quantity, 'avg_price': h.avg_price} for h in holdings}
    finally:
        session.close()

def db_add_portfolio_item(chat_id, ticker, quantity, avg_price):
    chat_id = str(chat_id)
    ticker = ticker.upper()
    session = get_session()
    try:
        item = session.query(Portfolio).filter_by(chat_id=chat_id, ticker=ticker).first()
        if item:
            new_qty = item.quantity + quantity
            new_avg = ((item.quantity * item.avg_price) + (quantity * avg_price)) / new_qty
            item.quantity = new_qty
            item.avg_price = round(new_avg, 2)
            session.commit()
            return item.quantity, item.avg_price
        else:
            session.add(Portfolio(chat_id=chat_id, ticker=ticker, quantity=quantity, avg_price=avg_price))
            session.commit()
            return quantity, avg_price
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def db_remove_portfolio_item(chat_id, ticker, quantity=None):
    chat_id = str(chat_id)
    ticker = ticker.upper()
    session = get_session()
    try:
        item = session.query(Portfolio).filter_by(chat_id=chat_id, ticker=ticker).first()
        if item:
            if quantity is None or quantity >= item.quantity:
                session.delete(item)
                session.commit()
                return 0
            else:
                item.quantity -= quantity
                session.commit()
                return item.quantity
        return -1
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def db_clear_portfolio(chat_id):
    chat_id = str(chat_id)
    session = get_session()
    try:
        items = session.query(Portfolio).filter_by(chat_id=chat_id).all()
        if items:
            for item in items:
                session.delete(item)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

# Signal Log Helpers (isabet oranı / performans takibi)
def db_log_signal(chat_id, ticker, signal_type, direction, price_at_signal, created_at=None):
    chat_id = str(chat_id)
    ticker = ticker.upper()
    if not created_at:
        created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    session = get_session()
    try:
        session.add(SignalLog(
            chat_id=chat_id,
            ticker=ticker,
            signal_type=signal_type,
            direction=direction,
            price_at_signal=price_at_signal,
            created_at=created_at
        ))
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def db_get_signals_due_for_check(window, min_age_days):
    """window: '5d' or '10d'. Henuz o pencerede sonucu kaydedilmemis ve yeterince
    eski (min_age_days gun once ya da daha once olusturulmus) sinyalleri dondurur."""
    price_col = "price_5d" if window == "5d" else "price_10d"
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=min_age_days)).strftime('%Y-%m-%d %H:%M')
    session = get_session()
    try:
        q = session.query(SignalLog).filter(getattr(SignalLog, price_col).is_(None))
        q = q.filter(SignalLog.created_at <= cutoff)
        rows = q.all()
        return [{
            'id': r.id, 'ticker': r.ticker, 'signal_type': r.signal_type,
            'direction': r.direction, 'price_at_signal': r.price_at_signal,
            'created_at': r.created_at
        } for r in rows]
    finally:
        session.close()

def db_set_signal_result(log_id, window, price, return_pct):
    session = get_session()
    try:
        row = session.query(SignalLog).filter_by(id=log_id).first()
        if row:
            now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            if window == "5d":
                row.price_5d = price
                row.return_5d_pct = return_pct
                row.checked_5d_at = now_str
            else:
                row.price_10d = price
                row.return_10d_pct = return_pct
                row.checked_10d_at = now_str
            session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def db_get_performance_summary():
    """Sinyal tipi + yone gore ozetlenmis, gerceklesmis (5 gunu dolmus) getiri istatistigi."""
    session = get_session()
    try:
        rows = session.query(SignalLog).filter(SignalLog.return_5d_pct.isnot(None)).all()
        groups = {}
        for r in rows:
            key = (r.signal_type, r.direction)
            groups.setdefault(key, []).append(r)
        summary = []
        for (signal_type, direction), items in groups.items():
            n = len(items)
            avg_5d = sum(i.return_5d_pct for i in items) / n
            is_short = direction == 'Sat'
            wins = sum(1 for i in items if (i.return_5d_pct < 0 if is_short else i.return_5d_pct > 0))
            win_rate = wins / n * 100
            with_10d = [i for i in items if i.return_10d_pct is not None]
            avg_10d = (sum(i.return_10d_pct for i in with_10d) / len(with_10d)) if with_10d else None
            summary.append({
                'signal_type': signal_type,
                'direction': direction,
                'n': n,
                'avg_return_5d_pct': round(avg_5d, 2),
                'win_rate_5d_pct': round(win_rate, 1),
                'avg_return_10d_pct': round(avg_10d, 2) if avg_10d is not None else None,
                'n_10d': len(with_10d)
            })
        summary.sort(key=lambda s: s['n'], reverse=True)
        return summary
    finally:
        session.close()

def db_get_pending_signal_count():
    session = get_session()
    try:
        return session.query(SignalLog).filter(SignalLog.return_5d_pct.is_(None)).count()
    finally:
        session.close()
