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
    
    
@dataclass    
class Orders:
   order_id: int  # <-- FIXED: Added missing type annotation
   shop_id  : int
   ordered_at : date
   order_status : str # 'pending', 'served', 'cancelled'
   order_subtotal : float
   order_tax : float
   order_total : float


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
        "Espresso": 55.00,
        "Double Espresso": 75.00,
        "Americano": 55.00,
        "Long Black": 60.00,
        "Cappuccino": 70.00,
        "Caffe Latte": 75.00,
        "Flat White": 70.00,
        "Mocha": 85.00,
        "Caramel Macchiato": 90.00,
        "Vanilla Latte": 80.00,
        "Hazelnut Latte": 80.00,
        "Turkish Coffee (Sade)": 60.00,
        "Turkish Coffee (Az Şekerli)": 60.00,
        "Turkish Coffee (Orta Şekerli)": 60.00,
        "Turkish Coffee (Şekerli)": 60.00,
        "Turkish Coffee with Cardamom": 75.00,
        "Turkish Coffee with Mastic": 80.00,
        "Dibek Coffee": 70.00,
        "Menengiç Coffee": 75.00,
        "Filter Coffee (Colombia)": 65.00,
        "Filter Coffee (Ethiopia)": 70.00,
        "Filter Coffee (Brazil)": 65.00,
        "Cold Brew (Hot Service)": 80.00,
        "Masala Chai": 120.00,
        "Turmeric Latte": 110.00,
        "Matcha Latte": 100.00,
        "Golden Milk": 105.00,
        "London Fog": 85.00,
        "Dirty Chai": 130.00,
        "Affogato": 95.00,
        "Cortado": 65.00,
        "Macchiato": 60.00,
        "Hot Chocolate": 75.00,
        "White Hot Chocolate": 80.00,
        "Sahlep (Winter Special)": 90.00,
        "Boza (Winter Special)": 85.00,
        "Salep with Cinnamon": 95.00
    },
    "Cold Drinks": {
        "Iced Americano": 70.00,
        "Iced Latte": 85.00,
        "Iced Vanilla Latte": 95.00,
        "Iced Caramel Latte": 95.00,
        "Iced Mocha": 100.00,
        "Iced Matcha Latte": 105.00,
        "Iced Chai": 100.00,
        "Cold Brew": 90.00,
        "Nitro Cold Brew": 110.00,
        "Frappe": 110.00,
        "Caramel Frappe": 120.00,
        "Mocha Frappe": 120.00,
        "Turkish Ice Coffee": 85.00,
        "Lemonade": 70.00,
        "Strawberry Lemonade": 85.00,
        "Peach Lemonade": 85.00,
        "Iced Tea": 65.00,
        "Peach Iced Tea": 75.00,
        "Thai Iced Tea": 95.00,
        "Ayran (Cold)": 50.00,
        "Smoothie (Berry)": 130.00,
        "Smoothie (Mango)": 130.00,
        "Smoothie (Banana)": 130.00,
        "Milkshake (Chocolate)": 115.00,
        "Milkshake (Strawberry)": 115.00,
        "Milkshake (Vanilla)": 115.00,
        "Orange Juice (Fresh)": 80.00,
        "Pomegranate Juice (Fresh)": 85.00,
        "Carrot Juice (Fresh)": 75.00,
        "Watermelon Juice (Seasonal)": 70.00,
        "Kefir": 90.00,
        "Şalgam (Cold)": 60.00
    },
    "Turkish Breakfast & Brunch": {
        "Serpme Kahvaltı (For 2)": 450.00,
        "Serpme Kahvaltı (For 1)": 250.00,
        "Menemen (Classic)": 160.00,
        "Menemen with Sucuk": 190.00,
        "Menemen with Kaşar": 180.00,
        "Sucuklu Yumurta": 170.00,
        "Pastırmalı Yumurta": 190.00,
        "Avocado Toast (Turkish Twist)": 150.00,
        "Simit (Plain)": 40.00,
        "Simit with Cream Cheese": 70.00,
        "Simit with Sucuk & Egg": 110.00,
        "Açma (Plain)": 35.00,
        "Açma with Cheese": 60.00,
        "Poğaça (Cheese)": 45.00,
        "Poğaça (Potato)": 45.00,
        "Poğaça (Minced Meat)": 55.00,
        "Börek (Spinach & Feta)": 90.00,
        "Börek (Potato)": 85.00,
        "Börek (Minced Meat)": 95.00,
        "Su Böreği": 100.00,
        "Kol Böreği": 90.00,
        "Sigara Böreği (3 pcs)": 75.00,
        "Fried Eggs (Sade)": 120.00,
        "Eggs Benedict (Turkish style)": 190.00,
        "Kaşarlı Tost": 85.00,
        "Sucuklu Tost": 95.00,
        "Tahin & Pekmez (with Bread)": 60.00,
        "Kaymak & Honey (with Bread)": 90.00,
        "Olive Plate": 70.00,
        "Cheese Plate (Mixed)": 110.00,
        "Balık Kahvaltı (Breakfast Fish)": 220.00
    },
    "Bakery & Pastry": {
        "Croissant (Plain)": 65.00,
        "Chocolate Croissant": 80.00,
        "Almond Croissant": 90.00,
        "Pistachio Croissant": 95.00,
        "Pain au Chocolat": 80.00,
        "Cinnamon Roll": 85.00,
        "Danish Pastry (Fruit)": 70.00,
        "San Sebastian Cheesecake": 150.00,
        "New York Cheesecake": 140.00,
        "Berry Cheesecake": 155.00,
        "Lemon Cheesecake": 145.00,
        "Chocolate Cookie": 55.00,
        "White Chocolate Cookie": 65.00,
        "Double Chocolate Cookie": 65.00,
        "Oatmeal Cookie": 60.00,
        "Brownie (Classic)": 70.00,
        "Brownie with Ice Cream": 110.00,
        "Blondie": 70.00,
        "Muffin (Blueberry)": 65.00,
        "Muffin (Chocolate)": 65.00,
        "Muffin (Banana Walnut)": 70.00,
        "Banana Bread": 80.00,
        "Carrot Cake": 120.00,
        "Red Velvet Cake": 130.00,
        "Chocolate Cake": 125.00,
        "Lemon Drizzle Cake": 115.00,
        "Tahini Cookie": 50.00,
        "Kurabiye (Turkish Shortbread)": 45.00,
        "Un Kurabiyesi": 40.00,
        "Revani (Semolina Cake)": 90.00,
        "Şekerpare": 80.00,
        "Kemalpaşa Tatlısı": 85.00,
        "Sütlaç (Rice Pudding)": 70.00,
        "Fırın Sütlaç": 75.00,
        "Kazandibi": 85.00,
        "Trileçe": 100.00,
        "Profiterol": 110.00,
        "Künefe (Small)": 130.00,
        "Künefe (Large)": 180.00
    },
    "Sandwiches & Savory": {
        "Grilled Cheese (Kaşar)": 90.00,
        "Grilled Cheese with Sucuk": 120.00,
        "Tuna Melt": 110.00,
        "Chicken Wrap": 130.00,
        "Veggie Wrap": 110.00,
        "Falafel Wrap": 120.00,
        "Panini (Chicken)": 140.00,
        "Panini (Veggie)": 120.00,
        "Panini (Turkey)": 150.00,
        "Club Sandwich (Chicken)": 150.00,
        "Club Sandwich (Turkey)": 160.00,
        "BLT Sandwich": 130.00,
        "Bagel with Cream Cheese": 80.00,
        "Bagel with Smoked Salmon": 170.00,
        "Bagel with Avocado": 130.00,
        "Toast (Kaşarlı)": 75.00,
        "Toast (Sucuklu)": 95.00,
        "Toast (Pastırmalı)": 110.00,
        "Ham & Cheese Toast": 85.00,
        "Vegetarian Toast": 80.00,
        "Quiche (Spinach & Feta)": 110.00,
        "Quiche (Mushroom)": 110.00,
        "Focaccia (Plain)": 80.00,
        "Focaccia (Olive & Herb)": 90.00,
        "Focaccia (Cheese)": 95.00,
        "Pizza Slice (Margherita)": 100.00,
        "Pizza Slice (Pepperoni)": 110.00,
        "Pizza Slice (Vegetable)": 105.00,
        "Lahmacun (Turkish Pizza)": 120.00,
        "Pide (Kaşarlı)": 140.00,
        "Pide (Sucuklu)": 160.00,
        "Pide (Pastırmalı)": 170.00,
        "Pide (Spinach & Egg)": 150.00,
        "Pide (Minced Meat)": 165.00
    },
    "Salads & Bowls": {
        "Çoban Salata (Turkish Shepherd)": 100.00,
        "Greek Salad": 130.00,
        "Caesar Salad (Chicken)": 160.00,
        "Caesar Salad (Veggie)": 140.00,
        "Mediterranean Salad": 150.00,
        "Quinoa Bowl (Veggie)": 160.00,
        "Quinoa Bowl (Chicken)": 180.00,
        "Buddha Bowl": 170.00,
        "Poke Bowl (Salmon)": 210.00,
        "Poke Bowl (Chicken)": 190.00,
        "Falafel Bowl": 160.00,
        "Avocado Bowl": 170.00,
        "Mercimek Çorbası (Lentil Soup)": 70.00,
        "Ezogelin Çorbası": 75.00,
        "Tarhana Çorbası": 80.00,
        "Yayla Çorbası": 75.00
    },
    "Tea & Herbal Drinks": {
        "Turkish Tea (Demlik)": 30.00,
        "Turkish Tea (Double)": 40.00,
        "Apple Tea (Elma Çayı)": 35.00,
        "Linden Tea (Ihlamur)": 40.00,
        "Sage Tea (Adaçayı)": 40.00,
        "Rosehip Tea (Kuşburnu)": 45.00,
        "Black Tea (English Breakfast)": 45.00,
        "Earl Grey": 50.00,
        "Darjeeling": 55.00,
        "Green Tea": 50.00,
        "Matcha Tea": 70.00,
        "Peppermint Tea": 45.00,
        "Chamomile Tea": 45.00,
        "Lemon & Ginger Tea": 50.00,
        "Rooibos Tea": 48.00,
        "Oolong Tea": 60.00,
        "Jasmine Tea": 55.00,
        "Berry Blast Tea": 55.00,
        "Mango & Passionfruit Tea": 55.00,
        "Tea Pot for 2": 60.00
    },
    "Add-ons & Extras": {
        "Extra Espresso Shot": 35.00,
        "Whipped Cream": 20.00,
        "Soy Milk": 35.00,
        "Oat Milk": 40.00,
        "Almond Milk": 40.00,
        "Coconut Milk": 40.00,
        "Vanilla Syrup": 25.00,
        "Caramel Syrup": 25.00,
        "Hazelnut Syrup": 25.00,
        "Coconut Syrup": 25.00,
        "Chocolate Sauce": 20.00,
        "Caramel Drizzle": 20.00,
        "Cinnamon Dust": 15.00,
        "Nutmeg": 15.00,
        "Honey (Organic)": 20.00,
        "Agave Syrup": 20.00,
        "Pekmez (Grape Molasses)": 20.00,
        "Tahini": 20.00,
        "Butter (Small)": 15.00,
        "Jam (Mixed Berry)": 15.00,
        "Jam (Apricot)": 15.00,
        "Nutella": 25.00,
        "Peanut Butter": 25.00,
        "Extra Cheese": 20.00,
        "Extra Sucuk": 30.00,
        "Extra Pastırma": 35.00,
        "Extra Egg": 20.00
    },
    "Bottled & Packaged Drinks": {
        "Bottled Water (Small)": 20.00,
        "Bottled Water (Large)": 30.00,
        "Sparkling Water (Soda)": 30.00,
        "Sparkling Water (Fruit)": 35.00,
        "Coca-Cola": 55.00,
        "Diet Coke": 55.00,
        "Sprite": 55.00,
        "Fanta": 55.00,
        "Ice Tea (Lemon)": 60.00,
        "Ice Tea (Peach)": 60.00,
        "Energy Drink": 80.00,
        "Kombucha": 100.00,
        "Cold Pressed Juice (Green)": 110.00,
        "Cold Pressed Juice (Beetroot)": 110.00,
        "Cold Pressed Juice (Orange)": 100.00,
        "Coconut Water": 85.00,
        "Ayran (Bottle)": 45.00,
        "Şalgam (Bottle)": 50.00,
        "Smoothie Bottle (Ready)": 90.00,
        "Protein Shake": 120.00
    },
    "Desserts (Special)": {
        "Baklava (1 pc)": 60.00,
        "Baklava (4 pcs)": 200.00,
        "Fıstıklı Baklava": 70.00,
        "Cevizli Baklava": 65.00,
        "Sütlü Nuriye": 75.00,
        "Kadayıf (Fıstıklı)": 80.00,
        "Kadayıf (Cevizli)": 75.00,
        "Ekmek Kadayıfı": 85.00,
        "Güllaç (Seasonal)": 90.00,
        "Tavuk Göğsü": 80.00,
        "Kazandibi": 85.00,
        "Sütlaç": 70.00,
        "Fırın Sütlaç": 75.00,
        "Muhallebi": 65.00,
        "Keşkül": 70.00,
        "Aşure (Seasonal)": 80.00,
        "Helva (Tahini)": 70.00,
        "Helva (Chocolate)": 80.00,
        "Dondurma (1 scoop)": 40.00,
        "Dondurma (2 scoops)": 70.00,
        "Maraş Dondurması": 50.00,
        "Dondurma with Baklava": 120.00,
        "Panna Cotta": 110.00,
        "Crème Brûlée": 130.00,
        "Tiramisu": 120.00,
        "Lemon Tart": 100.00,
        "Fruit Tart": 110.00,
        "Chocolate Mousse": 95.00,
        "Macaron (1 pc)": 45.00,
        "Macaron (Box of 6)": 240.00,
        "Cupcake (Vanilla)": 65.00,
        "Cupcake (Chocolate)": 70.00,
        "Cupcake (Red Velvet)": 75.00,
        "Donut (Glazed)": 55.00,
        "Donut (Chocolate)": 65.00,
        "Donut (Strawberry)": 65.00
    },
    "Specialty Coffee (Third Wave)": {
        "V60 (Single Origin)": 90.00,
        "Chemex (For 2)": 160.00,
        "AeroPress": 85.00,
        "Siphon Coffee": 110.00,
        "Cold Drip": 120.00,
        "Nitro Cold Brew (Special)": 130.00,
        "Geisha Coffee (Reserve)": 190.00,
        "Ethiopian Yirgacheffe": 100.00,
        "Colombian Geisha": 140.00,
        "Costa Rican Honey Process": 110.00,
        "Kenyan AA": 105.00,
        "Sumatra Mandheling": 100.00
    }
}

LOCATION_PREMIUMS = {
    "Kadiroy": 1.25, "Besiktas": 1.25, "Sisli": 1.25, "Cankaya": 1.25,
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


def generate_single_order(
    order_id: int, 
    shop: CoffeeShop, 
    shop_products: List[Product]
) -> Optional[Orders]:
    """
    Generates a single realistic order for a given shop using its actual products.
    """
    if not shop_products:
        return None  # Can't buy anything if the shop has no products!
        
    # 1. Generate a realistic order date (must be between shop opening date and today)
    today = date.today()
    days_open = (today - shop.shop_opened_at).days
    
    if days_open <= 0:
        ordered_at = shop.shop_opened_at
    else:
        random_days = random.randint(0, days_open)
        ordered_at = shop.shop_opened_at + timedelta(days=random_days)
        
    # 2. Simulate a customer cart (buying between 1 and 5 items)
    # We only pull from products that are marked as available (is_available == True)
    available_products = [p for p in shop_products if p.product_is_available]
    if not available_products:
        available_products = shop_products  # Fallback if somehow nothing is available
        
    cart_size = random.choices([1, 2, 3, 4, 5], weights=[0.40, 0.35, 0.15, 0.07, 0.03], k=1)[0]
    purchased_items = random.choices(available_products, k=cart_size)
    
    # 3. Calculate subtotal from chosen products
    subtotal = 0.0
    for item in purchased_items:
        price_float = float(item.product_current_price.replace(" TL", ""))
        subtotal += price_float
        
    # 4. Calculate Tax (Using standard Turkish cafe VAT of 10%)
    tax_rate = 0.10 
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)
    
    # 5. Order Status
    status = random.choices(
        ['completed', 'cancelled', 'refunded'], 
        weights=[0.95, 0.03, 0.02], 
        k=1
    )[0]
    
    return Orders(
        order_id=order_id,
        shop_id=shop.shop_id,
        ordered_at=ordered_at,
        order_status=status,
        order_subtotal=round(subtotal, 2),
        order_tax=tax,
        order_total=total
    )


# Quick verification test
if __name__ == "__main__":
    
    shop = generate_coffee_shop(1)
    print(f"Shop Name: {shop.shop_name}")
    print(f"Address:   {shop.shop_address.to_string()}")
    print(f"Opened:    {shop.shop_opened_at}")
    print("\n" + "="*50)
    print("HIRING STAFF (Ensuring active minimums are met)...")
    print("="*50)
    
    
    all_employees = generate_shop_staff(shop)
    
   
    # 3. Print out the results to verify
    active_employees = [e for e in all_employees if e.employee_current_status == 'active']
    suspended_employees = [e for e in all_employees if e.employee_current_status == 'suspended']
    terminated_employees = [e for e in all_employees if e.employee_current_status == 'terminated']
    
    print(f"\nTotal Hired Historically: {len(all_employees)}")
    print(f"Total Currently Active:   {len(active_employees)}")
    print(f"Total Suspended:          {len(suspended_employees)}")
    print(f"Total Terminated:         {len(terminated_employees)}")
    
    # --- NEW: Print details of each employee ---
    print("\n" + "="*20 + " ALL EMPLOYEE ROSTER " + "="*20)
    for idx, employee in enumerate(all_employees, 1):
        # Format middle name nicely if it doesn't exist
        mid_name = employee.employee_middle_name if employee.employee_middle_name else ""
        full_name = f"{employee.employee_first_name} {mid_name} {employee.employee_surname_name}".replace("  ", " ")
        
        status_tag = employee.employee_current_status.upper()
        if employee.employee_current_status == 'suspended':
            status_tag = f"SUSPENDED ({employee.reason_for_suspension})"
            
        print(f"\nEmployee #{idx}: {full_name}")
        print(f"  Role:       {employee.employee_role.capitalize()}")
        print(f"  Gender:     {employee.employee_gender.capitalize()}")
        print(f"  DOB:        {employee.employee_dob} (Hired: {employee.employee_hire_date})")
        print(f"  Status:     {status_tag}")
    print("="*61)
    
    
    active_by_role = {'manager': 0, 'barista': 0, 'cashier': 0, 'waiter': 0}
    for e in active_employees:
        active_by_role[e.employee_role] += 1
        
    print("\nActive Staff Breakdown:")
    for role, count in active_by_role.items():
        print(f"  - {role.capitalize()}s: {count}")
      
    
    products = generate_shop_products(shop, total_employees=len(active_employees))
    
    print("\n" + "="*20 + " GENERATED PRODUCTS " + "="*20)
    for prod in products[:5]: 
        status_str = "In Stock" if prod.product_is_available else "Out of Stock"
        print(f"- [{prod.product_category}] {prod.product_name}: {prod.product_current_price} ({status_str})")
         
    print(f"\nGenerating orders for: {shop.shop_name} (Opened: {shop.shop_opened_at})")
    print("="*60)
    
    
    orders_list = []
    for order_seq in range(1001, 1011): # Generates IDs 1001 to 1010
        order = generate_single_order(order_seq, shop, products)
        if order:
            orders_list.append(order)
            
    
    for o in orders_list:
        print(f"Order #{o.order_id} | Date: {o.ordered_at} | Status: {o.order_status:<10} | Subtotal: {o.order_subtotal:>6.2f} TL | Tax: {o.order_tax:>5.2f} TL | Total: {o.order_total:>6.2f} TL")
