import unittest

from pyramid import testing
from pyramid.httpexceptions import HTTPForbidden
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject
from voteit.core.models.meeting import Meeting
from voteit.core.testing_helpers import bootstrap_and_fixture
from voteit.core.testing_helpers import active_poll_fixture
from voteit.core.scripts.catalog import find_all_base_content
from voteit.core.models.catalog import index_object
from voteit.core.security import unrestricted_wf_transition_to

from .interfaces import IMeetingDelegation
from .interfaces import IMeetingDelegations


class MeetingDelegationsTests(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from .models import MeetingDelegations
        return MeetingDelegations

    def test_verify_class(self):
        self.failUnless(verifyClass(IMeetingDelegations, self._cut))

    def test_verify_obj(self):
        context = testing.DummyModel()
        self.failUnless(verifyObject(IMeetingDelegations, self._cut(context)))

    def test_integration(self):
        self.config.include('voteit.core.models.fanstatic_resources')
        self.config.include('sfs_ga')
        meeting = Meeting()
        self.failUnless(self.config.registry.queryAdapter(meeting, IMeetingDelegations))

    def test_new(self):
        context = Meeting()
        obj = self._cut(context)
        name = obj.new()
        self.assertIn(name, context.__delegations__)
        self.assertEqual(len(context.__delegations__), 1)

    def test_getitem(self):
        context = Meeting()
        obj = self._cut(context)
        name = obj.new()
        self.failUnless(obj[name])

    def test_delitem(self):
        context = Meeting()
        obj = self._cut(context)
        name = obj.new()
        del obj[name]
        self.assertEqual(len(obj), 0)


class MeetingDelegationTests(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from .models import MeetingDelegation
        return MeetingDelegation

    def test_verify_class(self):
        self.failUnless(verifyClass(IMeetingDelegation, self._cut))

    def test_verify_obj(self):
        context = testing.DummyModel()
        self.failUnless(verifyObject(IMeetingDelegation, self._cut(context)))


class EditMeetingDelegationsViewTests(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from .views import EditMeetingDelegationsView
        return EditMeetingDelegationsView

    def test_meeting_delegations(self):
        meeting = _active_poll_fixture(self.config)
        request = testing.DummyRequest()
        obj = self._cut(meeting, request)
        self.failUnless(IMeetingDelegations.providedBy(obj.meeting_delegations))

    def test_check_ongoing_poll_nothing_registered(self):
        root = bootstrap_and_fixture(self.config)
        self.config.include('voteit.core.models.fanstatic_resources')
        self.config.include('voteit.core.testing_helpers.register_workflows')
        root['meeting'] = Meeting()
        request = testing.DummyRequest()
        obj = self._cut(root['meeting'], request)
        self.assertEqual(obj.check_ongoing_poll(), None)

    def test_check_ongoing_poll(self):
        meeting = _active_poll_fixture(self.config)
        request = testing.DummyRequest()
        obj = self._cut(meeting, request)
        self.assertRaises(HTTPForbidden, obj.check_ongoing_poll)


def _active_poll_fixture(config):
    config.testing_securitypolicy(userid='mrs_tester')
    config.include('voteit.core.models.fanstatic_resources')
    config.include('voteit.core.testing_helpers.register_workflows')
    config.include('voteit.core.testing_helpers.register_catalog')
    root = active_poll_fixture(config)
    unrestricted_wf_transition_to(root['meeting']['ai']['poll'], 'ongoing')
    config.include('voteit.core.testing_helpers.register_security_policies')
    config.include('sfs_ga')
    #for obj in find_all_base_content(root):
    #    index_object(root.catalog, obj)
    return root['meeting']

