import os, sqlite3, json
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "store.db"))
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Galoulcabba124@")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name_ar TEXT NOT NULL, name_en TEXT NOT NULL,
        description_ar TEXT DEFAULT '', description_en TEXT DEFAULT '', category TEXT DEFAULT 'computer',
        price INTEGER NOT NULL DEFAULT 0, stock INTEGER NOT NULL DEFAULT 0, image_url TEXT DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT NOT NULL, phone TEXT NOT NULL,
        address TEXT DEFAULT '', items_json TEXT NOT NULL, total INTEGER NOT NULL,
        notes TEXT DEFAULT '', status TEXT DEFAULT 'New', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS service_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT NOT NULL, phone TEXT NOT NULL,
        device TEXT NOT NULL, issue TEXT NOT NULL, city TEXT DEFAULT '', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS used_device_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT NOT NULL, phone TEXT NOT NULL,
        device TEXT NOT NULL, condition_text TEXT DEFAULT '', expected_price INTEGER DEFAULT 0,
        city TEXT DEFAULT '', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        sample = [
            ("حاسوب محمول مستعمل","Used Laptop","جهاز مستعمل بحالة جيدة. عدّل التفاصيل والسعر قبل البيع.","Pre-owned laptop in good condition. Update details and price before selling.","laptop",45000,3,""),
            ("حاسوب مكتبي","Desktop Computer","حاسوب مكتبي للاستخدام اليومي والعمل.","Desktop PC for everyday work and productivity.","desktop",65000,2,""),
            ("قرص SSD","SSD Storage","ترقية سريعة لتحسين أداء الكمبيوتر.","A fast upgrade to improve computer performance.","parts",7500,5,""),
            ("ذاكرة RAM","RAM Memory","ذاكرة إضافية لتحسين تعدد المهام.","Extra memory to improve multitasking.","parts",5500,6,"")
        ]
        conn.executemany("INSERT INTO products (name_ar,name_en,description_ar,description_en,category,price,stock,image_url) VALUES (?,?,?,?,?,?,?,?)", sample)
    conn.commit()
    conn.close()

init_db()

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_globals():
    return {"cart_count": sum(int(v) for v in session.get("cart", {}).values())}

@app.route("/")
def home():
    conn = db()
    products = conn.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC LIMIT 8").fetchall()
    conn.close()
    return render_template("index.html", products=products)

@app.route("/shop")
def shop():
    category = request.args.get("category", "")
    conn = db()
    if category:
        products = conn.execute("SELECT * FROM products WHERE active=1 AND category=? ORDER BY id DESC", (category,)).fetchall()
    else:
        products = conn.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("shop.html", products=products, category=category)

@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    conn = db()
    product = conn.execute("SELECT id,stock,active FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    if not product or not product["active"]:
        abort(404)
    cart = session.get("cart", {})
    key = str(product_id)
    cart[key] = min(int(cart.get(key, 0)) + 1, max(1, product["stock"]))
    session["cart"] = cart
    flash("تمت إضافة المنتج إلى السلة / Added to cart.")
    return redirect(request.referrer or url_for("shop"))

@app.route("/cart")
def cart():
    cart_data = session.get("cart", {})
    items, total = [], 0
    conn = db()
    for pid, qty in cart_data.items():
        p = conn.execute("SELECT * FROM products WHERE id=? AND active=1", (pid,)).fetchone()
        if p:
            line_total = p["price"] * int(qty)
            items.append({"product": p, "qty": int(qty), "line_total": line_total})
            total += line_total
    conn.close()
    return render_template("cart.html", items=items, total=total)

@app.post("/update-cart")
def update_cart():
    new_cart = {}
    for key, value in request.form.items():
        if key.startswith("qty_"):
            pid = key[4:]
            try:
                qty = max(0, min(99, int(value)))
            except ValueError:
                qty = 0
            if qty:
                new_cart[pid] = qty
    session["cart"] = new_cart
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart_data = session.get("cart", {})
    items, total = [], 0
    conn = db()
    for pid, qty in cart_data.items():
        p = conn.execute("SELECT * FROM products WHERE id=? AND active=1", (pid,)).fetchone()
        if p:
            line_total = p["price"] * int(qty)
            items.append({"product": p, "qty": int(qty), "line_total": line_total})
            total += line_total
    if request.method == "POST":
        name, phone = request.form.get("customer_name","").strip(), request.form.get("phone","").strip()
        if not items:
            flash("سلة المشتريات فارغة / Your cart is empty.")
        elif not name or not phone:
            flash("يرجى إدخال الاسم ورقم الهاتف / Enter your name and phone.")
        else:
            conn.execute("INSERT INTO orders (customer_name,phone,address,items_json,total,notes) VALUES (?,?,?,?,?,?)",
                         (name, phone, request.form.get("address","").strip(),
                          json.dumps([{"id":i["product"]["id"],"name_ar":i["product"]["name_ar"],"name_en":i["product"]["name_en"],"qty":i["qty"],"price":i["product"]["price"]} for i in items], ensure_ascii=False),
                          total, request.form.get("notes","").strip()))
            conn.commit()
            conn.close()
            session["cart"] = {}
            flash("تم استلام طلبك. سنتواصل معك لتأكيده. / Order received. We will contact you to confirm.")
            return redirect(url_for("home"))
    conn.close()
    return render_template("checkout.html", items=items, total=total)

@app.route("/services", methods=["GET", "POST"])
def services():
    if request.method == "POST":
        data = [request.form.get(k,"").strip() for k in ("customer_name","phone","device","issue")]
        if all(data):
            conn = db()
            conn.execute("INSERT INTO service_requests (customer_name,phone,device,issue,city) VALUES (?,?,?,?,?)",
                         (*data, request.form.get("city","").strip()))
            conn.commit()
            conn.close()
            flash("تم إرسال طلب الصيانة بنجاح. / Repair request sent.")
            return redirect(url_for("services"))
        flash("يرجى ملء جميع الحقول المطلوبة / Please complete all required fields.")
    return render_template("services.html")

@app.route("/sell-used", methods=["GET", "POST"])
def sell_used():
    if request.method == "POST":
        name, phone, device = (request.form.get(k,"").strip() for k in ("customer_name","phone","device"))
        if name and phone and device:
            try:
                price = max(0, int(request.form.get("expected_price","0") or 0))
            except ValueError:
                price = 0
            conn = db()
            conn.execute("INSERT INTO used_device_requests (customer_name,phone,device,condition_text,expected_price,city) VALUES (?,?,?,?,?,?)",
                         (name, phone, device, request.form.get("condition_text","").strip(), price, request.form.get("city","").strip()))
            conn.commit()
            conn.close()
            flash("تم إرسال عرضك، سنتواصل معك. / Offer sent. We will contact you.")
            return redirect(url_for("sell_used"))
        flash("يرجى ملء الاسم والهاتف ونوع الجهاز. / Please fill in name, phone and device.")
    return render_template("sell_used.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username","")
        password = request.form.get("password","")
        if username == ADMIN_USER and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        flash("بيانات الدخول غير صحيحة / Invalid login.")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("home"))

@app.route("/admin")
@admin_required
def admin():
    conn = db()
    products = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 100").fetchall()
    repairs = conn.execute("SELECT * FROM service_requests ORDER BY id DESC LIMIT 100").fetchall()
    used = conn.execute("SELECT * FROM used_device_requests ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()
    return render_template("admin.html", products=products, orders=orders, repairs=repairs, used=used)

@app.route("/admin/products", methods=["POST"])
@admin_required
def admin_add_product():
    name_ar = request.form.get("name_ar","").strip()
    name_en = request.form.get("name_en","").strip()
    if name_ar and name_en:
        try:
            price = max(0, int(request.form.get("price","0")))
            stock = max(0, int(request.form.get("stock","0")))
        except ValueError:
            price, stock = 0, 0
        conn = db()
        conn.execute("INSERT INTO products (name_ar,name_en,description_ar,description_en,category,price,stock,image_url) VALUES (?,?,?,?,?,?,?,?)",
                     (name_ar,name_en,request.form.get("description_ar",""),request.form.get("description_en",""),
                      request.form.get("category","computer"),price,stock,request.form.get("image_url","").strip()))
        conn.commit()
        conn.close()
        flash("تمت إضافة المنتج / Product added.")
    return redirect(url_for("admin"))

@app.route("/admin/product/<int:product_id>/toggle", methods=["POST"])
@admin_required
def toggle_product(product_id):
    conn = db()
    conn.execute("UPDATE products SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

@app.route("/admin/order/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    status = request.form.get("status","New")
    if status not in ("New","Confirmed","Completed","Cancelled"):
        status = "New"
    conn = db()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
