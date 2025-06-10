import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)

MODULE_NAME = "grievance_social_protection"

DEFAULT_STRING = 'Default'
# CRON timedelta: {days},{hours}
DEFAULT_TIME_RESOLUTION = '5,0'

DEFAULT_CFG = {
    "default_validations_disabled": False,
    "gql_query_tickets_perms": ["127000"],
    "gql_query_comments_perms": ["127004"],
    "gql_mutation_create_tickets_perms": ["127001"],
    "gql_mutation_update_tickets_perms": ["127002"],
    "gql_mutation_delete_tickets_perms": ["127003"],
    "gql_mutation_create_comment_perms": ["127005"],
    "gql_mutation_resolve_grievance_perms": ["127006"],
    "tickets_attachments_root_path": None,

    # Main grievance categories from form
    "grievance_types": [
        DEFAULT_STRING, 
        # Sensitive categories
        "violence_vbg", 
        "corruption", 
        "accident_negligence", 
        "discrimination_ethnie_religion", 
        # Special categories
        "erreur_exclusion", 
        "erreur_inclusion", 
        "maladie_mentale", 
        # Non-sensitive categories
        "paiement", 
        "telephone", 
        "compte", 
        "information"
    ],
    
    # Flags for sensitive/special cases
    "grievance_flags": [
        DEFAULT_STRING, 
        "SENSITIVE", 
        "SPECIAL"
    ],
    
    # Communication channels
    "grievance_channels": [
        DEFAULT_STRING, 
        "telephone", 
        "sms", 
        "en_personne", 
        "courrier_simple", 
        "courrier_electronique", 
        "ligne_verte", 
        "boite_suggestion", 
        "autre"
    ],
    
    # VBG subcategories
    "vbg_types": [
        "viol",
        "mariage_force_precoce",
        "violence_abus",
        "sante_maternelle",
        "autre",
        "autre_"
    ],
    
    # Exclusion error subcategories
    "exclusion_types": [
        "demande_insertion",
        "probleme_identification",
        "autre"
    ],
    
    # Payment problem subcategories
    "payment_types": [
        "paiement_pas_recu",
        "paiement_en_retard",
        "paiement_incomplet",
        "vole",
        "autre"
    ],
    
    # Phone problem subcategories
    "phone_types": [
        "perdu",
        "pas_de_reseau",
        "allume_pas_batterie",
        "recoit_pas_tm",
        "mot_de_passe_oublie",
        "autre"
    ],
    
    # Account problem subcategories
    "account_types": [
        "non_active",
        "bloque",
        "autre"
    ],
    
    # Beneficiary types
    "beneficiary_types": [
        "ordinaire",
        "securite_alimentaire_cerc",
        "chocs_climatiques",
        "autre"
    ],

    "default_responses": {DEFAULT_STRING: DEFAULT_STRING},
    "grievance_anonymized_fields": {DEFAULT_STRING: []},
    # CRON timedelta: {days},{hours}
    "resolution_times": DEFAULT_TIME_RESOLUTION,
    "default_resolution": {
        DEFAULT_STRING: DEFAULT_TIME_RESOLUTION, 
        # Sensitive cases (high priority)
        "violence_vbg": "2,0", 
        "corruption": "3,0", 
        # Special cases (medium priority)
        "erreur_exclusion": "4,0", 
        "erreur_inclusion": "4,0", 
        "maladie_mentale": "3,0", 
        # Non-sensitive cases (normal priority)
        "paiement": "5,0", 
        "telephone": "5,0", 
        "compte": "5,0", 
        "information": "3,0"
    },

    "attending_staff_role_ids": [],
    "default_attending_staff_role_ids": {DEFAULT_STRING: [1, 2]},
}


class TicketConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = MODULE_NAME
    gql_query_tickets_perms = []
    gql_query_comments_perms = []
    gql_mutation_create_tickets_perms = []
    gql_mutation_update_tickets_perms = []
    gql_mutation_delete_tickets_perms = []
    gql_mutation_resolve_grievance_perms = []
    gql_mutation_create_comment_perms = []
    tickets_attachments_root_path = None

    grievance_types = []
    grievance_flags = []
    grievance_channels = []
    default_responses = {}
    grievance_anonymized_fields = {}
    resolution_times = {}
    default_resolution = {}
    attending_staff_role_ids = []
    default_attending_staff_role_ids = {}
    
    # Processed structures for enhanced configurations
    processed_categories = {}
    processed_flags = {}
    unified_resolution_times = {}

    def ready(self):
        from core.models import ModuleConfiguration
        cfg = ModuleConfiguration.get_or_default(MODULE_NAME, DEFAULT_CFG)
        self.__process_unified_categories(cfg)
        self.__process_unified_flags(cfg)
        self.__validate_grievance_dict_fields(cfg, 'default_responses')
        self.__validate_grievance_dict_fields(cfg, 'grievance_anonymized_fields')
        self.__validate_grievance_dict_fields(cfg, 'default_resolution')
        self.__validate_grievance_default_resolution_time(cfg)
        self.__load_config(cfg)

    @classmethod
    def __validate_grievance_dict_fields(cls, cfg, field_name):
        def get_grievance_type_options_msg(types):
            types_string = ", ".join(types)
            return logger.info(f'Available grievance types: {types_string}')

        dict_field = cfg.get(field_name, {})
        if not dict_field:
            return

        grievance_types = cfg.get('grievance_types', [])
        if not grievance_types:
            logger.warning('Please specify grievance_types if you want to setup %s.', field_name)

        if not isinstance(dict_field, dict):
            get_grievance_type_options_msg(grievance_types)
            return

        for field_key in dict_field.keys():
            if field_key not in grievance_types:
                logger.warning('%s in %s not in grievance_types', field_key, field_name)
                get_grievance_type_options_msg(grievance_types)

    @classmethod
    def __validate_grievance_default_resolution_time(cls, cfg):
        """
        Validate resolution times from both legacy default_resolution and new category-specific resolution_times.
        This method also builds a unified resolution times mapping that considers:
        1. Category-specific resolution_times (from processed_categories)
        2. Legacy default_resolution configuration
        3. Global resolution_times fallback
        """
        # First, validate legacy default_resolution
        dict_field = cfg.get("default_resolution", {})
        if dict_field:
            for key in dict_field:
                value = dict_field[key]
                if value in ['', None]:
                    resolution_times = cfg.get("resolution_times", DEFAULT_TIME_RESOLUTION)
                    logger.warning(
                        '"%s" has no value for resolution. The default one is taken as "%s".',
                        key,
                        resolution_times
                    )
                    dict_field[key] = resolution_times
                else:
                    cls.__validate_resolution_time_format(value, f"default_resolution[{key}]")
        
        # Then, validate resolution_times in processed categories
        processed_categories = cfg.get("processed_categories", {})
        for category_name, category_info in processed_categories.items():
            resolution_time = category_info.get('resolution_times')
            if resolution_time:
                cls.__validate_resolution_time_format(resolution_time, f"category '{category_name}'")
        
        # Build unified resolution times mapping for backward compatibility
        unified_resolution = {}
        
        # Start with legacy default_resolution
        if dict_field:
            unified_resolution.update(dict_field)
        
        # Override/add with category-specific resolution_times
        for category_name, category_info in processed_categories.items():
            resolution_time = category_info.get('resolution_times')
            if resolution_time:
                unified_resolution[category_name] = resolution_time
        
        # Store the unified mapping back
        cfg['unified_resolution_times'] = unified_resolution
    
    @classmethod
    def __validate_resolution_time_format(cls, value, context=""):
        """Validate a single resolution time format"""
        if ',' not in value:
            logger.warning(f"Invalid resolution time format for {context}. "
                         "Configuration should contain two integers representing days and hours, "
                         "separated by a comma.")
            return False
        
        try:
            parts = value.split(',')
            days = int(parts[0])
            hours = int(parts[1])
            
            if 0 <= days < 99 and 0 <= hours < 24:
                return True
            else:
                logger.warning(f"Invalid resolution time values for {context}. "
                             "Days must be between 0 and 99, and hours must be between 0 and 24.")
                return False
        except (ValueError, IndexError):
            logger.warning(f"Invalid resolution time format for {context}. "
                         "Expected format: 'days,hours' where both are integers.")
            return False

    @classmethod
    def __process_unified_categories(cls, cfg):
        """
        Process grievance_types configuration supporting both string and dict formats
        """
        categories = cfg.get('grievance_types', [])
        processed_categories = {}
        flat_types = []
        
        def process_category_item(item, parent_name=None, parent_info=None):
            """Process a single category item (string or dict)"""
            if isinstance(item, str):
                # Simple string format (backward compatible)
                full_name = f"{parent_name}|{item}" if parent_name else item
                processed_categories[full_name] = {
                    'priority': parent_info.get('priority', 'Medium') if parent_info else 'Medium',
                    'permissions': parent_info.get('permissions', []) if parent_info else [],  # Inherit from parent
                    'default_flags': parent_info.get('default_flags', []) if parent_info else [],
                    'resolution_times': parent_info.get('resolution_times') if parent_info else None,
                    'parent': parent_name,
                    'children': {}
                }
                flat_types.append(full_name)
                return full_name
                
            elif isinstance(item, dict):
                # Enhanced dict format with permissions
                cat_name = item.get('name')
                if not cat_name:
                    logger.warning("Category dict must have 'name' field")
                    return None
                
                full_name = f"{parent_name}|{cat_name}" if parent_name else cat_name
                
                # Process permissions - list format only, inherit from parent if not specified
                permissions = item.get('permissions', parent_info.get('permissions', []) if parent_info else [])
                
                # Inherit from parent if not specified
                priority = item.get('priority', parent_info.get('priority', 'Medium') if parent_info else 'Medium')
                default_flags = item.get('default_flags', parent_info.get('default_flags', []) if parent_info else [])
                
                # Handle resolution_times - inherit from parent if not specified
                resolution_times = item.get('resolution_times')
                if not resolution_times and parent_info:
                    resolution_times = parent_info.get('resolution_times')
                
                category_info = {
                    'priority': priority,
                    'permissions': permissions,
                    'default_flags': default_flags,
                    'resolution_times': resolution_times,
                    'parent': parent_name,
                    'children': {}
                }
                
                processed_categories[full_name] = category_info
                flat_types.append(full_name)
                
                # Process children recursively
                children = item.get('children', [])
                for child in children:
                    child_full_name = process_category_item(child, full_name, category_info)
                    if child_full_name:
                        child_short_name = child_full_name.split('|')[-1]
                        category_info['children'][child_short_name] = child_full_name
                
                return full_name
            
            return None
        
        # Process all top-level categories
        for category in categories:
            process_category_item(category)
        
        # Store processed data
        cfg['processed_categories'] = processed_categories
        # Update flat list for backward compatibility
        cfg['grievance_types'] = flat_types
        TicketConfig.processed_categories = processed_categories

    @classmethod
    def __process_unified_flags(cls, cfg):
        """
        Process grievance_flags configuration supporting both string and dict formats
        """
        flags = cfg.get('grievance_flags', [])
        processed_flags = {}
        flat_flags = []
        
        for flag in flags:
            if isinstance(flag, str):
                # Simple string format (backward compatible)
                processed_flags[flag] = {
                    'priority': 'Medium',
                    'permissions': []  # No restrictions - empty list
                }
                flat_flags.append(flag)
                
            elif isinstance(flag, dict):
                # Enhanced dict format with permissions
                flag_name = flag.get('name')
                if not flag_name:
                    logger.warning("Flag dict must have 'name' field")
                    continue
                
                # Process permissions - list format only
                permissions = flag.get('permissions', [])
                
                processed_flags[flag_name] = {
                    'priority': flag.get('priority', 'Medium'),
                    'permissions': permissions
                }
                flat_flags.append(flag_name)
        
        # Store processed data
        cfg['processed_flags'] = processed_flags
        # Update flat list for backward compatibility
        cfg['grievance_flags'] = flat_flags
        TicketConfig.processed_flags = processed_flags

    @classmethod
    def __load_config(cls, cfg):
        """
        Load all config fields that match current AppConfig class fields, all custom fields have to be loaded separately
        """
        for field in cfg:
            if hasattr(TicketConfig, field):
                setattr(TicketConfig, field, cfg[field])
