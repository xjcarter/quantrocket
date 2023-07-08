import mysql.connector

# Connect to the MySQL server using the root user
connection = mysql.connector.connect(
    host="localhost",  # Replace with your MySQL server host
    user="root",  # Replace with your MySQL root username
    password="tarzan001"  # Replace with your MySQL root password
)

# Create a cursor to execute SQL queries
cursor = connection.cursor()

# Define the new username and password
new_username = "jcarter"
new_password = "jcarter123"

# Create a new user
cursor.execute(f"CREATE USER '{new_username}'@'localhost' IDENTIFIED BY '{new_password}'")
print(f"User '{new_username}' created successfully.")

# Grant privileges to the new user
cursor.execute(f"GRANT ALL PRIVILEGES ON *.* TO '{new_username}'@'localhost'")
cursor.execute("FLUSH PRIVILEGES")
print(f"Privileges granted to user '{new_username}'.")

# Close the cursor and connection
cursor.close()
connection.close()
