import mysql.connector
import app_secrets
mysql_db = mysql.connector.connect(
    host=app_secrets.MYSQL_HOST,
    port=app_secrets.MYSQL_PORT,
    user=app_secrets.MYSQL_USER,
    password=app_secrets.MYSQL_PASSWORD
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


