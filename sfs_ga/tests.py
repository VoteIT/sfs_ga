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
from voteit.core.models.interfaces import IProposalIds

from sfs_ga.interfaces import IMeetingDelegation
from sfs_ga.interfaces import IMeetingDelegations
from sfs_ga.interfaces import IProposalSupporters
from voteit.irl.models.interfaces import IParticipantNumbers


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
        self.config.include('arche.testing')
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


class MeetingDelegationsViewTests(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include('pyramid_chameleon')

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from .views import MeetingDelegationsView
        return MeetingDelegationsView

    def test_meeting_delegations(self):
        meeting = _active_poll_fixture(self.config)
        request = testing.DummyRequest()
        request.meeting = meeting
        obj = self._cut(meeting, request)
        self.failUnless(IMeetingDelegations.providedBy(obj.meeting_delegations))

    def test_check_ongoing_poll_nothing_registered(self):
        from sfs_ga.views import _check_ongoing_poll
        self.config.include('arche.models.catalog')
        root = bootstrap_and_fixture(self.config)
        self.config.include('voteit.core.testing_helpers.register_workflows')
        root['meeting'] = Meeting()
        request = testing.DummyRequest()
        request.root = root
        request.meeting = root['meeting']
        obj = self._cut(root['meeting'], request)
        self.assertEqual(_check_ongoing_poll(obj), None)

    def test_check_ongoing_poll(self):
        from sfs_ga.views import _check_ongoing_poll
        meeting = _active_poll_fixture(self.config)
        request = testing.DummyRequest()
        request.meeting = meeting
        request.root = meeting.__parent__
        obj = self._cut(meeting, request)
        self.assertRaises(HTTPForbidden, _check_ongoing_poll, obj)

    def test_set_voter_role(self):
        meeting = _active_poll_fixture(self.config)
        request = testing.DummyRequest()
        request.meeting = meeting #Like VoteITs api
        obj = self._cut(meeting, request)
        self.assertEqual(meeting.local_roles.get('a', ()), ())
        obj.set_voter_role('a', True)
        self.assertEqual(meeting.local_roles.get('a'), frozenset(['role:Voter']))
        obj.set_voter_role('a', False)
        self.assertEqual(meeting.local_roles.get('a', ()), ())


class MultiplyVotesSubscriberTests(unittest.TestCase):

    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request = request)
        self.config.include('pyramid_chameleon')

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
        self.config.include('pyramid_chameleon')

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


class DelegationPNValidatorTests(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include('voteit.irl.models.participant_numbers')
        self.config.include('sfs_ga.models')

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from .schemas import DelegationPNValidator
        return DelegationPNValidator

    def _pn_fixture(self, meeting):
        pns = IParticipantNumbers(meeting)
        tickets = pns.new_tickets('jane_doe', 1, 10)
        pns.claim_ticket('a', pns.tickets[1].token)
        pns.claim_ticket('b', pns.tickets[2].token)
        pns.claim_ticket('c', pns.tickets[3].token)

    def test_no_other_numbers(self):
        meeting = Meeting()
        delegation = _delegation_fixture(self.config, meeting)
        obj = self._cut(meeting, delegation.name, 'members')
        try:
            obj(None, (1,2,3))
        except Invalid:
            self.fail("Invalid raised")

    def test_pn_in_other_delegation(self):
        meeting = Meeting()
        delegation_one = _delegation_fixture(self.config, meeting)
        delegation_one.pn_members.update([1,2,3])
        delegation_two = _delegation_fixture(self.config, meeting)
        obj = self._cut(meeting, delegation_two.name, 'members')
        try:
            obj(None, (4, 5, 6))
        except Invalid:
            self.fail("Invalid raised")
        self.assertRaises(Invalid, obj, None, (3,4,5))
        self.assertRaises(Invalid, obj, None, (1,))

    def test_userid_in_other_delegation(self):
        meeting = Meeting()
        self._pn_fixture(meeting)
        delegation_one = _delegation_fixture(self.config, meeting)
        delegation_one.members.update(['a', 'b', 'c'])
        delegation_two = _delegation_fixture(self.config, meeting)
        obj = self._cut(meeting, delegation_two.name, 'members')
        try:
            obj(None, (4, 5, 6))
        except Invalid:
            self.fail("Invalid raised")
        self.assertRaises(Invalid, obj, None, (3,4,5))
        self.assertRaises(Invalid, obj, None, (1,))


class DelegationPNIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp(request = testing.DummyRequest())
        self.config.include('voteit.irl.models.participant_numbers')
        self.config.include('sfs_ga.models')
        self.config.include('sfs_ga.subscribers')
        self.config.include('arche.models.flash_messages')

    def tearDown(self):
        testing.tearDown()

    def _pn_fixture(self, meeting):
        pns = IParticipantNumbers(meeting)
        tickets = pns.new_tickets('jane_doe', 1, 10)
        pns.claim_ticket('a', pns.tickets[1].token)
        pns.claim_ticket('b', pns.tickets[2].token)
        pns.claim_ticket('c', pns.tickets[3].token)

    def test_leaders_added_to_delegation_on_ticket_claim(self):
        meeting = Meeting()
        delegation = _delegation_fixture(self.config, meeting)
        delegation.pn_leaders.update([1,2])
        self._pn_fixture(meeting) #Also fires even when ticket claimed
        self.assertEqual(set(delegation.leaders), set(['a', 'b']))

    def test_members_added_to_delegation_on_ticket_claim(self):
        meeting = Meeting()
        delegation = _delegation_fixture(self.config, meeting)
        delegation.pn_members.update([1,2])
        self._pn_fixture(meeting) #Also fires even when ticket claimed
        self.assertEqual(set(delegation.members), set(['a', 'b', 'mrs_tester']))

    def test_existing_leaders_not_added(self):
        meeting = Meeting()
        delegation = _delegation_fixture(self.config, meeting)
        delegation.pn_leaders.update([1,2])
        delegation2 = _delegation_fixture(self.config, meeting)
        delegation2.leaders.update(['a'])
        self._pn_fixture(meeting) #Also fires even when ticket claimed
        self.assertEqual(set(delegation.leaders), set(['b']))

    def test_existing_members_not_added(self):
        meeting = Meeting()
        delegation = _delegation_fixture(self.config, meeting)
        delegation.pn_members.update([1,2])
        delegation2 = _delegation_fixture(self.config, meeting)
        delegation2.members.update(['a'])
        self._pn_fixture(meeting) #Also fires even when ticket claimed
        self.assertEqual(set(delegation.members), set(['b', 'mrs_tester']))


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
        self.config.include('arche.testing')
        self.config.include('sfs_ga')
        prop = Proposal()
        self.failUnless(self.config.registry.queryAdapter(prop, IProposalSupporters))


class AgendaItemBasedProposalIdsTests(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from .models import AgendaItemBasedProposalIds
        return AgendaItemBasedProposalIds

    def test_verify_class(self):
        self.failUnless(verifyClass(IProposalIds, self._cut))

    def test_verify_obj(self):
        self.failUnless(verifyObject(IProposalIds, self._cut(Meeting())))

    def test_component_integration(self):
        self.config.include('arche.testing')
        self.config.include('sfs_ga')
        meeting = Meeting()
        self.failUnless(self.config.registry.queryAdapter(meeting, IProposalIds))

    def test_add(self):
        self.config.include('pyramid_chameleon')
        meeting = _active_poll_fixture(self.config)
        obj = self._cut(meeting)
        obj.add(meeting['ai']['prop1'])
        obj.add(meeting['ai']['prop2'])
        self.assertEqual(meeting['ai']['prop1'].get_field_value('aid'), u"ai-1")
        self.assertEqual(obj.proposal_ids['ai'], 2)

    def test_integration(self):
        self.config.include('arche.testing')
        self.config.include('pyramid_chameleon')
        #It will be readded when active poll fixture is run, which is silly
        self.config.registry.acl.clear()
        self.config.include('voteit.core.models.proposal_ids')
        self.config.include('sfs_ga')
        meeting = _active_poll_fixture(self.config)
        obj = self._cut(meeting)
        self.assertEqual(obj.proposal_ids['ai'], 2)
        self.assertEqual(meeting['ai']['prop1'].get_field_value('aid'), u"ai-1")
        self.assertEqual(meeting['ai']['prop2'].get_field_value('aid'), u"ai-2")


def _active_poll_fixture(config):
    config.testing_securitypolicy(userid='mrs_tester')
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
