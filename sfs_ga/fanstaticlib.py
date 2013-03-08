""" Fanstatic lib"""
from fanstatic import Library
from fanstatic import Resource

from voteit.core.fanstaticlib import voteit_main_css
from voteit.core.fanstaticlib import voteit_common_js

sfs_ga_lib = Library('sfs_ga_lib', 'static')

sfs_styles = Resource(sfs_ga_lib, 'styles.css', depends = (voteit_main_css,))
sfs_manage_delegation = Resource(sfs_ga_lib, 'manage_delegation.js', depends = (voteit_common_js,))
