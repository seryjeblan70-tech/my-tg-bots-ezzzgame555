from pydantic import BaseModel
from typing import Optional, List

class GameUser(BaseModel):
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    food: int = 50
    gems: float = 100.0
    click_power: float = 1.0
    click_upgrade_level: int = 0
    stamina: int = 100
    max_stamina: int = 100
    stamina_regen_rate: float = 1.0
    regen_upgrade_level: int = 0
    max_stamina_upgrade_level: int = 0
    total_clicks: int = 0
    unlocked_pets: List[str] = ['dog', 'cat', 'rabbit']
    selected_pet: str = 'dog'
    friends_count: int = 0
    created_at: Optional[str] = None

    class Config:
        from_attributes = True  # позволяет создавать модель из SQLAlchemy-объекта