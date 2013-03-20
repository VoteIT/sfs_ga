import deform
from betahaus.pyracont.factories import createSchema
from betahaus.viewcomponent import view_action
from pyramid.decorator import reify
from pyramid.view import view_config
from pyramid.renderers import render
from pyramid.response import Response
from pyramid.traversal import resource_path
from pyramid.traversal import find_resource
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPForbidden
from voteit.core.views.base_edit import BaseEdit
from voteit.core.models.interfaces import IMeeting
from voteit.core.models.interfaces import IProposal
from voteit.core.models.interfaces import IUser
from voteit.core.schemas.common import add_csrf_token
from voteit.core.models.schemas import button_cancel
from voteit.core.models.schemas import button_delete
from voteit.core.models.schemas import button_save
from voteit.core import security

from .interfaces import IMeetingDelegations
from .interfaces import IProposalSupporters
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

    @view_config(name = "delegation_votes_overview", context = IMeeting, permission = security.VIEW,
                 renderer = "templates/delegation_votes.pt")
    def delegation_votes_overview(self):
        delegation = self.meeting_delegations[self.request.GET.get('delegation')]
        if not self.api.userid in delegation.leaders:
            raise HTTPForbidden(_(u"Only for delegation leaders"))
        self.response['delegation'] = delegation
        result_ais = []
        result_polls = {}
        for ai in self.api.get_restricted_content(self.context, content_type = 'AgendaItem'):
            polls = self.api.get_restricted_content(ai, content_type = 'Poll')
            if polls:
                result_ais.append(ai)
                result_polls[ai.__name__] = polls
        self.response['result_ais'] = result_ais
        self.response['result_polls'] = result_polls

        def _vote_count_for(poll, userids):
            """ Return first element of query result, which is a count. """
            return self.api.search_catalog(path = resource_path(poll),
                                           content_type = 'Vote',
                                           creators = {'query': userids,
                                                       'operator': 'or'})[0]
        self.response['vote_count_for'] = _vote_count_for
        return self.response

    @view_config(name = "_toggle_delegation_support_proposal", context = IProposal, permission = security.VIEW)
    def toggle_delegation_support_proposal(self):
        delegation = self.meeting_delegations.get_delegation_for(self.api.userid)
        if not delegation:
            raise HTTPForbidden()
        supporters = self.request.registry.getAdapter(self.context, IProposalSupporters)
        do = int(self.request.GET['do'])
        if do:
            supporters.add(delegation.name)
        else:
            supporters.remove(delegation.name)
        return Response(self.api.render_single_view_component(self.context, self.request, 'metadata_listing', 'support_proposal'))

    def _show_supporters_tpl(self):
        supporters = self.request.registry.getAdapter(self.context, IProposalSupporters)
        self.response['delegations'] = [self.meeting_delegations.get(x, x) for x in supporters()]
        return render("templates/supporters_popup.pt", self.response, request = self.request)

    @view_config(context=IProposal, name="_show_supporters_popup", permission=security.VIEW, xhr=True)
    def show_supporters_popup_ajax_wrapper(self):
        return Response(self._show_supporters_tpl())

    @view_config(context=IProposal, name="_show_supporters_popup", permission=security.VIEW, xhr=False,
                 renderer="voteit.core.views:templates/simple_view.pt")
    def show_supporters_popup(self):
        self.response['content'] = self._show_supporters_tpl()
        return self.response

    @view_config(name = "_publish_proposal", context = IProposal, permission = security.VIEW)
    def publish_proposal_action(self):
        """ Set a proposal as published if it's unhandled and user has voter role.
            FIXME: Additional checks required, this shouldn't be performed in any meeting state for instance.
        """
        if self.context.get_workflow_state() != 'unhandled':
            return HTTPForbidden(_(u"This proposal isn't in state 'Unhandled'"))
        if security.ROLE_VOTER not in self.api.cached_effective_principals:
            return HTTPForbidden(_(u"You must have the voter role to do that"))
        security.unrestricted_wf_transition_to(self.context, 'published')
        self.api.flash_messages.add(_(u"Proposal now set as published"))
        url = self.request.resource_url(self.context.__parent__, anchor = self.context.uid)
        return HTTPFound(location = url)

@view_action('meeting', 'delegations', title = _(u"Delegations"))
def delegations_menu_link(context, request, va, **kw):
    api = kw['api']
    url = "%s%s" % (api.meeting_url, 'meeting_delegations')
    return """<li><a href="%s">%s</a></li>""" % (url, api.translate(va.title))

@view_action('metadata_listing', 'support_proposal')
def support_proposal(context, request, va, **kw):
    """ Note that the brain within the kw dict is the actual context we want. """
    api = kw['api']
    if 'brain' in kw:
        prop = find_resource(api.root, kw['brain']['path'])
    else:
        prop = context
    
    if not IProposal.providedBy(prop):
        return u""
    delegations = request.registry.getAdapter(api.meeting, IMeetingDelegations)
    delegation = delegations.get_delegation_for(api.userid)
    response = dict(
        api = api,
        delegation = delegation,
        context = prop,
    )
    supporters = request.registry.getAdapter(prop, IProposalSupporters)
    supporters_count = len(supporters())
    response['supporters_text'] = api.pluralize(_(u"${supporters_count} supporter"),
                                            _(u"${supporters_count} supporters"),
                                            supporters_count,
                                            domain = 'sfs_ga',
                                            mapping = {'supporters_count': supporters_count})
    response['voter'] = voter = delegation and delegation.voters.get(api.userid, 0) or 0
    if voter:
        if delegation.name in supporters():
            response['do'] = 0
            response['action_title'] = _(u"Remove support")
        else:
            response['do'] = 1
            response['action_title'] = _(u"Support this")

    return render("templates/support_proposal.pt", response, request = request)

@view_action('metadata_listing', 'publish_undhandled_proposal')
def publish_undhandled_proposal_link(context, request, va, **kw):
    """ Note that the brain within the kw dict is the actual context we want. """
    api = kw['api']
    brain = kw['brain']
    if brain['content_type'] == 'Proposal' and\
        security.ROLE_VOTER in api.cached_effective_principals and\
        brain['workflow_state'] == 'unhandled':
        url = "%s/_publish_proposal" % brain['path']
        title = api.translate(_(u"Publish"))
        return """<a href="%s">%s</a>""" % (url, title)
    return u""

@view_action('user_info', 'delegation_info', interface = IUser)
def delegation_info(context, request, va, **kw):
    api = kw['api']
    if not api.meeting:
        return u""
    delegations = request.registry.getAdapter(api.meeting, IMeetingDelegations)
    delegation = delegations.get_delegation_for(context.userid)
    if not delegation:
        return u""
    response = dict(
        api = api,
        delegation = delegation,)
    return render("templates/user_delegation_info.pt", response, request = request)
