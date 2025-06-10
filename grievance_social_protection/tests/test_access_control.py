from django.core.exceptions import PermissionDenied
from django.test import TestCase
from core.test_helpers import create_test_interactive_user

from grievance_social_protection.access_control import GrievanceAccessControl
from grievance_social_protection.apps import TicketConfig


class GrievanceAccessControlTest(TestCase):
    """Test rights-based access control for grievance categories and flags"""
    
    user_with_perms = None
    user_no_perms = None
    user_limited_perms = None
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test users with different permission levels
        cls.user_with_perms = create_test_interactive_user(username='user_all_perms', roles=[7])
        cls.user_no_perms = create_test_interactive_user(username='user_no_perms', roles=[1])
        cls.user_limited_perms = create_test_interactive_user(username='user_limited_perms', roles=[1])
        
        # Mock has_perm for test users
        cls.user_with_perms.has_perm = lambda perm: True
        cls.user_no_perms.has_perm = lambda perm: False
        cls.user_limited_perms.has_perm = lambda perm: perm in [
            '127000',  # View tickets
            '127001',  # Create tickets
            '127004'   # View comments
        ]
    
    def setUp(self):
        """Set up test configuration before each test"""
        self._setup_test_config()
    
    def _setup_test_config(self):
        """Set up test configuration data"""
        # Create configuration in the format that TicketConfig expects
        cfg = {
            'grievance_types': [
                'simple_category',
                {
                    'name': 'complaint',
                    'priority': 'High',
                    'permissions': ['127000', '127001'],  # View and create tickets
                    'default_flags': ['urgent'],
                    'children': [
                        {
                            'name': 'service_complaint',
                            'permissions': ['127002']  # Update tickets
                        }
                    ]
                },
                {
                    'name': 'feedback',
                    'priority': 'Low',
                    'permissions': ['127000']  # View tickets
                },
                {
                    'name': 'restricted_category',
                    'priority': 'Critical',
                    'permissions': ['127002', '127003'],  # Update and delete tickets
                    'default_flags': ['sensitive']
                }
            ],
            'grievance_flags': [
                {
                    'name': 'urgent',
                    'priority': 'High'
                },
                {
                    'name': 'sensitive',
                    'priority': 'Critical',
                    'permissions': ['127004', '127005']  # View and create comments
                },
                'public'
            ]
        }
        
        # Process the configuration using TicketConfig methods (mimicking ready() method)
        TicketConfig._TicketConfig__process_unified_categories(cfg)
        TicketConfig._TicketConfig__process_unified_flags(cfg)
        TicketConfig._TicketConfig__load_config(cfg)
    
    def test_check_category_permission_no_restrictions(self):
        """Test category access with no permission restrictions"""
        # Should allow access for all users when no permissions defined
        result = GrievanceAccessControl.check_category_permission(
            self.user_no_perms, 'simple_category'
        )
        self.assertTrue(result)
        
        result = GrievanceAccessControl.check_category_permission(
            self.user_with_perms, 'simple_category'
        )
        self.assertTrue(result)
    
    def test_check_category_permission_with_restrictions(self):
        """Test category access with permission restrictions"""
        # User with permissions should have access
        result = GrievanceAccessControl.check_category_permission(
            self.user_with_perms, 'complaint'
        )
        self.assertTrue(result)
        
        # User without permissions should not have access
        result = GrievanceAccessControl.check_category_permission(
            self.user_no_perms, 'complaint'
        )
        self.assertFalse(result)
    
    def test_check_category_permission_inheritance(self):
        """Test permission inheritance from parent categories"""
        # Child inherits create permission from parent - user with all perms
        result = GrievanceAccessControl.check_category_permission(
            self.user_with_perms, 'complaint|service_complaint'
        )
        self.assertTrue(result)
        
        # User without permissions should not inherit
        result = GrievanceAccessControl.check_category_permission(
            self.user_no_perms, 'complaint|service_complaint'
        )
        self.assertFalse(result)
    
    def test_check_flag_permission(self):
        """Test flag permission checking"""
        # No restrictions
        result = GrievanceAccessControl.check_flag_permission(
            self.user_no_perms, 'urgent'
        )
        self.assertTrue(result)
        
        # With restrictions - user with perms
        result = GrievanceAccessControl.check_flag_permission(
            self.user_with_perms, 'sensitive'
        )
        self.assertTrue(result)
        
        # With restrictions - user without perms
        result = GrievanceAccessControl.check_flag_permission(
            self.user_no_perms, 'sensitive'
        )
        self.assertFalse(result)
    
    def test_get_accessible_categories(self):
        """Test filtering categories by user permissions"""
        # User with all permissions
        accessible = GrievanceAccessControl.get_accessible_categories(
            self.user_with_perms
        )
        self.assertEqual(len(accessible), 5)  # All categories
        
        # User with no permissions
        accessible = GrievanceAccessControl.get_accessible_categories(
            self.user_no_perms
        )
        self.assertEqual(accessible, ['simple_category'])  # Only unrestricted
    
    def test_get_category_hierarchy(self):
        """Test hierarchical category structure generation"""
        hierarchy = GrievanceAccessControl.get_category_hierarchy(
            self.user_with_perms
        )
        
        # Should have top-level categories
        names = [cat['name'] for cat in hierarchy]
        self.assertIn('complaint', names)
        self.assertIn('simple_category', names)
        
        # Check children
        complaint = next(cat for cat in hierarchy if cat['name'] == 'complaint')
        self.assertEqual(len(complaint['children']), 1)
        self.assertEqual(complaint['children'][0]['name'], 'service_complaint')
    
    def test_get_accessible_flags(self):
        """Test filtering flags by user permissions"""
        # User with permissions
        flags = GrievanceAccessControl.get_accessible_flags(self.user_with_perms)
        self.assertEqual(set(flags), {'urgent', 'sensitive', 'public'})
        
        # User without permissions
        flags = GrievanceAccessControl.get_accessible_flags(self.user_no_perms)
        self.assertEqual(set(flags), {'urgent', 'public'})  # Only unrestricted
    
    def test_validate_ticket_access(self):
        """Test ticket access validation"""
        # Should not raise for valid access
        try:
            GrievanceAccessControl.validate_ticket_access(
                self.user_with_perms, 'complaint', 'urgent'
            )
        except PermissionDenied:
            self.fail("validate_ticket_access raised PermissionDenied unexpectedly")
        
        # Should raise for invalid category access
        with self.assertRaises(PermissionDenied) as context:
            GrievanceAccessControl.validate_ticket_access(
                self.user_no_perms, 'complaint', None
            )
        self.assertIn('complaint', str(context.exception))
        
        # Should raise for invalid flag access
        with self.assertRaises(PermissionDenied) as context:
            GrievanceAccessControl.validate_ticket_access(
                self.user_no_perms, 'simple_category', 'sensitive'
            )
        self.assertIn('sensitive', str(context.exception))
    
    def test_get_category_defaults(self):
        """Test getting category default values"""
        defaults = GrievanceAccessControl.get_category_defaults('complaint')
        self.assertEqual(defaults['priority'], 'High')
        self.assertEqual(defaults['default_flags'], ['urgent'])
        
    
    def test_get_effective_priority(self):
        """Test priority calculation from category and flags"""
        # Category priority
        priority = GrievanceAccessControl.get_effective_priority('complaint', None)
        self.assertEqual(priority, 'High')
        
        # Flag overrides with higher priority
        priority = GrievanceAccessControl.get_effective_priority(
            'simple_category', 'sensitive'
        )
        self.assertEqual(priority, 'Critical')
        
        # Multiple flags - highest wins
        priority = GrievanceAccessControl.get_effective_priority(
            'simple_category', ['urgent', 'public']
        )
        self.assertEqual(priority, 'High')
    
    def test_backward_compatibility(self):
        """Test backward compatibility with simple string configurations"""
        # Reset to simple configuration
        TicketConfig.processed_categories = {}
        TicketConfig.processed_flags = {}
        
        # Should return all categories when no processed config
        categories = GrievanceAccessControl.get_accessible_categories(
            self.user_no_perms
        )
        self.assertEqual(categories, TicketConfig.grievance_types)
        
        # Should return all flags when no processed config
        flags = GrievanceAccessControl.get_accessible_flags(self.user_no_perms)
        self.assertEqual(flags, TicketConfig.grievance_flags)
    
    def test_parent_visible_child_restricted_permissions(self):
        """Test permission checking where parent is accessible but specific child is not"""
        # Add test configuration for mixed parent-child permissions
        additional_cfg = {
            'grievance_types': [
                {
                    'name': 'parent_mixed',
                    'priority': 'Medium',
                    'permissions': ['127000'],  # View tickets - Limited user has this
                    'children': [
                        {
                            'name': 'accessible_child'
                            # No permissions - will inherit parent's
                        },
                        {
                            'name': 'restricted_child',
                            'priority': 'High',
                            'permissions': ['127006']  # Resolve grievances - Limited user doesn't have this
                        }
                    ]
                }
            ]
        }
        
        # Process the additional configuration
        TicketConfig._TicketConfig__process_unified_categories(additional_cfg)
        
        # Merge with existing configuration and reload
        TicketConfig.grievance_types.extend(additional_cfg['grievance_types'])
        TicketConfig.processed_categories.update(additional_cfg['processed_categories'])
        
        # Test parent access
        self.assertTrue(
            GrievanceAccessControl.check_category_permission(
                self.user_limited_perms, 'parent_mixed'
            )
        )
        
        # Test accessible child (inherits parent permission)
        self.assertTrue(
            GrievanceAccessControl.check_category_permission(
                self.user_limited_perms, 'parent_mixed|accessible_child'
            )
        )
        
        # Test restricted child (requires different permission)
        self.assertFalse(
            GrievanceAccessControl.check_category_permission(
                self.user_limited_perms, 'parent_mixed|restricted_child'
            )
        )
        
        # User with all permissions should access everything
        self.assertTrue(
            GrievanceAccessControl.check_category_permission(
                self.user_with_perms, 'parent_mixed|restricted_child'
            )
        )
        
        # Test hierarchy retrieval
        hierarchy = GrievanceAccessControl.get_category_hierarchy(
            self.user_limited_perms
        )
        
        # Find the parent_mixed category in hierarchy
        parent_mixed = next((cat for cat in hierarchy if cat['name'] == 'parent_mixed'), None)
        self.assertIsNotNone(parent_mixed)
        
        # Should have only one visible child
        visible_children = parent_mixed.get('children', [])
        self.assertEqual(len(visible_children), 1)
        self.assertEqual(visible_children[0]['name'], 'accessible_child')
    