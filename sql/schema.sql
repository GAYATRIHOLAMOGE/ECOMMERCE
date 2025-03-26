DROP DATABASE commerce;
CREATE DATABASE IF NOT EXISTS commerce;
USE commerce;

-- Users Table
CREATE TABLE users (
    iduser INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- Products Table
CREATE TABLE product (
    idproduct INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    image_url VARCHAR(255),
    category VARCHAR(100) NOT NULL
);

-- Categories Table (if needed separately)
CREATE TABLE category (
    idcategory INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- Orders Table
CREATE TABLE `order` (
    idorder INT AUTO_INCREMENT PRIMARY KEY,
    userid INT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userid) REFERENCES users(iduser) ON DELETE CASCADE
);

-- Order Items Table (Cart items)
CREATE TABLE order_item (
    idorder_item INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    price DECIMAL(10,2) NOT NULL,
    checkedout BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (order_id) REFERENCES `order`(idorder) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product(idproduct) ON DELETE CASCADE
);
