import json

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String, Text

from database import Base
from domain_types import (
    coerce_league_info_storage,
    expected_category,
    league_info_key_category_check_sql,
    league_info_key_check_sql,
    league_info_key_type_check_sql,
    league_info_payload_check_sql,
    league_info_value_type_check_sql,
    parse_league_info_python_value,
    serialize_league_info_value,
    transfer_operation_check_sql,
)


class LeagueInfo(Base):
    __tablename__ = "league_info"
    __table_args__ = (
        CheckConstraint(league_info_key_check_sql(), name="ck_league_info_key"),
        CheckConstraint(league_info_value_type_check_sql(), name="ck_league_info_value_type"),
        CheckConstraint(league_info_payload_check_sql(), name="ck_league_info_payload"),
        CheckConstraint(league_info_key_type_check_sql(), name="ck_league_info_key_type"),
        CheckConstraint(league_info_key_category_check_sql(), name="ck_league_info_key_category"),
    )

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, nullable=False)
    value_type = Column(String, nullable=False)
    int_value = Column(Integer)
    float_value = Column(Float)
    text_value = Column(String)

    @property
    def value(self) -> str:
        return serialize_league_info_value(self.value_type, self.int_value, self.float_value, self.text_value)

    @property
    def python_value(self):
        return parse_league_info_python_value(self.value_type, self.int_value, self.float_value, self.text_value)

    def set_typed_value(self, raw_value) -> "LeagueInfo":
        value_type, int_value, float_value, text_value = coerce_league_info_storage(self.key, raw_value)
        self.category = expected_category(self.key)
        self.value_type = value_type
        self.int_value = int_value
        self.float_value = float_value
        self.text_value = text_value
        return self


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    manager = Column(String)
    level = Column(String)
    wage = Column(Float)
    team_size = Column(Integer, default=0)
    gk_count = Column(Integer, default=0)
    extra_wage = Column(Float, default=0)
    after_tax = Column(Float, default=0)
    final_wage = Column(Float, default=0)
    count_8m = Column(Integer, default=0)
    count_7m = Column(Integer, default=0)
    count_fake = Column(Integer, default=0)
    total_value = Column(Float, default=0)
    avg_value = Column(Float, default=0)
    avg_ca = Column(Float, default=0)
    avg_pa = Column(Float, default=0)
    total_growth = Column(Integer, default=0)
    stats_cache_refresh_mode = Column(String, default="unknown")
    stats_cache_refresh_scopes = Column(String, default="")
    stats_cache_refresh_at = Column(DateTime)
    notes = Column(String)


class Player(Base):
    __tablename__ = "players"

    uid = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer)
    initial_ca = Column(Integer, default=0)
    ca = Column(Integer)
    pa = Column(Integer)
    position = Column(String)
    nationality = Column(String)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    team_name = Column(String, index=True)
    wage = Column(Float)
    slot_type = Column(String)


class PlayerAttribute(Base):
    __tablename__ = "player_attributes"

    uid = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    position = Column(String)
    age = Column(Integer)
    ca = Column(Integer)
    pa = Column(Integer)
    nationality = Column(String)
    club = Column(String)

    corner = Column(Integer, default=0)
    crossing = Column(Integer, default=0)
    dribbling = Column(Integer, default=0)
    finishing = Column(Integer, default=0)
    first_touch = Column(Integer, default=0)
    free_kick = Column(Integer, default=0)
    heading = Column(Integer, default=0)
    long_shots = Column(Integer, default=0)
    long_throws = Column(Integer, default=0)
    marking = Column(Integer, default=0)
    passing = Column(Integer, default=0)
    penalty = Column(Integer, default=0)
    tackling = Column(Integer, default=0)
    technique = Column(Integer, default=0)

    aggression = Column(Integer, default=0)
    anticipation = Column(Integer, default=0)
    bravery = Column(Integer, default=0)
    composure = Column(Integer, default=0)
    concentration = Column(Integer, default=0)
    decisions = Column(Integer, default=0)
    determination = Column(Integer, default=0)
    flair = Column(Integer, default=0)
    leadership = Column(Integer, default=0)
    off_the_ball = Column(Integer, default=0)
    positioning = Column(Integer, default=0)
    teamwork = Column(Integer, default=0)
    vision = Column(Integer, default=0)
    work_rate = Column(Integer, default=0)

    acceleration = Column(Integer, default=0)
    agility = Column(Integer, default=0)
    balance = Column(Integer, default=0)
    jumping = Column(Integer, default=0)
    natural_fitness = Column(Integer, default=0)
    pace = Column(Integer, default=0)
    stamina = Column(Integer, default=0)
    strength = Column(Integer, default=0)

    consistency = Column(Integer, default=0)
    dirtiness = Column(Integer, default=0)
    important_matches = Column(Integer, default=0)
    injury_proneness = Column(Integer, default=0)
    versatility = Column(Integer, default=0)
    adaptability = Column(Integer, default=0)
    ambition = Column(Integer, default=0)
    controversy = Column(Integer, default=0)
    loyalty = Column(Integer, default=0)
    pressure = Column(Integer, default=0)
    professionalism = Column(Integer, default=0)
    sportsmanship = Column(Integer, default=0)
    temperament = Column(Integer, default=0)

    aerial_ability = Column(Integer, default=0)
    command_of_area = Column(Integer, default=0)
    communication = Column(Integer, default=0)
    eccentricity = Column(Integer, default=0)
    handling = Column(Integer, default=0)
    kicking = Column(Integer, default=0)
    one_on_ones = Column(Integer, default=0)
    reflexes = Column(Integer, default=0)
    rushing_out = Column(Integer, default=0)
    tendency_to_punch = Column(Integer, default=0)
    throwing = Column(Integer, default=0)

    pos_gk = Column(Integer, default=0)
    pos_dl = Column(Integer, default=0)
    pos_dc = Column(Integer, default=0)
    pos_dr = Column(Integer, default=0)
    pos_wbl = Column(Integer, default=0)
    pos_wbr = Column(Integer, default=0)
    pos_dm = Column(Integer, default=0)
    pos_ml = Column(Integer, default=0)
    pos_mc = Column(Integer, default=0)
    pos_mr = Column(Integer, default=0)
    pos_aml = Column(Integer, default=0)
    pos_amc = Column(Integer, default=0)
    pos_amr = Column(Integer, default=0)
    pos_st = Column(Integer, default=0)

    height = Column(Integer, default=0)
    weight = Column(Integer, default=0)
    left_foot = Column(Integer, default=0)
    right_foot = Column(Integer, default=0)
    radar_defense = Column(Float, default=0.0)
    radar_physical = Column(Float, default=0.0)
    radar_speed = Column(Float, default=0.0)
    radar_creativity = Column(Float, default=0.0)
    radar_attack = Column(Float, default=0.0)
    radar_technical = Column(Float, default=0.0)
    radar_aerial = Column(Float, default=0.0)
    radar_mental = Column(Float, default=0.0)
    radar_gk_shot_stopping = Column(Float, default=0.0)
    radar_gk_physical = Column(Float, default=0.0)
    radar_gk_speed = Column(Float, default=0.0)
    radar_gk_mental = Column(Float, default=0.0)
    radar_gk_command = Column(Float, default=0.0)
    radar_gk_eccentricity = Column(Float, default=0.0)
    radar_gk_aerial = Column(Float, default=0.0)
    radar_gk_kicking = Column(Float, default=0.0)
    birth_date = Column(String)
    national_caps = Column(Integer, default=0)
    national_goals = Column(Integer, default=0)
    player_habits = Column(String)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)


class TransferLog(Base):
    __tablename__ = "transfer_logs"
    __table_args__ = (CheckConstraint(transfer_operation_check_sql(), name="ck_transfer_logs_operation"),)

    id = Column(Integer, primary_key=True, index=True)
    player_uid = Column(Integer, index=True)
    player_name = Column(String)
    from_team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    from_team = Column(String)
    to_team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    to_team = Column(String)
    operation = Column(String, index=True, nullable=False)
    ca_change = Column(Integer, default=0)
    pa_change = Column(Integer, default=0)
    age_change = Column(Integer, default=0)
    operator = Column(String)
    created_at = Column(DateTime, index=True)
    notes = Column(String)


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    username = Column(String, index=True)
    created_at = Column(DateTime)
    expires_at = Column(DateTime, index=True)


class OperationAudit(Base):
    __tablename__ = "operation_audits"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, index=True, nullable=False)
    action = Column(String, index=True, nullable=False)
    status = Column(String, index=True, nullable=False)
    source = Column(String, index=True, nullable=False, default="system")
    operator = Column(String, index=True)
    summary = Column(String, nullable=False)
    details_json = Column(Text)
    created_at = Column(DateTime, index=True)

    @property
    def details(self) -> dict:
        if not self.details_json:
            return {}
        try:
            payload = json.loads(self.details_json)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}
