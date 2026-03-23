"""Brand management — create and manage brand identities."""

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from libro.models.brand import Brand


# Curated color palettes for quick brand creation
COLOR_PALETTES = {
    "midnight": {
        "primary_color": "#1A1A2E",
        "secondary_color": "#E8E8E8",
        "accent_color": "#E94560",
        "description": "Dark navy with red accent — elegant, premium",
    },
    "forest": {
        "primary_color": "#2D4A3E",
        "secondary_color": "#F5F0E8",
        "accent_color": "#C8A96E",
        "description": "Deep green with gold — natural, calming",
    },
    "ocean": {
        "primary_color": "#1B4965",
        "secondary_color": "#F0F4F8",
        "accent_color": "#5FA8D3",
        "description": "Navy blue with light blue — clean, trustworthy",
    },
    "sunset": {
        "primary_color": "#4A1942",
        "secondary_color": "#FFF4E0",
        "accent_color": "#F0A500",
        "description": "Deep purple with gold — warm, inspiring",
    },
    "minimal": {
        "primary_color": "#FFFFFF",
        "secondary_color": "#1A1A1A",
        "accent_color": "#C0392B",
        "description": "White with black text — clean, modern",
    },
    "sage": {
        "primary_color": "#A8B5A2",
        "secondary_color": "#2C2C2C",
        "accent_color": "#6B4C3B",
        "description": "Sage green with brown — organic, wellness",
    },
    "blush": {
        "primary_color": "#F4D1D1",
        "secondary_color": "#2C2C2C",
        "accent_color": "#8B4513",
        "description": "Soft pink with brown — feminine, gentle",
    },
    "slate": {
        "primary_color": "#2F3640",
        "secondary_color": "#DFE6E9",
        "accent_color": "#00B894",
        "description": "Dark gray with teal — professional, focused",
    },
}


@dataclass
class BrandStyle:
    """Parsed brand style configuration."""
    font: str
    primary_color: str
    secondary_color: str
    accent_color: str

    @classmethod
    def from_brand(cls, brand: Brand) -> "BrandStyle":
        if brand.style_config_json:
            data = json.loads(brand.style_config_json)
        else:
            data = {}
        return cls(
            font=data.get("font", "Sans"),
            primary_color=data.get("primary_color", "#2C3E50"),
            secondary_color=data.get("secondary_color", "#ECF0F1"),
            accent_color=data.get("accent_color", "#E74C3C"),
        )

    def to_json(self) -> str:
        return json.dumps({
            "font": self.font,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "accent_color": self.accent_color,
        })


def create_brand(
    session: Session,
    name: str,
    palette: str | None = None,
    font: str = "Sans",
    primary_color: str | None = None,
    secondary_color: str | None = None,
    accent_color: str | None = None,
) -> Brand:
    """Create a brand with a color palette or custom colors."""
    if palette and palette in COLOR_PALETTES:
        p = COLOR_PALETTES[palette]
        primary_color = primary_color or p["primary_color"]
        secondary_color = secondary_color or p["secondary_color"]
        accent_color = accent_color or p["accent_color"]

    style = BrandStyle(
        font=font,
        primary_color=primary_color or "#2C3E50",
        secondary_color=secondary_color or "#ECF0F1",
        accent_color=accent_color or "#E74C3C",
    )

    brand = Brand(name=name, style_config_json=style.to_json())
    session.add(brand)
    session.flush()
    return brand
