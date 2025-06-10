from django.test import TestCase

from grievance_social_protection.apps import TicketConfig


class ConfigProcessingTest(TestCase):
    """Test configuration processing for unified category and flag formats"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
    
    def test_process_simple_string_categories(self):
        """Test processing simple string category list"""
        cfg = {
            'grievance_types': ['complaint', 'feedback', 'appeal']
        }
        
        TicketConfig._TicketConfig__process_unified_categories(cfg)
        
        # Check flat list maintained
        self.assertEqual(cfg['grievance_types'], ['complaint', 'feedback', 'appeal'])
        
        # Check processed structure
        processed = cfg['processed_categories']
        self.assertEqual(len(processed), 3)
        
        # Check category details
        self.assertIn('complaint', processed)
        self.assertEqual(processed['complaint']['priority'], 'Medium')
        self.assertEqual(processed['complaint']['permissions'], [])
        self.assertEqual(processed['complaint']['parent'], None)
    
    def test_process_mixed_categories(self):
        """Test processing mixed string and dict categories"""
        cfg = {
            'grievance_types': [
                'simple',
                {
                    'name': 'complex',
                    'priority': 'High',
                    'permissions': ['127001', '127002'] 
                },
                {
                    'name': 'detailed',
                    'priority': 'Critical',
                    'permissions': ['127003', '127004'],
                    'default_flags': ['urgent']
                }
            ]
        }
        
        TicketConfig._TicketConfig__process_unified_categories(cfg)
        
        # Check flat list
        self.assertEqual(set(cfg['grievance_types']), {'simple', 'complex', 'detailed'})
        
        # Check processed details
        processed = cfg['processed_categories']
        
        # Simple string
        self.assertEqual(processed['simple']['permissions'], [])
        
        # List permissions
        self.assertEqual(processed['complex']['priority'], 'High')
        self.assertEqual(processed['complex']['permissions'], ['127001', '127002'])
        
        # Another list permissions format
        self.assertEqual(processed['detailed']['priority'], 'Critical')
        self.assertEqual(processed['detailed']['permissions'], ['127003', '127004'])
        self.assertEqual(processed['detailed']['default_flags'], ['urgent'])
    
    def test_process_hierarchical_categories(self):
        """Test processing hierarchical category structure"""
        cfg = {
            'grievance_types': [
                {
                    'name': 'parent',
                    'priority': 'High',
                    'permissions': ['127001', '127002'],
                    'default_flags': ['important'],
                    'children': [
                        {
                            'name': 'child1',
                            'permissions': ['127003']  # Override parent permissions
                        },
                        'child2',  # Simple string child
                        {
                            'name': 'child3',
                            'priority': 'Critical',  # Override parent priority
                        }
                    ]
                }
            ]
        }
        
        TicketConfig._TicketConfig__process_unified_categories(cfg)
        
        # Check flat list includes all levels
        expected = {'parent', 'parent|child1', 'parent|child2', 'parent|child3'}
        self.assertEqual(set(cfg['grievance_types']), expected)
        
        processed = cfg['processed_categories']
        
        # Check parent
        self.assertEqual(processed['parent']['priority'], 'High')
        self.assertEqual(processed['parent']['children'], {
            'child1': 'parent|child1',
            'child2': 'parent|child2',
            'child3': 'parent|child3'
        })
        
        # Check child inheritance
        self.assertEqual(processed['parent|child1']['parent'], 'parent')
        self.assertEqual(processed['parent|child1']['default_flags'], ['important'])
        self.assertEqual(processed['parent|child1']['permissions'], ['127003'])

        self.assertEqual(processed['parent|child3']['default_flags'], ['important'])  # Inherited
        self.assertEqual(processed['parent|child3']['permissions'], ['127001', '127002'])  # Inherited
        self.assertEqual(processed['parent|child3']['priority'], 'Critical')

        # Check simple string child
        self.assertEqual(processed['parent|child2']['priority'], 'High')  # Inherited
        self.assertEqual(processed['parent|child2']['permissions'], ['127001', '127002'])  # Inherited from parent
        self.assertEqual(processed['parent|child2']['default_flags'], ['important'])  # Inherited


    def test_process_flags(self):
        """Test processing flag configurations"""
        cfg = {
            'grievance_flags': [
                'simple_flag',
                {
                    'name': 'complex_flag',
                    'priority': 'High',
                    'permissions': ['127004', '127005']
                }
            ]
        }
        
        TicketConfig._TicketConfig__process_unified_flags(cfg)
        
        # Check flat list
        self.assertEqual(cfg['grievance_flags'], ['simple_flag', 'complex_flag'])

        processed = cfg['processed_flags']
        
        # Simple flag
        self.assertEqual(processed['simple_flag']['permissions'], [])
        
        # List permissions - stored as-is
        self.assertEqual(processed['complex_flag']['priority'], 'High')
        self.assertEqual(processed['complex_flag']['permissions'], ['127004', '127005'])
    
    def test_category_resolution_times(self):
        """Test processing categories with resolution times"""
        cfg = {
            'grievance_types': [
                {
                    'name': 'urgent',
                    'resolution_times': '1,0',  # 1 day
                    'children': [
                        {
                            'name': 'very_urgent',
                            'resolution_times': '0,12'  # 12 hours
                        },
                        {
                            'name': 'less_urgent'
                            # Inherits parent's 1,0 during processing
                        }
                    ]
                },
                'normal'  # No resolution time specified
            ],
            'resolution_times': '5,0'  # Global default
        }
        
        TicketConfig._TicketConfig__process_unified_categories(cfg)
        
        processed = cfg['processed_categories']
        
        # Check resolution times are stored
        self.assertEqual(processed['urgent']['resolution_times'], '1,0')
        self.assertEqual(processed['urgent|very_urgent']['resolution_times'], '0,12')
        # Child without resolution_times inherits from parent during processing
        self.assertEqual(processed['urgent|less_urgent']['resolution_times'], '1,0')
        # Simple category should not have resolution_times
        self.assertIsNone(processed['normal']['resolution_times'])
    
    def test_resolution_times_with_mixed_configuration(self):
        """Test resolution times with both category-specific and default_resolution"""
        cfg = {
            'grievance_types': [
                {
                    'name': 'priority_cat',
                    'resolution_times': '2,0'  # Category-specific
                },
                'legacy_cat'
            ],
            'default_resolution': {
                'priority_cat': '3,0',  # Should be overridden by category-specific
                'legacy_cat': '4,0'     # Should be used
            },
            'resolution_times': '5,0'
        }
        
        TicketConfig._TicketConfig__process_unified_categories(cfg)
        TicketConfig._TicketConfig__validate_grievance_default_resolution_time(cfg)
        
        # Check unified resolution times mapping
        unified = cfg.get('unified_resolution_times', {})
        self.assertEqual(unified['priority_cat'], '2,0')  # Category-specific wins
        self.assertEqual(unified['legacy_cat'], '4,0')    # From default_resolution