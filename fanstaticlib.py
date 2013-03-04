""" Fanstatic lib"""
from fanstatic import Library
from fanstatic import Resource

from voteit.core.fanstaticlib import voteit_main_css


fsf_ga_lib = Library('fsf_ga_lib', 'static')

fsf_styles = Resource(fsf_ga_lib, 'styles.css', depends=(voteit_main_css,))
