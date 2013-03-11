from zope.interface import Attribute
from zope.interface import Interface


class IMeetingDelegations(Interface):
    """ An adapter that handles meeting delegations. Adapts a meeting.
        Implements a dict-like interface to handle MeetingDelegation objects.
    """

    def new():
        """ New meeting delegation. Returns id. """


class IMeetingDelegation(Interface):
    """ A meeting delegation. Handled by IMeetingDelegations adapter.
    """
    name = Attribute("Name of the interface. Used to fetch this object from the IMeetingDelegations adapter.")
    title = Attribute("Title of delegation")
    vote_count = Attribute("Total number of votes for this delegation. Set by moderator.")
    leaders = Attribute("Leaders who're allowed to manage members and votes.")
    members = Attribute("Members. You need to be a member to be able to have votes.")
    voters = Attribute("""
        Voters - distribution of votes where key is userid and value
        is an int of number of votes. Can be 0.""")

    def __init__(name, title = u"", vote_count = 0, leaders = (), members = ()):
        """ Constructor, normally not passed any values within this app. """
