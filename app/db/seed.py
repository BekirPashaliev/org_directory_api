from __future__ import annotations

from sqlalchemy import select

from app.db.models import Activity, Building, Organization, OrganizationPhone
from app.db.session import get_sessionmaker


async def seed_demo_data() -> None:
    """Idempotent demo seed.

    Creates several buildings, activities (max depth=3) and organizations.
    """

    async_session = get_sessionmaker()
    async with async_session() as session:
        # Seed only if DB is empty (at least buildings exist)
        has_any = await session.execute(select(Building.id).limit(1))
        if has_any.first() is not None:
            return

        # Buildings
        b1 = Building(address="г. Москва, ул. Ленина 1, офис 3", latitude=55.7558, longitude=37.6176)
        b2 = Building(address="г. Екатеринбург, ул. Блюхера, 32/1", latitude=56.8420, longitude=60.6122)
        b3 = Building(address="г. Санкт-Петербург, Невский проспект 10", latitude=59.9320, longitude=30.3470)
        b4 = Building(address="г. Казань, ул. Баумана 5", latitude=55.7963, longitude=49.1088)
        b5 = Building(address="г. Новосибирск, Красный проспект 25", latitude=55.0302, longitude=82.9204)

        session.add_all([b1, b2, b3, b4, b5])
        await session.flush()

        # Activities tree
        food = Activity(name="Еда", parent_id=None)
        auto = Activity(name="Автомобили", parent_id=None)
        session.add_all([food, auto])
        await session.flush()

        meat = Activity(name="Мясная продукция", parent_id=food.id)
        dairy = Activity(name="Молочная продукция", parent_id=food.id)
        cars = Activity(name="Легковые", parent_id=auto.id)
        trucks = Activity(name="Грузовые", parent_id=auto.id)
        session.add_all([meat, dairy, cars, trucks])
        await session.flush()

        sausages = Activity(name="Колбасы", parent_id=meat.id)
        cheeses = Activity(name="Сыры", parent_id=dairy.id)
        parts = Activity(name="Запчасти", parent_id=cars.id)
        accessories = Activity(name="Аксессуары", parent_id=cars.id)
        session.add_all([sausages, cheeses, parts, accessories])
        await session.flush()

        # Organizations
        o1 = Organization(name='ООО "Рога и Копыта"', building_id=b2.id)
        o1.phones = [
            OrganizationPhone(phone="2-222-222"),
            OrganizationPhone(phone="3-333-333"),
            OrganizationPhone(phone="8-923-666-13-13"),
        ]
        o1.activities = [meat, dairy]

        o2 = Organization(name='ИП "Молочный мир"', building_id=b1.id)
        o2.phones = [OrganizationPhone(phone="8-800-111-22-33")]
        o2.activities = [dairy, cheeses]

        o3 = Organization(name='ООО "Мясной двор"', building_id=b3.id)
        o3.phones = [OrganizationPhone(phone="8-495-000-00-01")]
        o3.activities = [meat, sausages]

        o4 = Organization(name='ООО "Авто-Лайн"', building_id=b4.id)
        o4.phones = [OrganizationPhone(phone="8-843-100-10-10")]
        o4.activities = [cars, accessories]

        o5 = Organization(name='ООО "Запчасти плюс"', building_id=b4.id)
        o5.phones = [OrganizationPhone(phone="8-843-200-20-20")]
        o5.activities = [parts]

        o6 = Organization(name='ООО "ГрузСервис"', building_id=b5.id)
        o6.phones = [OrganizationPhone(phone="8-383-300-30-30")]
        o6.activities = [trucks]

        o7 = Organization(name='Кафе "У дома"', building_id=b1.id)
        o7.phones = [OrganizationPhone(phone="8-495-777-77-77")]
        o7.activities = [food]

        session.add_all([o1, o2, o3, o4, o5, o6, o7])
        await session.commit()
