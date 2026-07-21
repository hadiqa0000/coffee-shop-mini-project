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
import numpy as np
import math

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

# ============ POISSON PROCESS CLASSES ============

class TimeOfDayIntensity:
    """Models customer arrival intensity throughout the day"""
    
    def __init__(self, opening_hour: int = 8, closing_hour: int = 22):
        self.opening_hour = opening_hour
        self.closing_hour = closing_hour
        
        # Define intensity profile for different times of day
        # These are multipliers that increase/decrease arrival rates
        self.hourly_intensity = {
            # Morning rush: 8-10 AM
            8: 0.6, 9: 1.8, 10: 1.5,
            # Late morning: 11-12
            11: 1.0, 12: 0.9,
            # Lunch rush: 1-2 PM
            13: 1.4, 14: 1.6,
            # Afternoon: 3-5 PM
            15: 1.1, 16: 1.0, 17: 0.9,
            # Evening rush: 6-8 PM
            18: 1.3, 19: 1.5, 20: 1.2,
            # Late evening: 9-10 PM
            21: 0.7, 22: 0.4
        }
        
        # Smooth the intensity curve using interpolation
        self.intensity_cache = {}
        self._build_intensity_cache()
    
    def _build_intensity_cache(self):
        """Build minute-by-minute intensity cache for smooth transitions"""
        for minute in range(0, 24 * 60):
            hour = minute // 60
            minute_of_hour = minute % 60
            
            # Get surrounding hours
            h1 = hour
            h2 = (hour + 1) % 24
            
            # Get intensities for surrounding hours (default to 0.5 if not defined)
            i1 = self.hourly_intensity.get(h1, 0.5)
            i2 = self.hourly_intensity.get(h2, 0.5)
            
            # Linear interpolation between hours
            fraction = minute_of_hour / 60.0
            intensity = i1 * (1 - fraction) + i2 * fraction
            
            # Apply opening/closing boundaries
            if hour < self.opening_hour or hour > self.closing_hour:
                intensity = 0.0
            elif hour == self.opening_hour and minute_of_hour < 30:
                # Gradual opening
                intensity = intensity * (minute_of_hour / 30.0)
            elif hour == self.closing_hour and minute_of_hour > 30:
                # Gradual closing
                intensity = intensity * (1 - (minute_of_hour - 30) / 30.0)
                if minute_of_hour > 45:
                    intensity = 0.0
            
            self.intensity_cache[minute] = max(0, intensity)
    
    def get_intensity(self, minute_of_day: int) -> float:
        """Get arrival intensity at a specific minute of day (0-1439)"""
        return self.intensity_cache.get(minute_of_day, 0.0)
    
    def get_average_intensity(self, base_rate: float = 1.0) -> float:
        """Calculate average intensity across the day"""
        total = sum(self.intensity_cache.values())
        return (total / (24 * 60)) * base_rate

class PoissonArrivalProcess:
    """
    Non-homogeneous Poisson process for customer arrivals
    λ(t) = base_rate * intensity_profile(t) * state_multiplier
    """
    
    def __init__(self, base_rate: float, intensity_profile: TimeOfDayIntensity):
        """
        Args:
            base_rate: Base arrivals per minute (e.g., 0.5 = 1 customer every 2 minutes)
            intensity_profile: TimeOfDayIntensity object
        """
        self.base_rate = base_rate
        self.intensity_profile = intensity_profile
        self.state_multiplier = 1.0  # Modified by Markov chain state
        self.arrival_history = []
        
    def set_state_multiplier(self, multiplier: float):
        """Update arrival rate based on Markov state"""
        self.state_multiplier = multiplier
    
    def get_rate_at(self, minute_of_day: int) -> float:
        """Get arrival rate at specific minute (arrivals per minute)"""
        base_intensity = self.intensity_profile.get_intensity(minute_of_day)
        return self.base_rate * base_intensity * self.state_multiplier
    
    def generate_arrival_times(self, start_time: time, end_time: time, 
                               max_arrivals: int = 1000) -> List[datetime]:
        """
        Generate arrival times using inverse transform sampling
        Returns list of datetime objects for each arrival
        """
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        
        arrivals = []
        current_time = start_minutes
        current_date = None
        
        # Use thinning method for non-homogeneous Poisson
        max_rate = max([self.get_rate_at(m) for m in range(start_minutes, end_minutes)]) * 1.2
        
        while len(arrivals) < max_arrivals:
            # Generate exponential inter-arrival time
            if max_rate > 0:
                u = random.random()
                inter_arrival = -math.log(u) / max_rate if u > 0 else 0
            else:
                break
            
            # Advance time
            current_time += inter_arrival * 60  # Convert minutes to seconds
            current_time = min(current_time, end_minutes)
            
            # Accept or reject based on thinning
            if current_time >= end_minutes:
                break
                
            current_minute = int(current_time)
            current_rate = self.get_rate_at(current_minute)
            
            # Thinning acceptance probability
            accept_prob = current_rate / max_rate if max_rate > 0 else 0
            
            if random.random() < accept_prob:
                # Create datetime for this arrival
                hours = current_minute // 60
                mins = current_minute % 60
                
                # Randomize seconds within the minute
                seconds = random.randint(0, 59)
                arrival_dt = datetime.combine(
                    date.today(), 
                    time(hours, mins, seconds)
                )
                arrivals.append(arrival_dt)
        
        return arrivals

# ============ RANDOM WALK & MARKOV CHAIN (from previous) ============

class RandomWalkGenerator:
    """Geometric Brownian Motion with mean reversion"""
    
    def __init__(self, initial_value: float, volatility: float = 0.15, 
                 drift: float = 0.0005, mean_reversion: float = 0.05,
                 long_term_mean: Optional[float] = None):
        self.current_value = initial_value
        self.volatility = volatility
        self.drift = drift
        self.mean_reversion = mean_reversion
        self.long_term_mean = long_term_mean if long_term_mean is not None else initial_value
        self.history = [initial_value]
    
    def step(self) -> float:
        epsilon = random.gauss(0, 1)
        deviation_ratio = (self.long_term_mean - self.current_value) / self.long_term_mean
        reversion_component = self.mean_reversion * deviation_ratio
        total_change = self.drift + reversion_component + self.volatility * epsilon
        self.current_value *= (1 + total_change)
        self.current_value = max(self.current_value, 0.5)
        self.history.append(self.current_value)
        return self.current_value

class MarkovChain:
    """Markov chain for shop operational states"""
    
    STATES = ['booming', 'normal', 'slow', 'struggling']
    
    TRANSITION_MATRIX = {
        'booming': {'booming': 0.30, 'normal': 0.50, 'slow': 0.15, 'struggling': 0.05},
        'normal': {'booming': 0.20, 'normal': 0.50, 'slow': 0.25, 'struggling': 0.05},
        'slow': {'booming': 0.10, 'normal': 0.40, 'slow': 0.40, 'struggling': 0.10},
        'struggling': {'booming': 0.05, 'normal': 0.25, 'slow': 0.40, 'struggling': 0.30}
    }
    
    STATE_MODIFIERS = {
        'booming': 1.5,
        'normal': 1.0,
        'slow': 0.7,
        'struggling': 0.4
    }
    
    TICKET_MODIFIERS = {
        'booming': 1.15,
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
        transitions = self.TRANSITION_MATRIX[self.current_state]
        next_state = random.choices(
            list(transitions.keys()),
            weights=list(transitions.values()),
            k=1
        )[0]
        
        if next_state == self.current_state:
            self.days_in_state += 1
        else:
            self.days_in_state = 0
            self.current_state = next_state
            
        self.state_history.append(self.current_state)
        return self.current_state
    
    def get_order_multiplier(self) -> float:
        return self.STATE_MODIFIERS[self.current_state]
    
    def get_ticket_multiplier(self) -> float:
        return self.TICKET_MODIFIERS[self.current_state]

class ShopStateTracker:
    """Tracks all time-series state for a shop"""
    
    def __init__(self, shop_id: int, opening_hour: int = 8, closing_hour: int = 22):
        self.shop_id = shop_id
        self.opening_hour = opening_hour
        self.closing_hour = closing_hour
        
        # Base arrival rate (customers per minute)
        # Typical coffee shop: 0.3-1.0 customers per minute (18-60 per hour)
        self.base_arrival_rate = random.uniform(0.3, 0.8)
        
        # Initialize intensity profile
        self.intensity_profile = TimeOfDayIntensity(opening_hour, closing_hour)
        
        # Initialize Poisson arrival process
        self.arrival_process = PoissonArrivalProcess(
            base_rate=self.base_arrival_rate,
            intensity_profile=self.intensity_profile
        )
        
        # Initialize random walk for daily total orders
        # Daily total = base_rate * minutes_open * average_intensity
        avg_intensity = self.intensity_profile.get_average_intensity()
        initial_daily_orders = int(self.base_arrival_rate * (closing_hour - opening_hour) * 60 * avg_intensity)
        initial_daily_orders = max(10, initial_daily_orders)
        
        self.order_walk = RandomWalkGenerator(
            initial_value=initial_daily_orders,
            volatility=random.uniform(0.10, 0.20),
            drift=random.uniform(-0.0002, 0.001),
            mean_reversion=0.05,
            long_term_mean=initial_daily_orders
        )
        
        # Initialize random walk for average ticket
        self.current_avg_ticket = random.gauss(120, 30)
        self.ticket_walk = RandomWalkGenerator(
            initial_value=self.current_avg_ticket,
            volatility=0.08,
            drift=0.0003,
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
        self.total_arrivals = []
    
    def advance_day(self) -> Tuple[int, float, float]:
        """Advance one day and return (actual_orders, avg_ticket, state_multiplier)"""
        # Update Markov state
        if self.day_counter % random.randint(5, 10) == 0:
            self.markov.step()
        
        # Update random walks
        expected_daily_orders = self.order_walk.step()
        self.current_avg_ticket = self.ticket_walk.step()
        
        # Apply Markov state multiplier
        state_multiplier = self.markov.get_order_multiplier()
        self.arrival_process.set_state_multiplier(state_multiplier)
        
        # Apply day-of-week effects
        day_of_week = (self.day_counter % 7)
        dow_multiplier = [1.0, 0.95, 0.95, 0.95, 1.1, 1.3, 1.2][day_of_week]
        expected_daily_orders *= dow_multiplier
        
        # Apply seasonality
        month = (self.day_counter // 30) % 12
        season_multiplier = [0.8, 0.85, 0.9, 1.0, 1.1, 1.15, 
                           1.1, 1.0, 1.05, 1.0, 0.9, 0.85][month]
        expected_daily_orders *= season_multiplier
        
        # Generate actual orders using Poisson
        try:
            actual_orders = np.random.poisson(max(1, int(expected_daily_orders)))
        except:
            # Fallback
            lam = max(1, int(expected_daily_orders))
            actual_orders = random.choices(range(lam*2), 
                                          weights=[(lam**k * math.exp(-lam)) / math.factorial(k) 
                                                  for k in range(lam*2)])[0]
        
        self.daily_orders.append(actual_orders)
        self.day_counter += 1
        
        return actual_orders, self.current_avg_ticket, state_multiplier
    
    def generate_arrivals_for_day(self, current_date: date) -> List[datetime]:
        """
        Generate customer arrival times for a specific day using Poisson process
        """
        opening_time = time(self.opening_hour, 0)
        closing_time = time(self.closing_hour, 0)
        
        # Adjust arrival rate based on current state
        state_multiplier = self.markov.get_order_multiplier()
        self.arrival_process.set_state_multiplier(state_multiplier)
        
        # Generate arrival times
        arrivals = self.arrival_process.generate_arrival_times(
            opening_time, closing_time, 
            max_arrivals=500  # Cap to prevent infinite loops
        )
        
        # Attach dates to arrivals
        dated_arrivals = []
        for arr in arrivals:
            # Replace date with current_date
            dated_arrival = datetime.combine(
                current_date,
                time(arr.hour, arr.minute, arr.second)
            )
            dated_arrivals.append(dated_arrival)
        
        self.total_arrivals.extend(dated_arrivals)
        return dated_arrivals

# ============ END OF POISSON PROCESS CLASSES ============

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

# ============ MODIFIED: Transaction generation with Poisson arrivals ============

def generate_single_transaction(
    order_id: int, 
    shop: CoffeeShop, 
    shop_products: List[Product],
    total_employees: int,
    ordered_at: datetime,
    avg_ticket: Optional[float] = None,
    markov_state: str = 'normal'
) -> Optional[Tuple[Orders, List[OrderItem], Payment]]:
    """Generate a single transaction at a specific time"""
    
    if not shop_products:
        return None
    
    available_products = [p for p in shop_products if p.product_is_available]
    if not available_products:
        available_products = shop_products
    
    # Determine cart size based on average ticket or state
    if avg_ticket is None:
        avg_ticket = random.gauss(120, 30)
    
    avg_item_price = 70.0
    expected_items = max(1, int(avg_ticket / avg_item_price))
    
    # Cart size influenced by Markov state
    if markov_state == 'booming':
        cart_variety_size = min(
            random.choices([1, 2, 3, 4, 5, 6], weights=[0.1, 0.2, 0.25, 0.2, 0.15, 0.1], k=1)[0],
            len(available_products)
        )
    elif markov_state == 'struggling':
        cart_variety_size = min(
            random.choices([1, 2, 3, 4], weights=[0.3, 0.35, 0.25, 0.1], k=1)[0],
            len(available_products)
        )
    else:
        cart_variety_size = min(
            random.choices([1, 2, 3, 4, 5], weights=[0.15, 0.25, 0.25, 0.2, 0.15], k=1)[0],
            len(available_products)
        )
    
    purchased_products = random.sample(available_products, k=cart_variety_size)
    order_items = []
    subtotal = 0.0
    
    for prod in purchased_products:
        # Quantity influenced by state
        if markov_state == 'booming':
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
    if markov_state == 'booming':
        order_status = random.choices(['pending', 'served', 'cancelled'], weights=[0.65, 0.30, 0.05], k=1)[0]
    elif markov_state == 'struggling':
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

def generate_transactions_with_poisson(
    order_id_counter: int,
    shop: CoffeeShop,
    shop_products: List[Product],
    shop_state: ShopStateTracker,
    total_employees: int,
    max_days: Optional[int] = None
) -> Tuple[List[Orders], List[OrderItem], List[Payment], int]:
    """
    Generate transactions using Poisson arrival process for realistic timing
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
        days_open = 30
    
    print(f"   Shop {shop.shop_id} ({shop.shop_name}): Generating {days_open} days with Poisson arrivals...")
    
    for day in range(days_open):
        current_date = shop.shop_opened_at + timedelta(days=day)
        
        if current_date > date.today():
            break
        
        # Advance shop state
        actual_orders, avg_ticket, state_multiplier = shop_state.advance_day()
        
        # Generate Poisson arrival times for this day
        arrival_times = shop_state.generate_arrivals_for_day(current_date)
        
        # Limit to expected number of orders (trim or expand)
        if len(arrival_times) > actual_orders:
            # Keep only first N arrivals (or randomly sample)
            arrival_times = random.sample(arrival_times, actual_orders)
        elif len(arrival_times) < actual_orders:
            # Generate additional orders at random times
            extra_needed = actual_orders - len(arrival_times)
            opening_hour = shop_state.opening_hour
            closing_hour = shop_state.closing_hour
            for _ in range(extra_needed):
                hour = random.randint(opening_hour, closing_hour - 1)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                extra_time = datetime.combine(current_date, time(hour, minute, second))
                arrival_times.append(extra_time)
        
        # Sort arrivals chronologically
        arrival_times.sort()
        
        # Generate transaction for each arrival
        for arrival_time in arrival_times:
            transaction = generate_single_transaction(
                order_id_counter,
                shop,
                shop_products,
                total_employees,
                arrival_time,
                avg_ticket,
                shop_state.markov.current_state
            )
            
            if transaction:
                order, items, payment = transaction
                all_orders.append(order)
                all_items.extend(items)
                all_payments.append(payment)
                order_id_counter += 1
    
    return all_orders, all_items, all_payments, order_id_counter

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

    CHUNK_SIZE = 10  # Smaller chunks due to more complex generation
    total_processed = 0
    
    print(f"\n🚀 Streaming data generation with Poisson arrival processes...")
    
    try:
        for chunk_start in range(start_shop_id, start_shop_id + num_shops, CHUNK_SIZE):
            chunk_end = min(chunk_start + CHUNK_SIZE, start_shop_id + num_shops)
            print(f"\nProcessing shops {chunk_start} to {chunk_end - 1}...")
            
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

            # Generate transactions with Poisson arrival process
            chunk_orders = []
            chunk_items = []
            chunk_payments = []
            
            for shop in shops:
                shop_products = products_by_shop[shop.shop_id]
                active_staff_count = len([e for e in employees_by_shop[shop.shop_id] if e.employee_current_status == 'active'])
                
                # Extract opening and closing hours from shop
                if shop.operating_hours:
                    opening_hour = shop.operating_hours[0][0].hour
                    closing_hour = shop.operating_hours[0][1].hour
                else:
                    opening_hour = 8
                    closing_hour = 22
                
                # Initialize shop state with Poisson process
                shop_state = ShopStateTracker(
                    shop.shop_id,
                    opening_hour=opening_hour,
                    closing_hour=closing_hour
                )
                
                # Generate transactions using Poisson arrivals
                orders, items, payments, order_id_counter = generate_transactions_with_poisson(
                    order_id_counter,
                    shop,
                    shop_products,
                    shop_state,
                    active_staff_count,
                    max_days=None
                )
                
                chunk_orders.extend(orders)
                chunk_items.extend(items)
                chunk_payments.extend(payments)
                
                # Print summary
                if len(orders) > 0:
                    print(f"   ✓ Generated {len(orders)} orders over {shop_state.day_counter} days "
                          f"(avg {len(orders)/max(1, shop_state.day_counter):.1f}/day)")

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
            print(f"   -> Progress: Completed {total_processed}/{num_shops} shops")

        print(f"\n🎉 Grand Success! All {num_shops} shops with Poisson arrival data written to database!")

    except Exception as error:
        print("\n❌ Error during execution chunk loop:", error)
        if conn: conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
