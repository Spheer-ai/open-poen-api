from . import initiative as i
from . import activity as a
from . import user as u
from . import payment as p
from . import debit_card as d
from . import bng as bng


class InitiativeOutputGuestWithLinkedEntities(i.InitiativeOutputGuest):
    initiative_owners: list[u.UserOutputGuest]
    activities: list[a.ActivityOutputGuest]

    class Config:
        orm_mode = True


class InitiativeOutputActivityOwnerWithLinkedEntities(i.InitiativeOutputActivityOwner):
    initiative_owners: list[u.UserOutputActivityOwner]
    activities: list[a.ActivityOutputActivityOwner]

    class Config:
        orm_mode = True


class InitiativeOutputInitiativeOwnerWithLinkedEntities(
    i.InitiativeOutputInitiativeOwner
):
    initiative_owners: list[u.UserOutputInitiativeOwner]
    activies: list[a.ActivityOutputInitiativeOwner]


class InitiativeOutputAdminWithLinkedEntities(i.InitiativeOutputAdmin):
    initiative_owners: list[u.UserOutputAdmin]
    activities: list[a.ActivityOutputAdmin]

    class Config:
        orm_mode = True
        title = "InitiativeOutputWithLinkedEntities"


class UserOutputUserWithLinkedEntities(u.UserOutputUser):
    initiatives: list[i.InitiativeOutputUser]
    activities: list[a.ActivityOutputUser]

    class Config:
        orm_mode = True


class UserOutputUserOwnerWithLinkedEntities(u.UserOutputUserOwner):
    initiatives: list[i.InitiativeOutputUserOwner]
    activities: list[a.ActivityOutputUserOwner]

    class Config:
        orm_mode = True


class UserOutputAdminWithLinkedEntities(u.UserOutputAdmin):
    initiatives: list[i.InitiativeOutputAdmin]
    activities: list[a.ActivityOutputAdmin]
    bng: bng.BNGOutputAdmin

    class Config:
        orm_mode = True
        title = "UserOutputWithLinkedEntities"


class ActivityOutputGuestWithLinkedEntities(a.ActivityOutputGuest):
    activity_owners: list[u.UserOutputGuest]
    initiative: i.InitiativeOutputGuest

    class Config:
        orm_mode = True


class ActivityOutputInitiativeOwnerWithLinkedEntities(a.ActivityOutputInitiativeOwner):
    activity_owners: list[u.UserOutputInitiativeOwner]
    initiative: i.InitiativeOutputInitiativeOwner

    class Config:
        orm_mode = True


class ActivityOutputAdminWithLinkedEntities(a.ActivityOutputAdmin):
    activity_owners: list[u.UserOutputAdmin]
    initiative: i.InitiativeOutputAdmin

    class Config:
        orm_mode = True
        title = "ActivityOutputWithLinkedEntities"


class PaymentOutputInitiativeOwnerWithLinkedEntities(p.PaymentOutputInitiativeOwner):
    pass

    class Config:
        orm_mode = True


class PaymentOutputFinancialWithLinkedEntities(p.PaymentOutputFinancial):
    pass

    class Config:
        orm_mode = True
        title = "PaymentOutputWithLinkedEntities"


class DebitCardOutputActivityOwnerWithLinkedEntities(d.DebitCardOutputActivityOwner):
    pass

    class Config:
        orm_mode = True
        title = "DebitCardOutputWithLinkedEntities"


class BNGOutputAdminWithLinkedEntities(bng.BNGOutputAdmin):
    user: u.UserOutputAdmin

    class Config:
        orm_mode = True
        title = "BNGOutputWithLinkedEntities"
