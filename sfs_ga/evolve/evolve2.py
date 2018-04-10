from voteit.core.models.interfaces import IMeeting
from voteit.core.models.interfaces import IAgendaItem


def evolve(root):
    """ Change to voteit core's system of named hashtags
    """
    for meeting in root.values():
        if not IMeeting.providedBy(meeting):
            continue
        meeting.proposal_id_method = 'ai_hashtag'
        for ai in meeting.values():
            if not IAgendaItem.providedBy(ai):
                continue
            proposal_hashtag = ai.field_storage.pop('proposal_hashtag', None)
            if proposal_hashtag:
                ai.hashtag = proposal_hashtag
