"""EcoFin monetisation: where the platform earns, computed from real rows.

Route savings alone do not fund the platform. One skipped stop is worth
379 KZT, a pilot container generates roughly 2 200 KZT of savings per month,
and a subscription that stayed below that number can only ever be a fraction
of a small figure. That is not a flaw in the pricing — it is the reason the
business model has to stand on several legs at once.

Five legs are modelled here, and every one of them is derived from something
already stored: container devices, write-off records, the CO2 the savings
engine computed, and residents who actually earned points. Nothing is a round
number typed in to make a slide look better.

The projection to city scale is kept strictly separate from the pilot figure
and repeats the assumptions it rests on, because a projection presented as a
measurement is the fastest way to lose a technical defence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CostProfile, PointTransaction, User, WriteOffRecord
from app.schemas import (
    RevenueModel,
    RevenueScenario,
    RevenueStream,
    SavingsReport,
)
from app.services.eco_savings import DAYS_PER_MONTH


KG_PER_TON = 1000.0

# Порог, ниже которого углеродные единицы не стоит и упоминать: доход с них
# меньше стоимости оформления verification-отчёта.
CARBON_MEANINGFUL_KZT_PER_MONTH = 50_000.0


def _kzt(value: float) -> str:
    """Тысячи разделяются пробелом.

    Форматировать число отдельно, а не заменять запятые во всей строке:
    иначе замена съедает запятые самого предложения.
    """

    return f"{value:,.0f}".replace(",", " ")


def _plural(count: int, one: str, few: str, many: str) -> str:
    """«1 бак», «2 бака», «5 баков» — иначе подпись выдаёт машинный текст."""

    tail_two = abs(count) % 100
    tail_one = abs(count) % 10
    if 11 <= tail_two <= 14:
        return many
    if tail_one == 1:
        return one
    if 2 <= tail_one <= 4:
        return few
    return many


@dataclass(frozen=True, slots=True)
class RevenueBasis:
    """Measured counts the revenue model multiplies its tariffs by."""

    containers: int
    businesses: int
    active_residents: int
    co2_tons_per_month: float
    business_write_off_kzt_per_month: float


def _count_businesses(db: Session) -> int:
    """How many organisations actually keep a write-off journal.

    A cabinet nobody fills in is not a paying customer, so the count comes
    from journals that have rows rather than from profiles that exist.
    """

    return int(
        db.scalar(select(func.count(func.distinct(WriteOffRecord.profile_id)))) or 0
    )


def _count_active_residents(
    db: Session, period_start: datetime, period_end: datetime
) -> int:
    """Residents who earned or spent points during the period.

    Registration alone is not activity — a sponsor pays for people who open
    the app, not for rows in the users table.
    """

    return int(
        db.scalar(
            select(func.count(func.distinct(PointTransaction.user_id)))
            .join(User, User.id == PointTransaction.user_id)
            .where(
                PointTransaction.created_at >= period_start,
                PointTransaction.created_at <= period_end,
                User.role == "user",
            )
        )
        or 0
    )


def _write_off_value_per_month(
    db: Session, profile: CostProfile, days: float
) -> float:
    """Money the business loses on unsold product, normalised to a month.

    This is the size of the problem the bakery cabinet works on, and the only
    honest yardstick for pricing that cabinet.
    """

    if days <= 0:
        return 0.0
    total = (
        db.scalar(
            select(
                func.sum(WriteOffRecord.kg_written_off * WriteOffRecord.cost_kzt_per_kg)
            ).where(WriteOffRecord.profile_id == profile.id)
        )
        or 0.0
    )
    return float(total) / days * DAYS_PER_MONTH


def collect_basis(
    db: Session,
    profile: CostProfile,
    report: SavingsReport,
    period_start: datetime,
    period_end: datetime,
) -> RevenueBasis:
    """Measure everything the tariffs will be multiplied by."""

    days = max((period_end - period_start).total_seconds() / 86_400.0, 0.0)
    co2_per_month = (
        report.resources.co2_kg_saved / days * DAYS_PER_MONTH / KG_PER_TON
        if days > 0
        else 0.0
    )
    return RevenueBasis(
        containers=report.containers,
        businesses=_count_businesses(db),
        active_residents=_count_active_residents(db, period_start, period_end),
        co2_tons_per_month=co2_per_month,
        business_write_off_kzt_per_month=_write_off_value_per_month(db, profile, days),
    )


def _streams(profile: CostProfile, basis: RevenueBasis) -> list[RevenueStream]:
    """The five revenue legs, each with the arithmetic that produced it."""

    saas = profile.subscription_kzt_per_month * basis.containers
    business = profile.business_subscription_kzt_per_month * basis.businesses
    carbon = profile.carbon_price_kzt_per_ton * basis.co2_tons_per_month
    sponsor = profile.sponsor_kzt_per_active_resident * basis.active_residents
    hardware_margin = (
        profile.install_price_kzt - profile.hardware_cost_kzt
    ) * basis.containers

    # Тариф пекарни имеет смысл только как доля предотвращённого убытка.
    if basis.business_write_off_kzt_per_month > 0:
        break_even = (
            profile.business_subscription_kzt_per_month
            / basis.business_write_off_kzt_per_month
            * 100.0
        )
        business_note = (
            f"Средняя пекарня списывает {_kzt(basis.business_write_off_kzt_per_month)} ₸ "
            f"в месяц. Тариф окупается, если прогноз сократит списания хотя бы "
            f"на {break_even:.1f}% — ниже этого порога брать деньги не за что."
        )
    else:
        business_note = (
            "Журнал списаний пуст, поэтому предотвращённый убыток посчитать не на "
            "чем — тариф показан как потенциальный."
        )

    carbon_note = (
        "Собственная система торговли квотами в Казахстане, цена на порядок ниже "
        "европейской. Поток становится заметен только там, где тонны идут "
        "сотнями."
    )
    if carbon > 0 and carbon < CARBON_MEANINGFUL_KZT_PER_MONTH:
        carbon_note += (
            f" Сейчас {_kzt(carbon)} ₸ в месяц — меньше стоимости верификации."
        )

    return [
        RevenueStream(
            key="operator_saas",
            title="Подписка коммунального оператора",
            monthly_kzt=round(saas, 2),
            basis=f"{basis.containers} "
            f"{_plural(basis.containers, 'бак', 'бака', 'баков')} × "
            f"{_kzt(profile.subscription_kzt_per_month)} ₸",
            note="Основной поток. Тариф удерживается ниже создаваемой экономии, "
            "иначе оператору невыгодно оставаться клиентом.",
            is_recurring=True,
        ),
        RevenueStream(
            key="business_saas",
            title="Кабинет пекарни и столовой",
            monthly_kzt=round(business, 2),
            basis=f"{basis.businesses} "
            f"{_plural(basis.businesses, 'организация', 'организации', 'организаций')}"
            f" × {_kzt(profile.business_subscription_kzt_per_month)} ₸",
            note=business_note,
            is_recurring=True,
        ),
        RevenueStream(
            key="sponsored_rewards",
            title="Спонсорские награды в эко-магазине",
            monthly_kzt=round(sponsor, 2),
            basis=f"{basis.active_residents} активных "
            f"{_plural(basis.active_residents, 'житель', 'жителя', 'жителей')} × "
            f"{_kzt(profile.sponsor_kzt_per_active_resident)} ₸",
            note="Бренд платит за место в витрине наград. Считаем только тех, кто "
            "за период реально начислял или тратил баллы, а не всех "
            "зарегистрированных.",
            is_recurring=True,
        ),
        RevenueStream(
            key="carbon_credits",
            title="Углеродные единицы",
            monthly_kzt=round(carbon, 2),
            basis=f"{basis.co2_tons_per_month:.3f} т CO₂ × "
            f"{_kzt(profile.carbon_price_kzt_per_ton)} ₸",
            note=carbon_note,
            is_recurring=True,
        ),
        RevenueStream(
            key="hardware_margin",
            title="Маржа на оборудовании",
            monthly_kzt=round(hardware_margin, 2),
            basis=f"{basis.containers} "
            f"{_plural(basis.containers, 'бак', 'бака', 'баков')} × "
            f"({_kzt(profile.install_price_kzt)} − "
            f"{_kzt(profile.hardware_cost_kzt)}) ₸",
            note="Разовый доход при монтаже, а не ежемесячный. Показан отдельно и "
            "не входит в сумму регулярной выручки.",
            is_recurring=False,
        ),
    ]


def _scenario(title: str, streams: list[RevenueStream], containers: int) -> RevenueScenario:
    recurring = sum(s.monthly_kzt for s in streams if s.is_recurring)
    one_time = sum(s.monthly_kzt for s in streams if not s.is_recurring)
    return RevenueScenario(
        title=title,
        containers=containers,
        streams=streams,
        monthly_recurring_kzt=round(recurring, 2),
        one_time_kzt=round(one_time, 2),
        annual_recurring_kzt=round(recurring * 12.0, 2),
    )


def build_revenue_model(
    db: Session,
    profile: CostProfile,
    report: SavingsReport,
    period_start: datetime,
    period_end: datetime,
    projection_containers: int | None = None,
) -> RevenueModel:
    """Revenue the pilot tariff would produce, plus an optional city-scale projection.

    Nothing here is money received. The pilot figure is the tariff applied to
    the containers actually installed and the savings actually measured — an
    honest unit economics calculation, not booked revenue, because the pilot
    has no paying customers yet. Calling it a fact on screen would be a lie
    the jury is entitled to catch.

    The projection scales only what genuinely scales with the number of
    containers: subscriptions, hardware and CO2. Businesses and residents are
    scaled by the same factor, which is an assumption and is labelled as one —
    a bakery does not appear because a container was installed.
    """

    basis = collect_basis(db, profile, report, period_start, period_end)
    pilot = _scenario(
        "Пилот, расчёт по тарифу", _streams(profile, basis), basis.containers
    )

    projection: RevenueScenario | None = None
    if projection_containers and basis.containers > 0:
        factor = projection_containers / basis.containers
        scaled = RevenueBasis(
            containers=projection_containers,
            businesses=max(1, round(basis.businesses * factor)),
            active_residents=round(basis.active_residents * factor),
            co2_tons_per_month=basis.co2_tons_per_month * factor,
            business_write_off_kzt_per_month=basis.business_write_off_kzt_per_month,
        )
        projection = _scenario(
            f"Проекция на {projection_containers} баков",
            _streams(profile, scaled),
            projection_containers,
        )

    return RevenueModel(
        generated_at=report.generated_at,
        period_start=period_start,
        period_end=period_end,
        currency="KZT",
        pilot=pilot,
        projection=projection,
        assumptions=[
            "Подписка оператора удерживается ниже создаваемой экономии, иначе "
            "клиент теряет деньги на платформе.",
            "Тариф кабинета оправдан только тем убытком, который прогноз "
            "предотвращает; порог окупаемости указан рядом с потоком.",
            "Спонсорские награды считаются по активным жителям за период, а не "
            "по числу регистраций.",
            "Проекция масштабирует организации и жителей пропорционально бакам. "
            "Это допущение, а не измерение: пекарня не появляется оттого, что "
            "установили контейнер.",
        ],
    )
