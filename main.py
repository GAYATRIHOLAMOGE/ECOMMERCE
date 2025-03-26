from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask_mysqldb import MySQL
from datetime import datetime

load_dotenv()

app = Flask(__name__)

DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOSTNAME = os.getenv("DB_HOSTNAME")
DB_NAME = os.getenv("DB_NAME") or 'commerce'

secret_key = os.getenv("secret_key")

mysql = MySQL(app)

app.config['MYSQL_USER'] = DB_USERNAME
app.config['MYSQL_PASSWORD'] = DB_PASSWORD
app.config['MYSQL_HOST'] = DB_HOSTNAME
app.config['MYSQL_DB'] = DB_NAME
app.config["SECRET_KEY"] = secret_key
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

app.secret_key = 'your_secret_key'  # Replace with a real secret key

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Set the login view for @login_required

# Database connection


def get_db_connection():
    return pymysql.connect(
        host=DB_HOSTNAME or 'localhost',
        user=DB_USERNAME or 'root',  # Replace with your MySQL username if not using env vars
        password=DB_PASSWORD,  # Replace with your MySQL password if not using env vars
        database='commerce',
        cursorclass=pymysql.cursors.DictCursor
    )


class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE iduser = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                return User(
                    id=user['iduser'],
                    username=user['username'],
                    email=user['email'],
                    password=user['password']
                )
    finally:
        conn.close()
    return None

# Routes


@app.route('/')
def home():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM product LIMIT 6")
            featured_products = cursor.fetchall()
    finally:
        conn.close()
    return render_template('home.html', products=featured_products)


@app.route('/products')
def products():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM product")
            all_products = cursor.fetchall()
    finally:
        conn.close()
    return render_template('product_temp.html', products=all_products)


@app.route('/product_category/<category>', methods=['GET'])
def product_category(category):
    # Fetch products based on the selected category
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM product WHERE category = %s", (category,))
            all_products = cursor.fetchall()
    finally:
        conn.close()

    # Return the filtered products
    return render_template('product_category.html', all_products=all_products, category=category)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM product WHERE idproduct = %s", (product_id,))
            product = cursor.fetchone()
    finally:
        conn.close()

    if product:
        return render_template('product_detail.html', product=product)
    else:
        flash('Product not found.')
        return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        hashed_password = generate_password_hash(password)
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            flash('Passwords do not match!')
            return render_template('register.html')

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                               (username, email, hashed_password))
            conn.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except pymysql.err.IntegrityError:
            flash('Username or email already exists!')
        finally:
            conn.close()
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE username = %s", (username,))
                user_data = cursor.fetchone()

                if user_data and check_password_hash(user_data['password'], password):
                    user = User(
                        id=user_data['iduser'],
                        username=user_data['username'],
                        email=user_data['email'],
                        password=user_data['password']
                    )
                    login_user(user)

                    # Get user's active cart from database or create a new one
                    get_or_create_active_order(user_data['iduser'])

                    flash('Login successful!')

                    # Redirect to the next page if specified, otherwise go to home
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('home'))
                else:
                    flash('Invalid username or password!')
        finally:
            conn.close()
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    if 'order_id' in session:
        session.pop('order_id', None)
    flash('You have been logged out!')
    return redirect(url_for('home'))

# Function to get or create an active order for the user


def get_or_create_active_order(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Check if the user has an active order (not yet checked out)
            cursor.execute(
                "SELECT idorder FROM `order` WHERE userid = %s ORDER BY idorder DESC LIMIT 1",
                (user_id,)
            )
            order = cursor.fetchone()

            if order:
                order_id = order['idorder']
            else:
                # Create a new order if none exists
                cursor.execute(
                    "INSERT INTO `order` (userid, timestamp) VALUES (%s, %s)",
                    (user_id, datetime.now())
                )
                conn.commit()
                cursor.execute("SELECT LAST_INSERT_ID()")
                order_id = cursor.fetchone()['LAST_INSERT_ID()']

            # Store the active order ID in the session
            session['order_id'] = order_id
            return order_id
    finally:
        conn.close()

# Cart functionality


@app.route('/add_to_cart/<int:product_id>')
@login_required  # Require login to add to cart
def add_to_cart(product_id):
    # Ensure user has an active order
    if 'order_id' not in session:
        get_or_create_active_order(current_user.id)

    order_id = session['order_id']

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Check if product exists
            cursor.execute(
                "SELECT * FROM product WHERE idproduct = %s", (product_id,))
            product = cursor.fetchone()

            if not product:
                flash('Product not found!')
                return redirect(url_for('products'))

            # Check if the product is already in the cart
            cursor.execute(
                "SELECT * FROM order_item WHERE order_id = %s AND product_id = %s",
                (order_id, product_id)
            )
            existing_item = cursor.fetchone()

            if existing_item:
                # Update quantity if already in cart
                cursor.execute(
                    "UPDATE order_item SET quantity = quantity + 1 WHERE order_id = %s AND product_id = %s",
                    (order_id, product_id)
                )
            else:
                # Add new item to cart
                cursor.execute(
                    "INSERT INTO order_item (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
                    (order_id, product_id, 1, product['price'])
                )

            conn.commit()
            flash('Product added to cart!')
    except Exception as e:
        flash(f'Error adding product to cart: {str(e)}')
    finally:
        conn.close()

    return redirect(url_for('products'))


@app.route('/cart')
@login_required
def cart():
    # Ensure user has an active order
    if 'order_id' not in session:
        get_or_create_active_order(current_user.id)

    order_id = session['order_id']

    conn = get_db_connection()
    cart_items = []
    total_amount = 0

    try:
        with conn.cursor() as cursor:
            # Only retrieve items that are not checked out
            cursor.execute("""
                SELECT oi.*, p.name, p.description, p.image_url 
                FROM order_item oi 
                JOIN product p ON oi.product_id = p.idproduct 
                WHERE oi.order_id = %s AND oi.checkedout = 0
            """, (order_id,))

            items = cursor.fetchall()

            for item in items:
                item_total = float(item['price']) * item['quantity']
                cart_items.append({
                    'id': item['product_id'],
                    'name': item['name'],
                    'description': item['description'],
                    'price': float(item['price']),
                    'quantity': item['quantity'],
                    'image': item['image_url']
                })
                total_amount += item_total
    finally:
        conn.close()

    return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)


@app.route('/remove_from_cart/<int:product_id>')
@login_required  # Require login to remove from cart
def remove_from_cart(product_id):
    if 'order_id' not in session:
        flash('No active cart!')
        return redirect(url_for('products'))

    order_id = session['order_id']

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Remove the product from the cart
            cursor.execute(
                "DELETE FROM order_item WHERE order_id = %s AND product_id = %s",
                (order_id, product_id)
            )
            conn.commit()
            flash('Item removed from cart!')
    except Exception as e:
        flash(f'Error removing product from cart: {str(e)}')
    finally:
        conn.close()

    return redirect(url_for('cart'))


@app.route('/update_cart_quantity/<int:product_id>', methods=['POST'])
@login_required
def update_cart_quantity(product_id):
    if 'order_id' not in session:
        flash('No active cart!')
        return redirect(url_for('products'))

    order_id = session['order_id']
    quantity = int(request.form.get('quantity', 1))

    if quantity <= 0:
        return remove_from_cart(product_id)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Update the quantity
            cursor.execute(
                "UPDATE order_item SET quantity = %s WHERE order_id = %s AND product_id = %s",
                (quantity, order_id, product_id)
            )
            conn.commit()
            flash('Cart updated!')
    except Exception as e:
        flash(f'Error updating cart: {str(e)}')
    finally:
        conn.close()

    return redirect(url_for('cart'))


@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if 'order_id' not in session:
        flash('Your cart is empty!')
        return redirect(url_for('products'))

    order_id = session['order_id']

    # Check if the cart has items (only non-checked out items)
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) as count FROM order_item WHERE order_id = %s AND checkedout = 0", (order_id,))
            result = cursor.fetchone()
            if result['count'] == 0:
                flash('Your cart is empty!')
                return redirect(url_for('products'))
    finally:
        conn.close()

    if request.method == 'POST' and request.form.get('order_confirmed') == 'true':
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Mark all non-checked out items in this order as checked out
                cursor.execute(
                    "UPDATE order_item SET checkedout = 1 WHERE order_id = %s AND checkedout = 0",
                    (order_id,)
                )

                # Optionally, update the order timestamp to indicate completion
                cursor.execute(
                    "UPDATE `order` SET timestamp = %s WHERE idorder = %s",
                    (datetime.now(), order_id)
                )

                conn.commit()

                # Create a new active order (which will be empty)
                new_order_id = get_or_create_active_order(current_user.id)

                flash('Your order has been placed successfully!')
                return redirect(url_for('home'))
        except Exception as e:
            flash(f'Error processing order: {str(e)}')
        finally:
            conn.close()

    # Get cart items for the checkout page (only items not yet checked out)
    conn = get_db_connection()
    cart_items = []
    total_amount = 0

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT oi.*, p.name, p.description, p.image_url 
                FROM order_item oi 
                JOIN product p ON oi.product_id = p.idproduct 
                WHERE oi.order_id = %s AND oi.checkedout = 0
            """, (order_id,))

            items = cursor.fetchall()

            for item in items:
                item_total = float(item['price']) * item['quantity']
                cart_items.append({
                    'id': item['product_id'],
                    'name': item['name'],
                    'description': item['description'],
                    'price': float(item['price']),
                    'quantity': item['quantity'],
                    'image': item['image_url']
                })
                total_amount += item_total
    finally:
        conn.close()

    return render_template('checkout.html', cart_items=cart_items, total_amount=total_amount)


@app.route('/orders')
@login_required
def orders():
    user_id = current_user.id
    conn = get_db_connection()
    orders_list = []

    try:
        with conn.cursor() as cursor:
            # Fetch past orders for the user
            cursor.execute(
                "SELECT * FROM `order` WHERE userid = %s ORDER BY timestamp DESC", (user_id,))
            orders = cursor.fetchall()  # Ensure fetchall() is called correctly

            for order in orders:
                cursor.execute("""
                    SELECT oi.product_id, oi.quantity, oi.price, p.name 
                    FROM order_item oi 
                    JOIN product p ON oi.product_id = p.idproduct 
                    WHERE oi.order_id = %s
                """, (order['idorder'],))
                order_items = cursor.fetchall()  # Rename items to order_items

                total_amount = sum(
                    float(item['price']) * item['quantity'] for item in order_items)

                orders_list.append({
                    'idorder': order['idorder'],
                    'timestamp': order['timestamp'],
                    'order_items': order_items,  # Use new key name
                    'total_amount': total_amount
                })
    finally:
        conn.close()

    return render_template('orders.html', orders=orders_list)


if __name__ == '__main__':
    app.run(debug=True)
