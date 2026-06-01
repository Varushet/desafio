import psycopg2

conn_str = "dbname=postgres user=postgres password=1234 host=localhost"

try:
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM user_data.users;")
    usuarios = cur.fetchall()
    
    for user in usuarios:
        print(user)
        
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")