#from betahaus.pyracont.interfaces import ISchemaBoundEvent
#from betahaus.pyracont.interfaces import ISchemaCreatedEvent
#from voteit.core.schemas.common import deferred_autocompleting_userid_widget
#from voteit.core.schemas.interfaces import IAgendaItemSchema
#from voteit.core.schemas.interfaces import IProposalSchema
#from voteit.core.validators import GlobalExistingUserId
#from voteit.core.validators import deferred_existing_userid_validator
from arche.interfaces import ISchemaCreatedEvent
from arche.schemas import userid_hinder_widget
from arche.validators import ExistingUserIDs
from arche.validators import existing_userids
from voteit.core.models.interfaces import IMeeting
from voteit.core.schemas.agenda_item import AgendaItemSchema
import colander
import deform

from sfs_ga import _
from sfs_ga.interfaces import IMeetingDelegations


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
        existing_userid = ExistingUserIDs(self.context)
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
                                 description = _(u"Start typing a userid"),
                                 widget = userid_hinder_widget,
                                 validator = existing_userids)


class EditMeetingDelegationSchema(colander.Schema):
    title = colander.SchemaNode(colander.String(),
                                title = _(u"Title"))
    description = colander.SchemaNode(colander.String(),
                                      title = _("Description"),
                                      missing = "",
                                      widget = deform.widget.TextAreaWidget())
    vote_count = colander.SchemaNode(colander.Integer(),
                                title = _(u"Total number of votes"))
    leaders = LeadersSequence(title = _(u"Delegation leaders"),
                              description = _(u"Add one UserID per row."))


class MembersSequence(colander.SequenceSchema):
    members = colander.SchemaNode(colander.String(),
                                 title = _(u"Delegation members"),
                                 description = _(u"Start typing a userid"),
                                 widget = userid_hinder_widget,
                                 validator = deferred_single_delegation_validator)


class MeetingDelegationMembersSchema(colander.Schema):
    title = _(u"Edit delegation members")
    description = _(u"manage_delegation_schema_description",
                    default = u"Add or remove delegation members with form below. "
                    u"Only the users listed below will be members of the delegation.")
    members = MembersSequence(title = _(u"Members"),
                              description = _(u"Add one UserID per row."))


class UserIDAndVotesSchema(colander.Schema):
    userid = colander.SchemaNode(colander.String(),)
    votes = colander.SchemaNode(colander.Int(),)


class UserIDsAndVotesSequence(colander.SequenceSchema):
    userid_votes = UserIDAndVotesSchema()


class DelegationVotesDistributionSchema(colander.Schema):
    """This schema is used as marshaller for the view to handle vote distribution. """
    userids_votes = UserIDsAndVotesSequence()


def add_ai_hashtag(schema, event):
    """ Subscriber that sets hashtag base for an agenda item. """
    schema.add(colander.SchemaNode(colander.String(),
                                   name = "proposal_hashtag",
                                   title = _(u"Base for hashtags."),
                                   validator = colander.Regex(r'[a-zA-Z0-9\-\_]{2,30}',
                                                              msg = _(u"Only letters, words, '-' and '_'. Required length 2-30 chars.")),
                                   description = _(u"Any proposals added here will have this string plus a number. "
                                                   u"Something like this: [base for hashtag]-[number]"),
                                   missing = u""),)

def includeme(config):
    config.add_subscriber(add_ai_hashtag, [AgendaItemSchema, ISchemaCreatedEvent])
    config.add_content_schema('MeetingDelegation', EditMeetingDelegationSchema, 'edit')
    config.add_content_schema('MeetingDelegation', MeetingDelegationMembersSchema, 'members')

# @subscriber([IAgendaItemSchema, ISchemaCreatedEvent])
# def add_selectable_tags(schema, event):
#     #FIXME: This is temporary - the proper widget should be sortable!
#     schema.add(colander.SchemaNode(
#                     colander.Sequence(),
#                     colander.SchemaNode(colander.String(),
#                                         title = _('tag'),
#                                         name = 'not_used',
#                                         validator = colander.Regex(r'^[a-z0-9\_\-]{1,20}$',
#                                                                    msg = _(u"Only lowercase, numbers, '-' and '_'."))
#                                         ),
#                     name = 'selectable_proposal_tags',
#                     widget = deform.widget.SequenceWidget(orderable = True),))

# @subscriber([IProposalSchema, ISchemaBoundEvent])
# def add_forced_hashtag(schema, event):
#     context = event.kw['context']
#     request = event.kw['request']
#     if context.content_type != 'AgendaItem' or request.view_name != '_inline_form':
#         return
#     selectable_tags = context.get_field_value('selectable_proposal_tags', ())
#     if not selectable_tags:
#         return
#     selectable_values = [(x.lower(), "#%s" % x.lower()) for x in selectable_tags]
#     selectable_values.insert(0, ('', _(u"<Choose category>")))
#     selectable_values.append(('__nothing__', _(u"None of the above")))
#     schema.add(colander.SchemaNode(colander.String(),
#                                    name = "extra_hashtag",
#                                    widget = deform.widget.SelectWidget(values = selectable_values)
#                                    ))
