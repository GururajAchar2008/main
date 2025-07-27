from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from functools import wraps
from datetime import datetime
import json # To store service details as JSON in the database

app = Flask(__name__)

# --- MySQL Configuration ---
# IMPORTANT: Replace with your actual MySQL credentials if different
app.config['MYSQL_HOST'] = "servicemanegergroup.mysql.pythonanywhere-services.com"
app.config['MYSQL_USER'] = 'servicemanegergr'
app.config['MYSQL_PASSWORD'] = 'Gururaj@1002005'
app.config['MYSQL_DB'] = 'user_authentication' # Ensure this database exists and tables are created
mysql = MySQL(app)

# --- Flask Secret Key for Sessions ---
# IMPORTANT: In production, use an environment variable!
app.secret_key = 'Admingptkadur@1002005'

# --- Service Prices and Details ---
# Each service item now includes a 'name', 'price', and 'unit' for better display and calculation
SERVICE_PRICES = {
    "sedimentFilter": {"name": "Sediment Filter", "price": 300, "unit": "item"},
    "carbonFilter": {"name": "Pre/Post Carbon", "price": 300, "unit": "item"},
    "sv": {"name": "SV", "price": 450, "unit": "item"},
    "boosterPump": {"name": "Booster Pump", "price": 1800, "unit": "item"},
    "membraneHousing": {"name": "Membrane Housing", "price": 250, "unit": "item"},
    "membrane": {"name": "Membrane", "price": 1500, "unit": "item"},
    "fr": {"name": "FR", "price": 250, "unit": "item"},
    "tdsController": {"name": "TDS Controller", "price": 150, "unit": "item"},
    "uvBarrel": {"name": "UV Barrel", "price": 300, "unit": "item"},
    "uvLight": {"name": "UV Light", "price": 200, "unit": "item"},
    "bucketPumpSmall": {"name": "Bucket Pump (Small)", "price": 350, "unit": "item"},
    "bucketPumpBig": {"name": "Bucket Pump (Big)", "price": 600, "unit": "item"},
    "spun": {"name": "Spun", "price": 100, "unit": "item"},
    "preFilter": {"name": "Pre Filter", "price": 450, "unit": "item"},
    "antiScalentBolls": {"name": "Anti-Scalent Balls", "price": 25, "unit": "per ball"}
}
SERVICE_CHARGE = 100 # Base service charge for any service visit

# --- City-Pincode Mapping (Example data) ---
CITY_PINCODE_MAP = {
    "bangalore": "560001",
    "mysore": "570001",
    "hubli": "580001",
    "mangalore": "575001",
    "chennai": "600001",
    "mumbai": "400001",
    "delhi": "110001"
}

# --- Decorators for Access Control ---
def login_required(f):
    """Decorator to ensure user is logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to ensure user has 'admin' or 'super_admin' role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or session.get('role') not in ['admin', 'super_admin']:
            flash('You do not have administrative privileges to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """Decorator to ensure user has 'super_admin' role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or session.get('role') != 'super_admin':
            flash('You do not have super administrative privileges to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    """Decorator to ensure user has 'user' role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or session.get('role') != 'user':
            flash('You do not have user privileges to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Database Helper Functions ---
def get_db_connection():
    """Establishes a database connection and returns a cursor."""
    try:
        return mysql.connection.cursor()
    except Exception as e:
        # Log the error for debugging purposes
        app.logger.error(f"Database connection failed: {e}")
        # Re-raise or handle as appropriate for your application
        raise

def fetch_all_customers(search_term=''):
    """Fetches all non-deleted customers from the database, optionally filtered by search term."""
    cur = None
    try:
        cur = get_db_connection()
        query = "SELECT id, customerName, customerNumber, customerAddress, customerCity, customerPincode, customerVillage, customerID, customerModel, customerColor, addedByUserId, timestamp FROM customers WHERE isDeleted = FALSE"
        params = []
        if search_term:
            search_term_like = f"%{search_term}%"
            query += " AND (customerName LIKE %s OR customerID LIKE %s OR customerNumber LIKE %s OR customerCity LIKE %s OR customerPincode LIKE %s OR customerVillage LIKE %s)"
            params = [search_term_like, search_term_like, search_term_like, search_term_like, search_term_like, search_term_like]
        # Order by timestamp for consistent display
        query += " ORDER BY timestamp DESC"
        cur.execute(query, params)
        customers_data = cur.fetchall()
        
        customers_list = []
        for customer in customers_data:
            customer_dict = {
                'id': customer[0],
                'customerName': customer[1],
                'customerNumber': customer[2],
                'customerAddress': customer[3],
                'customerCity': customer[4],
                'customerPincode': customer[5],
                'customerVillage': customer[6],
                'customerID': customer[7],
                'customerModel': customer[8],
                'customerColor': customer[9],
                'addedByUserId': customer[10],
                'timestamp': customer[11].isoformat() if customer[11] else None,
                'services': fetch_services_for_customer(customer[0]) # Fetch services for each customer
            }
            customers_list.append(customer_dict)
        return customers_list
    except Exception as e:
        app.logger.error(f"Error fetching customers: {e}")
        flash(f"Error fetching customer data: {e}", 'danger')
        return [] # Return empty list on error
    finally:
        if cur:
            cur.close()


def fetch_customer_by_id(customer_db_id):
    """Fetches a single non-deleted customer by their database ID."""
    cur = None
    try:
        cur = get_db_connection()
        cur.execute("SELECT id, customerName, customerNumber, customerAddress, customerCity, customerPincode, customerVillage, customerID, customerModel, customerColor, addedByUserId, timestamp FROM customers WHERE id = %s AND isDeleted = FALSE", (customer_db_id,))
        customer = cur.fetchone()
        if customer:
            return {
                'id': customer[0],
                'customerName': customer[1],
                'customerNumber': customer[2],
                'customerAddress': customer[3],
                'customerCity': customer[4],
                'customerPincode': customer[5],
                'customerVillage': customer[6],
                'customerID': customer[7],
                'customerModel': customer[8],
                'customerColor': customer[9],
                'addedByUserId': customer[10],
                'timestamp': customer[11].isoformat() if customer[11] else None
            }
        return None
    except Exception as e:
        app.logger.error(f"Error fetching customer by ID {customer_db_id}: {e}")
        flash(f"Error retrieving customer details: {e}", 'danger')
        return None
    finally:
        if cur:
            cur.close()

def fetch_services_for_customer(customer_db_id):
    """Fetches services for a given customer from the database."""
    cur = None
    try:
        cur = get_db_connection()
        # Order services by date descending to show most recent first
        cur.execute("SELECT service_details, totalCost, serviceDate, servedByUserId FROM services WHERE customer_id = %s ORDER BY serviceDate DESC", (customer_db_id,))
        services_data = cur.fetchall()
        
        services_list = []
        for service in services_data:
            service_dict = json.loads(service[0]) # Parse JSON string
            service_dict['totalCost'] = float(service[1])
            service_dict['serviceDate'] = service[2].isoformat() if service[2] else None
            service_dict['servedByUserId'] = service[3]
            services_list.append(service_dict)
        return services_list
    except Exception as e:
        app.logger.error(f"Error fetching services for customer {customer_db_id}: {e}")
        flash(f"Error retrieving service history: {e}", 'danger')
        return []
    finally:
        if cur:
            cur.close()

def get_dashboard_stats():
    """Calculates and returns dashboard statistics."""
    cur = None
    total_customers = 0
    total_services = 0
    try:
        cur = get_db_connection()
        cur.execute("SELECT COUNT(*) FROM customers WHERE isDeleted = FALSE")
        total_customers = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM services")
        total_services = cur.fetchone()[0]
    except Exception as e:
        app.logger.error(f"Error getting dashboard stats: {e}")
        flash(f"Error loading dashboard statistics: {e}", 'danger')
    finally:
        if cur:
            cur.close()
    return total_customers, total_services

# --- Routes ---

@app.route('/')
def home():
    """Redirects to the login page."""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login and redirects to appropriate dashboard."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        selected_role = request.form['role'] # 'admin' or 'user' selected from dropdown

        # --- Super Admin Login (Hardcoded for initial access) ---
        # This is a special login that bypasses the database for a 'super_admin' role.
        # It's intended for initial setup and user management.
        if username == "shashidhar.G" and password == "makein9741india" and selected_role == "admin":
            session['logged_in'] = True
            session['username'] = username
            session['role'] = 'super_admin' # Assign 'super_admin' role
            flash('Logged in as Super Admin!', 'success')
            return redirect(url_for('dashboard'))

        # --- Database User Login (for 'admin' and 'user' roles) ---
        cur = None
        try:
            cur = get_db_connection()
            # Fetch user from users_information table
            cur.execute("SELECT name, role, username, password FROM users_information WHERE username = %s AND password = %s", (username, password))
            user = cur.fetchone()
            
            if user:
                db_role = user[1] # Role stored in the database

                # Check if the selected role matches the database role
                if selected_role == db_role:
                    session['logged_in'] = True
                    session['username'] = username
                    session['role'] = db_role
                    flash(f'Logged in as {db_role.capitalize()}!', 'success')
                    if db_role == 'admin':
                        return redirect(url_for('dashboard'))
                    elif db_role == 'user':
                        return redirect(url_for('user_dashboard'))
                else:
                    flash(f"Role mismatch. You selected '{selected_role}', but your account is a '{db_role}'.", 'danger')
                    # Render template to show error immediately
                    return render_template('login.html', now=datetime.now())
            else:
                flash("Invalid username or password. Please try again.", 'danger')
                # Render template to show error immediately
                return render_template('login.html', now=datetime.now())
        except Exception as e:
            app.logger.error(f"Login database error: {e}")
            flash(f"An error occurred during login. Please try again. Error: {e}", 'danger')
            # Render template to show error immediately
            return render_template('login.html', now=datetime.now())
        finally:
            if cur:
                cur.close()
    else:
        return render_template('login.html', now=datetime.now()) # Pass now to login.html

@app.route('/logout')
@login_required
def logout():
    """Logs out the current user."""
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@admin_required # Only admins (including super_admin) can access this dashboard
def dashboard():
    """Admin dashboard displaying overall statistics and navigation."""
    total_customers, total_services = get_dashboard_stats()
    return render_template('dashboard.html',
                           username=session.get('username'),
                           total_customers=total_customers,
                           total_services=total_services,
                           current_role=session.get('role'),
                           now=datetime.now()) # Pass now to dashboard.html

@app.route('/user_dashboard')
@user_required # Only regular users can access this dashboard
def user_dashboard():
    """Regular user dashboard displaying overall statistics and limited navigation."""
    # For a user, maybe they only see their own customers or a limited view.
    # For now, it shows overall stats, but you could filter this by user_id
    # if you want users to only manage customers they added.
    total_customers, total_services = get_dashboard_stats()
    return render_template('user_dashboard.html',
                           username=session.get('username'),
                           total_customers=total_customers,
                           total_services=total_services,
                           current_role=session.get('role'),
                           now=datetime.now()) # Pass now to user_dashboard.html

@app.route('/add_user', methods=['GET', 'POST'])
@super_admin_required # Only super_admin can add new users/staff
def add_user():
    """Allows super admin to add new admin or regular users."""
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        number = request.form['number']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role'] # 'admin' or 'user'

        if not all([name, email, number, username, password, role]):
            flash("All fields are required!", 'danger')
            return render_template('add_user.html', now=datetime.now()) # Pass now to add_user.html

        cur = None
        try:
            cur = get_db_connection()
            # Check if username or email or number already exists
            cur.execute("SELECT id FROM users_information WHERE username = %s OR email = %s OR number = %s", (username, email, number))
            if cur.fetchone():
                flash("Username, Email, or Phone Number already exists. Please use unique values.", 'danger')
                return render_template('add_user.html', now=datetime.now()) # Pass now to add_user.html

            cur.execute(
                "INSERT INTO users_information (name, email, number, username, password, role) VALUES (%s, %s, %s, %s, %s, %s)",
                (name, email, number, username, password, role)
            )
            mysql.connection.commit()
            flash(f"New {role} user '{username}' added successfully!", 'success')
            return redirect(url_for('dashboard')) # Redirect to dashboard after adding user
        except Exception as e:
            mysql.connection.rollback()
            app.logger.error(f"Error adding user: {e}")
            flash(f"Error adding user: {str(e)}", 'danger')
        finally:
            if cur:
                cur.close()
    return render_template('add_user.html', now=datetime.now()) # Pass now to add_user.html


@app.route('/add_customer', methods=['GET', 'POST'])
@login_required # Changed from admin_required to login_required
def add_customer():
    """Allows admins and users to add new customer details."""
    if request.method == 'POST':
        customer_name = request.form['customerName']
        customer_number = request.form['customerNumber']
        customer_address = request.form['customerAddress']
        customer_city = request.form['customerCity']
        customer_pincode = request.form['customerPincode']
        customer_village = request.form['customerVillage']
        customer_id_unique = request.form['customerID'] # This is the unique ID from the form
        customer_model = request.form['customerModel']
        customer_color = request.form['customerColor']
        added_by_user_id = session.get('username', 'unknown') # Get current logged-in user

        # Basic validation
        if not all([customer_name, customer_number, customer_address, customer_city,
                    customer_pincode, customer_village, customer_id_unique, customer_model, customer_color]):
            flash("All fields are required!", 'danger')
            return render_template('add_customer.html', CITY_PINCODE_MAP=CITY_PINCODE_MAP, now=datetime.now()) # Pass now to add_customer.html

        cur = None
        try:
            cur = get_db_connection()
            # Check if customerID (unique ID) already exists
            cur.execute("SELECT id FROM customers WHERE customerID = %s AND isDeleted = FALSE", (customer_id_unique,))
            if cur.fetchone():
                flash(f"Customer ID '{customer_id_unique}' already exists. Please use a unique ID.", 'danger')
                return render_template('add_customer.html', CITY_PINCODE_MAP=CITY_PINCODE_MAP, now=datetime.now()) # Pass now to add_customer.html

            cur.execute(
                "INSERT INTO customers (customerName, customerNumber, customerAddress, customerCity, customerPincode, customerVillage, customerID, customerModel, customerColor, addedByUserId, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (customer_name, customer_number, customer_address, customer_city, customer_pincode, customer_village, customer_id_unique, customer_model, customer_color, added_by_user_id, datetime.now())
            )
            mysql.connection.commit()
            flash("Customer added successfully!", 'success')
            return redirect(url_for('view_customers')) # Redirect to view all customers
        except Exception as e:
            mysql.connection.rollback()
            app.logger.error(f"Error adding customer: {e}")
            flash(f"Error adding customer: {str(e)}", 'danger')
        finally:
            if cur:
                cur.close()
    return render_template('add_customer.html', CITY_PINCODE_MAP=CITY_PINCODE_MAP, now=datetime.now()) # Pass now to add_customer.html

@app.route('/view_customers', methods=['GET'])
@login_required # Both admin and user can view customers
def view_customers():
    """Displays a list of customers with search, add service, edit, and remove options."""
    search_term = request.args.get('search', '').strip()
    customers = fetch_all_customers(search_term)

    # Prepare data for modals (if they are triggered via query params)
    customer_id_for_modal = request.args.get('customer_id', None)
    customer_for_modal = None
    if customer_id_for_modal:
        customer_for_modal = fetch_customer_by_id(customer_id_for_modal)
        if not customer_for_modal:
            flash("Customer not found for modal operation.", 'danger')
            # Reset modal flags if customer not found
            request.args = request.args.copy()
            request.args.pop('show_add_service', None)
            request.args.pop('show_edit_customer', None)
            request.args.pop('customer_id', None)

    return render_template('view_customers.html',
                           customers=customers,
                           search_term=search_term,
                           SERVICE_PRICES=SERVICE_PRICES, # Pass service prices for the add service modal
                           SERVICE_CHARGE=SERVICE_CHARGE,
                           current_role=session.get('role'),
                           customer_for_modal=customer_for_modal, # Pass customer data for pre-filling edit modal
                           CITY_PINCODE_MAP=CITY_PINCODE_MAP, # Pass CITY_PINCODE_MAP to view_customers.html
                           now=datetime.now() # Pass now to view_customers.html
                           )

@app.route('/add_service/<int:customer_db_id>', methods=['POST'])
@login_required # Both admin and user can add services (already was login_required)
def add_service(customer_db_id):
    """Handles adding a new service record for a customer."""
    customer = fetch_customer_by_id(customer_db_id)
    if not customer:
        flash("Customer not found for adding service.", 'danger')
        return redirect(url_for('view_customers'))

    selected_services_with_qty = {}
    total_cost = float(SERVICE_CHARGE) # Start with base service charge

    # Iterate through all possible service items to get their quantities
    for service_key, service_info in SERVICE_PRICES.items():
        quantity_str = request.form.get(f'quantity_{service_key}', '0')
        try:
            quantity = int(quantity_str)
        except ValueError:
            quantity = 0 # Default to 0 if not a valid number

        if quantity > 0:
            selected_services_with_qty[service_key] = {
                "name": service_info["name"],
                "quantity": quantity,
                "price_per_unit": service_info["price"],
                "unit": service_info["unit"]
            }
            total_cost += (service_info["price"] * quantity)

    # Get additional service charge (user input)
    additional_service_charge_str = request.form.get('additionalServiceCharge', '0')
    try:
        additional_service_charge = float(additional_service_charge_str)
    except ValueError:
        additional_service_charge = 0.0

    total_cost += additional_service_charge

    description = request.form.get('description', '').strip()

    service_data = {
        "selected_items": selected_services_with_qty,
        "additionalServiceCharge": additional_service_charge,
        "description": description,
        "totalCost": total_cost, # This will be stored in the DB column as well
        "serviceDate": datetime.now().isoformat(),
        "servedByUserId": session.get('username', 'unknown')
    }

    cur = None
    try:
        cur = get_db_connection()
        cur.execute(
            "INSERT INTO services (customer_id, service_details, totalCost, serviceDate, servedByUserId) VALUES (%s, %s, %s, %s, %s)",
            (customer_db_id, json.dumps(service_data), total_cost, datetime.now(), session.get('username', 'unknown'))
        )
        mysql.connection.commit()
        flash("Service added successfully!", 'success')
    except Exception as e:
        mysql.connection.rollback()
        app.logger.error(f"Error adding service for customer {customer_db_id}: {e}")
        flash(f"Error adding service: {str(e)}", 'danger')
    finally:
        if cur:
            cur.close()

    # Redirect back to view_customers, potentially with a search term if one was active
    return redirect(url_for('view_customers', search=request.args.get('search', '')))

@app.route('/edit_customer/<int:customer_db_id>', methods=['GET', 'POST'])
@login_required # Changed from admin_required to login_required
def edit_customer(customer_db_id):
    """Allows admins and users to edit existing customer details."""
    customer = fetch_customer_by_id(customer_db_id)
    if not customer:
        flash("Customer not found for editing.", 'danger')
        return redirect(url_for('view_customers'))

    if request.method == 'POST':
        customer_name = request.form['customerName']
        customer_number = request.form['customerNumber']
        customer_address = request.form['customerAddress']
        customer_city = request.form['customerCity']
        customer_pincode = request.form['customerPincode']
        customer_village = request.form['customerVillage']
        customer_id_unique = request.form['customerID'] # This is the unique ID from the form
        customer_model = request.form['customerModel']
        customer_color = request.form['customerColor']

        # Basic validation
        if not all([customer_name, customer_number, customer_address, customer_city,
                    customer_pincode, customer_village, customer_id_unique, customer_model, customer_color]):
            flash("All fields are required!", 'danger')
            return render_template('edit_customer.html', customer=customer, CITY_PINCODE_MAP=CITY_PINCODE_MAP, now=datetime.now()) # Pass now to edit_customer.html

        cur = None
        try:
            cur = get_db_connection()
            # Check if the new customerID (unique ID) conflicts with another existing customer
            cur.execute("SELECT id FROM customers WHERE customerID = %s AND id != %s AND isDeleted = FALSE", (customer_id_unique, customer_db_id))
            if cur.fetchone():
                flash(f"Customer ID '{customer_id_unique}' already exists for another customer. Please use a unique ID.", 'danger')
                return render_template('edit_customer.html', customer=customer, CITY_PINCODE_MAP=CITY_PINCODE_MAP, now=datetime.now()) # Pass now to edit_customer.html

            cur.execute(
                "UPDATE customers SET customerName=%s, customerNumber=%s, customerAddress=%s, customerCity=%s, customerPincode=%s, customerVillage=%s, customerID=%s, customerModel=%s, customerColor=%s WHERE id=%s",
                (customer_name, customer_number, customer_address, customer_city, customer_pincode, customer_village, customer_id_unique, customer_model, customer_color, customer_db_id)
            )
            mysql.connection.commit()
            flash("Customer details updated successfully!", 'success')
            return redirect(url_for('view_customers'))
        except Exception as e:
            mysql.connection.rollback()
            app.logger.error(f"Error updating customer {customer_db_id}: {e}")
            flash(f"Error updating customer: {str(e)}", 'danger')
        finally:
            if cur:
                cur.close()
    # For GET request, render the form with existing customer data
    return render_template('edit_customer.html', customer=customer, CITY_PINCODE_MAP=CITY_PINCODE_MAP, now=datetime.now()) # Pass now to edit_customer.html


@app.route('/remove_customer/<int:customer_db_id>', methods=['POST'])
@admin_required # Remains admin_required
def remove_customer(customer_db_id):
    """Performs a soft delete on a customer record."""
    cur = None
    try:
        cur = get_db_connection()
        # Perform a soft delete by setting isDeleted to TRUE and recording deletion time
        cur.execute("UPDATE customers SET isDeleted = TRUE, deletedAt = %s WHERE id = %s", (datetime.now(), customer_db_id))
        mysql.connection.commit()
        flash("Customer marked as removed successfully!", 'success')
    except Exception as e:
        mysql.connection.rollback()
        app.logger.error(f"Error removing customer {customer_db_id}: {e}")
        flash(f"Error removing customer: {str(e)}", 'danger')
    finally:
        if cur:
            cur.close()
    return redirect(url_for('view_customers'))


@app.route('/about_app')
def about_app():
    """Displays information about the application."""
    return render_template('about_app.html', now=datetime.now()) # Pass now to about_app.html

# --- Main entry point ---
if __name__ == '__main__':
    # Run on 0.0.0.0 to be accessible on local network (useful for testing across devices)
    app.run(debug=True, host='0.0.0.0')
