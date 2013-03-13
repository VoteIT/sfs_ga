from uuid import uuid4

from pyramid.events import subscriber
from pyramid.traversal import find_interface
from pyramid.traversal import find_root
from pyramid.traversal import resource_path
from pyramid.threadlocal import get_current_request
from pyramid.security import authenticated_userid
from repoze.folder.interfaces import IObjectAddedEvent
from voteit.core.models.interfaces import IVote
from voteit.core.interfaces import IObjectUpdatedEvent
from voteit.core.models.interfaces import IMeeting
from voteit.core.models.catalog import resolve_catalog_docid

from .interfaces import IMeetingDelegations


@subscriber([IVote, IObjectAddedEvent])
@subscriber([IVote, IObjectUpdatedEvent])
def multiply_votes(obj, event):
    """ This subscriber multiplies votes for delegation members that have received several votes.
        Technically a single member might be part of several delegations, but this will hardly be the case.
        Nevertheless, we need to tace care of any eventualities.
    """
    request = get_current_request()
    userid = authenticated_userid(request)
    #Only preform this functon on the inital vote object
    if userid != obj.__name__:
        return
    meeting = find_interface(obj, IMeeting)
    delegations = request.registry.getAdapter(meeting, IMeetingDelegations)
    vote_counter = -1 #Since the current vote was added already
    for delegation in delegations.values():
        vote_counter += delegation.voters.get(userid, 0)
    if not vote_counter > 0:
        return
    
    poll = obj.__parent__
    poll_plugin = poll.get_poll_plugin()
    vote_data = poll[userid].get_vote_data()

    if IObjectAddedEvent.providedBy(event):
        Vote = poll_plugin.get_vote_class()
        assert IVote.implementedBy(Vote)
        for i in range(vote_counter):
            name = unicode(uuid4())
            vote = Vote(creators = [userid])
            vote.set_vote_data(vote_data, notify = False)
            poll[name] = vote
            
    if IObjectUpdatedEvent.providedBy(event):
        root = find_root(obj)
        path = resource_path(poll)
        count, docids = root.catalog.search(path = path,
                            content_type = 'Vote',
                            creators = (userid,))
        assert count == vote_counter + 1
        for docid in docids:
            vote = resolve_catalog_docid(root.catalog, root, docid)
            if vote.__name__ == userid:
                continue
            vote.set_vote_data(vote_data)
