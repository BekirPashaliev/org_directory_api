"""Add geo constraints, indexes, and guard against activity cycles

Revision ID: 0002_geo_constraints
Revises: 0001_init
Create Date: 2026-01-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_geo_constraints"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_organization_activity_activity_id", "organization_activity", ["activity_id"])

    op.create_check_constraint("ck_buildings_latitude_range", "buildings", "latitude >= -90 AND latitude <= 90")
    op.create_check_constraint("ck_buildings_longitude_range", "buildings", "longitude >= -180 AND longitude <= 180")
    op.create_index("ix_buildings_latitude", "buildings", ["latitude"])
    op.create_index("ix_buildings_longitude", "buildings", ["longitude"])

    op.create_check_constraint(
        "ck_activities_no_self_parent",
        "activities",
        "parent_id IS NULL OR parent_id <> id",
    )

    op.execute(
        '''
        CREATE OR REPLACE FUNCTION set_activity_level()
        RETURNS TRIGGER AS $$
        DECLARE
            parent_level SMALLINT;
            cur_id INTEGER;
            cur_parent INTEGER;
        BEGIN
            IF NEW.parent_id IS NULL THEN
                NEW.level := 1;
                RETURN NEW;
            END IF;

            IF NEW.id IS NOT NULL AND NEW.parent_id = NEW.id THEN
                RAISE EXCEPTION 'activity cannot be its own parent';
            END IF;

            cur_id := NEW.parent_id;
            LOOP
                EXIT WHEN cur_id IS NULL;
                IF NEW.id IS NOT NULL AND cur_id = NEW.id THEN
                    RAISE EXCEPTION 'activity cycle detected';
                END IF;
                SELECT parent_id INTO cur_parent FROM activities WHERE id = cur_id;
                cur_id := cur_parent;
            END LOOP;

            SELECT level INTO parent_level FROM activities WHERE id = NEW.parent_id;
            IF parent_level IS NULL THEN
                RAISE EXCEPTION 'parent activity % not found', NEW.parent_id;
            END IF;
            IF parent_level >= 3 THEN
                RAISE EXCEPTION 'activity depth limit exceeded (max 3 levels)';
            END IF;

            NEW.level := parent_level + 1;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        '''
    )


def downgrade() -> None:
    op.execute(
        '''
        CREATE OR REPLACE FUNCTION set_activity_level()
        RETURNS TRIGGER AS $$
        DECLARE parent_level SMALLINT;
        BEGIN
            IF NEW.parent_id IS NULL THEN
                NEW.level := 1;
                RETURN NEW;
            END IF;
            SELECT level INTO parent_level FROM activities WHERE id = NEW.parent_id;
            IF parent_level IS NULL THEN
                RAISE EXCEPTION 'parent activity % not found', NEW.parent_id;
            END IF;
            IF parent_level >= 3 THEN
                RAISE EXCEPTION 'activity depth limit exceeded (max 3 levels)';
            END IF;
            NEW.level := parent_level + 1;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        '''
    )
    op.drop_constraint("ck_activities_no_self_parent", "activities", type_="check")
    op.drop_index("ix_buildings_longitude", table_name="buildings")
    op.drop_index("ix_buildings_latitude", table_name="buildings")
    op.drop_constraint("ck_buildings_longitude_range", "buildings", type_="check")
    op.drop_constraint("ck_buildings_latitude_range", "buildings", type_="check")
    op.drop_index("ix_organization_activity_activity_id", table_name="organization_activity")