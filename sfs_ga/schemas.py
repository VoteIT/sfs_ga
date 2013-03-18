import colander
from betahaus.pyracont.decorators import schema_factory
from voteit.core.models.interfaces import IMeeting
from voteit.core.validators import deferred_existing_userid_validator
from voteit.core.validators import GlobalExistingUserId
from voteit.core.schemas.common import deferred_autocompleting_userid_widget



from . import SFS_TSF as _
from .interfaces import IMeetingDelegations


@colander.deferred
def deferred_single_delegation_validator(node, kw):
    """ Check both GlobalExistingUserId and SingleDelegationValidator"""
    context = kw['context']
    request = kw['request']
    assert IMeeting.providedBy(context)
    return SingleDelegationValidator(context, request)


class SingleDelegationValidator(object):

    def __init__(self, context , request):
        self.context = context
        self.request = request

    def __call__(self, node, value):
        existing_userid = GlobalExistingUserId(self.context)
        existing_userid(node, value) #Make sure userid exists
        delegations = self.request.registry.getAdapter(self.context, IMeetingDelegations)
        current_name = self.request.GET.get('delegation')
        for delegation in delegations.values():
            if delegation.name == current_name:
                continue
            if value in delegation.members:
                raise colander.Invalid(node, _(u"Already part of the delegation ${delegation}",
                                               mapping = {'delegation': delegation.title}))


class LeadersSequence(colander.SequenceSchema):
    leaders = colander.SchemaNode(colander.String(),
                                 title = _(u"Delegation leaders"),
                                 description = _(u"Start typing a userid,"),
                                 widget = deferred_autocompleting_userid_widget,
                                 validator = deferred_existing_userid_validator)


@schema_factory('EditMeetingDelegationSchema')
class EditMeetingDelegationSchema(colander.Schema):
    title = colander.SchemaNode(colander.String(),
                                title = _(u"Title"))
    vote_count = colander.SchemaNode(colander.Integer(),
                                title = _(u"Total number of votes"))
    leaders = LeadersSequence()


class MembersSequence(colander.SequenceSchema):
    members = colander.SchemaNode(colander.String(),
                                 title = _(u"Delegation members"),
                                 description = _(u"Start typing a userid,"),
                                 widget = deferred_autocompleting_userid_widget,
                                 validator = deferred_single_delegation_validator)


@schema_factory('MeetingDelegationMembersSchema')
class MeetingDelegationMembersSchema(colander.Schema):
    members = MembersSequence()


class UserIDAndVotesSchema(colander.Schema):
    userid = colander.SchemaNode(colander.String(),)
    votes = colander.SchemaNode(colander.Int(),)


class UserIDsAndVotesSequence(colander.SequenceSchema):
    userid_votes = UserIDAndVotesSchema()


@schema_factory('DelegationVotesDistributionSchema')
class DelegationVotesDistributionSchema(colander.Schema):
    """This schema is used as marshaller for the view to handle vote distribution. """
    userids_votes = UserIDsAndVotesSequence()
