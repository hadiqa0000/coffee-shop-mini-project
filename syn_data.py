from __future__ import annotations
from dataclasses import dataclass
import datetime 
from datetime import date, timedelta, time, datetime
import random
from faker import Faker
from typing import Optional, List, Dict, Tuple
import psycopg2
from psycopg2.extras import execute_values
import json
import re
import numpy as np  # Added for Poisson distribution

fake = Faker('tr_TR')
existing_address_strings = set()

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

INFLATION_DATA = {
    2020: 1.146,
    2021: 1.560,
    2022: 2.562,
    2023: 4.221,
    2024: 6.094,
    2025: 8.136,
    2026: 10.658
}

# ============ NEW: Random Walk & Markov Process Classes ============

class RandomWalkGenerator:
    """Geometric Brownian Motion with mean reversion"""
    
    def __init__(self, initial_value: float, volatility: float = 0.15, 
                 drift: float = 0.0005, mean_reversion: float = 0.05,
                 long_term_mean: Optional[float] = None):
        """
        Args:
            initial_value: Starting value (e.g., daily orders)
            volatility: σ - daily volatility (0.15 = 15%)
            drift: μ - daily growth trend (0.0005 = 0.05% per day)
            mean_reversion: θ - strength of pull toward long-term mean (0.05 = 5%)
            long_term_mean: Target mean for reversion (if None, uses initial_value)
        """
        self.current_value = initial_value
        self.volatility = volatility
        self.drift = drift
        self.mean_reversion = mean_reversion
        self.long_term_mean = long_term_mean if long_term_mean is not None else initial_value
        self.history = [initial_value]
    
    def step(self) -> float:
        """Generate next value using mean-reverting geometric Brownian motion"""
        # Random shock from normal distribution
        epsilon = random.gauss(0, 1)
        
        # Calculate mean reversion component
        deviation_ratio = (self.long_term_mean - self.current_value) / self.long_term_mean
        reversion_component = self.mean_reversion * deviation_ratio
        
        # Combined change: drift + reversion + random shock
        total_change = self.drift + reversion_component + self.volatility * epsilon
        
        # Apply change multiplicatively (geometric Brownian motion)
        self.current_value *= (1 + total_change)
        
        # Ensure value stays positive
        self.current_value = max(self.current_value, 0.5)
        
        self.history.append(self.current_value)
        return self.current_value

class MarkovChain:
    """Markov chain for shop operational states"""
    
    STATES = ['booming', 'normal', 'slow', 'struggling']
    
    # Transition matrix: P(next_state | current_state)
    TRANSITION_MATRIX = {
        'booming': {'booming': 0.30, 'normal': 0.50, 'slow': 0.15, 'struggling': 0.05},
        'normal': {'booming': 0.20, 'normal': 0.50, 'slow': 0.25, 'struggling': 0.05},
        'slow': {'booming': 0.10, 'normal': 0.40, 'slow': 0.40, 'struggling': 0.10},
        'struggling': {'booming': 0.05, 'normal': 0.25, 'slow': 0.40, 'struggling': 0.30}
    }
    
    # State multipliers for order volume
    STATE_MODIFIERS = {
        'booming': 1.5,      # 50% more orders
        'normal': 1.0,       # baseline
        'slow': 0.7,         # 30% fewer orders
        'struggling': 0.4    # 60% fewer orders
    }
    
    # State modifiers for average ticket size
    TICKET_MODIFIERS = {
        'booming': 1.15,     # 15% higher spend
        'normal': 1.0,
        'slow': 0.9,
        'struggling': 0.8
    }
    
    def __init__(self, initial_state: str = 'normal'):
        if initial_state not in self.STATES:
            initial_state = 'normal'
        self.current_state = initial_state
        self.state_history = [initial_state]
        self.days_in_state = 0
    
    def step(self) -> str:
        """Transition to next state based on Markov process"""
        transitions = self.TRANSITION_MATRIX[self.current_state]
        next_state = random.choices(
            list(transitions.keys()),
            weights=list(transitions.values()),
            k=1
        )[0]
        
        # Update state
        if next_state == self.current_state:
            self.days_in_state += 1
        else:
            self.days_in_state = 0
            self.current_state = next_state
            
        self.state_history.append(self.current_state)
        return self.current_state
    
    def get_order_multiplier(self) -> float:
        """Get multiplier for expected orders based on current state"""
        return self.STATE_MODIFIERS[self.current_state]
    
    def get_ticket_multiplier(self) -> float:
        """Get multiplier for average ticket based on current state"""
        return self.TICKET_MODIFIERS[self.current_state]
    
    def get_state_duration(self) -> int:
        """Get number of consecutive days in current state"""
        return self.days_in_state

class ShopStateTracker:
    """Tracks all time-series state for a shop"""
    
    def __init__(self, shop_id: int, base_daily_orders: float = 30.0):
        self.shop_id = shop_id
        self.base_daily_orders = base_daily_orders
        self.current_avg_ticket = random.gauss(120, 30)  # Average order value ~120 TL
        
        # Initialize random walk for orders
        self.order_walk = RandomWalkGenerator(
            initial_value=base_daily_orders,
            volatility=random.uniform(0.10, 0.20),  # 10-20% daily volatility
            drift=random.uniform(-0.0002, 0.001),   # Slight positive or negative trend
            mean_reversion=0.05,
            long_term_mean=base_daily_orders
        )
        
        # Initialize random walk for average ticket
        self.ticket_walk = RandomWalkGenerator(
            initial_value=self.current_avg_ticket,
            volatility=0.08,      # 8% volatility
            drift=0.0003,         # 0.03% daily increase (inflation/price increases)
            mean_reversion=0.03,
            long_term_mean=self.current_avg_ticket
        )
        
        # Initialize Markov chain
        self.markov = MarkovChain(
            initial_state=random.choices(['booming', 'normal', 'slow'], 
                                        weights=[0.15, 0.65, 0.20])[0]
        )
        
        # Historical tracking
        self.daily_orders = []
        self.daily_revenue = []
        self.day_counter = 0
    
    def advance_day(self) -> Tuple[float, float, float]:
        """Advance one day and return (expected_orders, avg_ticket, state_multiplier)"""
        # 1. Update Markov state (weekly state changes)
        if self.day_counter % random.randint(5, 10) == 0:
            self.markov.step()
        
        # 2. Update random walks
        baseline_orders = self.order_walk.step()
        self.current_avg_ticket = self.ticket_walk.step()
        
        # 3. Apply Markov state multiplier
        state_multiplier = self.markov.get_order_multiplier()
        expected_orders = baseline_orders * state_multiplier
        
        # 4. Apply day-of-week effects
        day_of_week = (self.day_counter % 7)
        dow_multiplier = [1.0, 0.95, 0.95, 0.95, 1.1, 1.3, 1.2][day_of_week]
        expected_orders *= dow_multiplier
        
        # 5. Apply seasonality (month effects)
        month = (self.day_counter // 30) % 12
        season_multiplier = [0.8, 0.85, 0.9, 1.0, 1.1, 1.15, 
                           1.1, 1.0, 1.05, 1.0, 0.9, 0.85][month]
        expected_orders *= season_multiplier
        
        # 6. Generate actual orders using Poisson distribution
        # Use numpy for Poisson, or implement manually if numpy not available
        try:
            actual_orders = np.random.poisson(max(1, int(expected_orders)))
        except:
            # Fallback if numpy not available
            lam = max(1, int(expected_orders))
            actual_orders = random.choices(range(lam*2), 
                                          weights=[(lam**k * np.exp(-lam)) / np.math.factorial(k) 
                                                  for k in range(lam*2)])[0]
        
        self.daily_orders.append(actual_orders)
        self.day_counter += 1
        
        return actual_orders, self.current_avg_ticket, state_multiplier

# ============ END OF NEW CLASSES ============

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
    shop_opened_at: date
    operating_hours: list[tuple[time, time]]
    shop_markup_multiplier: float

@dataclass
class Employee:
    shop_id: int
    employee_first_name: str
    employee_surname_name: str
    employee_gender: str
    employee_dob: date 
    employee_role: str
    employee_hire_date: date
    employee_current_status: str
    employee_middle_name: Optional[str] = None
    reason_for_suspension: Optional[str] = None  
    
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
   order_status: str  
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
   amount : float

PAYMENT_METHOD = ['cash', 'card']
PAYMENT_STATUS = ['pending', 'completed', 'cancelled']

generated_addresses = set()

def generate_unique_address() -> Address:
    while True:
        city = random.choice(list(TURKIYE_GEOGRAPHY.keys()))
        district = random.choice(TURKIYE_GEOGRAPHY[city])
        building_no = str(random.randint(1, 120))
        street_no = str(random.randint(1, 180))
        
        addr = Address(building_no=building_no, street_no=street_no, district=district, city=city)
        address_string = addr.to_string()
        address_token = (street_no, building_no, district, city)
        
        if address_token not in generated_addresses and address_string not in existing_address_strings:
            generated_addresses.add(address_token)
            return addr

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
        raw_phone = fake.phone_number()
        clean_phone = re.sub(r'\D', '', raw_phone)
        if len(clean_phone) > 11:
            clean_phone = clean_phone[-11:]
        if clean_phone not in generated_phones and len(clean_phone) <= 11:
            generated_phones.add(clean_phone)
            return clean_phone
            
def minutes_to_time(minutes: float, step_minutes: int = 30) -> time:
    rounded_minutes = int(round(minutes / step_minutes) * step_minutes)
    total_minutes = rounded_minutes % 1440
    hours = total_minutes // 60
    mins = total_minutes % 60
    return time(hours, mins)
    
def generate_coffee_shop(shop_index: int) -> CoffeeShop:
    shop_name = generate_unique_shop_name()
    shop_address = generate_unique_address()
    shop_phone = generate_unique_phone()
    
    start_date = date(2020, 1, 1)
    end_date = date(2026, 1, 1)
    random_days = random.randint(0, (end_date - start_date).days)
    shop_opened_at = start_date + timedelta(days=random_days)
    
    open_minutes = random.gauss(mu=465, sigma=30)
    opening_time = minutes_to_time(open_minutes)
    
    close_minutes = random.gauss(mu=1440, sigma=60)
    closing_time = minutes_to_time(close_minutes)
    operating_hours = [(opening_time, closing_time)]
    
    shop_markup_multiplier = random.uniform(0.95, 1.05)
    
    return CoffeeShop(
        shop_id=shop_index,
        shop_name=shop_name,
        shop_address=shop_address,
        shop_phone=shop_phone,
        shop_opened_at=shop_opened_at,
        operating_hours=operating_hours,
        shop_markup_multiplier=shop_markup_multiplier
    )

EMPLOYEE_GENDER = ['Female', 'Male', 'Intersex']
GENDER_WEIGHTS = [51.90, 47.2, 1.7]

def generate_employee_first_name(gender: str) -> str:
    if gender == 'Male':
        return fake.first_name_male()
    elif gender == 'Female':
        return fake.first_name_female()
    return fake.first_name()

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
    return employee_hire_date - timedelta(days=age_in_days)

def get_staff_factor(employee_count: int) -> float:
    if employee_count <= 2:
        return 1.15
    elif employee_count <= 5:
        return 1.10
    elif employee_count <= 10:
        return 1.05
    elif employee_count <= 20:
        return 1.00
    elif employee_count <= 50:
        return 1.10
    return 1.20

def generate_employee_hire_date(shop_opened_at: date) -> date:
    today = date.today()
    window_in_days = (today - shop_opened_at).days
    if window_in_days <= 0:
        return shop_opened_at
    return shop_opened_at + timedelta(days=random.randint(0, window_in_days))

def generate_expected_tenure_days() -> int:
    return max(15, min(int(random.gauss(16 * 30, 4 * 30)), 5 * 365))

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
            if days_since_hired + 180 > expected_tenure_days:
                return ('terminated', None)
            return ('suspended', 'military service') if random.random() >= 0.18 else ('terminated', None)
            
    if gender_lower == 'female' and 27 <= current_age <= 30:
        if random.random() < 0.18:
            if random.random() < 0.56: 
                return ('terminated', None)
            elif days_since_hired + 120 <= expected_tenure_days and random.random() >= 0.75:
                return ('suspended', 'maternity leave')
            return ('terminated', None)
            
    if days_since_hired > 180 and random.random() < (1 - (1 - 0.76) ** (1/365)):
        return ('terminated', None)
    return ('active', None)

def generate_employee(parent_shop: CoffeeShop, assigned_role: str) -> Employee:
    gender = random.choices(EMPLOYEE_GENDER, weights=GENDER_WEIGHTS, k=1)[0]
    first_name = generate_employee_first_name(gender)
    middle_name = generate_employee_middle_name(gender, first_name)
    surname = generate_employee_surname_name()
    order_hire_date = generate_employee_hire_date(parent_shop.shop_opened_at)
    dob = generate_employee_dob(order_hire_date)
    status, suspension_reason = determine_employment_status(gender, dob, order_hire_date)
    
    return Employee(
        shop_id=parent_shop.shop_id,
        employee_first_name=first_name,
        employee_surname_name=surname,
        employee_middle_name=middle_name,
        employee_gender=gender.lower(),
        employee_dob=dob,
        employee_role=assigned_role,
        employee_hire_date=order_hire_date,
        employee_current_status=status,
        reason_for_suspension=suspension_reason if suspension_reason else None
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

def calculate_historical_price(base_price: float, shop: CoffeeShop, total_employees: int, target_year: int) -> float:
    inflation_factor = INFLATION_DATA.get(target_year, 10.658)
    location_premium = LOCATION_PREMIUMS.get(shop.shop_address.district, 1.00)
    staff_factor = get_staff_factor(total_employees)
    
    final_price = base_price * inflation_factor * location_premium * staff_factor * shop.shop_markup_multiplier
    return max(5.00, round(final_price, 2))

def generate_shop_products(shop: CoffeeShop, total_employees: int) -> List[Product]:
    shop_products = []
    pid_counter = 1
    for category, products in PRODUCT_BASELINE.items():
        for product_name, base_price in products.items():
            if random.random() < 0.75:
                current_price = calculate_historical_price(base_price, shop, total_employees, 2026)
                is_available = random.choices([True, False], weights=[0.93, 0.07], k=1)[0]
                shop_products.append(Product(
                    product_id=pid_counter,
                    shop_id=shop.shop_id,
                    product_name=product_name,
                    product_category=category,
                    product_current_price=current_price, 
                    product_is_available=is_available
                ))
                pid_counter += 1
    return shop_products   

def generate_shop_staff(shop: CoffeeShop) -> List[Employee]:
    all_employees: List[Employee] = []
    target_active_managers = random.randint(1, 3)
    target_active_baristas = random.randint(1, 6)
    target_active_cashiers = random.randint(1, 4)
    target_active_waiters = random.randint(1, 6)
    
    if target_active_managers == 1 and target_active_baristas == 1 and target_active_cashiers == 1 and target_active_waiters == 1:
        if random.random() < 0.85: 
            target_active_baristas = random.randint(2, 4)
            target_active_waiters = random.randint(2, 4)

    active_counts = {'manager': 0, 'barista': 0, 'cashier': 0, 'waiter': 0}
    
    while (active_counts['manager'] < target_active_managers or
           active_counts['barista'] < target_active_baristas or
           active_counts['cashier'] < target_active_cashiers or
           active_counts['waiter'] < target_active_waiters):
        
        needed_roles = [role for role, target in {
            'manager': target_active_managers, 'barista': target_active_baristas,
            'cashier': target_active_cashiers, 'waiter': target_active_waiters
        }.items() if active_counts[role] < target]
        
        chosen_role = random.choice(needed_roles)
        new_emp = generate_employee(shop, chosen_role)
        all_employees.append(new_emp)
        
        if new_emp.employee_current_status == 'active':
            active_counts[chosen_role] += 1
            
    return all_employees

# ============ MODIFIED: Transaction generation with time-series state ============

def generate_order_time(markov_state: str, day_counter: int) -> time:
    """Generate realistic order time based on Markov state"""
    # Peak hours (9-10 AM, 2-4 PM)
    peak_hours = [9, 10, 14, 15, 16]
    
    if markov_state == 'booming':
        # More orders during peak hours
        hour = random.choices(
            list(range(8, 21)),
            weights=[1,3,5,4,3,2,4,6,5,3,2,1,1],  # Peaks at 10 and 15
            k=1
        )[0]
    elif markov_state == 'struggling':
        # Flatter distribution, fewer peak concentration
        hour = random.randint(8, 20)
    else:
        # Normal distribution around 2 PM
        hour = int(random.gauss(14, 2.5))
        hour = max(8, min(20, hour))
    
    minute = random.randint(0, 59)
    return time(hour, minute)

def generate_transactions_for_shop(
    order_id_counter: int,
    shop: CoffeeShop,
    shop_products: List[Product],
    shop_state: ShopStateTracker,
    total_employees: int,
    max_days: Optional[int] = None
) -> Tuple[List[Orders], List[OrderItem], List[Payment], int]:
    """
    Generate transactions using random walk and Markov processes
    Returns: (orders, order_items, payments, new_order_id_counter)
    """
    all_orders = []
    all_items = []
    all_payments = []
    
    # Determine number of days to generate
    if max_days is None:
        days_open = (date.today() - shop.shop_opened_at).days
    else:
        days_open = max_days
    
    if days_open <= 0:
        days_open = 30  # Minimum 30 days if just opened
    
    # Generate day by day with time-series continuity
    for day in range(days_open):
        current_date = shop.shop_opened_at + timedelta(days=day)
        
        # Skip future dates
        if current_date > date.today():
            break
        
        # Advance the shop state for this day
        actual_orders, avg_ticket, state_multiplier = shop_state.advance_day()
        
        # Generate each order for this day
        for order_num in range(actual_orders):
            # Generate realistic order time
            order_hour = generate_order_time(shop_state.markov.current_state, day)
            order_time = datetime.combine(current_date, order_hour)
            
            # Generate the transaction
            transaction = generate_single_transaction_with_state(
                order_id_counter,
                shop,
                shop_products,
                total_employees,
                shop_state,
                order_time,
                avg_ticket
            )
            
            if transaction:
                order, items, payment = transaction
                all_orders.append(order)
                all_items.extend(items)
                all_payments.append(payment)
                order_id_counter += 1
    
    return all_orders, all_items, all_payments, order_id_counter

def generate_single_transaction_with_state(
    order_id: int,
    shop: CoffeeShop,
    shop_products: List[Product],
    total_employees: int,
    shop_state: ShopStateTracker,
    ordered_at: datetime,
    avg_ticket: float
) -> Optional[Tuple[Orders, List[OrderItem], Payment]]:
    """Generate a single transaction using shop state"""
    
    if not shop_products:
        return None
    
    # Get available products
    available_products = [p for p in shop_products if p.product_is_available]
    if not available_products:
        available_products = shop_products
    
    # Determine cart size based on average ticket
    # Average item price is around 70 TL
    avg_item_price = 70.0
    expected_items = max(1, int(avg_ticket / avg_item_price))
    
    # Add randomness to cart size (Poisson-like)
    cart_variety_size = min(
        random.choices(
            [1, 2, 3, 4, 5, 6],
            weights=[0.15, 0.25, 0.25, 0.20, 0.10, 0.05],
            k=1
        )[0],
        len(available_products)
    )
    
    # Apply Markov state modifier to ticket size
    ticket_multiplier = shop_state.markov.get_ticket_multiplier()
    effective_cart_size = max(1, min(
        int(cart_variety_size * ticket_multiplier),
        len(available_products)
    ))
    
    # Select products
    purchased_products = random.sample(available_products, k=effective_cart_size)
    
    order_items = []
    subtotal = 0.0
    
    for prod in purchased_products:
        # Quantity distribution influenced by state
        if shop_state.markov.current_state == 'booming':
            quantity = random.choices([1, 2, 3, 4], weights=[0.6, 0.25, 0.10, 0.05], k=1)[0]
        else:
            quantity = random.choices([1, 2, 3], weights=[0.85, 0.12, 0.03], k=1)[0]
        
        base_uninflated_price = PRODUCT_BASELINE[prod.product_category][prod.product_name]
        unit_price = calculate_historical_price(base_uninflated_price, shop, total_employees, ordered_at.year)
        line_total = round(unit_price * quantity, 2)
        
        order_items.append(OrderItem(
            shop_id=shop.shop_id,
            order_id=order_id,
            product_id=prod.product_id,
            quantity=quantity,
            unit_price=unit_price,
            line_total=line_total
        ))
        subtotal += line_total
    
    subtotal = round(subtotal, 2)
    tax = round(subtotal * 0.10, 2)
    total = round(subtotal + tax, 2)
    
    # Order status influenced by state
    if shop_state.markov.current_state == 'booming':
        order_status = random.choices(['pending', 'served', 'cancelled'], weights=[0.65, 0.30, 0.05], k=1)[0]
    elif shop_state.markov.current_state == 'struggling':
        order_status = random.choices(['pending', 'served', 'cancelled'], weights=[0.70, 0.20, 0.10], k=1)[0]
    else:
        order_status = random.choices(['pending', 'served', 'cancelled'], weights=[0.70, 0.25, 0.05], k=1)[0]
    
    order = Orders(
        order_id=order_id, shop_id=shop.shop_id, ordered_at=ordered_at,
        order_status=order_status, order_subtotal=subtotal, order_tax=tax, order_total=total
    )
    
    pay_method = random.choice(PAYMENT_METHOD)
    pay_status = 'completed' if order_status == 'completed' else (
        'cancelled' if order_status == 'cancelled' else random.choice(['completed', 'cancelled'])
    )
    
    payment = Payment(
        shop_id=shop.shop_id, order_id=order_id, paid_at=ordered_at,
        payment_method=pay_method, payment_status=pay_status, amount=total
    )
    
    return order, order_items, payment

# ============ END OF MODIFIED FUNCTIONS ============

if __name__ == "__main__":
    user_input = input("Enter the number of NEW coffee shops you want to generate: ").strip()
    num_shops = int(user_input)

    conn = None
    cursor = None
    start_shop_id = 1
    
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="hadiqaimrannn0",
            password="240303924",
            host="localhost",
            port="5432"
        )
        cursor = conn.cursor()
        print("\nChecking database for existing records to prevent duplicates...")

        cursor.execute("SELECT shop_name FROM CoffeeShop;")
        for row in cursor.fetchall():
            generated_shop_names.add(row[0])

        cursor.execute("SELECT shop_phone FROM CoffeeShop;")
        for row in cursor.fetchall():
            generated_phones.add(row[0])

        cursor.execute("SELECT shop_address FROM CoffeeShop;")
        for row in cursor.fetchall():
            existing_address_strings.add(row[0])

        cursor.execute("SELECT COALESCE(MAX(shop_id), 0) FROM CoffeeShop;")
        start_shop_id = cursor.fetchone()[0] + 1
        
        try:
            cursor.execute("SELECT COALESCE(MAX(order_id), 10000) FROM Orders;")
            order_id_counter = cursor.fetchone()[0] + 1
        except:
            order_id_counter = 10001
        
        print(f"-> Found {start_shop_id - 1} existing shops. Starting shop_id: {start_shop_id}, order_id: {order_id_counter}.")

    except Exception as error:
        print("\n❌ Failed to sync pre-existing database constraints:", error)
        if conn: conn.close()
        exit(1)

    CHUNK_SIZE = 50
    total_processed = 0
    
    print(f"\n🚀 Streaming data generation in chunks of {CHUNK_SIZE} shops with Random Walk & Markov processes...")
    
    try:
        for chunk_start in range(start_shop_id, start_shop_id + num_shops, CHUNK_SIZE):
            chunk_end = min(chunk_start + CHUNK_SIZE, start_shop_id + num_shops)
            print(f"Processing shops {chunk_start} to {chunk_end - 1}...")
            
            # Generate shops
            shops = [generate_coffee_shop(i) for i in range(chunk_start, chunk_end)]
            
            # Insert shops
            shop_id_map = {}
            for s in shops:
                hours_json = json.dumps([{"open": h[0].strftime('%H:%M'), "close": h[1].strftime('%H:%M')} for h in s.operating_hours])
                cursor.execute("""
                    INSERT INTO CoffeeShop (shop_name, shop_address, shop_phone, shop_opened_at, operating_hours, shop_markup_multiplier)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING shop_id;
                """, (s.shop_name, s.shop_address.to_string(), s.shop_phone, s.shop_opened_at, hours_json, s.shop_markup_multiplier))
                shop_id_map[s.shop_id] = cursor.fetchone()[0]

            # Generate employees and products
            chunk_employees = []
            employees_by_shop = {}
            products_by_shop = {}
            
            for shop in shops:
                employees = generate_shop_staff(shop)
                chunk_employees.extend(employees)
                employees_by_shop[shop.shop_id] = employees
                
                active_employees = [e for e in employees if e.employee_current_status == 'active']
                products_by_shop[shop.shop_id] = generate_shop_products(shop, len(active_employees))

            # Insert employees
            employee_id_map = {}
            emp_records = []
            emp_lookup = []
            for idx, e in enumerate(chunk_employees):
                db_shop_id = shop_id_map[e.shop_id]
                emp_records.append((
                    db_shop_id, e.employee_first_name, e.employee_middle_name, e.employee_surname_name,
                    e.employee_gender, e.employee_dob, e.employee_role, e.employee_hire_date,
                    e.employee_current_status, e.reason_for_suspension
                ))
                emp_lookup.append((e.shop_id, idx))
                
            inserted_emp_ids = execute_values(
                cursor, 
                """INSERT INTO Employee (shop_id, employee_first_name, employee_middle_name, employee_surname_name, employee_gender, employee_dob, employee_role, employee_hire_date, employee_current_status, reason_for_suspension) 
                   VALUES %s RETURNING employee_id;""", emp_records, fetch=True
            )
            for lookup_key, res_row in zip(emp_lookup, inserted_emp_ids):
                employee_id_map[lookup_key] = res_row[0]

            # Insert products
            product_id_map = {}
            prod_records = []
            prod_lookup = []
            for shop_id, prods in products_by_shop.items():
                db_shop_id = shop_id_map[shop_id]
                for p in prods:
                    prod_records.append((
                        db_shop_id, p.product_name, p.product_category, p.product_current_price, p.product_is_available
                    ))
                    prod_lookup.append((shop_id, p.product_id))
                    
            inserted_prod_ids = execute_values(
                cursor,
                """INSERT INTO Product (shop_id, product_name, product_category, product_current_price, product_is_available) 
                   VALUES %s RETURNING product_id;""", prod_records, fetch=True
            )
            for lookup_key, res_row in zip(prod_lookup, inserted_prod_ids):
                product_id_map[lookup_key] = res_row[0]

            # ============ MODIFIED: Generate transactions with time-series state ============
            chunk_orders = []
            chunk_items = []
            chunk_payments = []
            
            for shop in shops:
                shop_products = products_by_shop[shop.shop_id]
                active_staff_count = len([e for e in employees_by_shop[shop.shop_id] if e.employee_current_status == 'active'])
                
                # Initialize shop state with random walk and Markov
                base_orders = random.uniform(10, 50)  # Base daily orders
                shop_state = ShopStateTracker(shop.shop_id, base_orders)
                
                # Generate transactions using random walk and Markov
                orders, items, payments, order_id_counter = generate_transactions_for_shop(
                    order_id_counter,
                    shop,
                    shop_products,
                    shop_state,
                    active_staff_count,
                    max_days=None  # Generate from shop opening to today
                )
                
                chunk_orders.extend(orders)
                chunk_items.extend(items)
                chunk_payments.extend(payments)
                
                # Optional: Print summary for this shop
                if len(orders) > 0:
                    print(f"   Shop {shop.shop_id} ({shop.shop_name}): {len(orders)} orders over {shop_state.day_counter} days, "
                          f"avg {len(orders)/max(1, shop_state.day_counter):.1f}/day")

            # Insert orders
            order_id_map = {}
            order_records = []
            order_lookup = []
            shop_to_employees_cache = {}
            for (s_id, _), emp_id in employee_id_map.items():
                shop_to_employees_cache.setdefault(s_id, []).append(emp_id)

            for order in chunk_orders:
                db_shop_id = shop_id_map[order.shop_id]
                shop_emp_pool = shop_to_employees_cache.get(order.shop_id)
                assigned_emp_id = random.choice(shop_emp_pool) if shop_emp_pool else None
                order_records.append((
                    db_shop_id, assigned_emp_id, order.ordered_at, order.order_status,
                    order.order_subtotal, order.order_tax, order.order_total
                ))
                order_lookup.append(order.order_id)
                
            inserted_order_ids = execute_values(
                cursor,
                """INSERT INTO Orders (shop_id, employee_id, ordered_at, order_status, order_subtotal, order_tax, order_total) 
                   VALUES %s RETURNING order_id;""", order_records, fetch=True
            )
            for old_id, res_row in zip(order_lookup, inserted_order_ids):
                order_id_map[old_id] = res_row[0]

            # Insert order items
            item_records = []
            for item in chunk_items:
                item_records.append((
                    shop_id_map[item.shop_id], order_id_map[item.order_id], 
                    product_id_map[(item.shop_id, item.product_id)], item.quantity, item.unit_price
                ))
            execute_values(cursor, "INSERT INTO OrderItem (shop_id, order_id, product_id, quantity, unit_price) VALUES %s;", item_records)

            # Insert payments
            pay_records = []
            for pay in chunk_payments:
                pay_records.append((
                    shop_id_map[pay.shop_id], order_id_map[pay.order_id], 
                    pay.paid_at, pay.payment_method, pay.payment_status, pay.amount
                ))
            execute_values(cursor, "INSERT INTO Payment (shop_id, order_id, paid_at, payment_method, payment_status, payment_amount) VALUES %s;", pay_records)

            conn.commit()
            total_processed += len(shops)
            print(f"   -> Progress: Completed {total_processed}/{num_shops} shops cleanly.")

        print(f"\n🎉 Grand Success! All {num_shops} shops with time-series data written to database!")

    except Exception as error:
        print("\n❌ Error during execution chunk loop:", error)
        if conn: conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
