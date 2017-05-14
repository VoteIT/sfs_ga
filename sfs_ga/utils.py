from pyramid.renderers import render

from sfs_ga.interfaces import IMeetingDelegations


def _get_delegation_title(userid, request):
    try:
        cached_delegation_titles = request._cached_delegation_titles
    except AttributeError:
        cached_delegation_titles = request._cached_delegation_titles = {}
    try:
        return request._cached_delegation_titles[userid]
    except KeyError:
        delegations = IMeetingDelegations(request.meeting, None)
        if delegations is not None:
            delegation = delegations.get_delegation_for(userid)
            if delegation:
                cached_delegation_titles[userid] = delegation.title
            else:
                cached_delegation_titles[userid] = ""
    return cached_delegation_titles[userid]

def creators_info(request, creators, portrait = True, lookup = True, at = False, no_tag = False, no_userid = False):
    #FIXME: Respect no_userid
    if lookup == False:
        portrait = False #No portrait without lookup
    users = []
    delegations = {}
    for userid in creators:
        if lookup:
            user = request.root['users'].get(userid, None)
            if user:
                users.append(user)
                #Also fetch delegations in this case
                delegations[userid] = _get_delegation_title(userid, request)
        else:
            users.append(userid)
    response = {'users': users,
                'portrait': portrait,
                'lookup': lookup,
                'at': at,
                'no_tag': no_tag,
                'delegations': delegations}
    return render('sfs_ga:templates/creators_info.pt', response, request = request)

def includeme(config):
    #SFS version of creators_info
    config.add_request_method(callable = creators_info, name = 'creators_info')
