import sqlite3
from werkzeug.security import generate_password_hash

DATABASE_NAME = "perpustakaan.db"

def get_db_connection():
    """Membuat koneksi ke SQLite dan mengembalikan baris berbasis nama kolom (Row class)."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Membuat tabel jika belum ada dan mengisi data awal (seeding)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Tabel Pengguna (Users)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('pustakawan', 'peminjam'))
        )
    ''')

    # 2. Tabel Buku (Books)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT NOT NULL,
            stock INTEGER NOT NULL DEFAULT 1
        )
    ''')

    # 3. Tabel Peminjaman (Loans)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            borrow_date DATE DEFAULT (DATE('now')),
            return_date DATE,
            status TEXT NOT NULL DEFAULT 'dipinjam' CHECK(status IN ('dipinjam', 'dikembalikan')),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
        )
    ''')

    # Seed Data Pengguna Dummy (jika kosong)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        dummy_users = [
            ('admin', generate_password_hash('admin123'), 'pustakawan'),
            ('siswa1', generate_password_hash('siswa123'), 'peminjam')
        ]
        cursor.executemany(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            dummy_users
        )

    # Seed Data Buku Dummy (jika kosong)
    cursor.execute("SELECT COUNT(*) FROM books")
    if cursor.fetchone()[0] == 0:
        dummy_books = [
            ('Filosofi Teras', 'Henry Manampiring', 'Pengembangan Diri', 5),
            ('Atomic Habits', 'James Clear', 'Self Improvement', 3),
            ('Clean Code', 'Robert C. Martin', 'Pemrograman', 2),
            ('Laskar Pelangi', 'Andrea Hirata', 'Novel', 4)
        ]
        cursor.executemany(
            "INSERT INTO books (title, author, category, stock) VALUES (?, ?, ?, ?)",
            dummy_books
        )

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database perpustakaan.db dan data dummy berhasil dibuat.")