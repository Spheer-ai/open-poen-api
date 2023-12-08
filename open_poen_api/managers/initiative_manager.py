from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request, UploadFile, Depends
from .. import models as ent
from ..schemas import InitiativeCreate, InitiativeUpdate
from sqlalchemy.exc import IntegrityError
from ..exc import EntityAlreadyExists, EntityNotFound, raise_err_if_unique_constraint
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from .base_manager import BaseManager
from .handlers import ProfilePictureHandler
from .user_manager.user_manager_ex_current_user import optional_login
from ..database import get_async_session


class InitiativeManager(BaseManager):
    def __init__(
        self,
        session: AsyncSession = Depends(get_async_session),
        current_user: ent.User | None = Depends(optional_login),
    ):
        super().__init__(session, current_user)
        self.profile_picture_handler = ProfilePictureHandler[ent.Initiative](
            self.session, current_user, ent.AttachmentEntityType.INITIATIVE
        )

    async def create(
        self,
        initiative_create: InitiativeCreate,
        grant_id: int,
        request: Request | None = None,
    ) -> ent.Initiative:
        try:
            initiative = await self.crud.create(
                initiative_create, ent.Initiative, request, grant_id=grant_id
            )
        except IntegrityError as e:
            raise_err_if_unique_constraint("unique initiative name", e)
            raise
        return initiative

    async def update(
        self,
        initiative_update: InitiativeUpdate,
        initiative_db: ent.Initiative,
        request: Request | None = None,
    ) -> ent.Initiative:
        try:
            initiative = await self.crud.update(
                initiative_update, initiative_db, request
            )
        except IntegrityError as e:
            raise_err_if_unique_constraint("unique initiative name", e)
            raise
        return initiative

    async def delete(
        self, initiative: ent.Initiative, request: Request | None = None
    ) -> None:
        await self.crud.delete(initiative, request)

    async def make_users_owner(
        self,
        initiative: ent.Initiative,
        user_ids: list[int],
        request: Request | None = None,
    ):
        linked_user_ids = {role.user_id for role in initiative.user_roles}

        matched_users_q = await self.session.execute(
            select(ent.User).where(ent.User.id.in_(user_ids))
        )
        matched_users = matched_users_q.scalars().all()
        matched_user_ids = {user.id for user in matched_users}

        if not len(matched_users) == len(user_ids):
            raise EntityNotFound(
                message=f"There exist no Users with id's: {set(user_ids) - matched_user_ids}"
            )

        # TODO: Log this.
        stay_linked_user_ids = linked_user_ids.intersection(matched_user_ids)
        unlink_user_ids = linked_user_ids - matched_user_ids
        link_user_ids = matched_user_ids - linked_user_ids

        for role in [
            role for role in initiative.user_roles if role.user_id in unlink_user_ids
        ]:
            await self.session.delete(role)

        for user_id in link_user_ids:
            new_role = ent.UserInitiativeRole(
                user_id=user_id, initiative_id=initiative.id
            )
            self.session.add(new_role)

        await self.session.commit()
        return initiative

    async def link_debit_cards(
        self,
        initiative: ent.Initiative,
        card_numbers: list[str],
        request: Request | None,
        ignore_already_linked: bool = True,
    ):
        linked_card_numbers = {card.card_number for card in initiative.debit_cards}

        matched_cards_q = await self.session.execute(
            select(ent.DebitCard).where(ent.DebitCard.card_number.in_(card_numbers))
        )
        matched_cards = matched_cards_q.scalars().all()
        if not ignore_already_linked:
            already_linked_cards = [
                (card.card_number, card.initiative_id)
                for card in matched_cards
                if card.initiative_id is not None
            ]
            if any(already_linked_cards):
                already_linked_card_numbers, already_linked_initiative_ids = zip(
                    *already_linked_cards
                )
                raise EntityAlreadyExists(
                    message=f"Debit cards with numbers {already_linked_card_numbers} are already linked to initiatives with id's {already_linked_initiative_ids}"
                )
        matched_card_numbers = {card.card_number for card in matched_cards}

        # TODO: Log this.
        stay_linked_card_numbers = linked_card_numbers.intersection(
            matched_card_numbers
        )
        unlink_card_numbers = linked_card_numbers - matched_card_numbers
        link_existing_card_numbers = matched_card_numbers - linked_card_numbers
        link_non_existing_card_numbers = (
            set(card_numbers) - matched_card_numbers - linked_card_numbers
        )

        for card in [
            card
            for card in initiative.debit_cards
            if card.card_number in unlink_card_numbers
        ]:
            card.initiative_id = None
            self.session.add(card)

        for card_number in link_non_existing_card_numbers:
            new_debit_card = ent.DebitCard(
                card_number=card_number, initiative_id=initiative.id
            )
            self.session.add(new_debit_card)

        for card_number in link_existing_card_numbers:
            card_q = await self.session.execute(
                select(ent.DebitCard).where(ent.DebitCard.card_number == card_number)
            )
            card = card_q.scalars().one()
            card.initiative_id = initiative.id
            self.session.add(card)

        await self.session.commit()
        return initiative

    async def detail_load(self, id: int):
        query_result_q = await self.session.execute(
            select(ent.Initiative)
            .options(
                selectinload(ent.Initiative.user_roles).joinedload(
                    ent.UserInitiativeRole.user
                ),
                selectinload(ent.Initiative.activities),
                joinedload(ent.Initiative.profile_picture),
            )
            .where(ent.Initiative.id == id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Initiative not found")
        return query_result

    async def min_load(self, initiative_id: int):
        return await self.load.min_load(ent.Initiative, initiative_id)
