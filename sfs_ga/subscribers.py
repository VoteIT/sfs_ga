from uuid import uuid4

from pyramid.events import subscriber
from pyramid.traversal import find_interface
from pyramid.threadlocal import get_current_request
from pyramid.traversal import find_root
from arche.interfaces import IObjectAddedEvent
from arche.interfaces import IObjectUpdatedEvent
from voteit.core.models.interfaces import IVote
from voteit.core.models.interfaces import IProposal
from voteit.core.models.interfaces import IMeeting
from .interfaces import IMeetingDelegations


@subscriber([IVote, IObjectAddedEvent])
@subscriber([IVote, IObjectUpdatedEvent])
def multiply_votes(obj, event):
    """ This subscriber multiplies votes for delegation members that have received several votes.
        Technically a single member might be part of several delegations, but this will hardly be the case.
        Nevertheless, we need to tace care of any eventualities.
    """
    request = get_current_request()
    userid = request.authenticated_userid
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
    vote_data = poll[userid].get_vote_data() #Just to make sure, get from the initial one

    if IObjectAddedEvent.providedBy(event):
        Vote = poll_plugin.get_vote_class()
        assert IVote.implementedBy(Vote)
        for i in range(vote_counter):
            name = unicode(uuid4())
            vote = Vote(creators = [userid])
            vote.set_vote_data(vote_data, notify = False)
            poll[name] = vote
            
    if IObjectUpdatedEvent.providedBy(event):
        for vote in poll.get_content(iface = IVote):
            if vote.creators[0] != userid:
                continue
            if vote.__name__ == userid:
                continue
            vote.set_vote_data(vote_data)


@subscriber([IProposal, IObjectAddedEvent])
def adjust_section_hashtag(obj, event):
    extra_hashtag = obj.field_storage.pop('extra_hashtag', None)
    #__nothing__ is a valid value, but is for when a user actively chose not to use a hashtag
    if extra_hashtag in (None, '__nothing__', ''):
        return
    if extra_hashtag not in obj.tags:
        prop_text = "%s\n#%s" % (obj.text, extra_hashtag)
        obj.update(text = prop_text)
