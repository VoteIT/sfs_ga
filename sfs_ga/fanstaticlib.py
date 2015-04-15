from arche.interfaces import IViewInitializedEvent
from arche.interfaces import IBaseView
from fanstatic import Library
from fanstatic import Resource

from voteit.core.fanstaticlib import voteit_main_css
from arche.fanstatic_lib import common_js
#from voteit.core.fanstaticlib import voteit_common_js

sfs_ga_lib = Library('sfs_ga_lib', 'static')

sfs_styles = Resource(sfs_ga_lib, 'styles.css', depends = (voteit_main_css,))
sfs_manage_delegation = Resource(sfs_ga_lib, 'manage_delegation.js', depends = (common_js,))
sfs_delegations = Resource(sfs_ga_lib, 'delegations.js', depends = ())


def need_sfs(view, event):
    """ Load generic sfs resources
    """
    if view.request.meeting:
        sfs_styles.need()

def includeme(config):
    config.add_subscriber(need_sfs, [IBaseView, IViewInitializedEvent])
