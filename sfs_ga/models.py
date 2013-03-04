from uuid import uuid4

from BTrees.OOBTree import OOBTree
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

    def __init__(self, name, title = u"", votes = 0, leaders = ()):
        self.name = name
        self.title = title
        self.votes = votes
        self.leaders = leaders
        self.__members__ = OOBTree()

    def _get_votes(self):
        return getattr(self, '__votes__', 0)
    def _set_votes(self, value):
        self.__votes__ = int(value)
    votes = property(_get_votes, _set_votes)

    def _get_leaders(self):
        return getattr(self, '__leaders__', ())
    def _set_leaders(self, value):
        self.__leaders__ = tuple(value)
    leaders = property(_get_leaders, _set_leaders)

    def _get_members(self):
        return self.__members__
    def _set_members(self, values):
        self.__members__ = tuple(values) #Should be a list of dicts
    members = property(_get_members, _set_members)
