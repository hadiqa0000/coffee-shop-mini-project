from __future__ import annotations
from dataclasses import dataclass
import datetime 
from datetime import date, timedelta
import random
from faker import Faker
from typing import Optional, List
import math



fake = Faker('tr_TR')

TURKIYE_GEOGRAPHY = {
    "Istanbul": ["Kadikoy", "Besiktas", "Fatih", "Uskudar", "Sisli", "Sariyer", "Avcilar"],
    "Ankara": ["Cankaya", "Keçiören", "Yenimahalle", "Etimesgut"],
    "Izmir": ["Karsiyaka", "Konak", "Bornova", "Buca"],
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
    shop_id : int
    product_name: str
    product_category : str
    product_current_price : str
    product_is_available : bool


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

def generate_coffee_shop(shop_index: int) -> CoffeeShop:
    shop_name = generate_unique_shop_name()
    shop_address = generate_unique_address()
    shop_phone = generate_unique_phone()
    
    start_date = date(1950, 1, 1)
    end_date = date(2026, 1, 1)
    random_days = random.randint(0, (end_date - start_date).days)
    shop_opened_at = start_date + timedelta(days=random_days)
    
    return CoffeeShop(
        shop_id=shop_index,
        shop_name=shop_name,
        shop_address=shop_address,
        shop_phone=shop_phone,
        shop_opened_at=shop_opened_at
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
    surname = fake.last_name()
    return surname

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
        "Espresso": 45.00,
        "Caffe Latte": 65.00,
        "Turkish Coffee": 50.00,
        "Filter Coffee": 55.00
    },
    "Cold Drinks": {
        "Iced Latte": 70.00,
        "Cold Brew": 75.00,
        "Iced Americano": 60.00
    },
    "Bakery & Pastry": {
        "Croissant": 55.00,
        "San Sebastian Cheesecake": 120.00,
        "Chocolate Cookie": 45.00
    }
}

LOCATION_PREMIUMS = {
    "Kadikoy": 1.25, "Besiktas": 1.25, "Sisli": 1.25, "Cankaya": 1.25,
    "Uskudar": 1.10, "Karsiyaka": 1.10, "Bornova": 1.10, "Yenimahalle": 1.10,
    "Fatih": 1.00, "Sariyer": 1.15, "Konak": 1.05,
    "Avcilar": 0.90, "Keçiören": 0.90, "Etimesgut": 0.90, "Buca": 0.90
} 

def get_employees_by_shop(shop_id: int, all_employees: List[Employee]) -> List[Employee]:
    """Get all employees working at a specific coffee shop."""
    return [emp for emp in all_employees if emp.shop_id == shop_id]

    
def calculate_shop_price_modifier(shop: CoffeeShop, total_employees: int) -> float:
    # Uses the total_employees passed down to compute labor premium
    district = shop.shop_address.district
    location_multiplier = LOCATION_PREMIUMS.get(district, 1.00)
    labor_multiplier = 1.0 + (total_employees * 0.02)
    return location_multiplier * labor_multiplier   
    
    
def generate_shop_products(shop: CoffeeShop, total_employees: int) -> list[Product]:
    shop_products = []
    price_modifier = calculate_shop_price_modifier(shop, total_employees)
    for category, products in PRODUCT_BASELINE.items():
        for product_name, base_price in products.items():
            if random.random() < 0.75:
                # Apply the modifier to the baseline price
                final_price = round(base_price * price_modifier, 2)
                is_available = random.choices([True, False], weights=[0.93, 0.07], k=1)[0]
                new_product = Product(
                    shop_id=shop.shop_id,
                    product_name=product_name,
                    product_category=category,
                    product_current_price=f"{final_price:.2f} TL",
                    product_is_available=is_available
                )
                shop_products.append(new_product)
                
                
    return shop_products   
    
    
    
    
def generate_shop_staff(shop: CoffeeShop) -> List[Employee]:
    """
    Generates employees for a shop, ensuring strict active staff minimums:
    - At least 1 Active Manager (Max 3)
    - At least 1 Active Barista (Max 6)
    - At least 1 Active Cashier (Max 4)
    - At least 1 Active Waiter (Max 6)
    
    It will keep hiring (generating) employees until these conditions are met.
    """
    all_employees: List[Employee] = []
    
    # Define our targets for ACTIVE staff
    # We will randomly choose a target capacity for this shop within your limits
    target_active_managers = random.randint(1, 3)
    target_active_baristas = random.randint(1, 6)
    target_active_cashiers = random.randint(1, 4)
    target_active_waiters = random.randint(1, 6)
    
    # It is rare to have only 1 of everything, so let's make sure that if 
    # everything rolled a 1, we occasionally boost them to make it look natural
    if (target_active_managers == 1 and target_active_baristas == 1 and 
        target_active_cashiers == 1 and target_active_waiters == 1):
        if random.random() < 0.85: # 85% of the time, boost some roles
            target_active_baristas = random.randint(2, 4)
            target_active_waiters = random.randint(2, 4)

    # We track how many ACTIVE employees of each role we currently have
    active_counts = {
        'manager': 0,
        'barista': 0,
        'cashier': 0,
        'waiter': 0
    }
    
    # We keep hiring until all our active targets are satisfied
    while (active_counts['manager'] < target_active_managers or
           active_counts['barista'] < target_active_baristas or
           active_counts['cashier'] < target_active_cashiers or
           active_counts['waiter'] < target_active_waiters):
        
        # Decide which role we need to hire next
        needed_roles = [role for role, target in {
            'manager': target_active_managers,
            'barista': target_active_baristas,
            'cashier': target_active_cashiers,
            'waiter': target_active_waiters
        }.items() if active_counts[role] < target]
        
        # Hire for one of the missing roles
        chosen_role = random.choice(needed_roles)
        new_emp = generate_employee(shop, chosen_role)
        all_employees.append(new_emp)
        
        # If the newly hired employee rolled an 'active' status, increment our count!
        if new_emp.employee_current_status == 'active':
            active_counts[chosen_role] += 1
            
    return all_employees


# Quick verification test
# Quick verification test
if __name__ == "__main__":
    # 1. Generate a shop
    shop = generate_coffee_shop(1)
    print(f"Shop Name: {shop.shop_name}")
    print(f"Address:   {shop.shop_address.to_string()}")
    print(f"Opened:    {shop.shop_opened_at}")
    print("\n" + "="*50)
    print("HIRING STAFF (Ensuring active minimums are met)...")
    print("="*50)
    
    # 2. Generate staff using our strict constraint solver loop
    all_employees = generate_shop_staff(shop)
    
    # 3. Print out the results to verify
    active_employees = [e for e in all_employees if e.employee_current_status == 'active']
    suspended_employees = [e for e in all_employees if e.employee_current_status == 'suspended']
    terminated_employees = [e for e in all_employees if e.employee_current_status == 'terminated']
    
    print(f"\nTotal Hired Historically: {len(all_employees)}")
    print(f"Total Currently Active:   {len(active_employees)}")
    print(f"Total Suspended:          {len(suspended_employees)}")
    print(f"Total Terminated:         {len(terminated_employees)}")
    
    # Let's count active roles to make sure our limits worked
    active_by_role = {'manager': 0, 'barista': 0, 'cashier': 0, 'waiter': 0}
    for e in active_employees:
        active_by_role[e.employee_role] += 1
        
    print("\nActive Staff Breakdown:")
    for role, count in active_by_role.items():
        print(f"  - {role.capitalize()}s: {count}")
        
    # 4. Generate Products using our guaranteed active count!
    products = generate_shop_products(shop, total_employees=len(active_employees))
    
    print("\n" + "="*20 + " GENERATED PRODUCTS " + "="*20)
    for prod in products[:5]: # Print first 5 products as sample
        status_str = "In Stock" if prod.product_is_available else "Out of Stock"
        print(f"- [{prod.product_category}] {prod.product_name}: {prod.product_current_price} ({status_str})")
