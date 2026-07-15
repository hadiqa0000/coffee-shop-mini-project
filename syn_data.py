from dataclasses import dataclass
import datetime 
from datetime import date, timedelta
import random
from faker import Faker
from typing import Optional
import math

fake = Faker('tr_TR')

#GLOBAL_SEED = 42
#random.seed(GLOBAL_SEED)

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
    shop_id : int
    shop_name: str
    shop_address: Address  
    shop_phone: str
    shop_opened_at: datetime.date

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

def generate_coffee_shop(shop_index:int) -> CoffeeShop:
    shop_name = generate_unique_shop_name()
    shop_address = generate_unique_address()
    shop_phone = generate_unique_phone()
    
    start_date = date(1950, 1, 1)
    end_date = date(2026, 1, 1)
    random_days = random.randint(0, (end_date - start_date).days)
    shop_opened_at = start_date + timedelta(days=random_days)
    
    return CoffeeShop(
        shop_id=shop_id,
        shop_name=shop_name,
        shop_address=shop_address,
        shop_phone=shop_phone,
        shop_opened_at=shop_opened_at
    )
    
    
    
@dataclass Employee
shop_id : int
    employee_first_name : str
    employee_surname_name : str
    employee_middle_name: Optional[str] = None
    employee_gender : str
    employee_dob : date 
    employee_role : str
    employee_hire_date : date
    employee_current_status : str

EMPLOYEE_GENDER = ['Female', 'Male', 'Intersex']
gender = random.choices(GENDERS, weights=[51.90, 47.2, 1.7], k=1)[0]

def generate_employee_first_name() ->str:
        
        
        if gender == 'Male'
        first_name = fake.first_name_male() 
        
        if gender == 'Female'
        first_name = fake.first_name_female()
        
        
        else:
        first_name = fake.first_name()
        
        
        return gender, first_name
def generate_employee_middle_name()->str:
       if gender == 'Male'
        middle_name = fake.first_name_male() 
        
       if gender == 'Female'
       middle_name == fake.first_name_female()
       
       else:
       middle_name == fake.first_name()
       
       return middle_name
       
     #rules to implement later
     ##in the faker,since we're using first_name builtin function, the name for the second and first name (defined funcitons) cannot be the same 
     
     #not the whole population will have middlenames, there will be a specific percentage of people who will have middle names 
     #maybe i can do random choices when generating middlenames inthe generate employee loop with a weighted percentage list
def generate_employee_surname_name() -> str:
       surname = fake.last_name():
       
       return surname

      

def generate_employee_dob(employee_hire_date : date) -> date:
    while True:
        age_in_years = random.gauss(23.0, 4.5)
        if age_in_years >= 16.0:
            break
        age_in_days = int(age_in_years * 365.25)
    dob = hire_date - timedelta(days=age_in_days)
    return dob
#helper function
def determine_shop_capacity() -> int:
   capacity = int(random.gauss(6.0, 2.0))
    return max(3, min(capacity, 12))


def allocate_roles_for_shop(total_employees: int) -> list[str]:
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


#helper function
import random
from datetime import date, timedelta
import numpy as np
from collections import Counter

def generate_expected_tenure_days() -> int:
   
    mean_days = 16 * 30
    std_dev_days = 4 * 30
    tenure_days = int(random.gauss(mean_days, std_dev_days))
    return max(15, min(tenure_days, 5 * 365))
    
    
    
    

def determine_termination_reason(gender: str) -> str:
    """15-20% fired, 80-85% voluntary. Men fired more."""
    if gender == 'male':
        fired_chance = 0.22
    else:
        fired_chance = 0.14
    
    if random.random() < fired_chance:
        return 'fired'
    else:
        return 'voluntary'



def determine_employment_status(gender: str, dob: date, hire_date: date) -> tuple:
    """
    Returns: (status, reason, details)
    status: 'active', 'suspended', 'terminated'
    """
    today = date.today()
    current_age = (today - dob).days / 365.25
    days_since_hired = (today - hire_date).days
    
    expected_tenure_days = generate_expected_tenure_days()
    
    
    if days_since_hired > expected_tenure_days:
        termination_reason = determine_termination_reason(gender)
        return ('terminated', termination_reason, None)
    
    
    if gender == 'male' and 20 <= current_age <= 30:
        if random.random() < 0.65:  # 65% go to military
            suspension_duration = 6 * 30
            
            
        return_age = current_age + 0.5
            
            if days_since_hired + suspension_duration > expected_tenure_days:
                return ('terminated', 'fired_during_suspension', None)
            return ('suspended', 'military_service', {
                'duration_days': suspension_duration,
                'expected_return': (today + timedelta(days=suspension_duration)).isoformat()
            })
            
            
            if random.random() < 0.18:
                return ('terminated', 'did_not_return_from_military', {
                    'reason': 'Did not return to job after military service',
                    'service_duration_months': 6
                })
           return ('suspended', 'military_service', {
                'duration_days': suspension_duration,
                'expected_return': (today + timedelta(days=suspension_duration)).isoformat(),
                'return_age': return_age
            })
    
    # 3. MATERNITY for females (27-30)
    if gender == 'female' and 27 <= current_age <= 30:
        if random.random() < 0.18: 
            
            # 56% leave permanently within 12 months (national statistic)
            if random.random() < 0.56:
                return ('terminated', 'maternity_exit', {
                    'reason': 'Left labor market after childbirth',
                    'statistic': '56% of mothers leave within 12 months'
                })
            else:
                suspension_duration = 4 * 30  
                
                
                if random.random() < 0.75:  
                    return ('terminated', 'terminated_after_maternity', {
                        'reason': 'Terminated after maternity leave return',
                        'suspension_duration': suspension_duration,
                        'note': 'Most women are let go shortly after maternity leave'
                    })
                else:
                   
                    if days_since_hired + suspension_duration > expected_tenure_days:
                        return ('terminated', 'fired_during_suspension', None)
                    return ('suspended', 'maternity_leave', {
                        'duration_days': suspension_duration,
                        'expected_return': (today + timedelta(days=suspension_duration)).isoformat(),
                        'will_return': True,
                        'return_probability': 'Low (25% chance of keeping job)'
                    })
    
    # 4. Annual turnover check (75-80%)
    if days_since_hired > 180:
        annual_turnover_chance = 0.76
        daily_turnover_chance = 1 - (1 - annual_turnover_chance) ** (1/365)
        
        if random.random() < daily_turnover_chance:
            termination_reason = determine_termination_reason(gender)
            return ('terminated', termination_reason, None)
    
    return ('active', None, None)
    
    
    
    
    
def determine_termination_reason(gender: str) -> str:
   
    if gender == 'male':
        fired_chance = 0.22
    else:
        fired_chance = 0.14
    
    if random.random() < fired_chance:
        return 'fired'
    else:
        return 'voluntary'




# Quick verification test
if __name__ == "__main__":
    shop = generate_coffee_shop()
    print(shop)
    print(shop.shop_address.to_string())
    
    
    
    
    
    
    
    
    
    

