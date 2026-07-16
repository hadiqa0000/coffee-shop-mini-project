CREATE TABLE CoffeeShop(
    shop_id BIGINT GENERATED ALWAYS AS IDENTITY,
    shop_name VARCHAR(30) NOT NULL,
    shop_address VARCHAR(255) NOT NULL,
    shop_phone VARCHAR(11) NOT NULL,
    shop_opened_at DATE NOT NULL,
    operating_hours JSONB NOT NULL,
    shop_markup_multiplier REAL NOT NULL,
    PRIMARY KEY(shop_id)
);

CREATE TABLE Employee(
    employee_id BIGINT GENERATED ALWAYS AS IDENTITY,
    shop_id BIGINT NOT NULL,
    employee_first_name VARCHAR(20) NOT NULL,
    employee_middle_name VARCHAR(20) NULL,
    employee_surname_name VARCHAR(20) NOT NULL,
    employee_gender VARCHAR(10) NOT NULL, CHECK(employee_gender IN('male', 'female', 'intersex')),
    employee_dob DATE NOT NULL,
    employee_role VARCHAR(20) NOT NULL CHECK (employee_role IN ('cashier','manager','barista', 'waiter')),
    employee_hire_date DATE NOT NULL,
    employee_current_status VARCHAR(15) NOT NULL DEFAULT 'active' CHECK(employee_current_status IN('active', 'suspended', 'terminated')),
    reason_for_suspension VARCHAR(15) NOT NULL DEFAULT 'active' CHECK(reason_for_suspension IN('maternity leave', 'military service')),
    PRIMARY KEY(shop_id, employee_id),
    FOREIGN KEY (shop_id) REFERENCES CoffeeShop(shop_id) ON DELETE CASCADE
); 

CREATE TABLE Product(
    product_id BIGINT GENERATED ALWAYS AS IDENTITY,
    shop_id BIGINT NOT NULL,
    product_name VARCHAR(40) NOT NULL,
    product_category VARCHAR(40) NOT NULL,
    product_current_price DECIMAL(12,2) NOT NULL CHECK(product_current_price >= 0),
    product_is_available BOOLEAN NOT NULL,
    PRIMARY KEY(shop_id, product_id),
    FOREIGN KEY (shop_id) REFERENCES CoffeeShop(shop_id) ON DELETE CASCADE
);

CREATE TABLE Orders(
    shop_id BIGINT NOT NULL,
    order_id BIGINT GENERATED ALWAYS AS IDENTITY,
    employee_id BIGINT NOT NULL,
    ordered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, --timestamp, which means date and time 
    order_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (order_status IN('pending', 'served', 'cancelled')),
    order_subtotal DECIMAL(12,2) NOT NULL,
    order_tax DECIMAL(15,2) NOT NULL,
    order_total DECIMAL(15,2) NOT NULL,
    CONSTRAINT chk_total CHECK (order_total = order_subtotal + order_tax),
    PRIMARY KEY(shop_id, order_id),
    FOREIGN KEY(shop_id) REFERENCES CoffeeShop(shop_id) ON DELETE CASCADE,
    FOREIGN KEY (shop_id, employee_id) REFERENCES Employee(shop_id, employee_id)
);

CREATE TABLE OrderItem(
    shop_id BIGINT NOT NULL,
    order_item_id BIGINT GENERATED ALWAYS AS IDENTITY,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INT NOT NULL CHECK(quantity > 0),
    unit_price DECIMAL(12,2) NOT NULL CHECK(unit_price >= 0),
    line_total DECIMAL(12,2) NOT NULL CHECK(line_total = quantity * unit_price),
    PRIMARY KEY(shop_id, order_item_id),
    FOREIGN KEY(shop_id, order_id) REFERENCES Orders(shop_id, order_id) ON DELETE CASCADE,
    FOREIGN KEY(shop_id, product_id) REFERENCES Product(shop_id, product_id) ON DELETE CASCADE
);

CREATE TABLE Payment(
    payment_id BIGINT GENERATED ALWAYS AS IDENTITY,
    shop_id BIGINT NOT NULL,
    order_id BIGINT NOT NULL,
    paid_at TIMESTAMP NULL, --cannot be before shop_opened_at, it is a timestamp, which means date AND time
    payment_method VARCHAR(20) CHECK (payment_method IN ('cash', 'card')),
    payment_status VARCHAR(20) DEFAULT 'completed' CHECK(payment_status IN('pending', 'completed', 'cancelled')),
    payment_amount DECIMAL(12,2) NOT NULL, --should be equal to order_total
    PRIMARY KEY(shop_id, payment_id),
    FOREIGN KEY(shop_id, order_id) REFERENCES Orders(shop_id, order_id) ON DELETE CASCADE
);
