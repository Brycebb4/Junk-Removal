import sqlite3

class LeadDatabase:
    def __init__(self, db_name="leads.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_lead_table()

    def create_lead_table(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS leads (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT NOT NULL,
                                email TEXT NOT NULL,
                                phone TEXT NOT NULL
                            )''')
        self.connection.commit()

    def add_lead(self, name, email, phone):
        self.cursor.execute('''INSERT INTO leads (name, email, phone)
                              VALUES (?, ?, ?)''', (name, email, phone))
        self.connection.commit()

    def get_leads(self):
        self.cursor.execute('SELECT * FROM leads')
        return self.cursor.fetchall()

    def close(self):
        self.connection.close()