"""Initial migration

Revision ID: 0001_initial
Revises: 
Create Date: 2025-05-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create buildings table
    op.create_table(
        'buildings',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(length=255), nullable=False, unique=True, comment="Уникальное название/идентификатор здания"),
        sa.Column('address', sa.String(length=255), nullable=True, comment="Адрес или описание здания"),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Когда запись была создана"),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="Когда запись была обновлена"),
    )
    op.create_index('ix_buildings_id', 'buildings', ['id'])
    op.create_index('ix_buildings_name', 'buildings', ['name'])

    # Create floor_polygons table
    op.create_table(
        'floor_polygons',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('building_id', sa.Integer(), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('floor', sa.Integer(), nullable=False, comment="Этаж, к которому привязан полигон"),
        sa.Column('polygon', sa.JSON(), nullable=False, comment="Список 3D-координат точек [[x, y, z], …] для карты этажа"),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    op.create_index('ix_floor_polygons_id', 'floor_polygons', ['id'])

    # Create access_points table
    op.create_table(
        'access_points',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('bssid', sa.String(length=17), nullable=False, unique=True, index=True, comment="MAC-адрес точек доступа"),
        sa.Column('ssid', sa.String(length=255), nullable=True, comment="SSID сети, к которой принадлежит AP"),
        sa.Column('building_id', sa.Integer(), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('x', sa.Float(), nullable=True, comment="X-координата, если есть"),
        sa.Column('y', sa.Float(), nullable=True, comment="Y-координата, если есть"),
        sa.Column('z', sa.Float(), nullable=True, comment="Z-координата (высота), если есть"),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    op.create_index('ix_access_points_id', 'access_points', ['id'])
    op.create_index('ix_access_points_bssid', 'access_points', ['bssid'])

    # Create wifi_snapshots table
    op.create_table(
        'wifi_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('building_id', sa.Integer(), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('floor', sa.Integer(), nullable=False, comment="Этаж, на котором сделан снимок"),
        sa.Column('yaw', sa.Float(), nullable=True, comment="Поворот вокруг вертикальной оси (Z) — yaw"),
        sa.Column('pitch', sa.Float(), nullable=True, comment="Наклон вокруг боковой оси (X) — pitch"),
        sa.Column('roll', sa.Float(), nullable=True, comment="Наклон вокруг продольной оси (Y) — roll"),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Время получения снимка"),
    )
    op.create_index('ix_wifi_snapshots_id', 'wifi_snapshots', ['id'])

    # Create wifi_observations table
    op.create_table(
        'wifi_observations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('snapshot_id', sa.Integer(), sa.ForeignKey('wifi_snapshots.id', ondelete='CASCADE'), nullable=False),
        sa.Column('access_point_id', sa.Integer(), sa.ForeignKey('access_points.id', ondelete='SET NULL'), nullable=True, comment="Если AP уже зарегистрирован, ставим FK; иначе NULL"),
        sa.Column('ssid', sa.String(length=255), nullable=False, comment="Имя сети"),
        sa.Column('bssid', sa.String(length=17), nullable=False, comment="MAC-адрес сканируемой сети"),
        sa.Column('rssi', sa.Integer(), nullable=False, comment="Уровень сигнала (dBm)"),
        sa.Column('frequency', sa.Integer(), nullable=True, comment="Частота (MHz)"),
    )
    op.create_index('ix_wifi_observations_id', 'wifi_observations', ['id'])


def downgrade():
    op.drop_index('ix_wifi_observations_id', table_name='wifi_observations')
    op.drop_table('wifi_observations')
    op.drop_index('ix_wifi_snapshots_id', table_name='wifi_snapshots')
    op.drop_table('wifi_snapshots')
    op.drop_index('ix_access_points_bssid', table_name='access_points')
    op.drop_index('ix_access_points_id', table_name='access_points')
    op.drop_table('access_points')
    op.drop_index('ix_floor_polygons_id', table_name='floor_polygons')
    op.drop_table('floor_polygons')
    op.drop_index('ix_buildings_name', table_name='buildings')
    op.drop_index('ix_buildings_id', table_name='buildings')
    op.drop_table('buildings')