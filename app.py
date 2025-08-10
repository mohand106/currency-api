import os
import sqlite3
import requests
from flask import Flask, request, jsonify, redirect, url_for
import stripe

app = Flask(__name__)

# Stripe keys (ضع مفاتيحك هنا أو في Environment Variables)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "ضع_مفتاحك_السري")
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY", "ضع_المفتاح_العام")

# قاعدة بيانات SQLite
DB_FILE = "database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, price REAL DEFAULT 5.0, limit_per_day INTEGER DEFAULT 100)")
    c.execute("SELECT COUNT(*) FROM settings")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO settings (price, limit_per_day) VALUES (?, ?)", (5.0, 100))
    conn.commit()
    conn.close()

init_db()

# API مجاني لجلب سعر العملات
def get_currency_rate(base="USD", target="EUR"):
    url = f"https://api.exchangerate-api.com/v4/latest/{base}"
    r = requests.get(url)
    data = r.json()
    return data.get("rates", {}).get(target, None)

@app.route("/")
def index():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT price, limit_per_day FROM settings LIMIT 1")
    price, limit_per_day = c.fetchone()
    conn.close()
    return f"<h1>خدمة أسعار العملات</h1><p>الخطة الحالية: {limit_per_day} طلب يومياً</p><form action='/create-checkout-session' method='POST'><button type='submit'>ترقية الخطة بـ {price}$</button></form>"

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT price FROM settings LIMIT 1")
    price, = c.fetchone()
    conn.close()

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': 'ترقية الخطة'
                },
                'unit_amount': int(price * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=url_for('success', _external=True),
        cancel_url=url_for('cancel', _external=True),
    )
    return redirect(session.url, code=303)

@app.route("/success")
def success():
    return "✅ تم الدفع بنجاح! خطتك تم ترقيتها."

@app.route("/cancel")
def cancel():
    return "❌ تم إلغاء الدفع."

# لوحة التحكم لتعديل السعر والحد
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        price = float(request.form.get("price"))
        limit_per_day = int(request.form.get("limit_per_day"))
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE settings SET price=?, limit_per_day=? WHERE id=1", (price, limit_per_day))
        conn.commit()
        conn.close()
        return "✅ تم التعديل بنجاح."

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT price, limit_per_day FROM settings LIMIT 1")
    price, limit_per_day = c.fetchone()
    conn.close()
    return f"<h1>لوحة التحكم</h1><form method='POST'>السعر بالدولار: <input type='text' name='price' value='{price}'><br>الحد اليومي: <input type='text' name='limit_per_day' value='{limit_per_day}'><br><button type='submit'>حفظ</button></form>"

# API لاستخدام أسعار العملات
@app.route("/api/rate")
def api_rate():
    base = request.args.get("base", "USD")
    target = request.args.get("target", "EUR")
    rate = get_currency_rate(base, target)
    return jsonify({"base": base, "target": target, "rate": rate})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
