from uuid import uuid4

from arche.models.evolver import BaseEvolver
from BTrees.OIBTree import OIBTree
from BTrees.OOBTree import OOBTree
from BTrees.OOBTree import OOSet
from persistent import Persistent
from zope.interface import implementer
from zope.component import adapter
from pyramid.traversal import find_interface

from voteit.core.models.interfaces import IAgendaItem
from voteit.core.models.interfaces import IMeeting
from voteit.core.models.interfaces import IProposal
from voteit.core.models.proposal_ids import ProposalIds

from sfs_ga.evolve import VERSION
from sfs_ga.interfaces import IMeetingDelegation
from sfs_ga.interfaces import IMeetingDelegations
from sfs_ga.interfaces import IProposalSupporters


@implementer(IMeetingDelegations)
@adapter(IMeeting)
class MeetingDelegations(object):
    """ See .interfaces.IMeetingDelegations """

    def __init__(self, context):
        self.context = context
        if not hasattr(self.context, '__delegations__'):
            self.context.__delegations__ = OOBTree()

    def new(self):
        name = unicode(uuid4())
        self.context.__delegations__[name] = MeetingDelegation(name)
        return name

    def get_delegation_for(self, userid):
        for delegation in self.values():
            if userid in delegation.members:
                return delegation

    def get(self, name, default = None):
        return self.context.__delegations__.get(name, default)

    def __getitem__(self, name):
        return self.context.__delegations__[name]

    def __delitem__(self, name):
        del self.context.__delegations__[name]

    def __len__(self):
        return len(self.context.__delegations__)

    def keys(self):
        return self.context.__delegations__.keys()

    def __iter__(self):
        return iter(self.keys())

    def values(self):
        return self.context.__delegations__.values()

    def items(self):
        return self.context.__delegations__.items()

    def __nonzero__(self):
        """ This object should be "true" even if it has no content. """
        return True


@implementer(IMeetingDelegation)
class MeetingDelegation(Persistent):
    title = ""
    description = ""
    vote_count = 0

    def __init__(self, name, title = u"", description = u"", vote_count = 0,
                 leaders = (), members = ()):
        self.name = name
        self.title = title
        self.description = description
        self.vote_count = vote_count
        self.leaders = OOSet(leaders)
        self.members = OOSet(members)
        #Important: attribute must match leaders/members attributes with "pn_" in front!
        self.pn_leaders = OOSet()
        self.pn_members = OOSet()
        self.voters = OIBTree()


@implementer(IProposalSupporters)
@adapter(IProposal)
class ProposalSupporters(object):

    def __init__(self, context):
        self.context = context

    def __call__(self):
        return self.context.get_field_value('proposal_supporters', ())

    def add(self, name):
        if not self.context.get_field_value('proposal_supporters', None):
            self.context.set_field_value('proposal_supporters', OOSet())
        delegations = self.context.get_field_value('proposal_supporters')
        delegations.add(name)

    def remove(self, name):
        supporters = self.context.get_field_value('proposal_supporters', ())
        if name in supporters:
            supporters.remove(name)


class AgendaItemBasedProposalIds(ProposalIds):
    """ Count agenda items instead of userids. """

    def add(self, proposal):
        ai = find_interface(proposal, IAgendaItem)
        aid_int = self.proposal_ids.get(ai.__name__, 0) + 1
        tag_name = ai.get_field_value('proposal_hashtag', None)
        if not tag_name:
            tag_name = ai.__name__
        aid = "%s-%s" % (tag_name, aid_int)
        proposal.set_field_appstruct({'aid': aid, 'aid_int': aid_int})
        self.proposal_ids[ai.__name__] = aid_int


def _get_proposal_hashtag(self):
    return self.get_field_value('proposal_hashtag', '')

def _set_proposal_hashtag(self, value):
    self.set_field_value('proposal_hashtag', value)


class SFSGAEvolver(BaseEvolver):
    name = 'sfs_ga'
    sw_version = VERSION
    initial_db_version = 0


def includeme(config):
    config.registry.registerAdapter(MeetingDelegations)
    config.registry.registerAdapter(ProposalSupporters)
    config.registry.registerAdapter(AgendaItemBasedProposalIds)
    config.add_evolver(SFSGAEvolver)

    from voteit.core.models.agenda_item import AgendaItem
    #Make sure proposal_hashtag property exist for agenda items
    AgendaItem.proposal_hashtag = property(_get_proposal_hashtag, _set_proposal_hashtag)
