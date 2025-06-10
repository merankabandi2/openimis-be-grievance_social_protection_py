from django.test import TestCase

from core.test_helpers import create_test_interactive_user
from grievance_social_protection.access_control import GrievanceAccessControl
from grievance_social_protection.apps import TicketConfig
from grievance_social_protection.models import Ticket


class TicketQueryFilteringTest(TestCase):
    """Test ticket queryset filtering based on permissions"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_test_config()
        cls._create_test_users()
        cls._create_test_tickets()
    
    def setUp(self):
        # Reset config for each test
        self._setup_test_config()
    
    @classmethod
    def _setup_test_config(cls):
        """Set up test configuration"""
        config = {
            'grievance_types': [
                'public_category',
                {
                    'name': 'restricted_category',
                    'permissions': ['127002', '127003']
                },
                {
                    'name': 'sensitive_category',
                    'permissions': ['127006'],
                    'default_flags': ['sensitive']
                }
            ],
            'grievance_flags': [
                'urgent',
                {
                    'name': 'sensitive',
                    'permissions': ['127004', '127005']
                },
                {
                    'name': 'confidential',
                    'permissions': ['127006']
                }
            ]
        }
        
        # Process configuration
        TicketConfig._TicketConfig__process_unified_categories(config)
        TicketConfig._TicketConfig__process_unified_flags(config)
        TicketConfig._TicketConfig__load_config(config)
    
    @classmethod
    def _create_test_users(cls):
        """Create test users with different permission levels"""
        # User with all permissions
        cls.user_all_perms = create_test_interactive_user(username='user_all_perms', roles=[7])  # Admin role
        
        # User with limited permissions (only view tickets)
        cls.user_limited = create_test_interactive_user(username='user_limited', roles=[1])  # Basic role
        # Manually add specific permissions
        cls._add_permissions_to_user(cls.user_limited, ['127000', '127001'])  # View and create tickets
        
        # User with mixed permissions
        cls.user_mixed = create_test_interactive_user(username='user_mixed', roles=[1])  # Basic role
        cls._add_permissions_to_user(cls.user_mixed, ['127000', '127004'])  # View tickets and comments
    
    @classmethod
    def _add_permissions_to_user(cls, user, permission_codes):
        """Add specific permissions to a user"""
        if hasattr(user, 'i_user') and user.i_user:
            # Add to the user's rights through their role
            from core.models import Role, RoleRight, UserRole
            
            # Create a custom role for this user
            role = Role.objects.create(
                name=f"TestRole_{user.username}",
                is_system=0,
                is_blocked=False,
                audit_user_id=-1
            )
            
            # Add rights to the role
            for perm_code in permission_codes:
                RoleRight.objects.create(
                    role=role,
                    right_id=int(perm_code),
                    audit_user_id=-1
                )
            
            # Assign role to user
            UserRole.objects.create(
                user=user.i_user,
                role=role,
                audit_user_id=-1
            )
    
    @classmethod
    def _create_test_tickets(cls):
        """Create test tickets"""
        # Create tickets with user for history tracking
        cls.tickets = {}
        
        ticket = Ticket(
            title='Public ticket',
            category='public_category',
            flags='urgent',
            resolution='5,0'
        )
        ticket.save(user=cls.user_all_perms)
        cls.tickets['public'] = ticket
        
        ticket = Ticket(
            title='Restricted ticket',
            category='restricted_category',
            flags='urgent',
            resolution='5,0'
        )
        ticket.save(user=cls.user_all_perms)
        cls.tickets['restricted'] = ticket
        
        ticket = Ticket(
            title='Sensitive ticket',
            category='sensitive_category',
            flags='sensitive',
            resolution='5,0'
        )
        ticket.save(user=cls.user_all_perms)
        cls.tickets['sensitive'] = ticket
        
        ticket = Ticket(
            title='Public with confidential flag',
            category='public_category',
            flags='confidential',
            resolution='5,0'
        )
        ticket.save(user=cls.user_all_perms)
        cls.tickets['confidential'] = ticket
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test data"""
        # Get all ticket IDs before cleanup
        ticket_ids = [t.id for t in cls.tickets.values()]
        # Delete using a single query
        Ticket.objects.filter(id__in=ticket_ids).delete()
        super().tearDownClass()
    
    def test_filter_all_permissions(self):
        """Test filtering with all permissions"""
        # Admin user should see all tickets
        queryset = Ticket.objects.all()
        filtered = GrievanceAccessControl.filter_ticket_queryset(queryset, self.user_all_perms)
        
        # Should see all tickets
        ticket_ids = list(filtered.values_list('id', flat=True))
        for ticket in self.tickets.values():
            self.assertIn(ticket.id, ticket_ids)
    
    def test_filter_limited_permissions(self):
        """Test filtering with limited permissions"""
        # User with only basic permissions
        queryset = Ticket.objects.all()
        filtered = GrievanceAccessControl.filter_ticket_queryset(queryset, self.user_limited)
        
        ticket_ids = list(filtered.values_list('id', flat=True))
        
        # Should only see public category with urgent flag (no restricted permissions)
        self.assertIn(self.tickets['public'].id, ticket_ids)
        # Should NOT see these due to category/flag restrictions
        self.assertNotIn(self.tickets['restricted'].id, ticket_ids)  # Needs 127002/127003
        self.assertNotIn(self.tickets['sensitive'].id, ticket_ids)   # Needs 127006
        self.assertNotIn(self.tickets['confidential'].id, ticket_ids)  # Needs 127006 for flag
    
    def test_filter_no_config(self):
        """Test filtering when no config exists"""
        # Save and clear config
        original_cats = TicketConfig.processed_categories
        original_flags = TicketConfig.processed_flags
        TicketConfig.processed_categories = {}
        TicketConfig.processed_flags = {}
        
        try:
            queryset = Ticket.objects.all()
            filtered = GrievanceAccessControl.filter_ticket_queryset(queryset, self.user_limited)
            # Should return all when no config
            self.assertEqual(queryset.count(), filtered.count())
        finally:
            # Restore config
            TicketConfig.processed_categories = original_cats
            TicketConfig.processed_flags = original_flags
    
    def test_filter_mixed_flags(self):
        """Test filtering with mixed flag permissions"""
        # Create ticket with multiple flags
        mixed_ticket = Ticket(
            title='Mixed flags',
            category='public_category',
            flags='urgent sensitive',
            resolution='5,0'
        )
        mixed_ticket.save(user=self.user_mixed)
        
        try:
            queryset = Ticket.objects.all()
            filtered = GrievanceAccessControl.filter_ticket_queryset(queryset, self.user_mixed)
            
            ticket_ids = list(filtered.values_list('id', flat=True))
            # User has 127004 which allows sensitive flag
            self.assertIn(mixed_ticket.id, ticket_ids)
            # But not confidential flag (needs 127006)
            self.assertNotIn(self.tickets['confidential'].id, ticket_ids)
        finally:
            mixed_ticket.delete(username=self.user_mixed.username)
    
    def test_filter_hierarchical_categories(self):
        """Test filtering with hierarchical categories"""
        # Add parent-child categories
        config = {
            'grievance_types': [
                'public_category',
                {
                    'name': 'parent',
                    'permissions': ['127002'],
                    'children': ['child1', 'child2']
                }
            ],
            'grievance_flags': ['urgent']
        }
        
        # Process config
        TicketConfig._TicketConfig__process_unified_categories(config)
        TicketConfig._TicketConfig__load_config(config)
        
        # Create hierarchical tickets
        parent_ticket = Ticket(title='Parent', category='parent', resolution='5,0')
        parent_ticket.save(user=self.user_limited)
        child_ticket = Ticket(title='Child', category='parent|child1', resolution='5,0')
        child_ticket.save(user=self.user_limited)
        
        try:
            queryset = Ticket.objects.all()
            filtered = GrievanceAccessControl.filter_ticket_queryset(queryset, self.user_limited)
            
            ticket_ids = list(filtered.values_list('id', flat=True))
            # User doesn't have 127002, shouldn't see parent or child
            self.assertNotIn(parent_ticket.id, ticket_ids)
            self.assertNotIn(child_ticket.id, ticket_ids)
        finally:
            parent_ticket.delete(username=self.user_limited.username)
            child_ticket.delete(username=self.user_limited.username)