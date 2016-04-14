import logging

from pyramid.i18n import TranslationStringFactory
from voteit.core.models.interfaces import IJSUtil


PROJECTNAME = 'sfs_ga'
SFS_TSF = _ = TranslationStringFactory(PROJECTNAME)

log = logging.getLogger(__name__)


def includeme(config):
    config.commit() #Since we override other voteit views
    config.add_translation_dirs('%s:locale/' % PROJECTNAME)
    cache_max_age = int(config.registry.settings.get('arche.cache_max_age', 60*60*24))
    config.add_static_view('sfs_ga_static', '%s:static' % PROJECTNAME, cache_max_age = cache_max_age)

    config.scan(PROJECTNAME)
    config.include('.fanstaticlib')
    config.include('.models')
    config.include('.schemas')
    config.include('.utils')

    #Register js translations
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
