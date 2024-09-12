from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import MySQLdb.cursors
import os
from werkzeug.utils import secure_filename

# Initialize MySQL and Bcrypt globally
mysql = MySQL()
bcrypt = Bcrypt()

# Create shopkeeper Blueprint
shopkeeper_bp = Blueprint('shopkeeper_bp', __name__, url_prefix='/shopkeeper')

# Define static folder paths
STATIC_FOLDER_IMAGES = os.path.join('static', 'images')
STATIC_FOLDER_DOCUMENTS = os.path.join('static', 'documents')

# Ensure these directories exist
if not os.path.exists(STATIC_FOLDER_IMAGES):
    os.makedirs(STATIC_FOLDER_IMAGES)

if not os.path.exists(STATIC_FOLDER_DOCUMENTS):
    os.makedirs(STATIC_FOLDER_DOCUMENTS)

@shopkeeper_bp.route('/login', methods=['GET', 'POST'])
def login_shopkeeper():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM shopkeepers WHERE username = %s", (username,))
        shopkeeper = cursor.fetchone()
        cursor.close()
        
        if shopkeeper:
            stored_password_hash = shopkeeper[2]  # assuming password hash is in the 3rd column (index 2)
            is_approved = shopkeeper[8]  # assuming approval status is in the 9th column (index 8)
            
            if bcrypt.check_password_hash(stored_password_hash, password):
                if is_approved is None:
                    flash("Your shop is awaiting approval. Please contact the admin.", 'warning')
                elif is_approved == 0:
                    flash("Your shop registration has been rejected. Please contact the admin.", 'danger')
                else:
                    session['username'] = shopkeeper[1]  # username (index 1)
                    session['shopkeeper_logged_in'] = True
                    session['shopkeeper_id'] = shopkeeper[0]  # Assuming shopkeeper ID is the first column (index 0)
                    return redirect(url_for('shopkeeper_bp.shopkeeper_dashboard'))
            else:
                flash("Invalid username or password", 'danger')
        else:
            flash("Invalid username or password", 'danger')
            
    return render_template('shopkeeper/login_shopkeeper.html')

@shopkeeper_bp.route('/register', methods=['GET', 'POST'])
def register_shopkeeper():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        shop_name = request.form['shop_name']
        address = request.form['address']
        district = request.form['district']
        locality = request.form['locality']

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Handle file uploads
        image = request.files.get('image')
        document = request.files.get('document')
        
        image_filename = None
        if image:
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(STATIC_FOLDER_IMAGES, image_filename))
        
        document_filename = None
        if document:
            document_filename = secure_filename(document.filename)
            document.save(os.path.join(STATIC_FOLDER_DOCUMENTS, document_filename))

        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO shopkeepers (username, password, email, shop_name, address, district, locality, image_filename, document_filename, is_approved)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (username, hashed_password, email, shop_name, address, district, locality, image_filename, document_filename, None))
            mysql.connection.commit()
            flash('Successfully registered. Please wait for admin approval.', 'success')
            return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred while registering: {str(e)}", 'danger')

    return render_template('shopkeeper/register_shopkeeper.html')
@shopkeeper_bp.route('/shopkeeper_dashboard')
def shopkeeper_dashboard():
    if 'shopkeeper_logged_in' not in session or not session['shopkeeper_logged_in']:
        flash("You need to be logged in to access this page.", 'warning')
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
    
    username = session.get('username')
    
    if not username:
        flash("Unable to retrieve user information. Please log in again.", 'danger')
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT is_approved, image_filename, shop_name, address, district, locality
            FROM shopkeepers
            WHERE username = %s
        """, (username,))
        shopkeeper = cursor.fetchone()
        
        if not shopkeeper:
            flash("Shopkeeper details not found. Please contact support.", 'danger')
            session.pop('shopkeeper_logged_in', None)
            return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
        
        is_approved, image_filename, shop_name, address, district, locality = shopkeeper
        
        if is_approved != 1:
            flash("Your shop registration status has not been approved yet. Please wait for admin approval.", 'warning')
            session.pop('shopkeeper_logged_in', None)
            return redirect(url_for('shopkeeper_bp.login_shopkeeper'))

        # Debug print statement
        print(f"Image filename: {image_filename}")

        # Get counts for groceries, brands, and orders
        cursor.execute("SELECT COUNT(*) FROM groceries WHERE shopkeeper_id = %s", (session.get('shopkeeper_id'),))
        grocery_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM brands WHERE shopkeeper_id = %s", (session.get('shopkeeper_id'),))
        brand_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM order_ITEMS WHERE shopkeeper_id = %s", (session.get('shopkeeper_id'),))
        order_count = cursor.fetchone()[0]
        
        cursor.close()

        return render_template('shopkeeper/shopkeeper_dashboard.html', 
                               username=username, 
                               image_filename=image_filename,
                               shop_name=shop_name,
                               address=address,
                               district=district,
                               locality=locality,
                               grocery_count=grocery_count,
                               brand_count=brand_count,
                               order_count=order_count)
    
    except Exception as e:
        flash(f"An error occurred while retrieving your dashboard details: {str(e)}", 'danger')
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))

        
@shopkeeper_bp.route('/update_profile', methods=['POST'])
def update_profile():
    username = request.form.get('username')
    password = request.form.get('password')
    profile_image = request.files.get('profile_image')

    if 'shopkeeper_id' not in session:
        flash('You need to be logged in to update your profile.', 'danger')
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))

    user_id = session['shopkeeper_id']

    if username:
        update_username(user_id, username)
    
    if password:
        update_password(user_id, password)
    
    if profile_image:
        filename = secure_filename(profile_image.filename)
        profile_image.save(os.path.join(STATIC_FOLDER_IMAGES, filename))
        update_profile_image(user_id, filename)
    
    return redirect(url_for('shopkeeper_bp.shopkeeper_dashboard'))

def update_username(user_id, new_username):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("UPDATE shopkeepers SET username = %s WHERE id = %s", (new_username, user_id))
        mysql.connection.commit()
        flash('Username updated successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f"An error occurred while updating username: {str(e)}", 'danger')
    finally:
        cursor.close()

def update_password(user_id, new_password):
    hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("UPDATE shopkeepers SET password = %s WHERE id = %s", (hashed_password, user_id))
        mysql.connection.commit()
        flash('Password updated successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f"An error occurred while updating password: {str(e)}", 'danger')
    finally:
        cursor.close()

def update_profile_image(user_id, image_filename):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("UPDATE shopkeepers SET image_filename = %s WHERE id = %s", (image_filename, user_id))
        mysql.connection.commit()
        flash('Profile image updated successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f"An error occurred while updating profile image: {str(e)}", 'danger')
    finally:
        cursor.close()

@shopkeeper_bp.route('/section', methods=['GET'])
def section():
    if 'shopkeeper_logged_in' not in session or not session['shopkeeper_logged_in']:
        flash("You need to be logged in to access this page.", 'warning')
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))

    username = session.get('username')

    if not username:
        flash("Unable to retrieve user information. Please log in again.", 'danger')
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT shop_name, locality, image_filename
            FROM shopkeepers
            WHERE username = %s
        """, (username,))
        shopkeeper = cursor.fetchone()
        cursor.close()

        if not shopkeeper:
            flash("Shopkeeper details not found. Please contact support.", 'danger')
            session.pop('shopkeeper_logged_in', None)
            return redirect(url_for('shopkeeper_bp.login_shopkeeper'))

        shop_name, locality, image_filename = shopkeeper
        
        return render_template('shopkeeper/section.html', 
                               shop_name=shop_name, 
                               locality=locality,
                               image_filename=image_filename)
    
    except Exception as e:
        flash(f"An error occurred while retrieving the section details: {str(e)}", 'danger')
        return redirect(url_for('shopkeeper_bp.shopkeeper_dashboard'))



@shopkeeper_bp.route('/orders')
def shopkeeper_orders():
    shopkeeper_id = session.get('shopkeeper_id')

    if not shopkeeper_id:
        flash("You must be logged in as a shopkeeper to view orders.", 'danger')
        return redirect(url_for('shopkeeper_bp.login'))

    # Query to fetch orders where the shopkeeper has at least one product in the order
    orders_query = """
        SELECT DISTINCT o.id AS order_id, o.amount, o.description AS order_description, o.status, o.created_at,
               u.username AS customer_name
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN users u ON o.customer_id = u.id
        WHERE oi.shopkeeper_id = %s
        ORDER BY o.created_at DESC
    """

    # Query to fetch the items in the orders for the current shopkeeper, including delivery_status
    items_query = """
        SELECT oi.order_id, g.name AS product_name, g.description AS product_description,
               g.selling_price, g.image AS product_image, oi.quantity, oi.delivery_status
        FROM order_items oi
        JOIN groceries g ON oi.product_id = g.id
        WHERE oi.shopkeeper_id = %s
    """

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Fetch all orders for the shopkeeper
        cursor.execute(orders_query, (shopkeeper_id,))
        orders = cursor.fetchall()

        # Fetch all items for the shopkeeper's orders
        cursor.execute(items_query, (shopkeeper_id,))
        items = cursor.fetchall()

        # Organize items by order_id
        order_items = {}
        for item in items:
            if item['order_id'] not in order_items:
                order_items[item['order_id']] = []
            order_items[item['order_id']].append(item)

        # Calculate total amounts
        total_amounts = {}
        for order_id, items in order_items.items():
            total_amount = sum(item['selling_price'] * item['quantity'] for item in items)
            total_amounts[order_id] = total_amount

        if not orders:
            flash("No orders found for your shop.", 'info')
    except MySQLdb.Error as e:
        flash(f"An error occurred while fetching your orders: {str(e)}", 'danger')
        orders = []
        order_items = {}
        total_amounts = {}
    finally:
        cursor.close()

    return render_template('shopkeeper/orders.html', orders=orders, order_items=order_items, total_amounts=total_amounts)


@shopkeeper_bp.route('/update_delivery_status/<int:order_id>', methods=['POST'])
def update_delivery_status(order_id):
    if not session.get('shopkeeper_id'):
        flash("You must be logged in as a shopkeeper to update delivery status.", 'danger')
        return redirect(url_for('shopkeeper_bp.login'))
    
    shopkeeper_id = session['shopkeeper_id']
    delivery_status = request.form.get('delivery_status')
    
    cursor = mysql.connection.cursor()
    try:
        # Check if the order items belong to the current shopkeeper
        cursor.execute("""
            SELECT DISTINCT oi.id
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE oi.order_id = %s AND oi.shopkeeper_id = %s
        """, (order_id, shopkeeper_id))
        order_items = cursor.fetchall()
        
        if not order_items:
            flash("Unauthorized: You do not have permission to update this order.", 'danger')
            return redirect(url_for('shopkeeper_bp.shopkeeper_orders'))

        # Update delivery status for all items in the order
        cursor.execute("""
            UPDATE order_items
            SET delivery_status = %s
            WHERE order_id = %s AND shopkeeper_id = %s
        """, (delivery_status, order_id, shopkeeper_id))

        mysql.connection.commit()
        flash('Delivery status updated successfully.', 'success')
    except MySQLdb.Error as e:
        mysql.connection.rollback()
        flash(f"An error occurred: {str(e)}", 'danger')
    finally:
        cursor.close()

    return redirect(url_for('shopkeeper_bp.shopkeeper_orders'))

@shopkeeper_bp.route('/logout')
def logout_shopkeeper():
    # Check if the session belongs to a shopkeeper
    if session.get('shopkeeper_logged_in'):
        session.pop('shopkeeper_logged_in', None)
        session.pop('shopkeeper_username', None)  # Use a specific key for shopkeepers
        session.pop('shopkeeper_id', None)
        session.pop('shopkeeper_image', None)  # Clear the session image data

    # Redirect to the home page or any other page you want after logout
    return redirect(url_for('home'))
