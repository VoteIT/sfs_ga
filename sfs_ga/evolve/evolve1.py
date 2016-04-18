
def evolve(root):
    from voteit.core.models.interfaces import IMeeting
    from BTrees.OOBTree import OOSet
    from sfs_ga.interfaces import IMeetingDelegations

    for obj in root.values():
        if not IMeeting.providedBy(obj):
            continue
        delegations = IMeetingDelegations(obj)
        for delegation in delegations.values():
            for attr in ('pn_leaders', 'pn_members'):
                if not hasattr(delegation, attr):
                    setattr(delegation, attr, OOSet())
