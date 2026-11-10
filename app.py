from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from db import init_db, get_db_connection

app = Flask(__name__)
app.secret_key = 'kunci-rahasia-perpustakaan-petik'

# Inisialisasi basis data saat aplikasi pertama kali berjalan
with app.app_context():
    init_db()


# --- Decorator Hak Akses ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('role') != role:
                flash('Anda tidak memiliki akses ke halaman tersebut.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# --- Rute Utama & Autentikasi ---
@app.route('/')
def index():
    if 'user_id' in session:
        if session['role'] == 'pustakawan':
            return redirect(url_for('dashboard_pustakawan'))
        return redirect(url_for('dashboard_peminjam'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Selamat datang kembali, {user["username"]}!', 'success')
            return redirect(url_for('index'))

        flash('Username atau password salah.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah keluar dari sistem.', 'info')
    return redirect(url_for('login'))


# --- Rute Role: Pustakawan ---
@app.route('/pustakawan')
@login_required
@role_required('pustakawan')
def dashboard_pustakawan():
    conn = get_db_connection()
    books = conn.execute('SELECT * FROM books ORDER BY id DESC').fetchall()

    loans = conn.execute('''
        SELECT loans.id, users.username, books.title, loans.borrow_date, loans.status
        FROM loans
        JOIN users ON loans.user_id = users.id
        JOIN books ON loans.book_id = books.id
        ORDER BY loans.id DESC
    ''').fetchall()

    conn.close()
    return render_template('pustakawan/index.html', books=books, loans=loans)


@app.route('/pustakawan/buku/tambah', methods=['POST'])
@login_required
@role_required('pustakawan')
def tambah_buku():
    title = request.form['title']
    author = request.form['author']
    category = request.form['category']
    stock = int(request.form['stock'])

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO books (title, author, category, stock) VALUES (?, ?, ?, ?)',
        (title, author, category, stock)
    )
    conn.commit()
    conn.close()
    flash('Buku berhasil ditambahkan.', 'success')
    return redirect(url_for('dashboard_pustakawan'))


@app.route('/pustakawan/buku/hapus/<int:id>', methods=['POST'])
@login_required
@role_required('pustakawan')
def hapus_buku(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM books WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Buku berhasil dihapus.', 'success')
    return redirect(url_for('dashboard_pustakawan'))


@app.route('/pustakawan/kembalikan/<int:loan_id>', methods=['POST'])
@login_required
@role_required('pustakawan')
def verifikasi_kembali(loan_id):
    conn = get_db_connection()
    loan = conn.execute('SELECT * FROM loans WHERE id = ?', (loan_id,)).fetchone()

    if loan and loan['status'] == 'dipinjam':
        # Kembalikan stok buku
        conn.execute('UPDATE books SET stock = stock + 1 WHERE id = ?', (loan['book_id'],))
        # Update status peminjaman
        conn.execute(
            "UPDATE loans SET status = 'dikembalikan', return_date = DATE('now') WHERE id = ?",
            (loan_id,)
        )
        conn.commit()
        flash('Buku telah dikembalikan dan stok diperbarui.', 'success')

    conn.close()
    return redirect(url_for('dashboard_pustakawan'))


# --- Rute Role: Peminjam ---
@app.route('/peminjam')
@login_required
@role_required('peminjam')
def dashboard_peminjam():
    conn = get_db_connection()
    books = conn.execute('SELECT * FROM books ORDER BY title ASC').fetchall()

    user_loans = conn.execute('''
        SELECT loans.id, books.title, books.author, loans.borrow_date, loans.return_date, loans.status
        FROM loans
        JOIN books ON loans.book_id = books.id
        WHERE loans.user_id = ?
        ORDER BY loans.id DESC
    ''', (session['user_id'],)).fetchall()

    conn.close()
    return render_template('peminjam/index.html', books=books, loans=user_loans)


@app.route('/peminjam/pinjam/<int:book_id>', methods=['POST'])
@login_required
@role_required('peminjam')
def pinjam_buku(book_id):
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if book and book['stock'] > 0:
        # Kurangi stok buku
        conn.execute('UPDATE books SET stock = stock - 1 WHERE id = ?', (book_id,))
        # Catat peminjaman
        conn.execute('INSERT INTO loans (user_id, book_id) VALUES (?, ?)', (session['user_id'], book_id))
        conn.commit()
        flash(f'Berhasil meminjam buku "{book["title"]}".', 'success')
    else:
        flash('Stok buku tidak tersedia.', 'danger')

    conn.close()
    return redirect(url_for('dashboard_peminjam'))


if __name__ == '__main__':
    app.run(debug=True)