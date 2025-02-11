import pymysql

class DBManager:
    """
    A class to handle MySQL database operations.
    """

    def __init__(self):
        """
        Initializes the database connection.
        """
        self.host = "your-host"
        self.user = "your-user"
        self.password = "your-password"
        self.database = "your-database"
        self.port = 3306  # Ensure this is an integer, not a string
        self.connection = None

    def connect(self):
        """
        Establishes a connection to the MySQL database.
        """
        if self.connection is not None:
            return  # If already connected, avoid reconnecting

        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                cursorclass=pymysql.cursors.DictCursor  # Return results as dictionaries
            )
            print("[DBManager] Database connection successful.")
        except pymysql.MySQLError as e:
            print(f"[DBManager] MySQL error: {e}")
            self.connection = None

    def close(self):
        """
        Closes the database connection.
        """
        if self.connection:
            self.connection.close()
            self.connection = None
            print("[DBManager] Database connection closed.")

    def execute_query(self, query, values=None, fetch=False):
        """
        Executes an SQL query.
        :param query: SQL query string
        :param values: Tuple containing query values (if needed)
        :param fetch: Boolean indicating whether to fetch results
        :return: Query results if fetch=True, else None
        """
        self.connect()  # Ensure connection is established before executing query

        if not self.connection:
            print("[DBManager] No active database connection.")
            return None

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, values)
                if fetch:
                    return cursor.fetchall()
                self.connection.commit()
        except pymysql.MySQLError as e:
            print(f"[DBManager] MySQL error: {e}")
            return None