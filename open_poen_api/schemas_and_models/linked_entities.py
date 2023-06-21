from . import initiative as i
from . import activity as a
from . import user as u


class InitiativeOutputGuestWithLinkedEntities(i.InitiativeOutputGuest):
    initiative_owners: list[u.UserOutputGuest]
    activities: list[a.ActivityOutputGuest]


class InitiativeOutputActivityOwnerWithLinkedEntities(i.InitiativeOutputActivityOwner):
    initiative_owners: list[u.UserOutputActivityOwner]
    activities: list[a.ActivityOutputActivityOwner]

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

    class Config:
        orm_mode = True
        title = "UserOutputWithLinkedEntities"


class ActivityOutputGuestWithLinkedEntities(a.ActivityOutputGuest):
    activity_owners: list[u.UserOutputGuest]
    initiative: i.InitiativeOutputGuest
