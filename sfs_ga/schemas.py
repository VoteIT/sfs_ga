# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from arche.interfaces import ISchemaCreatedEvent
from arche.schemas import userid_hinder_widget
from arche.validators import ExistingUserIDs
from arche.validators import existing_userids
from voteit.core.models.interfaces import IMeeting
from voteit.core.schemas.agenda_item import AgendaItemSchema
from voteit.irl.models.interfaces import IParticipantNumbers
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


@colander.deferred
def unique_pn_leader_validator(node, kw):
    request = kw['request']
    delegation_name = request.GET.get('delegation', '')
    return DelegationPNValidator(request.meeting, delegation_name, 'leaders')

@colander.deferred
def unique_pn_member_validator(node, kw):
    request = kw['request']
    delegation_name = request.GET.get('delegation', '')
    return DelegationPNValidator(request.meeting, delegation_name, 'members')


class DelegationPNValidator(object):

    def __init__(self, meeting, delegation_name, type_attr):
        self.meeting = meeting
        self.delegations = IMeetingDelegations(meeting)
        self.delegation = self.delegations[delegation_name]
        self.type_attr = type_attr
        self.pn_attr = "pn_" + type_attr
        #Just as a safeguard
        assert hasattr(self.delegation, self.type_attr)
        assert hasattr(self.delegation, self.pn_attr)

    def __call__(self, node, value):
        other_delegations = [v for (k, v) in self.delegations.items() if k != self.delegation.name]
        already_used_pns = set()
        for delegation in other_delegations:
            already_used_pns.update(getattr(delegation, self.pn_attr, ()))
        duplicate = already_used_pns & set(value)
        if duplicate:
            msg = "Följande nummer har redan använts i andra delegationer: "
            msg += ", ".join([str(x) for x in duplicate])
            raise colander.Invalid(node, msg)
        pns = IParticipantNumbers(self.meeting)
        for pn in value:
            userid = pns.number_to_userid.get(pn, None)
            if userid:
                for delegation in other_delegations:
                    if userid in getattr(delegation, self.type_attr):
                        msg = "Deltagarnummer %r mappar till '%s' som redan är med i delegationen '%s'"\
                            % (pn, userid, delegation.title)
                        raise colander.Invalid(node, msg)


class LeadersPnSequence(colander.SequenceSchema):
    leaders = colander.SchemaNode(colander.Int(),
                                  title = "ledare",)


class MembersPnSequence(colander.SequenceSchema):
    members = colander.SchemaNode(colander.Int(),
                                  title = "medlem",)


class PnToDelegationSchema(colander.Schema):
    pn_leaders = LeadersPnSequence(title = "Deltagarnummer för delegationsledare",
                                   validator = unique_pn_leader_validator)
    pn_members = MembersPnSequence(title = "Deltagarnummer för medlemmar",
                                   validator = unique_pn_member_validator)


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
    schema.add(colander.SchemaNode(
        colander.String(),
        name = "proposal_hashtag",
        title = _(u"Base for hashtags."),
        validator = colander.Regex(r'[a-zA-Z0-9\-\_]{2,30}',
                                   msg = _("ai_hashtag_validator_error",
                                          default = "Only letters, numbers, '-' and '_'. "
                                                    "Required length 2-30 chars.")),
        description = _("ai_hashtag_description",
                        default = "Any proposals added here will have this string plus a number. "
                        "Something like this: [base for hashtag]-[number]"),
        missing = ""),)

def includeme(config):
    config.add_subscriber(add_ai_hashtag, [AgendaItemSchema, ISchemaCreatedEvent])
    config.add_content_schema('MeetingDelegation', EditMeetingDelegationSchema, 'edit')
    config.add_content_schema('MeetingDelegation', MeetingDelegationMembersSchema, 'members')
    config.add_content_schema('MeetingDelegation', MeetingDelegationMembersSchema, 'members')
    config.add_content_schema('MeetingDelegation', PnToDelegationSchema, 'pn_to_delegation')
