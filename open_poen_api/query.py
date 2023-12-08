from . import models as ent
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import select, or_, literal, and_
from .exc import UnprocessableContent
from datetime import datetime, date, timedelta
from .schemas import TransactionAmount
from sqlalchemy import func, case


class RequestingUser:
    def __init__(self, user: ent.User):
        self.user = user

    @property
    def initiative_ids(self):
        return [i.initiative_id for i in self.user.initiative_roles]

    @property
    def activity_ids(self):
        return [i.activity_id for i in self.user.activity_roles]

    @property
    def grant_ids(self):
        return [i.grant_id for i in self.user.overseer_roles]

    @property
    def go_regulation_ids(self):
        return [i.regulation_id for i in self.user.grant_officer_regulation_roles]

    @property
    def po_regulation_ids(self):
        return [i.regulation_id for i in self.user.policy_officer_regulation_roles]

    @property
    def is_officer(self):
        return (
            len(self.user.grant_officer_regulation_roles) > 0
            or len(self.user.policy_officer_regulation_roles) > 0
        )

    @property
    def is_administrator(self):
        return self.user.role == ent.UserRole.ADMINISTRATOR

    @property
    def is_superuser(self):
        return self.user.is_superuser

    @property
    def id(self):
        return self.user.id

    @property
    def used_and_owned_bank_accounts(self):
        return [
            i.bank_account_id
            for i in self.user.user_bank_account_roles
            + self.user.owner_bank_account_roles
        ]


def get_users_q(
    optional_user: ent.User | None, email: str | None, offset: int, limit: int
):
    q = select(ent.User).options(joinedload(ent.User.profile_picture))

    if optional_user is not None:
        requesting_user = RequestingUser(optional_user)

    if optional_user is None:
        q = q.where(ent.User.hidden == False)
    else:
        q = q.where(
            or_(
                ent.User.hidden == False,
                ent.User.id == requesting_user.id,
                literal(requesting_user.is_administrator),
                literal(requesting_user.is_superuser),
            )
        )

    if email:
        q = q.where(ent.User.email.ilike(f"%{email}%"))

    q = q.order_by(ent.User.id.desc()).offset(offset).limit(limit)

    return q


def get_initiatives_q(
    optional_user: ent.User | None,
    name: str | None,
    only_mine: bool,
    offset: int,
    limit: int,
):
    q = select(ent.Initiative).join(ent.Grant).join(ent.Regulation)

    if optional_user is not None:
        requesting_user = RequestingUser(optional_user)

    if optional_user is None:
        q = q.where(ent.Initiative.hidden == False)
    else:
        q = q.where(
            or_(
                ent.Initiative.hidden == False,
                # You can see initiatives of your activities.
                ent.Initiative.id.in_(
                    select(ent.Activity.initiative_id).where(
                        ent.Activity.id.in_(requesting_user.activity_ids)
                    )
                ),
                # You can see your own initiatives.
                ent.Initiative.id.in_(requesting_user.initiative_ids),
                # You can see initiatives where you're overseer.
                ent.Initiative.id.in_(
                    select(ent.Initiative.id)
                    .join(ent.Grant)
                    .where(ent.Grant.id.in_(requesting_user.grant_ids))
                ),
                # You can see initiatives in your regulation as an officer.
                ent.Regulation.id.in_(requesting_user.go_regulation_ids),
                ent.Regulation.id.in_(requesting_user.po_regulation_ids),
                # Administrators or super users can see everything.
                literal(requesting_user.is_administrator),
                literal(requesting_user.is_superuser),
            )
        )

    if only_mine and optional_user is None:
        raise UnprocessableContent(
            message="only_mine can only be set to True if the user is logged in"
        )
    elif only_mine and optional_user is not None:
        q = q.where(
            or_(
                # You can see initiatives of your activities.
                ent.Initiative.id.in_(
                    select(ent.Activity.initiative_id).where(
                        ent.Activity.id.in_(requesting_user.activity_ids)
                    )
                ),
                # You can see your own initiatives.
                ent.Initiative.id.in_(requesting_user.initiative_ids),
            )
        )
    else:
        pass

    if name:
        q = q.where(ent.Initiative.name.ilike(f"%{name}%"))

    q = q.order_by(ent.Initiative.id.desc()).offset(offset).limit(limit)

    return q


def get_funders_q(name: str | None, offset: int, limit: int):
    q = select(ent.Funder)

    if name:
        q = q.where(ent.Funder.name.ilike(f"%{name}%"))

    q = q.order_by(ent.Funder.id.desc()).offset(offset).limit(limit)

    return q


def get_regulations_q(funder_id: int, name: str | None, offset: int, limit: int):
    q = select(ent.Regulation).where(ent.Regulation.funder_id == funder_id)

    if name:
        q = q.where(ent.Regulation.name.ilike(f"%{name}%"))

    q = q.order_by(ent.Regulation.id.desc()).offset(offset).limit(limit)

    return q


def get_grants_q(regulation_id: int, name: str | None, offset: int, limit: int):
    q = select(ent.Grant).where(ent.Grant.regulation_id == regulation_id)

    if name:
        q = q.where(ent.Grant.name.ilike(f"%{name}%"))

    q = q.order_by(ent.Grant.id.desc()).offset(offset).limit(limit)

    return q


def get_user_payments_q(
    user_id: int,
    initiative_name: str | None,
    activity_name: str | None,
    iban: str | None,
    offset: int,
    limit: int,
):
    q = (
        select(
            ent.Payment,
            ent.Payment.id,
            ent.Payment.booking_date,
            ent.Initiative.id.label("initiative_id"),
            ent.Initiative.name.label("initiative_name"),
            ent.Activity.id.label("activity_id"),
            ent.Activity.name.label("activity_name"),
            ent.Payment.creditor_name,
            ent.Payment.short_user_description,
            ent.BankAccount.iban,
            ent.Payment.transaction_amount,
        )
        .join(ent.BankAccount)
        .outerjoin(ent.Initiative, ent.Payment.initiative_id == ent.Initiative.id)
        .outerjoin(ent.Activity, ent.Payment.activity_id == ent.Activity.id)
        .join(
            ent.UserBankAccountRole,
            ent.BankAccount.id == ent.UserBankAccountRole.bank_account_id,
        )
        .join(ent.User)
        .where(ent.User.id == user_id)
    )

    if initiative_name:
        q = q.where(ent.Initiative.name.ilike(f"%{initiative_name}%"))
    if initiative_name:
        q = q.where(ent.Activity.name.ilike(f"%{activity_name}%"))
    if iban:
        q = q.where(ent.BankAccount.iban.ilike(f"%{iban}%"))

    # Distinct because the join condition on UserBankAccountRole can
    # result in double records where a user is both owner and user.
    q = (
        q.order_by(ent.Payment.booking_date.desc())
        .distinct()
        .offset(offset)
        .limit(limit)
    )

    return q


def get_linkable_initiatives_q(required_user: ent.User):
    requesting_user = RequestingUser(required_user)

    q = (
        select(ent.Initiative, ent.Initiative.id, ent.Initiative.name)
        # Necessary for the checking if the user is an activity owner of one
        # of the activities of this initiatives.
        .options(selectinload(ent.Initiative.activities))
        .where(
            or_(
                # Initiatives of your activities.
                ent.Initiative.id.in_(
                    select(ent.Activity.initiative_id).where(
                        ent.Activity.id.in_(requesting_user.activity_ids)
                    )
                ),
                # Your own initiatives.
                ent.Initiative.id.in_(requesting_user.initiative_ids),
                # Initiatives where you are overseer.
                ent.Initiative.id.in_(
                    select(ent.Initiative.id)
                    .join(ent.Grant)
                    .where(ent.Grant.id.in_(requesting_user.grant_ids))
                ),
            )
        )
        .order_by(ent.Initiative.id.desc())
    )

    return q


def get_linkable_activities_q(required_user: ent.User, initiative_id: int):
    requesting_user = RequestingUser(required_user)

    q = (
        select(ent.Activity, ent.Activity.id, ent.Activity.name)
        .where(ent.Activity.initiative_id == initiative_id)
        .order_by(ent.Activity.id.desc())
    )

    return q


def apply_date_range_filter(query, start_date: date | None, end_date: date | None):
    if start_date:
        query = query.where(ent.Payment.booking_date >= start_date)
    if end_date:
        end_date += timedelta(days=1)
        query = query.where(ent.Payment.booking_date <= end_date)
    return query


def apply_amount_range_filter(
    query, min_amount: TransactionAmount | None, max_amount: TransactionAmount | None
):
    if min_amount is not None:
        query = query.where(ent.Payment.transaction_amount >= min_amount)
    if max_amount is not None:
        query = query.where(ent.Payment.transaction_amount <= max_amount)
    return query


def apply_route_filter(query, route: ent.Route | None):
    if route:
        query = query.where(ent.Payment.route == route.value)
    return query


def get_initiative_payments_q(
    optional_user: ent.User | None,
    initiative_id: int,
    offset: int,
    limit: int,
    start_date: date | None,
    end_date: date | None,
    min_amount: TransactionAmount | None,
    max_amount: TransactionAmount | None,
    route: ent.Route | None,
):
    q = (
        select(
            ent.Payment.id,
            ent.Payment.booking_date,
            ent.Activity.name.label("activity_name"),
            ent.Payment.creditor_name,
            ent.Payment.debtor_name,
            ent.Payment.short_user_description,
            ent.Payment.transaction_amount,
            func.count(ent.Attachment.id).label("n_attachments"),
        )
        .join(ent.Initiative, ent.Payment.initiative_id == ent.Initiative.id)
        .join(ent.Grant, ent.Initiative.grant_id == ent.Grant.id)
        .join(ent.Regulation, ent.Grant.regulation_id == ent.Regulation.id)
        .outerjoin(ent.Activity, ent.Payment.activity_id == ent.Activity.id)
        .outerjoin(
            ent.Attachment,
            and_(
                ent.Payment.id == ent.Attachment.entity_id,
                ent.Attachment.entity_type == ent.AttachmentEntityType.PAYMENT.value,
            ),
        )
        .where(ent.Payment.initiative_id == initiative_id)
        .group_by(
            ent.Payment.id,
            ent.Payment.booking_date,
            ent.Activity.name,
            ent.Payment.creditor_name,
            ent.Payment.debtor_name,
            ent.Payment.short_user_description,
            ent.Payment.transaction_amount,
        )
    )

    if optional_user is not None:
        requesting_user = RequestingUser(optional_user)

    if optional_user is None:
        q = q.where(ent.Payment.hidden == False)
    else:
        q = q.where(
            or_(
                ent.Payment.hidden == False,
                # You can see hidden payments if you are initiative owner.
                ent.Payment.initiative_id.in_(requesting_user.initiative_ids),
                # You can see hidden payments if you are activity owner.
                ent.Payment.activity_id.in_(requesting_user.activity_ids),
                # You can see hidden payments if you are overseer.
                ent.Payment.initiative_id.in_(
                    select(ent.Initiative.id)
                    .join(ent.Grant)
                    .where(ent.Grant.id.in_(requesting_user.grant_ids))
                ),
                # You can see hidden payments in your regulation as an officer.
                ent.Regulation.id.in_(requesting_user.go_regulation_ids),
                ent.Regulation.id.in_(requesting_user.po_regulation_ids),
                # Administrators or super users can see everything.
                literal(requesting_user.is_administrator),
                literal(requesting_user.is_superuser),
                # Users can always see payments from their bank accounts.
                ent.Payment.bank_account_id.in_(
                    requesting_user.used_and_owned_bank_accounts
                ),
            )
        )

    q = apply_date_range_filter(q, start_date, end_date)
    q = apply_amount_range_filter(q, min_amount, max_amount)
    q = apply_route_filter(q, route)
    q = q.order_by(ent.Payment.id.desc()).offset(offset).limit(limit)

    return q


def get_activity_payments_q(
    optional_user: ent.User | None,
    activity_id: int,
    offset: int,
    limit: int,
    start_date: date | None,
    end_date: date | None,
    min_amount: TransactionAmount | None,
    max_amount: TransactionAmount | None,
    route: ent.Route | None,
):
    q = (
        select(
            ent.Payment.id,
            ent.Payment.booking_date,
            ent.Payment.creditor_name,
            ent.Payment.debtor_name,
            ent.Payment.short_user_description,
            ent.Payment.transaction_amount,
            func.count(ent.Attachment.id).label("n_attachments"),
        )
        .join(ent.Initiative, ent.Payment.initiative_id == ent.Initiative.id)
        .join(ent.Grant, ent.Initiative.grant_id == ent.Grant.id)
        .join(ent.Regulation, ent.Grant.regulation_id == ent.Regulation.id)
        .outerjoin(
            ent.Attachment,
            and_(
                ent.Payment.id == ent.Attachment.entity_id,
                ent.Attachment.entity_type == ent.AttachmentEntityType.PAYMENT.value,
            ),
        )
        .where(ent.Payment.activity_id == activity_id)
        .group_by(
            ent.Payment.id,
            ent.Payment.booking_date,
            ent.Payment.creditor_name,
            ent.Payment.debtor_name,
            ent.Payment.short_user_description,
            ent.Payment.transaction_amount,
        )
    )

    if optional_user is not None:
        requesting_user = RequestingUser(optional_user)

    if optional_user is None:
        q = q.where(ent.Payment.hidden == False)
    else:
        q = q.where(
            or_(
                ent.Payment.hidden == False,
                # You can see hidden payments if you are initiative owner.
                ent.Payment.initiative_id.in_(requesting_user.initiative_ids),
                # You can see hidden payments if you are activity owner.
                ent.Payment.activity_id.in_(requesting_user.activity_ids),
                # You can see hidden payments if you are overseer.
                ent.Payment.initiative_id.in_(
                    select(ent.Initiative.id)
                    .join(ent.Grant)
                    .where(ent.Grant.id.in_(requesting_user.grant_ids))
                ),
                # You can see hidden payments in your regulation as an officer.
                ent.Regulation.id.in_(requesting_user.go_regulation_ids),
                ent.Regulation.id.in_(requesting_user.po_regulation_ids),
                # Administrators or super users can see everything.
                literal(requesting_user.is_administrator),
                literal(requesting_user.is_superuser),
                # Users can always see payments from their bank accounts.
                ent.Payment.bank_account_id.in_(
                    requesting_user.used_and_owned_bank_accounts
                ),
            )
        )

    q = apply_date_range_filter(q, start_date, end_date)
    q = apply_amount_range_filter(q, min_amount, max_amount)
    q = apply_route_filter(q, route)
    q = q.order_by(ent.Payment.id.desc()).offset(offset).limit(limit)

    return q


async def get_initiative_media_q(
    optional_user: ent.User | None, initiative_id: int, offset: int, limit: int
):
    q = (
        select(ent.Attachment)
        .join(ent.Payment, ent.Payment.id == ent.Attachment.entity_id)
        .join(ent.Initiative, ent.Payment.initiative_id == ent.Initiative.id)
        .join(ent.Grant, ent.Initiative.grant_id == ent.Grant.id)
        .join(ent.Regulation, ent.Grant.regulation_id == ent.Regulation.id)
        .where(
            and_(
                ent.Payment.initiative_id == initiative_id,
                ent.Attachment.entity_type == ent.AttachmentEntityType.PAYMENT.value,
            )
        )
    )

    if optional_user is not None:
        requesting_user = RequestingUser(optional_user)

    if optional_user is None:
        q = q.where(ent.Payment.hidden == False)
    else:
        q = q.where(
            or_(
                ent.Payment.hidden == False,
                # You can see hidden payments if you are initiative owner.
                ent.Payment.initiative_id.in_(requesting_user.initiative_ids),
                # You can see hidden payments if you are activity owner.
                ent.Payment.activity_id.in_(requesting_user.activity_ids),
                # You can see hidden payments if you are overseer.
                ent.Payment.initiative_id.in_(
                    select(ent.Initiative.id)
                    .join(ent.Grant)
                    .where(ent.Grant.id.in_(requesting_user.grant_ids))
                ),
                # You can see hidden payments in your regulation as an officer.
                ent.Regulation.id.in_(requesting_user.go_regulation_ids),
                ent.Regulation.id.in_(requesting_user.po_regulation_ids),
                # Administrators or super users can see everything.
                literal(requesting_user.is_administrator),
                literal(requesting_user.is_superuser),
                # Users can always see payments from their bank accounts.
                ent.Payment.bank_account_id.in_(
                    requesting_user.used_and_owned_bank_accounts
                ),
            )
        )

    q = q.order_by(ent.Attachment.id.desc()).offset(offset).limit(limit)

    return q
