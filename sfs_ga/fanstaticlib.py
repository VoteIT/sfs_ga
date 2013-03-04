""" Fanstatic lib"""
from fanstatic import Library
from fanstatic import Resource

from voteit.core.fanstaticlib import voteit_main_css


sfs_ga_lib = Library('sfs_ga_lib', 'static')

sfs_styles = Resource(sfs_ga_lib, 'styles.css', depends=(voteit_main_css,))
