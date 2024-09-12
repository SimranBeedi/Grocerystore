from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from flask_mysqldb import MySQL

# Initialize MySQL globally
mysql = MySQL()

# Blueprint definition for brands
brand_bp = Blueprint('brand_bp', __name__, url_prefix='/shopkeeper')

# Route to list all brands
@brand_bp.route('/list_brands', methods=['GET'])
def list_brands():
    if 'shopkeeper_logged_in' not in session or not session['shopkeeper_logged_in']:
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
    
    shopkeeper_id = session.get('shopkeeper_id')
    if not shopkeeper_id:
        flash('Shopkeeper ID not found in session', 'error')
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, name FROM brands WHERE shopkeeper_id = %s", (shopkeeper_id,))
    rows = cursor.fetchall()
    cursor.close()
    
    brands = [{'id': row[0], 'name': row[1]} for row in rows]
    
    # Fetch all brands for dropdown
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, name FROM brands")
    all_brands = cursor.fetchall()
    cursor.close()

    all_brands_dropdown = [{'id': row[0], 'name': row[1]} for row in all_brands]
    
    # Fetch shop name
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT shop_name FROM shopkeepers WHERE id = %s", (shopkeeper_id,))
    shop_name = cursor.fetchone()[0]
    cursor.close()

    return render_template('shopkeeper/list_brands.html', brands=brands, shop_name=shop_name, all_brands=all_brands_dropdown)


@brand_bp.route('/create_brand', methods=['POST'])
def create_brand():
    if 'shopkeeper_logged_in' not in session or not session['shopkeeper_logged_in']:
        flash('Please log in first', 'error')
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
    
    shopkeeper_id = session.get('shopkeeper_id')
    if not shopkeeper_id:
        flash('Shopkeeper ID not found in session', 'error')
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
    
    brand_name = request.form['name']
    
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("INSERT INTO brands (name, shopkeeper_id) VALUES (%s, %s)", (brand_name, shopkeeper_id))
        mysql.connection.commit()
        flash('Brand created successfully', 'success')
    except Exception as e:
        flash(f'Error creating brand: {str(e)}', 'error')
    finally:
        cursor.close()
    
    return redirect(url_for('brand_bp.list_brands'))


@brand_bp.route('/update_brand/<int:brand_id>', methods=['POST'])
def update_brand(brand_id):
    if 'shopkeeper_logged_in' not in session or not session['shopkeeper_logged_in']:
        flash('Please log in first', 'error')
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
    
    shopkeeper_id = session.get('shopkeeper_id')
    if not shopkeeper_id:
        flash('Shopkeeper ID not found in session', 'error')
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
    
    new_name = request.form['name']
    
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("UPDATE brands SET name = %s WHERE id = %s AND shopkeeper_id = %s", (new_name, brand_id, shopkeeper_id))
        mysql.connection.commit()
        flash('Brand updated successfully', 'success')
    except Exception as e:
        flash(f'Error updating brand: {str(e)}', 'error')
    finally:
        cursor.close()
    
    return redirect(url_for('brand_bp.list_brands'))


@brand_bp.route('/delete_brand/<int:brand_id>', methods=['POST'])
def delete_brand(brand_id):
    if 'shopkeeper_logged_in' not in session or not session['shopkeeper_logged_in']:
        flash('Please log in first', 'error')
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
    
    shopkeeper_id = session.get('shopkeeper_id')
    if not shopkeeper_id:
        flash('Shopkeeper ID not found in session', 'error')
        return redirect(url_for('shopkeeper_bp.login_shopkeeper'))
    
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("DELETE FROM brands WHERE id = %s AND shopkeeper_id = %s", (brand_id, shopkeeper_id))
        mysql.connection.commit()
        flash('Brand deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting brand: {str(e)}', 'error')
    finally:
        cursor.close()
    
    return redirect(url_for('brand_bp.list_brands'))
