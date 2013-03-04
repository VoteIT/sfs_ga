import deform
from betahaus.pyracont.factories import createSchema
from pyramid.decorator import reify
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPForbidden
from voteit.core.views.base_edit import BaseEdit
from voteit.core.models.interfaces import IMeeting
from voteit.core.schemas.common import add_csrf_token
from voteit.core.models.schemas import button_cancel
from voteit.core.models.schemas import button_save
from voteit.core import security

from .interfaces import IMeetingDelegations
from . import SFS_TSF as _


class EditMeetingDelegationsView(BaseEdit):

    @reify
    def meeting_delegations(self):
        return self.request.registry.getAdapter(self.api.meeting, IMeetingDelegations)

    def check_ongoing_poll(self):
        """ Check if a poll is ongoing, and raise 403 error message if that's the case """
        #FIXME: Implement
        return

    @view_config(name = "meeting_delegations", context = IMeeting, renderer = "templates/meeting_delegations.pt")
    def meeting_delegations_view(self):
        self.response['delegations'] = self.meeting_delegations.values()
        return self.response

    @view_config(name = "add_new_delegation", context = IMeeting, permission = security.MODERATE_MEETING)
    def add_new_delegation(self):
        """ Add a new delegation and redirect to edit view.
        """
        name = self.meeting_delegations.new()
        url = self.request.resource_url(self.context, 'edit_delegation', query = {'delegation': name})
        return HTTPFound(location = url)

    @view_config(name = "edit_delegation", context = IMeeting, permission = security.MODERATE_MEETING,
                 renderer = "voteit.core.views:templates/base_edit.pt")
    def edit_delegation(self):
        """ Edit delegation, for moderators.
        """
        delegation = self.meeting_delegations[self.request.GET.get('delegation')]
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
            delegation.leaders = appstruct['leaders']
            delegation.votes = appstruct['votes']
            self.api.flash_messages.add(_(u"Updated"))
            url = self.request.resource_url(self.context, 'meeting_delegations')
            return HTTPFound(location = url)
        if 'cancel' in self.request.POST:
            self.api.flash_messages.add(_(u"Canceled"))
            url = self.request.resource_url(self.context, 'meeting_delegations')
            return HTTPFound(location = url)
        appstruct = dict(
            title = delegation.title,
            leaders = delegation.leaders,
            votes = delegation.votes)
        self.response['form'] = form.render(appstruct = appstruct)
        return self.response

    @view_config(name = "manage_meeeting_delegation", context = IMeeting, permission = security.VIEW,
                 renderer = "templates/manage_delegation.pt")
    def manage_delegation(self):
        """ Manage delegation members and votes, for delegation leads.
            Note that delegation lead isn't a perm and has to be checked in this view.
        """
        #FIXME: Make sure no poll is ongoing                
        self.check_ongoing_poll()
        #FIXME: When we can use dynamic permissions, update perms here
        delegation = self.meeting_delegations[self.request.GET.get('delegation')]
        if not self.api.userid in delegation.leaders:
            raise HTTPForbidden(_(u"Only delegation leads may distribute votes"))
        return self.response
