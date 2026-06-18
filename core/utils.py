import datetime
import pytz

def get_istanbul_now():
    tz = pytz.timezone('Europe/Istanbul')
    return datetime.datetime.now(tz)

def format_timestamp(dt):
    return dt.strftime('%Y-%m-%d %H:%M')
