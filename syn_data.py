from __future__ import annotations
from dataclasses import dataclass, field
import datetime 
from datetime import date, timedelta, time, datetime
import random
from faker import Faker
from typing import Optional, List, Dict, Tuple, Any
import psycopg2
from psycopg2.extras import execute_values
import json
import re
import numpy as np
import math
from enum import Enum

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

# ============ STOCHASTIC SHOCK SYSTEM ============

class ShockType(Enum):
    """Types of stochastic shocks that can occur"""
    COMPETITOR_OPENING = "competitor_opening"
    VIRAL_TREND = "viral_trend"
    SUPPLY_CHAIN = "supply_chain"
    ECONOMIC_CRISIS = "economic_crisis"
    LOCAL_EVENT = "local_event"
    SEASONAL_SHIFT = "seasonal_shift"
    MENU_CHANGE = "menu_change"
    HEALTH_CRISIS = "health_crisis"
    SOCIAL_MEDIA = "social_media"
    WEATHER_EVENT = "weather_event"

@dataclass
class StochasticShock:
    """Represents a single stochastic shock event"""
    shock_id: int
    shop_id: int
    shock_type: ShockType
    occurrence_date: date
    magnitude: float  # Effect size (e.g., 0.30 = 30% change)
    duration_days: int  # How long the shock lasts
    decay_rate: float  # How quickly it fades (0 = no decay, 1 = immediate)
    is_permanent: bool
    affected_metric: str  # 'orders', 'prices', 'both', 'product_specific'
    affected_products: List[str] = field(default_factory=list)
    description: str = ""
    
    # For temporary shocks
    current_effect: float = 1.0  # Current multiplier (starts at 1 + magnitude)
    days_remaining: int = 0
    
    def apply_effect(self, days_since_occurrence: int) -> float:
        """Calculate the current effect multiplier for this shock"""
        if self.is_permanent:
            # Permanent shock: full effect forever
            return 1.0 + self.magnitude
        else:
            # Temporary shock with decay
            if days_since_occurrence >= self.duration_days:
                return 1.0  # Shock has ended
            
            # Exponential decay or linear decay
            progress = days_since_occurrence / self.duration_days
            if self.decay_rate < 0.5:
                # Slow decay: exponential
                decay_factor = math.exp(-self.decay_rate * days_since_occurrence)
            else:
                # Fast decay: linear
                decay_factor = 1 - progress
            
            effect = 1.0 + self.magnitude * decay_factor
            return max(0.5, min(2.5, effect))  # Cap extreme effects

class ShockGenerator:
    """Generates and manages stochastic shocks"""
    
    # Shock type definitions
    SHOCK_DEFINITIONS = {
        ShockType.COMPETITOR_OPENING: {
            'probability': 0.02,  # 2% per month
            'magnitude_range': (-0.30, -0.05),  # -5% to -30% traffic
            'duration_range': (180, 730),  # 6-24 months (often permanent)
            'is_permanent_probability': 0.85,
            'decay_rate_range': (0.001, 0.01),
            'affected_metrics': ['orders', 'revenue'],
            'description_template': "Competitor opened nearby, stealing {magnitude:.0%} of customers"
        },
        ShockType.VIRAL_TREND: {
            'probability': 0.015,  # 1.5% per month
            'magnitude_range': (0.15, 1.0),  # 15% to 100% increase
            'duration_range': (7, 30),  # 1-4 weeks
            'is_permanent_probability': 0.05,
            'decay_rate_range': (0.05, 0.15),
            'affected_metrics': ['orders', 'revenue', 'product_specific'],
            'description_template': "Product went viral on TikTok - {product} sales exploded"
        },
        ShockType.SUPPLY_CHAIN: {
            'probability': 0.025,  # 2.5% per month
            'magnitude_range': (-0.20, -0.02),  # -2% to -20% availability
            'duration_range': (14, 90),  # 2 weeks to 3 months
            'is_permanent_probability': 0.1,
            'decay_rate_range': (0.02, 0.08),
            'affected_metrics': ['prices', 'availability'],
            'description_template': "Supply chain disruption - {product} prices up {magnitude:.0%}"
        },
        ShockType.ECONOMIC_CRISIS: {
            'probability': 0.01,  # 1% per month
            'magnitude_range': (-0.40, -0.10),  # -10% to -40% traffic
            'duration_range': (60, 365),  # 2-12 months
            'is_permanent_probability': 0.2,
            'decay_rate_range': (0.005, 0.02),
            'affected_metrics': ['orders', 'revenue', 'prices'],
            'description_template': "Economic downturn - spending decreased by {magnitude:.0%}"
        },
        ShockType.LOCAL_EVENT: {
            'probability': 0.04,  # 4% per month
            'magnitude_range': (-0.30, 0.30),  # -30% to +30% traffic
            'duration_range': (1, 7),  # 1-7 days
            'is_permanent_probability': 0.0,
            'decay_rate_range': (0.1, 0.5),
            'affected_metrics': ['orders'],
            'description_template': "Local event affected traffic by {magnitude:.0%}"
        },
        ShockType.SEASONAL_SHIFT: {
            'probability': 0.03,  # 3% per month
            'magnitude_range': (-0.15, 0.15),  # -15% to +15% traffic
            'duration_range': (30, 90),  # 1-3 months
            'is_permanent_probability': 0.0,
            'decay_rate_range': (0.02, 0.05),
            'affected_metrics': ['orders'],
            'description_template': "Seasonal shift in customer behavior"
        },
        ShockType.MENU_CHANGE: {
            'probability': 0.02,  # 2% per month
            'magnitude_range': (-0.10, 0.20),  # -10% to +20% revenue
            'duration_range': (30, 180),  # 1-6 months
            'is_permanent_probability': 0.6,
            'decay_rate_range': (0.01, 0.03),
            'affected_metrics': ['revenue', 'product_specific'],
            'description_template': "New menu items - {product} performance changed"
        },
        ShockType.HEALTH_CRISIS: {
            'probability': 0.005,  # 0.5% per month (rare but impactful)
            'magnitude_range': (-0.50, -0.15),  # -15% to -50% traffic
            'duration_range': (30, 180),  # 1-6 months
            'is_permanent_probability': 0.05,
            'decay_rate_range': (0.01, 0.05),
            'affected_metrics': ['orders', 'revenue'],
            'description_template': "Health concern reduced foot traffic by {magnitude:.0%}"
        },
        ShockType.SOCIAL_MEDIA: {
            'probability': 0.03,  # 3% per month
            'magnitude_range': (-0.20, 0.50),  # -20% to +50% traffic
            'duration_range': (7, 21),  # 1-3 weeks
            'is_permanent_probability': 0.1,
            'decay_rate_range': (0.05, 0.15),
            'affected_metrics': ['orders', 'revenue'],
            'description_template': "Social media mention - {magnitude:.0%} change in traffic"
        },
        ShockType.WEATHER_EVENT: {
            'probability': 0.05,  # 5% per month
            'magnitude_range': (-0.40, 0.10),  # -40% to +10% traffic
            'duration_range': (1, 3),  # 1-3 days
            'is_permanent_probability': 0.0,
            'decay_rate_range': (0.2, 1.0),
            'affected_metrics': ['orders'],
            'description_template': "Weather event - {magnitude:.0%} change in daily traffic"
        }
    }
    
    def __init__(self, shop_id: int, seed: Optional[int] = None):
        self.shop_id = shop_id
        self.shock_counter = 0
        self.active_shocks: List[StochasticShock] = []
        self.shock_history: List[StochasticShock] = []
        
        if seed is not None:
            random.seed(seed)
    
    def check_for_shocks(self, current_date: date, shop_state: Any) -> List[StochasticShock]:
        """
        Check if any new shocks should occur on this date
        Returns list of new shocks
        """
        new_shocks = []
        
        # Only check for new shocks at the start of each month
        if current_date.day != 1:
            return new_shocks
        
        # Check each shock type for probability
        for shock_type, definition in self.SHOCK_DEFINITIONS.items():
            # Base probability per month
            prob = definition['probability']
            
            # Adjust probability based on shop state
            # e.g., booming shops more likely to attract competitors
            if shock_type == ShockType.COMPETITOR_OPENING:
                if shop_state.markov.current_state == 'booming':
                    prob *= 1.5
                elif shop_state.markov.current_state == 'struggling':
                    prob *= 0.5
            
            # Check if shock occurs
            if random.random() < prob:
                shock = self._create_shock(shock_type, current_date, shop_state)
                if shock:
                    new_shocks.append(shock)
                    self.active_shocks.append(shock)
                    self.shock_history.append(shock)
                    self.shock_counter += 1
        
        return new_shocks
    
    def _create_shock(self, shock_type: ShockType, occurrence_date: date, shop_state: Any) -> Optional[StochasticShock]:
        """Create a new shock event"""
        definition = self.SHOCK_DEFINITIONS[shock_type]
        
        # Generate magnitude (can be positive or negative)
        mag_min, mag_max = definition['magnitude_range']
        magnitude = random.uniform(mag_min, mag_max)
        
        # Round to nearest 5% for cleaner data
        magnitude = round(magnitude / 0.05) * 0.05
        
        # Generate duration
        dur_min, dur_max = definition['duration_range']
        duration = random.randint(dur_min, dur_max)
        
        # Determine if permanent
        is_permanent = random.random() < definition['is_permanent_probability']
        
        # Generate decay rate
        decay_min, decay_max = definition['decay_rate_range']
        decay_rate = random.uniform(decay_min, decay_max)
        
        # Determine affected products (for product-specific shocks)
        affected_products = []
        if 'product_specific' in definition['affected_metrics']:
            # Select random products from shop's menu
            if hasattr(shop_state, 'available_products') and shop_state.available_products:
                num_products = random.randint(1, min(3, len(shop_state.available_products)))
                affected_products = random.sample(shop_state.available_products, num_products)
        
        # Create description
        description = definition['description_template']
        if '{product}' in description:
            product_name = random.choice(affected_products) if affected_products else "coffee"
            description = description.replace('{product}', product_name)
        description = description.replace('{magnitude}', f"{abs(magnitude):.0%}")
        
        # Determine affected metric
        affected_metric = random.choice(definition['affected_metrics'])
        
        return StochasticShock(
            shock_id=self.shock_counter + 1,
            shop_id=self.shop_id,
            shock_type=shock_type,
            occurrence_date=occurrence_date,
            magnitude=magnitude,
            duration_days=duration,
            decay_rate=decay_rate,
            is_permanent=is_permanent,
            affected_metric=affected_metric,
            affected_products=affected_products,
            description=description,
            days_remaining=duration
        )
    
    def update_shocks(self, current_date: date) -> Dict[str, float]:
        """
        Update active shocks and return current effect multipliers
        Returns dict with metrics and their multipliers
        """
        # Remove expired shocks
        self.active_shocks = [s for s in self.active_shocks 
                             if not s.is_permanent and 
                             (current_date - s.occurrence_date).days < s.duration_days]
        
        # Calculate effects
        effects = {
            'orders': 1.0,
            'revenue': 1.0,
            'prices': 1.0,
            'availability': 1.0
        }
        
        for shock in self.active_shocks:
            days_since = (current_date - shock.occurrence_date).days
            effect = shock.apply_effect(days_since)
            
            # Apply to affected metrics
            if shock.affected_metric == 'orders' or shock.affected_metric == 'both':
                effects['orders'] *= effect
                effects['revenue'] *= effect
            elif shock.affected_metric == 'prices':
                effects['prices'] *= effect
            elif shock.affected_metric == 'revenue':
                effects['revenue'] *= effect
            elif shock.affected_metric == 'availability':
                effects['availability'] *= effect
            elif shock.affected_metric == 'product_specific':
                # Product-specific effects handled separately
                pass
        
        # Cap extreme effects
        for key in effects:
            effects[key] = max(0.3, min(2.5, effects[key]))
        
        return effects
    
    def get_shock_description(self) -> str:
        """Get description of current active shocks"""
        if not self.active_shocks:
            return "No active shocks"
        
        descriptions = []
        for shock in self.active_shocks[:3]:  # Show top 3
            days_remaining = shock.duration_days - (datetime.now().date() - shock.occurrence_date).days
            desc = f"{shock.shock_type.value}: {shock.description} ({days_remaining} days remaining)"
            descriptions.append(desc)
        
        return "; ".join(descriptions)

# ============ MODIFIED SHOP STATE TRACKER WITH SHOCKS ============

class ShopStateTracker:
    """Tracks all time-series state for a shop including stochastic shocks"""
    
    def __init__(self, shop_id: int, opening_hour: int = 8, closing_hour: int = 22):
        self.shop_id = shop_id
        self.opening_hour = opening_hour
        self.closing_hour = closing_hour
        
        # Base arrival rate (customers per minute)
        self.base_arrival_rate = random.uniform(0.3, 0.8)
        
        # Initialize intensity profile
        self.intensity_profile = TimeOfDayIntensity(opening_hour, closing_hour)
        
        # Initialize Poisson arrival process
        self.arrival_process = PoissonArrivalProcess(
            base_rate=self.base_arrival_rate,
            intensity_profile=self.intensity_profile
        )
        
        # Initialize random walk for daily total orders
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
        
        # Initialize shock generator
        self.shock_generator = ShockGenerator(shop_id)
        self.shock_effects = {'orders': 1.0, 'revenue': 1.0, 'prices': 1.0, 'availability': 1.0}
        
        # Historical tracking
        self.daily_orders = []
        self.daily_revenue = []
        self.day_counter = 0
        self.total_arrivals = []
        self.shock_log = []
    
    def advance_day(self, current_date: date) -> Tuple[int, float, float, Dict]:
        """Advance one day and return (actual_orders, avg_ticket, state_multiplier, shock_effects)"""
        
        # Check for new stochastic shocks (monthly check)
        new_shocks = self.shock_generator.check_for_shocks(current_date, self)
        if new_shocks:
            for shock in new_shocks:
                self.shock_log.append({
                    'date': current_date,
                    'shock_type': shock.shock_type.value,
                    'magnitude': shock.magnitude,
                    'description': shock.description
                })
                print(f"   ⚡ SHOCK at Shop {self.shop_id}: {shock.description}")
        
        # Update active shocks
        self.shock_effects = self.shock_generator.update_shocks(current_date)
        
        # Update Markov state
        if self.day_counter % random.randint(5, 10) == 0:
            self.markov.step()
        
        # Update random walks
        expected_daily_orders = self.order_walk.step()
        self.current_avg_ticket = self.ticket_walk.step()
        
        # Apply Markov state multiplier
        state_multiplier = self.markov.get_order_multiplier()
        self.arrival_process.set_state_multiplier(state_multiplier)
        
        # Apply shock effects
        order_shock_multiplier = self.shock_effects.get('orders', 1.0)
        expected_daily_orders *= order_shock_multiplier
        
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
        
        return actual_orders, self.current_avg_ticket, state_multiplier, self.shock_effects
    
    def generate_arrivals_for_day(self, current_date: date) -> List[datetime]:
        """Generate customer arrival times for a specific day using Poisson process"""
        opening_time = time(self.opening_hour, 0)
        closing_time = time(self.closing_hour, 0)
        
        # Adjust arrival rate based on current state and shocks
        state_multiplier = self.markov.get_order_multiplier()
        shock_multiplier = self.shock_effects.get('orders', 1.0)
        self.arrival_process.set_state_multiplier(state_multiplier * shock_multiplier)
        
        # Generate arrival times
        arrivals = self.arrival_process.generate_arrival_times(
            opening_time, closing_time, 
            max_arrivals=500
        )
        
        # Attach dates to arrivals
        dated_arrivals = []
        for arr in arrivals:
            dated_arrival = datetime.combine(
                current_date,
                time(arr.hour, arr.minute, arr.second)
            )
            dated_arrivals.append(dated_arrival)
        
        self.total_arrivals.extend(dated_arrivals)
        return dated_arrivals

# ============ MODIFIED TIME OF DAY INTENSITY CLASS ============

class TimeOfDayIntensity:
    """Models customer arrival intensity throughout the day"""
    
    def __init__(self, opening_hour: int = 8, closing_hour: int = 22):
        self.opening_hour = opening_hour
        self.closing_hour = closing_hour
        
        self.hourly_intensity = {
            8: 0.6, 9: 1.8, 10: 1.5,
            11: 1.0, 12: 0.9,
            13: 1.4, 14: 1.6,
            15: 1.1, 16: 1.0, 17: 0.9,
            18: 1.3, 19: 1.5, 20: 1.2,
            21: 0.7, 22: 0.4
        }
        
        self.intensity_cache = {}
        self._build_intensity_cache()
    
    def _build_intensity_cache(self):
        for minute in range(0, 24 * 60):
            hour = minute // 60
            minute_of_hour = minute % 60
            
            h1 = hour
            h2 = (hour + 1) % 24
            
            i1 = self.hourly_intensity.get(h1, 0.5)
            i2 = self.hourly_intensity.get(h2, 0.5)
            
            fraction = minute_of_hour / 60.0
            intensity = i1 * (1 - fraction) + i2 * fraction
            
            if hour < self.opening_hour or hour > self.closing_hour:
                intensity = 0.0
            elif hour == self.opening_hour and minute_of_hour < 30:
                intensity = intensity * (minute_of_hour / 30.0)
            elif hour == self.closing_hour and minute_of_hour > 30:
                intensity = intensity * (1 - (minute_of_hour - 30) / 30.0)
                if minute_of_hour > 45:
                    intensity = 0.0
            
            self.intensity_cache[minute] = max(0, intensity)
    
    def get_intensity(self, minute_of_day: int) -> float:
        return self.intensity_cache.get(minute_of_day, 0.0)
    
    def get_average_intensity(self, base_rate: float = 1.0) -> float:
        total = sum(self.intensity_cache.values())
        return (total / (24 * 60)) * base_rate

# ============ MODIFIED POISSON ARRIVAL PROCESS ============

class PoissonArrivalProcess:
    """Non-homogeneous Poisson process for customer arrivals"""
    
    def __init__(self, base_rate: float, intensity_profile: TimeOfDayIntensity):
        self.base_rate = base_rate
        self.intensity_profile = intensity_profile
        self.state_multiplier = 1.0
        self.arrival_history = []
        
    def set_state_multiplier(self, multiplier: float):
        self.state_multiplier = multiplier
    
    def get_rate_at(self, minute_of_day: int) -> float:
        base_intensity = self.intensity_profile.get_intensity(minute_of_day)
        return self.base_rate * base_intensity * self.state_multiplier
    
    def generate_arrival_times(self, start_time: time, end_time: time, 
                               max_arrivals: int = 1000) -> List[datetime]:
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        
        arrivals = []
        current_time = start_minutes
        
        max_rate = max([self.get_rate_at(m) for m in range(start_minutes, end_minutes)]) * 1.2
        
        while len(arrivals) < max_arrivals:
            if max_rate > 0:
                u = random.random()
                inter_arrival = -math.log(u) / max_rate if u > 0 else 0
            else:
                break
            
            current_time += inter_arrival * 60
            current_time = min(current_time, end_minutes)
            
            if current_time >= end_minutes:
                break
                
            current_minute = int(current_time)
            current_rate = self.get_rate_at(current_minute)
            
            accept_prob = current_rate / max_rate if max_rate > 0 else 0
            
            if random.random() < accept_prob:
                hours = current_minute // 60
                mins = current_minute % 60
                seconds = random.randint(0, 59)
                arrival_dt = datetime.combine(
                    date.today(), 
                    time(hours, mins, seconds)
                )
                arrivals.append(arrival_dt)
        
        return arrivals

# ============ MODIFIED GENERATE TRANSACTIONS FUNCTION ============

def generate_transactions_with_shocks(
    order_id_counter: int,
    shop: CoffeeShop,
    shop_products: List[Product],
    shop_state: ShopStateTracker,
    total_employees: int,
    max_days: Optional[int] = None
) -> Tuple[List[Orders], List[OrderItem], List[Payment], int, List[Dict]]:
    """
    Generate transactions with stochastic shocks
    """
    all_orders = []
    all_items = []
    all_payments = []
    shock_log = []
    
    if max_days is None:
        days_open = (date.today() - shop.shop_opened_at).days
    else:
        days_open = max_days
    
    if days_open <= 0:
        days_open = 30
    
    for day in range(days_open):
        current_date = shop.shop_opened_at + timedelta(days=day)
        
        if current_date > date.today():
            break
        
        # Advance shop state (includes shock checks)
        actual_orders, avg_ticket, state_multiplier, shock_effects = shop_state.advance_day(current_date)
        
        # Log any new shocks
        if shop_state.shock_log and len(shop_state.shock_log) > 0:
            latest_shock = shop_state.shock_log[-1]
            if latest_shock['date'] == current_date:
                shock_log.append(latest_shock)
        
        # Generate Poisson arrival times
        arrival_times = shop_state.generate_arrivals_for_day(current_date)
        
        # Adjust for shock effects on pricing
        price_multiplier = shock_effects.get('prices', 1.0)
        
        # Limit to expected number of orders
        if len(arrival_times) > actual_orders:
            arrival_times = random.sample(arrival_times, actual_orders)
        elif len(arrival_times) < actual_orders:
            extra_needed = actual_orders - len(arrival_times)
            opening_hour = shop_state.opening_hour
            closing_hour = shop_state.closing_hour
            for _ in range(extra_needed):
                hour = random.randint(opening_hour, closing_hour - 1)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                extra_time = datetime.combine(current_date, time(hour, minute, second))
                arrival_times.append(extra_time)
        
        arrival_times.sort()
        
        # Generate transaction for each arrival
        for arrival_time in arrival_times:
            # Apply price shock effects
            temp_price_multiplier = price_multiplier
            
            transaction = generate_single_transaction_with_shocks(
                order_id_counter,
                shop,
                shop_products,
                total_employees,
                arrival_time,
                avg_ticket,
                shop_state.markov.current_state,
                temp_price_multiplier,
                shop_state.shock_effects
            )
            
            if transaction:
                order, items, payment = transaction
                all_orders.append(order)
                all_items.extend(items)
                all_payments.append(payment)
                order_id_counter += 1
    
    return all_orders, all_items, all_payments, order_id_counter, shock_log

def generate_single_transaction_with_shocks(
    order_id: int,
    shop: CoffeeShop,
    shop_products: List[Product],
    total_employees: int,
    ordered_at: datetime,
    avg_ticket: float,
    markov_state: str,
    price_multiplier: float = 1.0,
    shock_effects: Dict = None
) -> Optional[Tuple[Orders, List[OrderItem], Payment]]:
    """Generate a single transaction with shock effects"""
    
    if not shop_products:
        return None
    
    available_products = [p for p in shop_products if p.product_is_available]
    if not available_products:
        available_products = shop_products
    
    # Apply shock effects to availability
    if shock_effects and shock_effects.get('availability', 1.0) < 0.8:
        # Some products unavailable due to supply chain shock
        availability_ratio = shock_effects['availability']
        available_count = max(1, int(len(available_products) * availability_ratio))
        available_products = random.sample(available_products, available_count)
    
    # Determine cart size based on average ticket and state
    avg_item_price = 70.0
    expected_items = max(1, int(avg_ticket / avg_item_price))
    
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
        if markov_state == 'booming':
            quantity = random.choices([1, 2, 3, 4], weights=[0.6, 0.25, 0.10, 0.05], k=1)[0]
        else:
            quantity = random.choices([1, 2, 3], weights=[0.85, 0.12, 0.03], k=1)[0]
        
        base_uninflated_price = PRODUCT_BASELINE[prod.product_category][prod.product_name]
        unit_price = calculate_historical_price(base_uninflated_price, shop, total_employees, ordered_at.year)
        
        # Apply price shock multiplier
        unit_price *= price_multiplier
        
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
        print("\n Failed to sync pre-existing database constraints:", error)
        if conn: conn.close()
        exit(1)

    # Configuration
    CHUNK_SIZE = 5  # Smaller chunks due to complex generation with shocks
    total_processed = 0
    all_shock_log = []  # Track all shocks across all shops
    
    print(f"\n🚀 Streaming data generation with:")
    print(f"   • Poisson arrival processes (realistic customer timing)")
    print(f"   • Random walks (day-to-day trends and momentum)")
    print(f"   • Markov chains (business cycles: booming/normal/slow/struggling)")
    print(f"   • Stochastic shocks (unexpected macro events)")
    print(f"   • Chunk size: {CHUNK_SIZE} shops per batch\n")
    
    try:
        for chunk_start in range(start_shop_id, start_shop_id + num_shops, CHUNK_SIZE):
            chunk_end = min(chunk_start + CHUNK_SIZE, start_shop_id + num_shops)
            print(f"\n{'='*60}")
            print(f"Processing shops {chunk_start} to {chunk_end - 1}...")
            print(f"{'='*60}")
            
            # Generate shops
            shops = [generate_coffee_shop(i) for i in range(chunk_start, chunk_end)]
            
            # --- INSERT COFFEE SHOPS ---
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

            # --- INSERT EMPLOYEES ---
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

            # --- INSERT PRODUCTS ---
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

            # --- GENERATE TRANSACTIONS WITH ALL FEATURES ---
            chunk_orders = []
            chunk_items = []
            chunk_payments = []
            chunk_shock_log = []
            
            shop_summaries = []
            
            for shop_idx, shop in enumerate(shops):
                print(f"\nShop {shop.shop_id}: {shop.shop_name}")
                print(f" {shop.shop_address.district}, {shop.shop_address.city}")
                print(f" Opened: {shop.shop_opened_at.strftime('%Y-%m-%d')}")
                
                shop_products = products_by_shop[shop.shop_id]
                active_staff_count = len([e for e in employees_by_shop[shop.shop_id] if e.employee_current_status == 'active'])
                
                # Extract opening and closing hours
                if shop.operating_hours:
                    opening_hour = shop.operating_hours[0][0].hour
                    closing_hour = shop.operating_hours[0][1].hour
                else:
                    opening_hour = 8
                    closing_hour = 22
                
                # Initialize shop state with all features
                shop_state = ShopStateTracker(
                    shop.shop_id,
                    opening_hour=opening_hour,
                    closing_hour=closing_hour
                )
                
                # Store available products for shock targeting
                shop_state.available_products = [p.product_name for p in shop_products]
                
                # Generate transactions with all features
                orders, items, payments, order_id_counter, shock_log = generate_transactions_with_shocks(
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
                chunk_shock_log.extend(shock_log)
                
                # Calculate summary statistics
                if len(orders) > 0:
                    total_revenue = sum(o.order_total for o in orders)
                    avg_order_value = total_revenue / len(orders) if orders else 0
                    days_active = shop_state.day_counter
                    
                    # Count orders by day (approximate)
                    order_days = {}
                    for order in orders:
                        order_date = order.ordered_at.date()
                        order_days[order_date] = order_days.get(order_date, 0) + 1
                    
                    avg_daily_orders = len(orders) / max(1, days_active)
                    
                    shop_summaries.append({
                        'shop_id': shop.shop_id,
                        'name': shop.shop_name,
                        'days_active': days_active,
                        'total_orders': len(orders),
                        'avg_daily_orders': avg_daily_orders,
                        'total_revenue': total_revenue,
                        'avg_order_value': avg_order_value,
                        'shocks': len(shock_log)
                    })
                    
                    print(f"Generated {len(orders)} orders over {days_active} days")
                    print(f"         Avg daily: {avg_daily_orders:.1f} orders/day")
                    print(f"         Total revenue: ₺{total_revenue:,.2f}")
                    print(f"         Avg order: ₺{avg_order_value:.2f}")
                    print(f"         ⚡ Shocks: {len(shock_log)} events")
                    
                    # Show shock summary if any
                    if shock_log:
                        print(f"         🚨 Recent shocks:")
                        for shock in shock_log[-3:]:  # Show last 3 shocks
                            print(f"            • {shock['date'].strftime('%Y-%m-%d')}: {shock['description']}")
                else:
                    print(f"No orders generated (shop may have just opened)")

            # --- INSERT ORDERS ---
            if chunk_orders:
                print(f"\n  💾 Inserting {len(chunk_orders)} orders into database...")
                
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

                # --- INSERT ORDER ITEMS ---
                print(f"Inserting {len(chunk_items)} order items...")
                item_records = []
                for item in chunk_items:
                    item_records.append((
                        shop_id_map[item.shop_id], order_id_map[item.order_id], 
                        product_id_map[(item.shop_id, item.product_id)], item.quantity, item.unit_price
                    ))
                execute_values(cursor, "INSERT INTO OrderItem (shop_id, order_id, product_id, quantity, unit_price) VALUES %s;", item_records)

                # --- INSERT PAYMENTS ---
                print(f"Inserting {len(chunk_payments)} payments...")
                pay_records = []
                for pay in chunk_payments:
                    pay_records.append((
                        shop_id_map[pay.shop_id], order_id_map[pay.order_id], 
                        pay.paid_at, pay.payment_method, pay.payment_status, pay.amount
                    ))
                execute_values(cursor, "INSERT INTO Payment (shop_id, order_id, paid_at, payment_method, payment_status, payment_amount) VALUES %s;", pay_records)
                
                # --- INSERT SHOCK LOG (Optional: If you want to track shocks in DB) ---
                # You could create a ShockLog table and insert here
            
            # Commit this chunk
            conn.commit()
            total_processed += len(shops)
            all_shock_log.extend(chunk_shock_log)
            
            # Print chunk summary
            print(f"\n{'─'*60}")
            print(f"Chunk complete: {total_processed}/{num_shops} shops processed")
            print(f"   Total orders in chunk: {len(chunk_orders)}")
            print(f"   Total shocks in chunk: {len(chunk_shock_log)}")
            print(f"{'─'*60}")

        # --- FINAL SUMMARY ---
        print(f"\n{'='*60}")
        print(f"🎉 GRAND SUCCESS! All {num_shops} shops processed!")
        print(f"{'='*60}")
        
        # Print overall statistics
        total_orders = 0
        total_revenue = 0
        total_shocks = len(all_shock_log)
        
        for summary in shop_summaries:
            total_orders += summary['total_orders']
            total_revenue += summary['total_revenue']
        
        print(f" OVERALL STATISTICS:")
        print(f"   • Shops generated: {num_shops}")
        print(f"   • Total orders: {total_orders:,}")
        print(f"   • Total revenue: ₺{total_revenue:,.2f}")
        print(f"   • Average orders per shop: {total_orders/num_shops:.1f}")
        print(f"   • Average revenue per shop: ₺{total_revenue/num_shops:,.2f}")
        print(f"   • Total stochastic shocks: {total_shocks}")
        print(f"   • Average shocks per shop: {total_shocks/num_shops:.1f}")
        
        # Print shock type breakdown
        if all_shock_log:
            from collections import Counter
            shock_types = Counter([s['shock_type'] for s in all_shock_log])
          
            for shock_type, count in shock_types.most_common():
                print(f"   • {shock_type}: {count} events")
        
        # Print shop with most orders
        if shop_summaries:
            best_shop = max(shop_summaries, key=lambda x: x['total_orders'])
            print(f" TOP PERFORMING SHOP:")
            print(f"   • {best_shop['name']} (ID: {best_shop['shop_id']})")
            print(f"   • {best_shop['total_orders']} orders over {best_shop['days_active']} days")
            print(f"   • Average {best_shop['avg_daily_orders']:.1f} orders/day")
            print(f"   • Revenue: ₺{best_shop['total_revenue']:,.2f}")
            
            # Shop with most shocks
            most_shocked = max(shop_summaries, key=lambda x: x['shocks'])
            if most_shocked['shocks'] > 0:
                print(f"\n⚡ MOST IMPACTED BY SHOCKS:")
                print(f"   • {most_shocked['name']} (ID: {most_shocked['shop_id']})")
                print(f"   • {most_shocked['shocks']} shock events")
        
        print(f"\nDatabase connection closed. All data committed successfully!")

    except Exception as error:
        print(f"\n Error during execution chunk loop: {error}")
        if conn: 
            conn.rollback()
            print(" Transaction rolled back")
        import traceback
        traceback.print_exc()
    finally:
        if cursor: 
            cursor.close()
        if conn: 
            conn.close()
            print("Database connection successfully closed")
