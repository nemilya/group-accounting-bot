import sqlite3

def initialize_db():
    conn = sqlite3.connect('group_accounting.db')
    cursor = conn.cursor()

    with open('database_setup.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()

    cursor.executescript(sql_script)
    conn.commit()
    conn.close()

if __name__ == '__main__':
    initialize_db()

