import unittest

from pyramid import testing
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject
from voteit.core.models.meeting import Meeting

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


