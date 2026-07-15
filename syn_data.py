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
    employee_middle_name: Optional[str] = None
    employee_gender: str
    employee_dob: date 
    employee_role: str
    employee_hire_date: date
    employee_current_status: str

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
        
        # Rule: First and middle names must be unique!
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

def generate_expected_tenure_days() -> int:
    mean_days = 16 * 30
    std_dev_days = 4 * 30
    tenure_days = int(random.gauss(mean_days, std_dev_days))
    return max(15, min(tenure_days, 5 * 365))

def determine_termination_reason(gender: str) -> str:
    """15-20% fired, 80-85% voluntary. Men fired more."""
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
    
    gender_lower = gender.lower()
    
    if gender_lower == 'male' and 20 <= current_age <= 30:
        if random.random() < 0.65:  # 65% go to military
            suspension_duration = 6 * 30
            return_age = current_age + 0.5
            
            if days_since_hired + suspension_duration > expected_tenure_days:
                return ('terminated', 'fired_during_suspension', None)
            
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
    
    if gender_lower == 'female' and 27 <= current_age <= 30:
        if random.random() < 0.18: 
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
    
    if days_since_hired > 180:
        annual_turnover_chance = 0.76
        daily_turnover_chance = 1 - (1 - annual_turnover_chance) ** (1/365)
        
        if random.random() < daily_turnover_chance:
            termination_reason = determine_termination_reason(gender)
            return ('terminated', termination_reason, None)
    
    return ('active', None, None)

def generate_employee(parent_shop: CoffeeShop, assigned_role: str) -> Employee:
    gender = random.choices(EMPLOYEE_GENDER, weights=GENDER_WEIGHTS, k=1)[0]
    first_name = generate_employee_first_name(gender)
    middle_name = generate_employee_middle_name(gender, first_name)
    surname = generate_employee_surname_name()
    
    hire_date = generate_employee_hire_date(parent_shop.shop_opened_at)
    dob = generate_employee_dob(hire_date)
    
    status, reason, details = determine_employment_status(gender, dob, hire_date)
    
    db_status = 'inactive' if status == 'terminated' else status
    
    return Employee(
        shop_id=parent_shop.shop_id,
        employee_first_name=first_name,
        employee_surname_name=surname,
        employee_middle_name=middle_name,
        employee_gender=gender.lower(), 
        employee_dob=dob,
        employee_role=assigned_role,
        employee_hire_date=hire_date,
        employee_current_status=db_status
    )

# Quick verification test
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("Generating Test Cluster...")
    
    
    for idx in range(1, 11:
        shop = generate_coffee_shop(idx)
        print("\n=============================================")
        print(f"STORE: {shop.shop_name} (Opened: {shop.shop_opened_at})")
        print(f"ADDRESS: {shop.shop_address.to_string()}")
        print("=============================================")
        
        num_staff = determine_shop_capacity()
        roles = allocate_roles_for_shop(num_staff)
        
        for role in roles:
            emp = generate_employee(shop, role)
            middle = f" {emp.employee_middle_name}" if emp.employee_middle_name else ""
            print(f"- [{emp.employee_role.upper()}] {emp.employee_first_name}{middle} {emp.employee_surname_name}")
            print(f"  Gender: {emp.employee_gender.capitalize()} | DOB: {emp.employee_dob} | Hired: {emp.employee_hire_date}")
            print(f"  Status: {emp.employee_current_status.upper()} ({emp.status_notes})")
            print("  -------------------------------------------")
