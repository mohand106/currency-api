from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
import stripe
import requests
import os

app = Flask(__name__)

# إعداد Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_yourkey")
PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY", "pk_test_yourkey")

# إنشاء قاعدة البيانات إذا لم تكن موجودة
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    price REAL,
                    currency TEXT,
                    requests_limit INTEGER
                )''')
    # خطة افتراضية
    c.execute("INSERT INTO plans (name, price, currency, requests_limit) VALUES (?, ?, ?, ?)", 
              ("Basic Plan", 5.0, "usd", 100))
    conn.commit()
    conn.close()

@app.route('/')
def index():
    # جلب سعر العملة من API مجاني
    try:
        data = requests.get("https://api.exchangerate-api.com/v4/latest/USD").json()
        rate = data['rates'].get("EGP", None)
    except:
        rate = None

    # جلب الخطط من قاعدة البيانات
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM plans")
    plans = c.fetchall()
    conn.close()

    html = '''
    <h1>خطط الاشتراك</h1>
    {% for p in plans %}
        <div style="border:1px solid #ccc; padding:10px; margin:10px;">
            <h3>{{p[1]}}</h3>
            <p>السعر: {{p[2]}} {{p[3]}}</p>
            {% if rate %}<p>بالجنيه: {{ "%.2f"|format(p[2]*rate) }} EGP</p>{% endif %}
            <form action="/checkout/{{p[0]}}" method="POST">
                <button type="submit">اشترك الآن</button>
            </form>
        </div>
    {% endfor %}
    '''
    return render_template_string(html, plans=plans, rate=rate)

@app.route('/checkout/<int:plan_id>', methods=['POST'])
def checkout(plan_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM plans WHERE id=?", (plan_id,))
    plan = c.fetchone()
    conn.close()

    if not plan:
        return "Plan not found", 404

    # إنشاء جلسة دفع Stripe
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': plan[3],
                'product_data': {
                    'name': plan[1],
                },
                'unit_amount': int(plan[2] * 100),  # Stripe uses cents
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.url_root + 'success',
        cancel_url=request.url_root + 'cancel',
    )
    return redirect(session.url, code=303)

@app.route('/success')
def success():
    return "<h1>تم الدفع بنجاح ✅</h1>"

@app.route('/cancel')
def cancel():
    return "<h1>تم إلغاء الدفع ❌</h1>"

if __name__ == '__main__':
    if not os.path.exists('database.db'):
        init_db()
    app.run(debug=True, host='0.0.0.0')
