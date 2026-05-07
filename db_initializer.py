import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host= "127.0.0.1",
        port= 3306,
        user= "root",
        password= "123456789",
        database= "flight_game",
    )

def initialize_database(sql_file='initialize_schema.sql'):

    connection = mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="123456789",
        database="flight_game",
    )

    cursor = connection.cursor()

    with open(sql_file, 'r') as file:
        sql_script = file.read()

    for statement in sql_script.split(';'):
        if statement.strip():
            cursor.execute(statement)

    connection.commit()
    connection.close()