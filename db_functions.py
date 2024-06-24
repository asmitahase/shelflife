def add_new_record(connection,table_name,data_dict):
    cur = connection.cursor()
    insert_query = f"INSERT INTO {table_name} ({','.join(data_dict.keys())}) VALUES({','.join(['%s']*len(data_dict))})"
    values = tuple(data_dict.values())
    try:
        cur.execute(insert_query,values)
        connection.commit()
        response = (True, None)
    except connection.Error as error: 
        response = (False, error)
    finally:
        cur.close()
    return response    

def get_all_records(connection, table_name, columns,**sort_orders):
    cur = connection.cursor()
    select_query = f"SELECT {','.join(columns)} FROM {table_name}"
    if sort_orders:
        order_by_clause = ','.join([ ' '.join(item) for item in sort_orders.items()])
        select_query = ' '.join([select_query,'ORDER BY',order_by_clause])
    record_count = cur.execute(select_query)
    records = cur.fetchall()
    cur.close()
    return (record_count,records)

def get_record(connection, table_name, columns, **condition):
    cur = connection.cursor()
    where_clause = [ f"{ column_name }=%s" for column_name in condition ][0]
    select_query = f"SELECT {','.join(columns)} FROM {table_name} WHERE { where_clause }"
    cur.execute(select_query, tuple(condition.values()))
    record = cur.fetchone()
    cur.close()
    return record

def edit_record(connection,table_name, data_dict, **condition):
    cur = connection.cursor()
    set_clause = ','.join([f"{ column_name }=%s" for column_name in data_dict])
    where_clause = ' AND '.join([ f"{ column_name }={ column_value }" for column_name, column_value in condition.items() ])
    update_query = f"UPDATE {table_name} SET { set_clause } WHERE { where_clause }" 
    try:
        cur.execute(update_query,tuple(data_dict.values()))
        connection.commit()
        response = (True,None)
    except connection.Error as error:
        response = (False,error)
    finally:
        cur.close()
    return response

def delete_record(connection,table_name,**condition):
    cur = connection.cursor()
    where_clause = [ f"{column_name}=%s" for column_name in condition ][0]
    delete_query = f"DELETE FROM { table_name } WHERE { where_clause }"
    try:
        cur.execute(delete_query,tuple(condition.values()))
        connection.commit()
        response = (True, None)
    except connection.Error as error:
        response = (False, error)
    finally:
        cur.close()
    return response

def search_string_in_table(connection,table_name,fetch_columns,search_string,search_columns):
    cur = connection.cursor()
    #SELECT book_id,title,authors,publisher,total_count,rented_count,available_count,isbn FROM books WHERE title LIKE %s OR authors LIKE %s OR publisher LIKE %s OR isbn LIKE %s"
    where_clause = ' OR '.join([f"{column} LIKE '%{search_string}%' " for column in search_columns])
    search_query = f"SELECT {','.join(fetch_columns)} FROM {table_name} WHERE { where_clause } "
    search_records_count = cur.execute(search_query)
    search_records = cur.fetchall()
    cur.close()
    return (search_records_count,search_records)

def get_rented_book_data(connection):
    cur = connection.cursor()
    select_query = "SELECT books.renting_cost,transactions.issued_on,members.member_id FROM books INNER JOIN transactions ON books.book_id=transactions.book_id INNER JOIN members ON transactions.member_id=members.member_id WHERE transactions.returned_on IS NULL"
    cur.execute(select_query)
    rented_books = cur.fetchall()
    cur.close()
    return rented_books

def get_completed_transactions(connection):
    cur = connection.cursor()
    select_query = "SELECT books.title,members.name,transactions.issued_on,transactions.returned_on,transactions.amount_paid FROM books INNER JOIN transactions ON books.book_id=transactions.book_id INNER JOIN members ON transactions.member_id=members.member_id WHERE returned_on IS NOT NULL ORDER BY transactions.returned_on DESC"
    cur.execute(select_query)
    transactions = cur.fetchall()
    cur.close()
    return transactions
    
def update_book_count(connection,book_id,action):
    with connection.cursor() as cur:
        if action == 'issue':
            update_query = "UPDATE books SET available_count=available_count-1,rented_count=rented_count+1 WHERE book_id=%s"
        if action == 'return':
            update_query = "UPDATE books SET available_count=available_count+1,rented_count=rented_count-1 WHERE book_id=%s"
        try:
            cur.execute(update_query,(book_id,))
            connection.commit()
            response = (True,None)
        except connection.Error as error:
            response = (False,error)
    return response

def get_books_issued_by_member(connection,member_id):
    with connection.cursor() as cur:
        select_query = "SELECT books.book_id,books.title,books.renting_cost,transactions.issued_on FROM transactions INNER JOIN books ON transactions.book_id=books.book_id WHERE member_id=%s AND transactions.returned_on IS NULL"
        cur.execute(select_query,(member_id,))
        books_issued_by_member = cur.fetchall()
    return books_issued_by_member

def reduce_outstanding_debt(connection,member_id,reduce_by):
    with connection.cursor() as cur:
        update_query = "UPDATE members SET outstanding_debt=outstanding_debt-%s WHERE member_id=%s"
        try:
            cur.execute(update_query,(reduce_by,member_id))
            connection.commit()
            response = (True,None)
        except connection.Error as error:
            response(False,error)
    return response
