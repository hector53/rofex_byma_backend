import pymysql
from app.pool.poolmysql import ConnectionPool

datos = {
    "host":"localhost",
    "database":"rofex",
    "userDb" : "root",
    "userPass":"",
    "secret_key_login": '65as4d56as4das651ads86'
}

#datos Host para db
host=datos["host"]
database=datos["database"]
userDb = datos["userDb"]
userPass=datos["userPass"]
length_of_string = 8

db_config = {
    'host': host,
    'user': userDb,
    'password': userPass,
    'database': database,
    'autocommit': True
}
pool = ConnectionPool(**db_config, maxsize=20)




def register_user(sql, params):
    con = pool.get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(sql, params )
            
            return {"status": 1, "id": cur.lastrowid}
    except pymysql.Error as e:
        print("errrorr", e)
        return {"status": 0, "error": e.args[1]}
    finally:
        con.close()


def insert_many(sql, data):
    con = pool.get_connection()
    try:
        with con.cursor() as cur:
            cur.executemany(sql, data )
            return {"status": 1}
    except pymysql.Error as e:
        print("errrorr", e)
        return {"status": 0, "error": e.args[1]}
    finally:
        con.close()

def insert_data(sql, params):
    con = pool.get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(sql, params )
            
            return {"status": 1, "id": cur.lastrowid}
    except pymysql.Error as e:
        print("errrorr", e)
        return {"status": 0, "error": e.args[1]}
    finally:
        con.close()

def verificar_email(email, sql):
    con = pool.get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(sql, (email) )
            rows = cur.fetchone()
            return rows
    finally:
        con.close()

def getDataOnly(consulta):
    con = pool.get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(consulta)
            rows = cur.fetchall()
            return rows
    finally:
        con.close()


def getData(consulta, params):
    con = pool.get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(consulta, params)
            rows = cur.fetchall()
            return rows
    finally:
        con.close()
def getDataOne(consulta, params):
    con = pool.get_connection()
    try:
        with con.cursor() as cur:
            cur.execute(consulta, params)
            rows = cur.fetchone()
            return rows
    finally:
        con.close()
def updateData(consulta, params):
    con = pool.get_connection()
    try:
        with con.cursor() as cur:
            guardar = cur.execute(consulta, params)
            
            return cur.lastrowid
    except pymysql.Error as e:
        print("errrorr", e)
        return 0
    finally:
        con.close()

def updateTable(consulta, params):
    con = pool.get_connection()
    try:
        with con.cursor() as cur:
            guardar = cur.execute(consulta, params)
            
            return 1
    except pymysql.Error as e:
        print("errrorr", e)
        return 0
    finally:
        con.close()