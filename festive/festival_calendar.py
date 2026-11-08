"""
CARTIVANTA - Festival Calendar & Festive Scheduling Module
Configurable calendar supporting Diwali, Pongal, Christmas, New Year, and custom festive events.
"""
from dataclasses import dataclass
from datetime import date
from typing import List, Dict, Optional
import pandas as pd

@dataclass
class FestivalEvent:
    festival_name: str
    start_date: str
    end_date: str
    festival_category: str
    demand_uplift_assumption: float # e.g. 0.35 = +35%
    notes: str
    is_synthetic: bool = True

    @property
    def start(self) -> date:
        return date.fromisoformat(self.start_date)

    @property
    def end(self) -> date:
        return date.fromisoformat(self.end_date)

# Reference Calendar of Key Retail Festivals
DEFAULT_FESTIVALS: List[FestivalEvent] = [
    FestivalEvent(
        festival_name="Diwali 2010",
        start_date="2010-10-25",
        end_date="2010-11-08",
        festival_category="Gifts & Home Decor",
        demand_uplift_assumption=0.45,
        notes="Diwali festive shopping peak across lighting, gifts, kitchenware, and seasonal hampers."
    ),
    FestivalEvent(
        festival_name="Christmas & New Year 2010",
        start_date="2010-12-01",
        end_date="2010-12-28",
        festival_category="Holiday & Seasonal",
        demand_uplift_assumption=0.55,
        notes="Major holiday peak in UK & international retail demand."
    ),
    FestivalEvent(
        festival_name="Pongal & Sankranti 2011",
        start_date="2011-01-10",
        end_date="2011-01-18",
        festival_category="Traditional & Home",
        demand_uplift_assumption=0.25,
        notes="Harvest festival seasonal demand for traditional gifts and tableware."
    ),
    FestivalEvent(
        festival_name="Diwali 2011",
        start_date="2011-10-15",
        end_date="2011-10-30",
        festival_category="Gifts & Home Decor",
        demand_uplift_assumption=0.50,
        notes="Autumn festive surge with focus on premium gifting and home adornment."
    ),
    FestivalEvent(
        festival_name="Christmas & Year End 2011",
        start_date="2011-11-25",
        end_date="2011-12-25",
        festival_category="Holiday & Seasonal",
        demand_uplift_assumption=0.60,
        notes="Annual peak volume driven by seasonal giftwares and decorations."
    )
]

class FestivalCalendarManager:
    def __init__(self, custom_festivals: Optional[List[FestivalEvent]] = None):
        self.festivals = list(DEFAULT_FESTIVALS)
        if custom_festivals:
            self.festivals.extend(custom_festivals)

    def get_all(self) -> List[FestivalEvent]:
        return self.festivals

    def to_dataframe(self) -> pd.DataFrame:
        data = [
            {
                "festival_name": f.festival_name,
                "start_date": f.start_date,
                "end_date": f.end_date,
                "festival_category": f.festival_category,
                "demand_uplift_assumption": f.demand_uplift_assumption,
                "notes": f.notes,
                "is_synthetic": f.is_synthetic
            }
            for f in self.festivals
        ]
        return pd.DataFrame(data)

    def get_festival(self, name: str) -> Optional[FestivalEvent]:
        for f in self.festivals:
            if f.festival_name.lower() == name.lower():
                return f
        return None

    def add_custom_festival(
        self,
        name: str,
        start_date: str,
        end_date: str,
        category: str,
        uplift: float,
        notes: str = "User configured festival"
    ) -> FestivalEvent:
        event = FestivalEvent(
            festival_name=name,
            start_date=start_date,
            end_date=end_date,
            festival_category=category,
            demand_uplift_assumption=uplift,
            notes=notes,
            is_synthetic=True
        )
        self.festivals.append(event)
        return event
