from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from flask_bcrypt import Bcrypt
import random
import os
import re

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'e21e4ff3f8e30edc042a1b9681b63f0290271eb04013d76d')  # Set a secret key for session management

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'buydirect'

# Flask-Mail configurations
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'simranbeedi@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'tgaq ygie afrs nyda')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'simranbeedi@gmail.com')
mysql = MySQL(app)
mail = Mail(app)
bcrypt = Bcrypt(app)

otp_storage = {}



@app.route('/')
def home():
    cursor = mysql.connection.cursor()
    try:
        # Fetch the four latest products
        cursor.execute("""
            SELECT g.id, g.name, g.description, g.selling_price, g.image, 
                   g.cost_price, g.quantity, cc.name AS category_name, 
                   b.name AS brand_name, sk.shop_name AS shopkeeper_name
            FROM groceries g
            LEFT JOIN core_category cc ON g.core_category_id = cc.id
            LEFT JOIN brands b ON g.brand_id = b.id
            LEFT JOIN shopkeepers sk ON g.shopkeeper_id = sk.id
            ORDER BY g.created_at DESC
            LIMIT 4
        """)
        products = cursor.fetchall()

        # Fetch all unique localities
        cursor.execute("""
            SELECT DISTINCT locality
            FROM shopkeepers
        """)
        localities = cursor.fetchall()

        # Fetch shopkeeper details (for the latest shops)
        cursor.execute("""
            SELECT shop_name, locality, image_filename
            FROM shopkeepers
        """)
        all_shops = cursor.fetchall()
        
        # Separate the two newest shops
        latest_shops = all_shops[:2]
        other_shops = all_shops[2:]

        # Fetch core category data
        cursor.execute("""
            SELECT id, name, image
            FROM core_category
        """)
        core_categories = cursor.fetchall()

    except Exception as e:
        app.logger.error(f"Error fetching home data: {e}")
        flash('An error occurred while fetching home data. Please try again later.', 'danger')
        return redirect(url_for('home'))
    finally:
        cursor.close()

    return render_template('home.html', 
                           products=products,
                           latest_shops=latest_shops,
                           other_shops=other_shops,
                           localities=localities,
                           core_categories=core_categories)

@app.route('/topstore', methods=['GET'])
def topstore():
    selected_locality = request.args.get('locality', '')

    # Fetch the filtered shops based on the selected locality
    cursor = mysql.connection.cursor()
    
    try:
        if selected_locality:
            cursor.execute("""
                SELECT shop_name, locality, image_filename
                FROM shopkeepers
                WHERE locality = %s
            """, (selected_locality,))
        else:
            cursor.execute("""
                SELECT shop_name, locality, image_filename
                FROM shopkeepers
            """)
        
        all_shops = cursor.fetchall()

        # Separate the two newest shops
        latest_shops = all_shops[:2]
        other_shops = all_shops[2:]

        # Fetch all unique localities for the filter
        cursor.execute("""
            SELECT DISTINCT locality
            FROM shopkeepers
        """)
        localities = cursor.fetchall()

    except Exception as e:
        app.logger.error(f"Error fetching topstore data: {e}")
        flash('An error occurred while fetching store data. Please try again later.', 'danger')
        return redirect(url_for('topstore'))
    finally:
        cursor.close()

    return render_template('topstore.html', 
                           latest_shops=latest_shops,
                           other_shops=other_shops,
                           localities=localities,
                           selected_locality=selected_locality)








@app.route('/add_to_cart', methods=['POST'])
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
        cart_count = get_cart_count(customer_id)  # Ensure this function is defined elsewhere
        session['cart_count'] = cart_count
        return jsonify({'success': True, 'cart_count': cart_count})
    
    except MySQLdb.Error as e:
        mysql.connection.rollback()
        app.logger.error(f"Database error: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while updating the cart. Please try again later.'})
    
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({'success': False, 'message': 'An unexpected error occurred. Please try again later.'})
    
    finally:
        cursor.close()

def get_cart_count(customer_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM cart_items WHERE customer_id = %s", (customer_id,))
    count = cursor.fetchone()[0]
    cursor.close()
    return count


@app.route('/store/<shop_name>', methods=['GET'])
def store_detail(shop_name):
    cursor = mysql.connection.cursor()

    try:
        # Fetch shop details
        cursor.execute("""
            SELECT shop_name, locality, image_filename
            FROM shopkeepers
            WHERE shop_name = %s
        """, (shop_name,))
        
        shop = cursor.fetchone()

        if not shop:
            flash('Shop not found.', 'danger')
            return redirect(url_for('topstore'))

        # Fetch groceries for the shop
        cursor.execute("""
            SELECT g.id, g.name, g.description, g.selling_price, g.image, 
                   g.cost_price, g.quantity, cc.name AS category_name, 
                   b.name AS brand_name
            FROM groceries g
            LEFT JOIN core_category cc ON g.core_category_id = cc.id
            LEFT JOIN brands b ON g.brand_id = b.id
            WHERE g.shopkeeper_id = (SELECT id FROM shopkeepers WHERE shop_name = %s)
        """, (shop_name,))
        
        groceries = cursor.fetchall()

        # Fetch categories
        cursor.execute("SELECT id, name FROM core_category")
        core_categories = cursor.fetchall()

        # Fetch subcategories
        cursor.execute("SELECT id, name, core_category_id FROM subcategory")
        subcategories = cursor.fetchall()

    except Exception as e:
        app.logger.error(f"Error fetching store details for {shop_name}: {e}")
        flash('An error occurred while fetching store details. Please try again later.', 'danger')
        return redirect(url_for('topstore'))
    
    finally:
        cursor.close()

    # Render the store details page
    return render_template(
        'customer/store.html', 
        shop=shop, 
        groceries=groceries, 
        core_categories=core_categories, 
        subcategories=subcategories
    )

@app.route('/get_subcategories', methods=['GET'])
def get_subcategories():
    category_id = request.args.get('category_id')
    cursor = mysql.connection.cursor()

    try:
        cursor.execute("""
            SELECT id, name 
            FROM subcategory
            WHERE core_category_id = %s
        """, (category_id,))
        subcategories = cursor.fetchall()

        return jsonify({'subcategories': [{'id': subcategory[0], 'name': subcategory[1]} for subcategory in subcategories]})
    
    except Exception as e:
        app.logger.error(f"Error fetching subcategories: {e}")
        return jsonify({'error': 'An error occurred while fetching subcategories.'}), 500
    
    finally:
        cursor.close()

@app.route('/filter_products', methods=['GET'])
def filter_products():
    category_id = request.args.get('category_id')
    subcategory_id = request.args.get('subcategory_id')
    shop_name = request.args.get('shop_name')
    cursor = mysql.connection.cursor()

    try:
        # Start building the query
        query = """
            SELECT g.id, g.name, g.description, g.selling_price, g.image, 
                   g.cost_price, g.quantity, cc.name AS category_name, 
                   b.name AS brand_name
            FROM groceries g
            LEFT JOIN core_category cc ON g.core_category_id = cc.id
            LEFT JOIN brands b ON g.brand_id = b.id
            WHERE g.shopkeeper_id = (SELECT id FROM shopkeepers WHERE shop_name = %s)
        """
        params = [shop_name]

        # Add filters for core category and subcategory
        if category_id:
            query += " AND g.core_category_id = %s"
            params.append(category_id)

        if subcategory_id:
            query += " AND g.subcategory_id = %s"
            params.append(subcategory_id)

        cursor.execute(query, tuple(params))
        products = cursor.fetchall()

        # Convert fetched data to a list of dictionaries
        products_list = [{'id': product[0], 'name': product[1], 'description': product[2], 'price': product[3], 'image': product[4]} for product in products]

        return jsonify({'products': products_list})
    
    except Exception as e:
        app.logger.error(f"Error filtering products: {e}")
        return jsonify({'error': 'An error occurred while filtering products.'}), 500
    
    finally:
        cursor.close()


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').strip()
    cursor = mysql.connection.cursor()

    try:
        # Search groceries by name or description
        cursor.execute("""
            SELECT g.id, g.name, g.description, g.selling_price, g.image, 
                   g.cost_price, g.quantity, cc.name AS category_name, 
                   b.name AS brand_name, sk.shop_name AS shopkeeper_name
            FROM groceries g
            LEFT JOIN core_category cc ON g.core_category_id = cc.id
            LEFT JOIN brands b ON g.brand_id = b.id
            LEFT JOIN shopkeepers sk ON g.shopkeeper_id = sk.id
            WHERE g.name LIKE %s OR g.description LIKE %s
        """, ('%' + query + '%', '%' + query + '%'))

        products = cursor.fetchall()
        
        if not products:
            flash('No results found for your query.', 'info')

    except Exception as e:
        app.logger.error(f"Error performing search: {e}")
        flash('An error occurred while searching. Please try again later.', 'danger')
        return redirect(url_for('home'))
    finally:
        cursor.close()

    return render_template('search_results.html', products=products, query=query)





                           # Import and register blueprints
from routes.admin_routes import admin_bp
from routes.shopkeeper_routes import shopkeeper_bp
from routes.customer_routes import customer_bp
from routes.category_routes import category_bp
from routes.brand_routes import brand_bp
from routes.grocery_routes import grocery_bp

app.register_blueprint(admin_bp)
app.register_blueprint(shopkeeper_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(category_bp)
app.register_blueprint(brand_bp)
app.register_blueprint(grocery_bp)

if __name__ == '__main__':
    app.run(debug=True)
