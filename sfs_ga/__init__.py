from pyramid.i18n import TranslationStringFactory


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
    util = config.registry.getUtility(IFanstaticResources)
    util.add('sfs_styles', sfs_styles)
