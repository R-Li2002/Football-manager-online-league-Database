import json
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint

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


class SiteNote(Base):
    __tablename__ = "site_notes"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True, nullable=False)
    text = Column(Text, nullable=False, default="")
    round_no = Column(Integer)
    updated_by = Column(String)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class HomePromotion(Base):
    __tablename__ = "home_promotions"
    __table_args__ = (
        UniqueConstraint("source_type", "source_key", name="uq_home_promotions_source"),
    )

    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String, index=True, nullable=False, default="announcement")
    theme = Column(String, nullable=False, default="violet")
    icon = Column(String, nullable=False, default="megaphone")
    eyebrow = Column(String, nullable=False, default="HEIGO Broadcast")
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False, default="")
    image_url = Column(String)
    action_label = Column(String)
    action_kind = Column(String, nullable=False, default="none")
    action_target = Column(String)
    display_mode = Column(String, nullable=False, default="board", server_default="board")
    is_active = Column(Integer, index=True, nullable=False, default=1)
    is_pinned = Column(Integer, index=True, nullable=False, default=0)
    is_dismissible = Column(Integer, nullable=False, default=1)
    sort_order = Column(Integer, index=True, nullable=False, default=100)
    starts_at = Column(DateTime, index=True)
    ends_at = Column(DateTime, index=True)
    source_type = Column(String, index=True, nullable=False, default="custom")
    source_key = Column(String, index=True)
    created_by = Column(String)
    updated_by = Column(String)
    created_at = Column(DateTime, index=True, default=datetime.now)
    updated_at = Column(DateTime, index=True, default=datetime.now, onupdate=datetime.now)


class DailyReportNarrativeTemplate(Base):
    __tablename__ = "daily_report_narrative_templates"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    template_text = Column(Text, nullable=False)
    is_active = Column(Integer, index=True, nullable=False, default=1)
    sort_order = Column(Integer, index=True, nullable=False, default=100)
    created_by = Column(String)
    updated_by = Column(String)
    created_at = Column(DateTime, index=True, default=datetime.now)
    updated_at = Column(DateTime, index=True, default=datetime.now, onupdate=datetime.now)


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(String(10), unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False, default="")
    payload_json = Column(Text, nullable=False, default="{}")
    status = Column(String, index=True, nullable=False, default="draft")
    fingerprint = Column(String, index=True, nullable=False)
    generated_at = Column(DateTime, index=True, default=datetime.now)
    published_at = Column(DateTime, index=True)
    published_by = Column(String)
    created_by = Column(String)
    updated_by = Column(String)
    created_at = Column(DateTime, index=True, default=datetime.now)
    updated_at = Column(DateTime, index=True, default=datetime.now, onupdate=datetime.now)


class SiteVisitStat(Base):
    __tablename__ = "site_visit_stats"

    visit_date = Column(String(10), primary_key=True)
    visit_count = Column(Integer, nullable=False, default=0)


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    manager = Column(String)
    level = Column(String)
    logo_path = Column(String)
    wage = Column(Float)
    team_size = Column(Integer, default=0)
    gk_count = Column(Integer, default=0)
    extra_wage = Column(Float, default=0)
    wage_cap = Column(Float, nullable=True)
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


class TeamLogoSource(Base):
    __tablename__ = "team_logo_sources"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False)
    provider = Column(String, index=True, nullable=False, default="fclogo")
    source_url = Column(String, nullable=False)
    source_name = Column(String)
    source_version = Column(String)
    source_variant = Column(String)
    svg_path = Column(String, nullable=False)
    webp_path = Column(String, nullable=False)
    sha256 = Column(String, index=True, nullable=False)
    matched_query = Column(String)
    matched_score = Column(Float)
    imported_by = Column(String)
    imported_at = Column(DateTime, index=True, default=datetime.now)


class TeamLineup(Base):
    __tablename__ = "team_lineups"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    formation = Column(String, nullable=False, default="4-3-3")
    picks_json = Column(Text, nullable=False, default="{}")
    updated_by = Column(String)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


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


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    season_label = Column(String, index=True)
    level = Column(String, index=True, nullable=False)
    round_no = Column(Integer, index=True, nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    home_team_name = Column(String, index=True, nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    away_team_name = Column(String, index=True, nullable=False)
    home_score = Column(Integer)
    away_score = Column(Integer)
    status = Column(String, index=True, nullable=False, default="scheduled")
    match_date = Column(DateTime)
    notes = Column(Text)
    source_file = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class MatchPlayerEvent(Base):
    __tablename__ = "match_player_events"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    team_name = Column(String, index=True, nullable=False)
    player_uid = Column(Integer, ForeignKey("players.uid", ondelete="SET NULL"), index=True)
    player_name = Column(String, index=True, nullable=False)
    event_type = Column(String, index=True, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CompetitionRoundWorkState(Base):
    __tablename__ = "competition_round_work_states"
    __table_args__ = (
        UniqueConstraint("level", "round_start", name="uq_competition_round_work_level_start"),
    )

    id = Column(Integer, primary_key=True)
    level = Column(String, index=True, nullable=False)
    round_start = Column(Integer, index=True, nullable=False)
    round_end = Column(Integer, nullable=False)
    assignee_principal_id = Column(String, index=True)
    assignee_display_name = Column(String)
    assigned_at = Column(DateTime)
    assigned_by = Column(String, index=True)
    suspension_confirmed_at = Column(DateTime)
    suspension_confirmed_by = Column(String, index=True)
    submitted_at = Column(DateTime)
    submitted_by = Column(String, index=True)
    completed_at = Column(DateTime)
    completed_by = Column(String, index=True)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CompetitionRoundWorkLog(Base):
    __tablename__ = "competition_round_work_logs"

    id = Column(Integer, primary_key=True)
    state_id = Column(Integer, ForeignKey("competition_round_work_states.id", ondelete="CASCADE"), index=True, nullable=False)
    level = Column(String, index=True, nullable=False)
    round_start = Column(Integer, index=True, nullable=False)
    action = Column(String, index=True, nullable=False)
    operator_principal_id = Column(String, index=True, nullable=False)
    operator_display_name = Column(String, nullable=False)
    from_status = Column(String)
    to_status = Column(String)
    detail = Column(Text)
    created_at = Column(DateTime, default=datetime.now, index=True)


class CompetitionResponsibilityAssignment(Base):
    __tablename__ = "competition_responsibility_assignments"
    __table_args__ = (
        UniqueConstraint("level", "responsibility_type", name="uq_competition_responsibility_level_type"),
    )

    id = Column(Integer, primary_key=True)
    level = Column(String, index=True, nullable=False)
    responsibility_type = Column(String, index=True, nullable=False)
    principal_id = Column(String, index=True, nullable=False)
    display_name = Column(String, nullable=False)
    assigned_by = Column(String, index=True, nullable=False)
    assigned_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CupMatch(Base):
    __tablename__ = "cup_matches"

    id = Column(Integer, primary_key=True, index=True)
    competition = Column(String, index=True, nullable=False)
    stage = Column(String, index=True, nullable=False)
    slot_no = Column(Integer, index=True, nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    home_team_name = Column(String)
    away_team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    away_team_name = Column(String)
    home_score = Column(Integer)
    away_score = Column(Integer)
    winner_team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    winner_team_name = Column(String)
    status = Column(String, index=True, nullable=False, default="scheduled")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class WumingjianQualificationTeam(Base):
    __tablename__ = "wumingjian_qualification_teams"
    __table_args__ = (
        UniqueConstraint("team_id", name="uq_wumingjian_qualification_team"),
    )

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False)
    team_name = Column(String, nullable=False)
    manager = Column(String)
    level = Column(String, index=True, nullable=False)
    source_rank = Column(Integer, nullable=False)
    qualification_type = Column(String, index=True, nullable=False)
    locked_at = Column(DateTime, default=datetime.now, nullable=False)


class SeasonArchive(Base):
    __tablename__ = "season_archives"
    __table_args__ = (
        UniqueConstraint("season_key", "revision_no", name="uq_season_archives_key_revision"),
    )

    id = Column(Integer, primary_key=True, index=True)
    season_key = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    revision_no = Column(Integer, nullable=False, default=1)
    parent_archive_id = Column(Integer, ForeignKey("season_archives.id", ondelete="SET NULL"), index=True)
    status = Column(String, index=True, nullable=False, default="draft")
    snapshot_json = Column(Text, nullable=False, default="{}")
    validation_json = Column(Text, nullable=False, default="{}")
    revision_reason = Column(Text)
    created_by = Column(String, index=True)
    confirmed_by = Column(String, index=True)
    created_at = Column(DateTime, index=True, default=datetime.now)
    confirmed_at = Column(DateTime, index=True)


class DrawSession(Base):
    __tablename__ = "draw_sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    draw_type = Column(String, index=True, nullable=False)
    competition = Column(String, index=True)
    season_label = Column(String, index=True)
    status = Column(String, index=True, nullable=False, default="draft")
    random_seed = Column(String, nullable=False)
    pool_hash = Column(String, index=True)
    config_json = Column(Text, nullable=False, default="{}")
    result_json = Column(Text, nullable=False, default="{}")
    candidate_list_id = Column(Integer, ForeignKey("candidate_lists.id", ondelete="SET NULL"), index=True)
    created_by = Column(String, index=True)
    updated_by = Column(String, index=True)
    locked_by = Column(String, index=True)
    completed_by = Column(String, index=True)
    published_by = Column(String, index=True)
    voided_by = Column(String, index=True)
    created_at = Column(DateTime, index=True, default=datetime.now)
    updated_at = Column(DateTime, index=True, default=datetime.now, onupdate=datetime.now)
    locked_at = Column(DateTime, index=True)
    completed_at = Column(DateTime, index=True)
    published_at = Column(DateTime, index=True)
    voided_at = Column(DateTime, index=True)
    void_reason = Column(Text)


class DrawPoolEntry(Base):
    __tablename__ = "draw_pool_entries"
    __table_args__ = (
        UniqueConstraint("session_id", "entity_key", name="uq_draw_pool_entries_session_entity"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("draw_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    entity_key = Column(String, nullable=False)
    entity_type = Column(String, index=True, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    player_uid = Column(Integer, ForeignKey("players.uid", ondelete="SET NULL"), index=True)
    entity_name = Column(String, nullable=False)
    team_name = Column(String, index=True)
    level = Column(String, index=True)
    source_rank = Column(Integer)
    pot_no = Column(Integer, index=True)
    seed_status = Column(String, index=True)
    self_save_count = Column(Integer, nullable=False, default=0)
    weight = Column(Float, nullable=False, default=1.0)
    final_value = Column(Float)
    slot_type = Column(String)
    is_active = Column(Integer, index=True, nullable=False, default=1)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DrawPick(Base):
    __tablename__ = "draw_picks"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence_no", name="uq_draw_picks_session_sequence"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("draw_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    sequence_no = Column(Integer, nullable=False)
    entry_id = Column(Integer, ForeignKey("draw_pool_entries.id", ondelete="CASCADE"), index=True, nullable=False)
    paired_entry_id = Column(Integer, ForeignKey("draw_pool_entries.id", ondelete="SET NULL"), index=True)
    target_group = Column(String, index=True)
    target_slot = Column(Integer)
    random_value = Column(String)
    status = Column(String, index=True, nullable=False, default="active")
    reason = Column(Text)
    created_by = Column(String, index=True)
    created_at = Column(DateTime, index=True, default=datetime.now)
    invalidated_by = Column(String, index=True)
    invalidated_at = Column(DateTime, index=True)


class CupGroupTeam(Base):
    __tablename__ = "cup_group_teams"
    __table_args__ = (
        UniqueConstraint("competition", "group_no", "slot_no", name="uq_cup_group_teams_competition_group_slot"),
        UniqueConstraint("competition", "team_id", name="uq_cup_group_teams_competition_team"),
    )

    id = Column(Integer, primary_key=True, index=True)
    competition = Column(String, index=True, nullable=False)
    group_no = Column(Integer, index=True, nullable=False)
    slot_no = Column(Integer, index=True, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False)
    team_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class RankingSeed(Base):
    __tablename__ = "ranking_seeds"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    team_name = Column(String, nullable=False)
    base_points = Column(Float, nullable=False, default=1000.0)
    matches = Column(Integer, nullable=False, default=0)
    wins = Column(Integer, nullable=False, default=0)
    draws = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)
    source_name = Column(String)
    source_row = Column(Integer)
    imported_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class RankingMatch(Base):
    __tablename__ = "ranking_matches"
    __table_args__ = (
        CheckConstraint("home_score >= 0", name="ck_ranking_matches_home_score_non_negative"),
        CheckConstraint("away_score >= 0", name="ck_ranking_matches_away_score_non_negative"),
        CheckConstraint("home_team_id != away_team_id", name="ck_ranking_matches_distinct_teams"),
    )

    id = Column(Integer, primary_key=True, index=True)
    home_team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    home_team_name = Column(String, nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    away_team_name = Column(String, nullable=False)
    home_score = Column(Integer, nullable=False)
    away_score = Column(Integer, nullable=False)
    created_by = Column(String)
    played_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class PlayerCompetitionStat(Base):
    __tablename__ = "player_competition_stats"

    id = Column(Integer, primary_key=True, index=True)
    player_uid = Column(Integer, ForeignKey("players.uid", ondelete="SET NULL"), index=True)
    player_name = Column(String, index=True, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    team_name = Column(String, index=True, nullable=False)
    level = Column(String, index=True, nullable=False)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    appearances = Column(Integer, default=0)
    notes = Column(Text)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PlayerSuspensionRecord(Base):
    __tablename__ = "player_suspension_records"

    id = Column(Integer, primary_key=True, index=True)
    player_uid = Column(Integer, ForeignKey("players.uid", ondelete="CASCADE"), index=True, unique=True, nullable=False)
    player_name = Column(String, index=True, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    team_name = Column(String, index=True, nullable=False)
    level = Column(String, index=True, nullable=False)
    yellow_cards = Column(Integer, default=0)
    red_card_suspended = Column(Integer, default=0)
    red_injury_suspended = Column(Integer, default=0)
    notes = Column(Text)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CandidateList(Base):
    __tablename__ = "candidate_lists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    type = Column(String, index=True, nullable=False, default="custom")
    status = Column(String, index=True, nullable=False, default="draft")
    base_data_version = Column(String, index=True)
    source_filters_json = Column(Text)
    created_by = Column(String, index=True)
    updated_by = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    published_at = Column(DateTime, index=True)
    published_by = Column(String, index=True)
    archived_at = Column(DateTime, index=True)
    archived_by = Column(String, index=True)
    locked_at = Column(DateTime, index=True)
    locked_by = Column(String, index=True)
    published_player_count = Column(Integer, default=0)
    last_published_snapshot_json = Column(Text)


class CandidateListPlayer(Base):
    __tablename__ = "candidate_list_players"

    id = Column(Integer, primary_key=True, index=True)
    list_id = Column(Integer, ForeignKey("candidate_lists.id", ondelete="CASCADE"), index=True, nullable=False)
    uid = Column(Integer, index=True, nullable=False)
    data_version = Column(String, index=True, nullable=False)
    name_snapshot = Column(String)
    club_snapshot = Column(String)
    heigo_club_snapshot = Column(String)
    ca_snapshot = Column(Integer)
    pa_snapshot = Column(Integer)
    added_by = Column(String, index=True)
    added_at = Column(DateTime, default=datetime.now)
    removed_at = Column(DateTime, index=True)
    removed_by = Column(String, index=True)


class Coach(Base):
    __tablename__ = "coaches"

    uid = Column(String, primary_key=True, index=True)
    nickname = Column(String, index=True, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    team_name = Column(String, index=True)
    level = Column(String, index=True)
    avatar_path = Column(String)
    title = Column(String)
    title_color = Column(String, default="white")
    bio = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CoachHonor(Base):
    __tablename__ = "coach_honors"

    id = Column(Integer, primary_key=True, index=True)
    coach_uid = Column(String, ForeignKey("coaches.uid", ondelete="CASCADE"), index=True, nullable=False)
    edition = Column(Integer)
    season = Column(String)
    competition = Column(String)
    placement = Column(String)
    honor = Column(String, nullable=False)
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CoachAssistant(Base):
    __tablename__ = "coach_assistants"

    id = Column(Integer, primary_key=True, index=True)
    coach_uid = Column(String, ForeignKey("coaches.uid", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String, nullable=False)
    level = Column(String, nullable=False)
    note = Column(Text)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CoachAccount(Base):
    __tablename__ = "coach_accounts"

    id = Column(Integer, primary_key=True, index=True)
    coach_uid = Column(String, ForeignKey("coaches.uid", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    qq_number = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Integer, nullable=False, default=1)
    must_change_password = Column(Integer, nullable=False, default=1)
    can_manage_schedule = Column(Integer, nullable=False, default=0)
    can_manage_cup_standings = Column(Integer, nullable=False, default=0)
    can_manage_rankings = Column(Integer, nullable=False, default=0)
    can_manage_suspensions = Column(Integer, nullable=False, default=0)
    can_manage_candidate_lists = Column(Integer, nullable=False, default=0)
    can_manage_daily_reports = Column(Integer, nullable=False, default=0)
    can_manage_draws = Column(Integer, nullable=False, default=0)
    can_manage_archives = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_login_at = Column(DateTime)


class CoachSession(Base):
    __tablename__ = "coach_sessions"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    coach_uid = Column(String, ForeignKey("coaches.uid", ondelete="CASCADE"), index=True, nullable=False)
    username = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, index=True, nullable=False)


class CoachReactionSummary(Base):
    __tablename__ = "coach_reaction_summaries"
    __table_args__ = (
        CheckConstraint("flowers >= 0", name="ck_coach_reaction_summaries_flowers_non_negative"),
        CheckConstraint("eggs >= 0", name="ck_coach_reaction_summaries_eggs_non_negative"),
    )

    coach_uid = Column(String, ForeignKey("coaches.uid", ondelete="CASCADE"), primary_key=True, index=True)
    flowers = Column(Integer, nullable=False, default=0)
    eggs = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, index=True)


class CoachReactionEvent(Base):
    __tablename__ = "coach_reaction_events"
    __table_args__ = (
        CheckConstraint("reaction_type IN ('flower', 'egg')", name="ck_coach_reaction_events_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    coach_uid = Column(String, ForeignKey("coaches.uid", ondelete="CASCADE"), index=True, nullable=False)
    visitor_token = Column(String, index=True, nullable=False)
    reaction_type = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, index=True, nullable=False)


class PlayerAttributeColumns:
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
    player_habits_raw_code = Column(String)
    player_habits_high_bits = Column(String)


class PlayerAttribute(PlayerAttributeColumns, Base):
    __tablename__ = "player_attributes"


class PlayerAttributeVersion(PlayerAttributeColumns, Base):
    __tablename__ = "player_attribute_versions"

    uid = Column(Integer, primary_key=True, index=True)
    data_version = Column(String, primary_key=True, index=True, nullable=False)


class PlayerReactionSummary(Base):
    __tablename__ = "player_reaction_summaries"
    __table_args__ = (
        CheckConstraint("flowers >= 0", name="ck_player_reaction_summaries_flowers_non_negative"),
        CheckConstraint("eggs >= 0", name="ck_player_reaction_summaries_eggs_non_negative"),
    )

    player_uid = Column(Integer, ForeignKey("player_attributes.uid", ondelete="CASCADE"), primary_key=True, index=True)
    flowers = Column(Integer, nullable=False, default=0)
    eggs = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, index=True)


class PlayerReactionEvent(Base):
    __tablename__ = "player_reaction_events"
    __table_args__ = (
        CheckConstraint("reaction_type IN ('flower', 'egg')", name="ck_player_reaction_events_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    player_uid = Column(Integer, ForeignKey("player_attributes.uid", ondelete="CASCADE"), index=True, nullable=False)
    visitor_token = Column(String, index=True, nullable=False)
    reaction_type = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, index=True, nullable=False)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, index=True, nullable=False, default="admin")


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


class DataFeedbackReport(Base):
    __tablename__ = "data_feedback_reports"

    id = Column(Integer, primary_key=True, index=True)
    player_uid = Column(Integer, index=True)
    player_name = Column(String, index=True)
    issue_type = Column(String, index=True, nullable=False)
    summary = Column(String, nullable=False)
    details = Column(Text, nullable=False)
    suggested_correction = Column(Text)
    contact = Column(String)
    source_page = Column(String)
    status = Column(String, index=True, nullable=False, default="open")
    created_at = Column(DateTime, index=True)
