import mysql.connector

mysql_db = mysql.connector.connect(
    host='your mysql host',
    # if you are using your local mysql server comment the port
    port=3306,
    user='your mysql root user name',
    password='your mysql password'
)
cur = mysql_db.cursor()

with open('librarydb.sql','r') as queries:
    for query in queries.read().split(';'):
        try: 
            cur.execute(query.strip())
        except mysql.connector.Error as error:
            print(error)
    mysql_db.commit()

cur.close()


