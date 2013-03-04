from zope.interface import Attribute
from zope.interface import Interface


class IMeetingDelegations(Interface):
    """ An adapter that handles meeting delegations. Adapts a meeting.
    """


class IMeetingDelegation(Interface):
    """ A meeting delegation. Handled by IMeetingDelegations adapter.
    """
    