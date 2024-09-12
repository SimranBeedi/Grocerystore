from flask import Blueprint, render_template, request, redirect, session, flash, url_for, jsonify
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import os

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'products', 'images')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize MySQL
mysql = MySQL()

# Blueprint definition for grocery
grocery_bp = Blueprint('grocery_bp', __name__, url_prefix='/shopkeeper')

# Route to list all groceries for a shopkeeper
@grocery_bp.route('/list_grocery', methods=['GET'])
def list_grocery():
    if 'shopkeeper_logged_in' not in session:
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
    
    shopkeeper_id = session['shopkeeper_id']
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT g.id, g.name, g.description, g.cost_price, g.selling_price, g.quantity, g.unit,
               g.core_category_id, g.subcategory, g.brand_id, g.mfg_date, g.expiry_date, g.image,
               c.name AS core_category_name, s.name AS subcategory_name, b.name AS brand_name
        FROM groceries g
        LEFT JOIN brands b ON g.brand_id = b.id
        LEFT JOIN core_category c ON g.core_category_id = c.id
        LEFT JOIN subcategory s ON g.subcategory = s.id
        WHERE g.shopkeeper_id = %s
    """, (shopkeeper_id,))
    
    rows = cursor.fetchall()
    
    groceries = []
    for row in rows:
        grocery = {
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'cost_price': row[3],
            'selling_price': row[4],
            'quantity': row[5],
            'unit': row[6],
            'core_category_id': row[7],
            'subcategory_id': row[8],
            'brand_id': row[9],
            'mfg_date': row[10],
            'expiry_date': row[11],
            'image': row[12],
            'core_category_name': row[13],  # Fetching core category name
            'subcategory_name': row[14],     # Fetching subcategory name
            'brand_name': row[15]             # Fetching brand name
        }
        groceries.append(grocery)
    
    cursor.execute("SELECT id, name FROM core_category")
    core_categories = cursor.fetchall()

    cursor.execute("SELECT id, name FROM brands")
    brands = cursor.fetchall()

    cursor.close()

    return render_template('shopkeeper/list_grocery.html', groceries=groceries, core_categories=core_categories, brands=brands)



# Route to fetch subcategories based on core category
@grocery_bp.route('/get_subcategories/<int:core_category_id>', methods=['GET'])
def get_subcategories(core_category_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, name FROM subcategory WHERE core_category_id = %s", (core_category_id,))
        subcategories = cursor.fetchall()
        cursor.close()

        # Prepare subcategories as a list of dictionaries
        subcategories_list = [{'id': sub[0], 'name': sub[1]} for sub in subcategories]

        return jsonify(subcategories_list)
    except Exception as e:
        print(f"Error fetching subcategories: {str(e)}")
        return jsonify([])


# Route to create a new grocery
@grocery_bp.route('/create_grocery', methods=['POST'])
def create_grocery():
    if 'shopkeeper_logged_in' not in session:
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
    
    shopkeeper_id = session['shopkeeper_id']
    grocery_name = request.form['name']
    description = request.form['description']
    cost_price = request.form['cost_price']
    selling_price = request.form['selling_price']
    quantity = request.form['quantity']
    unit = request.form['unit']
    core_category_id = request.form['core_category_id']
    subcategory = request.form['subcategory']
    brand_id = request.form['brand']
    mfg_date = request.form['mfg_date']
    expiry_date = request.form['expiry_date']
    image = request.files['image']
    
    # Save image to static/products/images folder and get filename
    image_filename = secure_filename(image.filename)
    image.save(os.path.join(UPLOAD_FOLDER, image_filename))
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO groceries (name, description, cost_price, selling_price, quantity, unit, core_category_id, subcategory, brand_id, mfg_date, expiry_date, image, shopkeeper_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (grocery_name, description, cost_price, selling_price, quantity, unit, core_category_id, subcategory, brand_id, mfg_date, expiry_date, image_filename, shopkeeper_id))
    
    mysql.connection.commit()
    cursor.close()
    
    flash('Grocery created successfully', 'success')
    return redirect(url_for('grocery_bp.list_grocery'))


# Route to update an existing grocery
@grocery_bp.route('/update_grocery/<int:grocery_id>', methods=['POST'])
def update_grocery(grocery_id):
    if 'shopkeeper_logged_in' not in session:
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
    
    shopkeeper_id = session['shopkeeper_id']
    new_name = request.form['name']
    description = request.form['description']
    cost_price = request.form['cost_price']
    selling_price = request.form['selling_price']
    quantity = request.form['quantity']
    unit = request.form['unit']
    core_category_id = request.form['core_category_id']
    subcategory = request.form['subcategory']
    brand_id = request.form['brand']
    mfg_date = request.form['mfg_date']
    expiry_date = request.form['expiry_date']
    image = request.files['image'] if 'image' in request.files else None
    
    cursor = mysql.connection.cursor()
    
    if image:
        # Save image to static/products/images folder and get filename
        image_filename = secure_filename(image.filename)
        image.save(os.path.join(UPLOAD_FOLDER, image_filename))
        
        cursor.execute("""
            UPDATE groceries
            SET name = %s, description = %s, cost_price = %s, selling_price = %s, quantity = %s, unit = %s,
                core_category_id = %s, subcategory = %s, brand_id = %s, mfg_date = %s, expiry_date = %s, image = %s
            WHERE id = %s AND shopkeeper_id = %s
        """, (new_name, description, cost_price, selling_price, quantity, unit, core_category_id, subcategory, brand_id, mfg_date, expiry_date, image_filename, grocery_id, shopkeeper_id))
    else:
        cursor.execute("""
            UPDATE groceries
            SET name = %s, description = %s, cost_price = %s, selling_price = %s, quantity = %s, unit = %s,
                core_category_id = %s, subcategory = %s, brand_id = %s, mfg_date = %s, expiry_date = %s
            WHERE id = %s AND shopkeeper_id = %s
        """, (new_name, description, cost_price, selling_price, quantity, unit, core_category_id, subcategory, brand_id, mfg_date, expiry_date, grocery_id, shopkeeper_id))
    
    mysql.connection.commit()
    cursor.close()
    
    flash('Grocery updated successfully', 'success')
    return redirect(url_for('grocery_bp.list_grocery'))


# Route to delete a grocery
@grocery_bp.route('/delete_grocery/<int:grocery_id>', methods=['POST'])
def delete_grocery(grocery_id):
    if 'shopkeeper_logged_in' not in session:
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
    
    shopkeeper_id = session['shopkeeper_id']
    
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM groceries WHERE id = %s AND shopkeeper_id = %s", (grocery_id, shopkeeper_id))
    mysql.connection.commit()
    cursor.close()
    
    flash('Grocery deleted successfully', 'success')
    return redirect(url_for('grocery_bp.list_grocery'))
