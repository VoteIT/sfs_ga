from __future__ import unicode_literals

from arche.security import PERM_MANAGE_SYSTEM
from arche.views.base import BaseForm
from arche.views.base import BaseView
from arche.views.base import DefaultDeleteForm
from arche.views.base import DefaultEditForm
from betahaus.viewcomponent import view_action
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render
from pyramid.traversal import find_interface
from pyramid.traversal import resource_path
from pyramid.view import view_config
from voteit.core import security
from voteit.core.models.interfaces import IAgendaItem
from voteit.core.models.interfaces import IMeeting
from voteit.core.models.interfaces import IProposal
from voteit.core.models.interfaces import IUser
import colander
import deform

from sfs_ga import _
from sfs_ga.fanstaticlib import sfs_manage_delegation
from sfs_ga.interfaces import IMeetingDelegations
from sfs_ga.schemas import DelegationVotesDistributionSchema

def _check_ongoing_poll(view):
    """ Check if a poll is ongoing, return number of ongoing polls """
    meeting_path = resource_path(view.request.meeting)
    ongoing = view.catalog_search(type_name = 'Poll',
                                  path = meeting_path,
                                  workflow_state = 'ongoing')
    if ongoing:
        raise HTTPForbidden(_(u"access_during_ongoing_not_allowed",
                            default = u"During ongoing polls, this action isn't allowed. "
                            "Try again when polls have closed."))

class MeetingDelegationsView(BaseView):

    @reify
    def meeting_delegations(self):
        return self.request.registry.getAdapter(self.request.meeting, IMeetingDelegations)

    @view_config(name = "meeting_delegations", context = IMeeting, renderer = "templates/meeting_delegations.pt")
    def delegations_view(self):
        show_all = self.request.GET.get('show_all', False)
        delegations = sorted(self.meeting_delegations.values(), key = lambda x: x.title.lower())
        my_delegations = []
        if not self.request.is_moderator:
            for delegation in delegations:
                pool = set(delegation.leaders) | set(delegation.members)
                if self.request.authenticated_userid in pool:
                    my_delegations.append(delegation)
        response = {}
        response['all_count'] = len(self.meeting_delegations)
        response['my_delegations'] = my_delegations
        response['show_all'] = show_all
        if show_all or self.request.is_moderator:
            response['delegations'] = delegations
        else:
            response['delegations'] = my_delegations
        return response

    @view_config(name = "add_new_delegation", context = IMeeting, permission = security.MODERATE_MEETING)
    def add_new_delegation(self):
        """ Add a new delegation and redirect to edit view.
        """
        _check_ongoing_poll(self)
        name = self.meeting_delegations.new()
        url = self.request.resource_url(self.context, 'edit_delegation', query = {'delegation': name})
        return HTTPFound(location = url)

    @view_config(name = "manage_meeeting_delegation",
                 context = IMeeting,
                 permission = security.VIEW,
                 renderer = "templates/manage_delegation.pt")
    def manage_delegation(self):
        """ Manage delegation members and votes, for delegation leads.
            Note that delegation lead isn't a perm and has to be checked in this view.
        """
        sfs_manage_delegation.need()
        _check_ongoing_poll(self)
        #FIXME: When we can use dynamic permissions, update perms here
        delegation = self.meeting_delegations[self.request.GET.get('delegation')]
        if not self.request.authenticated_userid in delegation.leaders and not self.request.is_moderator:
            raise HTTPForbidden(_(u"Only delegation leads may distribute votes"))
        response = {}
        response['delegation'] = delegation
        #Make sure all members are inbluded in form, even if they're not stored as voters
        voters = {}
        for userid in delegation.members:
            voters[userid] = 0
        voters.update(delegation.voters)
        response['voters'] = voters
        return response

    @view_config(name = "set_delegation_voters", context = IMeeting, permission = security.VIEW)
    def set_delegation_voters(self):
        _check_ongoing_poll(self)
        name = self.request.GET.get('delegation')
        delegation = self.meeting_delegations[name]
        if not self.request.authenticated_userid in delegation.leaders and not self.request.is_moderator:
            raise HTTPForbidden(_(u"Only delegation leads may distribute votes"))
        schema = DelegationVotesDistributionSchema()
        schema = schema.bind(context = self.context, request = self.request, view = self)
        form = deform.Form(schema, buttons=())
        controls = self.request.POST.items()
        try:
            appstruct = form.validate(controls)
        except deform.ValidationFailure:
            return HTTPForbidden(_(u"Something went wrong, please try again"))
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
                
        self.flash_messages.add(_(u"Updated"))
        url = self.request.resource_url(self.context, 'manage_meeeting_delegation', query = {'delegation': name})
        return HTTPFound(location = url)

    def set_voter_role(self, userid, voter = False):
        assert IMeeting.providedBy(self.context)
        groups = self.context.local_roles.get(userid, ())
        if voter:
            if security.ROLE_VOTER not in groups:
                self.context.local_roles.add(userid, security.ROLE_VOTER)
        else:
            if security.ROLE_VOTER in groups:
                self.context.local_roles.remove(userid, security.ROLE_VOTER)

@view_config(name = "manage_meeeting_delegation_members",
             context = IMeeting,
             permission = security.VIEW,
             renderer = "arche:templates/form.pt")
class MaangeDelegationMembersForm(DefaultEditForm):
    """ Manage delegation members, for delegation leads.
        Note that delegation lead isn't a perm and has to be checked in this view.
    """
    type_name = 'MeetingDelegation'
    schema_name = 'members'

    @reify
    def delegation(self):
        delegations = self.request.registry.getAdapter(self.request.meeting, IMeetingDelegations)
        name = self.request.GET.get('delegation', '')
        if name not in delegations:
            raise HTTPFound()
        return delegations[name]

    def __init__(self, context, request):
        super(MaangeDelegationMembersForm, self).__init__(context, request)
        _check_ongoing_poll(self)
        if not self.request.authenticated_userid in self.delegation.leaders and not self.request.is_moderator:
            raise HTTPForbidden(_("Only delegation leaders may change members."))

    def appstruct(self):
        return dict(members = self.delegation.members)

    def save_success(self, appstruct):
        previous_members = set(self.delegation.members) - set(appstruct['members'])
        self.delegation.members.clear()
        self.delegation.members.update(appstruct['members'])
        #Set discuss and propose for delegation members
        for userid in appstruct['members']:
            self.context.local_roles.add(userid, [security.ROLE_DISCUSS, security.ROLE_PROPOSE])
        #remove discuss and propose + vote in case they have that
        for userid in previous_members:
            self.context.local_roles.remove(userid, [security.ROLE_DISCUSS, security.ROLE_PROPOSE, security.ROLE_VOTER])
        #Remove non-members from vote list
        userids_non_members = set(self.delegation.voters.keys()) - set(appstruct['members'])
        for userid in userids_non_members:
            del self.delegation.voters[userid]
        if userids_non_members:
            msg = _(u"removed_from_voters_list_notice",
                    default = u"You removed users who had votes set to them - please update vote distribution. Previous voters are: ${prev_voters}",
                    mapping = {'prev_voters': ", ".join(userids_non_members)})
            self.flash_messages.add(msg, type = 'warning')
        else:
            self.flash_messages.add(self.default_success)
        url = self.request.resource_url(self.context, 'manage_meeeting_delegation', query = {'delegation': self.delegation.name})
        return HTTPFound(location = url)

    def cancel_success(self, *args):
        url = self.request.resource_url(self.context, 'meeting_delegations')
        return HTTPFound(location = url)


@view_config(name ="delete_delegation",
             context = IMeeting,
             permission = security.MODERATE_MEETING,
             renderer = "arche:templates/form.pt")
class DeleteDelegationForm(DefaultDeleteForm):
    @property
    def title(self):
        return _(u"really_delete_delegation_warning",
                 default = u"Really delete delegation '${delegation_title}'? This can't be undone",
                 mapping = {'delegation_title': self.meeting_delegations[self.delegation_name].title})

    @reify
    def delegation_name(self):
        return self.request.GET.get('delegation')

    @reify
    def meeting_delegations(self):
        return self.request.registry.getAdapter(self.request.meeting, IMeetingDelegations)

    def __init__(self, context, request):
        super(DeleteDelegationForm, self).__init__(context, request)
        _check_ongoing_poll(self)

    def delete_success(self, appstruct):
        msg = _("Deleted '${title}'",
                mapping = {'title': self.meeting_delegations[self.delegation_name].title})
        self.flash_messages.add(msg, type = 'warning')
        del self.meeting_delegations[self.delegation_name]
        url = self.request.resource_url(self.context, 'meeting_delegations')
        return HTTPFound(location = url)

    def cancel_success(self, *args):
        url = self.request.resource_url(self.context, 'meeting_delegations')
        return HTTPFound(location = url)


@view_config(name = "edit_delegation",
             context = IMeeting,
             permission = security.MODERATE_MEETING,
             renderer = "arche:templates/form.pt")
class EditDelegationForm(DefaultEditForm):
    """ Edit delegation, for moderators.
    """
    title = _(u"Edit delegation")
    type_name = 'MeetingDelegation'
    schema_name = 'edit'

    @reify
    def delegation_name(self):
        return self.request.GET.get('delegation')

    @reify
    def delegation(self):
        delegations = self.request.registry.getAdapter(self.request.meeting, IMeetingDelegations)
        return delegations[self.delegation_name]

    def __init__(self, context, request):
        super(EditDelegationForm, self).__init__(context, request)
        _check_ongoing_poll(self)

    def appstruct(self):
        return dict(title = self.delegation.title,
                    description = self.delegation.description,
                    leaders = self.delegation.leaders,
                    vote_count = self.delegation.vote_count)

    def save_success(self, appstruct):
        delegation = self.delegation
        delegation.title = appstruct['title']
        delegation.description = appstruct['description']
        delegation.leaders.clear()
        delegation.leaders.update(appstruct['leaders'])
        if delegation.vote_count != appstruct['vote_count']:
            delegation.vote_count = appstruct['vote_count']
            delegation.voters.clear()
            msg = _(u"voters_cleared_on_update_notice",
                    default = u"When you update vote count, vote distribution is cleared. Please redistribute votes for this group!")
            self.flash_messages.add(msg)
        else:
            self.flash_messages.add(self.default_success)
        url = self.request.resource_url(self.context, 'manage_meeeting_delegation', query = {'delegation': self.delegation_name})
        return HTTPFound(location = url)

    def cancel_success(self, *args):
        url = self.request.resource_url(self.context, 'manage_meeeting_delegation', query = {'delegation': self.delegation_name})
        return HTTPFound(location = url)

#FIXME: This doesn't work when the catalog changed
#     @view_config(name = "delegation_votes_overview", context = IMeeting, permission = security.VIEW,
#                  renderer = "templates/delegation_votes.pt")
#     def delegation_votes_overview(self):
#         delegation = self.meeting_delegations[self.request.GET.get('delegation')]
#         if not self.api.userid in delegation.leaders and not self.api.show_moderator_actions:
#             raise HTTPForbidden(_(u"Only for delegation leaders"))
#         self.response['delegation'] = delegation
#         result_ais = []
#         result_polls = {}
#         userids = set(delegation.members)
# 
#         for ai in self.api.get_restricted_content(self.context, content_type = 'AgendaItem'):
#             polls = self.api.get_restricted_content(ai, content_type = 'Poll')
#             if polls:
#                 result_ais.append(ai)
#                 result_polls[ai.__name__] = polls
#         self.response['result_ais'] = result_ais
#         self.response['result_polls'] = result_polls
# 
#         def _vote_count_for(poll, userids):
#             
#             return self.api.search_catalog(path = resource_path(poll),
#                                            content_type = 'Vote',
#                                            creators = {'query': userids,
#                                                        'operator': 'or'})[0]
#         self.response['vote_count_for'] = _vote_count_for
#         return self.response


@view_config(name = "adjust_proposals_to_unhandled",
             context = IMeeting,
             permission = PERM_MANAGE_SYSTEM,
             renderer = "arche:templates/form.pt")
class ProposalsToUnhandledForm(DefaultEditForm):
    title = _(u"Adjust all published proposals in ongoing AIs to unhandled?")

    def get_schema(self):
        return colander.Schema()

    def save_success(self, appstruct):
        count = 0
        for ai in self.context.get_content(content_type = 'AgendaItem', states = ['ongoing']):
            for proposal in ai.get_content(content_type = 'Proposal', states = ['published']):
                proposal.set_workflow_state(self.request, 'unhandled')
                count += 1
        self.flash_messages.add(_(u"Changed ${count} proposals",
                                  mapping = {'count': count}))
        return HTTPFound(location = self.request.resource_url(self.context))


# class RenameProposalIdsForm(BaseEdit):
# 
#     @view_config(name = "rename_proposal_ids", context = IAgendaItem, permission = security.MODERATE_MEETING,
#                  renderer = "voteit.core.views:templates/base_edit.pt")
#     def rename_proposal_ids(self):
#         description_txt = _(u"rename_proposal_ids_description",
#                             default = u"Specify the number part of the id. It's a good idea to make it unique. "
#                                 u"All proposals will also be renamed according to the currently set proposal hashtag. "
#                                 u"That value is set while editing the agenda item.")
#         schema = colander.Schema(title = _(u"Adjust value for Proposal IDs."),
#                                  description = description_txt)
#         current = {}
#         for prop in self.context.get_content(content_type = 'Proposal'):
#             current[prop.__name__] = prop.get_field_value('aid_int')
#             schema.add(colander.SchemaNode(colander.Int(),
#                                            name = prop.__name__,
#                                            title = prop.get_field_value('aid'),
#                                            description = prop.title))
#         form = deform.Form(schema, buttons = (button_save, button_cancel))
#         if 'cancel' in self.request.POST:
#             self.api.flash_messages.add(_(u"Canceled"))
#             return HTTPFound(location = self.request.resource_url(self.context))
#         if 'save' in self.request.POST:
#             controls = self.request.POST.items()
#             try:
#                 appstruct = form.validate(controls)
#             except deform.ValidationFailure, e:
#                 self.response['form'] = e.render()
#                 return self.response
#             tag_name = self.context.get_field_value('proposal_hashtag', None)
#             if not tag_name:
#                 tag_name = self.context.__name__
#             for (name, val) in appstruct.items():
#                 values = {'aid_int': val,
#                           'aid': "%s-%s" % (tag_name, val)}
#                 #Notify is for the catalog so metadata is reindexed
#                 self.context[name].set_field_appstruct(values, notify = True)
#             proposal_ids = self.request.registry.getAdapter(self.api.meeting, IProposalIds)
#             proposal_ids.proposal_ids[self.context.__name__] = max(appstruct.values())
#             self.api.flash_messages.add(_(u"Saved"))
#             return HTTPFound(location = self.request.resource_url(self.context))
#         self.response['form'] = form.render(appstruct = current)
#         return self.response


@view_config(name = "_print_proposals_form",
             context = IAgendaItem,
             permission = security.MODERATE_MEETING,
             renderer = "arche:templates/form.pt")
class PrintProposalsForm(BaseForm):

    @property
    def buttons(self):
        return (deform.Button('print', title = _("Print"), css_class = 'btn btn-primary'),
                self.button_cancel)

    def get_schema(self):
        schema = colander.Schema(title = _(u"Select proposals to print"),
                                 description = _(u"print_proposals_description",
                                                 default = u"Each proposal will be on its own page"))
        
        for prop in self.context.get_content(content_type = 'Proposal'):
            schema.add(colander.SchemaNode(colander.Bool(),
                                           name = prop.__name__,
                                           title = prop.get_field_value('aid'),
                                           description = prop.title))
        return schema

    def print_success(self, appstruct):
        self.request.session['print_proposal_ids'] = [name for (name, val) in appstruct.items() if val == True]
        return HTTPFound(location = self.request.resource_url(self.context, '_print_proposals'))


@view_config(name = "_print_proposals",
             context = IAgendaItem,
             permission = security.MODERATE_MEETING,
             renderer = "templates/print_proposals.pt")
class PrintProposalsView(BaseView):

    def __call__(self):
        response = {}
        proposal_ids = self.request.session.pop('print_proposal_ids', ())
        dt_handler = self.request.dt_handler
        response['proposals'] = [self.context[x] for x in proposal_ids]
        response['now'] = dt_handler.format_dt(dt_handler.utcnow())
        return response


# class SFSProjectorView(ProjectorView):
#     """ Custom version that may re-sort proprosals. """
# 
#     @view_config(context=IAgendaItem,
#                  name="projector",
#                  renderer="voteit.irl:views/templates/projector/projector.pt",
#                  permission=security.MODERATE_MEETING)
#     def view(self):
#         response = super(SFSProjectorView, self).view()
#         if self.request.session.get('ai_sort_tags', False):
#             tag_adjust_proposal_order(response, self.context.get_field_value('selectable_proposal_tags', ()), brains = False)
#         #And yet another sorter, this time for workflow
#         #Proposals should be grouped according to published, approved, denied
#         points = dict(published = 1, approved = 2, denied = 3)
#         maxpoint = 4
#         def _sorter(obj):
#             return points.get(obj.get_workflow_state(), maxpoint)
#         response['proposals'] = sorted(response['proposals'], key = _sorter)
#         return response


@view_action('participants_menu', 'delegations', title = _(u"Delegations"))
def delegations_menu_link(context, request, va, **kw):
    return """<li><a href="%s">%s</a></li>""" % (request.resource_url(request.meeting, 'meeting_delegations'),
                                                 request.localizer.translate(va.title))

@view_action('user_info', 'delegation_info', interface = IUser)
def delegation_info(context, request, va, **kw):
    if not request.meeting:
        return
    delegations = request.registry.getAdapter(request.meeting, IMeetingDelegations)
    delegation = delegations.get_delegation_for(context.userid)
    if not delegation:
        return
    response = dict(
        delegation = delegation,
        context = context)
    return render("templates/user_delegation_info.pt", response, request = request)

@view_action('context_actions', 'adjust_proposals_to_unhandled',
             title = _(u"Proposals to unhandled"),
             interface = IMeeting,
             permission = PERM_MANAGE_SYSTEM)
def adjust_proposals_to_unhandled(context, request, va, **kw):
    return """<li><a href="%s">%s</a></li>""" % (request.resource_url(context, 'adjust_proposals_to_unhandled'),
                                                 request.localizer.translate(va.title))

# @view_action('context_actions', 'rename_proposal_ids', title = _(u"Change Proposal IDs"),
#              interface = IAgendaItem)
# def rename_proposal_ids_action(context, request, va, **kw):
#     api = kw['api']
#     url = request.resource_url(context, 'rename_proposal_ids')
#     return """<li><a href="%s">%s</a></li>""" % (url,
#                                                  api.translate(va.title))

@view_action('context_actions', 'print_proposals',
             title = _(u"Print proposals"),
             interface = IAgendaItem)
def print_proposals_action(context, request, va, **kw):
    url = request.resource_url(context, '_print_proposals_form')
    return """<li><a href="%s">%s</a></li>""" % (url,
                                                 request.localizer.translate(va.title))

@view_action('context_actions', 'print_proposal',
             title = _(u"Print this proposal"),
             interface = IProposal)
def print_this_proposal_action(context, request, va, **kw):
    query = {'print': 'print', context.__name__: 'true'} #'true' is the marshalled True value
    ai = find_interface(context, IAgendaItem)
    url = request.resource_url(ai, '_print_proposals_form', query = query)
    return """<li><a href="%s">%s</a></li>""" % (url,
                                                 request.localizer.translate(va.title))

# def tag_adjust_proposal_order(response, important_tags, brains = True):
#     points = dict(zip(important_tags, [important_tags.index(x) for x in important_tags]))
#     maxpoint = len(important_tags) #Since index starts at 0
#     def _sorter(obj):
#         if brains:
#             return min([points.get(x, maxpoint) for x in obj['tags']])
#         else:
#             return min([points.get(x, maxpoint) for x in obj.get_tags()])
#     response['proposals'] = sorted(response['proposals'], key = _sorter)

# @view_action('proposals', 'sorting', interface = IAgendaItem)
# def proposal_sorting(context, request, va, **kw):
#     response = {'api': kw['api'], 'sort_tags': request.session.get('ai_sort_tags', None)}
#     return render("templates/proposal_sorting.pt", response, request = request)

#Override proposal listings
# @view_action('proposals', 'listing', interface = IAgendaItem)
# def proposal_listing_sfs(context, request, va, **kw):
#     if request.session.get('ai_sort_tags', False):
#         response = proposal_response(context, request, va, **kw)
#         tag_adjust_proposal_order(response, context.get_field_value('selectable_proposal_tags', ()))
#         return render('voteit.core:views/components/templates/proposals/listing.pt', response, request = request)
#     return proposal_listing(context, request, va, **kw)

# @view_config(name = '_set_ai_sorting_tags', context = IAgendaItem, permission = security.VIEW)
# def _set_ai_sorting(context, request):
#     if request.GET.get('sort', None) == 'tags':
#         request.session['ai_sort_tags'] = True
#     else:
#         request.session.pop('ai_sort_tags', None)
#     return HTTPFound(location = request.resource_url(context))
