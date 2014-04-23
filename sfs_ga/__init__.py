import logging

from pyramid.i18n import TranslationStringFactory
from voteit.core.models.interfaces import IJSUtil


PROJECTNAME = 'sfs_ga'
SFS_TSF = TranslationStringFactory(PROJECTNAME)

log = logging.getLogger(__name__)


def includeme(config):
    config.commit() #Since we override other voteit views
    config.scan(PROJECTNAME)
    config.add_translation_dirs('%s:locale/' % PROJECTNAME)
    cache_ttl_seconds = int(config.registry.settings.get('cache_ttl_seconds', 7200))
    config.add_static_view('sfs_ga_static', '%s:static' % PROJECTNAME, cache_max_age = cache_ttl_seconds)

    #Register fanstatic resources
    from voteit.core.models.interfaces import IFanstaticResources
    from .fanstaticlib import sfs_styles
    from .fanstaticlib import sfs_delegations
    util = config.registry.queryUtility(IFanstaticResources)
    if util:
        util.add('sfs_styles', sfs_styles)
        util.add('sfs_delegations', sfs_delegations)
    else:
        log.warn("IFanstaticResources util not found, this might be okay if you're just running a test")

    #Register components
    config.include('sfs_ga.models')

    #Register js translations
    _ = SFS_TSF
    js_util = config.registry.queryUtility(IJSUtil)
    if js_util:
        js_util.add_translations(
            supporters = _(u"Supporters"),
            )
    else:
        log.warn("IJSUtil util not found, this might be okay if you're just running a test")

    #Remove like action
    from betahaus.viewcomponent import IViewGroup
    vg_user_tags = config.registry.queryUtility(IViewGroup, name = 'user_tags')
    if vg_user_tags and 'like' in vg_user_tags:
        del vg_user_tags['like']
