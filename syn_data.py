from dataclasses import dataclass
import datetime 
import random
from faker import Faker
fake = Faker('tr_TR')


GLOBAL_SEED = 42
random.seed(GLOBAL_SEED)




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
        
        return f"Sk. {self.street_no}, No: {self.building_no}, {self.district}/{self.city}, {self.country}"


@dataclass 

class CoffeeShop:
    shop_name : str
    shop_address : str
    shop_phone : str
    shop_opened_at: datetime.date








generated_addresses = set()

def generate_unique_address() -> Address:
    while True:
      
        city = random.choice(list(TURKIYE_GEOGRAPHY.keys()))
        district = random.choice(TURKIYE_GEOGRAPHY[city])
        building_no = str(random.randint(1, 120))
        street_no = str(random.randint(1, 180))
        
        
        address_token = (street_no, building_no, district, city) #a combination of steet no building no district and city
        
       
        if address_token not in generated_addresses:
            
            generated_address.add(address_token)
            
            return Address(
                building_no=building_no,
                street_no=street_no,
                district=district,
                city=city
            )
        

SHOP_SUFFIXES = ["Shop", "Cafe", "Coffee", "Roasters", "Corner"]

generated_shop_name = set()

def generate_shop_name() -> str:
    while True:
    owner_name = fake.first_name() 
    suffix = random.choice(SHOP_SUFFIXES)
    
   
    
    if owner_name.endswith('s'):
        name_candidate = f"{owner_name}' {suffix}"
        else:
            name_candidate = f"{owner_name}'s {suffix}"
            
            
    if name_candidate not in generated_shop_name():
    	generated_shop_name.add(candidate_name)
    	return candidate_name
    	
    	
    	
    	
def generate_coffee_shop() -> CoffeeShop:
    
    shop_name = generate_unique_shop_name()
    shop_address = generate_unique_address()
    shop_phone = generate_unique_phone()
    
  
    start_date = date(1950, 1, 1)
    end_date = date(2026, 1, 1)
    random_days = random.randint(0, (end_date - start_date).days)
    shop_opened_at = start_date + timedelta(days=random_days)
    
    return CoffeeShop(
        shop_name=shop_name,
        shop_address=shop_address,
        shop_phone=shop_phone,
        shop_opened_at=shop_opened_at
    )
    	
    	
    
