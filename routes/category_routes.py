from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
import os
from werkzeug.utils import secure_filename

mysql = MySQL()
category_bp = Blueprint('category_bp', __name__, url_prefix='/admin')

STATIC_FOLDER_CORE_CATEGORY = os.path.join('static', 'core_category')
STATIC_FOLDER_SUB_CATEGORY = os.path.join('static', 'sub_category')

# Ensure these directories exist
os.makedirs(STATIC_FOLDER_CORE_CATEGORY, exist_ok=True)
os.makedirs(STATIC_FOLDER_SUB_CATEGORY, exist_ok=True)

# Helper functions
def save_image(file, folder):
    if file and file.filename:
        filename = secure_filename(file.filename)
        file_path = os.path.join(folder, filename)
        file.save(file_path)
        return filename
    return None
@category_bp.route('/list_grocery', methods=['GET'])
def list_grocery():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, name, description, core_category_id FROM grocery")
        groceries = cur.fetchall()
        cur.close()

        # Fetch core categories and subcategories
        core_categories = fetch_core_categories()
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, name FROM subcategory")
        subcategories = cur.fetchall()
        cur.close()

        return render_template('admin/list_grocery.html', groceries=groceries, core_categories=core_categories, subcategories=subcategories)
    except Exception as e:
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('category_bp.list_grocery'))


def fetch_core_categories():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, name, description, image FROM core_category")
        core_categories = cur.fetchall()
        cur.close()
        return core_categories
    except Exception as e:
        flash(f"An error occurred while fetching core categories: {str(e)}", 'error')
        return []

# Routes for core categories
@category_bp.route('/list_core_categories', methods=['GET'])
def list_core_categories():
    try:
        core_categories = fetch_core_categories()
        return render_template('admin/list_core_categories.html', core_categories=core_categories)
    except Exception as e:
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('category_bp.list_core_categories'))

# Add or Edit Core Category Route (Example)



@category_bp.route('/add_core_category', methods=['GET', 'POST'])
def add_core_category():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        image = request.files.get('image')
        
        image_filename = save_image(image, STATIC_FOLDER_CORE_CATEGORY) if image else None
        
        try:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO core_category (name, description, image) VALUES (%s, %s, %s)", (name, description, image_filename))
            mysql.connection.commit()
            cur.close()
            flash('Core category added successfully', 'success')
            return redirect(url_for('category_bp.list_core_categories'))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'error')
            return redirect(url_for('category_bp.add_core_category'))
    return render_template('admin/add_core_category.html')

@category_bp.route('/edit_core_category/<int:id>', methods=['GET', 'POST'])
def edit_core_category(id):
    if request.method == 'GET':
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT id, name, description, image FROM core_category WHERE id = %s", [id])
            core_category = cur.fetchone()
            cur.close()
            if core_category:
                return render_template('admin/edit_core_category.html', core_category=core_category)
            else:
                flash('Core category not found', 'error')
                return redirect(url_for('category_bp.list_core_categories'))
        except Exception as e:
            flash(f"An error occurred while fetching core category: {str(e)}", 'error')
            return redirect(url_for('category_bp.list_core_categories'))
    elif request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        image = request.files.get('image')
        
        # Fetch existing image if no new image is uploaded
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT image FROM core_category WHERE id = %s", [id])
            existing_image = cur.fetchone()
            cur.close()
        except Exception as e:
            flash(f"An error occurred while fetching core category for update: {str(e)}", 'error')
            existing_image = [None]

        image_filename = save_image(image, STATIC_FOLDER_CORE_CATEGORY) if image and image.filename else existing_image[0] if existing_image else None

        try:
            cur = mysql.connection.cursor()
            cur.execute("UPDATE core_category SET name = %s, description = %s, image = %s WHERE id = %s", (name, description, image_filename, id))
            mysql.connection.commit()
            cur.close()
            flash('Core category updated successfully', 'success')
            return redirect(url_for('category_bp.list_core_categories'))
        except Exception as e:
            flash(f"An error occurred while updating core category: {str(e)}", 'error')
            return redirect(url_for('category_bp.list_core_categories'))

@category_bp.route('/delete_core_category/<int:id>', methods=['GET'])
def delete_core_category(id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM core_category WHERE id = %s", [id])
        mysql.connection.commit()
        cur.close()
        flash('Core category deleted successfully', 'success')
    except mysql.connection.Error as e:
        if e.errno == 1451:
            flash("Cannot delete the core category because it is referenced by subcategories.", 'error')
        else:
            flash(f"An error occurred: {str(e)}", 'error')
    
    return redirect(url_for('category_bp.list_core_categories'))

@category_bp.route('/list_subcategories', methods=['GET'])
def list_subcategories():
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT s.id, s.name, s.description, c.name as core_category_name, s.image
            FROM subcategory s
            JOIN core_category c ON s.core_category_id = c.id
        """)
        subcategories = cur.fetchall()
        core_categories = fetch_core_categories()
        cur.close()
        return render_template('admin/list_subcategories.html', subcategories=subcategories, core_categories=core_categories)
    except Exception as e:
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('category_bp.list_subcategories'))

@category_bp.route('/add_subcategory', methods=['POST'])
def add_subcategory():
    name = request.form['name']
    description = request.form['description']
    core_category_id = request.form['core_category_id']
    image = request.files['image']
    
    image_filename = save_image(image, STATIC_FOLDER_SUB_CATEGORY)
    
    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO subcategory (name, description, core_category_id, image) VALUES (%s, %s, %s, %s)", (name, description, core_category_id, image_filename))
        mysql.connection.commit()
        cur.close()
        flash('Subcategory added successfully!', 'success')
        return redirect(url_for('category_bp.list_subcategories'))
    except Exception as e:
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('category_bp.list_subcategories'))

@category_bp.route('/edit_subcategory/<int:id>', methods=['GET', 'POST'])
def edit_subcategory(id):
    if request.method == 'GET':
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT id, name, description, core_category_id, image FROM subcategory WHERE id = %s", [id])
            subcategory = cur.fetchone()
            cur.close()
            if subcategory:
                core_categories = fetch_core_categories()
                return render_template('admin/edit_subcategory.html', subcategory=subcategory, core_categories=core_categories)
            else:
                flash('Subcategory not found', 'error')
                return redirect(url_for('category_bp.list_subcategories'))
        except Exception as e:
            flash(f"An error occurred while fetching subcategory: {str(e)}", 'error')
            return redirect(url_for('category_bp.list_subcategories'))
    elif request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        core_category_id = request.form['core_category_id']
        image = request.files['image']
        subcategory_id = request.form['id']

        # Fetch existing image if no new image is uploaded
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT image FROM subcategory WHERE id = %s", [subcategory_id])
            existing_image = cur.fetchone()
            cur.close()
        except Exception as e:
            flash(f"An error occurred while fetching subcategory for update: {str(e)}", 'error')
            existing_image = [None]

        image_filename = save_image(image, STATIC_FOLDER_SUB_CATEGORY) if image and image.filename else existing_image[0] if existing_image else None

        try:
            cur = mysql.connection.cursor()
            cur.execute("UPDATE subcategory SET name = %s, description = %s, core_category_id = %s, image = %s WHERE id = %s", (name, description, core_category_id, image_filename, subcategory_id))
            mysql.connection.commit()
            cur.close()
            flash('Subcategory updated successfully!', 'success')
            return redirect(url_for('category_bp.list_subcategories'))
        except Exception as e:
            flash(f"An error occurred while updating subcategory: {str(e)}", 'error')
            return redirect(url_for('category_bp.list_subcategories'))

@category_bp.route('/delete_subcategory/<int:id>')
def delete_subcategory(id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM subcategory WHERE id = %s", [id])
        mysql.connection.commit()
        cur.close()
        flash('Subcategory deleted successfully!', 'success')
    except mysql.connection.Error as e:
        flash(f"An error occurred: {str(e)}", 'error')
    
    return redirect(url_for('category_bp.list_subcategories'))
