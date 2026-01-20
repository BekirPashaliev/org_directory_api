"""initial schema

Revision ID: 0001_init
Revises: 
Create Date: 2026-01-16

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "buildings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("address", sa.String(length=512), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
    )
    op.create_index("ix_buildings_address", "buildings", ["address"])

    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("level", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["parent_id"], ["activities.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("parent_id", "name", name="uq_activity_parent_name"),
    )
    op.create_index("ix_activities_parent_id", "activities", ["parent_id"])
    op.create_check_constraint("ck_activities_level", "activities", "level BETWEEN 1 AND 3")

    # Trigger to maintain activities.level and enforce max depth=3
    # NOTE: asyncpg does not allow multiple SQL commands in one prepared statement
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_activity_level() RETURNS TRIGGER AS $$
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
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_set_activity_level ON activities")
    op.execute(
        """
        CREATE TRIGGER trg_set_activity_level
        BEFORE INSERT OR UPDATE OF parent_id
        ON activities
        FOR EACH ROW
        EXECUTE FUNCTION set_activity_level()
        """
    )

    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("building_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_organizations_name", "organizations", ["name"])
    op.create_index("ix_organizations_building_id", "organizations", ["building_id"])

    op.create_table(
        "organization_phones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "phone", name="uq_org_phone"),
    )
    op.create_index("ix_organization_phones_organization_id", "organization_phones", ["organization_id"])

    op.create_table(
        "organization_activity",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organization_id", "activity_id"),
    )


def downgrade() -> None:
    op.drop_table("organization_activity")
    op.drop_index("ix_organization_phones_organization_id", table_name="organization_phones")
    op.drop_table("organization_phones")
    op.drop_index("ix_organizations_building_id", table_name="organizations")
    op.drop_index("ix_organizations_name", table_name="organizations")
    op.drop_table("organizations")

    op.execute("DROP TRIGGER IF EXISTS trg_set_activity_level ON activities;")
    op.execute("DROP FUNCTION IF EXISTS set_activity_level();")

    op.drop_constraint("ck_activities_level", "activities", type_="check")
    op.drop_index("ix_activities_parent_id", table_name="activities")
    op.drop_table("activities")

    op.drop_index("ix_buildings_address", table_name="buildings")
    op.drop_table("buildings")
