from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'library_secret_key'

# ---------- Database Setup ----------
def init_db():
    with sqlite3.connect('library.db') as conn:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT UNIQUE,
                password TEXT,
                role TEXT
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                author TEXT,
                isbn TEXT,
                category TEXT,
                total_copies INTEGER,
                available_copies INTEGER
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS borrowed_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                book_id INTEGER,
                borrow_date TEXT,
                due_date TEXT,
                return_date TEXT,
                returned INTEGER DEFAULT 0,
                fine REAL DEFAULT 0.0
            )
        ''')

# ---------- Admin Account Creation ----------
def create_admin():
    with sqlite3.connect('library.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", ('admin@library.com',))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                        ('Admin', 'admin@library.com', 'admin123', 'admin'))
            conn.commit()
            print("✅ Admin user created: admin@library.com / admin123")
        else:
            print("ℹ️ Admin already exists.")

init_db()
create_admin()

# ---------- Routes ----------
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = 'student'
        with sqlite3.connect('library.db') as conn:
            try:
                conn.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                             (name, email, password, role))
            except:
                pass
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        with sqlite3.connect('library.db') as conn:
            user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password)).fetchone()
        if user:
            session['user_id'] = user[0]
            session['role'] = user[4]
            if user[4] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------- Admin Routes ----------
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    with sqlite3.connect('library.db') as conn:
        books = conn.execute("SELECT * FROM books").fetchall()
    return render_template('admin_dashboard.html', books=books)

@app.route('/admin/add_book', methods=['POST'])
def add_book():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    data = (request.form['title'], request.form['author'], request.form['isbn'],
            request.form['category'], request.form['copies'], request.form['copies'])
    with sqlite3.connect('library.db') as conn:
        conn.execute("INSERT INTO books (title, author, isbn, category, total_copies, available_copies) VALUES (?, ?, ?, ?, ?, ?)", data)
    return redirect(url_for('admin_dashboard'))

# ---------- Student Routes ----------
@app.route('/student/dashboard')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    with sqlite3.connect('library.db') as conn:
        books = conn.execute("SELECT * FROM books WHERE available_copies > 0").fetchall()
    return render_template('student_dashboard.html', books=books)

@app.route('/borrow/<int:book_id>')
def borrow_book(book_id):
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    student_id = session['user_id']
    borrow_date = datetime.now()
    due_date = borrow_date + timedelta(days=7)
    with sqlite3.connect('library.db') as conn:
        conn.execute("INSERT INTO borrowed_books (student_id, book_id, borrow_date, due_date) VALUES (?, ?, ?, ?)",
                     (student_id, book_id, borrow_date.strftime('%Y-%m-%d'), due_date.strftime('%Y-%m-%d')))
        conn.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id = ?", (book_id,))
    return redirect(url_for('student_dashboard'))

@app.route('/mybooks')
def my_books():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    student_id = session['user_id']
    with sqlite3.connect('library.db') as conn:
        books = conn.execute('''
            SELECT b.title, bb.borrow_date, bb.due_date, bb.returned
            FROM borrowed_books bb
            JOIN books b ON bb.book_id = b.id
            WHERE bb.student_id = ?
        ''', (student_id,)).fetchall()
    return render_template('mybooks.html', books=books)

if __name__ == '__main__':
    app.run(debug=True)