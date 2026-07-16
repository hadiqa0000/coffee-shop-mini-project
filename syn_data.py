from __future__ import annotations
from dataclasses import dataclass
import datetime 
from datetime import date, timedelta
import random
from faker import Faker
from typing import Optional, List, Dict, Tuple

fake = Faker('tr_TR')

TURKIYE_GEOGRAPHY = {
    "Istanbul": ["Kadikoy", "Besiktas", "Fatih", "Uskudar", "Sisli", "Sariyer", "Avcilar"],
    "Ankara": ["Cankaya", "Keçiören", "Yenimahalle", "Etimesgut"],
    "Izmir": ["Karsiyaka", "Konak", "Bornova", "Buca"],
}

LOCATION_PREMIUMS = {
    "Kadikoy": 1.25, "Besiktas": 1.25, "Sisli": 1.25, "Cankaya": 1.25,
    "Uskudar": 1.10, "Karsiyaka": 1.10, "Bornova": 1.10, "Yenimahalle": 1.10,
    "Fatih": 1.00, "Sariyer": 1.15, "Konak": 1.05,
    "Avcilar": 0.90, "Keçiören": 0.90, "Etimesgut": 0.90, "Buca": 0.90
} 

@dataclass
class Address:
    building_no: str
    street_no: str
    district: str
    city: str
    country: str = "Turkiye"
    
    def to_string(self) -> str:
        return f"Sk. {self.street_no}, bina: {self.building_no}, {self.district}/{self.city}, {self.country}"

@dataclass 
class CoffeeShop:
    shop_id: int
    shop_name: str
    shop_address: Address  
    shop_phone: str
    shop_opened_at: datetime.date
    operating_hours: list[tuple[datetime.time, datetime.time]]  #need to format the list into strings before dumping it into sql 

@dataclass
class Employee:
    shop_id: int
    employee_first_name: str
    employee_surname_name: str
    employee_gender: str
    employee_dob: date 
    employee_role: str
    employee_hire_date: date
    employee_current_status: str  # 'active', 'suspended', 'terminated'
    employee_middle_name: Optional[str] = None
    reason_for_suspension: str = 'active'  
    
@dataclass
class Product:
    product_id: int  
    shop_id: int
    product_name: str
    product_category: str
    product_current_price: float 
    product_is_available: bool
    
@dataclass         
class Orders:
   order_id: int  
   shop_id: int
   ordered_at: datetime
   order_status: str  # 'completed', 'cancelled', 'refunded'
   order_subtotal: float
   order_tax: float
   order_total: float
   
@dataclass
class OrderItem:
   shop_id: int
   order_id : int
   product_id : int
   quantity : int
   unit_price : float 
   line_total : float 
   
@dataclass
class Payment:
   shop_id: int
   order_id : int
   paid_at : datetime
   payment_method : str
   payment_status : str
   payment_amount : float
   
PAYMENT_METHOD = ['cash', 'card']
PAYMENT_STATUS = ['pending', 'completed', 'cancelled']

generated_addresses = set()

def generate_unique_address() -> Address:
    while True:
        city = random.choice(list(TURKIYE_GEOGRAPHY.keys()))
        district = random.choice(TURKIYE_GEOGRAPHY[city])
        building_no = str(random.randint(1, 120))
        street_no = str(random.randint(1, 180))
        
        address_token = (street_no, building_no, district, city)
        
        if address_token not in generated_addresses:
            generated_addresses.add(address_token)
            return Address(
                building_no=building_no,
                street_no=street_no,
                district=district,
                city=city
            )

SHOP_SUFFIXES = ["Shop", "Cafe", "Coffee", "Roasters", "Corner"]
generated_shop_names = set()

def generate_unique_shop_name() -> str:
    while True:
        owner_name = fake.first_name() 
        suffix = random.choice(SHOP_SUFFIXES)
        
        if owner_name.endswith('s'):
            name_candidate = f"{owner_name}' {suffix}"
        else:
            name_candidate = f"{owner_name}'s {suffix}"
            
        if name_candidate not in generated_shop_names:
            generated_shop_names.add(name_candidate)
            return name_candidate

generated_phones = set()

def generate_unique_phone() -> str:
    while True:
        phone = fake.phone_number()
        if phone not in generated_phones:
            generated_phones.add(phone)
            return phone


def minutes_to_time(minutes: float) -> time:
    """Helper to clamp minutes within a 24-hour cycle and return a time object."""
    total_minutes = int(minutes) % 1440
    hours = total_minutes // 60
    mins = total_minutes % 60
    return time(hours, mins)
    
    
def generate_coffee_shop(shop_index: int) -> CoffeeShop:
    shop_name = generate_unique_shop_name()
    shop_address = generate_unique_address()
    shop_phone = generate_unique_phone()
    
    start_date = date(1950, 1, 1)
    end_date = date(2026, 1, 1)
    random_days = random.randint(0, (end_date - start_date).days)
    shop_opened_at = start_date + timedelta(days=random_days)
    
    
        
    
    open_minutes = random.gauss(mu=465, sigma=30)
    opening_time = minutes_to_time(open_minutes)
    
    close_minutes = random.gauss(mu=1440, sigma=60)
    closing_time = minutes_to_time(close_minutes)
    operating_hours = [(opening_time, closing_time)]
    
    return CoffeeShop(
        shop_id=shop_index,
        shop_name=shop_name,
        shop_address=shop_address,
        shop_phone=shop_phone,
        shop_opened_at=shop_opened_at
        operating_hours=operating_hours
    )

EMPLOYEE_GENDER = ['Female', 'Male', 'Intersex']
GENDER_WEIGHTS = [51.90, 47.2, 1.7]

def generate_employee_first_name(gender: str) -> str:
    if gender == 'Male':
        first_name = fake.first_name_male()
    elif gender == 'Female':
        first_name = fake.first_name_female()
    else:
        first_name = fake.first_name()
    return first_name

def generate_employee_middle_name(gender: str, first_name: str) -> Optional[str]:
    if random.random() > 0.25:
        return None
        
    while True:
        if gender == 'Male':
            mid = fake.first_name_male()
        elif gender == 'Female':
            mid = fake.first_name_female()
        else:
            mid = fake.first_name()
        
        if mid != first_name:
            return mid

def generate_employee_surname_name() -> str:
    return fake.last_name()

def generate_employee_dob(employee_hire_date: date) -> date:
    while True:
        age_in_years = random.gauss(23.0, 4.5)
        if age_in_years >= 16.0:
            break
    age_in_days = int(age_in_years * 365.25)
    dob = employee_hire_date - timedelta(days=age_in_days)
    return dob

def determine_shop_capacity() -> int:
    capacity = int(random.gauss(6.0, 2.0))
    return max(3, min(capacity, 12))

def allocate_roles_for_shop(total_employees: int) -> List[str]:
    roles = []
    if total_employees >= 8:
        roles.extend(['manager', 'manager']) 
    else:
        roles.append('manager')  
    remaining_slots = total_employees - len(roles)
    pool_options = ['barista', 'cashier']
    pool_weights = [0.65, 0.35]
    
    allocated_staff = random.choices(pool_options, weights=pool_weights, k=remaining_slots)
    roles.extend(allocated_staff)
    
    random.shuffle(roles)
    return roles

def generate_employee_hire_date(shop_opened_at: date) -> date:
    today = date.today()
    window_in_days = (today - shop_opened_at).days
    if window_in_days <= 0:
        return shop_opened_at
    random_days_to_add = random.randint(0, window_in_days)
    hire_date = shop_opened_at + timedelta(days=random_days_to_add)
    return hire_date

def generate_expected_tenure_days() -> int:
    mean_days = 16 * 30
    std_dev_days = 4 * 30
    tenure_days = int(random.gauss(mean_days, std_dev_days))
    return max(15, min(tenure_days, 5 * 365))

def determine_termination_reason(gender: str) -> str:
    gender_lower = gender.lower()
    if gender_lower == 'male':
        fired_chance = 0.22
    else:
        fired_chance = 0.14
    
    if random.random() < fired_chance:
        return 'fired'
    else:
        return 'voluntary'

def determine_employment_status(gender: str, dob: date, hire_date: date) -> tuple:
    today = date.today()
    current_age = (today - dob).days / 365.25
    days_since_hired = (today - hire_date).days
    
    expected_tenure_days = generate_expected_tenure_days()
    
    if days_since_hired > expected_tenure_days:
        return ('terminated', None)
    
    gender_lower = gender.lower()
    
    if gender_lower == 'male' and 20 <= current_age <= 30:
        if random.random() < 0.65:  
            suspension_duration = 6 * 30
            
            if days_since_hired + suspension_duration > expected_tenure_days:
                return ('terminated', None)
            
            if random.random() < 0.18:
                return ('terminated', None)
            
            return ('suspended', 'military service')
    
    if gender_lower == 'female' and 27 <= current_age <= 30:
        if random.random() < 0.18:
            if random.random() < 0.56:  
                return ('terminated', None)
            else:
                suspension_duration = 4 * 30
                
                if random.random() < 0.75:  
                    return ('terminated', None)
                else:
                    if days_since_hired + suspension_duration > expected_tenure_days:
                        return ('terminated', None)
                    return ('suspended', 'maternity leave')
    
    if days_since_hired > 180:
        annual_turnover_chance = 0.76
        daily_turnover_chance = 1 - (1 - annual_turnover_chance) ** (1/365)
        
        if random.random() < daily_turnover_chance:
            return ('terminated', None)
    
    return ('active', None)

def generate_employee(parent_shop: CoffeeShop, assigned_role: str) -> Employee:
    gender = random.choices(EMPLOYEE_GENDER, weights=GENDER_WEIGHTS, k=1)[0]
    first_name = generate_employee_first_name(gender)
    middle_name = generate_employee_middle_name(gender, first_name)
    surname = generate_employee_surname_name()
    
    hire_date = generate_employee_hire_date(parent_shop.shop_opened_at)
    dob = generate_employee_dob(hire_date)
    
    status, suspension_reason = determine_employment_status(gender, dob, hire_date)
    
    return Employee(
        shop_id=parent_shop.shop_id,
        employee_first_name=first_name,
        employee_surname_name=surname,
        employee_middle_name=middle_name,
        employee_gender=gender.lower(),
        employee_dob=dob,
        employee_role=assigned_role,
        employee_hire_date=hire_date,
        employee_current_status=status,
        reason_for_suspension=suspension_reason if suspension_reason else 'active'
    )

PRODUCT_BASELINE = {
    "Hot Drinks": {
        "Espresso": 55.00, "Double Espresso": 75.00, "Americano": 55.00, "Long Black": 60.00,
        "Cappuccino": 70.00, "Caffe Latte": 75.00, "Flat White": 70.00, "Mocha": 85.00,
        "Caramel Macchiato": 90.00, "Vanilla Latte": 80.00, "Hazelnut Latte": 80.00,
        "Turkish Coffee (Sade)": 60.00, "Turkish Coffee (Az Şekerli)": 60.00,
        "Turkish Coffee (Orta Şekerli)": 60.00, "Turkish Coffee (Şekerli)": 60.00,
        "Turkish Coffee with Cardamom": 75.00, "Turkish Coffee with Mastic": 80.00,
        "Dibek Coffee": 70.00, "Menengiç Coffee": 75.00, "Filter Coffee (Colombia)": 65.00,
        "Filter Coffee (Ethiopia)": 70.00, "Filter Coffee (Brazil)": 65.00,
        "Cold Brew (Hot Service)": 80.00, "Masala Chai": 120.00, "Turmeric Latte": 110.00,
        "Matcha Latte": 100.00, "Golden Milk": 105.00, "London Fog": 85.00, "Dirty Chai": 130.00,
        "Affogato": 95.00, "Cortado": 65.00, "Macchiato": 60.00, "Hot Chocolate": 75.00,
        "White Hot Chocolate": 80.00, "Sahlep (Winter Special)": 90.00, "Boza (Winter Special)": 85.00,
        "Salep with Cinnamon": 95.00
    },
    "Cold Drinks": {
        "Iced Americano": 70.00, "Iced Latte": 85.00, "Iced Vanilla Latte": 95.00,
        "Iced Caramel Latte": 95.00, "Iced Mocha": 100.00, "Iced Matcha Latte": 105.00,
        "Iced Chai": 100.00, "Cold Brew": 90.00, "Nitro Cold Brew": 110.00, "Frappe": 110.00,
        "Caramel Frappe": 120.00, "Mocha Frappe": 120.00, "Turkish Ice Coffee": 85.00,
        "Lemonade": 70.00, "Strawberry Lemonade": 85.00, "Peach Lemonade": 85.00,
        "Iced Tea": 65.00, "Peach Iced Tea": 75.00, "Thai Iced Tea": 95.00, "Ayran (Cold)": 50.00,
        "Smoothie (Berry)": 130.00, "Smoothie (Mango)": 130.00, "Smoothie (Banana)": 130.00,
        "Milkshake (Chocolate)": 115.00, "Milkshake (Strawberry)": 115.00, "Milkshake (Vanilla)": 115.00,
        "Orange Juice (Fresh)": 80.00, "Pomegranate Juice (Fresh)": 85.00, "Carrot Juice (Fresh)": 75.00,
        "Watermelon Juice (Seasonal)": 70.00, "Kefir": 90.00, "Şalgam (Cold)": 60.00
    },
    "Bakery & Pastry": {
        "Croissant (Plain)": 65.00, "Chocolate Croissant": 80.00, "Almond Croissant": 90.00,
        "San Sebastian Cheesecake": 150.00, "New York Cheesecake": 140.00, "Chocolate Cookie": 55.00,
        "Brownie (Classic)": 70.00, "Muffin (Blueberry)": 65.00, "Banana Bread": 80.00,
        "Carrot Cake": 120.00
    }
}

def get_employees_by_shop(shop_id: int, all_employees: List[Employee]) -> List[Employee]:
    return [emp for emp in all_employees if emp.shop_id == shop_id]
    
def calculate_shop_price_modifier(shop: CoffeeShop, total_employees: int) -> float:
    district = shop.shop_address.district
    location_multiplier = LOCATION_PREMIUMS.get(district, 1.00)
    labor_multiplier = 1.0 + (total_employees * 0.02)
    return location_multiplier * labor_multiplier   
    
def generate_shop_products(shop: CoffeeShop, total_employees: int) -> List[Product]:
    shop_products = []
    price_modifier = calculate_shop_price_modifier(shop, total_employees)
    pid_counter = 1
    for category, products in PRODUCT_BASELINE.items():
        for product_name, base_price in products.items():
            if random.random() < 0.75:
                final_price = round(base_price * price_modifier, 2)
                is_available = random.choices([True, False], weights=[0.93, 0.07], k=1)[0]
                new_product = Product(
                    product_id=pid_counter,
                    shop_id=shop.shop_id,
                    product_name=product_name,
                    product_category=category,
                    product_current_price=final_price, 
                    product_is_available=is_available
                )
                shop_products.append(new_product)
                pid_counter += 1
    return shop_products   
    
def generate_shop_staff(shop: CoffeeShop) -> List[Employee]:
    all_employees: List[Employee] = []
    
    target_active_managers = random.randint(1, 3)
    target_active_baristas = random.randint(1, 6)
    target_active_cashiers = random.randint(1, 4)
    target_active_waiters = random.randint(1, 6)
    
    if (target_active_managers == 1 and target_active_baristas == 1 and 
        target_active_cashiers == 1 and target_active_waiters == 1):
        if random.random() < 0.85: 
            target_active_baristas = random.randint(2, 4)
            target_active_waiters = random.randint(2, 4)

    active_counts = {
        'manager': 0,
        'barista': 0,
        'cashier': 0,
        'waiter': 0
    }
    
    while (active_counts['manager'] < target_active_managers or
           active_counts['barista'] < target_active_baristas or
           active_counts['cashier'] < target_active_cashiers or
           active_counts['waiter'] < target_active_waiters):
        
        needed_roles = [role for role, target in {
            'manager': target_active_managers,
            'barista': target_active_baristas,
            'cashier': target_active_cashiers,
            'waiter': target_active_waiters
        }.items() if active_counts[role] < target]
        
        chosen_role = random.choice(needed_roles)
        new_emp = generate_employee(shop, chosen_role)
        all_employees.append(new_emp)
        
        if new_emp.employee_current_status == 'active':
            active_counts[chosen_role] += 1
            
    return all_employees



def generate_single_transaction(
    order_id: int, 
    shop: CoffeeShop, 
    shop_products: List[Product]
) -> Optional[Tuple[Orders, List[OrderItem], Payment]]:
    """
    Simultaneously populates parent Order, multiple UNIQUE OrderItems with 
    distinct quantities, and the Payment to guarantee realistic shopping carts.
    """
    if not shop_products:
        return None  
        
    today = date.today()
    days_open = (today - shop.shop_opened_at).days
    
    if days_open <= 0:
        ordered_at = shop.shop_opened_at
    else:
        random_days = random.randint(0, days_open)
        ordered_at = shop.shop_opened_at + timedelta(days=random_days)
        
    available_products = [p for p in shop_products if p.product_is_available]
    if not available_products:
        available_products = shop_products  
        
    
    max_cart_variety = min(len(available_products), 4)
    cart_variety_size = random.choices(
        [1, 2, 3, 4], 
        weights=[0.50, 0.35, 0.12, 0.03], 
        k=1
    )[0]
    cart_variety_size = min(cart_variety_size, max_cart_variety)
    
    
    purchased_products = random.sample(available_products, k=cart_variety_size)
    
    
    order_items = []
    subtotal = 0.0
    
    for prod in purchased_products:
        
        quantity = random.choices([1, 2, 3], weights=[0.85, 0.12, 0.03], k=1)[0]
        unit_price = prod.product_current_price
        line_total = round(unit_price * quantity, 2)
        
        item = OrderItem(
            shop_id=shop.shop_id,
            order_id=order_id,
            product_id=prod.product_id,
            quantity=quantity,
            unit_price=unit_price,
            line_total=line_total
        )
        order_items.append(item)
        subtotal += line_total
        
    subtotal = round(subtotal, 2)
    tax_rate = 0.10 
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)
    
    
    order_status = random.choices(
        ['completed', 'cancelled', 'refunded'], 
        weights=[0.95, 0.03, 0.02], 
        k=1
    )[0]
    
   
    order = Orders(
        order_id=order_id,
        shop_id=shop.shop_id,
        ordered_at=ordered_at,
        order_status=order_status,
        order_subtotal=subtotal,
        order_tax=tax,
        order_total=total
    )
    
    
    pay_method = random.choice(PAYMENT_METHOD)
    
    if order_status == 'completed':
        pay_status = 'completed'
    elif order_status == 'cancelled':
        pay_status = 'cancelled'
    else:
        pay_status = random.choice(['completed', 'cancelled'])

    payment = Payment(
        shop_id=shop.shop_id,
        order_id=order_id,
        paid_at=ordered_at,
        payment_method=pay_method,
        payment_status=pay_status,
        amount=f"{total:.2f} TL"
    )
    
    return order, order_items, payment


if __name__ == "__main__":
    print("Creating coffee shops...")
    shops = []
    num_shops = 1  
    
    for i in range(1, num_shops + 1):
        shop = generate_coffee_shop(i)
        shops.append(shop)
        print(f"  Shop #{i}: {shop.shop_name} in {shop.shop_address.district}, {shop.shop_address.city}")
    
    print("\nGenerating employees and products...")
    all_employees = []
    employees_by_shop = {}
    products_by_shop = {}
    
    for shop in shops:
        employees = generate_shop_staff(shop)
        all_employees.extend(employees)
        employees_by_shop[shop.shop_id] = employees
        
        active_employees = [e for e in employees if e.employee_current_status == 'active']
        products = generate_shop_products(shop, len(active_employees))
        products_by_shop[shop.shop_id] = products
        
        print(f"  {shop.shop_name}: {len(employees)} employees ({len(active_employees)} active), {len(products)} products")
    
    print("\n" + "="*60)
    print("GENERATING INTERLOCKING TRANSACTION ENTRIES")
    print("="*60)
    
    all_orders: List[Orders] = []
    all_order_items: List[OrderItem] = []
    all_payments: List[Payment] = []
    order_id_counter = 10001
    
    for shop in shops:
        shop_products = products_by_shop[shop.shop_id]
        days_open = (date.today() - shop.shop_opened_at).days
        order_rate = random.uniform(0.1, 0.4)
        num_orders = int(days_open * order_rate)
        num_orders = max(5, num_orders)
        
        print(f"\nShop: '{shop.shop_name}' (ID: {shop.shop_id})")
        print(f"  -> Generating {num_orders} orders & items...")
        
        for _ in range(num_orders):
            transaction = generate_single_transaction(order_id_counter, shop, shop_products)
            if transaction:
                order, items, payment = transaction
                all_orders.append(order)
                all_order_items.extend(items)
                all_payments.append(payment)
                order_id_counter += 1
    
    print(f"\n{'='*60}")
    print(f"GENERATION COMPLETE!")
    print(f"  Total Orders: {len(all_orders)}")
    print(f"  Total OrderItems: {len(all_order_items)}")
    print(f"  Total Payments: {len(all_payments)}")
    print(f"{'='*60}")
    
   
    print("\nSample Transaction Match Checking (First 5 orders):")
    for idx, order in enumerate(all_orders[:]):
        shop = next(s for s in shops if s.shop_id == order.shop_id)
        print(f"\nOrder #{order.order_id} | Shop: {shop.shop_name} | Status: {order.order_status} | Total: ₺{order.order_total}")
        
       
        matching_items = [item for item in all_order_items if item.order_id == order.order_id]
        print("  Items Purchased:")
        for item in matching_items:
            prod_name = next(p.product_name for p in products_by_shop[shop.shop_id] if p.product_id == item.product_id)
            print(f"    - {prod_name} | Qty: {item.quantity} | Unit Price: ₺{item.unit_price} | Line Total: ₺{item.line_total}")
            
        
        matching_pay = next(p for p in all_payments if p.order_id == order.order_id)
        print(f"  Associated Payment: Method: {matching_pay.payment_method} | Status: {matching_pay.payment_status} | Paid amount: {matching_pay.amount}")
