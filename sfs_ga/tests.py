import unittest

from colander import Invalid
from pyramid import testing
from pyramid.httpexceptions import HTTPForbidden
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject
from voteit.core.models.meeting import Meeting
from voteit.core.models.proposal import Proposal
from voteit.core.models.vote import Vote
from voteit.core.models.user import User
from voteit.core.testing_helpers import bootstrap_and_fixture
from voteit.core.testing_helpers import active_poll_fixture
from voteit.core.security import unrestricted_wf_transition_to

from .interfaces import IMeetingDelegation
from .interfaces import IMeetingDelegations
from .interfaces import IProposalSupporters


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
        self.config.include('voteit.core.models.js_util')
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

    def test_set_voter_role(self):
        meeting = _active_poll_fixture(self.config)
        request = testing.DummyRequest()
        obj = self._cut(meeting, request)
        self.assertEqual(obj.api.meeting.get_groups('a'), ())
        obj.set_voter_role('a', True)
        self.assertEqual(obj.api.meeting.get_groups('a'), ('role:Voter', 'role:Viewer'))
        obj.set_voter_role('a', False)
        self.assertEqual(obj.api.meeting.get_groups('a'), ('role:Viewer',))


class MultiplyVotesSubscriberTests(unittest.TestCase):

    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request = request)

    def tearDown(self):
        testing.tearDown()

    def test_vote_multiplies_no_extra_votes(self):
        meeting = _active_poll_fixture(self.config)
        _delegation_fixture(self.config, meeting)
        self.config.testing_securitypolicy(userid='mr_tester')
        poll = meeting['ai']['poll']
        vote = Vote(creators = ['mr_tester'], notify = False)
        vote.set_vote_data('John Doe for pressy', notify = False)
        poll['mr_tester'] = vote
        self.assertEqual(len(poll.get_content()), 1)

    def test_vote_multiplies_3_votes(self):
        meeting = _active_poll_fixture(self.config)
        _delegation_fixture(self.config, meeting)
        self.config.testing_securitypolicy(userid='mrs_tester')
        poll = meeting['ai']['poll']
        vote = Vote(creators = ['mrs_tester'], notify = False )
        vote.set_vote_data('Jane Doe for pressy', notify = False)
        poll['mrs_tester'] = vote
        votes = poll.get_content()
        self.assertEqual(len(votes), 3)
        self.assertEqual(votes[0].get_vote_data(), 'Jane Doe for pressy')
        self.assertEqual(votes[0].get_vote_data(), votes[1].get_vote_data(), votes[2].get_vote_data())
    
    def test_all_votes_change_on_update(self):
        meeting = _active_poll_fixture(self.config)
        _delegation_fixture(self.config, meeting)
        self.config.testing_securitypolicy(userid='mrs_tester')
        poll = meeting['ai']['poll']
        vote = Vote(creators = ['mrs_tester'], notify = False )
        vote.set_vote_data('Jane Doe for pressy', notify = False)
        poll['mrs_tester'] = vote
        vote.set_vote_data('Mrs tester for pressy instead')
        votes = poll.get_content()
        self.assertEqual(votes[0].get_vote_data(), 'Mrs tester for pressy instead')
        self.assertEqual(votes[0].get_vote_data(), votes[1].get_vote_data(), votes[2].get_vote_data())


class SingleDelegationValidatorTests(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from .schemas import SingleDelegationValidator
        return SingleDelegationValidator

    def test_validator_no_other_existing_groups(self):
        meeting = _active_poll_fixture(self.config)
        root = meeting.__parent__
        root['users']['jeff'] = User()
        delegation = _delegation_fixture(self.config, meeting)
        request = testing.DummyRequest(params = {'delegation': delegation.name})
        obj = self._cut(meeting, request)
        self.assertEqual(obj(None, 'jeff'), None)

    def test_validator_exists_in_other_group(self):
        meeting = _active_poll_fixture(self.config)
        root = meeting.__parent__
        root['users']['jonas'] = User()
        delegation1 = _delegation_fixture(self.config, meeting)
        delegation2 = _delegation_fixture(self.config, meeting)
        delegation1.members.add('jonas')
        request = testing.DummyRequest(params = {'delegation': delegation2.name})
        obj = self._cut(meeting, request)
        self.assertRaises(Invalid, obj, None, 'jonas')



class ProposalSupportersTests(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from .models import ProposalSupporters
        return ProposalSupporters

    def test_verify_class(self):
        self.failUnless(verifyClass(IProposalSupporters, self._cut))

    def test_verify_obj(self):
        context = testing.DummyModel()
        self.failUnless(verifyObject(IProposalSupporters, self._cut(context)))

    def test_integration(self):
        self.config.include('voteit.core.models.fanstatic_resources')
        self.config.include('voteit.core.models.js_util')
        self.config.include('sfs_ga')
        prop = Proposal()
        self.failUnless(self.config.registry.queryAdapter(prop, IProposalSupporters))



def _active_poll_fixture(config):
    config.testing_securitypolicy(userid='mrs_tester')
    config.include('voteit.core.models.fanstatic_resources')
    config.include('voteit.core.models.js_util')
    config.include('voteit.core.plugins.majority_poll')
    config.include('voteit.core.testing_helpers.register_workflows')
    config.include('voteit.core.testing_helpers.register_catalog')
    root = active_poll_fixture(config)
    poll = root['meeting']['ai']['poll']
    poll.set_field_value('poll_plugin', 'majority_poll')
    unrestricted_wf_transition_to(poll, 'ongoing')
    config.include('voteit.core.testing_helpers.register_security_policies')
    config.include('sfs_ga')
    return root['meeting']

def _delegation_fixture(config, meeting):
    delegations = config.registry.getAdapter(meeting, IMeetingDelegations)
    name = delegations.new()
    delegation = delegations[name]
    delegation.title = u"Hello worlders"
    delegation.members.add('mrs_tester')
    delegation.voters['mrs_tester'] = 3
    delegation.vote_count = 3
    return delegation

