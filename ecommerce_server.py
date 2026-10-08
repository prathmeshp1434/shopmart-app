from flask import Flask, render_template, request, redirect, url_for,session
from flask_sqlalchemy import SQLAlchemy
import os
import sqlite3
import random
from datetime import datetime
import ssl
from sqlalchemy import text

app = Flask(__name__)
# Database connection string (with local SQLite


# SSL Context (Neon DB ke secure connection ke liye zaroori hai)
ssl_context = ssl.create_default_context()

app.secret_key = os.environ.get('SECRET_KEY', 'my_super_secret_ecom_key_123')

# ---------------------------------------
# DATABASE CONNECTION SETUP
# --------------------------------------------
db_url = os.environ.get('DATABASE_URL')

if db_url:
    # Render par standard 'postgresql://' aata hai, use pg8000 ke liye update karein
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+pg8000://", 1)
    elif db_url.startswith("postgresql://") and "+pg8000" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+pg8000://", 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///local.db'
	
# -------------------------------------------------------------

# ORM initialisation 
db = SQLAlchemy(app)

class User(db.Model):
	id= db.Column(db.Integer,primary_key= True)
	mobile= db.Column(db.String(15),unique=True,nullable=False)
	name= db.Column(db.String(50),default='Customer')
	otp= db.Column(db.String(6),nullable=True)
	is_admin= db.Column(db.Boolean,default=False)
	
	def __repr__(self):
		return f"<User{self.mobile}>"

# Database Tables Building

# Table 1: Category
class Category(db.Model):  
    id = db.Column(db.Integer, primary_key=True)  
    name = db.Column(db.String(50), nullable=False, unique=True)  
    products = db.relationship('Product', backref='category', lazy=True)
    
    def __repr__(self):
        return f"<Category {self.name}>"

# Table 2: Product
class Product(db.Model):  # <-- P बड़ा, M बड़ा
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)  # <-- F बड़ा
    stock = db.Column(db.Integer, default=1)
    image_url = db.Column(db.String(500), default='https://via.placeholder.com/300')
    is_active= db.Column(db.Boolean,default=True)
    
    # Foreign Key
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    
    def __repr__(self):
        return f"<Product {self.name}>"
#order save karne ke liye;
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    address = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='orders')
    
    # OrderItem ke saath relationship
    items = db.relationship('OrderItem', backref='order', lazy=True)

# 2. Individual Items inside Order
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False) 
	

# Database tables auto-create
with app.app_context():
    db.create_all()
         

    print("🎉 ")
    

   

@app.route('/')
def home():
    # 1. URL से सर्च क्वेरी निकाली (jaise /?q=phone)
    search_query = request.args.get('q', '')

    if search_query:
        # 2. Agar user ne kuch type kiya hai to filter karke nikalo
        products = Product.query.filter(Product.name.ilike(f'%{search_query}%')).all()
    else:
        # 3. Warna saare products nikalo
        products = Product.query.filter_by(is_active=True).all()
        
        print(f"\n📦 TOTAL PRODUCTS FOUND IN DB: {len(products)}\n")

    return render_template('home.html', products=products, search_query=search_query)

	
#new route today

@app.route('/add_product',methods=['GET','POST'])
def add_products():
	if not session.get('is_admin'):
		return redirect('/')
	if request.method =='POST':
		prod_name=request.form['name']
		prod_price=float(request.form['price'])
		prod_stock=int(request.form['stock'])
		cat_id= int(request.form['category_id'])
		prod_image=request.form.get('image_url')
		
		if not prod_image or not prod_image.strip():
			default_image = 'https://placehold.co/600x400/f1f5f9/475569?text=No+Image+Available'
			
		
		new_product= Product(name=prod_name,price=prod_price,stock=prod_stock,image_url=prod_image,category_id=cat_id)
		db.session.add(new_product)
		db.session.commit()
		print(f"\n✅ PRODUCT SAVED SUCCESSFULLY: {new_product.name} (ID: {new_product.id})\n")
		return redirect(url_for('home'))
	#if get request
	all_categories=Category.query.all()
	return render_template('/add_products.html',categories=all_categories)
		
# --- 🛒 CART ROUTES (Naye Routes) ---
@app.route('/delete-product/<int:product_id>',methods=['POST'])
def delete_product(product_id):
	if not session.get('is_admin'):
		return redirect('/')
	prod=Product.query.get_or_404(product_id)
	prod.is_active=False
	db.session.commit()
	db.session.commit()
	print(f"🗑️ Product {product_id} deleted by Admin!")
	return redirect('/')
	
	
# 1. Product ko Cart me jodhne ke liye
@app.route('/add-to-cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']
    str_id = str(product_id)

    # Agar product pehle se cart me hai to quantity badao, nahi to 1 karo
    cart[str_id] = cart.get(str_id, 0) + 1
    session['cart'] = cart  # Session Update Trigger
    
    return redirect(request.referrer or url_for('home'))


# 2. Cart Page dekhne ke liye (Bill Calculation)
@app.route('/cart')
def view_cart():
    cart = session.get('cart', {})
    cart_items = []
    total_price = 0

    for prod_id_str, qty in cart.items():
        product = Product.query.get(int(prod_id_str))
        if product:
            subtotal = product.price * qty
            total_price += subtotal
            cart_items.append({
                'product': product,
                'quantity': qty,
                'subtotal': subtotal
            })

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)


# 3. Cart Khali (Clear) karne ke liye
@app.route('/clear-cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('view_cart'))
	
@app.route('/remove-from-cart/<int:product_id>')
def remove_from_cart(product_id):
	cart=session.get('cart',{})
	str_id = str(product_id)
	if str_id in cart:
		cart.pop(str_id)
		session['cart']=cart
	return redirect('/cart')
		
# ➕ Quantity बढ़ाने का Route
@app.route('/increase-qty/<int:product_id>')
def increase_qty(product_id):
    cart = session.get('cart', {})
    str_id = str(product_id)
    
    if str_id in cart:
        cart[str_id] += 1        # Quantity 1 से बढ़ा दी
        session['cart'] = cart  # Session अपडेट किया
        
    return redirect('/cart')

# ➖ Quantity घटाने का Route
@app.route('/decrease-qty/<int:product_id>')
def decrease_qty(product_id):
    cart = session.get('cart', {})
    str_id = str(product_id)
    
    if str_id in cart:
        cart[str_id] -= 1        # Quantity 1 से घटा दी
        
        # अगर घटते-घटते Quantity 0 या उससे कम हो जाए, तो आइटम कार्ट से हटा दो
        if cart[str_id] <= 0:
            cart.pop(str_id)
            
        session['cart'] = cart  # Session अपडेट किया
        
    return redirect('/cart')
		
#1. Step 1: Mobile Number Enter karne ka route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mobile = request.form.get('mobile')
        password= request.form.get('otp')
        user = User.query.filter_by(mobile=mobile).first()
        if user and user.otp == password:
            session['user_id'] = user.id
            session['user_mobile']=user.mobile
               
        # User exist karta hai ya nahi check karein, nahi toh naya banayein
        user = User.query.filter_by(mobile=mobile).first()
        if not user:
            user = User(mobile=mobile, name=f"User_{mobile[-4:]}")
            db.session.add(user)
        
        # 6 digit OTP generate karke database me save karein
        otp = str(random.randint(100000, 999999))
        user.otp = otp
        db.session.commit()
        
        # Testing ke liye Terminal me print hoga OTP
        print(f"\n==============================")
        print(f"🔑 OTP FOR {mobile} IS: {otp}")
        print(f"==============================\n")
        
        session['pending_mobile'] = mobile
        return redirect(url_for('verify_otp'))
        
    return render_template('login.html')

# 2. Step 2: OTP Verify karne ka route
@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    mobile = session.get('pending_mobile')
    if not mobile:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        user = User.query.filter_by(mobile=mobile).first()
        
        if user and user.otp == entered_otp:
            # Login successful: Session me user details set karein
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_phone'] = user.mobile
            session['is_admin'] = user.is_admin
            
            user.otp = None  # Use hone ke baad OTP clear kar dein
            db.session.commit()
            session.pop('pending_mobile', None)
            
            return redirect('/')
        else:
            return render_template('verify_otp.html', error="गलत OTP! दोबारा कोशिश करें।")
            
    return render_template('verify_otp.html')

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # 1. Login Guard: Agar user logged in nahi hai, to pehle /login bhejo
    if 'user_id' not in session:
        return redirect('/login')

    cart = session.get('cart', {})
    
    # 2. Empty Cart Check: Agar cart me kuch nahi hai, to /cart par wapas bhejo
    if not cart:
        return redirect('/cart')

    # 3. Database se cart ke items ka real data aur Total Price nikalna
    cart_items = []
    grand_total = 0
    for product_id, qty in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            item_total = product.price * qty
            grand_total += item_total
            cart_items.append({
                'product': product,
                'quantity': qty,
                'item_total': item_total
            })

    # 4. POST Request: Jab user Address bharkar "Place Order" button dabayega
    if request.method == 'POST':
        address = request.form.get('address')
        
        # A. Main Order Table me entry karo
        new_order = Order(
            user_id=session['user_id'],
            total_amount=grand_total,
            address=address
        )
        db.session.add(new_order)
        db.session.flush()  # Isse new_order ki 'id' turant generate ho jayegi (commit se pehle)

        # B. Har item ko OrderItem Table me daalo
        for item in cart_items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item['product'].id,
                quantity=item['quantity'],
                price=item['product'].price
            )
            db.session.add(order_item)

        # C. Database me changes Pukka (Save) karo
        db.session.commit()

        # D. Order Place hote hi Cart bilkul saaf (Empty) kar do
        session['cart'] = {}

        print(f"\n🎉 ORDER PLACED SUCCESSFULLY! Order ID: {new_order.id}\n")
        return render_template('order_success.html', order_id=new_order.id)

    # 5. GET Request: Jab user Checkout Page kholega
    return render_template('checkout.html', cart_items=cart_items, grand_total=grand_total)

@app.route('/orders')
def my_orders():
	if 'user_mobile' not in session:
		return redirect('/login')
	current_user_id=session['user_id']
	
	orders=Order.query.filter_by(user_id=current_user_id).order_by(Order.id.desc()).all()
	return render_template('orders-history.html',orders=orders)

# 3. Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# (यहाँ आपके ऊपर के सारे Routes / @app.route खत्म हो रहे हैं...)


# --- SABSE NICHE YE POORA BLOCK RAKHEIN ---
if __name__ == '__main__':
    with app.app_context():
        try:
            # PostgreSQL table me naya column jod rahe hain
            db.session.execute(text('ALTER TABLE "product" ADD COLUMN is_active BOOLEAN DEFAULT TRUE;'))
            db.session.commit()
            print("✅ PostgreSQL me 'is_active' column jud gaya hai!")
        except Exception as e:
            print("ℹ️ Column pehle se bana hua hai ya koi choti problem hai:", e)

    app.run(debug=True)


