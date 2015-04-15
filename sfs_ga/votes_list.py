#FIXME: Refactor if needed

# from pyramid.httpexceptions import HTTPForbidden
# from betahaus.viewcomponent.interfaces import IViewGroup
# from betahaus.viewcomponent.models import ViewAction
# from voteit.core.models.interfaces import IPoll
# from voteit.core.views.base_view import BaseView
# from voteit.core import security
# 
# from . import SFS_TSF as _
# 
# #Note: These functions aren't ment to be maintained or included by default even in SFS!
# 
# 
# class VotesListView(BaseView):
# 
#     def __call__(self):
#         if not self.api.show_moderator_actions:
#             return HTTPForbidden()
#         vote_counter = {}
#         votes = []
#         for vote in self.context.get_all_votes():
#             userid = vote.creators[0]
#             if userid == vote.__name__:
#                 votes.append(vote)
#             if userid not in vote_counter:
#                 vote_counter[userid] = 0
#             vote_counter[userid] += 1
#         
#         
#         self.response['votes'] = votes
#         self.response['vote_counter'] = vote_counter
#         return self.response
# 
# 
# def cogwheel_votes_list_link(context, request, va, **kw):
#     if context.get_workflow_state() != u"closed" or context.poll_plugin_name not in ('schulze_stv', 'schulze_pr'):
#         return u""
#     api = kw['api']
#     return "<li><a href='%s'>%s</a></li>" % (request.resource_url(context, '_schulze_votes_list'), api.translate(va.title))
# 
# def includeme(config):
#     vg = config.registry.getUtility(IViewGroup, name = u"context_actions")
#     va =  ViewAction(cogwheel_votes_list_link, 'cogwheel_schulze_votes_list_link', title = _(u"Schulze votes list"), interface = IPoll)
#     vg.add(va)
#     config.add_view(VotesListView, '_schulze_votes_list', context = IPoll, permission = security.VIEW,
#                     renderer = 'templates/votes_list.pt')
