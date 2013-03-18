from pyramid.i18n import TranslationStringFactory
from voteit.core.models.interfaces import IJSUtil


PROJECTNAME = 'sfs_ga'
SFS_TSF = TranslationStringFactory(PROJECTNAME)


def includeme(config):
    config.scan(PROJECTNAME)
    config.add_translation_dirs('%s:locale/' % PROJECTNAME)
    cache_ttl_seconds = int(config.registry.settings.get('cache_ttl_seconds', 7200))
    config.add_static_view('sfs_ga_static', '%s:static' % PROJECTNAME, cache_max_age = cache_ttl_seconds)

    #Register fanstatic resources
    from voteit.core.models.interfaces import IFanstaticResources
    from .fanstaticlib import sfs_styles
    from .fanstaticlib import sfs_delegations
    util = config.registry.getUtility(IFanstaticResources)
    util.add('sfs_styles', sfs_styles)
    util.add('sfs_delegations', sfs_delegations)

    #Register components
    from .models import MeetingDelegations
    config.registry.registerAdapter(MeetingDelegations)
    from .models import ProposalSupporters
    config.registry.registerAdapter(ProposalSupporters)

    #Register js translations
    _ = SFS_TSF
    js_util = config.registry.getUtility(IJSUtil)
    js_util.add_translations(
        supporters = _(u"Supporters"),
        )
