CREATE TABLE CoffeeShop(
shop_id BIGINT GENERATED ALWAYS AS IDENTITY,
shop_name VARCHAR(30) NOT NULL,
shop_address VARCHAR(255) NOT NULL,
shop_phone VARCHAR(11) NOT NULL,
PRIMARY KEY(shop_id)
);

CREATE TABLE Employee(
employee_id BIGINT GENERATED ALWAYS AS IDENTITY,
shop_id BIGINT NOT NULL,
first_name VARCHAR(20) NOT NULL,
middle_name VARCHAR(20) NULL,
last_name VARCHAR(20) NOT NULL,
role VARCHAR(20) NOT NULL,
hire_date DATE NOT NULL,
status VARCHAR(15) NOT NULL DEFAULT 'active'
PRIMARY KEY(shop_id, employee_id),
FORIEGN KEY (shop_id) REFERENCES CofeeShop(shop_id)
); 


CREATE TABLE Product(
product_id BIGINT ALWAYS GENERATE AS IDENTITY,
shop_id BIGINT NOT NULL,
product_name VARCHAR(40)  NOT NULL,
product_category VARCHAR(40) NOT NULL,
product_current_price DECIMAL(12,2) NOT NULL,
product_is_available BOOLEAN NOT NULL,
PRIMARY KEY(shop_id, product_id),
FOREIGN KEY (shop_id) REFERENCES CoffeeShop(shop_id)

);


CREATE TABLE Orders(
shop_id BIGINT NOT NULL,
order_id BIGINT ALWAYS GENERATE AS IDENTITY,
employee_id BIGINT NOT NULL,
ordered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK IN('pending', 'served', 'cancelled'),
subtotal DECIMAL(12,2) NOT NULL,
tax DECIMAL(15.2) NOT NULL,
total DECIMAL(15,2) NOT NULL,
CONSTRAINT chk_total CHECK (total = subtotal + tax)
PRIMARY KEY(shop_id,order_id),
FOREIGN KEY(shop_id) REFERENCES CoffeeShop(shop_id)
);


CREATE TABLE OrderItem(
shop_id BIGINT NOT NULL,
order_item_id BIGINT ALWAYS GEMERATE AS IDENTITY,
order_id BIGINT NOT NULL,
product_id BIGINT NOT NULL,
quantity INT NOT NULL,
unit_price DECIMAL(12,2) NOT NULL,
line_total DECIMAL(12,2) NOT NULL,
PRIMARY KEY(order_item_id, shop_id),
FORIEGN KEY(order_id) REFERENCES Orders(order_id),
FORIEGN KEY(product_id) REFERENCES Product(product_id)

);


CREATE TABLE Payment
payment_id BIGINT ALWAYS GENERATE AS IDENTITY,
shop_id BIGINT NOT NULL,
order_id BIGINT NOT NULL,
paid_at TIMESTAMP NOT NULL,
payment_method VARCHAR(20) CHECK (payment_method IN  ('cash', 'card'),
payment_status VARCHAR(20) DEFAULT 'completed' CHECK(payment_status IN('pending', 'completed', 'cancelled'),
amount DECIMAL(12,2) NOT NULL,
PRIMARY KEY(shop_id,order_id),
FOREIGN KEY(order_id) REFERENCES Orders(order_id)

);


