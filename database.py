import sqlite3
from datetime import datetime

class Database:
    def __init__(self, path_to_db='group_accounting.db'):
        self.path_to_db = path_to_db

    @property
    def connection(self):
        return sqlite3.connect(self.path_to_db)

    def execute(self, sql, parameters=(), fetchone=False, fetchall=False, commit=False):
        connection = self.connection
        connection.set_trace_callback(self.logger)
        cursor = connection.cursor()
        data = None
        cursor.execute(sql, parameters)

        if commit:
            connection.commit()
        if fetchone:
            data = cursor.fetchone()
        if fetchall:
            data = cursor.fetchall()

        connection.close()
        return data

    def logger(self, statement):
        print(f'Executing: {statement}')

    def get_participant(self, telegram_id):
        sql = "SELECT * FROM participants WHERE telegram_id = ?"
        return self.execute(sql, (telegram_id,), fetchone=True)

    def add_participant(self, telegram_id, name):
        sql = "INSERT INTO participants (telegram_id, name) VALUES (?, ?)"
        self.execute(sql, (telegram_id, name), commit=True)

    def is_admin(self, telegram_id):
        sql = "SELECT is_admin FROM participants WHERE telegram_id = ?"
        result = self.execute(sql, (telegram_id,), fetchone=True)
        return result and result[0] == 1

    def set_admin(self, telegram_id):
        self.execute("UPDATE participants SET is_admin = 1 WHERE telegram_id = ?", (telegram_id,), commit=True)

    def add_training(self, date, time, location, fee):
        connection = self.connection
        cursor = connection.cursor()
        cursor.execute("INSERT INTO trainings (date, time, location, fee) VALUES (?, ?, ?, ?)", (date, time, location, fee))
        connection.commit()
        training_id = cursor.lastrowid
        self.logger(f"New training_id: {training_id}")
        connection.close()
        return training_id

    def link_poll_to_training(self, training_id, poll_id):
        sql = "INSERT INTO training_polls (training_id, poll_id) VALUES (?, ?)"
        self.execute(sql, (training_id, poll_id), commit=True)

    def get_training_id_by_poll(self, poll_id):
        sql = "SELECT training_id FROM training_polls WHERE poll_id = ?"
        result = self.execute(sql, (poll_id,), fetchone=True)
        return result[0] if result else None

    def update_registration(self, telegram_id, training_id, status):
        participant_id = self.get_participant_id(telegram_id)
        registration = self.execute(
            "SELECT * FROM training_registrations WHERE training_id = ? AND participant_id = ?",
            (training_id, participant_id), fetchone=True
        )
        if registration:
            self.execute(
                "UPDATE training_registrations SET status = ? WHERE id = ?",
                (status, registration[0]), commit=True
            )
        else:
            self.execute(
                "INSERT INTO training_registrations (training_id, participant_id, status) VALUES (?, ?, ?)",
                (training_id, participant_id, status), commit=True
            )

    def get_participant_id(self, telegram_id):
        sql = "SELECT id FROM participants WHERE telegram_id = ?"
        result = self.execute(sql, (telegram_id,), fetchone=True)
        return result[0] if result else None

    def get_training_fee(self, training_id):
        sql = "SELECT fee FROM trainings WHERE id = ?"
        result = self.execute(sql, (training_id,), fetchone=True)
        return result[0] if result else None

    def get_training_date(self, training_id):
        sql = "SELECT date FROM trainings WHERE id = ?"
        result = self.execute(sql, (training_id,), fetchone=True)
        return result[0] if result else None

    def add_payment(self, telegram_id, amount, date=None):
        participant_id = self.get_participant_id(telegram_id)
        if participant_id:
            date = date or datetime.now().strftime('%Y-%m-%d')
            sql = "INSERT INTO payments (participant_id, amount, date) VALUES (?, ?, ?)"
            self.execute(sql, (participant_id, amount, date), commit=True)
            return True
        return False

    def calculate_balance(self, telegram_id):
        participant_id = self.get_participant_id(telegram_id)
        last_initial_balance = self.execute(
            "SELECT balance, date FROM initial_balances WHERE participant_id = ? ORDER BY date DESC LIMIT 1",
            (participant_id,), fetchone=True
        )
        if last_initial_balance:
            initial_balance, initial_date = last_initial_balance
            payments = self.execute(
                "SELECT SUM(amount) FROM payments WHERE participant_id = ? AND date >= ?",
                (participant_id, initial_date), fetchone=True
            )[0] or 0
            balance = initial_balance + payments
        else:
            payments = self.execute(
                "SELECT SUM(amount) FROM payments WHERE participant_id = ?",
                (participant_id,), fetchone=True
            )[0] or 0
            balance = payments
        return balance

    def get_all_balances(self):
        participants = self.execute("SELECT id, name FROM participants", fetchall=True)
        report = ""
        for participant_id, name in participants:
            balance = self.calculate_balance_by_id(participant_id)
            report += f"{name}: {balance:.2f} руб.\n"
        return report

    def calculate_balance_by_id(self, participant_id):
        last_initial_balance = self.execute(
            "SELECT balance, date FROM initial_balances WHERE participant_id = ? ORDER BY date DESC LIMIT 1",
            (participant_id,), fetchone=True
        )
        if last_initial_balance:
            initial_balance, initial_date = last_initial_balance
            payments = self.execute(
                "SELECT SUM(amount) FROM payments WHERE participant_id = ? AND date >= ?",
                (participant_id, initial_date), fetchone=True
            )[0] or 0
            balance = initial_balance + payments
        else:
            payments = self.execute(
                "SELECT SUM(amount) FROM payments WHERE participant_id = ?",
                (participant_id,), fetchone=True
            )[0] or 0
            balance = payments
        return balance

    def set_initial_balance(self, telegram_id, balance):
        participant_id = self.get_participant_id(telegram_id)
        if participant_id:
            sql = "INSERT INTO initial_balances (participant_id, balance, date) VALUES (?, ?, date('now'))"
            self.execute(sql, (participant_id, balance), commit=True)

    def get_all_participants(self):
        sql = "SELECT name, telegram_id FROM participants"
        return self.execute(sql, fetchall=True)

