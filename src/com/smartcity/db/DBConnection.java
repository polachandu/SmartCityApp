package com.smartcity.db;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.Scanner;

/**
 * Handles the database connection for the Smart City Guide application.
 * This class uses the Singleton pattern approach for providing a connection
 * to the MySQL database. It prompts the user for the root database password
 * upon initialization.
 *
 * @author Rajath2005 (Original Creator)
 * @version 1.0
 */
public class DBConnection {
    // Database credentials
    private static final String DB_URL = "jdbc:mysql://localhost:3306/smart_city_guide";
    private static final String DB_USER = "root";
    private static String DB_PASSWORD = "";

    /**
     * Static initialization block.
     * This block is executed once when the class is first loaded into memory.
     * It loads the MySQL JDBC driver and securely prompts the developer
     * for the database password via the console.
     */
    static {
        // Load MySQL JDBC driver
        try {
            Class.forName("com.mysql.cj.jdbc.Driver");
            System.out.println("✅ MySQL JDBC Driver loaded successfully.");
        } catch (ClassNotFoundException e) {
            System.out.println("❌ Error: MySQL JDBC Driver not found.");
            System.out.println("   Please add mysql-connector-java JAR to your project.");
            e.printStackTrace();
        }


        // Ask developer for database password
        Scanner scanner = new Scanner(System.in);
        System.out.print("\n🔐 Enter MySQL password for user 'root': ");
        DB_PASSWORD = scanner.nextLine();
    }

    /**
     * Establishes and returns a connection to the MySQL database.
     * If the connection fails, it catches the SQLException and returns null.
     * 
     * Note: Callers are responsible for closing this connection (preferably
     * using try-with-resources) to prevent resource leaks.
     *
     * @return A valid {@link Connection} object, or null if connection fails.
     */
    public static Connection getConnection() {
        try {
            Connection connection = DriverManager.getConnection(DB_URL, DB_USER, DB_PASSWORD);
            return connection;
        } catch (SQLException e) {
            System.out.println("❌ Error: Failed to connect to database.");
            System.out.println("   Error message: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }
}
