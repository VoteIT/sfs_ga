from uuid import uuid4

from BTrees.OIBTree import OIBTree
from BTrees.OOBTree import OOBTree
from BTrees.OOBTree import OOSet
from persistent import Persistent
from zope.interface import implements
from zope.component import adapts
from voteit.core.models.interfaces import IMeeting

from .interfaces import IMeetingDelegation
from .interfaces import IMeetingDelegations


class MeetingDelegations(object):
    """ See .interfaces.IMeetingDelegations """
    implements(IMeetingDelegations)
    adapts(IMeeting)

    def __init__(self, context):
        self.context = context
        if not hasattr(self.context, '__delegations__'):
            self.context.__delegations__ = OOBTree()

    def new(self):
        name = unicode(uuid4())
        self.context.__delegations__[name] = MeetingDelegation(name)
        return name

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


class MeetingDelegation(Persistent):
    implements(IMeetingDelegation)

    def __init__(self, name, title = u"", vote_count = 0, leaders = (), members = ()):
        self.name = name
        self.title = title
        self.vote_count = vote_count
        self.leaders = OOSet(leaders)
        self.members = OOSet(members)
        self.voters = OIBTree()
