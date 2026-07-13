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




def generate_address() -> Address:

	city = random.choice(list(TURKIYE_GEOGRAPHY.keys()))
	district = random.choice(TURKIYE_GEOGRAPHY[city])
	building_no = str(random.randint(1,120))
	street_no = str(random.randint(1,180))

	return Address( 
	building_no = building_no,
	street_no = street_no,
	district = district,
	city = city
) 

for _ in range(3):
    addr = generate_address()
    print(addr.to_string())




generated_address = set()

def generate_unique_address() -> Address:
    while True:
      
        city = random.choice(list(TURKIYE_GEOGRAPHY.keys()))
        district = random.choice(TURKIYE_GEOGRAPHY[city])
        building_no = str(random.randint(1, 120))
        street_no = str(random.randint(1, 180))
        
        
        address_token = (street_no, building_no, district, city)
        
       
        if address_token not in generated_address:
            
            generated_address.add(address_token)
            
            return Address(
                building_no=building_no,
                street_no=street_no,
                district=district,
                city=city
            )
        

SHOP_SUFFIXES = ["Shop", "Cafe", "Coffee", "Roasters", "Corner"]

def generate_shop_name() -> str:
   
    owner_name = fake.first_name() 
    suffix = random.choice(SHOP_SUFFIXES)
    
    
    if owner_name.endswith('s'):
        return f"{owner_name}' {suffix}"
    return f"{owner_name}'s {suffix}"

