import colander
from betahaus.pyracont.decorators import schema_factory
from voteit.core.validators import deferred_existing_userid_validator
from voteit.core.schemas.common import deferred_autocompleting_userid_widget

from . import SFS_TSF as _


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
                                 validator = deferred_existing_userid_validator)


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
