import json
from django.core.exceptions import ValidationError
from django.test import TestCase

from core.test_helpers import LogInHelper, create_test_interactive_user
from core.models import Role, RoleRight, UserRole
from grievance_social_protection.services import TicketService
from grievance_social_protection.apps import TicketConfig
from grievance_social_protection.models import Ticket


class TicketServicePermissionsTest(TestCase):
    """Test permission-based access control in TicketService"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_test_config()
        cls._create_test_users()
    
    def setUp(self):
        # Reset processed data before each test
        TicketConfig.processed_categories = {}
        TicketConfig.processed_flags = {}
        self._setup_test_config()
    
    @classmethod
    def _setup_test_config(cls):
        """Set up test configuration"""
        config = {
            'grievance_types': [
                'open_category',
                {
                    'name': 'restricted_category',
                    'priority': 'High',
                    'permissions': ['127001', '127002'],
                    'default_flags': ['urgent']
                }
            ],
            'grievance_flags': [
                'public',
                {
                    'name': 'sensitive',
                    'priority': 'Critical',
                    'permissions': ['127004', '127005']
                },
                {
                    'name': 'urgent',
                    'priority': 'High'
                }
            ],
            'resolution_times': '5,0'
        }
        
        # Process configuration
        TicketConfig._TicketConfig__process_unified_categories(config)
        TicketConfig._TicketConfig__process_unified_flags(config)
        TicketConfig._TicketConfig__load_config(config)
    
    @classmethod
    def _create_test_users(cls):
        """Create test users with different permission levels"""
        # User with permissions for restricted category
        cls.user_with_perms = create_test_interactive_user(username='user_with_perms', roles=[1])
        cls._add_permissions_to_user(cls.user_with_perms, ['127001', '127002'])
        
        # User without permissions
        cls.user_no_perms = create_test_interactive_user(username='user_no_perms', roles=[1])
        
        # User with flag permissions
        cls.user_flag_perms = create_test_interactive_user(username='user_flag_perms', roles=[1])
        cls._add_permissions_to_user(cls.user_flag_perms, ['127004', '127005'])
        
        # Anonymous-like user (no permissions)
        cls.user_anon = create_test_interactive_user(username='user_anon', roles=[1])
    
    @classmethod
    def _add_permissions_to_user(cls, user, permission_codes):
        """Add specific permissions to a user"""
        if hasattr(user, 'i_user') and user.i_user:
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
    
    def test_create_with_permissions_allowed(self):
        """Test ticket creation when user has required permissions"""
        service = TicketService(self.user_with_perms)
        
        obj_data = {
            'category': 'restricted_category',
            'title': 'Test with permissions',
            'resolution': '5,0'
        }
        
        result = service.create(obj_data)
        
        # Verify success
        self.assertTrue(result.get('success', False), f"Creation failed: {result}")
        self.assertIsNotNone(result.get('data', {}).get('uuid'))
        
        # Check ticket was created with correct values
        ticket = Ticket.objects.get(uuid=result['data']['uuid'])
        self.assertEqual(ticket.category, 'restricted_category')
        self.assertEqual(ticket.flags, 'urgent')  # Default flag applied
        self.assertEqual(ticket.priority, 'High')  # Category priority
        
        # Clean up
        ticket.delete(username=self.user_with_perms.username)
    
    def test_create_with_permissions_denied(self):
        """Test ticket creation fails when user lacks permissions"""
        service = TicketService(self.user_no_perms)
        
        obj_data = {
            'category': 'restricted_category',
            'title': 'Test without permissions',
            'resolution': '5,0'
        }
        
        # Service converts PermissionDenied to ValidationError
        with self.assertRaises(ValidationError) as cm:
            service.create(obj_data)
        
        self.assertIn('restricted_category', str(cm.exception))
    
    def test_flag_permissions(self):
        """Test flag permission checking"""
        # User without sensitive flag permissions
        service = TicketService(self.user_no_perms)
        
        obj_data = {
            'category': 'open_category',
            'title': 'Test flag permissions',
            'flags': 'public sensitive',
            'resolution': '5,0'
        }
        
        # Should raise ValidationError for sensitive flag
        with self.assertRaises(ValidationError) as cm:
            service.create(obj_data)
        
        self.assertIn('sensitive', str(cm.exception))
        
        # User with flag permissions should succeed
        service_with_flag_perms = TicketService(self.user_flag_perms)
        result = service_with_flag_perms.create(obj_data)
        
        self.assertTrue(result.get('success', False))
        if result.get('success'):
            ticket = Ticket.objects.get(uuid=result['data']['uuid'])
            self.assertIn('sensitive', ticket.flags)
            ticket.delete(username=self.user_flag_perms.username)
    
    def test_open_category_no_permissions_required(self):
        """Test that open categories don't require permissions"""
        # User with no special permissions
        service = TicketService(self.user_no_perms)
        
        obj_data = {
            'category': 'open_category',
            'title': 'Test open category',
            'resolution': '5,0'
        }
        
        result = service.create(obj_data)
        
        # Should succeed
        self.assertTrue(result.get('success', False), f"Creation failed: {result}")
        
        # Clean up
        if result.get('success'):
            ticket = Ticket.objects.get(uuid=result['data']['uuid'])
            ticket.delete(username=self.user_no_perms.username)
    
    def test_anonymous_user_behavior(self):
        """Test behavior with user having no permissions"""
        # Create a mock anonymous user by setting is_anonymous
        class AnonymousLikeUser:
            def __init__(self, base_user):
                self.base_user = base_user
                self.is_anonymous = True
                
            def __getattr__(self, name):
                return getattr(self.base_user, name)
        
        anon_user = AnonymousLikeUser(self.user_anon)
        service = TicketService(anon_user)
        
        obj_data = {
            'category': 'open_category',
            'title': 'Test anonymous',
            'resolution': '5,0'
        }
        
        with self.assertRaises(ValidationError) as cm:
            service.create(obj_data)
        
        # Check for authentication error
        error_str = str(cm.exception).lower()
        self.assertTrue('authentication' in error_str or 'permission' in error_str)
    
    def test_category_defaults_applied(self):
        """Test that category defaults are applied correctly"""
        user = LogInHelper().get_or_create_user_api()
        service = TicketService(user)
        
        # Test with restricted category (user needs permissions)
        self._add_permissions_to_user(user, ['127001', '127002'])
        
        obj_data = {
            'category': 'restricted_category',
            'title': 'Test defaults',
            'resolution': '5,0'
        }
        
        result = service.create(obj_data)
        
        if result.get('success'):
            ticket = Ticket.objects.get(uuid=result['data']['uuid'])
            # Should have category defaults
            self.assertEqual(ticket.priority, 'High')  # From category
            self.assertEqual(ticket.flags, 'urgent')  # Default flag
            ticket.delete(username=user.username)
    
    def test_permission_inheritance(self):
        """Test that child categories inherit parent permissions"""
        # Create a new config with hierarchical categories
        config = {
            'grievance_types': [
                'open_category',
                {
                    'name': 'parent_cat',
                    'permissions': ['127003'],
                    'children': ['child1', 'child2']
                }
            ],
            'grievance_flags': ['urgent'],
            'resolution_times': '5,0'
        }
        
        # Process config
        TicketConfig._TicketConfig__process_unified_categories(config)
        TicketConfig._TicketConfig__process_unified_flags(config)
        TicketConfig._TicketConfig__load_config(config)
        
        # User without parent permission
        service = TicketService(self.user_no_perms)
        
        obj_data = {
            'category': 'parent_cat|child1',
            'title': 'Test child category',
            'resolution': '5,0'
        }
        
        # Should fail - needs parent permission
        with self.assertRaises(ValidationError) as cm:
            service.create(obj_data)
        
        self.assertIn('parent_cat|child1', str(cm.exception))