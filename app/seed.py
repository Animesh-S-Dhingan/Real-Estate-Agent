"""Delhi NCR pilot seed data (permissioned sample inventory)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.amenity import Amenity, DataSource
from app.models.geo import GeographicArea, Project
from app.models.market import MarketObservation
from app.models.property import Listing, Property
from app.models.user import Organisation, OrganisationMembership, User, UserRole

settings = get_settings()


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace("/", "-")


def seed_if_empty(db: Session) -> None:
    if db.query(GeographicArea).count() > 0:
        return
    seed_all(db)


def seed_all(db: Session) -> dict:
    now = datetime.now(timezone.utc)

    internal = DataSource(
        name="EstateAI Direct Listings",
        source_type="internal",
        terms_url=None,
        permitted_storage_policy="full",
        permitted_display_policy="full",
        attribution_requirements="EstateAI inventory",
    )
    report = DataSource(
        name="Internal Asking-Price Sample",
        source_type="market_observation",
        permitted_storage_policy="full",
        permitted_display_policy="disclose_methodology",
        attribution_requirements="Asking prices only — not transactions",
    )
    db.add_all([internal, report])
    db.flush()

    # Cities
    cities = {
        "Delhi": (28.6139, 77.2090),
        "Gurugram": (28.4595, 77.0266),
        "Noida": (28.5355, 77.3910),
        "Greater Noida": (28.4744, 77.5040),
        "Ghaziabad": (28.6692, 77.4538),
        "Faridabad": (28.4089, 77.3178),
    }
    city_rows: dict[str, GeographicArea] = {}
    for name, (lat, lng) in cities.items():
        row = GeographicArea(
            name=name,
            area_type="city",
            canonical_slug=_slug(name),
            center_lat=lat,
            center_lng=lng,
            coverage_level="partial" if name in {"Gurugram", "Noida", "Ghaziabad"} else "minimal",
            source_reference="pilot-onboarding-wave-1",
        )
        db.add(row)
        city_rows[name] = row
    db.flush()

    localities_spec = [
        ("Dwarka", "Delhi", 28.5921, 77.0460, "partial"),
        ("Rohini", "Delhi", 28.7495, 77.0565, "minimal"),
        ("South Delhi", "Delhi", 28.5245, 77.2066, "minimal"),
        ("Golf Course Road", "Gurugram", 28.4421, 77.1016, "partial"),
        ("Dwarka Expressway", "Gurugram", 28.5080, 76.9800, "partial"),
        ("Sohna Road", "Gurugram", 28.4089, 77.0410, "partial"),
        ("Sector 62", "Noida", 28.6270, 77.3649, "partial"),
        ("Noida Expressway", "Noida", 28.5350, 77.3910, "partial"),
        ("Greater Noida West", "Greater Noida", 28.5640, 77.3300, "minimal"),
        ("Indirapuram", "Ghaziabad", 28.6415, 77.3730, "partial"),
        ("Vaishali", "Ghaziabad", 28.6430, 77.3380, "partial"),
        ("Raj Nagar Extension", "Ghaziabad", 28.7005, 77.4200, "minimal"),
        ("Faridabad Metro Belt", "Faridabad", 28.4089, 77.3178, "minimal"),
    ]
    loc_rows: dict[str, GeographicArea] = {}
    for name, city, lat, lng, coverage in localities_spec:
        row = GeographicArea(
            name=name,
            area_type="locality",
            parent_area_id=city_rows[city].id,
            canonical_slug=_slug(name),
            center_lat=lat,
            center_lng=lng,
            coverage_level=coverage,
        )
        db.add(row)
        loc_rows[name] = row
    db.flush()

    admin = User(
        email=settings.seed_admin_email.lower(),
        password_hash=hash_password(settings.seed_admin_password),
        full_name="EstateAI Admin",
        preferences={"purpose": "buy", "preferred_locations": ["Noida", "Gurugram"]},
    )
    agent = User(
        email="agent@estateai.example",
        password_hash=hash_password("Agent@12345"),
        full_name="Priya Sharma",
        phone="+919811112222",
        preferences={},
    )
    consumer = User(
        email="buyer@estateai.example",
        password_hash=hash_password("Buyer@12345"),
        full_name="Aarav Mehta",
        preferences={
            "budget_max": 8000000,
            "configuration": ["2BHK", "3BHK"],
            "preferred_locations": ["Gurugram", "Noida"],
        },
    )
    db.add_all([admin, agent, consumer])
    db.flush()
    db.add_all(
        [
            UserRole(user_id=admin.id, role="admin"),
            UserRole(user_id=agent.id, role="agent"),
            UserRole(user_id=consumer.id, role="consumer"),
        ]
    )

    agency = Organisation(
        name="NCR Nest Realty",
        organisation_type="agency",
        verification_status="verified",
        registration_reference="DEMO-AGENCY-001",
        contact_email="agent@estateai.example",
        contact_phone="+919811112222",
    )
    db.add(agency)
    db.flush()
    db.add(OrganisationMembership(organisation_id=agency.id, user_id=agent.id, role="agent", status="active"))

    projects = [
        Project(
            developer_organisation_id=None,
            locality_id=loc_rows["Sector 62"].id,
            name="Green Heights Residences",
            address="Sector 62, Noida",
            lat=28.6275,
            lng=77.3655,
            construction_status="ready",
            registration_authority="UP RERA",
            registration_number="UPRERAPRJ12345",
            verification_status="recorded",
        ),
        Project(
            locality_id=loc_rows["Golf Course Road"].id,
            name="Fairway Towers",
            address="Golf Course Road, Gurugram",
            lat=28.4430,
            lng=77.1025,
            construction_status="ready",
            registration_authority="Haryana RERA",
            registration_number="HRERA-GGM-9988",
            verification_status="recorded",
        ),
    ]
    db.add_all(projects)
    db.flush()

    listings_data = [
        {
            "title": "Bright 2BHK near Sector 62 metro",
            "locality": "Sector 62",
            "purpose": "buy",
            "type": "apartment",
            "config": "2BHK",
            "beds": 2,
            "baths": 2,
            "sba": Decimal("1180"),
            "carpet": Decimal("950"),
            "price": Decimal("7500000"),
            "rent": None,
            "lat": 28.6272,
            "lng": 77.3645,
            "furnish": "semi-furnished",
            "desc": "Owner-authorised listing. Facing park. Metro ~1.2 km (estimate).",
            "tags": ["metro", "parking", "power-backup"],
            "project": projects[0],
        },
        {
            "title": "Spacious 3BHK on Golf Course Road",
            "locality": "Golf Course Road",
            "purpose": "buy",
            "type": "apartment",
            "config": "3BHK",
            "beds": 3,
            "baths": 3,
            "sba": Decimal("1850"),
            "carpet": Decimal("1450"),
            "price": Decimal("18500000"),
            "rent": None,
            "lat": 28.4428,
            "lng": 77.1019,
            "furnish": "furnished",
            "desc": "Premium corridor apartment with club access. Asking price observation only.",
            "tags": ["club", "parking", "security"],
            "project": projects[1],
        },
        {
            "title": "Affordable 2BHK Indirapuram for rent",
            "locality": "Indirapuram",
            "purpose": "rent",
            "type": "apartment",
            "config": "2BHK",
            "beds": 2,
            "baths": 2,
            "sba": Decimal("1100"),
            "carpet": Decimal("900"),
            "price": None,
            "rent": Decimal("22000"),
            "lat": 28.6418,
            "lng": 77.3735,
            "furnish": "semi-furnished",
            "desc": "Available immediately. Deposit negotiable. Near schools and markets.",
            "tags": ["school", "market"],
            "project": None,
        },
        {
            "title": "3BHK family home Vaishali",
            "locality": "Vaishali",
            "purpose": "buy",
            "type": "apartment",
            "config": "3BHK",
            "beds": 3,
            "baths": 2,
            "sba": Decimal("1450"),
            "carpet": Decimal("1200"),
            "price": Decimal("9200000"),
            "rent": None,
            "lat": 28.6435,
            "lng": 77.3390,
            "furnish": "unfurnished",
            "desc": "Metro-connected Ghaziabad locality. Fresh inventory for pilot wave 1.",
            "tags": ["metro", "park"],
            "project": None,
        },
        {
            "title": "2BHK Dwarka Expressway apartment",
            "locality": "Dwarka Expressway",
            "purpose": "buy",
            "type": "apartment",
            "config": "2BHK",
            "beds": 2,
            "baths": 2,
            "sba": Decimal("1250"),
            "carpet": Decimal("1000"),
            "price": Decimal("9800000"),
            "rent": None,
            "lat": 28.5085,
            "lng": 76.9810,
            "furnish": "semi-furnished",
            "desc": "New inventory along expressway corridor. Project status should be verified independently.",
            "tags": ["expressway", "parking"],
            "project": None,
        },
        {
            "title": "1BHK studio rental Sector 62",
            "locality": "Sector 62",
            "purpose": "rent",
            "type": "apartment",
            "config": "1BHK",
            "beds": 1,
            "baths": 1,
            "sba": Decimal("650"),
            "carpet": Decimal("520"),
            "price": None,
            "rent": Decimal("16000"),
            "lat": 28.6260,
            "lng": 77.3630,
            "furnish": "furnished",
            "desc": "Suitable for working professionals near IT hubs.",
            "tags": ["office", "metro"],
            "project": projects[0],
        },
        {
            "title": "4BHK villa Sohna Road",
            "locality": "Sohna Road",
            "purpose": "buy",
            "type": "villa",
            "config": "4BHK",
            "beds": 4,
            "baths": 4,
            "sba": Decimal("3200"),
            "carpet": Decimal("2800"),
            "price": Decimal("35000000"),
            "rent": None,
            "lat": 28.4095,
            "lng": 77.0420,
            "furnish": "semi-furnished",
            "desc": "Independent villa listing. Legal diligence recommended before commitment.",
            "tags": ["garden", "parking"],
            "project": None,
        },
        {
            "title": "2BHK Dwarka for sale",
            "locality": "Dwarka",
            "purpose": "buy",
            "type": "apartment",
            "config": "2BHK",
            "beds": 2,
            "baths": 2,
            "sba": Decimal("1050"),
            "carpet": Decimal("850"),
            "price": Decimal("8200000"),
            "rent": None,
            "lat": 28.5925,
            "lng": 77.0465,
            "furnish": "unfurnished",
            "desc": "Wave-2 locality sample. Coverage still partial.",
            "tags": ["metro"],
            "project": None,
        },
    ]

    for item in listings_data:
        prop = Property(
            project_id=item["project"].id if item["project"] else None,
            locality_id=loc_rows[item["locality"]].id,
            title=item["title"],
            address=f"{item['locality']}, Delhi NCR",
            lat=item["lat"],
            lng=item["lng"],
            property_type=item["type"],
            configuration=item["config"],
            bedrooms=item["beds"],
            bathrooms=item["baths"],
            carpet_area=item["carpet"],
            super_built_up_area=item["sba"],
            area_unit="sq_ft",
            furnishing_status=item["furnish"],
            parking_details="1 covered",
            floor_number=5,
            total_floors=18,
            amenities_tags=",".join(item["tags"]),
        )
        db.add(prop)
        db.flush()
        listing = Listing(
            property_id=prop.id,
            submitted_by_user_id=agent.id,
            organisation_id=agency.id,
            listing_purpose=item["purpose"],
            asking_price=item["price"],
            monthly_rent=item["rent"],
            security_deposit=item["rent"] * 2 if item["rent"] else None,
            currency="INR",
            availability_status="available",
            publication_status="published",
            description=item["desc"],
            source_type="agent",
            last_confirmed_at=now,
            published_at=now,
            expires_at=now + timedelta(days=settings.listing_freshness_days),
        )
        db.add(listing)

    amenities = [
        ("Sector 62 Metro Station", "metro", 28.6205, 77.3640),
        ("Fortis Hospital Noida", "hospital", 28.5700, 77.3250),
        ("Amity International School", "school", 28.6300, 77.3700),
        ("Gardens Galleria Mall", "shopping", 28.5670, 77.3255),
        ("City Park Indirapuram", "park", 28.6400, 77.3700),
        ("Vaishali Metro", "metro", 28.6498, 77.3395),
        ("Max Hospital Vaishali", "hospital", 28.6450, 77.3405),
        ("Golf Course Road Metro Hub", "metro", 28.4510, 77.1000),
        ("Cyber Hub Offices", "office", 28.4950, 77.0890),
        ("Dwarka Sector 21 Metro", "metro", 28.5520, 77.0580),
        ("Local Kirana Cluster Sector 62", "grocery", 28.6280, 77.3660),
        ("HDFC ATM Sector 62", "bank", 28.6278, 77.3650),
    ]
    for name, cat, lat, lng in amenities:
        db.add(
            Amenity(
                provider_name="seed",
                provider_place_id=f"seed-{_slug(name)}",
                name=name,
                category=cat,
                lat=lat,
                lng=lng,
                address=f"{name}, Delhi NCR",
                operational_status=None,
                source_updated_at=now,
            )
        )

    # Asking-price benchmarks (illustrative, insufficient for some localities)
    for loc_name, value, sample in [
        ("Sector 62", Decimal("6200"), 12),
        ("Golf Course Road", Decimal("14500"), 8),
        ("Indirapuram", Decimal("5800"), 10),
        ("Vaishali", Decimal("6100"), 6),
        ("Dwarka Expressway", Decimal("8500"), 4),  # insufficient (<5)
    ]:
        db.add(
            MarketObservation(
                locality_id=loc_rows[loc_name].id,
                property_type="apartment",
                configuration="2BHK",
                transaction_type="asking",
                area_basis="super_built_up",
                metric_name="asking_price_per_sq_ft",
                value=value,
                currency="INR",
                observation_period_start=date(2026, 7, 1),
                observation_period_end=date(2026, 9, 30),
                sample_size=sample,
                data_source_id=report.id,
                methodology_version="v1-pilot",
            )
        )

    db.commit()
    return {
        "cities": len(city_rows),
        "localities": len(loc_rows),
        "listings": len(listings_data),
        "amenities": len(amenities),
        "users": {
            "admin": settings.seed_admin_email,
            "agent": "agent@estateai.example",
            "buyer": "buyer@estateai.example",
        },
    }
