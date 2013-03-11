import colander
import deform
from betahaus.pyracont.factories import createSchema
from pyramid.decorator import reify
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.renderers import render
from pyramid.traversal import resource_path
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPForbidden
from voteit.core.views.base_edit import BaseEdit
from voteit.core.models.interfaces import IMeeting
from voteit.core.schemas.common import add_csrf_token
from voteit.core.models.schemas import button_cancel
from voteit.core.models.schemas import button_delete
from voteit.core.models.schemas import button_save
from voteit.core import security

from .interfaces import IMeetingDelegations
from .fanstaticlib import sfs_manage_delegation
from . import SFS_TSF as _


class EditMeetingDelegationsView(BaseEdit):

    @reify
    def meeting_delegations(self):
        return self.request.registry.getAdapter(self.api.meeting, IMeetingDelegations)

    def check_ongoing_poll(self):
        """ Check if a poll is ongoing, return number of ongoing polls """
        meeting_path = resource_path(self.api.meeting)
        ongoing = self.api.search_catalog(content_type = 'Poll',
                                          path = meeting_path,
                                          workflow_state = 'ongoing')
        if ongoing[0]: #Count for hits
            raise HTTPForbidden(_(u"access_during_ongoing_not_allowed",
                                default = u"During ongoing polls, this action isn't allowed. Try again when polls have closed."))

    @view_config(name = "meeting_delegations", context = IMeeting, renderer = "templates/meeting_delegations.pt")
    def meeting_delegations_view(self):
        self.response['delegations'] = self.meeting_delegations.values()
        return self.response

    @view_config(name = "add_new_delegation", context = IMeeting, permission = security.MODERATE_MEETING)
    def add_new_delegation(self):
        """ Add a new delegation and redirect to edit view.
        """
        self.check_ongoing_poll()
        name = self.meeting_delegations.new()
        url = self.request.resource_url(self.context, 'edit_delegation', query = {'delegation': name})
        return HTTPFound(location = url)

    @view_config(name = "edit_delegation", context = IMeeting, permission = security.MODERATE_MEETING,
                 renderer = "voteit.core.views:templates/base_edit.pt")
    def edit_delegation(self):
        """ Edit delegation, for moderators.
        """
        self.check_ongoing_poll()
        name = self.request.GET.get('delegation')
        delegation = self.meeting_delegations[name]
        schema = createSchema('EditMeetingDelegationSchema')
        add_csrf_token(self.context, self.request, schema)
        schema = schema.bind(context = self.context, request = self.request, api = self.api)
        form = deform.Form(schema, buttons=(button_save, button_cancel))
        if 'save' in self.request.POST:
            controls = self.request.POST.items()
            try:
                appstruct = form.validate(controls)
            except deform.ValidationFailure, e:
                self.response['form'] = e.render()
                return self.response
            delegation.title = appstruct['title']
            delegation.leaders.clear()
            delegation.leaders.update(appstruct['leaders'])
            if delegation.vote_count != appstruct['vote_count']:
                delegation.vote_count = appstruct['vote_count']
                delegation.voters.clear()
                msg = _(u"voters_cleared_on_update_notice",
                        default = u"When you update vote count, vote distribution is cleared. Please redistribute votes for this group!")
                self.api.flash_messages.add(msg)
            else:
                self.api.flash_messages.add(_(u"Updated"))
            url = self.request.resource_url(self.context, 'manage_meeeting_delegation', query = {'delegation': name})
            return HTTPFound(location = url)
        if 'cancel' in self.request.POST:
            self.api.flash_messages.add(_(u"Canceled"))
            url = self.request.resource_url(self.context, 'meeting_delegations')
            return HTTPFound(location = url)
        appstruct = dict(
            title = delegation.title,
            leaders = delegation.leaders,
            vote_count = delegation.vote_count)
        self.response['form'] = form.render(appstruct = appstruct)
        return self.response

#    @view_config(name ="delete_delegation", context = IMeeting, permission = security.MODERATE_MEETING,
#                 renderer = "voteit.core.views:templates/base_edit.pt")
#    def delete_delegation(self):
#        schema = colander.Schema()
#        add_csrf_token(self.context, self.request, schema)
#        schema = schema.bind(context=self.context, request=self.request, api=self.api)
#        form = deform.Form(schema, buttons = (button_delete, button_cancel,))
#        if 'delete' in self.request.POST:
#            


    @view_config(name = "manage_meeeting_delegation", context = IMeeting, permission = security.VIEW,
                 renderer = "templates/manage_delegation.pt")
    def manage_delegation(self):
        """ Manage delegation members and votes, for delegation leads.
            Note that delegation lead isn't a perm and has to be checked in this view.
        """
        sfs_manage_delegation.need()
        self.check_ongoing_poll()
        #FIXME: When we can use dynamic permissions, update perms here
        delegation = self.meeting_delegations[self.request.GET.get('delegation')]
        if not self.api.userid in delegation.leaders:
            raise HTTPForbidden(_(u"Only delegation leads may distribute votes"))
        self.response['delegation'] = delegation
        #Make sure all members are inbluded in form, even if they're not stored as voters
        voters = {}
        for userid in delegation.members:
            voters[userid] = 0
        voters.update(delegation.voters)
        self.response['voters'] = voters
        return self.response

    @view_config(name = "set_delegation_voters", context = IMeeting, permission = security.VIEW)
    def set_delegation_voters(self):
        self.check_ongoing_poll()
        name = self.request.GET.get('delegation')
        delegation = self.meeting_delegations[name]
        if not self.api.userid in delegation.leaders:
            raise HTTPForbidden(_(u"Only delegation leads may distribute votes"))
        schema = createSchema('DelegationVotesDistributionSchema')
        schema = schema.bind(context = self.context, request = self.request, api = self.api)
        form = deform.Form(schema, buttons=())
        controls = self.request.POST.items()
        try:
            appstruct = form.validate(controls)
        except deform.ValidationFailure:
            return HTTPForbidden(_u("Something went wrong with your post"))
        #We validate this data without the schema here
        userids_votes = appstruct['userids_votes']
        vote_count = sum([x['votes'] for x in userids_votes])
        if delegation.vote_count != vote_count:
            return HTTPForbidden(_(u"Vote count didn't match."))
        #clear current voters
        delegation.voters.clear()
        for item in userids_votes:
            if item['votes']:
                #Make sure they're voters
                delegation.voters[item['userid']] = item['votes']
                self.set_voter_role(item['userid'], True)
            else:
                #Remove voting permisison
                self.set_voter_role(item['userid'], False)
                
        self.api.flash_messages.add(_(u"Updated"))
        url = self.request.resource_url(self.context, 'manage_meeeting_delegation', query = {'delegation': name})
        return HTTPFound(location = url)

    def set_voter_role(self, userid, voter = False):
        groups = self.api.meeting.get_groups(userid)
        if voter:
            if security.ROLE_VOTER not in groups:
                self.api.meeting.add_groups(userid, [security.ROLE_VOTER])
        else:
            if security.ROLE_VOTER in groups:
                self.api.meeting.del_groups(userid, [security.ROLE_VOTER])

    @view_config(name = "manage_meeeting_delegation_members", context = IMeeting, permission = security.VIEW,
                 renderer = "voteit.core.views:templates/base_edit.pt")
    def manage_meeeting_delegation_members(self):
        """ Manage delegation members, for delegation leads.
            Note that delegation lead isn't a perm and has to be checked in this view.
        """
        self.check_ongoing_poll()
        #FIXME: When we can use dynamic permissions, update perms here
        delegation = self.meeting_delegations[self.request.GET.get('delegation')]
        if not self.api.userid in delegation.leaders:
            raise HTTPForbidden(_(u"Only delegation leads may distribute votes"))
        self.response['delegation'] = delegation
        schema = createSchema('MeetingDelegationMembersSchema')
        add_csrf_token(self.context, self.request, schema)
        schema = schema.bind(context = self.context, request = self.request, api = self.api)
        form = deform.Form(schema, buttons=(button_save, button_cancel))
        if 'save' in self.request.POST:
            controls = self.request.POST.items()
            try:
                appstruct = form.validate(controls)
            except deform.ValidationFailure, e:
                self.response['form'] = e.render()
                return self.response
            delegation.members.clear()
            delegation.members.update(appstruct['members'])
            
            #Remove non-members from vote list
            userids_non_members = set(delegation.voters.keys()) - set(appstruct['members'])
            for userid in userids_non_members:
                del delegation.voters[userid]
            if userids_non_members:
                msg = _(u"removed_from_voters_list_notice",
                        default = u"You removed users who had votes set to them - please update vote distribution. Previous voters were: ${prev_voters}",
                        mapping = {'prev_voters': ", ".join(userids_non_members)})
                self.api.flash_messages.add(msg)
            
            self.api.flash_messages.add(_(u"Updated"))
            url = self.request.resource_url(self.context, 'manage_meeeting_delegation', query = {'delegation': delegation.name})
            return HTTPFound(location = url)
        if 'cancel' in self.request.POST:
            self.api.flash_messages.add(_(u"Canceled"))
            url = self.request.resource_url(self.context, 'meeting_delegations')
            return HTTPFound(location = url)
        appstruct = dict(members = delegation.members)
        self.response['form'] = form.render(appstruct = appstruct)
        return self.response
