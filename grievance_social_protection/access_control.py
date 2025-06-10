import logging
from django.apps import apps
from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

class GrievanceAccessControl:
    """
    Handles rights-based access control for grievance categories and flags.
    
    Access rules:
    1. Categories/flags can have permission requirements using numeric permission codes
    2. Children inherit parent's permissions unless overridden
    3. Users must have ANY of the listed permissions for access
    4. Empty permissions list means no restrictions (backward compatibility)
    """
    
    @classmethod
    def check_category_permission(cls, user, category_name):
        """
        Check if user has permission for category
        
        Args:
            user: Django user object
            category_name: Full category name (e.g., "complaint" or "complaint|service_complaint")
        
        Returns:
            bool: True if user has permission or no permissions defined
        """
        if not user or user.is_anonymous:
            return False
        
        from .apps import TicketConfig
        
        processed_categories = getattr(TicketConfig, 'processed_categories', {})
        if not processed_categories or category_name not in processed_categories:
            # If no processed categories or category not found, allow access
            return True
        
        category_info = processed_categories[category_name]
        permissions = category_info.get('permissions', {})
        
        # If no permissions defined, allow access (backward compatibility)
        if not permissions:
            return True
        
        # Handle list format - if user has ANY permission in the list, they have access
        if isinstance(permissions, list):
            for perm_code in permissions:
                if user.has_perm(perm_code):
                    return True
            return False
        
        # Check inherited permissions from parent
        parent_name = category_info.get('parent')
        if parent_name:
            return cls.check_category_permission(user, parent_name)
        
        return True
    
    @classmethod
    def check_flag_permission(cls, user, flag_name):
        """
        Check if user has permission for flag
        
        Args:
            user: Django user object
            flag_name: Flag name
        
        Returns:
            bool: True if user has permission or no permissions defined
        """
        if not user or user.is_anonymous:
            return False
        
        from .apps import TicketConfig
        
        processed_flags = getattr(TicketConfig, 'processed_flags', {})
        if not processed_flags or flag_name not in processed_flags:
            # If no processed flags or flag not found, allow access
            return True
        
        flag_info = processed_flags[flag_name]
        permissions = flag_info.get('permissions', {})
        
        # If no permissions defined, allow access
        if not permissions:
            return True
        
        # Handle list format - if user has ANY permission in the list, they have access
        if isinstance(permissions, list):
            for perm_code in permissions:
                if user.has_perm(perm_code):
                    return True
            return False
        
        return True
    
    @classmethod
    def get_accessible_categories(cls, user, include_children=True):
        """
        Return list of categories accessible to the user.
        
        Args:
            user: The user to check access for
            include_children: If True, includes child categories in flat format
        
        Returns:
            List of category names the user can access
        """
        from .apps import TicketConfig
        
        # Start with all grievance_types for backward compatibility
        all_categories = list(TicketConfig.grievance_types)
        processed_categories = getattr(TicketConfig, 'processed_categories', {})
        
        if not processed_categories:
            return all_categories
        
        accessible_categories = []
        
        for category_name in all_categories:
            if cls.check_category_permission(user, category_name):
                if include_children or '|' not in category_name:
                    accessible_categories.append(category_name)
        
        return accessible_categories
    
    @classmethod
    def get_category_hierarchy(cls, user):
        """
        Return hierarchical structure of categories accessible to the user.
        
        Returns:
            List of category dicts with hierarchical structure
        """
        from .apps import TicketConfig
        
        processed_categories = getattr(TicketConfig, 'processed_categories', {})
        if not processed_categories:
            # Return flat list as hierarchy if no processed categories
            return [{"name": cat, "children": []} for cat in TicketConfig.grievance_types]
        
        hierarchy = []
        
        # Build hierarchy from processed categories
        for category_name, category_info in processed_categories.items():
            if not category_info.get('parent') and cls.check_category_permission(user, category_name):
                category_dict = {
                    'name': category_name,
                    'priority': category_info.get('priority', 'Medium'),
                    'permissions': category_info.get('permissions', []),
                    'default_flags': category_info.get('default_flags', []),
                    'children': []
                }
                
                # Add accessible children
                for child_name, child_info in processed_categories.items():
                    if child_info.get('parent') == category_name and cls.check_category_permission(user, child_name):
                        child_dict = {
                            'name': child_name.split('|')[-1],  # Just the child part
                            'full_name': child_name,
                            'priority': child_info.get('priority', category_info.get('priority', 'Medium')),
                            'permissions': child_info.get('permissions', []),
                            'default_flags': child_info.get('default_flags', [])
                        }
                        category_dict['children'].append(child_dict)
                
                hierarchy.append(category_dict)
        
        return hierarchy
    
    @classmethod
    def get_accessible_flags(cls, user):
        """Return list of flags accessible to the user"""
        from .apps import TicketConfig
        
        # Start with all grievance_flags
        all_flags = list(TicketConfig.grievance_flags)
        processed_flags = getattr(TicketConfig, 'processed_flags', {})
        
        if not processed_flags:
            return all_flags
        
        accessible_flags = []
        
        for flag_name in all_flags:
            if cls.check_flag_permission(user, flag_name):
                accessible_flags.append(flag_name)
        
        return accessible_flags
    
    @classmethod
    def validate_ticket_access(cls, user, category, flags=None):
        """
        Validate if user can create/view ticket with given category and flags.
        Raises PermissionDenied if access is not allowed.
        """
        # Check category access
        if category and not cls.check_category_permission(user, category):
            raise PermissionDenied(f"User does not have permission to create ticket with category: {category}")
        
        # Check flags access
        if flags:
            flag_list = flags.split() if isinstance(flags, str) else flags
            for flag in flag_list:
                if flag and not cls.check_flag_permission(user, flag):
                    raise PermissionDenied(f"User does not have permission to use flag: {flag}")
    
    @classmethod
    def get_category_defaults(cls, category_name):
        """Get default flags and priority for a category"""
        from .apps import TicketConfig
        
        processed_categories = getattr(TicketConfig, 'processed_categories', {})
        if not processed_categories or category_name not in processed_categories:
            return {'priority': 'Medium', 'default_flags': []}
        
        category_info = processed_categories[category_name]
        return {
            'priority': category_info.get('priority', 'Medium'),
            'default_flags': category_info.get('default_flags', [])
        }
    
    @classmethod
    def get_effective_priority(cls, category_name, flag_names=None):
        """
        Get the effective priority for a ticket based on category and flags.
        Higher priority wins (Critical > High > Medium > Low).
        """
        from .apps import TicketConfig
        
        priorities = ['Low', 'Medium', 'High', 'Critical']
        max_priority = 'Medium'  # Default
        
        # Check category priority
        processed_categories = getattr(TicketConfig, 'processed_categories', {})
        if processed_categories and category_name in processed_categories:
            cat_priority = processed_categories[category_name].get('priority', 'Medium')
            if priorities.index(cat_priority) > priorities.index(max_priority):
                max_priority = cat_priority
        
        # Check flag priorities
        if flag_names:
            processed_flags = getattr(TicketConfig, 'processed_flags', {})
            flag_list = flag_names.split() if isinstance(flag_names, str) else flag_names
            
            for flag_name in flag_list:
                if processed_flags and flag_name in processed_flags:
                    flag_priority = processed_flags[flag_name].get('priority', 'Medium')
                    if priorities.index(flag_priority) > priorities.index(max_priority):
                        max_priority = flag_priority
        
        return max_priority
    
    @classmethod
    def filter_ticket_queryset(cls, queryset, user):
        """
        Filter a ticket queryset based on user's category and flag view permissions.
        
        Args:
            queryset: Django queryset of tickets
            user: User to check permissions for
            
        Returns:
            Filtered queryset
        """
        from .apps import TicketConfig
        
        # Get accessible categories for viewing
        accessible_categories = cls.get_accessible_categories(user)
        
        # Filter tickets by accessible categories
        if accessible_categories is not None:
            # Only filter if we have processed categories (for backward compatibility)
            if hasattr(TicketConfig, 'processed_categories') and TicketConfig.processed_categories:
                queryset = queryset.filter(category__in=accessible_categories)
        
        # Further filter by flag permissions if needed
        if hasattr(TicketConfig, 'processed_flags') and TicketConfig.processed_flags:
            # Get flags that require permissions to view
            restricted_flags = []
            for flag_name, flag_info in TicketConfig.processed_flags.items():
                permissions = flag_info.get('permissions', [])
                # If flag has any permissions, check if user has at least one
                if permissions and not cls.check_flag_permission(user, flag_name):
                    restricted_flags.append(flag_name)
            
            # Exclude tickets with restricted flags
            if restricted_flags:
                for flag in restricted_flags:
                    queryset = queryset.exclude(flags__icontains=flag)
        
        return queryset