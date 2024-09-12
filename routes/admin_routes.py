from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

# Define a function to get MySQL connection
def get_mysql_connection():
    from app import mysql
    return mysql.connection

@admin_bp.route('/login', methods=['POST', 'GET'])
def login_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin@123':
            session['admin_logged_in'] = username  # Set admin username in session
            return redirect(url_for('admin_bp.admin_dashboard'))
        else:
            flash("Invalid username or password", 'danger')
    return render_template('admin/login_admin.html')

@admin_bp.route('/admin_dashboard', methods=['GET'])
def admin_dashboard():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_bp.login_admin'))
    
    try:
        cursor = get_mysql_connection().cursor()

        # Fetch shopkeepers awaiting approval
        cursor.execute("SELECT * FROM shopkeepers WHERE is_approved IS NULL")
        pending_shopkeepers = cursor.fetchall()

        # Fetch core categories
        cursor.execute("SELECT COUNT(*) FROM core_category")
        total_core_categories = cursor.fetchone()[0]

        # Fetch subcategories
        cursor.execute("SELECT COUNT(*) FROM subcategory")
        total_subcategories = cursor.fetchone()[0]

        # Fetch approved shopkeepers
        cursor.execute("SELECT COUNT(*) FROM shopkeepers WHERE is_approved = 1")
        total_approved_shopkeepers = cursor.fetchone()[0]

        # Fetch total customers
        cursor.execute("SELECT COUNT(*) FROM users")
        total_customers = cursor.fetchone()[0]

        # Fetch pending shopkeepers count
        total_pending_shopkeepers = len(pending_shopkeepers)

        cursor.close()

        return render_template('admin/admin_dashboard.html',
                               total_customers=total_customers,
                               total_approved_shopkeepers=total_approved_shopkeepers,
                               total_pending_shopkeepers=total_pending_shopkeepers,
                               total_core_categories=total_core_categories,
                               total_subcategories=total_subcategories)
    except Exception as e:
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('admin_bp.admin_dashboard'))
    


@admin_bp.route('/admin/approval', methods=['GET', 'POST'])
def approval():
    if request.method == 'POST':
        shopkeeper_id = request.form.get('shopkeeper_id')
        action = request.form.get('action')

        try:
            with get_mysql_connection().cursor() as cur:
                if action == 'accept':
                    cur.execute("UPDATE shopkeepers SET is_approved = 1 WHERE id = %s", [shopkeeper_id])
                elif action == 'reject':
                    cur.execute("DELETE FROM shopkeepers WHERE id = %s", [shopkeeper_id])
                get_mysql_connection().commit()
                flash('Action performed successfully', 'success')
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')

        return redirect(url_for('admin_bp.approval'))  # Redirect to GET route after POST

    # Fetch shopkeepers awaiting approval
    try:
        with get_mysql_connection().cursor() as cur:
            cur.execute("SELECT id, username, email, address, registration_date FROM shopkeepers WHERE is_approved IS NULL")
            shopkeepers_tuples = cur.fetchall()
    except Exception as e:
        flash(f"An error occurred while fetching data: {str(e)}", 'danger')
        shopkeepers_tuples = []

    # Convert tuples to dictionaries
    shopkeepers = [{
        'id': shopkeeper[0],
        'username': shopkeeper[1],
        'email': shopkeeper[2],
        'address': shopkeeper[3],
        'registration_date': shopkeeper[4].strftime('%Y-%m-%d') if shopkeeper[4] else 'N/A'
    } for shopkeeper in shopkeepers_tuples]

    return render_template('admin/approval.html', shopkeepers=shopkeepers)



@admin_bp.route('/admin/list_approved_shopkeepers', methods=['GET'])
def list_approved_shopkeepers():
    try:
        with get_mysql_connection().cursor() as cur:
            cur.execute("SELECT id, username, email, registration_date FROM shopkeepers WHERE is_approved = 1")
            columns = [col[0] for col in cur.description]  # Get column names
            shopkeepers = [dict(zip(columns, row)) for row in cur.fetchall()]  # Convert rows to dictionaries
    except Exception as e:
        flash(f"An error occurred while fetching data: {str(e)}", 'error')
        shopkeepers = []

    return render_template('admin/list_approved_shopkeepers.html', shopkeepers=shopkeepers)

@admin_bp.route('/view_customers', methods=['GET'])
def view_customers():
    try:
        with get_mysql_connection().cursor() as cur:
            cur.execute("SELECT username, email FROM users")
            users = cur.fetchall()
    except Exception as e:
        flash(f"An error occurred while fetching data: {str(e)}", 'danger')
        users = []

    return render_template('admin/view_customers.html', users=users)






@admin_bp.route('/logout', methods=['POST'])
def logout_admin():
    session.pop('admin_logged_in', None)  # Remove admin username from session
    return redirect(url_for('home'))
