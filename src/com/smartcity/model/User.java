package com.smartcity.model;

public class User {

    private String username;
    private String password;
    private String role;

    public User(String username, String password) {
        this.username = username;
        this.password = password;
        this.role = "USER";
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getPassword() {
        return password;
    }

    // No public setPassword() as per issue requirements

    public String getRole() {
        return role;
    }

    public void setRole(String role) {
        this.role = role;
    }
}