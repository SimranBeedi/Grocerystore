from flask import Flask, Blueprint, render_template, request, redirect, session, flash, url_for, jsonify
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import MySQLdb.cursors
import stripe
from flask_mail import Mail, Message
from flask_bcrypt import Bcrypt
import random
from datetime import datetime, timedelta
import re

from werkzeug.security import generate_password_hash, check_password_hash
stripe.api_key = 'sk_test_51Pksa1BQaGAcoXBgzEfpegBuEuNFz9aId4up3Qfkwtga9lrbmKgwBci1spLmxYNSNeTy9DfPfSCmb7oT8dC57mdZ00aaI19dLc'  # Replace with your Stripe Secret key

mysql = MySQL()
mail = Mail()
bcrypt = Bcrypt()
otp_storage = {}

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Make sure this is a strong, secure key

# Initialize extensions
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'your_user'
app.config['MYSQL_PASSWORD'] = 'your_password'
app.config['MYSQL_DB'] = 'your_database'


# Blueprint definition for customers
customer_bp = Blueprint('customer_bp', __name__, url_prefix='/customer')

# Route for login/signup page
@customer_bp.route('/loginsignup', methods=['GET'])
def loginsignup():
    show_otp = 'showOtp' in request.args
    return render_template('customer/loginsignup.html', show_otp=show_otp)

# Route for sending OTP
@customer_bp.route('/send-otp', methods=['POST'])
def send_otp_route():
    email = request.json.get('email')
    if email:
        otp = send_otp_to_email(email)
        if otp:
            return jsonify({"message": "OTP sent successfully"})
        else:
            return jsonify({"message": "Failed to send OTP"}), 500
    return jsonify({"message": "Email required"}), 400

# Route for verifying OTP
@customer_bp.route('/verify-otp', methods=['POST'])
def verify_otp_route():
    email = request.json.get('email')
    otp = request.json.get('otp')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT otp, expiry FROM otp_records WHERE email = %s ORDER BY created_at DESC LIMIT 1", (email,))
    record = cursor.fetchone()

    if record:
        current_time = datetime.now()
        if record['otp'] == int(otp) and record['expiry'] > current_time:
            return jsonify({"message": "OTP verified"})
        else:
            return jsonify({"message": "Invalid OTP or OTP expired"}), 400
    return jsonify({"message": "No OTP found for this email"}), 400@customer_bp.route('/signup', methods=['POST'])


@customer_bp.route('/signup', methods=['POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        otp = request.form.get('otp')
        password = request.form.get('password')

        if not username or not email or not otp or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('customer_bp.loginsignup', form='signup'))

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT otp, expiry FROM otp_records WHERE email = %s ORDER BY created_at DESC LIMIT 1", (email,))
        record = cursor.fetchone()

        if not record:
            flash('No OTP found for this email. Please request a new OTP.', 'danger')
            return redirect(url_for('customer_bp.loginsignup', form='signup', showOtp='true'))

        current_time = datetime.now()
        if record['otp'] != int(otp) or record['expiry'] < current_time:
            flash('Invalid OTP or OTP expired. Please try again.', 'danger')
            return redirect(url_for('customer_bp.loginsignup', form='signup', showOtp='true'))

        if not is_valid_password(password):
            flash('Password must meet complexity requirements.', 'danger')
            return redirect(url_for('customer_bp.loginsignup', form='signup', showOtp='true'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            cursor.execute("INSERT INTO users (username, email, password, is_verified) VALUES (%s, %s, %s, %s)", 
                           (username, email, hashed_password, 1))
            mysql.connection.commit()
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('customer_bp.loginsignup', form='login'))

        except MySQLdb.IntegrityError as e:
            if e.args[0] == 1062:
                flash('The email is already registered. Please log in or use another email.', 'danger')
            else:
                flash('An error occurred during registration. Please try again.', 'danger')

        return redirect(url_for('customer_bp.loginsignup', form='signup'))

    return redirect(url_for('customer_bp.loginsignup'))


def send_otp_to_email(email):
    otp = random.randint(100000, 999999)
    expiry = datetime.now() + timedelta(minutes=5)  # OTP expiry time set to 5 minutes

    # Create the email message
    msg = Message(
        subject='Your OTP Code for BUY Direct',
        recipients=[email],
        html=f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9;">
                <h2 style="color: #2b85d8;">BUY Direct - OTP Verification</h2>
                <p>Dear Valued Customer,</p>
                <p>Thank you for choosing BuyDirect, your trusted online grocery store where fresh produce and quality products are delivered directly to your doorstep.


</p>
                <p>Below is your One-Time Password (OTP) for verification:</p>
                <h3 style="font-size: 24px; color: #333;">{otp}</h3>
                <p>This OTP is valid for the next 5 minutes. Please enter this OTP on the verification page to complete the process. If you did not request this OTP, please ignore this email.</p>
                <p>If you need any assistance, feel free to contact our support team at <a href="mailto:support@buydirect.com" style="color: #2b85d8;">support@buydirect.com</a>.</p>
                <p>Thank you for choosing BUY Direct!</p>
                <p>Best regards,</p>
                <p>The BUY Direct Team</p>
                <footer style="margin-top: 20px; font-size: 12px; color: #666;">
                    <p>&copy; {datetime.now().year} BUY Direct. All rights reserved.</p>
                    <p><a href="https://www.buydirect.com" style="color: #2b85d8;">Visit our website</a></p>
                </footer>
            </div>
        </body>
        </html>
        """
    )

    try:
        mail.send(msg)
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO otp_records (email, otp, created_at, expiry) VALUES (%s, %s, NOW(), %s)", (email, otp, expiry))
        mysql.connection.commit()
        return otp
    except Exception as e:
        print(f"Error sending OTP: {e}")
        return None
def is_valid_password(password):
    pattern = re.compile(r'^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')
    return pattern.match(password) is not None

@customer_bp.route('/login', methods=['POST'])
def login_customer():
    username = request.form['username']
    password = request.form['password']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user:
            stored_password_hash = user['password']
            if bcrypt.check_password_hash(stored_password_hash, password):
                if user['is_verified'] == 1:
                    session['customer_id'] = user['id']
                    session['username'] = user['username']
                    session['loggedin'] = True
                    flash('You have successfully logged in!', 'success')
                    return redirect(url_for('home'))
                else:
                    flash("Your account is not verified. Please complete the registration.", 'danger')
            else:
                flash("Invalid username or password", 'danger')
        else:
            flash("Invalid username or password", 'danger')

    except Exception as e:
        flash(f"An error occurred during login. Please try again later. Error: {str(e)}", 'danger')

    finally:
        cursor.close()

    return render_template('customer/loginsignup.html')

@customer_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            SELECT g.id, g.name, g.description, g.selling_price, g.image, 
                   g.cost_price, g.quantity, g.unit, cc.name AS category_name, 
                   b.name AS brand_name, sk.shop_name AS shopkeeper_name
            FROM groceries g
            LEFT JOIN core_category cc ON g.core_category_id = cc.id
            LEFT JOIN brands b ON g.brand_id = b.id
            LEFT JOIN shopkeepers sk ON g.shopkeeper_id = sk.id
            WHERE g.id = %s
        """, (product_id,))
        product = cursor.fetchone()

        # Fetch cart count
        cart_count = get_cart_count(session.get('user_id'))

    except MySQLdb.Error as e:
        flash(f"An error occurred while fetching product details: {str(e)}", 'danger')
        product = None
    finally:
        cursor.close()

    if product:
        return render_template('customer/product_detail.html', product=product, cart_count=cart_count)
    else:
        return 'Product not found', 404

@customer_bp.route('/explore', methods=['GET'])
def explore():
    core_category_id = request.args.get('core_category_id')
    subcategory_id = request.args.get('subcategory_id')
    brand_id = request.args.get('brand_id')

    query = """
        SELECT g.id, g.name, g.description, g.selling_price AS discounted_price, g.image, g.cost_price AS original_price
        FROM groceries g
        LEFT JOIN subcategory s ON g.subcategory = s.id
        LEFT JOIN core_category c ON g.core_category_id = c.id
        LEFT JOIN brands b ON g.brand_id = b.id
        WHERE 1=1
    """
    
    params = []
    if core_category_id:
        query += " AND c.id = %s"
        params.append(core_category_id)
    if subcategory_id:
        query += " AND s.id = %s"
        params.append(subcategory_id)
    if brand_id:
        query += " AND b.id = %s"
        params.append(brand_id)

    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(query, params)
        products = cursor.fetchall()

        cursor.execute("SELECT id, name FROM core_category")
        core_categories = cursor.fetchall()

        cursor.execute("SELECT id, name FROM subcategory")
        subcategories = cursor.fetchall()

        cursor.execute("SELECT id, name FROM brands")
        brands = cursor.fetchall()

        # Fetch cart count
        cart_count = get_cart_count(session.get('user_id'))
        
    except MySQLdb.Error as e:
        flash(f"An error occurred while fetching products or filters: {str(e)}", 'danger')
        products = []
        core_categories = []
        subcategories = []
        brands = []
        cart_count = 0
    finally:
        cursor.close()

    return render_template('customer/explore.html', products=products, core_categories=core_categories, subcategories=subcategories, brands=brands, cart_count=cart_count)

@customer_bp.route('/get_filters')
def get_filters():
    core_category_id = request.args.get('core_category_id')
    
    if core_category_id:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        query = """
            SELECT id, name
            FROM subcategory
            WHERE core_category_id = %s
        """
        cursor.execute(query, (core_category_id,))
        subcategories = cursor.fetchall()
        cursor.close()
        return jsonify({'subcategories': subcategories})
    else:
        return jsonify({'subcategories': []})

@customer_bp.route('/get_products')
def get_products():
    core_category_id = request.args.get('core_category_id')
    subcategory_id = request.args.get('subcategory_id')
    brand_id = request.args.get('brand_id')

    query = """
        SELECT g.id, g.name, g.description, g.selling_price as discounted_price, g.image
        FROM groceries g
        LEFT JOIN subcategory s ON g.subcategory = s.id
        LEFT JOIN core_category c ON g.core_category_id = c.id
        LEFT JOIN brands b ON g.brand_id = b.id
        WHERE 1=1
    """
    
    params = []
    if core_category_id:
        query += " AND c.id = %s"
        params.append(core_category_id)
    if subcategory_id:
        query += " AND s.id = %s"
        params.append(subcategory_id)
    if brand_id:
        query += " AND b.id = %s"
        params.append(brand_id)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(query, params)
    products = cursor.fetchall()
    cursor.close()

    return jsonify({'products': products})

@customer_bp.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if not session.get('loggedin'):
        return jsonify({'success': False, 'message': 'Please log in to add items to your cart.'})

    product_id = request.form.get('product_id')
    customer_id = session.get('customer_id')

    if not product_id or not customer_id:
        return jsonify({'success': False, 'message': 'Invalid product or customer information.'})

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("SELECT * FROM cart_items WHERE customer_id = %s AND product_id = %s", (customer_id, product_id))
        item = cursor.fetchone()

        if item:
            cursor.execute("UPDATE cart_items SET quantity = quantity + 1 WHERE customer_id = %s AND product_id = %s", (customer_id, product_id))
        else:
            cursor.execute("INSERT INTO cart_items (customer_id, product_id, quantity) VALUES (%s, %s, %s)", (customer_id, product_id, 1))
        
        mysql.connection.commit()
        cart_count = get_cart_count(customer_id)
        session['cart_count'] = cart_count
        return jsonify({'success': True, 'cart_count': cart_count})
    except MySQLdb.Error as e:
        return jsonify({'success': False, 'message': 'An error occurred while updating the cart. Please try again later.'})
    finally:
        cursor.close()
def get_cart_count(customer_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("SELECT COUNT(*) AS count FROM cart_items WHERE customer_id = %s", (customer_id,))
        result = cursor.fetchone()
        count = result['count'] if result else 0
        print(f"Cart count for customer {customer_id}: {count}")
    except MySQLdb.Error as e:
        print(f"Database error while fetching cart count: {e}")
        count = 0
    finally:
        cursor.close()
    
    return count


@customer_bp.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    item_id = request.form.get('item_id')
    customer_id = session.get('customer_id')

    if not customer_id:
        return redirect(url_for('customer_bp.loginsignup'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("DELETE FROM cart_items WHERE id = %s AND customer_id = %s", (item_id, customer_id))
        mysql.connection.commit()

        # Update cart count in session
        session['cart_count'] = get_cart_count(customer_id)
        flash('Item removed from cart', 'success')
    except MySQLdb.Error as e:
        flash(f"An error occurred while removing the item: {str(e)}", 'danger')
    finally:
        cursor.close()

    return redirect(url_for('customer_bp.view_cart'))


from decimal import Decimal

from decimal import Decimal, ROUND_HALF_UP

@customer_bp.route('/cart')
def view_cart():
    # Ensure user is logged in
    if not session.get('loggedin'):
        return redirect(url_for('customer_bp.loginsignup'))

    customer_id = session.get('customer_id')

    if not customer_id:
        flash('Customer ID is missing.', 'danger')
        return redirect(url_for('customer_bp.loginsignup'))

    # Get the cart count
    cart_count = get_cart_count(customer_id)

    query = """
        SELECT ci.id, g.name, g.description, g.selling_price AS discounted_price, g.image, 
               b.name AS brand_name, ci.quantity, s.shop_name
        FROM cart_items ci
        LEFT JOIN groceries g ON ci.product_id = g.id
        LEFT JOIN brands b ON g.brand_id = b.id
        LEFT JOIN shopkeepers s ON g.shopkeeper_id = s.id
        WHERE ci.customer_id = %s
    """

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute(query, (customer_id,))
        cart_items = cursor.fetchall()

        # Initialize totals
        subtotal = Decimal(0)
        total_gst = Decimal(0)

        # Calculate subtotal and GST for each item
        for item in cart_items:
            price = Decimal(item['discounted_price'])
            quantity = Decimal(item['quantity'])
            item_total = price * quantity
            
            # GST rate
            gst_rate = Decimal(0.05)
            item_gst = item_total * gst_rate
            
            subtotal += item_total
            total_gst += item_gst

        # Check if subtotal is above 600 to adjust shipping cost
        shipping = Decimal(0) if subtotal > 600 else Decimal(40)
        
        # Total calculation including GST and shipping
        total = subtotal + shipping + total_gst

        # Format values to 2 decimal places
        decimal_format = Decimal('0.01')  # Define the format
        subtotal = subtotal.quantize(decimal_format, rounding=ROUND_HALF_UP)
        shipping = shipping.quantize(decimal_format, rounding=ROUND_HALF_UP)
        total_gst = total_gst.quantize(decimal_format, rounding=ROUND_HALF_UP)
        total = total.quantize(decimal_format, rounding=ROUND_HALF_UP)

    except MySQLdb.Error as e:
        flash(f"An error occurred while fetching cart items: {str(e)}", 'danger')
        cart_items = []
        subtotal = Decimal(0).quantize(decimal_format, rounding=ROUND_HALF_UP)
        shipping = Decimal(0).quantize(decimal_format, rounding=ROUND_HALF_UP)
        total_gst = Decimal(0).quantize(decimal_format, rounding=ROUND_HALF_UP)
        total = Decimal(0).quantize(decimal_format, rounding=ROUND_HALF_UP)
        
    finally:
        cursor.close()

    return render_template('customer/view_cart.html', cart_items=cart_items, subtotal=subtotal, shipping=shipping, gst=total_gst, total=total, cart_count=cart_count)

@customer_bp.route('/checkout')
def checkout():
    if not session.get('loggedin'):
        return redirect(url_for('customer_bp.loginsignup'))

    customer_id = session['customer_id']

    query = """
        SELECT ci.id, g.name, g.description, g.selling_price AS discounted_price, g.image, 
               b.name AS brand_name, ci.quantity, g.shopkeeper_id, s.shop_name
        FROM cart_items ci
        LEFT JOIN groceries g ON ci.product_id = g.id
        LEFT JOIN brands b ON g.brand_id = b.id
        LEFT JOIN shopkeepers s ON g.shopkeeper_id = s.id
        WHERE ci.customer_id = %s
    """

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute(query, (customer_id,))
        cart_items = cursor.fetchall()

        if cart_items:
            subtotal = sum(item['discounted_price'] * item['quantity'] for item in cart_items)
            shipping = 40  # Example shipping cost, adjust as needed
            total = subtotal + shipping
        else:
            cart_items = []
            subtotal = 0
            shipping = 0
            total = 0

    except MySQLdb.Error as e:
        flash(f"An error occurred while fetching cart items: {str(e)}", 'danger')
        cart_items = []
        subtotal = 0
        shipping = 0
        total = 0

    finally:
        cursor.close()

    return render_template('customer/checkout.html', cart_items=cart_items, subtotal=subtotal, shipping=shipping, total=total)

@customer_bp.route('/process_payment', methods=['POST'])
def process_payment():
    token = request.form.get('stripeToken')
    amount_str = request.form.get('amount')

    try:
        amount = int(float(amount_str))
    except ValueError:
        flash('Invalid amount format.', 'danger')
        return redirect(url_for('customer_bp.checkout'))

    if not token:
        flash('Payment failed: No token provided.', 'danger')
        return redirect(url_for('customer_bp.checkout'))

    try:
        charge = stripe.Charge.create(
            amount=amount,
            currency='usd',
            description='Your Order Description',
            source=token
        )

        # Record the order and get the order ID
        order_id = record_order(charge, amount)
        if order_id:
            flash('Payment successful! Your order has been placed.', 'success')
            return redirect(url_for('customer_bp.order_success', order_id=order_id))
        else:
            flash('An error occurred while recording the order.', 'danger')

    except stripe.error.CardError as e:
        flash(f"Payment failed: {str(e)}", 'danger')
    except stripe.error.StripeError as e:
        flash(f"Stripe error: {str(e)}", 'danger')
    except Exception as e:
        flash(f"An unexpected error occurred: {str(e)}", 'danger')

    return redirect(url_for('customer_bp.checkout'))

def record_order(charge, amount):
    customer_id = session.get('customer_id')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Insert order details into `orders` table
        cursor.execute("""
            INSERT INTO orders (amount, description, status, stripe_charge_id, customer_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (amount / 100, charge['description'], 'Paid', charge['id'], customer_id))

        # Get the last inserted order ID
        order_id = cursor.lastrowid

        # Insert order items and shopkeeper_id from products linked to each cart item
        cursor.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, shopkeeper_id)
            SELECT %s, ci.product_id, ci.quantity, g.shopkeeper_id
            FROM cart_items ci
            JOIN groceries g ON ci.product_id = g.id
            WHERE ci.customer_id = %s
        """, (order_id, customer_id))

        # Commit the transaction
        mysql.connection.commit()

        # Clear the cart and update inventory
        cursor.execute("DELETE FROM cart_items WHERE customer_id = %s", (customer_id,))
        update_inventory(customer_id)

        return order_id

    except MySQLdb.Error as e:
        mysql.connection.rollback()  # Rollback in case of error
        flash(f"An error occurred while recording the order: {str(e)}", 'danger')
    finally:
        cursor.close()
    return None



def get_shopkeeper_id(customer_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT g.shopkeeper_id
            FROM cart_items ci
            JOIN groceries g ON ci.product_id = g.id
            WHERE ci.customer_id = %s
            LIMIT 1
        """, (customer_id,))
        shopkeeper = cursor.fetchone()
        if shopkeeper and shopkeeper['shopkeeper_id']:
            return shopkeeper['shopkeeper_id']
        else:
            print(f"No shopkeeper ID found for customer ID {customer_id}.")
            return None
    except MySQLdb.Error as e:
        print(f"Database error while fetching shopkeeper ID: {e}")
        return None
    finally:
        cursor.close()


def update_inventory(customer_id):
    cursor = mysql.connection.cursor()
    try:
        # Example query to update inventory based on the items in the customer's cart
        cursor.execute("""
            UPDATE groceries g
            JOIN cart_items ci ON g.id = ci.product_id
            SET g.stock = g.stock - ci.quantity
            WHERE ci.customer_id = %s
        """, (customer_id,))
        
        # Clear the cart after inventory update
        cursor.execute("DELETE FROM cart_items WHERE customer_id = %s", (customer_id,))

        # Commit the transaction
        mysql.connection.commit()

    except MySQLdb.Error as e:
        mysql.connection.rollback()  # Rollback in case of error
        print(f"Database error while updating inventory: {e}")
    finally:
        cursor.close()









@customer_bp.route('/order_success')
def order_success():
    order_id = request.args.get('order_id')

    if not order_id:
        flash('No order ID provided.', 'danger')
        return redirect(url_for('customer_bp.checkout'))

    query = """
        SELECT o.id, o.amount AS order_amount, o.description AS order_description, o.status, o.created_at,
               g.name AS product_name, g.description AS product_description, 
               g.selling_price, g.image, b.name AS brand_name, ci.quantity, s.shop_name
        FROM orders o
        LEFT JOIN order_items ci ON o.id = ci.order_id
        LEFT JOIN groceries g ON ci.product_id = g.id
        LEFT JOIN brands b ON g.brand_id = b.id
        LEFT JOIN shopkeepers s ON g.shopkeeper_id = s.id
        WHERE o.id = %s
    """

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute(query, (order_id,))
        order_details = cursor.fetchall()
        print("Order Details:", order_details)  # Debug statement

        if not order_details:
            flash('No details found for the given order ID.', 'warning')

    except MySQLdb.Error as e:
        flash(f"An error occurred while fetching order details: {str(e)}", 'danger')
        order_details = []

    finally:
        cursor.close()

    return render_template('customer/order_success.html', order_details=order_details)
@customer_bp.route('/orders', methods=['GET'])
def view_orders():
    if not session.get('loggedin'):
        return redirect(url_for('customer_bp.loginsignup'))
    
    customer_id = session['customer_id']
    status = request.args.get('status', '')  # Get status from query parameter, default to empty string
    delivery_status = request.args.get('delivery_status', '')  # Get delivery_status from query parameter

    # Query to fetch orders
    orders_query = """
        SELECT o.id, o.amount, o.description, o.status, o.created_at
        FROM orders o
        WHERE o.customer_id = %s
    """

    # Query to fetch items for the orders
    items_query = """
        SELECT oi.order_id, g.name AS product_name, g.description AS product_description,
               g.selling_price, oi.quantity, oi.delivery_status
        FROM order_items oi
        JOIN groceries g ON oi.product_id = g.id
        WHERE oi.order_id IN (SELECT id FROM orders WHERE customer_id = %s)
    """

    params = [customer_id]

    if status:
        orders_query += " AND o.status = %s"
        params.append(status)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Fetch orders
        cursor.execute(orders_query, params)
        orders = cursor.fetchall()

        # Fetch items for the orders
        cursor.execute(items_query, [customer_id])
        items = cursor.fetchall()

        # Filter items by delivery_status if specified
        if delivery_status:
            items = [item for item in items if item['delivery_status'] == delivery_status]

        # Organize items by order_id
        order_items = {}
        for item in items:
            if item['order_id'] not in order_items:
                order_items[item['order_id']] = []
            order_items[item['order_id']].append(item)

    except MySQLdb.Error as e:
        flash(f"An error occurred while fetching orders: {str(e)}", 'danger')
        orders = []
        order_items = {}
    finally:
        cursor.close()

    return render_template('customer/view_orders.html', orders=orders, order_items=order_items)


@customer_bp.route('/wishlist/toggle', methods=['POST'])
def toggle_wishlist():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'})
    
    product_id = request.form.get('product_id')
    customer_id = session['customer_id']
    
    cursor = mysql.connection.cursor()
    try:
        # Check if the product is already in the wishlist
        cursor.execute("SELECT * FROM wishlist WHERE product_id = %s AND customer_id = %s", (product_id, customer_id))
        wishlist_item = cursor.fetchone()
        
        if wishlist_item:
            # Remove from wishlist
            cursor.execute("DELETE FROM wishlist WHERE product_id = %s AND customer_id = %s", (product_id, customer_id))
            mysql.connection.commit()
            return jsonify({'success': True, 'wishlisted': False, 'message': 'Product removed from wishlist'})
        else:
            # Add to wishlist
            cursor.execute("INSERT INTO wishlist (product_id, customer_id) VALUES (%s, %s)", (product_id, customer_id))
            mysql.connection.commit()
            return jsonify({'success': True, 'wishlisted': True, 'message': 'Product added to wishlist'})
    except MySQLdb.Error as e:
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'})
    finally:
        cursor.close()

@customer_bp.route('/wishlist')
def wishlist():
    if not session.get('loggedin'):
        return jsonify({'success': False, 'message': 'Please log in to view your wishlist.'})

    customer_id = session.get('customer_id')
    if not customer_id:
        return jsonify({'success': False, 'message': 'User not found.'})

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT w.id AS wishlist_id, g.id AS product_id, g.name, g.description, g.selling_price, g.image, 
                   g.cost_price, g.quantity, g.unit, b.name AS brand_name
            FROM wishlist w
            JOIN groceries g ON w.product_id = g.id
            LEFT JOIN brands b ON g.brand_id = b.id
            WHERE w.customer_id = %s
        """, (customer_id,))
        wishlist_items = cursor.fetchall()

        # Append the base URL for images
        base_image_url = url_for('static', filename='products/images/')
        for item in wishlist_items:
            item['image_url'] = base_image_url + item['image']
        
        return render_template('customer/wishlist.html', wishlist_items=wishlist_items)
    except MySQLdb.Error as e:
        error_message = f"An error occurred while fetching wishlist items: {str(e)}"
        print(error_message)  # Log to console for debugging
        return jsonify({'success': False, 'message': error_message})
    finally:
        cursor.close()


@customer_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('loggedin'):
        return redirect(url_for('customer_bp.loginsignup'))

    customer_id = session.get('customer_id')

    if not customer_id:
        flash('Customer ID is missing.', 'danger')
        return redirect(url_for('customer_bp.loginsignup'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('customer_bp.profile'))

        if username and password:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            query = "UPDATE users SET username = %s, password = %s WHERE id = %s"
            cursor.execute(query, (username, hashed_password, customer_id))
            mysql.connection.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('customer_bp.profile'))

    try:
        query = "SELECT username, email FROM users WHERE id = %s"
        cursor.execute(query, (customer_id,))
        user = cursor.fetchone()
    except MySQLdb.Error as e:
        flash(f"An error occurred while fetching user data: {str(e)}", 'danger')
        user = {}

    finally:
        cursor.close()

    return render_template('customer/profile.html', user=user)






















@customer_bp.route('/logout')
def logout_customer():
    # Clear session data related to customer
    session.pop('customer_id', None)
    session.pop('username', None)
    session.pop('loggedin', None)
    
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)



