from config import settings


get_message_query = f'''
    SELECT *
    FROM (
        SELECT
            send_date,
            sender,
            receiver, 
            message
        FROM main.messages
        WHERE receiver in ('all', ?)
            AND send_date >= ?
            OR sender = ?
        ORDER BY send_date
    )
    UNION
    SELECT *
    FROM (
        SELECT 
            send_date,
            sender,
            receiver, 
            message
        FROM main.messages
        WHERE receiver in ('all', ?)
            AND send_date <= ?
        ORDER BY send_date
        LIMIT {settings.LIMIT_SHOW_MESSAGES}
    )
    ORDER BY send_date;
'''

store_message_query = '''
    INSERT INTO main.messages(
        message, sender, receiver, send_date)
        VALUES (?, ?, ?, ?);
'''

store_user_query = '''
    INSERT INTO main.registrations(
        username, reg_date)
        VALUES (?, ?);
'''

get_user_query = '''
    SELECT 
        r.username,
        r.reg_date,
        r.count_messages
    FROM main.registrations r
    WHERE r.username = ?;
'''

delete_message_query = f'''
    DELETE FROM main.messages 
    WHERE send_date < ?;
'''

append_count_query = ''' 
    UPDATE main.registrations
    SET count_messages = ?
    WHERE username = ?
'''

reset_limit_query = ''' 
    UPDATE main.registrations
    SET count_messages = 0
'''
