from datetime import datetime, timedelta
from decimal import Decimal

def get_datetime_interval(datetime_start: datetime, plus_days):
    datetime_end = datetime_start + timedelta(days=float(plus_days))
    return datetime_start, datetime_end

def get_current_datetime_interval(plus_days):
    now = datetime.now()
    return get_datetime_interval(now, plus_days)

def get_timestamp(datetime_obj: datetime, timestamp_type = 'Decimal'):
    timestamp_obj = datetime.timestamp(datetime_obj)
    if timestamp_type == 'int':
        return int(timestamp_obj)
    elif timestamp_type == 'Decimal':
        return Decimal(str(timestamp_obj))
    else:
        return timestamp_obj

def get_current_timestamp(timestamp_type = 'Decimal'):
    current_datetime = datetime.now()
    return get_timestamp(current_datetime, timestamp_type)
    

def timestamp_to_string(timestamp):
    if isinstance(timestamp, Decimal):
        timestamp = int(timestamp)
    if not isinstance(timestamp, int):
        raise Exception('Invalid type of timestamp! Should be either of Decimal or int, but is {} !'.format(type(timestamp)))
    return datetime.fromtimestamp(timestamp).strftime("%m/%d/%Y, %H:%M:%S")

def get_presigned_url_expires_in_maximum_seconds(record_expiration_time):
    remaining_time = int(record_expiration_time) - get_current_timestamp('int')
    if int(remaining_time) < 61:
        raise Exception('Record is expiring! Unable to get presigned URL!')
    return min(604800, remaining_time)